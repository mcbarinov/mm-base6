import asyncio
import time
from collections.abc import Coroutine
from contextvars import Context
from typing import Any

from mm_telegram import TelegramBot, TelegramHandler

from mm_base6.core.core import CoreProtocol
from mm_base6.server.config import ServerConfig
from mm_base6.server.jinja import JinjaConfig
from mm_base6.server.server import init_server
from mm_base6.server.uvicorn import serve_uvicorn


async def run[CoreType: CoreProtocol[Any, Any, Any, Any]](
    *,
    core: CoreType,
    server_config: ServerConfig,
    jinja_config_cls: type[JinjaConfig[CoreType]],
    telegram_handlers: list[TelegramHandler] | None = None,
    host: str,
    port: int,
    uvicorn_log_level: str,
) -> None:
    loop = asyncio.get_running_loop()
    loop.set_task_factory(_custom_task_factory)

    # Core startup is already handled in Core.init, just call startup hook
    await core.startup()

    telegram_bot = None
    if telegram_handlers is not None:
        telegram_bot = TelegramBot(telegram_handlers, {"core": core})
        telegram_bot_settings = core.base_services.telegram.get_bot_settings()
        if telegram_bot_settings and telegram_bot_settings.auto_start:
            await telegram_bot.start(telegram_bot_settings.token, telegram_bot_settings.admins)

    jinja_config = jinja_config_cls(core)
    fastapi_app = init_server(core, telegram_bot, server_config, jinja_config)
    await serve_uvicorn(fastapi_app, host=host, port=port, log_level=uvicorn_log_level)  # nosec


def _custom_task_factory(
    loop: asyncio.AbstractEventLoop, coro: Coroutine[Any, Any, Any], *, context: Context | None = None
) -> asyncio.tasks.Task[Any]:
    task = asyncio.Task(coro, loop=loop, context=context)
    task.start_time = time.time()  # type: ignore[attr-defined] # Inject a start_time attribute (timestamp in seconds)
    return task
