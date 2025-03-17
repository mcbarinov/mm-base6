from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServerConfig(BaseSettings):
    domain: str
    access_token: str
    use_https: bool = True
    tags: list[str] = Field(default_factory=list)
    main_menu: dict[str, str] = Field(default_factory=dict)

    @property
    def tags_metadata(self) -> list[dict[str, str]]:
        app = [{"name": t} for t in self.tags]
        return [*app, {"name": "system"}]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
