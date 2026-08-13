
from fastapi.middleware.cors import CORSMiddleware

import asyncio

from fastapi import FastAPI, HTTPException

from app.models.generate_schema import GenerateSchemaRequest, RefineSchemaRequest
from app.models.validate_schema import EntitySchema
from app.models.version_schema import (
    CreateSchemaVersionRequest,
    SchemaVersionRecord,
)
from app.models.task_schema import (
    CreateSchemaTaskRequest,
    SchemaTask,
    TaskAccepted,
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
from app.services.task_store import create_task, get_task, update_task


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


async def run_schema_task(
    task_id: str,
    request: CreateSchemaTaskRequest,
) -> None:
    async def report(
        status: str,
        message: str,
        progress: int,
        repair_attempt: int,
    ) -> None:
        await update_task(
            task_id,
            status=status,
            message=message,
            progress=min(progress, 95),
            repairAttempt=repair_attempt,
        )

    try:
        if request.type == "generate":
            if not request.requirement:
                raise ValueError("生成任务缺少 requirement")

            result = await generate_entity_schema(
                request.requirement,
                progress_callback=report,
            )
        else:
            if not request.instruction or request.currentSchema is None:
                raise ValueError("增量修改任务缺少 instruction 或 currentSchema")

            result = await refine_entity_schema(
                current_schema=request.currentSchema,
                instruction=request.instruction,
                progress_callback=report,
            )

        await update_task(
            task_id,
            status="succeeded",
            message="Schema 生成成功",
            progress=100,
            result=result,
        )

    except LLMOutputValidationError as error:
        await update_task(
            task_id,
            status="failed",
            message="模型结果经过两次自动修复后仍未通过校验",
            progress=100,
            repairAttempt=error.repair_attempts,
            error={
                "code": "LLM_OUTPUT_VALIDATION_FAILED",
                "errors": error.errors,
            },
        )

    except Exception as error:
        await update_task(
            task_id,
            status="failed",
            message=str(error),
            progress=100,
            error={
                "code": "SCHEMA_TASK_FAILED",
                "message": str(error),
            },
        )


@app.post(
    "/api/schema-tasks",
    response_model=TaskAccepted,
    status_code=202,
    tags=["schema-task"],
)
async def submit_schema_task(
    request: CreateSchemaTaskRequest,
) -> TaskAccepted:
    if request.type == "generate" and not request.requirement:
        raise HTTPException(status_code=422, detail="生成任务必须提供 requirement")

    if request.type == "refine" and (
        not request.instruction or request.currentSchema is None
    ):
        raise HTTPException(
            status_code=422,
            detail="增量修改任务必须提供 instruction 和 currentSchema",
        )

    task = await create_task(request.type)
    asyncio.create_task(run_schema_task(task.taskId, request))

    return TaskAccepted(taskId=task.taskId, status=task.status)


@app.get(
    "/api/schema-tasks/{task_id}",
    response_model=SchemaTask,
    tags=["schema-task"],
)
async def get_schema_task(task_id: str) -> SchemaTask:
    task = await get_task(task_id)

    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")

    return task

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
