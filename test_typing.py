#!/usr/bin/env python3
"""Test script to verify typing works correctly after CoreProtocol changes."""

from mm_base6 import Core
from app.settings import AppCore, create_services, DynamicConfigs, DynamicValues, Db
from app.server.deps import View
from app.settings import core_config
import asyncio


async def test_typing() -> None:
    """Test that typing works correctly."""
    # Test Core typing
    core = await Core.init(
        core_config=core_config,
        dynamic_configs_cls=DynamicConfigs,
        dynamic_values_cls=DynamicValues,
        db_cls=Db,
        create_services_fn=create_services,
    )
    
    # These should be properly typed now
    telegram_token = core.dynamic_configs.telegram_token  # Should be str
    processed_block = core.dynamic_values.processed_block  # Should be int
    data_collection = core.db.data  # Should be AsyncMongoCollection[ObjectId, Data]
    data_service = core.services.data  # Should be DataService
    
    assert isinstance(telegram_token, str)
    assert isinstance(processed_block, int)
    assert hasattr(data_collection, "find")
    assert hasattr(data_service, "generate_one")
    
    # Test View typing - should have proper core annotation
    assert hasattr(View, "__annotations__")
    assert "core" in View.__annotations__
    
    await core.shutdown()


if __name__ == "__main__":
    asyncio.run(test_typing())
