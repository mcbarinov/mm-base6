# mm-base6

Web framework with MongoDB integration and unified `self.core` access.

## Core Features

The main value of mm-base6 is the `self.core` object available in your services and routes, providing:

- **`core.settings`** - Type-safe persistent configuration
- **`core.state`** - Application state with MongoDB persistence
- **`core.event()`** - Event logging and monitoring
- **`core.base_services.telegram`** - Message sending and bot management
- **`core.services`** - Your custom application services

```python
class MyService(Service):
    async def do_something(self):
        # Access settings
        token = self.core.settings.api_token

        # Update state
        self.core.state.last_run = utc_now()

        # Log events
        await self.core.base_services.event.event("task_completed", {"status": "success"})

        # Send notifications
        await self.core.base_services.telegram.send_message("Task done!")

        # Use other services
        result = await self.core.services.data.process()
```

## Naming Conventions

- **MongoDB collections**: snake_case, singular (e.g., `user`, `data_item`)
- **Service classes**: PascalCase ending with "Service" (e.g., `DataService`, `UserService`)
- **Service registry attributes**: snake_case without "service" suffix (e.g., `data`, `user`)
