from fastapi import APIRouter
from mm_std import Result
from starlette.responses import PlainTextResponse

from mm_base6.server.deps import BaseCoreDep

router: APIRouter = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/stats")
async def get_stats(core: BaseCoreDep) -> dict[str, object]:
    psutil_stats = await core.system_service.get_psutil_stats()
    stats = await core.system_service.get_stats()
    return psutil_stats | stats.model_dump()


@router.get("/logfile", response_class=PlainTextResponse)
async def get_logfile(core: BaseCoreDep) -> str:
    return await core.system_service.read_logfile()


@router.delete("/logfile")
async def clean_logfile(core: BaseCoreDep) -> None:
    await core.system_service.clean_logfile()


@router.post("/scheduler/start")
async def start_scheduler(core: BaseCoreDep) -> None:
    core.scheduler.start()


@router.post("/scheduler/stop")
async def stop_scheduler(core: BaseCoreDep) -> None:
    core.scheduler.stop()


@router.post("/scheduler/reinit")
async def reinit_scheduler(core: BaseCoreDep) -> None:
    await core.reinit_scheduler()


@router.post("/update-proxies")
async def update_proxies(core: BaseCoreDep) -> int | None:
    return await core.system_service.update_proxies()


@router.post("/send-test-telegram-message")
async def send_test_telegram_message(core: BaseCoreDep) -> Result[list[int]]:
    message = ""
    for i in range(1800):
        message += f"{i} "
    return await core.system_service.send_telegram_message(message)
