from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.validate_schema import EntitySchema


VersionSource = Literal["generate", "refine", "restore", "draft"]


class CreateSchemaVersionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    sessionId: str = Field(min_length=1, max_length=100)
    schemaData: EntitySchema = Field(alias="schema")
    source: VersionSource
    reason: str | None = Field(default=None, max_length=500)


class SchemaVersionRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    sessionId: str
    version: int
    source: VersionSource
    reason: str | None = None
    createdAt: str
    schemaData: EntitySchema = Field(alias="schema")
