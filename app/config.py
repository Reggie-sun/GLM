from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "GLM Coding Bot"
    app_env: str = "development"
    debug: bool = True

    database_url: str = "postgresql://user:pass@localhost:5432/glm_bot"
    redis_url: str = "redis://localhost:6379/0"

    celery_broker_url: Optional[str] = None
    celery_result_backend: Optional[str] = None

    playwright_headless: bool = True

    snapshot_dir: str = "data/snapshots"
    snapshot_interval: int = 30

    class Config:
        env_file = ".env"

    def model_post_init(self, __context) -> None:
        if not self.celery_broker_url:
            self.celery_broker_url = self.redis_url
        if not self.celery_result_backend:
            self.celery_result_backend = self.redis_url


@lru_cache()
def get_settings():
    return Settings()
