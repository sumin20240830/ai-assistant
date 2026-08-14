
import asyncio
import json

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.models.generate_schema import GenerateSchemaRequest, RefineSchemaRequest
from app.models.knowledge_schema import (
    KnowledgeChunkListResponse,
    KnowledgeIndexSummary,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
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
from app.services.knowledge_service import (
    KnowledgeBaseError,
    get_knowledge_index_summary,
    list_knowledge_chunks,
    reindex_knowledge_base,
    search_knowledge,
)
from app.services.version_store import (
    create_schema_version,
    list_schema_versions,
)
from app.services.task_store import (
    create_task,
    get_task,
    subscribe_task,
    unsubscribe_task,
    update_task,
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


@app.get(
    "/api/knowledge/status",
    response_model=KnowledgeIndexSummary,
    tags=["knowledge"],
)
async def get_knowledge_status() -> KnowledgeIndexSummary:
    try:
        return await asyncio.to_thread(get_knowledge_index_summary)
    except KnowledgeBaseError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.post(
    "/api/knowledge/reindex",
    response_model=KnowledgeIndexSummary,
    tags=["knowledge"],
)
async def reindex_knowledge() -> KnowledgeIndexSummary:
    try:
        return await asyncio.to_thread(reindex_knowledge_base)
    except KnowledgeBaseError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.get(
    "/api/knowledge/chunks",
    response_model=KnowledgeChunkListResponse,
    tags=["knowledge"],
)
async def get_knowledge_chunks(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> KnowledgeChunkListResponse:
    try:
        items, total = await asyncio.to_thread(
            list_knowledge_chunks,
            offset,
            limit,
        )
        return KnowledgeChunkListResponse(items=items, total=total)
    except KnowledgeBaseError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.post(
    "/api/knowledge/search",
    response_model=KnowledgeSearchResponse,
    tags=["knowledge"],
)
async def search_knowledge_base(
    request: KnowledgeSearchRequest,
) -> KnowledgeSearchResponse:
    try:
        items = await asyncio.to_thread(
            search_knowledge,
            request.query,
            request.topK,
        )
        return KnowledgeSearchResponse(
            query=request.query,
            items=items,
            total=len(items),
        )
    except KnowledgeBaseError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


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

# SSE 通过taskId 确认前端查询的是哪个任务，避免前端在任务完成后继续订阅旧的taskId。
@app.get(
    "/api/schema-tasks/{task_id}/events",
    tags=["schema-task"],
)
async def stream_schema_task(
    task_id: str,
    request: Request,
) -> StreamingResponse:
    queue = await subscribe_task(task_id)
    initial_task = await get_task(task_id)

    if queue is None or initial_task is None:
        raise HTTPException(status_code=404, detail="任务不存在")

    async def event_generator():
        try:
            # 连接后先推送当前快照，避免任务创建到订阅之间的事件丢失。
            yield format_task_event(initial_task.model_dump(mode="json"))

            if initial_task.status in {"succeeded", "failed"}:
                return

            while True:
                if await request.is_disconnected():
                    return

                try:
                    event_data = await asyncio.wait_for(
                        queue.get(),
                        timeout=15,
                    )
                except TimeoutError:
                    # SSE 注释行作为心跳，不会触发 EventSource message。
                    yield ": keep-alive\n\n"
                    continue

                yield format_task_event(event_data)

                if event_data["status"] in {"succeeded", "failed"}:
                    return
        finally:
            await unsubscribe_task(task_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def format_task_event(task: dict) -> str:
    payload = json.dumps(task, ensure_ascii=False)
    return f"event: task\ndata: {payload}\n\n"

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
