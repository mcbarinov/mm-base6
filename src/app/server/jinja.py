from typing import override

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
    return Markup("<span style='color: {};'>{}</span>").format(color, status.value)


class AppJinjaConfig(JinjaConfig[AppCore]):
    filters = {"data_status": data_status}
    globals = {}
    header_status_inline = True

    @override
    async def header_status(self) -> Markup:
        count = await self.core.db.data.count({})
        return Markup("<span style='color: red'>data: {}</span>").format(count)
