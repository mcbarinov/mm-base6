from typing import Annotated

from fastapi import APIRouter, Form
from starlette import status
from starlette.responses import HTMLResponse, RedirectResponse

from mm_base6.server.cbv import cbv
from mm_base6.server.deps import InternalView
from mm_base6.server.middleware.auth import ACCESS_TOKEN_NAME

router: APIRouter = APIRouter(prefix="/auth", include_in_schema=False)


@cbv(router)
class CBV(InternalView):
    @router.get("/login")
    async def login_page(self) -> HTMLResponse:
        return await self.render.html("login.j2")

    @router.post("/login")
    async def login(self, token: Annotated[str, Form()]) -> RedirectResponse:
        response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            ACCESS_TOKEN_NAME, value=token, domain=self.server_config.domain, httponly=True, max_age=60 * 60 * 24 * 30
        )
        return response

    @router.get("/logout")
    async def logout(self) -> RedirectResponse:
        response = RedirectResponse(url="/")
        response.delete_cookie(ACCESS_TOKEN_NAME, domain=self.server_config.domain)
        return response
