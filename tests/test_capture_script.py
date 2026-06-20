from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from app.services.purchase_capture import (
    ButtonSnapshot,
    CaptureEvent,
    build_endpoint_summary,
    build_purchase_candidate_summaries,
    build_replay_template,
    ensure_output_dir,
    extract_product_snapshot,
    goto_dynamic_page,
    is_interesting_url,
    sanitize_headers,
    summarize_button_states,
)


def test_sanitize_headers_redacts_sensitive_values():
    headers = {
        "Authorization": "Bearer token",
        "Cookie": "a=b",
        "Content-Type": "application/json",
    }

    sanitized = sanitize_headers(headers)

    assert sanitized["Authorization"] == "<redacted>"
    assert sanitized["Cookie"] == "<redacted>"
    assert sanitized["Content-Type"] == "application/json"


def test_is_interesting_url_matches_purchase_flow_endpoints():
    assert is_interesting_url("https://bigmodel.cn/api/biz/pay/batch-preview") is True
    assert is_interesting_url("https://bigmodel.cn/api/biz/product/createPreOrder") is True
    assert is_interesting_url("https://bigmodel.cn/css/app.css") is False


def test_ensure_output_dir_creates_timestamped_directory(tmp_path: Path):
    output_dir = ensure_output_dir(tmp_path)

    assert output_dir.exists()
    assert output_dir.parent == tmp_path
    assert output_dir.name.startswith("purchase_capture_")


def test_extract_product_snapshot_reads_batch_preview_products():
    response_body = """
    {
      "code": 200,
      "msg": "ok",
      "success": true,
      "data": {
        "productList": [
          {
            "productId": "product-1",
            "productName": "Lite",
            "payAmount": 132.3,
            "renewAmount": 132.3,
            "soldOut": true,
            "forbidden": false
          }
        ]
      }
    }
    """

    snapshot = extract_product_snapshot(response_body)

    assert snapshot == [
        {
            "productId": "product-1",
            "productName": "Lite",
            "payAmount": 132.3,
            "renewAmount": 132.3,
            "soldOut": True,
            "forbidden": False,
            "canPurchase": None,
            "canRepurchase": None,
        }
    ]


def test_build_replay_template_uses_placeholders_for_sensitive_headers():
    event = CaptureEvent(
        timestamp="2026-05-11T00:00:00",
        phase="hero_click",
        method="POST",
        url="https://bigmodel.cn/api/biz/pay/batch-preview",
        status=200,
        page_url="https://bigmodel.cn/glm-coding",
        resource_type="xhr",
        request_headers={
            "authorization": "<redacted>",
            "bigmodel-organization": "org-1",
            "bigmodel-project": "proj-1",
            "content-type": "application/json;charset=UTF-8",
            ":authority": "bigmodel.cn",
        },
        response_headers={"content-type": "application/json"},
        request_body='{"invitationCode":""}',
        response_body='{"code":200,"success":true,"data":{"productList":[]}}',
    )

    template = build_replay_template(event)

    assert template["headers"]["authorization"] == "<paste Authorization header from browser>"
    assert template["headers"]["bigmodel-organization"] == (
        "<paste bigmodel-organization header from browser>"
    )
    assert template["headers"]["bigmodel-project"] == "<paste bigmodel-project header from browser>"
    assert template["phase"] == "hero_click"
    assert template["page_url"] == "https://bigmodel.cn/glm-coding"
    assert ":authority" not in template["headers"]
    assert template["body"] == {"invitationCode": ""}


def test_build_endpoint_summary_extracts_response_shape():
    event = CaptureEvent(
        timestamp="2026-05-11T00:00:00",
        phase="purchase_attempt",
        method="POST",
        url="https://bigmodel.cn/api/biz/pay/batch-preview",
        status=200,
        page_url="https://bigmodel.cn/glm-coding",
        resource_type="xhr",
        request_headers={"content-type": "application/json"},
        response_headers={"content-type": "application/json"},
        request_body='{"invitationCode":""}',
        response_body='{"code":200,"msg":"ok","success":true,"data":{"bizId":"biz-1","productList":[]}}',
    )

    summary = build_endpoint_summary(event)

    assert summary.phase == "purchase_attempt"
    assert summary.page_url == "https://bigmodel.cn/glm-coding"
    assert summary.resource_type == "xhr"
    assert summary.response_code == 200
    assert summary.response_success is True
    assert summary.response_message == "ok"
    assert summary.response_data_keys == ["bizId", "productList"]


def test_build_purchase_candidate_summaries_groups_by_endpoint_and_phase():
    preview_event = CaptureEvent(
        timestamp="2026-05-11T00:00:00",
        phase="hero_click",
        method="POST",
        url="https://bigmodel.cn/api/biz/pay/batch-preview",
        status=200,
        page_url="https://bigmodel.cn/glm-coding",
        resource_type="xhr",
        request_headers={"content-type": "application/json"},
        response_headers={"content-type": "application/json"},
        request_body='{"invitationCode":""}',
        response_body='{"code":200,"msg":"ok","success":true,"data":{"productList":[]}}',
    )
    order_event = CaptureEvent(
        timestamp="2026-05-11T00:00:01",
        phase="purchase_attempt",
        method="POST",
        url="https://bigmodel.cn/pay/bank/createBankOrder",
        status=200,
        page_url="https://bigmodel.cn/subscribe-pay",
        resource_type="xhr",
        request_headers={"content-type": "application/json"},
        response_headers={"content-type": "application/json"},
        request_body='{"productId":"product-1"}',
        response_body='{"code":200,"msg":"ok","success":true,"data":{"orderId":"order-1","payUrl":"https://pay.example.com"}}',
    )

    candidates = build_purchase_candidate_summaries([preview_event, order_event])

    assert [item["category"] for item in candidates] == ["order_creation", "preview"]
    assert candidates[0]["phases"] == ["purchase_attempt"]
    assert candidates[0]["page_urls"] == ["https://bigmodel.cn/subscribe-pay"]
    assert candidates[0]["response_data_keys"] == ["orderId", "payUrl"]
    assert candidates[1]["phases"] == ["hero_click"]
    assert candidates[1]["request_body"] == {"invitationCode": ""}


def test_summarize_button_states_counts_only_enabled_visible_buttons():
    summary = summarize_button_states(
        [
            ButtonSnapshot(text="立即购买", css_class="buy-btn", enabled=True, visible=True),
            ButtonSnapshot(text="抢购人数过多，请刷新再试", css_class="buy-btn disabled", enabled=False, visible=True),
            ButtonSnapshot(text="即刻订阅", css_class="hero-btn", enabled=True, visible=False),
        ]
    )

    assert summary["total_count"] == 3
    assert summary["actionable_count"] == 1
    assert summary["texts"] == ["立即购买", "抢购人数过多，请刷新再试", "即刻订阅"]


@pytest.mark.asyncio
async def test_goto_dynamic_page_does_not_wait_for_networkidle():
    page = Mock()
    page.page = Mock()
    page.page.goto = AsyncMock()

    await goto_dynamic_page(page, "https://bigmodel.cn/glm-coding")

    page.page.goto.assert_awaited_once_with(
        "https://bigmodel.cn/glm-coding",
        wait_until="domcontentloaded",
        timeout=60000,
    )
