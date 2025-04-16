from typing import Annotated, cast

from fastapi import APIRouter, Form, Query
from starlette.responses import HTMLResponse, RedirectResponse

from mm_base6.server.cbv import cbv
from mm_base6.server.deps import BaseView
from mm_base6.server.utils import redirect

router: APIRouter = APIRouter(prefix="/system", include_in_schema=False)


@cbv(router)
class PageCBV(BaseView):
    @router.get("/")
    async def system_page(self) -> HTMLResponse:
        has_telegram_settings = self.core.system_service.has_telegram_settings()
        has_proxies_settings = self.core.system_service.has_proxies_settings()
        return await self.render.html(
            "system.j2",
            stats=await self.core.system_service.get_stats(),
            has_telegram_settings=has_telegram_settings,
            has_proxies_settings=has_proxies_settings,
        )

    @router.get("/dynamic-configs")
    async def dynamic_configs(self) -> HTMLResponse:
        return await self.render.html("dynamic_configs.j2", info=self.core.system_service.get_dynamic_configs_info())

    @router.get("/dynamic-configs/toml")
    async def dynamic_configs_toml(self) -> HTMLResponse:
        return await self.render.html(
            "dynamic_configs_toml.j2", toml_str=self.core.system_service.export_dynamic_configs_as_toml()
        )

    @router.get("/dynamic-configs/multiline/{key:str}")
    async def dynamic_configs_multiline(self, key: str) -> HTMLResponse:
        return await self.render.html("dynamic_configs_multiline.j2", key=key)

    @router.get("/dynamic-values")
    async def dynamic_values(self) -> HTMLResponse:
        return await self.render.html("dynamic_values.j2", info=self.core.system_service.get_dynamic_values_info())

    @router.get("/dynamic-values/{key:str}")
    async def update_dynamic_value(self, key: str) -> HTMLResponse:
        return await self.render.html(
            "dynamic_values_update.j2", value=self.core.system_service.export_dynamic_value_as_toml(key), key=key
        )

    @router.get("/system-logs")
    async def system_logs(
        self, category: Annotated[str | None, Query()] = None, limit: Annotated[int, Query()] = 100
    ) -> HTMLResponse:
        category_stats = await self.core.system_service.get_system_log_category_stats()
        query = {"category": category} if category else {}
        logs = await self.core.db.system_log.find(query, "-created_at", limit)
        form = {"category": category, "limit": limit}
        all_count = await self.core.db.system_log.count({})
        return await self.render.html("system_logs.j2", logs=logs, category_stats=category_stats, form=form, all_count=all_count)


@cbv(router)
class ActionCBV(BaseView):
    @router.post("/dynamic-configs")
    async def update_dynamic_configs(self) -> RedirectResponse:
        data = cast(dict[str, str], self.form_data)
        await self.core.system_service.update_dynamic_config(data)
        self.render.flash("dynamic configs updated successfully")
        return redirect("/system/dynamic-configs")

    @router.post("/dynamic-configs/multiline/{key:str}")
    async def update_dynamic_config_multiline(self, key: str, value: Annotated[str, Form()]) -> RedirectResponse:
        await self.core.system_service.update_dynamic_config({key: value})
        self.render.flash("dynamic config updated successfully")
        return redirect("/system/dynamic-configs")

    @router.post("/dynamic-configs/toml")
    async def update_dynamic_config_from_toml(self, value: Annotated[str, Form()]) -> RedirectResponse:
        await self.core.system_service.update_dynamic_configs_from_toml(value)
        self.render.flash("dynamic configs updated successfully")
        return redirect("/system/dynamic-configs")

    @router.post("/dynamic-values/{key:str}")
    async def update_dynamic_value(self, key: str, value: Annotated[str, Form()]) -> RedirectResponse:
        await self.core.system_service.update_dynamic_value(key, value)
        self.render.flash("dynamic value updated successfully")
        return redirect("/system/dynamic-values")
