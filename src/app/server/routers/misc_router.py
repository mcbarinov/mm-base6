import asyncio
import logging
import time
from typing import Annotated

from fastapi import APIRouter, File, UploadFile
from mm_std import Result

from app.server.deps import View
from mm_base6 import UserError, cbv

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/misc", tags=["misc"])


@cbv(router)
class CBV(View):
    @router.get("/user-error")
    async def user_error(self) -> str:
        raise UserError("user bla bla bla")

    @router.get("/runtime-error")
    async def runtime_error(self) -> str:
        raise RuntimeError("runtime bla bla bla")

    @router.get("/sleep/{seconds}")
    async def sleep_seconds(self, seconds: int) -> dict[str, object]:
        start = time.perf_counter()
        logger.info("sleep_seconds called: %d", seconds)
        await asyncio.sleep(seconds)
        counter = self.core.misc_service.increment_counter()
        logger.info("sleep_seconds: %d, perf_counter=%s, counter=%s", seconds, time.perf_counter() - start, counter)
        return {"sleep_seconds": seconds, "counter": counter, "perf_counter": time.perf_counter() - start}

    @router.get("/result-ok")
    async def result_ok(self) -> Result[str]:
        return Result.success("it works")

    @router.get("/result-err")
    async def result_err(self) -> Result[str]:
        return Result.failure("bla bla", extra={"logs": ["ssss", 123]})

    @router.post("/upload")
    async def upload(self, file: Annotated[UploadFile, File()]) -> dict[str, str]:
        content = await file.read()
        text_content = content.decode("utf-8")
        return {"text_content": text_content}

    @router.post("/update-dynamic-value")
    async def update_dynamic_value(self) -> int:
        return await self.core.misc_service.update_dynamic_value()
