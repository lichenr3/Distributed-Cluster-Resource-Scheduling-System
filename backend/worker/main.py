import asyncio
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from uuid import uuid4

from fastapi import FastAPI

from worker.config import HEARTBEAT_INTERVAL, MASTER_URL
from worker.executor import execute_task
from worker.reporter import register, start_heartbeat_loop
from worker.schemas import ExecuteRequest


@dataclass
class WorkerRuntime:
    host: str
    port: int
    total_cpu: int
    total_mem: int
    worker_id: str
    master_url: str
    heartbeat_interval: int


class WorkerArgs:
    port: int = 0
    cpu: int = 0
    mem: int = 0
    worker_id: str | None = None
    master_url: str = MASTER_URL
    host: str = "0.0.0.0"


def load_runtime_from_env() -> WorkerRuntime:
    port = int(os.getenv("WORKER_PORT", "8001"))
    total_cpu = int(os.getenv("WORKER_CPU", "1"))
    total_mem = int(os.getenv("WORKER_MEM", "1"))
    host = os.getenv("WORKER_HOST", "0.0.0.0")
    worker_id = os.getenv("WORKER_ID", f"worker-{port}-{uuid4().hex[:8]}")
    master_url = os.getenv("MASTER_URL", MASTER_URL)
    heartbeat_interval = int(os.getenv("WORKER_HEARTBEAT_INTERVAL", str(HEARTBEAT_INTERVAL)))

    return WorkerRuntime(
        host=host,
        port=port,
        total_cpu=total_cpu,
        total_mem=total_mem,
        worker_id=worker_id,
        master_url=master_url,
        heartbeat_interval=heartbeat_interval,
    )


def create_app(runtime: WorkerRuntime) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        del app
        await register(
            runtime.master_url,
            runtime.worker_id,
            runtime.host,
            runtime.port,
            runtime.total_cpu,
            runtime.total_mem,
        )

        heartbeat_task = asyncio.create_task(
            start_heartbeat_loop(
                runtime.master_url,
                runtime.worker_id,
                runtime.host,
                runtime.port,
                runtime.total_cpu,
                runtime.total_mem,
                runtime.heartbeat_interval,
            ),
            name="worker_heartbeat_loop",
        )

        try:
            yield
        finally:
            cancelled = heartbeat_task.cancel()
            _ = cancelled
            gathered = await asyncio.gather(heartbeat_task, return_exceptions=True)
            _ = gathered

    app = FastAPI(title="Mini Scheduler Worker", lifespan=lifespan)

    @app.post("/execute")
    async def execute_endpoint(req: ExecuteRequest) -> dict[str, bool]:
        _ = asyncio.create_task(
            execute_task(
                runtime.master_url,
                runtime.worker_id,
                req.task_id,
                req.command,
            )
        )
        return {"accepted": True}

    _ = execute_endpoint

    return app


def parse_cli_args() -> tuple[int, int, int, str | None, str, str]:
    import argparse

    parser = argparse.ArgumentParser(description="Mini Scheduler Worker")
    _ = parser.add_argument("--port", type=int, required=True)
    _ = parser.add_argument("--cpu", type=int, required=True)
    _ = parser.add_argument("--mem", type=int, required=True)
    _ = parser.add_argument("--worker-id", type=str, default=None)
    _ = parser.add_argument("--master-url", type=str, default=MASTER_URL)
    _ = parser.add_argument("--host", type=str, default="0.0.0.0")
    parsed = parser.parse_args(namespace=WorkerArgs())
    port = parsed.port
    cpu = parsed.cpu
    mem = parsed.mem
    worker_id = parsed.worker_id
    master_url = parsed.master_url
    host = parsed.host
    return port, cpu, mem, worker_id, master_url, host


runtime = load_runtime_from_env()
app = create_app(runtime)


if __name__ == "__main__":
    import uvicorn

    port, cpu, mem, worker_id, master_url, host = parse_cli_args()
    os.environ["WORKER_PORT"] = str(port)
    os.environ["WORKER_CPU"] = str(cpu)
    os.environ["WORKER_MEM"] = str(mem)
    os.environ["WORKER_HOST"] = host
    os.environ["MASTER_URL"] = master_url
    os.environ["WORKER_ID"] = worker_id or f"worker-{port}-{uuid4().hex[:8]}"

    runtime_from_cli = load_runtime_from_env()
    cli_app = create_app(runtime_from_cli)
    uvicorn.run(cli_app, host=runtime_from_cli.host, port=runtime_from_cli.port, reload=False)
