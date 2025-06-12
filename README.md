# mm-base6

A comprehensive library for building production-ready async web applications in Python with maximum type safety and developer experience.

## Overview

**mm-base6** provides a batteries-included foundation for FastAPI applications with a focus on:

- **Type Safety** - Full generic typing with mypy strict mode support
- **Dynamic Configuration** - Runtime configuration management with web UI
- **MongoDB Integration** - Type-safe collections with automatic schema validation
- **Built-in Admin UI** - Ready-to-use web interface for system management
- **Telegram Bot Support** - Integrated bot framework
- **Background Tasks** - Async scheduler with monitoring
- **System Monitoring** - Resource usage, logs, and performance tracking
- **Authentication** - Token-based auth with middleware
- **Developer Experience** - Automatic dependency injection and code completion

## Core Architecture

The library uses a layered architecture with strong typing throughout:

```
┌─────────────────────────────────────────┐
│ User Application Layer                  │
├─────────────────────────────────────────┤
│ • Core (extends BaseCore)               │
│ • Services (extends BaseService)        │
│ • DB Models (extends BaseDb)            │
│ • Dynamic Config/Values                 │
│ • Routers (uses @cbv decorator)         │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│ mm-base6 Library Layer                  │
├─────────────────────────────────────────┤
│ • BaseCore[DC, DV, DB, SR]              │
│ • BaseService[DC, DV, DB]               │
│ • BaseView (dependency injection)       │
│ • System Services                       │
│ • Server & Middleware                   │
│ • Jinja2 Templates                      │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│ Infrastructure Layer                    │
├─────────────────────────────────────────┤
│ • FastAPI + Uvicorn                     │
│ • MongoDB + Motor                       │
│ • Telegram Bot API                      │
│ • Jinja2 + PicoCSS                      │
└─────────────────────────────────────────┘
```

## Quick Start

### 1. Project Structure

A typical mm-base6 application has the following structure:

```
your_app/
├── src/
│   └── app/
│       ├── __init__.py
│       ├── main.py              # Application entry point
│       ├── settings.py          # Configuration and routing
│       ├── telegram.py          # Telegram bot handlers (optional)
│       ├── core/
│       │   ├── __init__.py
│       │   ├── core.py          # Main application core
│       │   ├── db.py            # Database models
│       │   ├── types_.py        # Type aliases
│       │   └── services/        # Business logic services
│       │       ├── __init__.py
│       │       ├── data.py
│       │       └── misc.py
│       └── server/
│           ├── __init__.py
│           ├── jinja.py         # Template configuration
│           ├── routers/         # API endpoints
│           │   ├── __init__.py
│           │   ├── ui.py        # Web UI routes
│           │   ├── data.py      # API routes
│           │   └── misc.py
│           └── templates/       # Jinja2 templates
│               ├── index.j2
│               ├── data.j2
│               └── misc.j2
├── .env                         # Environment variables
├── pyproject.toml
└── README.md
```

### 2. Core Implementation

**`core/core.py`** - Main application core:

```python
from typing import Self
from app.core.db import Db
from app.core.services.data import DataService
from app.core.services.misc import MiscService
from app.settings import DynamicConfigs, DynamicValues
from mm_base6 import BaseCore, CoreConfig

class ServiceRegistry:
    data: DataService
    misc: MiscService

class Core(BaseCore[DynamicConfigs, DynamicValues, Db, ServiceRegistry]):
    @classmethod
    async def init(cls, core_config: CoreConfig) -> Self:
        res = await super().base_init(core_config, DynamicConfigs, DynamicValues, Db, ServiceRegistry)
        res.services.data = DataService(res.base_service_params)
        res.services.misc = MiscService(res.base_service_params)
        return res

    async def configure_scheduler(self) -> None:
        # Add background tasks
        self.scheduler.add_task("generate_data", 60, self.services.data.generate_one)

    async def start(self) -> None:
        # Startup logic
        pass

    async def stop(self) -> None:
        # Cleanup logic
        pass
```

