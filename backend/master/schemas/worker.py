from typing import Literal

from pydantic import BaseModel, Field


class WorkerRegisterRequest(BaseModel):
    worker_id: str
    display_name: str | None = None
    host: str
    port: int
    total_cpu: int = Field(..., ge=1)
    total_mem: int = Field(..., ge=1)


class WorkerHeartbeatRequest(BaseModel):
    worker_id: str


class WorkerInfo(BaseModel):
    worker_id: str
    display_name: str
    host: str
    port: int
    total_cpu: int
    total_mem: int
    used_cpu: int = 0
    used_mem: int = 0
    status: Literal["online", "offline"] = "online"
    task_count: int = 0
    last_heartbeat: str
    registered_at: str
