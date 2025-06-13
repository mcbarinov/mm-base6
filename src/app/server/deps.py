from typing import cast

from fastapi import Depends
from starlette.requests import Request

from app.core.core import Core
from app.core.db import Db
from app.settings import DynamicConfigs, DynamicValues
from mm_base6 import BaseView


async def get_core(request: Request) -> Core:
    return cast(Core, request.app.state.core)


class View(BaseView[DynamicConfigs, DynamicValues, Db]):
    core: Core = Depends(get_core)
