from typing import Optional
from pydantic_settings import BaseSettings

from app.config import get_settings

app_settings = get_settings()


class BrowserConfig(BaseSettings):
    headless: bool = True
    slow_mo: float = 0.0
    timeout: int = 30000
    viewport_width: int = 1920
    viewport_height: int = 1080
    user_agent: Optional[str] = None
    locale: str = "zh-CN"
    timezone: str = "Asia/Shanghai"

    class Config:
        env_prefix = "BROWSER_"


def get_browser_config() -> BrowserConfig:
    return BrowserConfig(
        headless=app_settings.playwright_headless
    )
