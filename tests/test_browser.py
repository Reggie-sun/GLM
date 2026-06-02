import pytest
from unittest.mock import AsyncMock, Mock, patch

from bot.browser import BrowserManager
from bot.config import BrowserConfig, get_browser_config
from bot.fingerprint import Fingerprint, FingerprintManager
from bot.session import Session, SessionManager
from bot.proxy import ProxyConfig, ProxyManager
from bot.navigator import PageNavigator
from bot.pages.bigmodel import StockStatus


def test_browser_config():
    """Test browser config creation"""
    config = BrowserConfig(
        headless=True,
        viewport_width=1920,
        viewport_height=1080,
    )
    assert config.headless is True
    assert config.viewport_width == 1920
    assert config.viewport_height == 1080


def test_get_browser_config():
    """Test get browser config function"""
    config = get_browser_config()
    assert config is not None


def test_fingerprint_creation():
    """Test fingerprint creation"""
    fp = Fingerprint(
        user_agent="test-user-agent",
        platform="Win32",
    )
    assert fp.user_agent == "test-user-agent"
    assert fp.platform == "Win32"


def test_fingerprint_to_dict():
    """Test fingerprint to dict conversion"""
    fp = Fingerprint(user_agent="test", platform="Win32")
    data = fp.to_dict()
    assert "user_agent" in data
    assert "platform" in data


def test_fingerprint_from_dict():
    """Test fingerprint from dict"""
    data = {"user_agent": "test", "platform": "Win32"}
    fp = Fingerprint.from_dict(data)
    assert fp.user_agent == "test"


def test_fingerprint_manager():
    """Test fingerprint manager"""
    fp_manager = FingerprintManager(storage_dir="/tmp/test_fingerprints")
    fp = fp_manager.generate("test")
    assert fp is not None
    loaded = fp_manager.get("test")
    assert loaded is not None
    assert loaded.user_agent == fp.user_agent


def test_session_creation():
    """Test session creation"""
    session = Session(session_id="test-session")
    assert session.session_id == "test-session"
    assert session.cookies == []
    assert session.local_storage == {}


def test_session_to_dict():
    """Test session to dict"""
    session = Session(session_id="test")
    data = session.to_dict()
    assert "session_id" in data
    assert "cookies" in data


def test_session_manager():
    """Test session manager"""
    session_manager = SessionManager(storage_dir="/tmp/test_sessions")
    session = session_manager.create("test-session")
    assert session is not None
    loaded = session_manager.get("test-session")
    assert loaded is not None
    assert loaded.session_id == "test-session"


def test_proxy_config():
    """Test proxy config"""
    proxy = ProxyConfig(
        server="127.0.0.1:8080",
        username="test",
        password="testpass",
    )
    assert proxy.server == "127.0.0.1:8080"
    assert proxy.username == "test"


def test_proxy_config_to_playwright():
    """Test proxy config to playwright dict"""
    proxy = ProxyConfig(server="127.0.0.1:8080")
    pd = proxy.to_playwright_dict()
    assert pd["server"] == "127.0.0.1:8080"


def test_proxy_manager():
    """Test proxy manager"""
    proxy_manager = ProxyManager()
    proxy = ProxyConfig(server="127.0.0.1:8080")
    proxy_manager.add_proxy(proxy)
    assert proxy_manager.count == 1


def test_proxy_manager_get_random():
    """Test proxy manager get random"""
    proxy_manager = ProxyManager()
    assert proxy_manager.get_random() is None
    proxy = ProxyConfig(server="127.0.0.1:8080")
    proxy_manager.add_proxy(proxy)
    assert proxy_manager.get_random() is not None


def test_browser_manager_import():
    """Test browser manager can be imported"""
    assert BrowserManager is not None


def test_page_navigator_import():
    """Test page navigator can be imported"""
    assert PageNavigator is not None


