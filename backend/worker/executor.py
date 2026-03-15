import asyncio
import logging

from worker.reporter import report_log, report_status

logger = logging.getLogger(__name__)


async def execute_task(master_url: str, worker_id: str, task_id: str, command: str) -> None:
    try:
        await report_status(master_url, task_id, worker_id, "running")

        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        line_no = 1
        assert process.stdout is not None
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            try:
                content = line.decode("utf-8").rstrip("\r\n")
            except UnicodeDecodeError:
                content = line.decode("gbk", errors="replace").rstrip("\r\n")
            await report_log(master_url, task_id, worker_id, line_no, content)
            line_no += 1

        exit_code = await process.wait()
        status = "success" if exit_code == 0 else "failed"
        await report_status(master_url, task_id, worker_id, status)
    except Exception as exc:
        logger.exception("Task execution failed for task %s: %s", task_id, exc)
        try:
            await report_status(master_url, task_id, worker_id, "failed")
        except Exception:
            logger.exception("Failed to report task failure for task %s", task_id)
