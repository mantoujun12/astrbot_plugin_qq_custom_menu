"""core.redaction 的响应与文本脱敏测试。"""

from __future__ import annotations

from core.redaction import MASK_VALUE, redact_sensitive_data, redact_sensitive_text


def test_redacts_nested_sensitive_mapping_fields() -> None:
    payload = {
        "message": "bad request",
        "clientSecret": "client-secret",
        "nested": {
            "access_token": "token-value",
            "authorization": "QQBot token-value",
            "safe": "kept",
        },
        "items": [{"password": "hunter2"}, {"safe": 1}],
    }

    redacted = redact_sensitive_data(payload)

    assert redacted["message"] == "bad request"
    assert redacted["clientSecret"] == MASK_VALUE
    assert redacted["nested"]["access_token"] == MASK_VALUE
    assert redacted["nested"]["authorization"] == MASK_VALUE
    assert redacted["nested"]["safe"] == "kept"
    assert redacted["items"] == [{"password": MASK_VALUE}, {"safe": 1}]


def test_redacts_known_values_and_inline_credentials() -> None:
    text = (
        'client=known-secret access_token=tok-123 "clientSecret":"tok-123" '
        "Authorization: QQBot tok-123"
    )

    redacted = redact_sensitive_text(text, known_values=("known-secret", "tok-123"))

    assert "known-secret" not in redacted
    assert "tok-123" not in redacted
    assert redacted.count(MASK_VALUE) >= 3


def test_redacts_json_text_nested_in_raw_response() -> None:
    payload = {
        "raw": '{"error":"denied","access_token":"leaked-token","safe":"value"}',
    }

    redacted = redact_sensitive_data(payload)

    assert "leaked-token" not in str(redacted)
    assert MASK_VALUE in redacted["raw"]
    assert '"error":"denied"' in redacted["raw"]
