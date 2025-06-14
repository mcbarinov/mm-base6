from fastapi import APIRouter
from starlette.responses import PlainTextResponse

from mm_base6.server.cbv import cbv
from mm_base6.server.deps import InternalView

router: APIRouter = APIRouter(prefix="/api/system/settings", tags=["system"])


@cbv(router)
class CBV(InternalView):
    @router.get("/toml", response_class=PlainTextResponse)
    async def get_settings_toml(self) -> str:
        return self.core.base_services.settings.export_as_toml()
