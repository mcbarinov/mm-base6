# mm-base6

Web framework with MongoDB integration and unified `self.core` access.

## Config

```python
# app/config.py
from mm_base6 import CoreConfig, ServerConfig, BaseSettings, BaseState, setting_field, state_field

core_config = CoreConfig()
server_config = ServerConfig()

class Settings(BaseSettings):
    api_token: Annotated[str, setting_field("", "API token", hide=True)]
    check_interval: Annotated[int, setting_field(60, "Check interval in seconds")]

class State(BaseState):
    last_run: Annotated[datetime | None, state_field(None)]
    counter: Annotated[int, state_field(0, persistent=False)]  # not saved to DB
```

## MongoDB Model

```python
# app/core/db.py
from mm_mongo import AsyncMongoCollection, MongoModel
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
from mm_base6 import Service

class UserService(Service[AppCore]):
    async def on_start(self):
        await self.core.db.user.create_indexes()

    def configure_scheduler(self):
        self.core.scheduler.add_task("cleanup", 3600, self.cleanup_old_users)

    async def cleanup_old_users(self):
        cutoff = utc_now() - timedelta(days=30)
        await self.core.db.user.collection.delete_many({"created_at": {"$lt": cutoff}})
        await self.core.event("users_cleaned", {"cutoff": cutoff})
```

## Router (CBV)

```python
# app/server/routers/user.py
from fastapi import APIRouter
from mm_base6 import cbv

router = APIRouter(prefix="/api/user", tags=["user"])

@cbv(router)
class CBV(AppView):
    @router.get("/{id}")
    async def get_user(self, id: ObjectId) -> User:
        return await self.core.db.user.get(id)

    @router.post("/")
    async def create_user(self, name: str, email: str) -> User:
        user = User(id=ObjectId(), name=name, email=email)
        await self.core.db.user.insert_one(user)
        return user
```

## Naming Conventions

- **MongoDB models**: PascalCase, singular, no suffix (`User`, `DataItem`)
- **MongoDB collections**: snake_case, singular (`user`, `data_item`)
- **Service classes**: PascalCase + "Service" (`UserService`)
- **Service registry**: snake_case, no suffix (`user`, `data`)
