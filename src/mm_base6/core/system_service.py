from __future__ import annotations

import threading
from datetime import datetime
from logging import Logger
from typing import cast

import anyio
import mm_telegram
import pydash
from bson import ObjectId
from mm_std import AsyncScheduler, Err, Result, ahr, synchronized, toml_dumps, toml_loads, utc_now
from pydantic import BaseModel

from mm_base6.core.config import CoreConfig
from mm_base6.core.db import BaseDb, DConfigType, DLog
from mm_base6.core.dconfig import DConfigStorage
from mm_base6.core.dvalue import DValueStorage
from mm_base6.core.errors import UserError


class Stats(BaseModel):
    class ThreadInfo(BaseModel):
        name: str
        daemon: bool
        func_name: str | None

    class SchedulerTask(BaseModel):
        task_id: str
        interval: float
        run_count: int
        last_run: datetime | None
        running: bool

    db: dict[str, int]  # collection name -> count
    logfile: int  # size in bytes
    system_log: int  # count
    threads: list[ThreadInfo]
    scheduler_tasks: list[SchedulerTask]


class DConfigInfo(BaseModel):
    dconfig: dict[str, object]
    descriptions: dict[str, str]
    types: dict[str, DConfigType]
    hidden: set[str]


class DValueInfo(BaseModel):
    dvalue: dict[str, object]
    persistent: dict[str, bool]
    descriptions: dict[str, str]


# noinspection PyMethodMayBeStatic
class SystemService:
    def __init__(self, core_config: CoreConfig, logger: Logger, db: BaseDb, scheduler: AsyncScheduler) -> None:
        self.logger = logger
        self.db = db
        self.logfile = anyio.Path(core_config.data_dir / "app.log")
        self.scheduler = scheduler

    # dconfig

    def get_dconfig_info(self) -> DConfigInfo:
        return DConfigInfo(
            dconfig=DConfigStorage.storage,
            descriptions=DConfigStorage.descriptions,
            types=DConfigStorage.types,
            hidden=DConfigStorage.hidden,
        )

    def export_dconfig_as_toml(self) -> str:
        result = pydash.omit(DConfigStorage.storage, *DConfigStorage.hidden)
        return toml_dumps(result)

    async def update_dconfig_from_toml(self, toml_value: str) -> bool | None:
        data = toml_loads(toml_value)
        if isinstance(data, dict):
            return await DConfigStorage.update({key: str(value) for key, value in data.items()})

    async def update_dconfig(self, data: dict[str, str]) -> bool:
        return await DConfigStorage.update(data)

    def has_dconfig_key(self, key: str) -> bool:
        return key in DConfigStorage.storage

    # dvalue
    def get_dvalue_info(self) -> DValueInfo:
        return DValueInfo(
            dvalue=DValueStorage.storage,
            persistent=DValueStorage.persistent,
            descriptions=DValueStorage.descriptions,
        )

    def export_dvalue_as_toml(self) -> str:
        return toml_dumps(DValueStorage.storage)

    def export_dvalue_field_as_toml(self, key: str) -> str:
        return toml_dumps({key: DValueStorage.storage[key]})

    def get_dvalue_value(self, key: str) -> object:
        return DValueStorage.storage[key]

    async def update_dvalue_field(self, key: str, toml_str: str) -> None:
        data = toml_loads(toml_str)
        if key not in data:
            raise UserError(f"Key '{key}' not found in toml data")
        await DValueStorage.update_value(key, data[key])

    def has_dvalue_key(self, key: str) -> bool:
        return key in DValueStorage.storage

    # dlogs
    async def dlog(self, category: str, data: object = None) -> None:
        self.logger.debug("dlog: %s %s", category, data)
        await self.db.dlog.insert_one(DLog(id=ObjectId(), category=category, data=data))

    async def get_dlog_category_stats(self) -> dict[str, int]:
        result = {}
        for category in await self.db.dlog.collection.distinct("category"):
            result[category] = await self.db.dlog.count({"category": category})
        return result

    # system

    def has_telegram_settings(self) -> bool:
        try:
            token = cast(str, DConfigStorage.storage.get("telegram_token"))
            chat_id = cast(int, DConfigStorage.storage.get("telegram_chat_id"))
            return ":" in token and chat_id != 0  # noqa: TRY300
        except Exception:
            return False

    async def send_telegram_message(self, message: str) -> Result[list[int]]:
        # TODO: run it in a separate thread
        if not self.has_telegram_settings():
            return Err("telegram token or chat_id is not set")
        token = cast(str, DConfigStorage.storage.get("telegram_token"))
        chat_id = cast(int, DConfigStorage.storage.get("telegram_chat_id"))
        res = await mm_telegram.async_send_message(token, chat_id, message)
        if res.is_err():
            await self.dlog("send_telegram_message", {"error": res.err, "message": message, "data": res.data})
            self.logger.error("send_telegram_message error: %s", res.err)
        return res

    def has_proxies_settings(self) -> bool:
        return (
            "proxies_url" in DConfigStorage.storage
            and "proxies" in DValueStorage.storage
            and "proxies_updated_at" in DValueStorage.storage
        )

    @synchronized
    async def update_proxies(self) -> int | None:
        proxies_url = cast(str, DConfigStorage.storage.get("proxies_url"))
        res = await ahr(proxies_url)
        if res.is_error():
            await self.dlog("update_proxies", {"error": res.error})
            return -1
        proxies = res.body.strip().splitlines()
        proxies = [p.strip() for p in proxies if p.strip()]
        await DValueStorage.update_value("proxies", proxies)
        await DValueStorage.update_value("proxies_updated_at", utc_now())
        return len(proxies)

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
        scheduler_tasks: list[Stats.SchedulerTask] = []
        for task_id, task in self.scheduler.tasks.items():
            scheduler_tasks.append(
                Stats.SchedulerTask(
                    task_id=task_id,
                    interval=task.interval,
                    run_count=task.run_count,
                    last_run=task.last_run,
                    running=task.running,
                )
            )

        return Stats(
            db=db_stats,
            logfile=(await self.logfile.stat()).st_size,
            system_log=await self.db.dlog.count({}),
            threads=threads,
            scheduler_tasks=scheduler_tasks,
        )

    async def read_logfile(self) -> str:
        return await self.logfile.read_text(encoding="utf-8")

    async def clean_logfile(self) -> None:
        await self.logfile.write_text("")
