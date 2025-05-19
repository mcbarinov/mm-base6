from typing import cast

from fastapi import Depends, Request
from jinja2 import Environment
from mm_telegram import TelegramBot
from starlette.datastructures import FormData

from mm_base6 import ServerConfig
from mm_base6.core.core import BaseCoreAny
from mm_base6.server.jinja import Render


async def get_core(request: Request) -> BaseCoreAny:
    return cast(BaseCoreAny, request.app.state.core)


async def get_render(request: Request) -> Render:
    jinja_env = cast(Environment, request.app.state.jinja_env)
    return Render(jinja_env, request)


async def get_server_config(request: Request) -> ServerConfig:
    return cast(ServerConfig, request.app.state.server_config)


async def get_form_data(request: Request) -> FormData:
    return await request.form()


async def get_telegram_bot(request: Request) -> TelegramBot:
    return cast(TelegramBot, request.app.state.telegram_bot)


class BaseView:
    core: BaseCoreAny = Depends(get_core)
    telegram_bot: TelegramBot = Depends(get_telegram_bot)
    server_config: ServerConfig = Depends(get_server_config)
    form_data: FormData = Depends(get_form_data)
    render: Render = Depends(get_render)
