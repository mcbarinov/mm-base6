from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter
from mm_std import utc_now

from app.core.types import AppCore
from mm_base6 import DC, DV, CoreConfig, DynamicConfigsModel, DynamicValuesModel, ServerConfig

core_config = CoreConfig()

server_config = ServerConfig()
server_config.tags = ["data", "misc"]
server_config.main_menu = {"/data": "data", "/misc": "misc"}


class DynamicConfigs(DynamicConfigsModel):
    proxies_url = DC("http://localhost:8000", "proxies url, each proxy on new line")
    telegram_token = DC("", "telegram bot token", hide=True)
    telegram_chat_id = DC(0, "telegram chat id")
    telegram_bot_admins = DC("", "list of telegram bot admins, for example: 123456789,987654321")
    telegram_bot_auto_start = DC(False)
    price = DC(Decimal("1.23"), "long long long long long long long long long long long long long long long long ")
    secret_password = DC("abc", hide=True)
    long_cfg_1 = DC("many lines\n" * 5)


class DynamicValues(DynamicValuesModel):
    proxies: DV[list[str]] = DV([])
    proxies_updated_at: DV[datetime | None] = DV(None)
    tmp1 = DV("bla")
    tmp2 = DV("bla")
    processed_block = DV(111, "bla bla about processed_block")
    last_checked_at = DV(utc_now(), "bla bla about last_checked_at", False)


async def configure_scheduler(core: AppCore) -> None:
    """Configure background scheduler tasks."""
    core.scheduler.add_task("generate_one", 60, core.services.data.generate_one)


async def start_core(core: AppCore) -> None:
    """Startup logic for the application."""


async def stop_core(core: AppCore) -> None:
    """Cleanup logic for the application."""


def get_router() -> APIRouter:
    from app.server import routers

    router = APIRouter()
    router.include_router(routers.ui.router)
    router.include_router(routers.data.router)
    router.include_router(routers.misc.router)
    return router
