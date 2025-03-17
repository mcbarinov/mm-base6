import logging
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class CoreConfig(BaseSettings):
    app_name: str
    data_dir: Path
    database_url: str
    debug: bool = False

    @property
    def logger_level(self) -> int:
        return logging.DEBUG if self.debug else logging.INFO

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
