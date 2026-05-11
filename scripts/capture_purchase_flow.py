#!/usr/bin/env python3
"""
Capture GLM Coding purchase-related requests and save them to disk.

By default this script:
1. Reuses an account's stored cookies from the local database.
2. Opens the GLM Coding page.
3. Clicks the hero subscribe CTA to trigger purchase-preview requests.
4. Saves interesting request/response pairs to `data/captures/...`.

Sensitive headers such as Authorization and Cookie are redacted before writing.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

from app.services.purchase_capture import (  # noqa: E402
    ensure_output_dir,
    run_capture_session,
    wait_for_stock,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture GLM Coding purchase flow requests")
    parser.add_argument("--account-id", type=int, default=1, help="Account ID from local database")
    parser.add_argument(
        "--target-url",
        default="https://bigmodel.cn/glm-coding",
        help="Target purchase page",
    )
    parser.add_argument(
        "--output-dir",
        default=str(root / "data" / "captures"),
        help="Base directory for captured files",
    )
    parser.add_argument(
        "--wait-for-stock",
        action="store_true",
        help="Poll until the account sees the page as in stock before capturing",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=30,
        help="Polling interval in seconds when --wait-for-stock is enabled",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=0,
        help="Stop waiting after this many seconds; 0 means wait indefinitely",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Launch a visible browser instead of headless mode",
    )
    parser.add_argument(
        "--skip-hero-click",
        action="store_true",
        help="Do not click the hero subscribe CTA automatically",
    )
    parser.add_argument(
        "--settle-seconds",
        type=int,
        default=5,
        help="Seconds to wait after page actions so requests can finish",
    )
    parser.add_argument(
        "--hold-seconds",
        type=int,
        default=0,
        help="Keep the browser open for additional manual actions before closing",
    )
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    output_dir = ensure_output_dir(Path(args.output_dir))

    print("=" * 70)
    print("GLM Coding Purchase Flow Capture")
    print("=" * 70)
    print(f"Output directory: {output_dir}")

    if args.wait_for_stock:
        print("Waiting for in-stock status...")
        status, info = await wait_for_stock(
            account_id=args.account_id,
            target_url=args.target_url,
            poll_interval=args.poll_interval,
            timeout_seconds=args.timeout_seconds,
        )
        print(f"Latest stock status: {status.value}")
        if info.get("restock_time"):
            print(f"Restock hint: {info['restock_time']}")
        if status.value != "in_stock":
            print("Capture did not start because stock never became available within the wait window.")
            return 1

    summary = await run_capture_session(
        account_id=args.account_id,
        target_url=args.target_url,
        output_dir=output_dir,
        headless=not args.headed,
        click_hero=not args.skip_hero_click,
        settle_seconds=args.settle_seconds,
        hold_seconds=args.hold_seconds,
    )

    print("\nCapture complete")
    print(f"Captured events: {summary.event_count}")
    print(f"Final stock status: {summary.stock_status}")
    if summary.restock_time:
        print(f"Restock hint: {summary.restock_time}")
    print(f"Summary: {output_dir / 'summary.json'}")
    print(f"Events: {output_dir / 'events.jsonl'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