**`core/db.py`** - Database models:

```python
from datetime import datetime
from enum import Enum
from typing import ClassVar
from bson import ObjectId
from mm_mongo import AsyncMongoCollection, MongoModel
from mm_std import utc_now
from pydantic import Field
from mm_base6 import BaseDb

class DataStatus(str, Enum):
    OK = "OK"
    ERROR = "ERROR"

class Data(MongoModel[ObjectId]):
    status: DataStatus
    value: int
    created_at: datetime = Field(default_factory=utc_now)
    
    __collection__: str = "data"
    __indexes__ = "status, created_at"
    __validator__: ClassVar[dict[str, object]] = {
        "$jsonSchema": {
            "required": ["status", "value", "created_at"],
            "additionalProperties": False,
            "properties": {
                "_id": {"bsonType": "objectId"},
                "status": {"enum": ["OK", "ERROR"]},
                "value": {"bsonType": "int"},
                "created_at": {"bsonType": "date"},
            },
        },
    }

class Db(BaseDb):
    data: AsyncMongoCollection[ObjectId, Data]
```

**`settings.py`** - Configuration and routing:

```python
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter
from mm_std import utc_now
from mm_base6 import DC, DV, CoreConfig, DynamicConfigsModel, DynamicValuesModel, ServerConfig

core_config = CoreConfig()

server_config = ServerConfig()
server_config.tags = ["data", "misc"]
server_config.main_menu = {"/data": "data", "/misc": "misc"}

class DynamicConfigs(DynamicConfigsModel):
    # Runtime configuration with web UI
    telegram_token = DC("", "Telegram bot token", hide=True)
    telegram_chat_id = DC(0, "Telegram chat ID")
    price = DC(Decimal("1.23"), "Price configuration")
    secret_password = DC("abc", hide=True)

class DynamicValues(DynamicValuesModel):
    # Runtime values that can change
    processed_count = DV(0, "Number of processed items")
    last_checked_at = DV(utc_now(), "Last check timestamp", persistent=False)

def get_router() -> APIRouter:
    from app.server import routers
    router = APIRouter()
    router.include_router(routers.ui.router)
    router.include_router(routers.data.router)
    router.include_router(routers.misc.router)
    return router
```

### 3. Services Layer

**`core/services/data.py`** - Business logic:

```python
import random
from bson import ObjectId
from mm_mongo import MongoInsertOneResult
from app.core.db import Data, DataStatus
from app.core.types_ import AppService, AppServiceParams

class DataService(AppService):
    def __init__(self, base_params: AppServiceParams) -> None:
        super().__init__(base_params)

    async def generate_one(self) -> MongoInsertOneResult:
        status = random.choice(list(DataStatus))
        value = random.randint(0, 1_000_000)
        
        # Access to all core components
        await self.system_log("generate_one", {"status": status, "value": value})
        await self.send_telegram_message(f"Generated: {status} - {value}")
        
        return await self.db.data.insert_one(
            Data(id=ObjectId(), status=status, value=value)
        )
```

**`core/types_.py`** - Type aliases:

```python
from app.core.db import Db
from app.settings import DynamicConfigs, DynamicValues
from mm_base6 import BaseService, BaseServiceParams

# Type-safe aliases for your application
AppService = BaseService[DynamicConfigs, DynamicValues, Db]
AppServiceParams = BaseServiceParams[DynamicConfigs, DynamicValues, Db]
```

### 4. Web Interface

**`server/routers/data.py`** - API endpoints:

```python
from bson import ObjectId
from fastapi import APIRouter
from mm_mongo import MongoDeleteResult, MongoInsertOneResult
from app.core.db import Data
from app.server.deps import View
from mm_base6 import cbv

router = APIRouter(prefix="/api/data", tags=["data"])

@cbv(router)
class CBV(View):
    @router.get("/{id}")
    async def get_data(self, id: ObjectId) -> Data | None:
        return await self.core.db.data.get_or_none(id)
    
    @router.post("/generate-one")
    async def generate_one(self) -> MongoInsertOneResult:
        return await self.core.services.data.generate_one()
    
    @router.delete("/{id}")
    async def delete_data(self, id: ObjectId) -> MongoDeleteResult:
        return await self.core.db.data.delete_one({"_id": id})
```

