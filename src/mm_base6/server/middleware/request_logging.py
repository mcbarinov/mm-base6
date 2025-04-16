import logging
import time
from collections.abc import Awaitable, Callable
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import Request, Response
from mm_std import str_starts_with_any
from rich.logging import RichHandler
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from mm_base6.core.logger import ExtraFormatter


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        access_log_path: Path,
        developer_console: bool = False,
    ) -> None:
        super().__init__(app)

        self.access_logger = logging.getLogger("access")
        self.access_logger.setLevel(logging.INFO)
        self.access_logger.propagate = False
        self.access_logger.handlers.clear()

        file_handler = RotatingFileHandler(access_log_path, maxBytes=10 * 1024 * 1024, backupCount=1)
        file_handler.setFormatter(
            ExtraFormatter("{asctime} - {name} - {levelname} - {message}", datefmt="%Y-%m-%d %H:%M:%S", style="{")
        )

        console_handler: logging.Handler
        if developer_console:
            console_handler = RichHandler(rich_tracebacks=True, show_time=True, show_level=True, show_path=False)
            formatter = ExtraFormatter("{name} {message}", style="{")
        else:
            console_handler = logging.StreamHandler()
            formatter = ExtraFormatter("{asctime} - {name} - {levelname} - {message}", datefmt="%Y-%m-%d %H:%M:%S", style="{")
        console_handler.setFormatter(formatter)

        self.access_logger.addHandler(file_handler)
        self.access_logger.addHandler(console_handler)

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        start_time = time.perf_counter()
        response = await call_next(request)
        elapsed = (time.perf_counter() - start_time) * 1000
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path
        if not str_starts_with_any(path, ["/assets/", "/favicon.ico"]):
            self.access_logger.info(
                "request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "elapsed_ms": round(elapsed, 2),
                    "client_ip": client_ip,
                },
            )

        return response
