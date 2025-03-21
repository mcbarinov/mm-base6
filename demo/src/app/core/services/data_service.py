import random

from bson import ObjectId
from mm_mongo import MongoInsertManyResult, MongoInsertOneResult
from mm_std import hr

from app.core.db import Data, DataStatus
from app.core.types_ import AppService, AppServiceParams


class DataService(AppService):
    def __init__(self, base_params: AppServiceParams) -> None:
        super().__init__(base_params)

    async def generate_one(self) -> MongoInsertOneResult:
        status = random.choice(list(DataStatus))
        value = random.randint(0, 1_000_000)

        return await self.db.data.insert_one(Data(id=ObjectId(), status=status, value=value))

    async def generate_many(self) -> MongoInsertManyResult:
        res = hr("https://httpbin.org/get")
        await self.dlog("generate_many", {"res": res.json, "large-data": "abc" * 100})
        await self.dlog("ddd", self.dconfig.telegram_token)
        await self.send_telegram_message("generate_many")
        new_data_list = [
            Data(id=ObjectId(), status=random.choice(list(DataStatus)), value=random.randint(0, 1_000_000)) for _ in range(10)
        ]
        return await self.db.data.insert_many(new_data_list)
