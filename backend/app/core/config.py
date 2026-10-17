import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "WeatherSignal"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Persistence
    DATABASE_URL: str = "sqlite+aiosqlite:///./weathersignal.db"

    # LLM Settings
    LLM_PROVIDER: str = "deterministic"
    LLM_API_KEY: Optional[str] = None
    LLM_MODEL: Optional[str] = None

    # IMD Settings
    IMD_API_BASE_URL: str = "https://api.imd.gov.in/api/v1"
    IMD_API_KEY: Optional[str] = None
    IMD_TIMEOUT_SECONDS: float = 10.0

    # Open-Meteo Auxiliary Observations
    OPEN_METEO_BASE_URL: str = "https://archive-api.open-meteo.com/v1/archive"
    OPEN_METEO_TIMEOUT_SECONDS: float = 10.0

    # Geocoding
    GEOCODING_PROVIDER: str = "nominatim"
    GEOCODING_USER_AGENT: str = "WeatherSignal/1.0"
    GEOCODING_TIMEOUT_SECONDS: float = 5.0

    # Guardrails and thresholds
    MAX_INVESTIGATION_ROUNDS: int = 3
    MAX_TOOL_CALLS: int = 10
    REQUEST_TIMEOUT_SECONDS: float = 15.0
    EVIDENCE_MAX_AGE_MINUTES: int = 1440
    MAX_STATION_DISTANCE_KM: float = 50.0
    TEMPORAL_WINDOW_HOURS: float = 6.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
