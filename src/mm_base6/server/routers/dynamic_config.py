from fastapi import APIRouter
from starlette.responses import PlainTextResponse

from mm_base6 import BaseView
from mm_base6.server.cbv import cbv

router: APIRouter = APIRouter(prefix="/api/system/dynamic-configs", tags=["system"])


@cbv(router)
class CBV(BaseView):
    @router.get("/toml", response_class=PlainTextResponse)
    async def get_dynamic_configs_toml(self) -> str:
        return self.core.base_services.dynamic_config.export_as_toml()