@pytest.mark.asyncio
async def test_bigmodel_page_login():
    """Test BigModelPage login method structure"""
    from bot.pages.bigmodel import BigModelPage

    # Create mock page and navigator
    mock_page = Mock()
    mock_navigator = Mock()
    mock_navigator.fill = AsyncMock()
    mock_navigator.click = AsyncMock()
    mock_navigator.wait_for_load_state = AsyncMock()
    mock_navigator.is_visible = AsyncMock(return_value=True)

    page = BigModelPage(mock_page, mock_navigator)

    # Just test the method signature and basic structure
    result = await page.login("testuser", "testpass")

    # Result should be boolean
    assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_bigmodel_page_purchase():
    """Test BigModelPage purchase method structure"""
    from bot.pages.bigmodel import BigModelPage

    # Create mock page and navigator
    mock_page = Mock()
    mock_navigator = Mock()
    mock_navigator.click = AsyncMock()
    mock_navigator.wait_for_load_state = AsyncMock()
    mock_navigator.is_visible = AsyncMock(return_value=True)
    mock_navigator.get_text = AsyncMock(return_value="ORDER-123")

    page = BigModelPage(mock_page, mock_navigator)

    # Just test the method signature and basic structure
    success, order_id = await page.purchase()

    # Result should be tuple of (bool, Optional[str])
    assert isinstance(success, bool)
    assert order_id is None or isinstance(order_id, str)


@pytest.mark.asyncio
async def test_login_with_cookies_requires_logged_in_signal():
    """Cookie login should fail when the page still looks logged out."""
    from bot.pages.bigmodel import BigModelPage

    mock_page = Mock()
    mock_page.context = Mock()
    mock_page.context.add_cookies = AsyncMock()
    mock_page.goto = AsyncMock()
    mock_page.query_selector = AsyncMock(return_value=None)
    mock_page.inner_text = AsyncMock(return_value="请先登录\n手机号登录")

    page = BigModelPage(mock_page, Mock())

    result = await page.login_with_cookies([{"name": "session", "value": "abc"}])

    assert result is False
    mock_page.goto.assert_awaited_once_with(
        BigModelPage.BASE_URL,
        wait_until="domcontentloaded",
        timeout=30000,
    )


@pytest.mark.asyncio
async def test_purchase_does_not_click_non_purchase_button():
    """Purchase should ignore unrelated clickable elements."""
    from bot.pages.bigmodel import BigModelPage

    help_button = Mock()
    help_button.inner_text = AsyncMock(return_value="帮助")
    help_button.get_attribute = AsyncMock(return_value="")
    help_button.click = AsyncMock()

    mock_page = Mock()
    mock_page.query_selector_all = AsyncMock(side_effect=[[help_button], [help_button]])
    mock_page.inner_text = AsyncMock(return_value="当前页面只有帮助按钮")

    page = BigModelPage(mock_page, Mock())
    success, order_id = await page.purchase()

    assert success is False
    assert order_id is None
    help_button.click.assert_not_called()


@pytest.mark.asyncio
async def test_purchase_prefers_real_buy_button_over_modal_actions():
    """Real package purchase buttons should win over hidden modal actions."""
    from bot.pages.bigmodel import BigModelPage

    continue_button = Mock()
    continue_button.inner_text = AsyncMock(return_value="继续订阅")
    continue_button.get_attribute = AsyncMock(side_effect=lambda name: "" if name != "class" else "el-button")
    continue_button.bounding_box = AsyncMock(return_value=None)
    continue_button.click = AsyncMock()

    buy_button = Mock()
    buy_button.inner_text = AsyncMock(return_value="特惠订阅")
    buy_button.get_attribute = AsyncMock(side_effect=lambda name: "el-button buy-btn" if name == "class" else None)
    buy_button.bounding_box = AsyncMock(return_value={"x": 10, "y": 10, "width": 120, "height": 40})
    buy_button.click = AsyncMock()

    mock_page = Mock()

    async def query_selector_all(selector):
        if selector == "button.buy-btn":
            return [buy_button]
        if selector == 'button, [role="button"], a, [class*="btn"], [class*="button"]':
            return [continue_button, buy_button]
        if selector == "button":
            return [continue_button]
        return []

    mock_page.query_selector_all = AsyncMock(side_effect=query_selector_all)
    mock_page.inner_text = AsyncMock(return_value="订单 创建成功")

    page = BigModelPage(mock_page, Mock())
    success, order_id = await page.purchase()

    assert success is True
    assert order_id is None or isinstance(order_id, str)
    buy_button.click.assert_called_once()
    continue_button.click.assert_not_called()


