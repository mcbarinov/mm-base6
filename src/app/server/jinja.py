from markupsafe import Markup

from app.core.db import DataStatus
from app.core.types import AppCore
from mm_base6 import JinjaConfig


def data_status(status: DataStatus) -> Markup:
    color = "black"
    if status == DataStatus.OK:
        color = "green"
    elif status == DataStatus.ERROR:
        color = "red"
    return Markup(f"<span style='color: {color};'>{status.value}</span>")  # noqa: S704 # nosec


async def header_info(core: AppCore) -> Markup:
    count = await core.db.data.count({})
    info = f"<span style='color: red'>data: {count}</span>"
    return Markup(info)  # noqa: S704 # nosec


async def footer_info(core: AppCore) -> Markup:
    count = await core.db.data.count({})
    info = f"data: {count}"
    return Markup(info)  # noqa: S704 # nosec


jinja_config = JinjaConfig(
    header_info=header_info,
    header_info_new_line=False,
    footer_info=footer_info,
    filters={"data_status": data_status},
)
