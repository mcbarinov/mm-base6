from dataclasses import dataclass
from typing import Self

from mm_concurrency.async_scheduler import AsyncScheduler

from mm_base6.config import Config
from mm_base6.core.builtin_services.event import EventService
from mm_base6.core.builtin_services.logfile import LogfileService
from mm_base6.core.builtin_services.settings import SettingsService
from mm_base6.core.builtin_services.stat import StatService
from mm_base6.core.builtin_services.state import StateService
from mm_base6.core.builtin_services.telegram import TelegramService
from mm_base6.core.db import BaseDb


@dataclass
class BuiltinServices:
    """Container for framework's core services available to all applications.

    These services provide fundamental functionality needed by any application
    built with the framework: event logging, settings management, state persistence,
    statistics collection, log file operations, and Telegram integration.
    """

    event: EventService
    settings: SettingsService
    state: StateService
    stat: StatService
    logfile: LogfileService
    telegram: TelegramService

    @classmethod
    def init(cls, db: BaseDb, scheduler: AsyncScheduler, config: Config) -> Self:
        """Create all framework services with their dependencies."""
        event = EventService(db)
        settings = SettingsService(event)
        state = StateService(event)
        return cls(
            event=event,
            settings=settings,
            state=state,
            stat=StatService(db, scheduler),
            logfile=LogfileService(config),
            telegram=TelegramService(event, settings),
        )
