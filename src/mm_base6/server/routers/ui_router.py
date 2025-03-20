from typing import Annotated, cast

from fastapi import APIRouter, Form, Query
from starlette.responses import HTMLResponse, RedirectResponse

from mm_base6.server.deps import BaseCoreDep, FormDep, RenderDep
from mm_base6.server.utils import redirect

router: APIRouter = APIRouter(prefix="/system", include_in_schema=False)


# PAGES
@router.get("/")
async def system_page(render: RenderDep, core: BaseCoreDep) -> HTMLResponse:
    has_telegram_settings = core.system_service.has_telegram_settings()
    has_proxies_settings = core.system_service.has_proxies_settings()
    return await render.html(
        "system.j2",
        stats=await core.system_service.get_stats(),
        has_telegram_settings=has_telegram_settings,
        has_proxies_settings=has_proxies_settings,
    )


@router.get("/dconfigs")
async def dconfigs_page(render: RenderDep, core: BaseCoreDep) -> HTMLResponse:
    return await render.html("dconfigs.j2", info=core.system_service.get_dconfig_info())


@router.get("/dconfigs/toml")
async def dconfigs_toml_page(render: RenderDep, core: BaseCoreDep) -> HTMLResponse:
    return await render.html("dconfigs_toml.j2", toml_str=core.system_service.export_dconfig_as_toml())


@router.get("/dconfigs/multiline/{key:str}")
async def dconfigs_multiline_page(render: RenderDep, core: BaseCoreDep, key: str) -> HTMLResponse:
    return await render.html("dconfigs_multiline.j2", dconfig=core.dconfig, key=key)


@router.get("/dvalues")
async def dvalues_page(render: RenderDep, core: BaseCoreDep) -> HTMLResponse:
    return await render.html("dvalues.j2", info=core.system_service.get_dvalue_info())


@router.get("/dvalues/{key:str}")
async def update_dvalue_page(render: RenderDep, core: BaseCoreDep, key: str) -> HTMLResponse:
    return await render.html("dvalues_update.j2", value=core.system_service.export_dvalue_field_as_toml(key), key=key)


@router.get("/dlogs")
async def dlogs_page(
    render: RenderDep, core: BaseCoreDep, category: Annotated[str | None, Query()] = None, limit: Annotated[int, Query()] = 100
) -> HTMLResponse:
    category_stats = await core.system_service.get_dlog_category_stats()
    query = {"category": category} if category else {}
    dlogs = await core.db.dlog.find(query, "-created_at", limit)
    form = {"category": category, "limit": limit}
    all_count = await core.db.dlog.count({})
    return await render.html("dlogs.j2", dlogs=dlogs, category_stats=category_stats, form=form, all_count=all_count)


# ACTIONS


@router.post("/dconfigs")
async def update_dconfig(render: RenderDep, core: BaseCoreDep, form: FormDep) -> RedirectResponse:
    data = cast(dict[str, str], form)
    await core.system_service.update_dconfig(data)
    render.flash("dconfigs updated successfully")
    return redirect("/system/dconfigs")


@router.post("/dconfigs/multiline/{key:str}")
async def update_dconfig_multiline(
    render: RenderDep, core: BaseCoreDep, key: str, value: Annotated[str, Form()]
) -> RedirectResponse:
    await core.system_service.update_dconfig({key: value})
    render.flash("dconfig updated successfully")
    return redirect("/system/dconfigs")


@router.post("/dconfigs/toml")
async def update_dconfig_from_toml(render: RenderDep, core: BaseCoreDep, value: Annotated[str, Form()]) -> RedirectResponse:
    await core.system_service.update_dconfig_from_toml(value)
    render.flash("dconfigs updated successfully")
    return redirect("/system/dconfigs")


@router.post("/dvalues/{key:str}")
async def update_dvalue(render: RenderDep, core: BaseCoreDep, key: str, value: Annotated[str, Form()]) -> RedirectResponse:
    await core.system_service.update_dvalue_field(key, value)
    render.flash("dvalue updated successfully")
    return redirect("/system/dvalues")
