from fastapi import APIRouter
from mm_std import Result
from starlette.responses import PlainTextResponse

from mm_base6.server.cbv import cbv
from mm_base6.server.deps import BaseView

router: APIRouter = APIRouter(prefix="/api/system", tags=["system"])


@cbv(router)
class CBV(BaseView):
    @router.get("/stats")
    async def get_stats(self) -> dict[str, object]:
        psutil_stats = await self.core.system_service.get_psutil_stats()
        stats = await self.core.system_service.get_stats()
        return psutil_stats | stats.model_dump()

    @router.get("/logfile", response_class=PlainTextResponse)
    async def get_logfile(self) -> str:
        return await self.core.system_service.read_logfile()

    @router.delete("/logfile")
    async def clean_logfile(self) -> None:
        await self.core.system_service.clean_logfile()

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
        return await self.core.system_service.update_proxies()

    @router.post("/send-test-telegram-message")
    async def send_test_telegram_message(self) -> Result[list[int]]:
        message = ""
        for i in range(1800):
            message += f"{i} "
        return await self.core.system_service.send_telegram_message(message)
