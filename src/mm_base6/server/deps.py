from typing import Any, cast

from fastapi import Depends, Request
from jinja2 import Environment
from mm_telegram import TelegramBot
from starlette.datastructures import FormData

from mm_base6.config import Config
from mm_base6.core.builtin_services.settings import BaseSettings
from mm_base6.core.builtin_services.state import BaseState
from mm_base6.core.core import CoreProtocol
from mm_base6.core.db import BaseDb
from mm_base6.server.jinja import Render


async def get_core[SC: BaseSettings, ST: BaseState, DB: BaseDb, SR](
    request: Request,
) -> CoreProtocol[SC, ST, DB, SR]:
    return cast(CoreProtocol[SC, ST, DB, SR], request.app.state.core)


async def get_render(request: Request) -> Render:
    jinja_env = cast(Environment, request.app.state.jinja_env)
    return Render(jinja_env, request)


async def get_config(request: Request) -> Config:
    return cast(Config, request.app.state.core.config)


async def get_form_data(request: Request) -> FormData:
    return await request.form()


async def get_telegram_bot(request: Request) -> TelegramBot:
    return cast(TelegramBot, request.app.state.telegram_bot)


class View[SC: BaseSettings, ST: BaseState, DB: BaseDb, SR]:
    core: CoreProtocol[SC, ST, DB, SR] = Depends(get_core)
    telegram_bot: TelegramBot = Depends(get_telegram_bot)
    config: Config = Depends(get_config)
    form_data: FormData = Depends(get_form_data)
    render: Render = Depends(get_render)


# Type alias for internal library routers
InternalView = View[BaseSettings, BaseState, BaseDb, Any]
