import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from app.models.task_schema import SchemaTask, TaskType


_tasks: dict[str, SchemaTask] = {}
_lock = asyncio.Lock()


def now() -> datetime:
    return datetime.now(timezone.utc)


async def create_task(task_type: TaskType) -> SchemaTask:
    timestamp = now()
    task = SchemaTask(
        taskId=str(uuid4()),
        type=task_type,
        status="queued",
        message="任务已提交，等待处理",
        progress=0,
        createdAt=timestamp,
        updatedAt=timestamp,
    )

    async with _lock:
        _tasks[task.taskId] = task

    return task


async def get_task(task_id: str) -> SchemaTask | None:
    async with _lock:
        task = _tasks.get(task_id)
        return task.model_copy(deep=True) if task else None


async def update_task(task_id: str, **changes) -> SchemaTask | None:
    async with _lock:
        task = _tasks.get(task_id)

        if task is None:
            return None

        updated = task.model_copy(
            update={
                **changes,
                "updatedAt": now(),
            },
            deep=True,
        )
        _tasks[task_id] = updated
        return updated.model_copy(deep=True)
