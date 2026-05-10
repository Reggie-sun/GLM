from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "GLM Coding Bot"
    app_env: str = "development"
    debug: bool = True

    database_url: str = "postgresql://user:pass@localhost:5432/glm_bot"
    redis_url: str = "redis://localhost:6379/0"

    playwright_headless: bool = True

    snapshot_dir: str = "data/snapshots"
    snapshot_interval: int = 30

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()
