from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import partial
from typing import Any

import mm_jinja
from jinja2 import ChoiceLoader, Environment, PackageLoader
from markupsafe import Markup
from mm_mongo import json_dumps
from starlette.requests import Request
from starlette.responses import HTMLResponse

from mm_base6.core.core import BaseCoreAny
from mm_base6.server import utils
from mm_base6.server.config import ServerConfig


def system_log_data_truncate(data: object) -> str:
    if not data:
        return ""
    res = json_dumps(data)
    if len(res) > 100:
        return res[:100] + "..."
    return res


@dataclass
class JinjaConfig:
    header_info: Callable[..., Awaitable[Markup]] | None = None
    header_info_new_line: bool = False
    footer_info: Callable[..., Awaitable[Markup]] | None = None
    filters: dict[str, Callable[..., Any]] | None = None
    globals: dict[str, Any] | None = None


async def empty_markup(_: object) -> Markup:
    return Markup("")


def init_env(core: BaseCoreAny, server_config: ServerConfig, jinja_config: JinjaConfig) -> Environment:
    loader = ChoiceLoader([PackageLoader("mm_base6.server"), PackageLoader("app.server")])

    header_info = jinja_config.header_info if jinja_config.header_info else empty_markup
    footer_info = jinja_config.footer_info if jinja_config.footer_info else empty_markup
    custom_filters: dict[str, Callable[..., Any]] = {
        "system_log_data_truncate": system_log_data_truncate,
    }
    custom_globals: dict[str, Any] = {
        "core_config": core.core_config,
        "server_config": server_config,
        "dconfig": core.dconfig,
        "dvalue": core.dvalue,
        "confirm": Markup(""" onclick="return confirm('sure?')" """),
        "header_info": partial(header_info, core),
        "footer_info": partial(footer_info, core),
        "header_info_new_line": jinja_config.header_info_new_line,
        "app_version": utils.get_package_version("app"),
        "mm_base6_version": utils.get_package_version("mm_base6"),
    }

    if jinja_config.globals:
        custom_globals |= jinja_config.globals
    if jinja_config.filters:
        custom_filters |= jinja_config.filters

    return mm_jinja.init_jinja(loader, custom_globals=custom_globals, custom_filters=custom_filters, enable_async=True)


class Render:
    def __init__(self, env: Environment, request: Request) -> None:
        self.env = env
        self.request = request

    async def html(self, template_name: str, **kwargs: object) -> HTMLResponse:
        flash_messages = self.request.session.pop("flash_messages") if "flash_messages" in self.request.session else []
        html_content = await self.env.get_template(template_name).render_async(kwargs | {"flash_messages": flash_messages})
        return HTMLResponse(content=html_content, status_code=200)

    def flash(self, message: str, is_error: bool = False) -> None:
        if "flash_messages" not in self.request.session:
            self.request.session["flash_messages"] = []
        self.request.session["flash_messages"].append({"message": message, "error": is_error})
