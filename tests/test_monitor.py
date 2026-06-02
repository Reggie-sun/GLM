import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

from app.monitor.tasks import MonitorTask, TaskStatus, MonitorTaskRegistry
from app.monitor.scheduler import MonitorScheduler
from app.notifications import Notification, NotificationLevel, ConsoleNotificationChannel
from app.api.v1.monitor import CreateMonitorTaskRequest, create_monitor_task, trigger_purchase
from bot.pages.bigmodel import StockStatus, ProductInfo


def test_monitor_task_creation():
    """Test monitor task creation"""
    task = MonitorTask(
        task_id="test-123",
        name="Test Monitor",
        target_url="https://example.com",
        check_interval=30,
    )

    assert task.task_id == "test-123"
    assert task.name == "Test Monitor"
    assert task.target_url == "https://example.com"
    assert task.check_interval == 30
    assert task.status == TaskStatus.PENDING
    assert task.auto_purchase is False


def test_monitor_task_auto_id():
    """Test monitor task auto-generates ID"""
    task = MonitorTask(
        task_id="",
        name="Auto ID Test",
        target_url="https://example.com",
        check_interval=30,
    )

    assert task.task_id is not None
    assert len(task.task_id) > 0


def test_task_registry():
    """Test monitor task registry"""
    registry = MonitorTaskRegistry()

    task = MonitorTask(
        task_id="reg-test",
        name="Registry Test",
        target_url="https://example.com",
        check_interval=30,
    )

    # Add task
    registry.add(task)
    assert registry.get("reg-test") is not None

    # List tasks
    all_tasks = registry.list_all()
    assert len(all_tasks) == 1

    # Remove task
    success = registry.remove("reg-test")
    assert success is True
    assert registry.get("reg-test") is None


def test_task_status_update():
    """Test task status update"""
    registry = MonitorTaskRegistry()
    task = MonitorTask(
        task_id="status-test",
        name="Status Test",
        target_url="https://example.com",
        check_interval=30,
    )
    registry.add(task)

    registry.update_status("status-test", TaskStatus.RUNNING)
    updated = registry.get("status-test")
    assert updated.status == TaskStatus.RUNNING
    assert updated.last_run_at is not None


def test_stock_status_enum():
    """Test stock status enum"""
    assert StockStatus.IN_STOCK.value == "in_stock"
    assert StockStatus.OUT_OF_STOCK.value == "out_of_stock"
    assert StockStatus.UNKNOWN.value == "unknown"


def test_product_info():
    """Test product info dataclass"""
    product = ProductInfo(
        name="Test Product",
        status=StockStatus.IN_STOCK,
        price="99.99",
    )

    assert product.name == "Test Product"
    assert product.status == StockStatus.IN_STOCK
    assert product.price == "99.99"
    assert product.last_updated is None


def test_notification_creation():
    """Test notification creation"""
    notification = Notification(
        title="Test Alert",
        message="This is a test notification",
        level=NotificationLevel.INFO,
    )

    assert notification.title == "Test Alert"
    assert notification.message == "This is a test notification"
    assert notification.level == NotificationLevel.INFO
    assert notification.created_at is not None


def test_console_notification_channel():
    """Test console notification channel"""
    channel = ConsoleNotificationChannel()

    assert channel.name() == "console"
    assert channel.is_available() is True


def test_notification_level_enum():
    """Test notification level enum"""
    assert NotificationLevel.INFO.value == "info"
    assert NotificationLevel.WARNING.value == "warning"
    assert NotificationLevel.ERROR.value == "error"
    assert NotificationLevel.SUCCESS.value == "success"


@pytest.mark.asyncio
async def test_console_notification_send():
    """Test sending console notification"""
    channel = ConsoleNotificationChannel()

    notification = Notification(
        title="Test",
        message="Test message",
        level=NotificationLevel.INFO,
    )

    result = await channel.send(notification)
    assert result is True


def test_monitor_scheduler_import():
    """Test monitor scheduler can be imported"""
    assert MonitorScheduler is not None


def test_get_monitor_scheduler():
    """Test get monitor scheduler function"""
    from app.monitor.scheduler import get_monitor_scheduler

    scheduler = get_monitor_scheduler()
    assert scheduler is not None


def test_get_notification_service():
    """Test get notification service function"""
    from app.notifications import get_notification_service

    service = get_notification_service()
    assert service is not None
    assert "console" in service.list_channels()


def test_monitor_task_with_data():
    """Test monitor task with custom data"""
    task = MonitorTask(
        task_id="data-test",
        name="Data Test",
        target_url="https://example.com",
        check_interval=60,
        auto_purchase=True,
    )

    task.last_result = {"test": "data"}
    task.error_message = None

    assert task.auto_purchase is True
    assert task.last_result == {"test": "data"}
    assert task.error_message is None


