from fastapi import APIRouter

from . import (
    api_method,
    auth,
    dynamic_config,
    dynamic_value,
    system,
    system_log,
    ui,
)

base_router = APIRouter()
base_router.include_router(auth.router)
base_router.include_router(api_method.router)
base_router.include_router(ui.router)
base_router.include_router(dynamic_config.router)
base_router.include_router(dynamic_value.router)
base_router.include_router(system_log.router)
base_router.include_router(system.router)
