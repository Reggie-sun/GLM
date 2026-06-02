#!/usr/bin/env python3
"""Prewarm a logged-in browser before a target GLM Coding restock time."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

from app.services.purchase_capture import load_account_with_cookies  # noqa: E402
from bot.browser import BrowserManager  # noqa: E402
from bot.pages.bigmodel import create_bigmodel_page  # noqa: E402

DEFAULT_TIMEZONE = "Asia/Hong_Kong"


def current_time(timezone_name: str = DEFAULT_TIMEZONE) -> datetime:
    """Return current time in the user-facing purchase timezone."""
    return datetime.now(ZoneInfo(timezone_name))


def parse_target_datetime(
    value: str,
    now: datetime | None = None,
    timezone_name: str = DEFAULT_TIMEZONE,
    late_grace_seconds: int = 0,
) -> datetime:
    """Parse HH:MM and choose the next matching local datetime."""
    now = now or current_time(timezone_name)
    hour_text, minute_text = value.split(":", 1)
    target = now.replace(
        hour=int(hour_text),
        minute=int(minute_text),
        second=0,
        microsecond=0,
    )
    if target <= now and now - target > timedelta(seconds=late_grace_seconds):
        target += timedelta(days=1)
    return target


def should_start_prewarm_now(
    target_at: datetime,
    lead_seconds: int,
    now: datetime | None = None,
    timezone_name: str = DEFAULT_TIMEZONE,
) -> bool:
    """Return whether the configured prewarm lead window has started."""
    if now is None and target_at.tzinfo is not None:
        now = datetime.now(target_at.tzinfo)
    now = now or current_time(timezone_name)
    return now >= target_at - timedelta(seconds=lead_seconds)


async def build_result(
    *,
    page,
    execute: bool,
    purchase_timeout_ms: int,
    refresh_interval: float,
    stock_status: str,
    actionable_count: int,
    target_reached: bool,
) -> dict[str, Any]:
    """Return a dry-run result or execute purchase when explicitly armed."""
    base = {
        "success": False,
        "stock_status": stock_status,
        "actionable_purchase_button_count": actionable_count,
        "target_reached": target_reached,
        "execute": execute,
    }

    if actionable_count <= 0:
        return {**base, "reason": "no_actionable_purchase_button"}

    if not target_reached:
        return {**base, "reason": "prewarm_ready_waiting_for_target"}

    if not execute:
        return {**base, "reason": "dry_run_would_click"}

    purchase_result = await page.purchase_detailed(
        timeout=purchase_timeout_ms,
        refresh_interval=refresh_interval,
    )
    return {**base, **purchase_result}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prewarm GLM Coding purchase page before restock")
    parser.add_argument("--account-id", type=int, default=1)
    parser.add_argument("--target-url", default="https://bigmodel.cn/glm-coding")
    parser.add_argument("--target-time", default="10:00", help="Target time in HH:MM")
    parser.add_argument("--timezone", default=DEFAULT_TIMEZONE, help="Timezone for --target-time")
    parser.add_argument("--prewarm-seconds", type=int, default=600)
    parser.add_argument("--run-seconds", type=int, default=1200)
    parser.add_argument("--refresh-interval", type=float, default=2.0)
    parser.add_argument("--purchase-timeout-ms", type=int, default=30000)
    parser.add_argument("--wait-login-seconds", type=int, default=0)
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--keep-open-seconds", type=int, default=0)
    parser.add_argument(
        "--screenshot-path",
        default="data/screenshots/payment_page.png",
        help="Where to save the final page screenshot after an execute attempt",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually click the purchase flow after target time when an actionable button exists",
    )
    return parser.parse_args()


async def wait_for_login(page, timeout_seconds: int, poll_seconds: float = 2.0) -> bool:
    """Wait for a user-assisted login, such as scanning the site's QR code."""
    deadline = asyncio.get_running_loop().time() + max(timeout_seconds, 0)
    while asyncio.get_running_loop().time() <= deadline:
        if await page._is_logged_in():
            return True
        try:
            body_text = await page.page.inner_text("body")
            if "手机号登录" not in body_text and "微信扫码登录" not in body_text:
                return True
        except Exception:
            pass
        await asyncio.sleep(poll_seconds)
    return False


