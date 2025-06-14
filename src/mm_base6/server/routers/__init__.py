from fastapi import APIRouter

from . import (
    api_method,
    auth,
    event,
    settings,
    state,
    system,
    ui,
)

base_router = APIRouter()
base_router.include_router(auth.router)
base_router.include_router(api_method.router)
base_router.include_router(ui.router)
base_router.include_router(settings.router)
base_router.include_router(state.router)
base_router.include_router(event.router)
base_router.include_router(system.router)
