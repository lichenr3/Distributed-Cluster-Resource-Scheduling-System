from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, HTTPException, Query

from master.core.dependencies import get_task_service
from master.schemas.response import ApiResponse
from master.schemas.task import TaskSubmitRequest
from master.services.task_service import TaskService

router = APIRouter(tags=["tasks"])


@router.post("/api/tasks")
async def create_task(
    req: TaskSubmitRequest,
    task_service: Annotated[TaskService, Depends(get_task_service)],
):
    task_info = await task_service.create_and_schedule(req)
    return ApiResponse(data=task_info)


@router.get("/api/tasks")
async def list_tasks(
    task_service: Annotated[TaskService, Depends(get_task_service)],
    status: Annotated[str | None, Query()] = None,
):
    normalized_status: Literal["pending", "running", "success", "failed"] | None = None
    if status is not None and status not in {"pending", "running", "success", "failed"}:
        raise HTTPException(status_code=400, detail="Invalid status filter")
    if status is not None:
        normalized_status = cast(
            Literal["pending", "running", "success", "failed"],
            status,
        )

    result = task_service.list_tasks(status_filter=normalized_status)
    return ApiResponse(data=result)


@router.get("/api/tasks/{task_id}")
async def get_task(
    task_id: str,
    task_service: Annotated[TaskService, Depends(get_task_service)],
):
    task_info = task_service.get_task(task_id)
    if task_info is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return ApiResponse(data=task_info)