**`server/deps.py`** - Dependency injection:

```python
from typing import cast
from fastapi import Depends
from starlette.requests import Request
from app.core.core import Core
from mm_base6 import BaseView

async def get_core(request: Request) -> Core:
    return cast(Core, request.app.state.core)

class View(BaseView):
    core: Core = Depends(get_core)  # Type-safe dependency injection
```

### 5. Application Entry Point

**`main.py`**:

```python
from app import settings, telegram
from app.core.core import Core
from app.server import jinja
from mm_base6 import run

run(
    core_config=settings.core_config,
    server_config=settings.server_config,
    core_class=Core,
    telegram_handlers=telegram.handlers,  # Optional
    router=settings.get_router(),
    jinja_config=jinja.jinja_config,
    host="0.0.0.0",
    port=3000,
    uvicorn_log_level="warning",
)
```

### 6. Environment Configuration

**`.env`**:

```bash
APP_NAME=my-app
ACCESS_TOKEN=your-secret-token
DOMAIN=localhost
DATABASE_URL=mongodb://localhost/my-app
DATA_DIR=/data/my-app
DEBUG=True
USE_HTTPS=False
```

## Key Features

### Dynamic Configuration System

The library provides a powerful runtime configuration system with web UI:

```python
class DynamicConfigs(DynamicConfigsModel):
    # String configuration
    api_url = DC("https://api.example.com", "External API URL")
    
    # Hidden/secret values
    api_key = DC("", "API Secret Key", hide=True)
    
    # Typed configurations
    max_retries = DC(3, "Maximum retry attempts")
    price = DC(Decimal("9.99"), "Price setting")
    
    # Boolean flags
    debug_mode = DC(False, "Enable debug mode")
    
    # Multiline text
    custom_config = DC("line1\nline2\nline3", "Custom configuration")
```

Access in code:
```python
class MyService(AppService):
    async def call_api(self):
        url = self.dynamic_configs.api_url
        key = self.dynamic_configs.api_key
        # Configuration is type-safe and always current
```

**Web Interface**: Visit `/system/dynamic-configs` to manage configuration through a web UI with TOML support.

### Dynamic Values System

Runtime values that can be updated programmatically:

```python
class DynamicValues(DynamicValuesModel):
    # Persistent values (saved to DB)
    processed_count = DV(0, "Items processed")
    last_error = DV("", "Last error message")
    
    # Non-persistent values (memory only)
    current_status = DV("idle", "Current status", persistent=False)
    
    # Complex types
    stats = DV({"total": 0, "errors": 0}, "Processing statistics")
```

Update values:
```python
class MyService(AppService):
    async def process_item(self):
        # Update values programmatically
        self.dynamic_values.processed_count += 1
        self.dynamic_values.current_status = "processing"
```

### System Monitoring

Built-in monitoring and management:

- **System Stats**: CPU, memory, disk usage via `/system`
- **Database Monitoring**: Collection stats, slow queries
- **Log Management**: Application and access logs with web viewer
- **Scheduler Monitoring**: Background task status and performance
- **MongoDB Profiling**: Query performance analysis

### Class-Based Views (CBV)

Type-safe routing with automatic dependency injection:

```python
@cbv(router)
class UserCBV(View):
    # All dependencies automatically injected
    # self.core: Core - your typed application core
    # self.render: Render - template rendering
    # self.server_config: ServerConfig - server configuration
    # self.telegram_bot: TelegramBot - telegram integration
    
    @router.get("/users")
    async def list_users(self) -> list[User]:
        return await self.core.services.user.get_all()
    
    @router.post("/users")
    async def create_user(self, user_data: UserCreate) -> User:
        return await self.core.services.user.create(user_data)
```

