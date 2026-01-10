# Architecture Decision Records

Key design decisions for this project. Read this before suggesting changes.

## 1. CBV (Class-Based Views) Pattern

**Decision**: Use class-based views with the `@cbv` decorator for all routers.

**Why**:
- The `View` base class bundles 5 common dependencies (core, telegram_bot, server_config, form_data, render) that every endpoint needs
- Without CBV, each endpoint would repeat 5 `Annotated[..., Depends(...)]` declarations
- Provides type-safe generics: `View[Settings, State, Db, ServiceRegistry]`
- Groups related endpoints logically within classes

**Guidelines**:
- Use one CBV class per router file unless there's a clear reason to split
- Only split into multiple classes when they have different base classes or dependencies
- Don't split just by HTTP method (GET vs POST)
