import argparse
import os
from uuid import uuid4

import uvicorn

from worker.config import MASTER_URL


class RunWorkerArgs(argparse.Namespace):
    port: int = 0
    cpu: int = 0
    mem: int = 0
    worker_id: str | None = None
    master_url: str = MASTER_URL
    host: str = "0.0.0.0"


def parse_args() -> tuple[int, int, int, str | None, str, str]:
    parser = argparse.ArgumentParser(description="Run Mini Scheduler Worker")
    _ = parser.add_argument("--port", type=int, required=True)
    _ = parser.add_argument("--cpu", type=int, required=True)
    _ = parser.add_argument("--mem", type=int, required=True)
    _ = parser.add_argument("--worker-id", type=str, default=None)
    _ = parser.add_argument("--master-url", type=str, default=MASTER_URL)
    _ = parser.add_argument("--host", type=str, default="0.0.0.0")

    parsed = parser.parse_args(namespace=RunWorkerArgs())
    port = parsed.port
    cpu = parsed.cpu
    mem = parsed.mem
    worker_id = parsed.worker_id
    master_url = parsed.master_url
    host = parsed.host
    return port, cpu, mem, worker_id, master_url, host


if __name__ == "__main__":
    port, cpu, mem, worker_id, master_url, host = parse_args()

    os.environ["WORKER_PORT"] = str(port)
    os.environ["WORKER_CPU"] = str(cpu)
    os.environ["WORKER_MEM"] = str(mem)
    os.environ["WORKER_HOST"] = host
    os.environ["MASTER_URL"] = master_url
    os.environ["WORKER_ID"] = worker_id or f"worker-{port}-{uuid4().hex[:8]}"

    from worker.main import app

    uvicorn.run(app, host=host, port=port, reload=False)
