from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.validate_schema import EntitySchema


TaskType = Literal["generate", "refine"]
TaskStatus = Literal[
    "queued",
    "retrieving",
    "running",
    "validating",
    "repairing",
    "succeeded",
    "failed",
]

# 项目支持两种异步任务
# generate：首次生成 Schema
# refine：增量修改 Schema
# 参数来自于前端接口发送的请求体
class CreateSchemaTaskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: TaskType
    requirement: str | None = Field(default=None, min_length=5, max_length=2000)
    instruction: str | None = Field(default=None, min_length=2, max_length=1000)
    currentSchema: EntitySchema | None = None

    @model_validator(mode="after")
    def validate_payload(self):
        if self.type == "generate" and not self.requirement:
            raise ValueError("生成任务必须提供 requirement")

        if self.type == "refine" and (
            not self.instruction or self.currentSchema is None
        ):
            raise ValueError("增量修改任务必须提供 instruction 和 currentSchema")

        return self


class TaskAccepted(BaseModel):
    taskId: str
    status: TaskStatus


class SchemaTask(BaseModel):
    taskId: str
    type: TaskType
    status: TaskStatus
    message: str
    progress: int = Field(default=0, ge=0, le=100)
    repairAttempt: int = Field(default=0, ge=0, le=2)
    result: EntitySchema | None = None
    error: dict[str, Any] | None = None
    createdAt: datetime
    updatedAt: datetime
