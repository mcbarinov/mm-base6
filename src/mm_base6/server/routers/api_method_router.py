from fastapi import APIRouter
from mm_std import hr
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from mm_base6 import ServerConfig
from mm_base6.server.cbv import cbv
from mm_base6.server.deps import BaseView
from mm_base6.server.middleware.auth import ACCESS_TOKEN_NAME

router: APIRouter = APIRouter(include_in_schema=False)


@cbv(router)
class CBV(BaseView):
    @router.get("/api-post/{url:path}")
    def api_post(self, url: str, request: Request) -> object:
        return _api_method("post", url, self.server_config, request)

    @router.get("/api-delete/{url:path}")
    def api_delete(self, url: str, request: Request) -> object:
        return _api_method("delete", url, self.server_config, request)


def _api_method(method: str, url: str, server_config: ServerConfig, req: Request) -> object:
    base_url = str(req.base_url)
    if not base_url.endswith("/"):
        base_url = base_url + "/"
    url = base_url + "api/" + url
    if server_config.use_https:
        url = url.replace("http://", "https://", 1)
    if req.query_params:
        q = ""
        for k, v in req.query_params.items():
            q += f"{k}={v}&"
        url += f"?{q}"

    headers = {ACCESS_TOKEN_NAME: server_config.access_token}
    res = hr(url, method=method, headers=headers, params=dict(req.query_params), timeout=600)
    if res.content_type and res.content_type.startswith("text/plain"):
        return PlainTextResponse(res.body)
    if res.json:
        return res.json
    return res.body
