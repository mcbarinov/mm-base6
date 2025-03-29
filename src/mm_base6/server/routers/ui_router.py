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

    @router.get("/dconfigs")
    async def dconfigs_page(self) -> HTMLResponse:
        return await self.render.html("dconfigs.j2", info=self.core.system_service.get_dconfig_info())

    @router.get("/dconfigs/toml")
    async def dconfigs_toml_page(self) -> HTMLResponse:
        return await self.render.html("dconfigs_toml.j2", toml_str=self.core.system_service.export_dconfig_as_toml())

    @router.get("/dconfigs/multiline/{key:str}")
    async def dconfigs_multiline_page(self, key: str) -> HTMLResponse:
        return await self.render.html("dconfigs_multiline.j2", dconfig=self.core.dconfig, key=key)

    @router.get("/dvalues")
    async def dvalues_page(self) -> HTMLResponse:
        return await self.render.html("dvalues.j2", info=self.core.system_service.get_dvalue_info())

    @router.get("/dvalues/{key:str}")
    async def update_dvalue_page(self, key: str) -> HTMLResponse:
        return await self.render.html(
            "dvalues_update.j2", value=self.core.system_service.export_dvalue_field_as_toml(key), key=key
        )

    @router.get("/dlogs")
    async def dlogs_page(
        self, category: Annotated[str | None, Query()] = None, limit: Annotated[int, Query()] = 100
    ) -> HTMLResponse:
        category_stats = await self.core.system_service.get_dlog_category_stats()
        query = {"category": category} if category else {}
        dlogs = await self.core.db.dlog.find(query, "-created_at", limit)
        form = {"category": category, "limit": limit}
        all_count = await self.core.db.dlog.count({})
        return await self.render.html("dlogs.j2", dlogs=dlogs, category_stats=category_stats, form=form, all_count=all_count)


@cbv(router)
class ActionCBV(BaseView):
    @router.post("/dconfigs")
    async def update_dconfig(self) -> RedirectResponse:
        data = cast(dict[str, str], self.form_data)
        await self.core.system_service.update_dconfig(data)
        self.render.flash("dconfigs updated successfully")
        return redirect("/system/dconfigs")

    @router.post("/dconfigs/multiline/{key:str}")
    async def update_dconfig_multiline(self, key: str, value: Annotated[str, Form()]) -> RedirectResponse:
        await self.core.system_service.update_dconfig({key: value})
        self.render.flash("dconfig updated successfully")
        return redirect("/system/dconfigs")

    @router.post("/dconfigs/toml")
    async def update_dconfig_from_toml(self, value: Annotated[str, Form()]) -> RedirectResponse:
        await self.core.system_service.update_dconfig_from_toml(value)
        self.render.flash("dconfigs updated successfully")
        return redirect("/system/dconfigs")

    @router.post("/dvalues/{key:str}")
    async def update_dvalue(self, key: str, value: Annotated[str, Form()]) -> RedirectResponse:
        await self.core.system_service.update_dvalue_field(key, value)
        self.render.flash("dvalue updated successfully")
        return redirect("/system/dvalues")
