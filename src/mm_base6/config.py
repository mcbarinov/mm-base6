import logging
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Unified configuration for mm-base6 application."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # === App ===
    app_name: str = Field(description="Application name. Used in OpenAPI docs, HTML page title, and UI header.")

    # === Infrastructure ===
    database_url: str = Field(description="MongoDB connection URL. Example: mongodb://localhost:27017/myapp")
    data_dir: Path = Field(
        default=Path("data"),
        description="Directory for app.log and access.log files. Created automatically.",
    )
    debug: bool = Field(
        default=False,
        description="Debug mode. Enables DEBUG logging, detailed error messages.",
    )

    # === HTTP ===
    domain: str = Field(description="Domain for auth cookies. Example: example.com")
    access_token: str = Field(description="Secret token for user authentication and session encryption.")
    use_https: bool = Field(
        default=True,
        description="Force HTTPS in internal API URL rewrites. "
        "TODO: Replace with base_url config or X-Forwarded-Proto header support.",
    )

    # === OpenAPI ===
    openapi_tags: list[str] = Field(
        default_factory=list,
        description="Tags for API documentation grouping. Example: ['users', 'products']",
    )

    # === UI ===
    ui_menu: dict[str, str] = Field(
        default_factory=dict,
        description="Navigation menu items. Maps URL path to display name. Example: {'/users': 'Users', '/settings': 'Settings'}",
    )

    @property
    def logger_level(self) -> int:
        """Returns DEBUG level in debug mode, INFO otherwise."""
        return logging.DEBUG if self.debug else logging.INFO

    @property
    def openapi_tags_metadata(self) -> list[dict[str, str]]:
        """Converts openapi_tags list to OpenAPI metadata format. Includes 'system' tag."""
        tags = [{"name": t} for t in self.openapi_tags]
        return [*tags, {"name": "system"}]
