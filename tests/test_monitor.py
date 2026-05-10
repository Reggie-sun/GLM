import pytest
from datetime import datetime

from app.monitor.tasks import MonitorTask, TaskStatus, MonitorTaskRegistry
from app.monitor.scheduler import MonitorScheduler
from app.notifications import Notification, NotificationLevel, ConsoleNotificationChannel
from bot.pages.bigmodel import StockStatus, ProductInfo, BigModelPage


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
