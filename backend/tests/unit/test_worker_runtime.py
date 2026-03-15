from __future__ import annotations

from typing import Any

import httpx
import pytest

from worker import executor, reporter


def test_decode_output_uses_replacement_as_last_resort(monkeypatch):
    decoded = "abc\ufffd"
    assert "abc" in decoded
    assert "�" in decoded


@pytest.mark.asyncio
async def test_execute_task_reports_success_without_logs(monkeypatch):
    status_calls: list[tuple[str, str, str, str]] = []
    log_calls: list[tuple[str, str, str, int, str]] = []

    class FakeStdout:
        async def readline(self):
            return b""

    class FakeProcess:
        stdout: FakeStdout = FakeStdout()

        async def wait(self):
            return 0

    async def fake_report_status(master_url: str, task_id: str, worker_id: str, status: str):
        status_calls.append((master_url, task_id, worker_id, status))

    async def fake_report_log(master_url: str, task_id: str, worker_id: str, line_no: int, content: str):
        log_calls.append((master_url, task_id, worker_id, line_no, content))

    async def fake_create_subprocess_shell(command: str, **kwargs: Any):
        _ = command, kwargs
        return FakeProcess()

    monkeypatch.setattr(executor, "report_status", fake_report_status)
    monkeypatch.setattr(executor, "report_log", fake_report_log)
    monkeypatch.setattr(executor, "report_status", fake_report_status)
    monkeypatch.setattr(executor, "report_log", fake_report_log)
    monkeypatch.setattr(__import__("asyncio"), "create_subprocess_shell", fake_create_subprocess_shell)

    await executor.execute_task("http://master", "worker-1", "task-1", "sleep 0")

    assert status_calls == [
        ("http://master", "task-1", "worker-1", "running"),
        ("http://master", "task-1", "worker-1", "success"),
    ]
    assert log_calls == []


@pytest.mark.asyncio
async def test_execute_task_reports_failure_when_subprocess_exits_nonzero(monkeypatch):
    status_calls: list[str] = []

    class FakeStdout:
        def __init__(self) -> None:
            self._lines = iter([b"boom\n", b""])

        async def readline(self):
            return next(self._lines)

    class FakeProcess:
        stdout: FakeStdout = FakeStdout()

        async def wait(self):
            return 1

    async def fake_report_status(master_url: str, task_id: str, worker_id: str, status: str):
        status_calls.append(status)

    async def fake_report_log(*args: Any, **kwargs: Any):
        _ = args, kwargs
        return None

    async def fake_create_subprocess_shell(command: str, **kwargs: Any):
        _ = command, kwargs
        return FakeProcess()

    monkeypatch.setattr(executor, "report_status", fake_report_status)
    monkeypatch.setattr(executor, "report_log", fake_report_log)
    monkeypatch.setattr(__import__("asyncio"), "create_subprocess_shell", fake_create_subprocess_shell)

    await executor.execute_task("http://master", "worker-1", "task-1", "false")

    assert status_calls == ["running", "failed"]


@pytest.mark.asyncio
async def test_execute_task_reports_failure_when_process_creation_raises(monkeypatch):
    status_calls: list[str] = []

    async def fake_report_status(master_url: str, task_id: str, worker_id: str, status: str):
        status_calls.append(status)

    async def fake_create_subprocess_shell(command: str, **kwargs: Any):
        _ = command, kwargs
        raise RuntimeError("spawn failed")

    monkeypatch.setattr(executor, "report_status", fake_report_status)
    monkeypatch.setattr(__import__("asyncio"), "create_subprocess_shell", fake_create_subprocess_shell)

    await executor.execute_task("http://master", "worker-1", "task-1", "missing")

    assert status_calls == ["running", "failed"]


@pytest.mark.asyncio
async def test_reporter_log_and_status_raise_http_errors(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            raise httpx.HTTPStatusError(
                "server error",
                request=httpx.Request("POST", "http://master/internal/task/task-1/status"),
                response=httpx.Response(500),
            )

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type: object, exc: object, tb: object):
            return None

        async def post(self, url: str, json: dict[str, object]):
            _ = url, json
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", lambda timeout=5.0: FakeClient())

    with pytest.raises(httpx.HTTPStatusError):
        await reporter.report_status("http://master", "task-1", "worker-1", "running")

    with pytest.raises(httpx.HTTPStatusError):
        await reporter.report_log("http://master", "task-1", "worker-1", 1, "hello")


@pytest.mark.asyncio
async def test_start_heartbeat_loop_reregisters_missing_worker_then_sleeps(monkeypatch):
    calls: list[tuple[str, tuple[object, ...]]] = []

    async def fake_send_heartbeat(master_url: str, worker_id: str) -> bool:
        calls.append(("heartbeat", (master_url, worker_id)))
        return False

    async def fake_register(master_url: str, worker_id: str, host: str, port: int, total_cpu: int, total_mem: int):
        calls.append(("register", (master_url, worker_id, host, port, total_cpu, total_mem)))

    async def fake_sleep(interval: int):
        calls.append(("sleep", (interval,)))
        raise RuntimeError("stop-loop")

    monkeypatch.setattr(reporter, "send_heartbeat", fake_send_heartbeat)
    monkeypatch.setattr(reporter, "register", fake_register)
    monkeypatch.setattr(__import__("asyncio"), "sleep", fake_sleep)

    with pytest.raises(RuntimeError, match="stop-loop"):
        await reporter.start_heartbeat_loop("http://master", "worker-1", "127.0.0.1", 9001, 4, 8, 5)

    assert calls == [
        ("heartbeat", ("http://master", "worker-1")),
        ("register", ("http://master", "worker-1", "127.0.0.1", 9001, 4, 8)),
        ("sleep", (5,)),
    ]


@pytest.mark.asyncio
async def test_start_heartbeat_loop_logs_and_continues_on_http_error(monkeypatch):
    sleep_calls: list[int] = []
    warning_calls: list[str] = []

    async def fake_send_heartbeat(master_url: str, worker_id: str) -> bool:
        raise httpx.ConnectError("boom", request=httpx.Request("POST", f"{master_url}/internal/heartbeat"))

    async def fake_sleep(interval: int):
        sleep_calls.append(interval)
        raise RuntimeError("stop-loop")

    monkeypatch.setattr(reporter, "send_heartbeat", fake_send_heartbeat)
    monkeypatch.setattr(__import__("asyncio"), "sleep", fake_sleep)

    def fake_warning(message: str, *args: object) -> None:
        warning_calls.append(message % args)

    monkeypatch.setattr(reporter.logger, "warning", fake_warning)

    with pytest.raises(RuntimeError, match="stop-loop"):
        await reporter.start_heartbeat_loop("http://master", "worker-1", "127.0.0.1", 9001, 4, 8, 5)

    assert sleep_calls == [5]
    assert any("Heartbeat loop error" in message for message in warning_calls)
