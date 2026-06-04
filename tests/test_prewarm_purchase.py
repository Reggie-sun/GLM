from datetime import datetime
from unittest.mock import AsyncMock, Mock
from zoneinfo import ZoneInfo

import pytest

from scripts.prewarm_purchase import (
    build_result,
    parse_target_datetime,
    should_start_prewarm_now,
)


def test_parse_target_datetime_uses_today_when_time_is_future():
    now = datetime(2026, 6, 2, 9, 30)

    target = parse_target_datetime("10:00", now=now)

    assert target == datetime(2026, 6, 2, 10, 0)


def test_parse_target_datetime_rolls_to_tomorrow_when_time_has_passed():
    now = datetime(2026, 6, 2, 10, 30)

    target = parse_target_datetime("10:00", now=now)

    assert target == datetime(2026, 6, 3, 10, 0)


def test_parse_target_datetime_uses_today_when_inside_late_grace_window():
    now = datetime(2026, 6, 2, 10, 5)

    target = parse_target_datetime("10:00", now=now, late_grace_seconds=1200)

    assert target == datetime(2026, 6, 2, 10, 0)


def test_parse_target_datetime_preserves_target_timezone():
    now = datetime(2026, 6, 2, 9, 30, tzinfo=ZoneInfo("Asia/Hong_Kong"))

    target = parse_target_datetime("10:00", now=now)

    assert target == datetime(2026, 6, 2, 10, 0, tzinfo=ZoneInfo("Asia/Hong_Kong"))


def test_should_start_prewarm_now_inside_lead_window():
    now = datetime(2026, 6, 2, 9, 50)
    target = datetime(2026, 6, 2, 10, 0)

    assert should_start_prewarm_now(target, lead_seconds=600, now=now) is True


@pytest.mark.asyncio
async def test_build_result_dry_run_does_not_purchase_when_actionable():
    page = Mock()
    page.purchase_detailed = AsyncMock()

    result = await build_result(
        page=page,
        execute=False,
        purchase_timeout_ms=30000,
        refresh_interval=2.0,
        stock_status="in_stock",
        actionable_count=3,
        target_reached=True,
    )

    assert result["success"] is False
    assert result["reason"] == "dry_run_would_click"
    assert result["actionable_purchase_button_count"] == 3
    page.purchase_detailed.assert_not_awaited()


@pytest.mark.asyncio
async def test_build_result_execute_purchases_when_actionable_and_target_reached():
    page = Mock()
    button = Mock()
    page.purchase_detailed = AsyncMock(
        return_value={"success": True, "reason": "order_created", "attempts": 1}
    )

    result = await build_result(
        page=page,
        execute=True,
        purchase_timeout_ms=30000,
        refresh_interval=2.0,
        stock_status="in_stock",
        actionable_count=1,
        target_reached=True,
        actionable_buttons=[button],
    )

    assert result["success"] is True
    assert result["reason"] == "order_created"
    page.purchase_detailed.assert_awaited_once_with(
        timeout=30000,
        refresh_interval=2.0,
        initial_buy_button=button,
    )
