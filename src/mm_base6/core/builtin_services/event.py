from __future__ import annotations

import logging

from bson import ObjectId

from mm_base6.core.db import BaseDb, Event

logger = logging.getLogger(__name__)


class EventService:
    """Service for application event logging and monitoring.

    Provides centralized event tracking throughout the framework and applications.
    Events are persisted to MongoDB for debugging, monitoring, and audit purposes.
    All framework services use this for error reporting and state tracking.
    """

    def __init__(self, db: BaseDb) -> None:
        self.db = db

    async def event(self, event_type: str, data: object = None) -> None:
        """Log an event with optional data payload.

        Args:
            event_type: Categorization string for the event (e.g., "user.login", "error.db")
            data: Optional JSON-serializable data associated with the event
        """
        logger.debug("event: %s %s", event_type, data)
        await self.db.event.insert_one(Event(id=ObjectId(), type=event_type, data=data))

    async def get_event_type_stats(self) -> dict[str, int]:
        """Get count of events grouped by event type.

        Returns:
            Dictionary mapping event types to their occurrence counts
        """
        result = {}
        for event_type in await self.db.event.collection.distinct("type"):
            result[event_type] = await self.db.event.count({"type": event_type})
        return result