def test_monitor_task_with_account():
    """Test monitor task with account configuration"""
    task = MonitorTask(
        task_id="",
        name="Account Test",
        target_url="https://example.com",
        check_interval=30,
        auto_purchase=True,
        account_id=1,
    )

    assert task.account_id == 1
    assert task.auto_purchase is True


def test_monitor_task_with_webhook():
    """Test monitor task can store a webhook URL."""
    task = MonitorTask(
        task_id="webhook-test",
        name="Webhook Test",
        target_url="https://example.com",
        check_interval=30,
        webhook_url="https://hooks.example.com/glm",
    )

    assert task.webhook_url == "https://hooks.example.com/glm"


@pytest.mark.asyncio
async def test_create_monitor_task_preserves_webhook_url():
    """Create monitor task API should persist webhook URL on the task and response."""
    created_task = MonitorTask(
        task_id="task-with-webhook",
        name="Webhook API Test",
        target_url="https://example.com",
        check_interval=30,
        webhook_url="https://hooks.example.com/glm",
    )

    mock_scheduler = Mock()
    mock_scheduler.start_monitor = AsyncMock(return_value=created_task.task_id)
    mock_scheduler.get_task.return_value = created_task

    request = CreateMonitorTaskRequest(
        name="Webhook API Test",
        target_url="https://example.com",
        check_interval=30,
        webhook_url="https://hooks.example.com/glm",
    )

    with patch("app.api.v1.monitor.get_monitor_scheduler", return_value=mock_scheduler):
        response = await create_monitor_task(request)

    assert response.webhook_url == "https://hooks.example.com/glm"
    started_task = mock_scheduler.start_monitor.await_args.args[0]
    assert started_task.webhook_url == "https://hooks.example.com/glm"


@pytest.mark.asyncio
async def test_stock_change_notification_uses_console_and_webhook():
    """Stock change notifications should fan out to console and task webhook."""
    scheduler = MonitorScheduler()
    task = MonitorTask(
        task_id="notify-test",
        name="Notify Test",
        target_url="https://example.com",
        check_interval=30,
        webhook_url="https://hooks.example.com/glm",
    )

    result = {
        "status": StockStatus.IN_STOCK,
        "product": "GLM Coding",
        "checked_at": datetime.now().isoformat(),
    }

    with patch("app.monitor.scheduler.get_notification_service") as mock_get_notification_service:
        mock_service = Mock()
        mock_service.send = AsyncMock(return_value={"console": True})
        mock_get_notification_service.return_value = mock_service

        with patch("app.monitor.scheduler.WebhookNotificationChannel") as mock_webhook_channel:
            webhook_channel = Mock()
            webhook_channel.send = AsyncMock(return_value=True)
            mock_webhook_channel.return_value = webhook_channel

            await scheduler._notify_stock_change(
                task,
                StockStatus.OUT_OF_STOCK,
                StockStatus.IN_STOCK,
                result,
            )

    notification = mock_service.send.await_args.args[0]
    assert notification.title == "Stock Status Changed"
    assert notification.level == NotificationLevel.SUCCESS
    assert notification.data["previous_status"] == StockStatus.OUT_OF_STOCK.value
    assert notification.data["current_status"] == StockStatus.IN_STOCK.value
    mock_webhook_channel.assert_called_once_with("https://hooks.example.com/glm")
    webhook_channel.send.assert_awaited_once_with(notification)


def test_account_response_reports_cookie_presence_without_leaking_value():
    """Account API responses should show cookie readiness without exposing secrets."""
    from app.api.v1.accounts import _account_to_response
    from app.models import Account

    db_account = Account(id=1, username="whdgfr07", status="active", is_public=False)
    db_account.cookie = '[{"name":"bigmodel_token_production","value":"secret"}]'

    response = _account_to_response(db_account)

    assert response["has_cookie"] is True
    assert "cookie" not in response


@pytest.mark.asyncio
async def test_trigger_purchase_returns_full_diagnostic_result():
    """Manual trigger endpoint should not discard purchase diagnostics."""
    task = MonitorTask(
        task_id="trigger-diagnostics",
        name="Trigger Diagnostics",
        target_url="https://example.com",
        check_interval=30,
        auto_purchase=True,
        account_id=1,
    )

    purchase_result = {
        "success": False,
        "message": "Purchase failed: high_demand_retry_exhausted",
        "reason": "high_demand_retry_exhausted",
        "attempts": 4,
        "last_body_excerpt": "抢购人数过多，请刷新再试",
    }

    mock_scheduler = Mock()
    mock_scheduler.get_task.return_value = task
    mock_scheduler._attempt_purchase = AsyncMock(return_value=purchase_result)

    with patch("app.api.v1.monitor.get_monitor_scheduler", return_value=mock_scheduler):
        response = await trigger_purchase(task.task_id)

    assert response == purchase_result
