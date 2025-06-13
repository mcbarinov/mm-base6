from typing import cast

from fastapi import Depends
from starlette.requests import Request

from app.core.db import Db
from app.settings import AppCore, DynamicConfigs, DynamicValues
from mm_base6 import BaseView


async def get_core(request: Request) -> AppCore:
    return cast(AppCore, request.app.state.core)


class View(BaseView[DynamicConfigs, DynamicValues, Db]):
    core: AppCore = Depends(get_core)
