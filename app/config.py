from typing import Annotated, Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    litellm_base_url: str
    litellm_api_key: str
    litellm_chat_model: str
    litellm_embedding_model: str

    github_repo_url: str
    github_token: str
    indexer_interval_hours: int = 4

    web_search_backend: Literal["noop", "searxng", "bing"] = "noop"
    web_search_allowed_domains: Annotated[list[str], NoDecode] = Field(default_factory=list)

    admin_token: str
    rate_limit_per_min: int = 30
    data_dir: str = "/data"
    port: int = 8080
    session_secret: str = Field(min_length=16)

    @field_validator("web_search_allowed_domains", mode="before")
    @classmethod
    def split_csv(cls, v):
        if isinstance(v, str):
            return [d.strip() for d in v.split(",") if d.strip()]
        return v

    @field_validator("port")
    @classmethod
    def reject_port_3000(cls, v: int) -> int:
        if v == 3000:
            raise ValueError("port 3000 is reserved in this environment; choose another (default 8080)")
        return v


def get_settings() -> Settings:
    return Settings()
