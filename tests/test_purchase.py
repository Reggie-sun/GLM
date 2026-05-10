import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.monitor.scheduler import MonitorScheduler
from app.monitor.tasks import MonitorTask, TaskStatus
from app.models.account import Account


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
