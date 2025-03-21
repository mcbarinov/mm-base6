from typing import Annotated

from bson import ObjectId
from fastapi import APIRouter, Form
from fastapi.params import Query
from mm_base6 import RenderDep, redirect
from starlette.responses import HTMLResponse, RedirectResponse

from app.core.db import DataStatus
from app.server.deps import CoreDep

router = APIRouter(include_in_schema=False)


@router.get("/")
async def index_page(render: RenderDep) -> HTMLResponse:
    return await render.html("index.j2")


@router.get("/data")
async def data_page(
    render: RenderDep,
    core: CoreDep,
    status: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query()] = 100,
) -> HTMLResponse:
    query = {"status": status} if status else {}
    data = await core.db.data.find(query, "-created_at", limit)
    statuses = list(DataStatus)
    return await render.html("data.j2", data_list=data, statuses=statuses, form={"status": status, "limit": limit})


@router.get("/misc")
async def misc_page(render: RenderDep) -> HTMLResponse:
    return await render.html("misc.j2", zero=0)


# ACTIONS
@router.post("/data/{id}/inc")
async def inc_data(render: RenderDep, core: CoreDep, id: ObjectId, value: Annotated[int, Form()]) -> RedirectResponse:
    await core.db.data.update_one({"_id": id}, {"$inc": {"value": value}})
    render.flash(f"Data {id} incremented by {value}")
    return redirect("/data")
