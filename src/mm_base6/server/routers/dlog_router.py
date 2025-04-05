from bson import ObjectId
from fastapi import APIRouter
from mm_mongo import MongoDeleteResult

from mm_base6.core.db import DLog
from mm_base6.server.cbv import cbv
from mm_base6.server.deps import BaseView

router: APIRouter = APIRouter(prefix="/api/system/dlogs", tags=["system"])


@cbv(router)
class CBV(BaseView):
    @router.get("/{id}")
    async def get_dlog(self, id: ObjectId) -> DLog:
        return await self.core.db.dlog.get(id)

    @router.delete("/{id}")
    async def delete_dlog(self, id: ObjectId) -> MongoDeleteResult:
        return await self.core.db.dlog.delete(id)

    @router.delete("/category/{category}")
    async def delete_by_category(self, category: str) -> MongoDeleteResult:
        return await self.core.db.dlog.delete_many({"category": category})

    @router.delete("/")
    async def delete_all_dlogs(self) -> MongoDeleteResult:
        return await self.core.db.dlog.delete_many({})
