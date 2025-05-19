import logging
import random

from bson import ObjectId
from mm_mongo import MongoInsertManyResult, MongoInsertOneResult
from mm_std import http_request

from app.core.db import Data, DataStatus
from app.core.types_ import AppService, AppServiceParams

logger = logging.getLogger(__name__)


class DataService(AppService):
    def __init__(self, base_params: AppServiceParams) -> None:
        super().__init__(base_params)

    async def generate_one(self) -> MongoInsertOneResult:
        status = random.choice(list(DataStatus))
        value = random.randint(0, 1_000_000)

        logger.debug("generate_one", extra={"status": status, "value": value})

        return await self.db.data.insert_one(Data(id=ObjectId(), status=status, value=value))

    async def generate_many(self) -> MongoInsertManyResult:
        res = await http_request("https://httpbin.org/get")
        await self.system_log("generate_many", {"res": res.parse_json_body(none_on_error=True), "large-data": "abc" * 100})
        await self.system_log("ddd", self.dynamic_configs.telegram_token)
        await self.send_telegram_message("generate_many")
        new_data_list = [
            Data(id=ObjectId(), status=random.choice(list(DataStatus)), value=random.randint(0, 1_000_000)) for _ in range(10)
        ]
        return await self.db.data.insert_many(new_data_list)
