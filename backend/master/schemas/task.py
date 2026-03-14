from typing import Literal

from pydantic import BaseModel, Field


class TaskSubmitRequest(BaseModel):
    command: str = Field(..., min_length=1, max_length=1024)
    cpu_required: int = Field(..., ge=1)
    mem_required: int = Field(..., ge=1)


class TaskInfo(BaseModel):
    task_id: str
    command: str
    cpu_required: int
    mem_required: int
    status: Literal["pending", "running", "success", "failed"]
    worker_id: str | None = None
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None


class TaskStatusReport(BaseModel):
    worker_id: str
    status: Literal["running", "success", "failed"]


class TaskLogReport(BaseModel):
    worker_id: str
    line_no: int
    content: str
