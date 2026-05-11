import asyncio
from typing import Optional, Dict, Any

try:
    from playwright.async_api import Page, Locator, TimeoutError as PlaywrightTimeoutError
except ImportError:  # pragma: no cover - exercised only in minimal test envs
    Page = Locator = Any

    class PlaywrightTimeoutError(Exception):
        """Fallback timeout error used when Playwright is unavailable."""


class PageNavigator:
    def __init__(self, page: Page):
        self.page = page

    async def navigate(
        self,
        url: str,
        wait_until: str = "domcontentloaded",
        timeout: Optional[int] = None,
    ):
        """Navigate to a URL"""
        await self.page.goto(url, wait_until=wait_until, timeout=timeout)

    async def click(
        self,
        selector: str,
        timeout: Optional[int] = None,
        force: bool = False,
        delay: Optional[float] = None,
    ):
        """Click an element"""
        element = self.page.locator(selector)
        await element.click(timeout=timeout, force=force, delay=delay)

    async def fill(
        self,
        selector: str,
        value: str,
        timeout: Optional[int] = None,
    ):
        """Fill an input field"""
        element = self.page.locator(selector)
        await element.fill(value, timeout=timeout)

    async def type_text(
        self,
        selector: str,
        text: str,
        timeout: Optional[int] = None,
        delay: Optional[float] = None,
    ):
        """Type text character by character"""
        element = self.page.locator(selector)
        await element.type(text, timeout=timeout, delay=delay)

    async def wait_for_selector(
        self,
        selector: str,
        timeout: Optional[int] = None,
        state: str = "visible",
    ) -> Locator:
        """Wait for an element to appear"""
        element = self.page.locator(selector)
        await element.wait_for(timeout=timeout, state=state)
        return element

    async def wait_for_url(
        self,
        url: str,
        timeout: Optional[int] = None,
    ):
        """Wait for URL to change"""
        await self.page.wait_for_url(url, timeout=timeout)

    async def get_text(
        self,
        selector: str,
        timeout: Optional[int] = None,
    ) -> Optional[str]:
        """Get text content of an element"""
        try:
            element = self.page.locator(selector)
            return await element.text_content(timeout=timeout)
        except PlaywrightTimeoutError:
            return None

    async def get_attribute(
        self,
        selector: str,
        name: str,
        timeout: Optional[int] = None,
    ) -> Optional[str]:
        """Get attribute value of an element"""
        try:
            element = self.page.locator(selector)
            return await element.get_attribute(name, timeout=timeout)
        except PlaywrightTimeoutError:
            return None

    async def is_visible(
        self,
        selector: str,
        timeout: Optional[int] = None,
    ) -> bool:
        """Check if an element is visible"""
        try:
            element = self.page.locator(selector)
            await element.wait_for(state="visible", timeout=timeout or 1000)
            return True
        except PlaywrightTimeoutError:
            return False

    async def wait_for_load_state(
        self,
        state: str = "domcontentloaded",
        timeout: Optional[int] = None,
    ):
        """Wait for page to load"""
        await self.page.wait_for_load_state(state, timeout=timeout)

    async def screenshot(
        self,
        path: Optional[str] = None,
        full_page: bool = False,
    ):
        """Take a screenshot"""
        return await self.page.screenshot(path=path, full_page=full_page)

    async def scroll_to(
        self,
        selector: Optional[str] = None,
        x: Optional[float] = None,
        y: Optional[float] = None,
    ):
        """Scroll to an element or position"""
        if selector:
            element = self.page.locator(selector)
            await element.scroll_into_view_if_needed()
        elif x is not None and y is not None:
            await self.page.evaluate(f"window.scrollTo({x}, {y})")

    async def evaluate(
        self,
        script: str,
        *args: Any,
    ) -> Any:
        """Evaluate JavaScript in the page"""
        return await self.page.evaluate(script, *args)

    async def wait(
        self,
        duration: float,
    ):
        """Wait for a duration in seconds"""
        await asyncio.sleep(duration)

    async def wait_for_condition(
        self,
        condition_script: str,
        timeout: float = 30,
        check_interval: float = 0.5,
    ):
        """Wait for a JavaScript condition to be true"""
        start_time = asyncio.get_event_loop().time()
        while True:
            result = await self.page.evaluate(condition_script)
            if result:
                return
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                raise PlaywrightTimeoutError(f"Condition not met after {timeout} seconds")
            await asyncio.sleep(check_interval)


def create_navigator(page: Page) -> PageNavigator:
    """Create a PageNavigator instance for a page"""
    return PageNavigator(page)
