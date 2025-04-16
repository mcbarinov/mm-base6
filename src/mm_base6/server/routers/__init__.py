from fastapi import APIRouter

from mm_base6.server.routers import (
    api_method_router,
    auth_router,
    dynamic_config_router,
    dynamic_value_router,
    system_log_router,
    system_router,
    ui_router,
)

base_router = APIRouter()
base_router.include_router(auth_router.router)
base_router.include_router(api_method_router.router)
base_router.include_router(ui_router.router)
base_router.include_router(dynamic_config_router.router)
base_router.include_router(dynamic_value_router.router)
base_router.include_router(system_log_router.router)
base_router.include_router(system_router.router)