async def run(args: argparse.Namespace) -> dict[str, Any]:
    target_at = parse_target_datetime(
        args.target_time,
        timezone_name=args.timezone,
        late_grace_seconds=args.run_seconds,
    )
    prewarm_at = target_at - timedelta(seconds=args.prewarm_seconds)

    if not args.execute:
        print("DRY RUN: no purchase button will be clicked. Add --execute to arm real purchase.")
    print(f"Target timezone: {args.timezone}")
    print(f"Target time: {target_at.isoformat()}")
    print(f"Prewarm time: {prewarm_at.isoformat()}")

    while not should_start_prewarm_now(target_at, args.prewarm_seconds, timezone_name=args.timezone):
        sleep_for = min((prewarm_at - current_time(args.timezone)).total_seconds(), 60)
        await asyncio.sleep(max(sleep_for, 1))

    account, cookies = load_account_with_cookies(args.account_id)
    manager = BrowserManager()
    manager.config.headless = not args.headed
    context = None
    final_result: dict[str, Any] = {"success": False, "reason": "not_started"}

    try:
        await manager.start()
        context = await manager.create_context(user_agent=account.user_agent)
        page = await create_bigmodel_page(context)
        await page.go_to_home()
        login_ok = await page.login_with_cookies(cookies)
        if not login_ok:
            return {"success": False, "reason": "cookie_login_failed"}

        await page.go_to_glm_coding()
        deadline = target_at + timedelta(seconds=args.run_seconds)

        while current_time(args.timezone) <= deadline:
            status, product = await page.check_stock()
            package_buttons = await page._find_elements(page.PACKAGE_BUTTON_SELECTORS)
            actionable = await page._filter_purchase_buttons(package_buttons)
            final_result = await build_result(
                page=page,
                execute=args.execute,
                purchase_timeout_ms=args.purchase_timeout_ms,
                refresh_interval=args.refresh_interval,
                stock_status=status.value,
                actionable_count=len(actionable),
                target_reached=current_time(args.timezone) >= target_at,
            )
            final_result["restock_time"] = product.restock_time
            final_result["checked_at"] = current_time(args.timezone).isoformat()
            final_result["current_url"] = page.page.url
            print(json.dumps(final_result, ensure_ascii=False))

            if args.execute and final_result.get("target_reached") and final_result.get("attempts", 0) > 0:
                screenshot_path = Path(args.screenshot_path)
                screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                await page.page.screenshot(path=str(screenshot_path), full_page=False)
                final_result["screenshot_path"] = str(screenshot_path)
                final_result["current_url"] = page.page.url
                print(json.dumps({"final_page_captured": final_result}, ensure_ascii=False), flush=True)

                if final_result.get("reason") == "logged_out" and args.wait_login_seconds > 0:
                    print(
                        json.dumps(
                            {
                                "login_required": True,
                                "screenshot_path": str(screenshot_path),
                                "wait_login_seconds": args.wait_login_seconds,
                            },
                            ensure_ascii=False,
                        ),
                        flush=True,
                    )
                    if await wait_for_login(page, args.wait_login_seconds):
                        print(json.dumps({"login_resumed": True}, ensure_ascii=False), flush=True)
                        await page.go_to_glm_coding()
                        continue
                    print(json.dumps({"login_resumed": False}, ensure_ascii=False), flush=True)

            if final_result.get("success") or final_result.get("reason") == "dry_run_would_click":
                if args.execute:
                    if args.keep_open_seconds > 0:
                        await asyncio.sleep(args.keep_open_seconds)
                return final_result

            await page.page.reload(wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(max(args.refresh_interval, 0))

        return {**final_result, "reason": final_result.get("reason", "prewarm_window_ended")}
    finally:
        if context is not None:
            await context.close()
        await manager.close()


async def main() -> int:
    result = await run(parse_args())
    print("Final result:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("success") or result.get("reason") == "dry_run_would_click" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
