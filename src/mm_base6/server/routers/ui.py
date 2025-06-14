from typing import Annotated, cast

from fastapi import APIRouter, Form, Query
from starlette.responses import HTMLResponse, RedirectResponse

from mm_base6.server.cbv import cbv
from mm_base6.server.deps import InternalView
from mm_base6.server.utils import redirect

router: APIRouter = APIRouter(prefix="/system", include_in_schema=False)


@cbv(router)
class PageCBV(InternalView):
    @router.get("/")
    async def system_page(self) -> HTMLResponse:
        telegram_message_settings = self.core.base_services.telegram.get_message_settings()
        telegram_bot_settings = self.core.base_services.telegram.get_bot_settings()
        logfile_app_size = await self.core.base_services.logfile.get_logfile_size("app")
        logfile_access_size = await self.core.base_services.logfile.get_logfile_size("access")
        stats = await self.core.base_services.stat.get_stats(logfile_app_size, logfile_access_size)
        return await self.render.html(
            "system.j2",
            stats=stats,
            telegram_message_settings=telegram_message_settings,
            telegram_bot_settings=telegram_bot_settings,
            telegram_bot=self.telegram_bot,
        )

    @router.get("/settings")
    async def settings(self) -> HTMLResponse:
        return await self.render.html("settings.j2", info=self.core.base_services.settings.get_settings_info())

    @router.get("/settings/toml")
    async def settings_toml(self) -> HTMLResponse:
        return await self.render.html("settings_toml.j2", toml_str=self.core.base_services.settings.export_as_toml())

    @router.get("/settings/multiline/{key:str}")
    async def settings_multiline(self, key: str) -> HTMLResponse:
        return await self.render.html("settings_multiline.j2", key=key)

    @router.get("/state")
    async def state_values(self) -> HTMLResponse:
        return await self.render.html("state.j2", info=self.core.base_services.state.get_state_info())

    @router.get("/state/{key:str}")
    async def update_state_value(self, key: str) -> HTMLResponse:
        return await self.render.html(
            "state_update.j2", value=self.core.base_services.state.export_state_value_as_toml(key), key=key
        )

    @router.get("/events")
    async def events(
        self, event_type: Annotated[str | None, Query(alias="type")] = None, limit: Annotated[int, Query()] = 100
    ) -> HTMLResponse:
        type_stats = await self.core.base_services.event.get_event_type_stats()
        query = {"type": event_type} if event_type else {}
        events = await self.core.db.event.find(query, "-created_at", limit)
        form = {"type": event_type, "limit": limit}
        all_count = await self.core.db.event.count({})
        return await self.render.html("events.j2", events=events, type_stats=type_stats, form=form, all_count=all_count)


@cbv(router)
class ActionCBV(InternalView):
    @router.post("/settings")
    async def update_settings(self) -> RedirectResponse:
        data = cast(dict[str, str], self.form_data)
        await self.core.base_services.settings.update_configs(data)
        self.render.flash("settings updated successfully")
        return redirect("/system/settings")

    @router.post("/settings/multiline/{key:str}")
    async def update_settings_multiline(self, key: str, value: Annotated[str, Form()]) -> RedirectResponse:
        await self.core.base_services.settings.update_configs({key: value})
        self.render.flash("setting updated successfully")
        return redirect("/system/settings")

    @router.post("/settings/toml")
    async def update_settings_from_toml(self, value: Annotated[str, Form()]) -> RedirectResponse:
        await self.core.base_services.settings.update_from_toml(value)
        self.render.flash("settings updated successfully")
        return redirect("/system/settings")

    @router.post("/state/{key:str}")
    async def update_state_value(self, key: str, value: Annotated[str, Form()]) -> RedirectResponse:
        await self.core.base_services.state.update_state_value(key, value)
        self.render.flash("state value updated successfully")
        return redirect("/system/state")
