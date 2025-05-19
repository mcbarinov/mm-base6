from fastapi import APIRouter
from starlette.responses import PlainTextResponse

from mm_base6.core.db import DynamicValue
from mm_base6.server.cbv import cbv
from mm_base6.server.deps import BaseView

router: APIRouter = APIRouter(prefix="/api/system/dynamic-values", tags=["system"])


@cbv(router)
class CBV(BaseView):
    @router.get("/toml", response_class=PlainTextResponse)
    async def get_dynamic_values_as_toml(self) -> str:
        return self.core.base_services.dynamic_value.export_dynamic_values_as_toml()

    @router.get("/{key}/toml", response_class=PlainTextResponse)
    async def get_dynamic_value_as_toml(self, key: str) -> str:
        return self.core.base_services.dynamic_value.export_dynamic_value_as_toml(key)

    @router.get("/{key}/value")
    async def get_dynamic_value_value(self, key: str) -> object:
        return self.core.base_services.dynamic_value.get_dynamic_value(key)

    @router.get("/{key}")
    async def get_dynamic_value_key(self, key: str) -> DynamicValue:
        return await self.core.db.dynamic_value.get(key)
