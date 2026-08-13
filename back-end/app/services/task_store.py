import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from app.models.task_schema import SchemaTask, TaskType


_tasks: dict[str, SchemaTask] = {}
_subscribers: dict[str, set[asyncio.Queue]] = {}
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
        _subscribers[task.taskId] = set()

    return task.model_copy(deep=True)


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
        # model_copy 不会重新校验 update，转一次字典确保 SSE 数据合法。
        updated = SchemaTask.model_validate(updated.model_dump())
        _tasks[task_id] = updated
        subscribers = list(_subscribers.get(task_id, set()))
        event_data = updated.model_dump(mode="json")

    for queue in subscribers:
        queue.put_nowait(event_data)

    return updated.model_copy(deep=True)


async def subscribe_task(task_id: str) -> asyncio.Queue | None:
    queue: asyncio.Queue = asyncio.Queue()

    async with _lock:
        if task_id not in _tasks:
            return None

        _subscribers[task_id].add(queue)

    return queue


async def unsubscribe_task(task_id: str, queue: asyncio.Queue) -> None:
    async with _lock:
        subscribers = _subscribers.get(task_id)

        if subscribers is not None:
            subscribers.discard(queue)
