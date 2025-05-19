from app import settings, telegram
from app.core.core import Core
from app.server import jinja
from mm_base6 import run

run(
    core_config=settings.core_config,
    server_config=settings.server_config,
    core_class=Core,
    telegram_handlers=telegram.handlers,
    router=settings.get_router(),
    jinja_config=jinja.jinja_config,
    host="0.0.0.0",  # noqa: S104 # nosec
    port=3000,
    uvicorn_log_level="warning",
)
