import pytest
from unittest.mock import AsyncMock, Mock

from bot.browser import BrowserManager
from bot.config import BrowserConfig, get_browser_config
from bot.fingerprint import Fingerprint, FingerprintManager
from bot.session import Session, SessionManager
from bot.proxy import ProxyConfig, ProxyManager
from bot.navigator import PageNavigator


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
    mock_page.reload = AsyncMock()
    mock_page.query_selector = AsyncMock(return_value=None)
    mock_page.inner_text = AsyncMock(return_value="请先登录\n手机号登录")

    page = BigModelPage(mock_page, Mock())

    result = await page.login_with_cookies([{"name": "session", "value": "abc"}])

    assert result is False


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


# Note: Full browser tests are not run by default as they require Playwright browsers
# These are just import and basic functionality tests
