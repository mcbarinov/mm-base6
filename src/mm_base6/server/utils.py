import importlib.metadata

from starlette.responses import RedirectResponse
from starlette.status import HTTP_303_SEE_OTHER


def get_package_version(package: str) -> str:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return " unknown"


def redirect(url: str) -> RedirectResponse:
    return RedirectResponse(url, status_code=HTTP_303_SEE_OTHER)
