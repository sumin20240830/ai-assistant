import asyncio
import json

from fastapi.testclient import TestClient

from app.main import app
from app.models.knowledge_schema import KnowledgeChunk
from app.services import llm_service
from app.services import knowledge_service
from app.services.knowledge_service import (
    chunk_markdown,
    format_knowledge_context,
    list_knowledge_chunks,
    reindex_knowledge_base,
    search_knowledge,
)


def configure_test_knowledge_base(tmp_path, monkeypatch):
    knowledge_dir = tmp_path / "knowledge_base"
    knowledge_dir.mkdir()
    database_path = tmp_path / "data" / "knowledge_base.db"

    monkeypatch.setattr(knowledge_service, "KNOWLEDGE_DIR", knowledge_dir)
    monkeypatch.setattr(
        knowledge_service,
        "KNOWLEDGE_DB_PATH",
        database_path,
    )
    return knowledge_dir


def test_chunk_markdown_uses_level_two_sections(tmp_path):
    document = tmp_path / "rules.md"
    document.write_text(
        "# 字段规范\n\n## 类型规则\n\n手机号使用 string。\n\n"
        "## 枚举规则\n\nenum 必须提供 enumOptions。\n",
        encoding="utf-8",
    )

    chunks = chunk_markdown(document)

    assert len(chunks) == 2
    assert chunks[0].section_path == ["字段规范", "类型规则"]
    assert chunks[1].section_title == "枚举规则"
    assert chunks[0].content.startswith("# 字段规范")


def test_reindex_list_and_chinese_search(tmp_path, monkeypatch):
    knowledge_dir = configure_test_knowledge_base(tmp_path, monkeypatch)
    (knowledge_dir / "field_types.md").write_text(
        "# 字段类型\n\n## 手机号\n\n手机号用于标识，应使用 string。\n\n"
        "## 金额\n\n订单金额可能包含小数，应使用 number。\n",
        encoding="utf-8",
    )
    (knowledge_dir / "validation_rules.md").write_text(
        "# 校验规范\n\n## 枚举校验\n\nenum 必须提供 enumOptions。\n",
        encoding="utf-8",
    )

    summary = reindex_knowledge_base()
    chunks, total = list_knowledge_chunks()
    results = search_knowledge("客户手机号需要校验", top_k=2)

    assert summary.documentCount == 2
    assert summary.chunkCount == 3
    assert total == 3
    assert len(chunks) == 3
    assert results
    assert results[0].sectionTitle == "手机号"
    assert results[0].score is not None


def test_index_is_rebuilt_after_document_change(tmp_path, monkeypatch):
    knowledge_dir = configure_test_knowledge_base(tmp_path, monkeypatch)
    document = knowledge_dir / "rules.md"
    document.write_text(
        "# 规范\n\n## 类型\n\n手机号使用 string。\n",
        encoding="utf-8",
    )
    first = reindex_knowledge_base()

    document.write_text(
        "# 规范\n\n## 类型\n\n手机号使用 string。\n\n"
        "## 命名\n\nfieldCode 使用小驼峰。\n",
        encoding="utf-8",
    )
    chunks, total = list_knowledge_chunks()

    assert first.chunkCount == 1
    assert total == 2
    assert {chunk.sectionTitle for chunk in chunks} == {"类型", "命名"}


def test_context_contains_source_and_has_size_limit(tmp_path, monkeypatch):
    knowledge_dir = configure_test_knowledge_base(tmp_path, monkeypatch)
    (knowledge_dir / "rules.md").write_text(
        "# 规范\n\n## 类型\n\n" + "字段类型规则。" * 100,
        encoding="utf-8",
    )
    reindex_knowledge_base()
    results = search_knowledge("字段类型", top_k=1)

    context = format_knowledge_context(results, max_chars=160)

    assert "来源：knowledge_base/rules.md" in context
    assert "章节：规范 > 类型" in context
    assert len(context) <= 160


def test_llm_context_retrieval_reports_sse_progress(monkeypatch):
    chunk = KnowledgeChunk(
        chunkId=1,
        documentName="field_types.md",
        sourcePath="knowledge_base/field_types.md",
        sectionTitle="支持的字段类型",
        sectionPath=["实体字段类型规范", "支持的字段类型"],
        content="# 实体字段类型规范\n\n手机号使用 string。",
        score=1.0,
    )
    monkeypatch.setattr(
        llm_service,
        "search_knowledge",
        lambda query, top_k: [chunk],
    )
    progress_events = []

    async def report(status, message, progress, repair_attempt):
        progress_events.append(
            (status, message, progress, repair_attempt)
        )

    context = asyncio.run(
        llm_service.retrieve_knowledge_context("手机号", report)
    )
    prompt = llm_service.get_system_prompt(context)

    assert progress_events == [
        ("retrieving", "正在检索项目知识库", 10, 0)
    ]
    assert "knowledge_base/field_types.md" in context
    assert "<knowledge_context>" in prompt
    assert "手机号使用 string" in prompt


def test_knowledge_api(tmp_path, monkeypatch):
    knowledge_dir = configure_test_knowledge_base(tmp_path, monkeypatch)
    (knowledge_dir / "rules.md").write_text(
        "# 规范\n\n## 枚举\n\n枚举字段必须提供 enumOptions。\n",
        encoding="utf-8",
    )

    with TestClient(app) as client:
        reindex_response = client.post("/api/knowledge/reindex")
        search_response = client.post(
            "/api/knowledge/search",
            json={"query": "枚举字段怎么建模", "topK": 3},
        )
        chunks_response = client.get("/api/knowledge/chunks")

    assert reindex_response.status_code == 200
    assert reindex_response.json()["chunkCount"] == 1
    assert search_response.status_code == 200
    assert search_response.json()["items"][0]["sectionTitle"] == "枚举"
    assert chunks_response.status_code == 200
    assert chunks_response.json()["total"] == 1
    # API 输出必须是合法 JSON，避免 datetime 等字段序列化异常。
    json.dumps(reindex_response.json(), ensure_ascii=False)
