"""Supervise a bounded, disposable import worker for each API instance."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


async def _monitor_worker(process, timeout_sec: float) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_sec
    while line := await asyncio.wait_for(process.stdout.readline(), timeout=max(0, deadline - loop.time())):
        if line == b"tick\n":
            deadline = loop.time() + timeout_sec
    await process.wait()


async def run_ingest_worker(stop: asyncio.Event, *, timeout_sec: float = 300) -> None:
    while not stop.is_set():
        process = None
        stop_wait = None
        monitor = None
        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "app.services.rag_ingest_worker", "--loop",
                "--parent-pid", str(os.getpid()),
                cwd=str(Path(__file__).resolve().parents[2]),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
            )
            stop_wait = asyncio.create_task(stop.wait())
            monitor = asyncio.create_task(_monitor_worker(process, timeout_sec))
            done, _ = await asyncio.wait(
                {stop_wait, monitor},
                return_when=asyncio.FIRST_COMPLETED,
            )
            timed_out = monitor in done and isinstance(monitor.exception(), TimeoutError)
            if monitor not in done or timed_out:
                if not stop.is_set():
                    logger.warning("rag_ingest_worker outcome=timeout")
                process.kill()
                await process.wait()
            elif process.returncode:
                logger.warning("rag_ingest_worker outcome=failed")
        except OSError:
            logger.warning("rag_ingest_worker outcome=unavailable")
        finally:
            if monitor:
                monitor.cancel()
                await asyncio.gather(monitor, return_exceptions=True)
            if stop_wait:
                stop_wait.cancel()
                await asyncio.gather(stop_wait, return_exceptions=True)
            if process and process.returncode is None:
                process.kill()
                await process.wait()
        if not stop.is_set():
            try:
                await asyncio.wait_for(stop.wait(), timeout=1)
            except TimeoutError:
                pass
