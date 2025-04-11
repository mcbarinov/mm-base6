from markupsafe import Markup
from mm_base6 import JinjaConfig

from app.core.core import Core
from app.core.db import DataStatus


def data_status(status: DataStatus) -> Markup:
    color = "black"
    if status == DataStatus.OK:
        color = "green"
    elif status == DataStatus.ERROR:
        color = "red"
    return Markup(f"<span style='color: {color};'>{status.value}</span>")  # noqa: S704 # nosec


async def header_info(core: Core) -> Markup:
    count = await core.db.data.count({})
    info = f"<span style='color: red'>data: {count}</span>"
    return Markup(info)  # noqa: S704 # nosec


async def footer_info(core: Core) -> Markup:
    count = await core.db.data.count({})
    info = f"data: {count}"
    return Markup(info)  # noqa: S704 # nosec


jinja_config = JinjaConfig(
    header_info=header_info,
    header_info_new_line=False,
    footer_info=footer_info,
    filters={"data_status": data_status},
)
