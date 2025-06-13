from bson import ObjectId
from fastapi import APIRouter
from mm_mongo import MongoDeleteResult, MongoInsertManyResult, MongoInsertOneResult, MongoUpdateResult

from app.core.db import Data
from app.core.types import AppView
from mm_base6 import cbv

router = APIRouter(prefix="/api/data", tags=["data"])


@cbv(router)
class CBV(AppView):
    @router.post("/generate-one")
    async def generate_one(self) -> MongoInsertOneResult:
        return await self.core.services.data.generate_one()

    @router.post("/generate-many")
    async def generate_many(self) -> MongoInsertManyResult:
        return await self.core.services.data.generate_many()

    @router.get("/{id}")
    async def get_data(self, id: ObjectId) -> Data:
        return await self.core.db.data.get(id)

    @router.post("/{id}/inc")
    async def inc_data(self, id: ObjectId, value: int | None = None) -> MongoUpdateResult:
        return await self.core.db.data.update(id, {"$inc": {"value": value or 1}})

    @router.delete("/{id}")
    async def delete_data(self, id: ObjectId) -> MongoDeleteResult:
        return await self.core.db.data.delete(id)
