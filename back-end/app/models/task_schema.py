from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.validate_schema import EntitySchema


TaskType = Literal["generate", "refine"]
TaskStatus = Literal[
    "queued",
    "running",
    "validating",
    "repairing",
    "succeeded",
    "failed",
]


class CreateSchemaTaskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: TaskType
    requirement: str | None = Field(default=None, min_length=5, max_length=2000)
    instruction: str | None = Field(default=None, min_length=2, max_length=1000)
    currentSchema: EntitySchema | None = None


class TaskAccepted(BaseModel):
    taskId: str
    status: TaskStatus


class SchemaTask(BaseModel):
    taskId: str
    type: TaskType
    status: TaskStatus
    message: str
    progress: int = Field(ge=0, le=100)
    repairAttempt: int = 0
    createdAt: datetime
    updatedAt: datetime
    result: EntitySchema | None = None
    error: dict | None = None
