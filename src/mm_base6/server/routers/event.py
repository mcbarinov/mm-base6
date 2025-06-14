from bson import ObjectId
from fastapi import APIRouter
from mm_mongo import MongoDeleteResult

from mm_base6.core.db import Event
from mm_base6.server.cbv import cbv
from mm_base6.server.deps import InternalView

router: APIRouter = APIRouter(prefix="/api/system/events", tags=["system"])


@cbv(router)
class CBV(InternalView):
    @router.get("/{id}")
    async def get_event(self, id: ObjectId) -> Event:
        return await self.core.db.event.get(id)

    @router.delete("/{id}")
    async def delete_event(self, id: ObjectId) -> MongoDeleteResult:
        return await self.core.db.event.delete(id)

    @router.delete("/type/{event_type}")
    async def delete_by_type(self, event_type: str) -> MongoDeleteResult:
        return await self.core.db.event.delete_many({"type": event_type})

    @router.delete("/")
    async def delete_all_events(self) -> MongoDeleteResult:
        return await self.core.db.event.delete_many({})
