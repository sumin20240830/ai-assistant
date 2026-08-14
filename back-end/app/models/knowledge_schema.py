from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeSearchRequest(BaseModel):
    """知识库检索请求。"""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=2, max_length=2000)
    topK: int = Field(default=5, ge=1, le=10)


class KnowledgeChunk(BaseModel):
    """可以注入 LLM 提示词的知识片段。"""

    chunkId: int
    documentName: str
    sourcePath: str
    sectionTitle: str
    sectionPath: list[str]
    content: str
    score: float | None = None


class KnowledgeSearchResponse(BaseModel):
    query: str
    items: list[KnowledgeChunk]
    total: int


class KnowledgeChunkListResponse(BaseModel):
    items: list[KnowledgeChunk]
    total: int


class KnowledgeIndexSummary(BaseModel):
    documentCount: int
    chunkCount: int
    indexedAt: datetime

