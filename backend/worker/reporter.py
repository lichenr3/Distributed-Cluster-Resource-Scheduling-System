import asyncio
import logging
from typing import Literal

import httpx
from pydantic import BaseModel

from worker.schemas import HeartbeatRequest, LogReport, RegisterRequest, StatusReport

logger = logging.getLogger(__name__)


class HeartbeatData(BaseModel):
    exist: bool


class HeartbeatApiResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: HeartbeatData | None = None


async def register(
    master_url: str,
    worker_id: str,
    host: str,
    port: int,
    total_cpu: int,
    total_mem: int,
) -> None:
    payload = RegisterRequest(
        worker_id=worker_id,
        host=host,
        port=port,
        total_cpu=total_cpu,
        total_mem=total_mem,
    ).model_dump()
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(f"{master_url}/internal/register", json=payload)
        _ = response.raise_for_status()


async def send_heartbeat(master_url: str, worker_id: str) -> bool:
    payload = HeartbeatRequest(worker_id=worker_id).model_dump()
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(f"{master_url}/internal/heartbeat", json=payload)
        _ = response.raise_for_status()
        parsed = HeartbeatApiResponse.model_validate_json(response.text)
        if parsed.data is None:
            return False
        return parsed.data.exist


async def report_status(
    master_url: str,
    task_id: str,
    worker_id: str,
    status: Literal["running", "success", "failed"],
) -> None:
    payload = StatusReport(worker_id=worker_id, status=status).model_dump()
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(
            f"{master_url}/internal/task/{task_id}/status", json=payload
        )
        _ = response.raise_for_status()


async def report_log(
    master_url: str,
    task_id: str,
    worker_id: str,
    line_no: int,
    content: str,
) -> None:
    payload = LogReport(worker_id=worker_id, line_no=line_no, content=content).model_dump()
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(
            f"{master_url}/internal/task/{task_id}/log", json=payload
        )
        _ = response.raise_for_status()


async def start_heartbeat_loop(
    master_url: str,
    worker_id: str,
    host: str,
    port: int,
    total_cpu: int,
    total_mem: int,
    interval: int,
) -> None:
    while True:
        try:
            exists = await send_heartbeat(master_url, worker_id)
            if not exists:
                await register(
                    master_url,
                    worker_id,
                    host,
                    port,
                    total_cpu,
                    total_mem,
                )
        except httpx.HTTPError as exc:
            logger.warning("Heartbeat loop error for worker %s: %s", worker_id, exc)
        except Exception as exc:
            logger.exception("Unexpected heartbeat loop error for worker %s: %s", worker_id, exc)
        await asyncio.sleep(interval)
