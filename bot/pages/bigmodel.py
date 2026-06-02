import asyncio
import logging
from typing import Optional, Any, Tuple
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
    HIGH_DEMAND = "high_demand"
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
    BUY_KEYWORDS = (
        "购买",
        "立即购买",
        "立即开通",
        "立即抢购",
        "预约",
        "订阅",
        "即刻订阅",
        "特惠订阅",
        "订阅套餐",
        "去购买",
    )
    BUY_BLOCKLIST = ("帮助", "客服", "详情", "登录", "注册", "取消", "关闭", "暂不订阅")
    CONFIRM_KEYWORDS = ("确认购买", "立即支付", "去支付", "确认", "继续")
    PACKAGE_BUTTON_SELECTORS = (
        "button.buy-btn",
        "button[name='特惠订阅']",
        ".package-card-btn-box button",
    )
    HERO_BUTTON_SELECTORS = (
        ".subscribe-container button",
    )
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

            package_buttons = await self._find_elements(self.PACKAGE_BUTTON_SELECTORS)
            actionable_package_buttons = await self._filter_purchase_buttons(package_buttons)

            if actionable_package_buttons:
                product_info.status = StockStatus.IN_STOCK
                logger.info("Found actionable package subscribe button - In stock")

            elif await self._has_high_demand_package_buttons(package_buttons, body_text):
                product_info.status = StockStatus.HIGH_DEMAND
                logger.info("Found crowded package purchase window - High demand")

            elif await self._has_blocked_package_buttons(package_buttons, body_text):
                product_info.status = StockStatus.OUT_OF_STOCK
                logger.info("Found disabled package subscribe button - Out of stock")

            # Check for out of stock text
            elif '暂时售罄' in body_text:
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

            await self.page.goto(self.BASE_URL, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)
            logger.info("Cookies applied and page navigated")
            return await self._is_logged_in()

        except Exception as e:
            logger.error(f"Cookie login error: {e}")
            return False

    async def purchase(
        self,
        timeout: int = 30000,
        refresh_interval: float = 2.0,
    ) -> Tuple[bool, Optional[str]]:
        """Compatibility wrapper returning only success and order id."""
        result = await self.purchase_detailed(timeout=timeout, refresh_interval=refresh_interval)
        return result["success"], result.get("order_id")

    async def purchase_detailed(
        self,
        timeout: int = 30000,
        refresh_interval: float = 2.0,
    ) -> dict[str, Any]:
        """
        Attempt to purchase - looks for buy buttons on GLM Coding page

        Will try to find and click buttons like:
        - "立即购买"
        - "预约"
        - Any button that looks clickable and related to purchase
        """
        try:
            deadline = asyncio.get_running_loop().time() + max(timeout, 0) / 1000
            attempts = 0
            last_result: dict[str, Any] = {
                "success": False,
                "order_id": None,
                "reason": "not_started",
                "attempts": 0,
                "last_body_excerpt": "",
            }
            await asyncio.sleep(2)

            while True:
                buy_buttons = await self._find_purchase_buttons()
                buy_button = buy_buttons[0] if buy_buttons else None

                if buy_button:
                    attempts += 1
                    last_result = await self._complete_purchase(buy_button)
                    last_result["attempts"] = attempts
                    if last_result["success"]:
                        return last_result

                    now = asyncio.get_running_loop().time()
                    if now >= deadline:
                        logger.warning("Purchase click did not complete before timeout")
                        if last_result.get("reason") == "high_demand":
                            last_result["reason"] = "high_demand_retry_exhausted"
                        return last_result

                    logger.info("Purchase click did not complete, reloading page to retry")
                    await self.page.reload()
                    sleep_seconds = min(max(refresh_interval, 0), max(deadline - now, 0))
                    if sleep_seconds:
                        await asyncio.sleep(sleep_seconds)
                    continue

                now = asyncio.get_running_loop().time()
                if now >= deadline:
                    logger.warning("Could not find any buy button before purchase timeout")
                    return {
                        "success": False,
                        "order_id": None,
                        "reason": "no_purchase_button",
                        "attempts": attempts,
                        "last_body_excerpt": await self._safe_body_excerpt(),
                    }

                logger.info("No actionable buy button yet, reloading page to retry purchase")
                await self.page.reload()
                sleep_seconds = min(max(refresh_interval, 0), max(deadline - now, 0))
                if sleep_seconds:
                    await asyncio.sleep(sleep_seconds)

        except Exception as e:
            logger.error(f"Purchase error: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "order_id": None,
                "reason": "exception",
                "attempts": 0,
                "error": str(e),
                "last_body_excerpt": "",
            }

    async def _complete_purchase(self, buy_button) -> dict[str, Any]:
        """Click the purchase CTA and infer whether the order page succeeded."""
        logger.info("Clicking buy button...")
        await buy_button.click()
        await asyncio.sleep(3)

        confirm_button = await self._find_visible_confirmation_button()

        if confirm_button:
            logger.info("Clicking confirmation button...")
            await confirm_button.click(timeout=5000)
            await asyncio.sleep(3)

        body_text = await self.page.inner_text('body')
        success = any(kw in body_text for kw in ['成功', 'success', '订单', 'order']) or self._payment_page_reached(body_text)

        order_id = None
        if '订单' in body_text or 'order' in body_text.lower():
            lines = body_text.split('\n')
            for line in lines:
                if any(kw in line.lower() for kw in ['订单', 'order', '单号']):
                    order_id = line.strip()
                    break

        return {
            "success": success,
            "order_id": order_id,
            "reason": self._purchase_failure_reason(body_text) if not success else self._purchase_success_reason(body_text),
            "attempts": 1,
            "last_body_excerpt": self._body_excerpt(body_text),
        }

    async def _find_visible_confirmation_button(self):
        """Pick only a visible confirmation/payment-step button after the buy CTA."""
        confirm_elements = await self.page.query_selector_all('button')
        for elem in confirm_elements:
            try:
                text = (await elem.inner_text()).strip()
            except Exception:
                continue
            if not any(kw in text for kw in self.CONFIRM_KEYWORDS):
                continue
            if not await self._element_is_visible(elem):
                continue
            if not await self._element_is_enabled(elem):
                continue
            return elem
        return None

    async def _safe_body_excerpt(self) -> str:
        """Best-effort body excerpt for diagnostics without storing full page text."""
        try:
            return self._body_excerpt(await self.page.inner_text('body'))
        except Exception:
            return ""

    def _purchase_failure_reason(self, body_text: str) -> str:
        """Classify the most useful purchase failure reason from visible page text."""
        if "抢购人数过多" in body_text or "刷新再试" in body_text:
            return "high_demand"
        if any(hint in body_text for hint in self.LOGGED_OUT_HINTS):
            return "logged_out"
        if "暂时售罄" in body_text or "售罄" in body_text:
            return "sold_out"
        return "unknown_after_click"

    def _purchase_success_reason(self, body_text: str) -> str:
        """Classify successful stop points in the purchase flow."""
        if self._payment_page_reached(body_text):
            return "payment_page_reached"
        return "order_created"

    @staticmethod
    def _payment_page_reached(body_text: str) -> bool:
        """Detect the order payment page without clicking any final payment provider action."""
        payment_hints = ("支付金额", "支付方式", "微信支付", "支付宝", "付款", "二维码")
        return any(hint in body_text for hint in payment_hints)

    @staticmethod
    def _body_excerpt(body_text: str, limit: int = 500) -> str:
        """Keep diagnostics compact and avoid storing a full page dump."""
        return " ".join(body_text.split())[:limit]

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

    async def _find_purchase_buttons(self) -> list:
        """Prefer real package purchase buttons, then fall back to hero CTA only if needed."""
        package_buttons = await self._find_elements(self.PACKAGE_BUTTON_SELECTORS)
        actionable_package_buttons = await self._filter_purchase_buttons(package_buttons)
        if package_buttons:
            return actionable_package_buttons

        hero_buttons = await self._find_elements(self.HERO_BUTTON_SELECTORS)
        actionable_hero_buttons = await self._filter_purchase_buttons(hero_buttons)
        if actionable_hero_buttons:
            return actionable_hero_buttons

        generic_elements = await self._find_elements(
            ('button, [role="button"], a, [class*="btn"], [class*="button"]',)
        )
        return await self._filter_purchase_buttons(generic_elements)

    async def _find_elements(self, selectors: tuple[str, ...]) -> list:
        """Collect unique elements for the given selectors."""
        found = []
        seen = set()

        for selector in selectors:
            try:
                elements = await self.page.query_selector_all(selector)
            except Exception:
                continue

            for element in elements:
                if id(element) in seen:
                    continue
                found.append(element)
                seen.add(id(element))

        return found

    async def _filter_purchase_buttons(self, elements: list) -> list:
        """Keep only actionable purchase CTAs from a list of elements."""
        actionable = []
        for element in elements:
            if await self._element_is_actionable_purchase(element):
                actionable.append(element)
        return actionable

    async def _has_blocked_package_buttons(self, elements: list, body_text: str) -> bool:
        """Detect sold-out or rate-limited package buttons on the live page."""
        if not elements:
            return False

        for element in elements:
            try:
                text = (await element.inner_text()).strip()
            except Exception:
                continue
            if not self._looks_like_purchase_action(text) and "抢购人数过多" not in text:
                continue
            if not await self._element_is_visible(element):
                continue
            if not await self._element_is_enabled(element):
                return True
        return False

    async def _has_high_demand_package_buttons(self, elements: list, body_text: str) -> bool:
        """Detect the crowded-but-active purchase window shown by BigModel."""
        if not elements or "抢购人数过多，请刷新再试" not in body_text:
            return False

        for element in elements:
            try:
                text = (await element.inner_text()).strip()
            except Exception:
                continue
            if "抢购人数过多" in text and await self._element_is_visible(element):
                return True
        return False

    async def _element_is_actionable_purchase(self, element) -> bool:
        """Whether this element looks like a real purchase CTA on the live page."""
        try:
            text = (await element.inner_text()).strip()
        except Exception:
            return False

        if not self._looks_like_purchase_action(text):
            return False
        if not await self._element_is_enabled(element):
            return False
        if not await self._element_is_visible(element):
            return False

        logger.info(f"Found buy button with text: {text}")
        return True

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

    async def _element_is_visible(self, element) -> bool:
        """Best-effort visibility check so hidden modal actions do not win."""
        try:
            if hasattr(element, "bounding_box"):
                box = await element.bounding_box()
                if box:
                    return True
        except Exception:
            pass

        try:
            style = await element.get_attribute("style") or ""
            if "display: none" in style.lower() or "visibility: hidden" in style.lower():
                return False
        except Exception:
            pass

        return not hasattr(element, "bounding_box")

    def _looks_like_purchase_action(self, text: str) -> bool:
        """Keep button matching conservative to avoid accidental clicks."""
        if not text:
            return False
        normalized = text.strip()
        if len(normalized) > 24:
            return False
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
