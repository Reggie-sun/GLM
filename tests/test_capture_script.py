from pathlib import Path

from app.services.purchase_capture import (
    ensure_output_dir,
    is_interesting_url,
    sanitize_headers,
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
