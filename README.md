# mm-base6

Web framework with MongoDB integration and unified `self.core` access.

## Config

```python
# app/config.py
from typing import Annotated
from datetime import datetime

from mm_base6 import Config, BaseSettings, BaseState, setting_field, state_field

config = Config(openapi_tags=["user"], ui_menu={"/users": "Users"})

class Settings(BaseSettings):
    api_token: Annotated[str, setting_field("", "API token", hide=True)]  # hide=True excludes from exports
    check_interval: Annotated[int, setting_field(60, "Check interval in seconds")]

class State(BaseState):
    last_run: Annotated[datetime | None, state_field(None)]
    counter: Annotated[int, state_field(0, persistent=False)]  # persistent=False: memory-only, not saved to DB
```

## Type Aliases

```python
# app/core/types.py
from mm_base6 import Core, View

AppCore = Core[Settings, State, Db, ServiceRegistry]
AppView = View[Settings, State, Db, ServiceRegistry]
```

## MongoDB Model

```python
# app/core/db.py
from datetime import datetime

from bson import ObjectId
from pydantic import Field
from mm_mongo import AsyncMongoCollection, MongoModel, utc_now
from mm_base6 import BaseDb

class User(MongoModel[ObjectId]):
    name: str
    email: str
    created_at: datetime = Field(default_factory=utc_now)

    __collection__ = "user"
    __indexes__ = ["!email", "created_at"]

class Db(BaseDb):
    user: AsyncMongoCollection[ObjectId, User]
```

## Service

```python
# app/core/services/user.py
from datetime import timedelta
from typing import override

from mm_mongo import utc_now
from mm_base6 import Service

class UserService(Service[AppCore]):
    @override
    async def on_start(self):
        """Called during app startup."""
        await self.core.db.user.create_indexes()

    @override
    async def on_stop(self):
        """Called during app shutdown."""
        pass

    @override
    def configure_scheduler(self):
        """Register background tasks."""
        self.core.scheduler.add_task("cleanup", 3600, self.cleanup_old_users)

    async def cleanup_old_users(self):
        cutoff = utc_now() - timedelta(days=30)
        await self.core.db.user.collection.delete_many({"created_at": {"$lt": cutoff}})
        await self.core.event("users_cleaned", {"cutoff": cutoff})
```

## Events

```python
# Log events for audit/debugging
await self.core.event("user_created", {"user_id": str(user.id)})
await self.core.event("payment_processed", {"amount": 100})
```

## Router (CBV)

```python
# app/server/routers/user.py
from bson import ObjectId
from fastapi import APIRouter
from mm_base6 import cbv

router = APIRouter(prefix="/api/user", tags=["user"])

@cbv(router)
class CBV(AppView):
    # Auto-injected: self.core, self.config, self.render, self.form_data

    @router.get("/{id}")
    async def get_user(self, id: ObjectId) -> User:
        return await self.core.db.user.get(id)

    @router.post("/")
    async def create_user(self, name: str, email: str) -> User:
        user = User(id=ObjectId(), name=name, email=email)
        await self.core.db.user.insert_one(user)
        return user
```

## Telegram

```python
# In Settings
telegram_token: Annotated[str, setting_field("", "Bot token", hide=True)]
telegram_chat_id: Annotated[str, setting_field("", "Chat ID")]

# Send message
await self.core.builtin_services.telegram.send_message("Deploy complete!")
```

## Running the App

```python
# app/main.py
from mm_base6 import run

await run(
    core=core,
    jinja_config_cls=MyJinjaConfig,
    telegram_handlers=None,
    host="0.0.0.0",
    port=8000,
    uvicorn_log_level="info",
)
```

## Built-in System API

Framework provides `/api/system/*` endpoints:
- **Settings/State**: TOML export/import
- **Events**: query and delete
- **Stats**: app and system metrics
- **Logs**: read/clear app.log, access.log
- **Scheduler**: start/stop/reinit
- **Telegram**: send test message, start/stop bot

## Naming Conventions

- **MongoDB models**: PascalCase, singular, no suffix (`User`, `DataItem`)
- **MongoDB collections**: snake_case, singular (`user`, `data_item`)
- **Service classes**: PascalCase + "Service" (`UserService`)
- **Service registry**: snake_case, no suffix (`user`, `data`)

## Admin UI CSS Guidelines

The admin UI uses [Pico CSS](https://picocss.com/) as the base framework.

### Principles

1. **Pico-first** - Use Pico's semantic HTML patterns before writing custom CSS
2. **Variables everywhere** - Always use `--pico-*` variables for colors, spacing, borders
3. **Minimal custom CSS** - Only add custom styles when Pico doesn't provide a solution

### File Structure (`base.css`)

```
1. PICO CSS CUSTOMIZATION - Override Pico variables and element defaults
2. THIRD-PARTY LIBRARIES - Styles for external JS libraries (sortable.js, etc.)
3. CUSTOM APPLICATION STYLES - App-specific components (.alert, .stack, etc.)
```

### Customizing Pico

```css
/* Override base font size (bypasses Pico's responsive breakpoints) */
html {
    font-size: 14px;
}

/* Override spacing via variables */
:root {
    --pico-spacing: 0.75rem;
    --pico-form-element-spacing-vertical: 0.4rem;
}
```

### Prefer Inline Styles for One-Off Cases

For single-use elements, **inline styles are preferred** over adding to `base.css`:
- The style applies to exactly one element in the entire app
- Creating a CSS class adds unnecessary indirection
- Keeps `base.css` clean — only reusable patterns belong there

Example: `<nav style="justify-content: flex-start">` in header.

### Pico Patterns to Use

- `<fieldset role="group">` - horizontal form layout
- `<small class="secondary">` - muted text
- `class="outline"` - outline buttons
- `class="container-fluid"` - full-width container

### Reference

- [Pico CSS Variables](https://picocss.com/docs/css-variables)
- [Pico Components](https://picocss.com/docs)
