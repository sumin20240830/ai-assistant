
from fastapi.middleware.cors import CORSMiddleware

from fastapi import FastAPI, HTTPException

from app.models.generate_schema import GenerateSchemaRequest, RefineSchemaRequest
from app.models.validate_schema import EntitySchema
from app.models.version_schema import (
    CreateSchemaVersionRequest,
    SchemaVersionRecord,
)
from app.services.llm_service import (
    LLMOutputValidationError,
    LLMServiceError,
    generate_entity_schema,
    refine_entity_schema,
)
from app.services.version_store import (
    create_schema_version,
    list_schema_versions,
)


app = FastAPI(
    title="AI assistant API",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok"}


@app.post(
    "/api/schemas/validate",
    response_model=EntitySchema,
    tags=["schema"],
)
async def validate_schema(schema: EntitySchema) -> EntitySchema:
    return schema

# 保存草稿
@app.post(
    "/api/schemas/save",
    response_model=EntitySchema,
    tags=["schema"],
)
async def save_schema(schema: EntitySchema) -> EntitySchema:
    return schema


@app.post(
    "/api/schema-versions",
    response_model=SchemaVersionRecord,
    tags=["schema-version"],
)
async def create_version(
    request: CreateSchemaVersionRequest,
) -> SchemaVersionRecord:
    return create_schema_version(request)


@app.get(
    "/api/schema-versions/{session_id}",
    response_model=list[SchemaVersionRecord],
    tags=["schema-version"],
)
async def get_versions(session_id: str) -> list[SchemaVersionRecord]:
    return list_schema_versions(session_id)

#

# 生成schema
@app.post(
    "/api/schemas/generate",
    response_model=EntitySchema,
    tags=["schema"],
)
async def generate_schema(
    request: GenerateSchemaRequest,
) -> EntitySchema:
    try:
        return await generate_entity_schema(request.requirement)

    except LLMOutputValidationError as error:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "LLM_OUTPUT_VALIDATION_FAILED",
                "message": "模型结果经过两次自动修复后仍未通过校验",
                "repairAttempts": error.repair_attempts,
                "errors": error.errors,
            },
        ) from error

    except LLMServiceError as error:
        raise HTTPException(
            status_code=502,
            detail=str(error),
        ) from error


@app.post(
    "/api/schemas/refine",
    response_model=EntitySchema,
    tags=["schema"],
)
async def refine_schema(
    request: RefineSchemaRequest,
) -> EntitySchema:
    try:
        return await refine_entity_schema(
            current_schema=request.currentSchema,
            instruction=request.instruction,
        )

    except LLMOutputValidationError as error:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "LLM_OUTPUT_VALIDATION_FAILED",
                "message": "增量修改经过两次自动修复后仍未通过校验",
                "repairAttempts": error.repair_attempts,
                "errors": error.errors,
            },
        ) from error

    except LLMServiceError as error:
        raise HTTPException(
            status_code=502,
            detail=str(error),
        ) from error
