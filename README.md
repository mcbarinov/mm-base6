# mm-base6

A library for building async web applications in Python with type safety and developer experience.

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

## Naming Conventions

- **MongoDB collections**: snake_case, singular (e.g., `user`, `data_item`)
- **Service classes**: PascalCase ending with "Service" (e.g., `DataService`, `UserService`)
- **Service registry attributes**: snake_case without "service" suffix (e.g., `data`, `user`)
