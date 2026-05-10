import asyncio
from typing import Optional, Dict, Any, Tuple
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

from playwright.async_api import Page, BrowserContext, TimeoutError

from bot.navigator import PageNavigator, create_navigator
from bot.session import Session
from bot.fingerprint import Fingerprint


class StockStatus(Enum):
    IN_STOCK = "in_stock"
    OUT_OF_STOCK = "out_of_stock"
    UNKNOWN = "unknown"


@dataclass
class ProductInfo:
    name: str
    status: StockStatus
    price: Optional[str] = None
    last_updated: Optional[datetime] = None


class BigModelPage:
    BASE_URL = "https://bigmodel.cn"

    def __init__(
        self,
        page: Page,
        navigator: Optional[PageNavigator] = None,
    ):
        self.page = page
        self.navigator = navigator or create_navigator(page)

    async def go_to_home(self):
        """Navigate to home page"""
        await self.navigator.navigate(self.BASE_URL)

    async def check_stock(self, product_selector: str = "#stock-status") -> Tuple[StockStatus, ProductInfo]:
        """Check stock status"""
        try:
            await self.navigator.wait_for_selector(product_selector, timeout=10000)

            status_text = await self.navigator.get_text(product_selector)
            product_name = await self.navigator.get_text(".product-name") or "Unknown Product"

            if status_text and ("有货" in status_text or "in stock" in status_text.lower()):
                status = StockStatus.IN_STOCK
            elif status_text and ("无货" in status_text or "out of stock" in status_text.lower()):
                status = StockStatus.OUT_OF_STOCK
            else:
                status = StockStatus.UNKNOWN

            price = await self.navigator.get_text(".product-price")

            return status, ProductInfo(
                name=product_name,
                status=status,
                price=price,
                last_updated=datetime.now(),
            )

        except TimeoutError:
            return StockStatus.UNKNOWN, ProductInfo(
                name="Unknown",
                status=StockStatus.UNKNOWN,
                last_updated=datetime.now(),
            )

    async def login(self, username: str, password: str) -> bool:
        """Perform login"""
        try:
            # This is a template - actual selectors need to be adjusted based on real page
            await self.navigator.fill("#username", username)
            await self.navigator.fill("#password", password)
            await self.navigator.click("#login-button")
            await self.navigator.wait_for_load_state("networkidle")

            # Check if login successful
            return await self.navigator.is_visible(".user-profile")

        except Exception:
            return False

    async def purchase(self, timeout: int = 30000) -> Tuple[bool, Optional[str]]:
        """Attempt to purchase"""
        try:
            # Click buy button - selectors need to be adjusted
            await self.navigator.click(".buy-button", timeout=timeout)
            await self.navigator.wait_for_load_state("networkidle")

            # Confirm purchase
            await self.navigator.click(".confirm-button", timeout=timeout)
            await self.navigator.wait_for_load_state("networkidle")

            # Check result
            success = await self.navigator.is_visible(".success-message")
            order_id = await self.navigator.get_text(".order-id")

            return success, order_id

        except Exception as e:
            return False, str(e)

    async def save_screenshot(self, path: Optional[str] = None) -> bytes:
        """Take a screenshot"""
        if not path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = f"data/screenshots/{timestamp}.png"
        return await self.navigator.screenshot(path=path, full_page=True)

    async def get_page_content(self) -> str:
        """Get current page HTML content"""
        return await self.page.content()


async def create_bigmodel_page(
    context: BrowserContext,
    session: Optional[Session] = None,
    fingerprint: Optional[Fingerprint] = None,
) -> BigModelPage:
    """Create a BigModelPage instance"""
    page = await context.new_page()

    # Apply session if provided
    if session:
        await session.apply_to_context(context)

    navigator = create_navigator(page)
    return BigModelPage(page, navigator)
