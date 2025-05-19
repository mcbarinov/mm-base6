from bson import ObjectId
from fastapi import APIRouter
from mm_mongo import MongoDeleteResult

from mm_base6.core.db import SystemLog
from mm_base6.server.cbv import cbv
from mm_base6.server.deps import BaseView

router: APIRouter = APIRouter(prefix="/api/system/system-logs", tags=["system"])


@cbv(router)
class CBV(BaseView):
    @router.get("/{id}")
    async def get_system_log(self, id: ObjectId) -> SystemLog:
        return await self.core.db.system_log.get(id)

    @router.delete("/{id}")
    async def delete_system_log(self, id: ObjectId) -> MongoDeleteResult:
        return await self.core.db.system_log.delete(id)

    @router.delete("/category/{category}")
    async def delete_by_category(self, category: str) -> MongoDeleteResult:
        return await self.core.db.system_log.delete_many({"category": category})

    @router.delete("/")
    async def delete_all_system_logs(self) -> MongoDeleteResult:
        return await self.core.db.system_log.delete_many({})
