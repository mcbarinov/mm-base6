from typing import cast

from mm_telegram import TelegramHandler
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from app.core.types import AppCore


async def data_generate_one(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    core = cast(AppCore, context.bot_data.get("core"))
    res = await core.services.data.generate_one()
    if update.effective_chat is not None:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"result: {res}")


async def data_generate_many(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    core = cast(AppCore, context.bot_data.get("core"))
    res = await core.services.data.generate_many()
    if update.effective_chat is not None:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"result: {res}")


handlers: list[TelegramHandler] = [
    CommandHandler("data_generate_one", data_generate_one),
    CommandHandler("data_generate_many", data_generate_many),
]
