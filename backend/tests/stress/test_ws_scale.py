from __future__ import annotations

import asyncio
import time

import pytest

from master.ws import cluster, logs


class DummyWebSocket:
    def __init__(self, fail: bool = False) -> None:
        self.fail: bool = fail
        self.messages: list[dict[str, object]] = []

    async def send_json(self, payload: dict[str, object]) -> None:
        if self.fail:
            raise RuntimeError("dead connection")
        self.messages.append(payload)


@pytest.mark.asyncio
@pytest.mark.stress
async def test_cluster_broadcast_scales_to_many_clients(make_worker, make_task):
    make_worker(worker_id="worker-1", display_name="Worker One")
    make_task(task_id="task-1", status="pending")
    clients = [DummyWebSocket() for _ in range(250)]
    cluster.cluster_clients.update(clients)  # pyright: ignore[reportArgumentType]

    started = time.perf_counter()
    await cluster.broadcast_cluster_state()
    elapsed = time.perf_counter() - started

    assert all(client.messages for client in clients)
    assert elapsed < 1.0
    assert len(cluster.cluster_clients) == 250
    cluster.cluster_clients.clear()


@pytest.mark.asyncio
@pytest.mark.stress
async def test_log_broadcast_scales_and_cleans_dead_subscribers(make_task):
    task = make_task(task_id="task-1")
    alive = [DummyWebSocket() for _ in range(100)]
    dead = [DummyWebSocket(fail=True) for _ in range(5)]
    logs.log_subscribers[task["task_id"]] = set([*alive, *dead])  # pyright: ignore[reportArgumentType]

    await logs.broadcast_log(
        task["task_id"],
        {"line_no": 1, "content": "hello", "timestamp": "2026-03-14T00:00:00+00:00"},
    )

    assert all(client.messages for client in alive)
    assert logs.log_subscribers[task["task_id"]] == set(alive)


@pytest.mark.asyncio
@pytest.mark.stress
async def test_mixed_cluster_and_log_connections_do_not_block(make_task):
    task = make_task(task_id="task-mixed")
    cluster_clients = [DummyWebSocket() for _ in range(150)]
    log_clients = [DummyWebSocket() for _ in range(80)]
    cluster.cluster_clients.update(cluster_clients)  # pyright: ignore[reportArgumentType]
    logs.log_subscribers[task["task_id"]] = set(log_clients)  # pyright: ignore[reportArgumentType]

    started = time.perf_counter()
    _ = await asyncio.gather(
        cluster.broadcast_cluster_state(),
        logs.broadcast_log(
            task["task_id"],
            {"line_no": 1, "content": "live", "timestamp": "2026-03-14T00:00:00+00:00"},
        ),
    )
    elapsed = time.perf_counter() - started

    assert elapsed < 1.0
    assert all(client.messages for client in cluster_clients)
    assert all(client.messages for client in log_clients)
    cluster.cluster_clients.clear()
    logs.log_subscribers.clear()
