import logging
from typing import cast

import mm_telegram
from mm_std import Result
from mm_telegram import TelegramBot
from pydantic import BaseModel

from mm_base6.core.dynamic_config import DynamicConfigStorage
from mm_base6.core.errors import UserError
from mm_base6.core.services.system import SystemService


class TelegramMessageSettings(BaseModel):
    token: str
    chat_id: int


class TelegramBotSettings(BaseModel):
    token: str
    admins: list[int]
    auto_start: bool


logger = logging.getLogger(__name__)


class TelegramService:
    def __init__(self, system_service: SystemService) -> None:
        self.system_service = system_service

    def get_message_settings(self) -> TelegramMessageSettings | None:
        try:
            token = cast(str, DynamicConfigStorage.storage.get("telegram_token"))
            chat_id = cast(int, DynamicConfigStorage.storage.get("telegram_chat_id"))
            if ":" not in token or chat_id == 0:
                return None
            return TelegramMessageSettings(token=token, chat_id=chat_id)
        except Exception:
            return None

    def get_bot_settings(self) -> TelegramBotSettings | None:
        try:
            token = cast(str, DynamicConfigStorage.storage.get("telegram_token"))
            admins_str = cast(str, DynamicConfigStorage.storage.get("telegram_bot_admins"))
            admins = [int(admin.strip()) for admin in admins_str.split(",") if admin.strip()]
            auto_start = False
            if "telegram_bot_auto_start" in DynamicConfigStorage.storage:
                auto_start = cast(bool, DynamicConfigStorage.storage.get("telegram_bot_auto_start"))
            if ":" not in token or not admins:
                return None
            return TelegramBotSettings(token=token, admins=admins, auto_start=auto_start)
        except Exception:
            return None

    async def send_message(self, message: str) -> Result[list[int]]:
        # TODO: run it in a separate thread
        settings = self.get_message_settings()
        if settings is None:
            return Result.err("telegram_token or chat_id is not set")

        res = await mm_telegram.send_message(settings.token, settings.chat_id, message)
        if res.is_err():
            await self.system_service.system_log(
                "send_telegram_message", {"error": res.unwrap_error(), "message": message, "data": res.extra}
            )
            logger.error("send_telegram_message error: %s", res.unwrap_error())
        return res

    async def start_bot(self, bot: TelegramBot) -> bool:
        settings = self.get_bot_settings()
        if settings is None:
            raise UserError("Telegram settings not found: telegram_token, telegram_bot_admins")

        await bot.start(settings.token, settings.admins)
        return True

    async def shutdown_bot(self, bot: TelegramBot) -> bool:
        settings = self.get_bot_settings()
        if settings is None:
            raise UserError("Telegram settings not found: telegram_token, telegram_bot_admins")

        await bot.shutdown()
        return True
