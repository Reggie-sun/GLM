import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio

from app.monitor.scheduler import MonitorScheduler
from app.monitor.tasks import MonitorTask, TaskStatus
from app.models.account import Account
from bot.pages.bigmodel import StockStatus, ProductInfo


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
