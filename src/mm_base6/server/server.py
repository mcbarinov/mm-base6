import asyncio
import logging
import traceback
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from jinja2 import Environment
from mm_telegram import TelegramBot
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, PlainTextResponse
from starlette.staticfiles import StaticFiles
from starlette.types import Lifespan

from mm_base6 import CoreConfig, ServerConfig
from mm_base6.core.core import CoreProtocol
from mm_base6.core.db import BaseDb
from mm_base6.core.errors import UserError
from mm_base6.core.services.settings import SettingsModel
from mm_base6.core.services.state import StateModel
from mm_base6.server import utils
from mm_base6.server.jinja import JinjaConfig, init_env
from mm_base6.server.middleware.auth import AccessTokenMiddleware
from mm_base6.server.middleware.request_logging import RequestLoggingMiddleware
from mm_base6.server.routers import base_router

logger = logging.getLogger(__name__)


def init_server[CoreType: CoreProtocol[Any, Any, Any, Any]](
    core: CoreType,
    telegram_bot: TelegramBot | None,
    server_config: ServerConfig,
    jinja_config: JinjaConfig[CoreType],
) -> FastAPI:
    jinja_env = init_env(core, server_config, jinja_config)
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=configure_lifespan(core))

    configure_state(app, core, telegram_bot, server_config, jinja_env)
    configure_openapi(app, core.core_config, server_config)
    configure_exception_handler(app, core.core_config)

    app.include_router(base_router)
    app.include_router(server_config.get_router())
    app.mount("/assets", StaticFiles(directory=Path(__file__).parent.absolute() / "assets"), name="assets")
    app.add_middleware(AccessTokenMiddleware, access_token=server_config.access_token)
    app.add_middleware(SessionMiddleware, secret_key=server_config.access_token)
    app.add_middleware(RequestLoggingMiddleware, core.core_config.data_dir / "access.log", core.core_config.debug)
    return app


# noinspection PyUnresolvedReferences
def configure_state[SC: SettingsModel, ST: StateModel, DB: BaseDb, SR](
    app: FastAPI,
    core: CoreProtocol[SC, ST, DB, SR],
    telegram_bot: TelegramBot | None,
    server_config: ServerConfig,
    jinja_env: Environment,
) -> None:
    app.state.core = core
    app.state.jinja_env = jinja_env
    app.state.server_config = server_config
    app.state.telegram_bot = telegram_bot


def configure_openapi(app: FastAPI, core_config: CoreConfig, server_config: ServerConfig) -> None:
    @app.get("/system/openapi.json", include_in_schema=False)
    async def get_open_api_endpoint() -> JSONResponse:
        openapi = get_openapi(
            title=core_config.app_name,
            version=utils.get_package_version("app"),
            routes=app.routes,
            tags=server_config.tags_metadata,
        )
        return JSONResponse(openapi)

    @app.get("/system/openapi", include_in_schema=False)
    async def get_documentation() -> HTMLResponse:
        return get_swagger_ui_html(openapi_url="/system/openapi.json", title=core_config.app_name)


def configure_exception_handler(app: FastAPI, core_config: CoreConfig) -> None:
    @app.exception_handler(Exception)
    async def exception_handler(request: Request, err: Exception) -> PlainTextResponse:
        logger.debug("exception_handler", extra={"exception": err})
        code = getattr(err, "code", None)

        message = f"{err.__class__.__name__}: {err}"

        hide_stacktrace = isinstance(err, UserError)
        if code in [400, 401, 403, 404, 405]:
            hide_stacktrace = True

        if not hide_stacktrace:
            tb = traceback.format_exc()
            logger.error(f"exception_handler: url={request.url}, error={err}\n{tb}")
            message += "\n\n" + traceback.format_exc()

        if not core_config.debug:
            message = "error"

        logger.debug("exception_handler", extra={"m": message})
        return PlainTextResponse(message, status_code=500)


def configure_lifespan[SC: SettingsModel, ST: StateModel, DB: BaseDb, SR](
    core: CoreProtocol[SC, ST, DB, SR],
) -> Lifespan[FastAPI]:
    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:  # noqa: UP043
        try:
            yield
        finally:
            try:
                logger.debug("server shutdown")
                await core.shutdown()
            except asyncio.CancelledError:
                # Suppress CancelledError during shutdown
                logger.debug("server shutdown interrupted by cancellation")

    return lifespan
