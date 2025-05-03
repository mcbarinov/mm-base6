from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter
from mm_base6 import DC, DV, CoreConfig, DynamicConfigsModel, DynamicValuesModel, ServerConfig
from mm_std import utc_now

core_config = CoreConfig()

server_config = ServerConfig()
server_config.tags = ["data", "misc"]
server_config.main_menu = {"/data": "data", "/misc": "misc"}


class DynamicConfigs(DynamicConfigsModel):
    proxies_url = DC("http://localhost:8000", "proxies url, each proxy on new line")
    telegram_token = DC("", "telegram bot token", hide=True)
    telegram_chat_id = DC(0, "telegram chat id")
    telegram_polling = DC(False)
    telegram_admins = DC("", "admin1,admin2,admin3")
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


def get_router() -> APIRouter:
    from app.server.routers import data_router, misc_router, ui_router

    router = APIRouter()
    router.include_router(ui_router.router)
    router.include_router(data_router.router)
    router.include_router(misc_router.router)
    return router
