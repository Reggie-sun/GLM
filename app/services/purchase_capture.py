from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

from playwright.async_api import BrowserContext, Response
from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionLocal
from app.models.account import Account
from bot.browser import BrowserManager
from bot.pages.bigmodel import BigModelPage, StockStatus, create_bigmodel_page

SENSITIVE_HEADER_NAMES = {
    "authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "proxy-authorization",
}
INTERESTING_URL_PARTS = (
    "/api/biz/pay/",
    "/api/pay/",
    "/api/biz/tokenaccounts/",
    "/api/biz/tokenpurchaserecords/",
    "/api/biz/product/",
    "/subscribe-pay",
    "/finance/pay",
    "/finance/order",
)
TEXTUAL_CONTENT_TYPES = (
    "application/json",
    "application/javascript",
    "application/x-javascript",
    "text/",
)


@dataclass
class CaptureEvent:
    timestamp: str
    method: str
    url: str
    status: int
    request_headers: dict[str, str]
    response_headers: dict[str, str]
    request_body: Optional[str]
    response_body: str


@dataclass
class CaptureSummary:
    started_at: str
    finished_at: Optional[str]
    account_id: int
    account_username: str
    target_url: str
    stock_status: Optional[str]
    restock_time: Optional[str]
    output_dir: str
    event_count: int


def sanitize_headers(headers: dict[str, str]) -> dict[str, str]:
    sanitized: dict[str, str] = {}
    for key, value in headers.items():
        sanitized[key] = "<redacted>" if key.lower() in SENSITIVE_HEADER_NAMES else value
    return sanitized


def is_interesting_url(url: str) -> bool:
    parsed = urlparse(url)
    lowered = parsed.path.lower()
    return any(part in lowered for part in INTERESTING_URL_PARTS)


