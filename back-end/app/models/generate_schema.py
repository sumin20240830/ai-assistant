# 定义生成接口的请求模型
from pydantic import BaseModel, ConfigDict, Field

from app.models.validate_schema import EntitySchema


class GenerateSchemaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirement: str = Field(
        min_length=5,
        max_length=2000,
        description="用户输入的实体建模需求",
    )


class RefineSchemaRequest(BaseModel):
    """基于当前 Schema 执行增量修改。"""

    model_config = ConfigDict(extra="forbid")

    instruction: str = Field(
        min_length=2,
        max_length=1000,
        description="本次增量修改指令",
    )
    currentSchema: EntitySchema
