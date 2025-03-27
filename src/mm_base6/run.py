import asyncio
import time
from collections.abc import Coroutine
from contextvars import Context
from typing import Any, TypeVar

import uvloop
from fastapi import APIRouter

from mm_base6.core.config import CoreConfig
from mm_base6.core.core import BaseCore
from mm_base6.server.config import ServerConfig
from mm_base6.server.jinja import JinjaConfig
from mm_base6.server.server import init_server
from mm_base6.server.uvicorn import serve_uvicorn

Core = TypeVar("Core", bound=BaseCore[Any, Any, Any])


def run(
    *,
    core_config: CoreConfig,
    server_config: ServerConfig,
    jinja_config: JinjaConfig,
    core_class: type[Core],
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
    core_class: type[Core],
    router: APIRouter,
    host: str,
    port: int,
    uvicorn_log_level: str,
) -> None:
    loop = asyncio.get_running_loop()
    loop.set_task_factory(_custom_task_factory)
    core = await core_class.init(core_config)
    await core.startup()
    fastapi_app = init_server(core, server_config, jinja_config, router)
    await serve_uvicorn(fastapi_app, host=host, port=port, log_level=uvicorn_log_level)  # nosec


def _custom_task_factory(
    loop: asyncio.AbstractEventLoop, coro: Coroutine[Any, Any, Any], *, context: Context | None = None
) -> asyncio.tasks.Task[Any]:
    task = asyncio.Task(coro, loop=loop, context=context)
    task.start_time = time.time()  # type: ignore[attr-defined] # Inject a start_time attribute (timestamp in seconds)
    return task
