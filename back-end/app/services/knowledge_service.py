import hashlib
import json
import re
import sqlite3
import threading
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.models.knowledge_schema import (
    KnowledgeChunk,
    KnowledgeIndexSummary,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge_base"
KNOWLEDGE_DB_PATH = PROJECT_ROOT / "data" / "knowledge_base.db"

_index_lock = threading.RLock()
_heading_pattern = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_latin_pattern = re.compile(r"[a-zA-Z][a-zA-Z0-9_]{1,}")
_cjk_pattern = re.compile(r"[\u3400-\u9fff]+")


class KnowledgeBaseError(RuntimeError):
    """知识库加载、索引或检索失败。"""


@dataclass(frozen=True)
class MarkdownChunk:
    document_name: str
    source_path: str
    section_title: str
    section_path: list[str]
    content: str
    position: int


def chunk_markdown(path: Path) -> list[MarkdownChunk]:
    """按二级标题切分 Markdown，并保留文档标题作为上下文。"""

    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []

    lines = text.splitlines()
    document_title = path.stem

    for line in lines:
        match = _heading_pattern.match(line)
        if match and len(match.group(1)) == 1:
            document_title = match.group(2).strip()
            break

    sections: list[tuple[str, list[str]]] = []
    current_title: str | None = None
    current_lines: list[str] = []

    for line in lines:
        match = _heading_pattern.match(line)

        if match and len(match.group(1)) == 2:
            if current_title is not None and current_lines:
                sections.append((current_title, current_lines))

            current_title = match.group(2).strip()
            current_lines = [line]
            continue

        if current_title is not None:
            current_lines.append(line)

    if current_title is not None and current_lines:
        sections.append((current_title, current_lines))

    # 没有二级标题的文档仍作为一个完整片段进入知识库。
    if not sections:
        sections = [(document_title, lines)]

    source_path = f"knowledge_base/{path.name}"
    result: list[MarkdownChunk] = []

    for position, (section_title, section_lines) in enumerate(sections):
        section_content = "\n".join(section_lines).strip()
        content = f"# {document_title}\n\n{section_content}".strip()

        result.append(
            MarkdownChunk(
                document_name=path.name,
                source_path=source_path,
                section_title=section_title,
                section_path=[document_title, section_title],
                content=content,
                position=position,
            )
        )

    return result


def _connect() -> sqlite3.Connection:
    KNOWLEDGE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(KNOWLEDGE_DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def _initialize_database(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS knowledge_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )

    try:
        connection.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_chunks USING fts5(
                document_name UNINDEXED,
                source_path UNINDEXED,
                section_title,
                section_path,
                content,
                position UNINDEXED,
                content_hash UNINDEXED,
                tokenize='trigram'
            )
            """
        )
    except sqlite3.OperationalError as error:
        # 老版本 SQLite 可能没有 trigram tokenizer，仍可使用 unicode61
        # 建立索引，中文检索由 Python 兜底评分完成。
        if "tokenizer" not in str(error).lower():
            raise

        connection.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_chunks USING fts5(
                document_name UNINDEXED,
                source_path UNINDEXED,
                section_title,
                section_path,
                content,
                position UNINDEXED,
                content_hash UNINDEXED,
                tokenize='unicode61'
            )
            """
        )


def _list_documents() -> list[Path]:
    if not KNOWLEDGE_DIR.exists():
        raise KnowledgeBaseError(f"知识库目录不存在：{KNOWLEDGE_DIR}")

    documents = sorted(KNOWLEDGE_DIR.glob("*.md"))
    if not documents:
        raise KnowledgeBaseError("知识库目录中没有 Markdown 文档")

    return documents


def _calculate_source_hash(documents: list[Path]) -> str:
    digest = hashlib.sha256()

    for path in documents:
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")

    return digest.hexdigest()


def _get_meta(connection: sqlite3.Connection, key: str) -> str | None:
    row = connection.execute(
        "SELECT value FROM knowledge_meta WHERE key = ?",
        (key,),
    ).fetchone()
    return None if row is None else str(row["value"])


def _set_meta(connection: sqlite3.Connection, key: str, value: str) -> None:
    connection.execute(
        """
        INSERT INTO knowledge_meta(key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value),
    )


def _summary_from_connection(
    connection: sqlite3.Connection,
) -> KnowledgeIndexSummary:
    indexed_at = _get_meta(connection, "indexed_at")
    if indexed_at is None:
        raise KnowledgeBaseError("知识库尚未建立索引")

    return KnowledgeIndexSummary(
        documentCount=int(_get_meta(connection, "document_count") or 0),
        chunkCount=int(_get_meta(connection, "chunk_count") or 0),
        indexedAt=datetime.fromisoformat(indexed_at),
    )


def reindex_knowledge_base() -> KnowledgeIndexSummary:
    """重新读取全部 Markdown，并以单个事务替换现有索引。"""

    with _index_lock:
        try:
            documents = _list_documents()
            source_hash = _calculate_source_hash(documents)
            chunks = [
                chunk
                for document in documents
                for chunk in chunk_markdown(document)
            ]

            if not chunks:
                raise KnowledgeBaseError("知识库文档没有可索引的内容")

            indexed_at = datetime.now(timezone.utc)

            with _connect() as connection:
                _initialize_database(connection)
                connection.execute("BEGIN IMMEDIATE")
                connection.execute("DELETE FROM knowledge_chunks")

                for chunk in chunks:
                    content_hash = hashlib.sha256(
                        chunk.content.encode("utf-8")
                    ).hexdigest()
                    connection.execute(
                        """
                        INSERT INTO knowledge_chunks(
                            document_name,
                            source_path,
                            section_title,
                            section_path,
                            content,
                            position,
                            content_hash
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            chunk.document_name,
                            chunk.source_path,
                            chunk.section_title,
                            json.dumps(chunk.section_path, ensure_ascii=False),
                            chunk.content,
                            chunk.position,
                            content_hash,
                        ),
                    )

                _set_meta(connection, "source_hash", source_hash)
                _set_meta(connection, "indexed_at", indexed_at.isoformat())
                _set_meta(connection, "document_count", str(len(documents)))
                _set_meta(connection, "chunk_count", str(len(chunks)))

                return _summary_from_connection(connection)

        except (OSError, sqlite3.Error) as error:
            raise KnowledgeBaseError(f"知识库索引失败：{error}") from error


def ensure_knowledge_index() -> KnowledgeIndexSummary:
    """首次使用或源文档变化时自动重建索引。"""

    with _index_lock:
        try:
            documents = _list_documents()
            current_hash = _calculate_source_hash(documents)

            with _connect() as connection:
                _initialize_database(connection)
                indexed_hash = _get_meta(connection, "source_hash")

                if indexed_hash == current_hash:
                    return _summary_from_connection(connection)

            return reindex_knowledge_base()

        except KnowledgeBaseError:
            raise
        except (OSError, sqlite3.Error) as error:
            raise KnowledgeBaseError(f"知识库初始化失败：{error}") from error


def get_knowledge_index_summary() -> KnowledgeIndexSummary:
    return ensure_knowledge_index()


def _row_to_chunk(
    row: sqlite3.Row,
    score: float | None = None,
) -> KnowledgeChunk:
    return KnowledgeChunk(
        chunkId=int(row["chunk_id"]),
        documentName=str(row["document_name"]),
        sourcePath=str(row["source_path"]),
        sectionTitle=str(row["section_title"]),
        sectionPath=json.loads(row["section_path"]),
        content=str(row["content"]),
        score=score,
    )


def list_knowledge_chunks(
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[KnowledgeChunk], int]:
    ensure_knowledge_index()

    try:
        with _connect() as connection:
            total = int(
                connection.execute(
                    "SELECT COUNT(*) FROM knowledge_chunks"
                ).fetchone()[0]
            )
            rows = connection.execute(
                """
                SELECT
                    rowid AS chunk_id,
                    document_name,
                    source_path,
                    section_title,
                    section_path,
                    content
                FROM knowledge_chunks
                ORDER BY document_name, CAST(position AS INTEGER)
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()

        return [_row_to_chunk(row) for row in rows], total

    except sqlite3.Error as error:
        raise KnowledgeBaseError(f"读取知识片段失败：{error}") from error


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []

    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)

    return result


def _extract_search_terms(query: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", query).lower()
    terms = [item.lower() for item in _latin_pattern.findall(normalized)]

    for sequence in _cjk_pattern.findall(normalized):
        if len(sequence) <= 6:
            terms.append(sequence)

        if len(sequence) >= 3:
            terms.extend(
                sequence[index:index + 3]
                for index in range(len(sequence) - 2)
            )
        elif len(sequence) == 2:
            terms.append(sequence)

    # 查询过长时优先保留前面的业务词，防止 MATCH 表达式无限增长。
    return _unique(terms)[:40]


def _build_match_expression(query: str) -> str:
    terms = _extract_search_terms(query)
    return " OR ".join(
        f'"{term.replace(chr(34), chr(34) * 2)}"'
        for term in terms
    )


def _fts_search(
    connection: sqlite3.Connection,
    query: str,
    limit: int,
) -> list[tuple[sqlite3.Row, float]]:
    match_expression = _build_match_expression(query)
    if not match_expression:
        return []

    rows = connection.execute(
        """
        SELECT
            rowid AS chunk_id,
            document_name,
            source_path,
            section_title,
            section_path,
            content,
            bm25(knowledge_chunks) AS search_rank
        FROM knowledge_chunks
        WHERE knowledge_chunks MATCH ?
        ORDER BY search_rank
        LIMIT ?
        """,
        (match_expression, limit),
    ).fetchall()

    raw_scores = [max(0.0, -float(row["search_rank"])) for row in rows]
    max_score = max(raw_scores, default=0.0)

    return [
        (row, (score / max_score if max_score > 0 else 0.0))
        for row, score in zip(rows, raw_scores, strict=True)
    ]


def _fallback_search(
    connection: sqlite3.Connection,
    query: str,
    limit: int,
) -> list[tuple[sqlite3.Row, float]]:
    terms = _extract_search_terms(query)
    if not terms:
        return []

    rows = connection.execute(
        """
        SELECT
            rowid AS chunk_id,
            document_name,
            source_path,
            section_title,
            section_path,
            content
        FROM knowledge_chunks
        """
    ).fetchall()

    scored: list[tuple[sqlite3.Row, float]] = []

    for row in rows:
        searchable = unicodedata.normalize(
            "NFKC",
            f'{row["section_title"]} {row["content"]}',
        ).lower()
        matched_weight = sum(len(term) for term in terms if term in searchable)

        if matched_weight > 0:
            scored.append((row, float(matched_weight)))

    scored.sort(key=lambda item: item[1], reverse=True)
    scored = scored[:limit]
    max_score = max((score for _, score in scored), default=0.0)

    return [
        (row, score / max_score if max_score > 0 else 0.0)
        for row, score in scored
    ]


def search_knowledge(
    query: str,
    top_k: int = 5,
) -> list[KnowledgeChunk]:
    ensure_knowledge_index()

    if not query.strip():
        return []

    try:
        with _connect() as connection:
            try:
                matches = _fts_search(connection, query, top_k)
            except sqlite3.OperationalError:
                matches = []

            # unicode61 无法可靠切分中文，或 FTS 没找到结果时使用兜底检索。
            if len(matches) < top_k:
                fallback = _fallback_search(connection, query, top_k * 2)
                existing_ids = {int(row["chunk_id"]) for row, _ in matches}

                for row, score in fallback:
                    if int(row["chunk_id"]) not in existing_ids:
                        matches.append((row, score * 0.8))
                        existing_ids.add(int(row["chunk_id"]))

                    if len(matches) >= top_k:
                        break

        return [
            _row_to_chunk(row, round(score, 6))
            for row, score in matches[:top_k]
        ]

    except sqlite3.Error as error:
        raise KnowledgeBaseError(f"知识库检索失败：{error}") from error


def format_knowledge_context(
    chunks: list[KnowledgeChunk],
    max_chars: int = 6000,
) -> str:
    """把检索结果转换为有边界、可追踪来源的提示词上下文。"""

    parts: list[str] = []
    used_chars = 0

    for index, chunk in enumerate(chunks, start=1):
        header = (
            f"[知识片段 {index}]\n"
            f"来源：{chunk.sourcePath}\n"
            f"章节：{' > '.join(chunk.sectionPath)}\n"
        )
        remaining = max_chars - used_chars - len(header)
        if remaining <= 0:
            break

        content = chunk.content[:remaining]
        parts.append(f"{header}{content}")
        used_chars += len(header) + len(content)

        if len(content) < len(chunk.content):
            break

    return "\n\n".join(parts)