def ensure_output_dir(base_dir: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = base_dir / f"purchase_capture_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _serialize_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_jsonl(path: Path, data: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(data, ensure_ascii=False) + "\n")


def _textual_content_type(content_type: str) -> bool:
    return any(content_type.startswith(prefix) for prefix in TEXTUAL_CONTENT_TYPES)


def load_account_with_cookies(account_id: int) -> tuple[Account, list[dict[str, Any]]]:
    db = SessionLocal()
    try:
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise ValueError(f"Account {account_id} not found")
        if account.status != "active":
            raise ValueError(f"Account {account_id} is not active")
        if not account.cookie:
            raise ValueError(f"Account {account_id} has no cookies configured")
        return account, json.loads(account.cookie)
    except SQLAlchemyError as exc:
        raise RuntimeError(
            "Could not read account data from the local database. "
            "If you use Docker for this project, run the capture script with "
            "`docker compose exec -T web python scripts/capture_purchase_flow.py ...`."
        ) from exc
    finally:
        db.close()


async def check_stock_with_account(
    account_id: int,
    target_url: str,
    headless: bool = True,
) -> tuple[StockStatus, dict[str, Any]]:
    account, cookies = load_account_with_cookies(account_id)
    browser_manager = BrowserManager()
    browser_manager.config.headless = headless
    context: Optional[BrowserContext] = None
    try:
        context = await browser_manager.create_context(user_agent=account.user_agent)
        page = await create_bigmodel_page(context)
        await page.go_to_home()
        await asyncio.sleep(1)
        login_ok = await page.login_with_cookies(cookies)
        if not login_ok:
            return StockStatus.UNKNOWN, {"error": "cookie_login_failed"}

        await page.page.goto(target_url, wait_until="networkidle", timeout=120000)
        status, product_info = await page.check_stock()
        return status, {
            "product": product_info.name,
            "price": product_info.price,
            "restock_time": product_info.restock_time,
        }
    finally:
        if context is not None:
            await context.close()
        await browser_manager.close()


class PurchaseFlowRecorder:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.events_path = output_dir / "events.jsonl"
        self.pending_tasks: set[asyncio.Task] = set()
        self.event_count = 0

    def attach(self, page: BigModelPage) -> None:
        page.page.on("response", self._schedule_response_capture)

    def _schedule_response_capture(self, response: Response) -> None:
        if not is_interesting_url(response.url):
            return
        task = asyncio.create_task(self._capture_response(response))
        self.pending_tasks.add(task)
        task.add_done_callback(self.pending_tasks.discard)

    async def _capture_response(self, response: Response) -> None:
        request = response.request
        request_headers = sanitize_headers(await request.all_headers())
        response_headers = sanitize_headers(await response.all_headers())
        content_type = response_headers.get("content-type", "")
        if _textual_content_type(content_type):
            try:
                response_body = await response.text()
            except Exception as exc:  # pragma: no cover - network edge case
                response_body = f"<failed to read response body: {exc}>"
        else:
            response_body = f"<non-text response: {content_type or 'unknown'}>"

        event = CaptureEvent(
            timestamp=datetime.now().isoformat(),
            method=request.method,
            url=response.url,
            status=response.status,
            request_headers=request_headers,
            response_headers=response_headers,
            request_body=request.post_data,
            response_body=response_body,
        )
        _append_jsonl(self.events_path, asdict(event))
        self.event_count += 1

    async def flush(self) -> None:
        if self.pending_tasks:
            await asyncio.gather(*list(self.pending_tasks), return_exceptions=True)


async def run_capture_session(
    *,
    account_id: int,
    target_url: str,
    output_dir: Path,
    headless: bool,
    click_hero: bool,
    settle_seconds: int,
    hold_seconds: int,
) -> CaptureSummary:
    account, cookies = load_account_with_cookies(account_id)
    browser_manager = BrowserManager()
    browser_manager.config.headless = headless
    context: Optional[BrowserContext] = None
    summary = CaptureSummary(
        started_at=datetime.now().isoformat(),
        finished_at=None,
        account_id=account.id,
        account_username=account.username,
        target_url=target_url,
        stock_status=None,
        restock_time=None,
        output_dir=str(output_dir),
        event_count=0,
    )

    try:
        context = await browser_manager.create_context(user_agent=account.user_agent)
        page = await create_bigmodel_page(context)
        recorder = PurchaseFlowRecorder(output_dir)
        recorder.attach(page)

        await page.go_to_home()
        await asyncio.sleep(1)
        login_ok = await page.login_with_cookies(cookies)
        if not login_ok:
            raise RuntimeError("Cookie login failed before capture")

        await page.page.goto(target_url, wait_until="networkidle", timeout=120000)

        status, product_info = await page.check_stock()
        summary.stock_status = status.value
        summary.restock_time = product_info.restock_time

        screenshot_path = output_dir / "landing.png"
        await page.page.screenshot(path=str(screenshot_path), full_page=False)
        (output_dir / "landing.html").write_text(
            await page.page.content(),
            encoding="utf-8",
        )

        if click_hero:
            hero = page.page.locator(
                "button:has-text('即刻订阅'), [role='button']:has-text('即刻订阅')"
            ).first
            if await hero.count():
                await hero.click(timeout=5000)

        if settle_seconds > 0:
            await asyncio.sleep(settle_seconds)
        if hold_seconds > 0:
            await asyncio.sleep(hold_seconds)

        await recorder.flush()
        summary.event_count = recorder.event_count
        return summary
    finally:
        summary.finished_at = datetime.now().isoformat()
        _serialize_json(output_dir / "summary.json", asdict(summary))
        if context is not None:
            await context.close()
        await browser_manager.close()


async def wait_for_stock(
    *,
    account_id: int,
    target_url: str,
    poll_interval: int,
    timeout_seconds: int,
) -> tuple[StockStatus, dict[str, Any]]:
    started = asyncio.get_running_loop().time()
    while True:
        status, info = await check_stock_with_account(account_id, target_url, headless=True)
        if status == StockStatus.IN_STOCK:
            return status, info

        if timeout_seconds > 0 and asyncio.get_running_loop().time() - started >= timeout_seconds:
            return status, info

        await asyncio.sleep(poll_interval)