@pytest.mark.asyncio
async def test_check_stock_detects_real_subscribe_button():
    """Visible subscribe buttons on the live page should count as in stock."""
    from bot.pages.bigmodel import BigModelPage

    buy_button = Mock()
    buy_button.inner_text = AsyncMock(return_value="特惠订阅")
    buy_button.get_attribute = AsyncMock(side_effect=lambda name: "el-button buy-btn" if name == "class" else None)
    buy_button.bounding_box = AsyncMock(return_value={"x": 10, "y": 10, "width": 120, "height": 40})

    mock_page = Mock()
    mock_page.inner_text = AsyncMock(return_value="GLM Coding Plan\n特惠订阅\n¥134.1/月")
    mock_page.query_selector_all = AsyncMock(side_effect=[[buy_button]])

    page = BigModelPage(mock_page, Mock())
    status, product = await page.check_stock()

    assert status == StockStatus.IN_STOCK
    assert product.status == StockStatus.IN_STOCK


@pytest.mark.asyncio
async def test_check_stock_treats_crowded_package_buttons_as_high_demand():
    """Crowded live package buttons should trigger a high-demand purchase window."""
    from bot.pages.bigmodel import BigModelPage

    disabled_buy_button = Mock()
    disabled_buy_button.inner_text = AsyncMock(return_value="抢购人数过多，请刷新再试")
    disabled_buy_button.get_attribute = AsyncMock(
        side_effect=lambda name: "el-button buy-btn is-disabled disabled" if name == "class" else None
    )
    disabled_buy_button.bounding_box = AsyncMock(return_value={"x": 10, "y": 10, "width": 120, "height": 40})

    hero_button = Mock()
    hero_button.inner_text = AsyncMock(return_value="即刻订阅")
    hero_button.get_attribute = AsyncMock(side_effect=lambda name: "el-button el-button--default" if name == "class" else None)
    hero_button.bounding_box = AsyncMock(return_value={"x": 10, "y": 10, "width": 120, "height": 40})

    mock_page = Mock()

    async def query_selector_all(selector):
        if selector == "button.buy-btn":
            return [disabled_buy_button]
        if selector == '.package-card-btn-box button':
            return [disabled_buy_button]
        if selector == '.subscribe-container button':
            return [hero_button]
        if selector == 'button, [role="button"], a, [class*="btn"], [class*="button"]':
            return [hero_button, disabled_buy_button]
        return []

    mock_page.query_selector_all = AsyncMock(side_effect=query_selector_all)
    mock_page.inner_text = AsyncMock(return_value="GLM Coding Plan\n抢购人数过多，请刷新再试\n即刻订阅")

    page = BigModelPage(mock_page, Mock())
    status, product = await page.check_stock()

    assert status == StockStatus.HIGH_DEMAND
    assert product.status == StockStatus.HIGH_DEMAND


