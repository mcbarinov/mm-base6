from collections.abc import Mapping
from typing import Any

from bson import json_util
from fastapi import APIRouter
from mm_std import Result
from starlette.responses import PlainTextResponse, Response

from mm_base6.server.cbv import cbv
from mm_base6.server.deps import BaseView

router: APIRouter = APIRouter(prefix="/api/system", tags=["system"])


@cbv(router)
class CBV(BaseView):
    @router.get("/stats")
    async def get_stats(self) -> dict[str, object]:
        psutil_stats = await self.core.base_services.system.get_psutil_stats()
        stats = await self.core.base_services.system.get_stats()
        return psutil_stats | stats.model_dump()

    @router.get("/mongo/profile")
    async def read_mongo_profile(self) -> Mapping[str, Any]:
        return await self.core.database.command({"profile": -1})

    @router.get("/mongo/slow")
    async def get_mongo_slow(self) -> Response:
        limit = 10
        cursor = self.core.db.database["system.profile"].find().sort("ts", -1).limit(limit)
        res = await cursor.to_list(limit)
        json_data: str = json_util.dumps(res)
        return Response(content=json_data, media_type="application/json")

    @router.post("/mongo/profile")
    async def set_mongo_profiling(self, level: int, slowms: int) -> Mapping[str, Any]:
        return await self.core.database.command({"profile": level, "slowms": slowms})

    @router.delete("/mongo/slow")
    async def delete_mongo_slow_queries(self) -> None:
        await self.core.database.command({"profile": 0})
        await self.core.database.drop_collection("system.profile")

    @router.get("/logfile/{file}", response_class=PlainTextResponse)
    async def get_logfile(self, file: str) -> str:
        return await self.core.base_services.system.read_logfile(file)

    @router.delete("/logfile/{file}")
    async def clean_logfile(self, file: str) -> None:
        await self.core.base_services.system.clean_logfile(file)

    @router.post("/scheduler/start")
    async def start_scheduler(self) -> None:
        self.core.scheduler.start()

    @router.post("/scheduler/stop")
    async def stop_scheduler(self) -> None:
        self.core.scheduler.stop()

    @router.post("/scheduler/reinit")
    async def reinit_scheduler(self) -> None:
        await self.core.reinit_scheduler()

    @router.post("/update-proxies")
    async def update_proxies(self) -> int | None:
        return await self.core.base_services.proxy.update_proxies()

    @router.post("/telegram/send-test-message")
    async def send_test_telegram_message(self) -> Result[list[int]]:
        message = ""
        for i in range(1800):
            message += f"{i} "
        return await self.core.base_services.telegram.send_message(message)

    @router.post("/telegram/start-bot")
    async def start_telegram_bot(self) -> bool:
        return await self.core.base_services.telegram.start_bot(self.telegram_bot)

    @router.post("/telegram/shutdown-bot")
    async def shutdown_telegram_bot(self) -> bool:
        return await self.core.base_services.telegram.shutdown_bot(self.telegram_bot)
