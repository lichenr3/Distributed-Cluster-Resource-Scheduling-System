from typing import Annotated

from fastapi import APIRouter, Depends

from master.core.dependencies import get_worker_service
from master.schemas.response import ApiResponse
from master.services.worker_service import WorkerService

router = APIRouter(tags=["workers"])


@router.get("/api/workers")
async def list_workers(
    worker_service: Annotated[WorkerService, Depends(get_worker_service)],
):
    result = worker_service.list_workers()
    return ApiResponse(data=result)
