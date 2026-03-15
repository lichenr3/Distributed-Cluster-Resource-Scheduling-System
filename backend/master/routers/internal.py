from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from master.core.dependencies import get_task_service, get_worker_service
from master.schemas.response import ApiResponse
from master.schemas.task import TaskLogReport, TaskStatusReport
from master.schemas.worker import WorkerHeartbeatRequest, WorkerRegisterRequest
from master.services.task_service import TaskService
from master.services.worker_service import WorkerService

router = APIRouter(tags=["internal"])

_WILDCARD_HOSTS = {"0.0.0.0", "::", "[::]", ""}


@router.post("/internal/register")
async def register_worker(
    req: WorkerRegisterRequest,
    request: Request,
    worker_service: Annotated[WorkerService, Depends(get_worker_service)],
):
    if req.host in _WILDCARD_HOSTS and request.client:
        req = req.model_copy(update={"host": request.client.host})
    data = await worker_service.register(req)
    return ApiResponse(data=data)


@router.post("/internal/heartbeat")
async def worker_heartbeat(
    req: WorkerHeartbeatRequest,
    worker_service: Annotated[WorkerService, Depends(get_worker_service)],
):
    data = await worker_service.heartbeat(req)
    return ApiResponse(data=data)


@router.post("/internal/task/{task_id}/status")
async def report_task_status(
    task_id: str,
    report: TaskStatusReport,
    task_service: Annotated[TaskService, Depends(get_task_service)],
):
    try:
        data = await task_service.update_status(task_id, report)
    except KeyError:
        raise HTTPException(status_code=404, detail="Task not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ApiResponse(data=data)


@router.post("/internal/task/{task_id}/log")
async def report_task_log(
    task_id: str,
    report: TaskLogReport,
    task_service: Annotated[TaskService, Depends(get_task_service)],
):
    try:
        data = await task_service.append_log(task_id, report)
    except KeyError:
        raise HTTPException(status_code=404, detail="Task not found")
    return ApiResponse(data=data)
