from datetime import datetime
from decimal import Decimal
from typing import Annotated

from mm_std import utc_now

from mm_base6 import BaseSettings, BaseState, Config, setting_field, state_field

config = Config(openapi_tags=["data", "misc"], ui_menu={"/data": "data", "/misc": "misc"})


class Settings(BaseSettings):
    proxies_url: Annotated[str, setting_field("http://localhost:8000", "proxies url, each proxy on new line")]
    telegram_token: Annotated[str, setting_field("", "telegram bot token", hide=True)]
    telegram_chat_id: Annotated[int, setting_field(0, "telegram chat id")]
    telegram_bot_admins: Annotated[str, setting_field("", "list of telegram bot admins, for example: 123456789,987654321")]
    telegram_bot_auto_start: Annotated[bool, setting_field(False)]
    price: Annotated[
        Decimal, setting_field(Decimal("1.23"), "long long long long long long long long long long long long long long long long")
    ]
    secret_password: Annotated[str, setting_field("abc", hide=True)]
    long_cfg_1: Annotated[str, setting_field("many lines\n" * 5)]


class State(BaseState):
    proxies: Annotated[list[str], state_field([], "List of proxy URLs")]
    proxies_updated_at: Annotated[datetime | None, state_field(None, "Last proxy update timestamp")]
    tmp1: Annotated[str, state_field("bla", "Temporary value 1")]
    tmp2: Annotated[str, state_field("bla", "Temporary value 2")]
    processed_block: Annotated[int, state_field(111, "bla bla about processed_block")]
    last_checked_at: Annotated[datetime, state_field(utc_now(), "bla bla about last_checked_at", persistent=False)]
