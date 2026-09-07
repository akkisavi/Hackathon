"""Central app settings, loaded from environment / .env."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# the single project-root .env, found regardless of the process CWD
_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), extra="ignore")

    # NASA FIRMS
    firms_map_key: str = ""

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/firedetect"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"

    # LLM (OpenAI-compatible endpoint — Gemini primary, NVIDIA build as fallback)
    llm_api_key: str = ""
    llm_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    llm_model: str = "gemini-2.5-flash"

    # Google Earth Engine — land-cover sampling (optional; blank => skipped)
    gee_project: str = ""

    # App
    api_v1_prefix: str = "/api/v1"
    project_name: str = "SIH26162 — Industrial Fire & Thermal Source Detection"


@lru_cache
def get_settings() -> Settings:
    return Settings()
