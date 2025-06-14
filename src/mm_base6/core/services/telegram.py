import logging

import mm_telegram
from mm_result import Result
from mm_telegram import TelegramBot
from pydantic import BaseModel

from mm_base6.core.errors import UserError
from mm_base6.core.services.event import EventService
from mm_base6.core.services.settings import SettingsService


class TelegramMessageSettings(BaseModel):
    token: str
    chat_id: int


class TelegramBotSettings(BaseModel):
    token: str
    admins: list[int]
    auto_start: bool


logger = logging.getLogger(__name__)


class TelegramService:
    """Service for Telegram bot integration and message sending.

    Provides functionality for both message sending to specific chats and
    bot management with admin controls. Automatically extracts configuration
    from SettingsService and handles error reporting through EventService.
    Supports both one-off messaging and persistent bot operations.
    """

    def __init__(self, event_service: EventService, settings_service: SettingsService) -> None:
        self.event_service = event_service
        self.settings_service = settings_service

    def get_message_settings(self) -> TelegramMessageSettings | None:
        """Extract message sending configuration from settings.

        Returns:
            Configuration for sending messages, or None if incomplete/invalid
        """
        try:
            token = str(self.settings_service.get_setting("telegram_token"))
            chat_id_obj = self.settings_service.get_setting("telegram_chat_id")
            chat_id = int(chat_id_obj) if isinstance(chat_id_obj, (int, str)) else 0
            if ":" not in token or chat_id == 0:
                return None
            return TelegramMessageSettings(token=token, chat_id=chat_id)
        except (AttributeError, KeyError, ValueError, TypeError):
            return None

    def get_bot_settings(self) -> TelegramBotSettings | None:
        """Extract bot configuration from settings.

        Returns:
            Configuration for bot operations, or None if incomplete/invalid
        """
        try:
            token = str(self.settings_service.get_setting("telegram_token"))
            admins_str = str(self.settings_service.get_setting("telegram_bot_admins"))
            admins = [int(admin.strip()) for admin in admins_str.split(",") if admin.strip()]
            auto_start_obj = self.settings_service.get_setting("telegram_bot_auto_start")
            auto_start = bool(auto_start_obj) if isinstance(auto_start_obj, (bool, int, str)) else False
            if ":" not in token or not admins:
                return None
            return TelegramBotSettings(token=token, admins=admins, auto_start=auto_start)
        except (AttributeError, KeyError, ValueError, TypeError):
            return None

    async def send_message(self, message: str) -> Result[list[int]]:
        """Send a message to the configured Telegram chat.

        Uses settings for token and chat_id. Logs errors to EventService
        and returns detailed error information for debugging.

        Args:
            message: Text message to send

        Returns:
            Result containing message IDs on success, or error details on failure
        """
        # TODO: run it in a separate thread
        settings = self.get_message_settings()
        if settings is None:
            return Result.err("telegram_token or chat_id is not set")

        res = await mm_telegram.send_message(settings.token, settings.chat_id, message)
        if res.is_err():
            await self.event_service.event(
                "send_telegram_message", {"error": res.unwrap_err(), "message": message, "data": res.extra}
            )
            logger.error("send_telegram_message error: %s", res.unwrap_err())
        return res

    async def start_bot(self, bot: TelegramBot) -> bool:
        """Start a Telegram bot with admin configuration from settings.

        Args:
            bot: TelegramBot instance to start

        Returns:
            True on successful start

        Raises:
            UserError: If required settings are missing or invalid
        """
        settings = self.get_bot_settings()
        if settings is None:
            raise UserError("Telegram settings not found: telegram_token, telegram_bot_admins")

        await bot.start(settings.token, settings.admins)
        return True

    async def shutdown_bot(self, bot: TelegramBot) -> bool:
        """Shutdown a running Telegram bot.

        Args:
            bot: TelegramBot instance to shutdown

        Returns:
            True on successful shutdown

        Raises:
            UserError: If required settings are missing or invalid
        """
        settings = self.get_bot_settings()
        if settings is None:
            raise UserError("Telegram settings not found: telegram_token, telegram_bot_admins")

        await bot.shutdown()
        return True
