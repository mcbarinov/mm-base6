import traceback
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from logging import Logger
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.applications import AppType
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from jinja2 import Environment
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, PlainTextResponse
from starlette.staticfiles import StaticFiles
from starlette.types import Lifespan

from mm_base6 import CoreConfig, ServerConfig
from mm_base6.core.core import BaseCore, DB_co, DCONFIG_co, DVALUE_co
from mm_base6.core.errors import UserError
from mm_base6.server import utils
from mm_base6.server.auth import AccessTokenMiddleware
from mm_base6.server.jinja import JinjaConfig, init_env
from mm_base6.server.routers import base_router


def init_server(
    core: BaseCore[DCONFIG_co, DVALUE_co, DB_co],
    server_config: ServerConfig,
    jinja_config: JinjaConfig,
    router: APIRouter,
) -> FastAPI:
    jinja_env = init_env(core, server_config, jinja_config)
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=configure_lifespan(core))

    configure_state(app, core, server_config, jinja_env)
    configure_openapi(app, core.core_config, server_config)
    configure_exception_handler(app, core.core_config, core.logger)

    app.include_router(base_router)
    app.include_router(router)
    app.mount("/assets", StaticFiles(directory=Path(__file__).parent.absolute() / "assets"), name="assets")
    app.add_middleware(AccessTokenMiddleware, access_token=server_config.access_token)
    app.add_middleware(SessionMiddleware, secret_key=server_config.access_token)
    return app


# noinspection PyUnresolvedReferences
def configure_state(
    app: FastAPI, core: BaseCore[DCONFIG_co, DVALUE_co, DB_co], server_config: ServerConfig, jinja_env: Environment
) -> None:
    app.state.core = core
    app.state.jinja_env = jinja_env
    app.state.server_config = server_config


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


def configure_exception_handler(app: FastAPI, core_config: CoreConfig, logger: Logger) -> None:
    @app.exception_handler(Exception)
    async def exception_handler(_request: Request, err: Exception) -> PlainTextResponse:
        code = getattr(err, "code", None)

        message = f"{err.__class__.__name__}: {err}"

        hide_stacktrace = isinstance(err, UserError)
        if code in [400, 401, 403, 404, 405]:
            hide_stacktrace = True

        if not hide_stacktrace:
            logger.exception(err)
            message += "\n\n" + traceback.format_exc()

        if not core_config.debug:
            message = "error"

        return PlainTextResponse(message, status_code=500)


def configure_lifespan(core: BaseCore[DCONFIG_co, DVALUE_co, DB_co]) -> Lifespan[AppType]:
    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:  # noqa: UP043
        yield
        core.logger.debug("server shutdown")
        await core.shutdown()

    return lifespan
