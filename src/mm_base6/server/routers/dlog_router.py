from bson import ObjectId
from fastapi import APIRouter
from mm_mongo import MongoDeleteResult

from mm_base6.core.db import DLog
from mm_base6.server.deps import BaseCoreDep

router: APIRouter = APIRouter(prefix="/api/system/dlogs", tags=["system"])


@router.get("/{id}")
async def get_dlog(core: BaseCoreDep, id: ObjectId) -> DLog:
    return await core.db.dlog.get(id)


@router.delete("/{id}")
async def delete_dlog(core: BaseCoreDep, id: ObjectId) -> MongoDeleteResult:
    return await core.db.dlog.delete(id)


@router.delete("/category/{category}")
async def delete_by_category(core: BaseCoreDep, category: str) -> MongoDeleteResult:
    return await core.db.dlog.delete_many({"category": category})


@router.delete("")
async def delete_all_dlogs(core: BaseCoreDep) -> MongoDeleteResult:
    core.logger.debug("delete_all_dlogs called")
    return await core.db.dlog.delete_many({})
