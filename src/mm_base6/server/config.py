import importlib
import pkgutil
from typing import TYPE_CHECKING

from fastapi import APIRouter
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    pass


class ServerConfig(BaseSettings):
    domain: str
    access_token: str
    use_https: bool = True
    tags: list[str] = Field(default_factory=list)
    main_menu: dict[str, str] = Field(default_factory=dict)
    routers_package: str = "app.server.routers"

    @property
    def tags_metadata(self) -> list[dict[str, str]]:
        app = [{"name": t} for t in self.tags]
        return [*app, {"name": "system"}]

    def get_router(self) -> APIRouter:
        """Automatically scans routers_package and includes all found routers."""
        main_router = APIRouter()

        try:
            package = importlib.import_module(self.routers_package)
            for _, module_name, _ in pkgutil.iter_modules(package.__path__):
                if module_name.startswith("_"):
                    continue

                module = importlib.import_module(f"{self.routers_package}.{module_name}")
                if hasattr(module, "router"):
                    main_router.include_router(module.router)
        except ImportError:
            pass

        return main_router

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
