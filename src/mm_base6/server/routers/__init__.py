from fastapi import APIRouter

from mm_base6.server.routers import (
    api_method_router,
    auth_router,
    dconfig_router,
    dlog_router,
    dvalue_router,
    system_router,
    ui_router,
)

base_router = APIRouter()
base_router.include_router(auth_router.router)
base_router.include_router(api_method_router.router)
base_router.include_router(ui_router.router)
base_router.include_router(dconfig_router.router)
base_router.include_router(dvalue_router.router)
base_router.include_router(dlog_router.router)
base_router.include_router(system_router.router)
