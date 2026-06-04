import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio
from datetime import datetime

from app.monitor.scheduler import MonitorScheduler
from app.monitor.tasks import MonitorTask, TaskStatus
from app.models.account import Account
from bot.pages.bigmodel import BigModelPage, StockStatus, ProductInfo


@pytest.mark.asyncio
async def test_attempt_purchase_without_account():
    """Test purchase attempt without account configured"""
    scheduler = MonitorScheduler()

    task = MonitorTask(
        task_id="test-1",
        name="Test Task",
        target_url="https://example.com",
        check_interval=30,
        auto_purchase=True,
        account_id=None,
    )

    result = await scheduler._attempt_purchase(task)

    assert result["success"] is False
    assert "No account configured" in result["message"]


@pytest.mark.asyncio
async def test_attempt_purchase_with_account():
    """Test purchase attempt with account configured"""
    scheduler = MonitorScheduler()

    task = MonitorTask(
        task_id="test-1",
        name="Test Task",
        target_url="https://example.com",
        check_interval=30,
        auto_purchase=True,
        account_id=1,
    )

    # Mock account retrieval and browser
    with patch('app.monitor.scheduler.get_db') as mock_get_db:
        mock_db = Mock()
        mock_account = Account(
            id=1,
            username="testuser",
            password="testpass",
            status="active",
            is_public=True,
        )
        mock_db.query.return_value.filter.return_value.first.return_value = mock_account
        # get_db is a generator, so we need to make it return an iterator
        mock_get_db.return_value = iter([mock_db])

        with patch.object(scheduler, '_execute_purchase_flow', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {"success": True, "order_id": "12345"}

            result = await scheduler._attempt_purchase(task)

            assert result["success"] is True
            assert "order_id" in result


@pytest.mark.asyncio
async def test_purchase_sends_notification():
    """Test that purchase attempt sends notification"""
    scheduler = MonitorScheduler()

    task = MonitorTask(
        task_id="test-1",
        name="Test Task",
        target_url="https://example.com",
        check_interval=30,
        auto_purchase=True,
        account_id=1,
    )

    with patch('app.monitor.scheduler.get_db') as mock_get_db:
        mock_db = Mock()
        mock_account = Account(id=1, username="testuser", password="testpass", status="active", is_public=True)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_account
        mock_get_db.return_value = iter([mock_db])

        with patch.object(scheduler, '_execute_purchase_flow', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {"success": True, "order_id": "12345"}

            with patch('app.monitor.scheduler.get_notification_service') as mock_notification:
                mock_service = Mock()
                mock_service.send = AsyncMock()
                mock_notification.return_value = mock_service

                await scheduler._attempt_purchase(task)

                # Verify notification was sent
                mock_service.send.assert_called_once()


@pytest.mark.asyncio
async def test_monitor_task_waits_for_scheduler_start():
    """Tasks created before scheduler start should remain pending in the loop."""
    scheduler = MonitorScheduler()
    task = MonitorTask(
        task_id="wait-start",
        name="Wait Start",
        target_url="https://example.com",
        check_interval=30,
        auto_purchase=False,
    )

    task_id = await scheduler.start_monitor(task)
    await asyncio.sleep(0.05)

    assert task_id in scheduler._tasks
    assert scheduler._tasks[task_id].done() is False

    await scheduler.stop_monitor(task_id)


@pytest.mark.asyncio
async def test_initial_in_stock_triggers_auto_purchase():
    """The first in-stock observation should trigger one purchase attempt."""
    scheduler = MonitorScheduler()
    task = MonitorTask(
        task_id="initial-stock",
        name="Initial Stock",
        target_url="https://example.com",
        check_interval=30,
        auto_purchase=True,
        account_id=1,
    )

    async def fake_attempt(_: MonitorTask):
        task.status = TaskStatus.STOPPED
        return {"success": True, "order_id": "12345"}

    scheduler._check_stock_once = AsyncMock(return_value={"status": StockStatus.IN_STOCK})
    scheduler._attempt_purchase = AsyncMock(side_effect=fake_attempt)

    await scheduler.start()
    await scheduler.start_monitor(task)
    await asyncio.sleep(0.05)

    scheduler._attempt_purchase.assert_awaited_once()
    await scheduler.stop()


@pytest.mark.asyncio
async def test_initial_high_demand_triggers_auto_purchase():
    """A crowded purchase window should trigger one purchase attempt."""
    scheduler = MonitorScheduler()
    task = MonitorTask(
        task_id="initial-high-demand",
        name="Initial High Demand",
        target_url="https://example.com",
        check_interval=30,
        auto_purchase=True,
        account_id=1,
    )

    async def fake_attempt(_: MonitorTask):
        task.status = TaskStatus.STOPPED
        return {"success": False, "message": "retry window exhausted"}

    scheduler._check_stock_once = AsyncMock(return_value={"status": StockStatus.HIGH_DEMAND})
    scheduler._attempt_purchase = AsyncMock(side_effect=fake_attempt)

    await scheduler.start()
    await scheduler.start_monitor(task)
    await asyncio.sleep(0.05)

    scheduler._attempt_purchase.assert_awaited_once()
    await scheduler.stop()


@pytest.mark.asyncio
async def test_failed_high_demand_purchase_can_retry_next_check():
    """A failed crowded-window attempt should not suppress future retries."""
    scheduler = MonitorScheduler()
    task = MonitorTask(
        task_id="retry-high-demand",
        name="Retry High Demand",
        target_url="https://example.com",
        check_interval=30,
        auto_purchase=True,
        account_id=1,
    )

    async def fake_attempt(_: MonitorTask):
        task.status = TaskStatus.STOPPED
        return {"success": False, "message": "retry window exhausted"}

    scheduler._check_stock_once = AsyncMock(return_value={"status": StockStatus.HIGH_DEMAND})
    scheduler._attempt_purchase = AsyncMock(side_effect=fake_attempt)

    await scheduler.start()
    await scheduler.start_monitor(task)
    await asyncio.sleep(0.05)

    assert task.purchase_attempted is False
    await scheduler.stop()


def test_next_check_delay_speeds_up_before_restock_time():
    """Checks should accelerate shortly before a known restock time."""
    scheduler = MonitorScheduler()
    task = MonitorTask(
        task_id="restock-burst",
        name="Restock Burst",
        target_url="https://example.com",
        check_interval=30,
    )

    now = datetime(2026, 5, 14, 9, 56, 30)
    result = {
        "status": StockStatus.OUT_OF_STOCK,
        "restock_time": "暂时售罄 ｜05月14日 10:00 补货",
    }

    assert scheduler._next_check_delay(task, result, now=now) == 5


def test_next_check_delay_uses_hot_polling_at_restock_time():
    """Checks should use the fastest bounded polling at the restock moment."""
    scheduler = MonitorScheduler()
    task = MonitorTask(
        task_id="restock-hot",
        name="Restock Hot",
        target_url="https://example.com",
        check_interval=30,
    )

    now = datetime(2026, 5, 14, 10, 0, 10)
    result = {
        "status": StockStatus.OUT_OF_STOCK,
        "restock_time": "暂时售罄 ｜05月14日 10:00 补货",
    }

    assert scheduler._next_check_delay(task, result, now=now) == 2


def test_next_check_delay_keeps_normal_interval_when_restock_is_far():
    """Normal monitoring should not accelerate hours before restock."""
    scheduler = MonitorScheduler()
    task = MonitorTask(
        task_id="restock-normal",
        name="Restock Normal",
        target_url="https://example.com",
        check_interval=30,
    )

    now = datetime(2026, 5, 14, 9, 0, 0)
    result = {
        "status": StockStatus.OUT_OF_STOCK,
        "restock_time": "暂时售罄 ｜05月14日 10:00 补货",
    }

    assert scheduler._next_check_delay(task, result, now=now) == 30


@pytest.mark.asyncio
async def test_check_stock_once_uses_account_cookie_for_account_specific_status():
    """Stock checks should use the task account's cookies when an account is configured."""
    scheduler = MonitorScheduler()

    task = MonitorTask(
        task_id="account-aware-stock",
        name="Account Aware Stock",
        target_url="https://example.com",
        check_interval=30,
        auto_purchase=False,
        account_id=1,
    )

    mock_context = Mock()
    mock_context.close = AsyncMock()

    mock_browser_manager = Mock()
    mock_browser_manager.create_context = AsyncMock(return_value=mock_context)
    scheduler.browser_manager = mock_browser_manager

    mock_page = Mock()
    mock_page.go_to_home = AsyncMock()
    mock_page.go_to_glm_coding = AsyncMock()
    mock_page.login_with_cookies = AsyncMock(return_value=True)
    mock_page.login = AsyncMock(return_value=False)
    mock_page.check_stock = AsyncMock(
        return_value=(
            StockStatus.OUT_OF_STOCK,
            ProductInfo(name="GLM Coding", status=StockStatus.OUT_OF_STOCK),
        )
    )

    with patch('app.monitor.scheduler.get_db') as mock_get_db:
        mock_db = Mock()
        mock_account = Account(
            id=1,
            username="whdgfr07",
            password="cookie_only",
            status="active",
            is_public=False,
            cookie='[{"name":"session","value":"abc","domain":"bigmodel.cn","path":"/"}]',
        )
        mock_db.query.return_value.filter.return_value.first.return_value = mock_account
        mock_get_db.return_value = iter([mock_db])

        with patch('app.monitor.scheduler.create_bigmodel_page', new=AsyncMock(return_value=mock_page)):
            result = await scheduler._check_stock_once(task)

    assert result["status"] == StockStatus.OUT_OF_STOCK
    mock_page.go_to_home.assert_awaited_once()
    mock_page.login_with_cookies.assert_awaited_once()
    mock_page.check_stock.assert_awaited_once()


@pytest.mark.asyncio
async def test_execute_purchase_flow_returns_detailed_failure_reason():
    """Purchase flow should preserve page-level failure diagnostics."""
    scheduler = MonitorScheduler()

    task = MonitorTask(
        task_id="detailed-purchase",
        name="Detailed Purchase",
        target_url="https://example.com",
        check_interval=30,
        auto_purchase=True,
        account_id=1,
    )
    db_account = Account(id=1, username="whdgfr07", password="", status="active")

    mock_context = Mock()
    mock_context.close = AsyncMock()

    mock_browser_manager = Mock()
    mock_browser_manager.create_context = AsyncMock(return_value=mock_context)
    scheduler.browser_manager = mock_browser_manager

    mock_page = Mock()
    mock_page.go_to_glm_coding = AsyncMock()
    mock_page.purchase_detailed = AsyncMock(
        return_value={
            "success": False,
            "order_id": None,
            "reason": "high_demand_retry_exhausted",
            "attempts": 3,
            "last_body_excerpt": "抢购人数过多，请刷新再试",
        }
    )

    with patch.object(scheduler, "_login_page_with_account", new=AsyncMock(return_value=True)):
        with patch("app.monitor.scheduler.create_bigmodel_page", new=AsyncMock(return_value=mock_page)):
            result = await scheduler._execute_purchase_flow(task, db_account)

    assert result["success"] is False
    assert result["reason"] == "high_demand_retry_exhausted"
    assert result["attempts"] == 3
    assert "抢购人数过多" in result["last_body_excerpt"]
    mock_page.purchase_detailed.assert_awaited_once()


@pytest.mark.asyncio
async def test_purchase_detailed_clicks_initial_button_without_rescan():
    """A short-lived detected CTA should be clicked directly before any rescan/reload."""
    page = Mock()
    bigmodel_page = BigModelPage(page)
    button = Mock()

    bigmodel_page._complete_purchase = AsyncMock(
        return_value={
            "success": True,
            "order_id": None,
            "reason": "payment_page_reached",
            "attempts": 1,
            "last_body_excerpt": "支付方式",
        }
    )
    bigmodel_page._find_purchase_buttons = AsyncMock()

    result = await bigmodel_page.purchase_detailed(
        timeout=20000,
        refresh_interval=1,
        initial_buy_button=button,
    )

    assert result["success"] is True
    assert result["reason"] == "payment_page_reached"
    assert result["attempts"] == 1
    bigmodel_page._complete_purchase.assert_awaited_once_with(button)
    bigmodel_page._find_purchase_buttons.assert_not_awaited()
