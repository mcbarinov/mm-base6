from fastapi import APIRouter
from starlette.responses import PlainTextResponse

from mm_base6.core.db import State
from mm_base6.server.cbv import cbv
from mm_base6.server.deps import InternalView

router: APIRouter = APIRouter(prefix="/api/system/state", tags=["system"])


@cbv(router)
class CBV(InternalView):
    @router.get("/toml", response_class=PlainTextResponse)
    async def get_state_as_toml(self) -> str:
        return self.core.base_services.state.export_state_as_toml()

    @router.get("/{key}/toml", response_class=PlainTextResponse)
    async def get_state_value_as_toml(self, key: str) -> str:
        return self.core.base_services.state.export_state_value_as_toml(key)

    @router.get("/{key}/value")
    async def get_state_value(self, key: str) -> object:
        return self.core.base_services.state.get_state_value(key)

    @router.get("/{key}")
    async def get_state_value_key(self, key: str) -> State:
        return await self.core.db.state.get(key)
