from typing import Annotated

from bson import ObjectId
from fastapi import APIRouter, Form
from fastapi.params import Query
from starlette.responses import HTMLResponse, RedirectResponse

from app.core.db import DataStatus
from app.core.types import AppView
from mm_base6 import cbv, redirect

router = APIRouter(include_in_schema=False)


@cbv(router)
class PageCBV(AppView):
    @router.get("/")
    async def index(self) -> HTMLResponse:
        return await self.render.html("index.j2")

    @router.get("/data")
    async def data(self, status: Annotated[str | None, Query()] = None, limit: Annotated[int, Query()] = 100) -> HTMLResponse:
        query = {"status": status} if status else {}
        data = await self.core.db.data.find(query, "-created_at", limit)
        statuses = list(DataStatus)
        return await self.render.html("data.j2", data_list=data, statuses=statuses, form={"status": status, "limit": limit})

    @router.get("/misc")
    async def misc(self) -> HTMLResponse:
        counter = self.core.services.misc.counter.get()
        return await self.render.html("misc.j2", zero=0, counter=counter)


@cbv(router)
class ActionCBV(AppView):
    @router.post("/data/{id}/inc")
    async def inc_data(self, id: ObjectId, value: Annotated[int, Form()]) -> RedirectResponse:
        await self.core.db.data.update_one({"_id": id}, {"$inc": {"value": value}})
        self.render.flash(f"Data {id} incremented by {value}")
        return redirect("/data")
