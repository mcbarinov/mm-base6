from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from mm_base6.server.utils import redirect

ACCESS_TOKEN_NAME = "access-token"  # noqa: S105 # nosec


class AccessTokenMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, access_token: str) -> None:
        super().__init__(app)
        self.access_token = access_token

    async def dispatch(self, req: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        if req.url.path.startswith("/auth/"):
            return await call_next(req)

        success = (
            req.query_params.get(ACCESS_TOKEN_NAME) == self.access_token
            or req.headers.get(ACCESS_TOKEN_NAME) == self.access_token
            or req.cookies.get(ACCESS_TOKEN_NAME) == self.access_token
        )
        if success:
            return await call_next(req)

        if req.url.path.startswith("/api/"):
            return JSONResponse({"error": "access denied"}, status_code=401)
        return redirect("/auth/login")
