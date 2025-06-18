import logging
import random

from bson import ObjectId
from mm_http import http_request
from mm_mongo import MongoInsertManyResult, MongoInsertOneResult

from app.core.db import Data, DataStatus
from app.core.types import AppCore
from mm_base6 import Service

logger = logging.getLogger(__name__)


class DataService(Service):
    core: AppCore

    async def generate_one(self) -> MongoInsertOneResult:
        status = random.choice(list(DataStatus))
        value = random.randint(0, 1_000_000)
        self.core.services.misc.increment_counter()
        logger.debug("generate_one", extra={"status": status, "value": value})

        return await self.core.db.data.insert_one(Data(id=ObjectId(), status=status, value=value))

    async def generate_many(self) -> MongoInsertManyResult:
        res = await http_request("https://httpbin.org/get")
        await self.core.base_services.event.event(
            "generate_many", {"res": res.parse_json_body(none_on_error=True), "large-data": "abc" * 100}
        )
        await self.core.base_services.event.event("ddd", self.core.settings.telegram_token)
        await self.core.base_services.telegram.send_message("generate_many")
        new_data_list = [
            Data(id=ObjectId(), status=random.choice(list(DataStatus)), value=random.randint(0, 1_000_000)) for _ in range(10)
        ]
        return await self.core.db.data.insert_many(new_data_list)
