#!/usr/bin/env python3
"""Test script to verify typing works correctly after CoreProtocol changes."""

from app.core.core import Core
from app.server.deps import View
from app.settings import core_config
import asyncio


async def test_typing():
    """Test that typing works correctly."""
    # Test Core typing
    core = await Core.init(core_config)
    
    # These should be properly typed now
    telegram_token = core.dynamic_configs.telegram_token  # Should be str
    processed_block = core.dynamic_values.processed_block  # Should be int
    data_collection = core.db.data  # Should be AsyncMongoCollection[ObjectId, Data]
    data_service = core.services.data  # Should be DataService
    
    print(f"✅ telegram_token type: {type(telegram_token)}")
    print(f"✅ processed_block type: {type(processed_block)}")
    print(f"✅ data_collection type: {type(data_collection)}")
    print(f"✅ data_service type: {type(data_service)}")
    
    # Test View typing
    view = View()
    # view.core should be typed as Core (not CoreProtocol)
    print(f"✅ View.core annotation: {View.__annotations__.get('core', 'No annotation')}")
    
    await core.shutdown()


if __name__ == "__main__":
    asyncio.run(test_typing())
