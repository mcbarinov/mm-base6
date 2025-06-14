import asyncio
import logging
import time
from typing import Annotated

from fastapi import APIRouter, File, UploadFile
from mm_result import Result

from app.core.types import AppView
from mm_base6 import UserError, cbv

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/misc", tags=["misc"])


@cbv(router)
class CBV(AppView):
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
        counter = self.core.services.misc.increment_counter()
        logger.info("sleep_seconds: %d, perf_counter=%s, counter=%s", seconds, time.perf_counter() - start, counter)
        return {"sleep_seconds": seconds, "counter": counter, "perf_counter": time.perf_counter() - start}

    @router.get("/result-ok")
    async def result_ok(self) -> Result[str]:
        return Result.ok("it works")

    @router.get("/result-err")
    async def result_err(self) -> Result[str]:
        return Result.ok("bla bla", extra={"logs": ["ssss", 123]})

    @router.post("/upload")
    async def upload(self, file: Annotated[UploadFile, File()]) -> dict[str, str]:
        content = await file.read()
        text_content = content.decode("utf-8")
        return {"text_content": text_content}

    @router.post("/update-state-value")
    async def update_state_value(self) -> int:
        return await self.core.services.misc.update_state_value()