@pytest.mark.asyncio
async def test_purchase_does_not_fall_back_to_hero_when_package_buttons_disabled():
    """When live package buttons are disabled, purchase should not click the hero CTA."""
    from bot.pages.bigmodel import BigModelPage

    disabled_buy_button = Mock()
    disabled_buy_button.inner_text = AsyncMock(return_value="抢购人数过多，请刷新再试")
    disabled_buy_button.get_attribute = AsyncMock(
        side_effect=lambda name: "el-button buy-btn is-disabled disabled" if name == "class" else None
    )
    disabled_buy_button.bounding_box = AsyncMock(return_value={"x": 10, "y": 10, "width": 120, "height": 40})
    disabled_buy_button.click = AsyncMock()

    hero_button = Mock()
    hero_button.inner_text = AsyncMock(return_value="即刻订阅")
    hero_button.get_attribute = AsyncMock(side_effect=lambda name: "el-button el-button--default" if name == "class" else None)
    hero_button.bounding_box = AsyncMock(return_value={"x": 10, "y": 10, "width": 120, "height": 40})
    hero_button.click = AsyncMock()

    mock_page = Mock()

    async def query_selector_all(selector):
        if selector == "button.buy-btn":
            return [disabled_buy_button]
        if selector == '.package-card-btn-box button':
            return [disabled_buy_button]
        if selector == '.subscribe-container button':
            return [hero_button]
        if selector == 'button, [role="button"], a, [class*="btn"], [class*="button"]':
            return [hero_button, disabled_buy_button]
        if selector == "button":
            return [disabled_buy_button, hero_button]
        return []

    mock_page.query_selector_all = AsyncMock(side_effect=query_selector_all)
    mock_page.inner_text = AsyncMock(return_value="GLM Coding Plan\n抢购人数过多，请刷新再试\n即刻订阅")

    page = BigModelPage(mock_page, Mock())
    success, order_id = await page.purchase()

    assert success is False
    assert order_id is None
    disabled_buy_button.click.assert_not_called()
    hero_button.click.assert_not_called()


@pytest.mark.asyncio
async def test_purchase_reloads_until_package_button_appears():
    """Purchase should keep reloading the page until a real package button appears."""
    from bot.pages.bigmodel import BigModelPage

    buy_button = Mock()
    buy_button.inner_text = AsyncMock(return_value="特惠订阅")
    buy_button.get_attribute = AsyncMock(side_effect=lambda name: "el-button buy-btn" if name == "class" else None)
    buy_button.bounding_box = AsyncMock(return_value={"x": 10, "y": 10, "width": 120, "height": 40})
    buy_button.click = AsyncMock()

    poll_count = {"value": 0}

    mock_page = Mock()
    mock_page.reload = AsyncMock()
    mock_page.inner_text = AsyncMock(return_value="GLM Coding Plan\n订单 创建成功")

    async def query_selector_all(selector):
        if selector == "button.buy-btn":
            poll_count["value"] += 1
            return [] if poll_count["value"] == 1 else [buy_button]
        if selector == '.package-card-btn-box button':
            return []
        if selector == '.subscribe-container button':
            return []
        if selector == 'button, [role="button"], a, [class*="btn"], [class*="button"]':
            return []
        if selector == "button":
            return []
        return []

    mock_page.query_selector_all = AsyncMock(side_effect=query_selector_all)

    page = BigModelPage(mock_page, Mock())
    with patch("bot.pages.bigmodel.asyncio.sleep", new=AsyncMock()):
        success, order_id = await page.purchase(timeout=100, refresh_interval=0)

    assert success is True
    assert order_id is None or isinstance(order_id, str)
    assert poll_count["value"] >= 2
    mock_page.reload.assert_awaited_once()
    buy_button.click.assert_called_once()


@pytest.mark.asyncio
async def test_purchase_retries_after_crowded_click_failure():
    """Purchase should keep trying when the first click hits a crowded refresh state."""
    from bot.pages.bigmodel import BigModelPage

    buy_button = Mock()
    buy_button.inner_text = AsyncMock(return_value="特惠订阅")
    buy_button.get_attribute = AsyncMock(
        side_effect=lambda name: "el-button buy-btn" if name == "class" else None
    )
    buy_button.bounding_box = AsyncMock(return_value={"x": 10, "y": 10, "width": 120, "height": 40})
    buy_button.click = AsyncMock()

    mock_page = Mock()
    mock_page.reload = AsyncMock()
    mock_page.inner_text = AsyncMock(
        side_effect=[
            "GLM Coding Plan\n抢购人数过多，请刷新再试",
            "GLM Coding Plan\n订单 创建成功",
        ]
    )

    async def query_selector_all(selector):
        if selector == "button.buy-btn":
            return [buy_button]
        if selector == '.package-card-btn-box button':
            return []
        if selector == '.subscribe-container button':
            return []
        if selector == 'button, [role="button"], a, [class*="btn"], [class*="button"]':
            return []
        if selector == "button":
            return []
        return []

    mock_page.query_selector_all = AsyncMock(side_effect=query_selector_all)

    page = BigModelPage(mock_page, Mock())
    with patch("bot.pages.bigmodel.asyncio.sleep", new=AsyncMock()):
        success, order_id = await page.purchase(timeout=100, refresh_interval=0)

    assert success is True
    assert order_id is None or isinstance(order_id, str)
    assert buy_button.click.await_count == 2
    mock_page.reload.assert_awaited_once()


