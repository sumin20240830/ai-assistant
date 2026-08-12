# json 的校验规则
# 大模型生成的 JSON 不一定可靠，可以在返回给前端之前再验证一次：
# 既能对前端进行校验，也能对ai生成数据进行校验
import re
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class ConstraintSchema(BaseModel):
    """字段约束"""

    model_config = ConfigDict(extra="forbid")

    pattern: str | None = None
    patternMessage: str | None = None

    @field_validator("pattern")
    @classmethod
    def validate_pattern(cls, value: str | None) -> str | None:
        if value is None:
            return value

        try:
            re.compile(value)
        except re.error as error:
            raise ValueError(f"不是合法的正则表达式：{error}") from error

        return value


class EnumOptionSchema(BaseModel):
    """枚举选项"""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1)
    value: str = Field(min_length=1)


class FieldSchema(BaseModel):
    """实体字段"""

    model_config = ConfigDict(extra="forbid")

    fieldName: str = Field(min_length=1, max_length=50)
    fieldCode: str = Field(
        min_length=1,
        max_length=50,
        pattern=r"^[a-zA-Z][a-zA-Z0-9_]*$",
    )
    dataType: Literal[
        "string",
        "number",
        "integer",
        "enum",
        "date",
        "datetime",
        "boolean",
    ]
    required: bool = False
    constraints: ConstraintSchema | None = None
    enumOptions: list[EnumOptionSchema] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_enum_options(self):
        if self.dataType == "enum" and not self.enumOptions:
            raise ValueError("枚举类型字段必须提供 enumOptions")

        if self.dataType != "enum" and self.enumOptions:
            raise ValueError("只有枚举类型字段可以提供 enumOptions")

        return self


class EntitySchema(BaseModel):
    """实体 Schema 字段校验"""

    model_config = ConfigDict(extra="forbid")

    entityName: str = Field(min_length=1, max_length=50)
    entityCode: str = Field(
        min_length=1,
        max_length=50,
        pattern=r"^[a-zA-Z][a-zA-Z0-9_]*$",
    )
    version: int = Field(default=1, ge=1)
    fields: list[FieldSchema] = Field(min_length=1)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_field_codes(self):
        field_codes = [field.fieldCode for field in self.fields]

        if len(field_codes) != len(set(field_codes)):
            raise ValueError("fields 中存在重复的 fieldCode")

        return self
