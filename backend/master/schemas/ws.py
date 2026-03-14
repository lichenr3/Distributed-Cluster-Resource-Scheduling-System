from typing import Literal

from pydantic import BaseModel


class ClusterStateData(BaseModel):
    workers: list[dict[str, object]]
    tasks_summary: dict[str, int]


class ClusterStateFrame(BaseModel):
    type: Literal["cluster_state"] = "cluster_state"
    timestamp: str
    data: ClusterStateData


class LogConnectedFrame(BaseModel):
    type: Literal["connected"] = "connected"
    task_id: str
    timestamp: str


class LogHistoryFrame(BaseModel):
    type: Literal["history"] = "history"
    task_id: str
    lines: list[dict[str, int | str]]


class LogLineFrame(BaseModel):
    type: Literal["log"] = "log"
    task_id: str
    line_no: int
    content: str
    timestamp: str


class TaskCompletedFrame(BaseModel):
    type: Literal["task_completed"] = "task_completed"
    task_id: str
    status: Literal["success", "failed"]
    exit_code: int | None = None
    timestamp: str