### Template System

Jinja2 integration with custom filters and globals:

```python
# server/jinja.py
from mm_base6 import JinjaConfig

async def header_info(core: Core) -> Markup:
    count = await core.db.data.count({})
    return Markup(f"Total items: {count}")

jinja_config = JinjaConfig(
    header_info=header_info,
    filters={"custom_filter": my_filter},
    globals={"custom_var": "value"},
)
```

Templates automatically have access to:
- `core_config`, `server_config`
- `dynamic_configs`, `dynamic_values`
- Custom filters and globals
- Flash messaging system

### Telegram Integration

Built-in Telegram bot support:

```python
# telegram.py
from mm_telegram import TelegramHandler
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    core = context.bot_data.get("core")
    await core.services.data.generate_one()
    await update.message.reply_text("Data generated!")

handlers: list[TelegramHandler] = [
    CommandHandler("start", start_command),
]
```

### Background Tasks

Async scheduler with monitoring:

```python
class Core(BaseCore[...]):
    async def configure_scheduler(self) -> None:
        # Add periodic tasks
        self.scheduler.add_task("cleanup", 3600, self.cleanup_old_data)
        self.scheduler.add_task("sync", 300, self.sync_external_data)
    
    async def cleanup_old_data(self) -> None:
        cutoff = utc_now() - timedelta(days=30)
        await self.db.data.delete_many({"created_at": {"$lt": cutoff}})
```

Monitor tasks via `/system` web interface.

## Dependencies

### Core Dependencies
- **FastAPI** - Modern, fast web framework
- **mm-mongo** - Type-safe MongoDB ODM
- **mm-jinja** - Enhanced Jinja2 integration
- **mm-telegram** - Telegram bot library

### Frontend Libraries
- **PicoCSS** - Minimal CSS framework
- **Sortable** - Table sorting functionality


## Architecture Patterns

### Dependency Injection
The library uses constructor-based dependency injection:

```python
class BaseService[DC, DV, DB]:
    def __init__(self, base_params: BaseServiceParams[DC, DV, DB]):
        self.core_config = base_params.core_config
        self.dynamic_configs = base_params.dynamic_configs
        self.dynamic_values = base_params.dynamic_values
        self.db = base_params.db
        self.system_log = base_params.system_log
        self.send_telegram_message = base_params.send_telegram_message
```

### Generic Type System
Strong typing throughout the stack:

```python
# Application core with typed parameters
class Core(BaseCore[DynamicConfigs, DynamicValues, Db, ServiceRegistry]):
    pass

# Type-safe services
class MyService(BaseService[DynamicConfigs, DynamicValues, Db]):
    pass

# Type-safe views
class MyView(BaseView):
    core: Core = Depends(get_core)  # Fully typed
```

### Configuration as Code
Configuration is defined as Python classes:

```python
class DynamicConfigs(DynamicConfigsModel):
    # Type-safe configuration with validation
    max_connections = DC(100, "Maximum connections")
    timeout = DC(30.0, "Request timeout in seconds")
    debug = DC(False, "Enable debug mode")
```

## Production Deployment

### Environment Variables
```bash
# Production settings
APP_NAME=my-production-app
ACCESS_TOKEN=secure-random-token
DOMAIN=my-app.com
DATABASE_URL=mongodb://user:pass@mongo-cluster/myapp
DATA_DIR=/data/myapp
DEBUG=False
USE_HTTPS=True
```

### Monitoring
- Use built-in system monitoring at `/system`
- Monitor MongoDB performance with profiling
- Set up log aggregation for structured logs
- Monitor background task performance

### Security
- Use strong ACCESS_TOKEN for authentication
- Configure proper HTTPS with USE_HTTPS=True
- Hide sensitive configurations
- Implement proper input validation
- Use MongoDB connection with authentication

## Naming Conventions

- **MongoDB collections**: snake_case, singular (e.g., `user`, `data_item`)
