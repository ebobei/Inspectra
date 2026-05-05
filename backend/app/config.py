from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Inspectra"
    app_env: str = "development"

    database_url: str = Field(
        default="postgresql+psycopg://inspectra:inspectra@db:5432/inspectra"
    )
    redis_url: str = "redis://redis:6379/0"

    llm_provider: str = "openrouter"
    llm_base_url: str | None = "https://openrouter.ai/api/v1"
    llm_api_key: str | None = None
    llm_model: str | None = None
    llm_verify_ssl: bool = True
    request_timeout_sec: int = 60
    llm_max_retries: int = 3
    publish_max_retries: int = 3

    encryption_key: str = "change-me-change-me-change-me"
    admin_api_token: str = "change-me-admin-token"

    default_max_iterations: int = 3
    recheck_enabled_default: bool = True

    jira_enabled: bool = True
    gitlab_enabled: bool = True
    confluence_enabled: bool = True

    ui_default_locale: str = "en"
    ui_allowed_origins: str = (
        "http://localhost:8080,http://localhost:4173,http://localhost:5173"
    )

    webhook_shared_secret: str | None = None


settings = Settings()