from typing import Literal

from pydantic import BaseModel


class ExecuteRequest(BaseModel):
    task_id: str
    command: str
    cpu_required: int
    mem_required: int


class RegisterRequest(BaseModel):
    worker_id: str
    host: str
    port: int
    total_cpu: int
    total_mem: int


class HeartbeatRequest(BaseModel):
    worker_id: str


class StatusReport(BaseModel):
    worker_id: str
    status: Literal["running", "success", "failed"]


class LogReport(BaseModel):
    worker_id: str
    line_no: int
    content: str
