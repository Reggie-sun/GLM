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
REPLAY_HEADER_PLACEHOLDERS = {
    "authorization": "<paste Authorization header from browser>",
    "bigmodel-organization": "<paste bigmodel-organization header from browser>",
    "bigmodel-project": "<paste bigmodel-project header from browser>",
}


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


@dataclass
class ButtonSnapshot:
    text: str
    css_class: Optional[str]
    enabled: bool
    visible: bool


@dataclass
class WatchSample:
    checked_at: str
    stock_status: str
    price: Optional[str]
    restock_time: Optional[str]
    actionable_package_count: int
    actionable_hero_count: int
    package_buttons: list[ButtonSnapshot]
    hero_buttons: list[ButtonSnapshot]
    event_count: int


@dataclass
class WatchSummary:
    started_at: str
    finished_at: Optional[str]
    account_id: int
    account_username: str
    target_url: str
    output_dir: str
    poll_count: int
    actionable_detected: bool
    package_click_attempted: bool
    package_click_triggered: bool
    first_actionable_at: Optional[str]
    event_count: int
    final_stock_status: Optional[str]


@dataclass
class EndpointSummary:
    method: str
    url: str
    status: int
    request_header_names: list[str]
    request_body: Optional[Any]
    response_code: Optional[int]
    response_success: Optional[bool]
    response_message: Optional[str]
    response_data_keys: list[str]


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


def _button_snapshot_to_dict(snapshot: ButtonSnapshot) -> dict[str, Any]:
    return asdict(snapshot)


def _textual_content_type(content_type: str) -> bool:
    return any(content_type.startswith(prefix) for prefix in TEXTUAL_CONTENT_TYPES)


def try_parse_json(text: Optional[str]) -> Optional[Any]:
    if not text:
        return None
    try:
        return json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return None


def extract_product_snapshot(response_body: str) -> list[dict[str, Any]]:
    payload = try_parse_json(response_body)
    if not isinstance(payload, dict):
        return []

    data = payload.get("data")
    if not isinstance(data, dict):
        return []

    product_list = data.get("productList")
    if not isinstance(product_list, list):
        return []

    snapshot: list[dict[str, Any]] = []
    for item in product_list:
        if not isinstance(item, dict):
            continue
        snapshot.append(
            {
                "productId": item.get("productId"),
                "productName": item.get("productName"),
                "payAmount": item.get("payAmount"),
                "renewAmount": item.get("renewAmount"),
                "soldOut": item.get("soldOut"),
                "forbidden": item.get("forbidden"),
                "canPurchase": item.get("canPurchase"),
                "canRepurchase": item.get("canRepurchase"),
            }
        )
    return snapshot


def build_endpoint_summary(event: CaptureEvent) -> EndpointSummary:
    request_body = try_parse_json(event.request_body) if event.request_body else event.request_body
    response_json = try_parse_json(event.response_body)
    response_data = response_json.get("data") if isinstance(response_json, dict) else None
    response_data_keys = sorted(response_data.keys()) if isinstance(response_data, dict) else []
    return EndpointSummary(
        method=event.method,
        url=event.url,
        status=event.status,
        request_header_names=sorted(event.request_headers.keys()),
        request_body=request_body,
        response_code=response_json.get("code") if isinstance(response_json, dict) else None,
        response_success=response_json.get("success") if isinstance(response_json, dict) else None,
        response_message=response_json.get("msg") if isinstance(response_json, dict) else None,
        response_data_keys=response_data_keys,
    )


def build_replay_template(event: CaptureEvent) -> dict[str, Any]:
    headers_template: dict[str, str] = {}
    for name, value in event.request_headers.items():
        lowered = name.lower()
        if lowered in REPLAY_HEADER_PLACEHOLDERS:
            headers_template[name] = REPLAY_HEADER_PLACEHOLDERS[lowered]
        elif lowered.startswith(":"):
            continue
        elif lowered in {"accept-encoding", "content-length", "cookie"}:
            continue
        else:
            headers_template[name] = value

    return {
        "method": event.method,
        "url": event.url,
        "headers": headers_template,
        "body": try_parse_json(event.request_body) if event.request_body else None,
        "notes": [
            "Authorization, bigmodel-organization, and bigmodel-project must come from a live browser session.",
            "This template is generated from a captured request with sensitive values removed.",
        ],
    }


def write_capture_artifacts(output_dir: Path, events: list[CaptureEvent]) -> None:
    endpoint_summaries = [asdict(build_endpoint_summary(event)) for event in events]
    _serialize_json(output_dir / "endpoint_summary.json", {"events": endpoint_summaries})

    replay_templates: dict[str, Any] = {}
    batch_preview_products: list[dict[str, Any]] = []
    for event in events:
        if event.url.endswith("/api/biz/pay/batch-preview"):
            replay_templates["batch_preview"] = build_replay_template(event)
            batch_preview_products = extract_product_snapshot(event.response_body)
        elif event.url.endswith("/api/biz/pay/preview"):
            replay_templates["pay_preview"] = build_replay_template(event)
        elif event.url.endswith("/api/biz/pay/create-sign"):
            replay_templates["create_sign"] = build_replay_template(event)
        elif "/api/biz/pay/check" in event.url:
            replay_templates["pay_check"] = build_replay_template(event)

    _serialize_json(output_dir / "replay_templates.json", replay_templates)
    _serialize_json(output_dir / "batch_preview_products.json", {"products": batch_preview_products})


def summarize_button_states(buttons: list[ButtonSnapshot]) -> dict[str, Any]:
    actionable_count = sum(1 for button in buttons if button.enabled and button.visible)
    return {
        "total_count": len(buttons),
        "actionable_count": actionable_count,
        "texts": [button.text for button in buttons],
    }


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
        self.captured_events: list[CaptureEvent] = []

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
        self.captured_events.append(event)

    async def flush(self) -> None:
        if self.pending_tasks:
            await asyncio.gather(*list(self.pending_tasks), return_exceptions=True)


