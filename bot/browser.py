import asyncio
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
except ImportError:  # pragma: no cover - exercised only in minimal test envs
    async_playwright = None
    Browser = BrowserContext = Page = Any

from bot.config import BrowserConfig, get_browser_config
from bot.proxy import ProxyConfig


class BrowserManager:
    def __init__(self, config: Optional[BrowserConfig] = None):
        self.config = config or get_browser_config()
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    async def start(self):
        """Start the browser"""
        if self._browser:
            return
        if async_playwright is None:
            raise RuntimeError("playwright is not installed")

        self._playwright = await async_playwright().start()
        launch_options = {
            "headless": self.config.headless,
            "slow_mo": self.config.slow_mo,
        }
        self._browser = await self._playwright.chromium.launch(**launch_options)

    async def create_context(
        self,
        user_agent: Optional[str] = None,
        proxy: Optional[Dict[str, Any]] = None,
        proxy_config: Optional[ProxyConfig] = None,
        storage_state: Optional[str] = None,
    ) -> BrowserContext:
        """Create a new browser context"""
        if not self._browser:
            await self.start()

        context_options = {
            "viewport": {
                "width": self.config.viewport_width,
                "height": self.config.viewport_height,
            },
            "locale": self.config.locale,
            "timezone_id": self.config.timezone,
        }

        if user_agent:
            context_options["user_agent"] = user_agent

        if proxy:
            context_options["proxy"] = proxy
        elif proxy_config:
            context_options["proxy"] = proxy_config.to_playwright_dict()

        if storage_state:
            context_options["storage_state"] = storage_state

        context = await self._browser.new_context(**context_options)
        return context

    async def new_page(self, context: Optional[BrowserContext] = None) -> Page:
        """Create a new page"""
        if not context:
            if not self._context:
                self._context = await self.create_context()
            context = self._context

        page = await context.new_page()
        page.set_default_timeout(self.config.timeout)
        return page

    async def close(self):
        """Close the browser"""
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


@asynccontextmanager
async def get_browser_manager():
    """Get a browser manager instance as context manager"""
    manager = BrowserManager()
    try:
        await manager.start()
        yield manager
    finally:
        await manager.close()
