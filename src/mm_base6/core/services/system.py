from __future__ import annotations

import asyncio
import logging
import platform
import threading
import time
from datetime import datetime, timedelta
from typing import Literal

import anyio
import psutil
import pydash
from bson import ObjectId
from mm_std import AsyncScheduler, utc_now
from pydantic import BaseModel

from mm_base6.core.config import CoreConfig
from mm_base6.core.db import BaseDb, SystemLog


class Stats(BaseModel):
    class ThreadInfo(BaseModel):
        name: str
        daemon: bool
        func_name: str | None

    class Scheduler(BaseModel):
        class Task(BaseModel):
            task_id: str
            interval: float
            run_count: int
            error_count: int
            last_run: datetime | None
            running: bool

        running: bool
        tasks: list[Task]

    class AsyncTask(BaseModel):
        name: str
        coro: str | None
        start_time: float | None
        status: Literal["running", "done", "cancelled"]

        @property
        def running_time(self) -> float | None:
            if self.start_time is None:
                return None
            return time.time() - self.start_time

    db: dict[str, int]  # collection name -> count
    logfile_app: int  # size in bytes
    logfile_access: int  # size in bytes
    system_logs: int  # count
    threads: list[ThreadInfo]
    scheduler: Scheduler
    async_tasks: list[AsyncTask]


logger = logging.getLogger(__name__)


# noinspection PyMethodMayBeStatic
class SystemService:
    def __init__(self, core_config: CoreConfig, db: BaseDb, scheduler: AsyncScheduler) -> None:
        self.db = db
        self.logfile_app = anyio.Path(core_config.data_dir / "app.log")
        self.logfile_access = anyio.Path(core_config.data_dir / "access.log")
        self.scheduler = scheduler

    async def system_log(self, category: str, data: object = None) -> None:
        logger.debug("system log: %s %s", category, data)
        await self.db.system_log.insert_one(SystemLog(id=ObjectId(), category=category, data=data))

    async def get_system_log_category_stats(self) -> dict[str, int]:
        result = {}
        for category in await self.db.system_log.collection.distinct("category"):
            result[category] = await self.db.system_log.count({"category": category})
        return result

    async def get_stats(self) -> Stats:
        # threads
        threads = []
        for t in threading.enumerate():
            target = t.__dict__.get("_target")
            func_name = None
            if target:
                func_name = target.__qualname__
            threads.append(Stats.ThreadInfo(name=t.name, daemon=t.daemon, func_name=func_name))
        threads = pydash.sort(threads, key=lambda x: x.name)

        # db
        db_stats = {}
        for col in await self.db.database.list_collection_names():
            db_stats[col] = await self.db.database[col].estimated_document_count()

        # AsyncScheduler
        scheduler_tasks: list[Stats.Scheduler.Task] = []
        for task_id, task in self.scheduler.tasks.items():
            scheduler_tasks.append(
                Stats.Scheduler.Task(
                    task_id=task_id,
                    interval=task.interval,
                    run_count=task.run_count,
                    error_count=task.error_count,
                    last_run=task.last_run,
                    running=task.running,
                )
            )
        scheduler = Stats.Scheduler(running=self.scheduler.is_running(), tasks=scheduler_tasks)

        async_tasks: list[Stats.AsyncTask] = []
        for async_task in asyncio.all_tasks():
            name = async_task.get_name()
            coro = async_task.get_coro().__qualname__ if async_task.get_coro() is not None else None  # type: ignore[union-attr]
            start_time = getattr(async_task, "start_time", None)
            status = "cancelled" if async_task.cancelled() else "done" if async_task.done() else "running"
            async_tasks.append(Stats.AsyncTask(name=name, coro=coro, start_time=start_time, status=status))

        return Stats(
            db=db_stats,
            logfile_app=(await self.logfile_app.stat()).st_size,
            logfile_access=(await self.logfile_access.stat()).st_size,
            system_logs=await self.db.system_log.count({}),
            threads=threads,
            scheduler=scheduler,
            async_tasks=async_tasks,
        )

    async def get_psutil_stats(self) -> dict[str, object]:
        def format_bytes(num_bytes: int) -> str:
            """Convert bytes to a human-readable string."""
            for unit in ["B", "KB", "MB", "GB", "TB"]:
                if num_bytes < 1024.0:
                    return f"{num_bytes:.2f} {unit}"
                num_bytes /= 1024.0  # type: ignore[assignment]
            return f"{num_bytes:.2f} PB"

        def format_duration(seconds: float) -> str:
            """Convert seconds to a human-readable duration string."""
            return str(timedelta(seconds=int(seconds)))

        def psutils_stats() -> dict[str, object]:
            # CPU Information
            cpu_count = psutil.cpu_count(logical=True)
            # Measure CPU usage over an interval of 10 second for an average value
            cpu_percent = psutil.cpu_percent(interval=10)
            cpu_freq = psutil.cpu_freq()
            cpu_freq_current = f"{cpu_freq.current:.2f} MHz" if cpu_freq else "N/A"

            # Memory Information
            virtual_mem = psutil.virtual_memory()
            total_memory = format_bytes(virtual_mem.total)
            used_memory = format_bytes(virtual_mem.used)
            available_memory = format_bytes(virtual_mem.available)
            memory_percent = f"{virtual_mem.percent}%"

            # Disk Usage Information (using root partition as an example)
            disk_usage = psutil.disk_usage("/")
            total_disk = format_bytes(disk_usage.total)
            used_disk = format_bytes(disk_usage.used)
            free_disk = format_bytes(disk_usage.free)
            disk_percent = f"{disk_usage.percent}%"

            # System Uptime (since boot)
            boot_time = psutil.boot_time()
            uptime_seconds = time.time() - boot_time
            uptime = format_duration(uptime_seconds)

            # System Platform Information
            system_info = {
                "platform": platform.system(),
                "platform_release": platform.release(),
                "platform_version": platform.version(),
                "architecture": platform.machine(),
                "hostname": platform.node(),
                "processor": platform.processor(),
            }

            return {
                "system": system_info,
                "uptime": uptime,
                "cpu": {
                    "cpu_count": cpu_count,
                    "cpu_usage": f"{cpu_percent}%",
                    "cpu_frequency": cpu_freq_current,
                },
                "memory": {
                    "total": total_memory,
                    "used": used_memory,
                    "available": available_memory,
                    "usage_percent": memory_percent,
                },
                "disk": {"total": total_disk, "used": used_disk, "free": free_disk, "usage_percent": disk_percent},
                "time": {"local": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), "utc": utc_now()},
            }

        return await asyncio.to_thread(psutils_stats)

    async def read_logfile(self, file: str) -> str:
        if file == "app":
            return await self.logfile_app.read_text(encoding="utf-8")
        if file == "access":
            return await self.logfile_access.read_text(encoding="utf-8")
        raise ValueError(f"Unknown logfile: {file}")

    async def clean_logfile(self, file: str) -> None:
        if file == "app":
            await self.logfile_app.write_text("", encoding="utf-8")
            return
        if file == "access":
            await self.logfile_access.write_text("", encoding="utf-8")
            return
        raise ValueError(f"Unknown logfile: {file}")
