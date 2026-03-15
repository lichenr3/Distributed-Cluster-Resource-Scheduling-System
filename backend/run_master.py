import argparse
import os

import uvicorn


class RunMasterArgs(argparse.Namespace):
    host: str = "0.0.0.0"
    port: int = 8000
    heartbeat_interval: int = 5
    heartbeat_timeout: int = 15
    broadcast_interval: int = 1
    log_buffer_size: int = 1000


def parse_args() -> RunMasterArgs:
    parser = argparse.ArgumentParser(description="Run Mini Scheduler Master")
    _ = parser.add_argument("--host", type=str, default="0.0.0.0")
    _ = parser.add_argument("--port", type=int, default=8000)
    _ = parser.add_argument("--heartbeat-interval", type=int, default=5)
    _ = parser.add_argument("--heartbeat-timeout", type=int, default=15)
    _ = parser.add_argument("--broadcast-interval", type=int, default=1)
    _ = parser.add_argument("--log-buffer-size", type=int, default=1000)
    return parser.parse_args(namespace=RunMasterArgs())


if __name__ == "__main__":
    args = parse_args()

    os.environ["MASTER_HOST"] = args.host
    os.environ["MASTER_PORT"] = str(args.port)
    os.environ["MASTER_HEARTBEAT_INTERVAL"] = str(args.heartbeat_interval)
    os.environ["MASTER_HEARTBEAT_TIMEOUT"] = str(args.heartbeat_timeout)
    os.environ["MASTER_CLUSTER_BROADCAST_INTERVAL"] = str(args.broadcast_interval)
    os.environ["MASTER_LOG_BUFFER_SIZE"] = str(args.log_buffer_size)

    from master.main import app

    uvicorn.run(app, host=args.host, port=args.port, reload=False)