@pytest.mark.asyncio
async def test_purchase_detailed_reports_no_button_timeout_reason():
    """Detailed purchase results should explain when no purchase button appears."""
    from bot.pages.bigmodel import BigModelPage

    mock_page = Mock()
    mock_page.reload = AsyncMock()
    mock_page.inner_text = AsyncMock(return_value="GLM Coding Plan\n暂时售罄")
    mock_page.query_selector_all = AsyncMock(return_value=[])

    page = BigModelPage(mock_page, Mock())
    with patch("bot.pages.bigmodel.asyncio.sleep", new=AsyncMock()):
        result = await page.purchase_detailed(timeout=0, refresh_interval=0)

    assert result["success"] is False
    assert result["reason"] == "no_purchase_button"
    assert result["attempts"] == 0


@pytest.mark.asyncio
async def test_purchase_detailed_reports_crowded_retry_exhausted_reason():
    """Detailed purchase results should preserve the crowded retry failure reason."""
    from bot.pages.bigmodel import BigModelPage

    buy_button = Mock()
    buy_button.inner_text = AsyncMock(return_value="特惠订阅")
    buy_button.get_attribute = AsyncMock(
        side_effect=lambda name: "el-button buy-btn" if name == "class" else None
    )
    buy_button.bounding_box = AsyncMock(return_value={"x": 10, "y": 10, "width": 120, "height": 40})
    buy_button.click = AsyncMock()

    mock_page = Mock()
    mock_page.reload = AsyncMock()
    mock_page.inner_text = AsyncMock(return_value="GLM Coding Plan\n抢购人数过多，请刷新再试")

    async def query_selector_all(selector):
        if selector == "button.buy-btn":
            return [buy_button]
        if selector == "button":
            return []
        return []

    mock_page.query_selector_all = AsyncMock(side_effect=query_selector_all)

    page = BigModelPage(mock_page, Mock())
    with patch("bot.pages.bigmodel.asyncio.sleep", new=AsyncMock()):
        result = await page.purchase_detailed(timeout=0, refresh_interval=0)

    assert result["success"] is False
    assert result["reason"] == "high_demand_retry_exhausted"
    assert result["attempts"] == 1
    assert "抢购人数过多" in result["last_body_excerpt"]


@pytest.mark.asyncio
async def test_confirmation_button_must_be_visible():
    """Hidden confirmation/payment-step buttons should not be clicked."""
    from bot.pages.bigmodel import BigModelPage

    hidden_button = Mock()
    hidden_button.inner_text = AsyncMock(return_value="去支付")
    hidden_button.get_attribute = AsyncMock(return_value=None)
    hidden_button.bounding_box = AsyncMock(return_value=None)

    visible_button = Mock()
    visible_button.inner_text = AsyncMock(return_value="去支付")
    visible_button.get_attribute = AsyncMock(return_value=None)
    visible_button.bounding_box = AsyncMock(return_value={"x": 10, "y": 10, "width": 120, "height": 40})

    mock_page = Mock()
    mock_page.query_selector_all = AsyncMock(return_value=[hidden_button, visible_button])

    page = BigModelPage(mock_page, Mock())

    result = await page._find_visible_confirmation_button()

    assert result is visible_button


def test_payment_page_reached_detects_payment_hints():
    """Payment-page text should count as the requested purchase-flow stop point."""
    from bot.pages.bigmodel import BigModelPage

    assert BigModelPage._payment_page_reached("订单已创建\n微信支付\n支付金额 ¥499") is True


# Note: Full browser tests are not run by default as they require Playwright browsers
# These are just import and basic functionality tests
