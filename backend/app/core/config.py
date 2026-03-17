from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openweather_api_key: str = ""
    waqi_api_key: str = ""
    ambee_api_key: str = ""
    openuv_api_key: str = ""
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_key: str = ""
    anthropic_api_key: str = ""
    redis_url: str = "redis://localhost:6379/0"
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""
    sendgrid_api_key: str = ""
    firebase_service_account_json: str = ""
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ecovital"
    backend_cors_origins: str = "http://localhost:5173"

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
