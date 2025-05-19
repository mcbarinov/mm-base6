import asyncio
import time
from collections.abc import Coroutine
from contextvars import Context
from typing import Any, TypeVar

import uvloop
from fastapi import APIRouter
from mm_telegram import TelegramBot, TelegramHandler

from mm_base6.core.config import CoreConfig
from mm_base6.core.core import BaseCore, DB_co, DYNAMIC_CONFIGS_co, DYNAMIC_VALUES_co
from mm_base6.core.types import SERVICE_REGISTRY
from mm_base6.server.config import ServerConfig
from mm_base6.server.jinja import JinjaConfig
from mm_base6.server.server import init_server
from mm_base6.server.uvicorn import serve_uvicorn

Core = TypeVar("Core", bound=BaseCore[Any, Any, Any, Any])


def run(
    *,
    core_config: CoreConfig,
    server_config: ServerConfig,
    jinja_config: JinjaConfig,
    core_class: type[BaseCore[DYNAMIC_CONFIGS_co, DYNAMIC_VALUES_co, DB_co, SERVICE_REGISTRY]],
    telegram_handlers: list[TelegramHandler],
    router: APIRouter,
    host: str,
    port: int,
    uvicorn_log_level: str,
) -> None:
    uvloop.run(
        _main(
            core_config=core_config,
            server_config=server_config,
            core_class=core_class,
            telegram_handlers=telegram_handlers,
            router=router,
            jinja_config=jinja_config,
            host=host,
            port=port,
            uvicorn_log_level=uvicorn_log_level,
        )
    )


async def _main(
    *,
    core_config: CoreConfig,
    server_config: ServerConfig,
    jinja_config: JinjaConfig,
    core_class: type[BaseCore[DYNAMIC_CONFIGS_co, DYNAMIC_VALUES_co, DB_co, SERVICE_REGISTRY]],
    telegram_handlers: list[TelegramHandler],
    router: APIRouter,
    host: str,
    port: int,
    uvicorn_log_level: str,
) -> None:
    loop = asyncio.get_running_loop()
    loop.set_task_factory(_custom_task_factory)

    core = await core_class.init(core_config)
    await core.startup()

    telegram_bot = TelegramBot(telegram_handlers, {"core": core})
    telegram_bot_settings = core.base_services.telegram.get_bot_settings()
    if telegram_bot_settings and telegram_bot_settings.auto_start:
        await telegram_bot.start(telegram_bot_settings.token, telegram_bot_settings.admins)

    fastapi_app = init_server(core, telegram_bot, server_config, jinja_config, router)
    await serve_uvicorn(fastapi_app, host=host, port=port, log_level=uvicorn_log_level)  # nosec


def _custom_task_factory(
    loop: asyncio.AbstractEventLoop, coro: Coroutine[Any, Any, Any], *, context: Context | None = None
) -> asyncio.tasks.Task[Any]:
    task = asyncio.Task(coro, loop=loop, context=context)
    task.start_time = time.time()  # type: ignore[attr-defined] # Inject a start_time attribute (timestamp in seconds)
    return task
