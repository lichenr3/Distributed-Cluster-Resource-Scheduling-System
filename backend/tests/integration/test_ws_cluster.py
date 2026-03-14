from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from master.core import store
from master.main import app
from master.ws import cluster


@pytest.mark.asyncio
async def test_broadcast_cluster_state_sends_workers_and_task_summary(make_worker, make_task):
    make_worker(worker_id="worker-1", display_name="Worker One")
    make_task(task_id="task-pending", status="pending")
    make_task(task_id="task-running", status="running", worker_id="worker-1")

    with TestClient(app) as client:
        with client.websocket_connect("/ws/cluster") as websocket:
            cluster.cluster_clients.add(websocket)
            await cluster.broadcast_cluster_state()
            frame = websocket.receive_json()

    assert frame["type"] == "cluster_state"
    assert frame["data"]["workers"][0]["worker_id"] == "worker-1"
    assert frame["data"]["tasks_summary"] == {
        "pending": 1,
        "running": 1,
        "success": 0,
        "failed": 0,
        "total": 2,
    }


@pytest.mark.asyncio
async def test_broadcast_cluster_state_cleans_dead_connections():
    class DeadWebSocket:
        async def send_json(self, payload):
            raise RuntimeError("dead")

    dead = DeadWebSocket()
    cluster.cluster_clients.add(dead)  # type: ignore[arg-type]

    await cluster.broadcast_cluster_state()

    assert dead not in cluster.cluster_clients


def test_cluster_websocket_endpoint_accepts_and_cleans_up():
    with TestClient(app) as client:
        with client.websocket_connect("/ws/cluster") as websocket:
            assert len(cluster.cluster_clients) == 1
            websocket.close()

    assert len(cluster.cluster_clients) == 0