async def snapshot_button_states(page: BigModelPage) -> tuple[list[ButtonSnapshot], list[ButtonSnapshot]]:
    async def _collect(selectors: tuple[str, ...]) -> list[ButtonSnapshot]:
        snapshots: list[ButtonSnapshot] = []
        for element in await page._find_elements(selectors):
            try:
                snapshots.append(
                    ButtonSnapshot(
                        text=(await element.inner_text()).strip(),
                        css_class=await element.get_attribute("class"),
                        enabled=await page._element_is_enabled(element),
                        visible=await page._element_is_visible(element),
                    )
                )
            except Exception:
                continue
        return snapshots

    package_buttons = await _collect(page.PACKAGE_BUTTON_SELECTORS)
    hero_buttons = await _collect(page.HERO_BUTTON_SELECTORS)
    return package_buttons, hero_buttons


async def capture_watch_sample(
    page: BigModelPage,
    recorder: PurchaseFlowRecorder,
    *,
    checked_at: Optional[str] = None,
) -> WatchSample:
    status, product_info = await page.check_stock()
    package_buttons, hero_buttons = await snapshot_button_states(page)
    package_summary = summarize_button_states(package_buttons)
    hero_summary = summarize_button_states(hero_buttons)
    return WatchSample(
        checked_at=checked_at or datetime.now().isoformat(),
        stock_status=status.value,
        price=product_info.price,
        restock_time=product_info.restock_time,
        actionable_package_count=package_summary["actionable_count"],
        actionable_hero_count=hero_summary["actionable_count"],
        package_buttons=package_buttons,
        hero_buttons=hero_buttons,
        event_count=recorder.event_count,
    )


async def click_first_actionable_package_button(page: BigModelPage) -> bool:
    package_buttons = await page._find_elements(page.PACKAGE_BUTTON_SELECTORS)
    actionable_buttons = await page._filter_purchase_buttons(package_buttons)
    if not actionable_buttons:
        return False
    await actionable_buttons[0].click(timeout=5000)
    return True


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
        write_capture_artifacts(output_dir, recorder.captured_events)
        summary.event_count = recorder.event_count
        return summary
    finally:
        summary.finished_at = datetime.now().isoformat()
        _serialize_json(output_dir / "summary.json", asdict(summary))
        if context is not None:
            await context.close()
        await browser_manager.close()


async def watch_capture_session(
    *,
    account_id: int,
    target_url: str,
    output_dir: Path,
    headless: bool,
    click_hero: bool,
    refresh_interval: int,
    watch_seconds: int,
    stop_on_actionable: bool,
    click_package_on_actionable: bool,
    settle_seconds: int,
) -> WatchSummary:
    account, cookies = load_account_with_cookies(account_id)
    browser_manager = BrowserManager()
    browser_manager.config.headless = headless
    context: Optional[BrowserContext] = None
    samples_path = output_dir / "status_samples.jsonl"
    summary = WatchSummary(
        started_at=datetime.now().isoformat(),
        finished_at=None,
        account_id=account.id,
        account_username=account.username,
        target_url=target_url,
        output_dir=str(output_dir),
        poll_count=0,
        actionable_detected=False,
        package_click_attempted=click_package_on_actionable,
        package_click_triggered=False,
        first_actionable_at=None,
        event_count=0,
        final_stock_status=None,
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
            raise RuntimeError("Cookie login failed before watch capture")

        await page.page.goto(target_url, wait_until="networkidle", timeout=120000)

        if click_hero:
            hero = page.page.locator(
                "button:has-text('即刻订阅'), [role='button']:has-text('即刻订阅')"
            ).first
            if await hero.count():
                await hero.click(timeout=5000)
                if settle_seconds > 0:
                    await asyncio.sleep(settle_seconds)

        deadline = None if watch_seconds <= 0 else asyncio.get_running_loop().time() + watch_seconds

        while True:
            sample = await capture_watch_sample(page, recorder)
            _append_jsonl(
                samples_path,
                {
                    "checked_at": sample.checked_at,
                    "stock_status": sample.stock_status,
                    "price": sample.price,
                    "restock_time": sample.restock_time,
                    "actionable_package_count": sample.actionable_package_count,
                    "actionable_hero_count": sample.actionable_hero_count,
                    "package_buttons": [_button_snapshot_to_dict(button) for button in sample.package_buttons],
                    "hero_buttons": [_button_snapshot_to_dict(button) for button in sample.hero_buttons],
                    "event_count": sample.event_count,
                },
            )
            summary.poll_count += 1
            summary.final_stock_status = sample.stock_status

            if sample.actionable_package_count > 0:
                summary.actionable_detected = True
                if summary.first_actionable_at is None:
                    summary.first_actionable_at = sample.checked_at
                if click_package_on_actionable and not summary.package_click_triggered:
                    summary.package_click_triggered = await click_first_actionable_package_button(page)
                    if settle_seconds > 0:
                        await asyncio.sleep(settle_seconds)
                if stop_on_actionable:
                    break

            if deadline is not None and asyncio.get_running_loop().time() >= deadline:
                break

            await page.page.reload(wait_until="networkidle", timeout=120000)
            await asyncio.sleep(refresh_interval)

        await recorder.flush()
        write_capture_artifacts(output_dir, recorder.captured_events)
        summary.event_count = recorder.event_count
        await page.page.screenshot(path=str(output_dir / "watch_final.png"), full_page=False)
        return summary
    finally:
        summary.finished_at = datetime.now().isoformat()
        _serialize_json(output_dir / "watch_summary.json", asdict(summary))
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
