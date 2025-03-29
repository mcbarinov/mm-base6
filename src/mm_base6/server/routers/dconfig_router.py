from fastapi import APIRouter
from starlette.responses import PlainTextResponse

from mm_base6 import BaseView
from mm_base6.server.cbv import cbv

router: APIRouter = APIRouter(prefix="/api/system/dconfigs", tags=["system"])


@cbv(router)
class CBV(BaseView):
    @router.get("/toml", response_class=PlainTextResponse)
    async def get_dconfigs_toml(self) -> str:
        return self.core.system_service.export_dconfig_as_toml()
