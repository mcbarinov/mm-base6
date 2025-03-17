from bson import ObjectId
from fastapi import APIRouter
from mm_mongo import MongoDeleteResult, MongoInsertManyResult, MongoInsertOneResult, MongoUpdateResult

from app.core.db import Data
from app.server.deps import CoreDep

router = APIRouter(prefix="/api/data", tags=["data"])


@router.post("/generate-one")
async def generate_one(core: CoreDep) -> MongoInsertOneResult:
    return await core.data_service.generate_one()


@router.post("/generate-many")
async def generate_many(core: CoreDep) -> MongoInsertManyResult:
    return await core.data_service.generate_many()


@router.get("/{id}")
async def get_data(core: CoreDep, id: ObjectId) -> Data:
    return await core.db.data.get(id)


@router.post("/{id}/inc")
async def inc_data(core: CoreDep, id: ObjectId, value: int | None = None) -> MongoUpdateResult:
    return await core.db.data.update(id, {"$inc": {"value": value or 1}})


@router.delete("/{id}")
async def delete_data(core: CoreDep, id: ObjectId) -> MongoDeleteResult:
    return await core.db.data.delete(id)
