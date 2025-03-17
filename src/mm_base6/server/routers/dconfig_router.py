from fastapi import APIRouter
from starlette.responses import PlainTextResponse

from mm_base6.server.deps import BaseCoreDep

router: APIRouter = APIRouter(prefix="/api/system/dconfigs", tags=["system"])


@router.get("/toml", response_class=PlainTextResponse)
def get_dconfigs_toml(core: BaseCoreDep) -> str:
    return core.system_service.export_dconfig_as_toml()
