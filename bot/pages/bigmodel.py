import asyncio
import logging
from typing import Optional, Dict, Any, Tuple
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

try:
    from playwright.async_api import Page, BrowserContext
except ImportError:  # pragma: no cover - exercised only in minimal test envs
    Page = BrowserContext = Any

from bot.navigator import PageNavigator, create_navigator
from bot.session import Session
from bot.fingerprint import Fingerprint

logger = logging.getLogger(__name__)


class StockStatus(Enum):
    IN_STOCK = "in_stock"
    OUT_OF_STOCK = "out_of_stock"
    UNKNOWN = "unknown"


@dataclass
class ProductInfo:
    name: str
    status: StockStatus
    price: Optional[str] = None
    restock_time: Optional[str] = None
    last_updated: Optional[datetime] = None


class BigModelPage:
    BASE_URL = "https://bigmodel.cn"
    BUY_KEYWORDS = ("购买", "立即购买", "立即开通", "立即抢购", "预约", "订阅", "去购买")
    BUY_BLOCKLIST = ("帮助", "客服", "详情", "登录", "注册", "取消", "关闭")
    CONFIRM_KEYWORDS = ("确认购买", "立即支付", "去支付", "确认", "继续")
    AUTHENTICATED_SELECTORS = (
        "[class*='avatar']",
        "[data-testid*='avatar']",
        "[href*='/user']",
        "[href*='/account']",
        "button:has-text('退出')",
        "button:has-text('登出')",
    )
    LOGGED_OUT_HINTS = ("登录", "手机号登录", "验证码登录", "注册")

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

    async def go_to_glm_coding(self):
        """Navigate to GLM Coding product page"""
        await self.navigator.navigate(f"{self.BASE_URL}/glm-coding")

    async def check_stock(self) -> Tuple[StockStatus, ProductInfo]:
        """
        Check stock status on GLM Coding page

        Looking for patterns like:
        - "暂时售罄" - Out of stock
        - "立即购买" - In stock
        - "05月11日 10:00 补货" - Restock time
        """
        try:
            # Wait for page to load
            await asyncio.sleep(3)

            # Get page body text
            body_text = await self.page.inner_text('body')

            # Default info
            product_info = ProductInfo(
                name="GLM Coding",
                status=StockStatus.UNKNOWN,
                last_updated=datetime.now()
            )

            # Check for out of stock text
            if '暂时售罄' in body_text:
                product_info.status = StockStatus.OUT_OF_STOCK
                logger.info("Found '暂时售罄' - Out of stock")

                # Try to extract restock time
                if '补货' in body_text:
                    # Look for patterns like "05月11日 10:00 补货"
                    lines = body_text.split('\n')
                    for line in lines:
                        if '补货' in line and '日' in line and ':' in line:
                            product_info.restock_time = line.strip()
                            logger.info(f"Found restock time: {product_info.restock_time}")
                            break

            # Check for in stock - look for buy buttons
            elif any(keyword in body_text for keyword in ['购买', '立即', '预约']):
                product_info.status = StockStatus.IN_STOCK
                logger.info("Found buy keywords - In stock!")

            else:
                logger.info("Could not determine stock status")

            # Try to find price
            if '¥' in body_text:
                lines = body_text.split('\n')
                for line in lines:
                    if '¥' in line and any(kw in line for kw in ['/', '月', '季', '年']):
                        product_info.price = line.strip()
                        break

            return product_info.status, product_info

        except Exception as e:
            logger.error(f"Stock check error: {e}")
            return StockStatus.UNKNOWN, ProductInfo(
                name="Unknown",
                status=StockStatus.UNKNOWN,
                last_updated=datetime.now(),
            )

    async def login(self, username: str, password: str) -> bool:
        """
        Perform login with username/password

        Note: Since we have cookies, this is optional
        """
        try:
            await asyncio.sleep(2)

            # Try common input selectors
            username_input = None
            for selector in [
                'input[type="text"]',
                'input[placeholder*="手机"]',
                'input[placeholder*="账号"]',
                'input[name*="phone"]',
                'input[name*="user"]',
            ]:
                try:
                    username_input = await self.page.wait_for_selector(selector, timeout=2000)
                    if username_input:
                        break
                except:
                    continue

            if username_input:
                await username_input.fill(username)

            password_input = None
            for selector in [
                'input[type="password"]',
                'input[placeholder*="密码"]',
                'input[name*="password"]',
            ]:
                try:
                    password_input = await self.page.wait_for_selector(selector, timeout=2000)
                    if password_input:
                        break
                except:
                    continue

            if password_input:
                await password_input.fill(password)

            # Click login button
            login_button = None
            for selector in [
                'button[type="submit"]',
                'button:has-text("登录")',
                'button:has-text("登 录")',
            ]:
                try:
                    login_button = await self.page.wait_for_selector(selector, timeout=2000)
                    if login_button:
                        break
                except:
                    continue

            if not login_button:
                # Try finding any button that looks like login
                buttons = await self.page.query_selector_all('button')
                for btn in buttons:
                    try:
                        text = await btn.inner_text()
                        if '登录' in text:
                            login_button = btn
                            break
                    except:
                        pass

            if login_button:
                await login_button.click()
                await asyncio.sleep(3)
                return await self._is_logged_in()

            logger.warning("Could not find login button")
            return False

        except Exception as e:
            logger.error(f"Login error: {e}")
            return False

    async def login_with_cookies(self, cookies: list) -> bool:
        """
        Login using cookies (PREFERRED METHOD)

        Args:
            cookies: List of cookie dicts with name, value, domain, etc.
        """
        try:
            context = self.page.context
            for cookie in cookies:
                # Make sure cookie has required fields
                cookie_copy = cookie.copy()
                if 'domain' not in cookie_copy:
                    cookie_copy['domain'] = 'bigmodel.cn'
                if 'path' not in cookie_copy:
                    cookie_copy['path'] = '/'

                await context.add_cookies([cookie_copy])

            await self.page.reload()
            await asyncio.sleep(3)
            logger.info("Cookies applied and page reloaded")
            return await self._is_logged_in()

        except Exception as e:
            logger.error(f"Cookie login error: {e}")
            return False

    async def purchase(self, timeout: int = 30000) -> Tuple[bool, Optional[str]]:
        """
        Attempt to purchase - looks for buy buttons on GLM Coding page

        Will try to find and click buttons like:
        - "立即购买"
        - "预约"
        - Any button that looks clickable and related to purchase
        """
        try:
            await asyncio.sleep(2)

            buy_button = None

            elements = await self.page.query_selector_all(
                'button, [role="button"], a, [class*="btn"], [class*="button"]'
            )
            for elem in elements:
                try:
                    text = (await elem.inner_text()).strip()
                    if not self._looks_like_purchase_action(text):
                        continue
                    if not await self._element_is_enabled(elem):
                        continue
                    buy_button = elem
                    logger.info(f"Found buy button with text: {text}")
                    break
                except Exception:
                    continue

            if buy_button:
                logger.info("Clicking buy button...")
                await buy_button.click()
                await asyncio.sleep(3)

                # Check for any confirmation popup
                confirm_button = None
                confirm_elements = await self.page.query_selector_all('button')
                for elem in confirm_elements:
                    try:
                        text = (await elem.inner_text()).strip()
                        if any(kw in text for kw in self.CONFIRM_KEYWORDS) and await self._element_is_enabled(elem):
                            confirm_button = elem
                            break
                    except Exception:
                        continue

                if confirm_button:
                    logger.info("Clicking confirmation button...")
                    await confirm_button.click()
                    await asyncio.sleep(3)

                # Check if purchase was successful
                body_text = await self.page.inner_text('body')
                success = any(kw in body_text for kw in ['成功', 'success', '订单', 'order'])

                order_id = None
                # Try to find order number
                if '订单' in body_text or 'order' in body_text.lower():
                    lines = body_text.split('\n')
                    for line in lines:
                        if any(kw in line.lower() for kw in ['订单', 'order', '单号']):
                            order_id = line.strip()
                            break

                return success, order_id

            else:
                logger.warning("Could not find any buy button - maybe still out of stock?")
                return False, None

        except Exception as e:
            logger.error(f"Purchase error: {e}")
            import traceback
            traceback.print_exc()
            return False, None

    async def _is_logged_in(self) -> bool:
        """Best-effort login verification after cookie or password login."""
        for selector in self.AUTHENTICATED_SELECTORS:
            try:
                element = await self.page.query_selector(selector)
                if element:
                    return True
            except Exception:
                continue

        try:
            body_text = await self.page.inner_text('body')
        except Exception:
            return False

        if any(hint in body_text for hint in self.LOGGED_OUT_HINTS):
            logger.warning("Login validation still sees logged-out hints")
            return False

        return False

    async def _element_is_enabled(self, element) -> bool:
        """Return whether an element appears clickable."""
        try:
            disabled_attr = await element.get_attribute('disabled')
            aria_disabled = await element.get_attribute('aria-disabled')
            classes = (await element.get_attribute('class')) or ''
        except Exception:
            return False

        if disabled_attr is not None:
            return False
        if aria_disabled and aria_disabled.lower() == 'true':
            return False
        if 'disabled' in classes.lower():
            return False
        return True

    def _looks_like_purchase_action(self, text: str) -> bool:
        """Keep button matching conservative to avoid accidental clicks."""
        if not text:
            return False
        normalized = text.strip()
        if any(keyword in normalized for keyword in self.BUY_BLOCKLIST):
            return False
        return any(keyword in normalized for keyword in self.BUY_KEYWORDS)

    async def save_screenshot(self, path: Optional[str] = None) -> bytes:
        """Take a screenshot"""
        if not path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = f"data/screenshots/{timestamp}.png"
        return await self.navigator.screenshot(path=path, full_page=False)

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

    if session:
        await session.apply_to_context(context)

    navigator = create_navigator(page)
    return BigModelPage(page, navigator)
