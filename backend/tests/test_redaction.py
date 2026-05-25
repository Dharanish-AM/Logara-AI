"""Tests for backend/utils/redaction.py"""
from utils.redaction import build_default_redactor, Redactor, DEFAULT_RULES


def test_redacts_jwt():
    r = build_default_redactor()
    text = "User logged in with token eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.signature"
    out = r.redact(text)
    assert "[REDACTED:JWT]" in out
    assert "eyJhbGciOiJIUzI1NiJ9" not in out


def test_redacts_aws_access_key():
    r = build_default_redactor()
    out = r.redact("AWS key AKIAIOSFODNN7EXAMPLE was used")
    assert "[REDACTED:AWS_ACCESS_KEY]" in out
    assert "AKIAIOSFODNN7EXAMPLE" not in out


def test_redacts_openai_key():
    r = build_default_redactor()
    out = r.redact("sk-1234567890abcdefghij failed auth")
    assert "[REDACTED:API_KEY]" in out


def test_redacts_email():
    r = build_default_redactor()
    out = r.redact("user alice@example.com signed up")
    assert "[REDACTED:EMAIL]" in out
    assert "alice@example.com" not in out


def test_redacts_bearer_token():
    r = build_default_redactor()
    out = r.redact("Authorization: Bearer abc123def456ghi789jkl012")
    assert "[REDACTED:BEARER]" in out


def test_credit_card_luhn_valid():
    r = build_default_redactor()
    # 4111 1111 1111 1111 is a known valid Luhn test number
    out = r.redact("Charged card 4111 1111 1111 1111 for $50")
    assert "[REDACTED:CREDIT_CARD]" in out


def test_credit_card_luhn_invalid_passes_through():
    r = build_default_redactor()
    # Random 16-digit run that fails Luhn — should NOT be redacted
    out = r.redact("Order id 1234567890123456 placed")
    assert "1234567890123456" in out


def test_disabled_passes_text_through():
    r = build_default_redactor(enabled=False)
    text = "token eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.signature"
    assert r.redact(text) == text


def test_pattern_filter_only_enables_named():
    r = build_default_redactor(pattern_names=["email"])
    out = r.redact("alice@example.com used key sk-abcdef1234567890abcdef")
    assert "[REDACTED:EMAIL]" in out
    assert "sk-abcdef1234567890abcdef" in out  # API key NOT redacted


def test_ipv4_off_by_default():
    r = build_default_redactor()
    out = r.redact("Request from 192.168.1.100")
    assert "192.168.1.100" in out


def test_ipv4_when_enabled():
    r = build_default_redactor(include_ipv4=True)
    out = r.redact("Request from 192.168.1.100")
    assert "[REDACTED:IPV4]" in out


def test_redact_dict_walks_nested_values():
    r = build_default_redactor()

    data = {
        "user": {"email": "alice@example.com"},
        "headers": {"Authorization": "Bearer abc123def456ghi789jkl012"},
        "level": "ERROR",
        "tags": ["sk-abcdef1234567890abcdef", "normal-tag"],
    }

    redacted = r.redact_dict(data)

    # Original input should remain unchanged
    assert data["user"]["email"] == "alice@example.com"

    # Returned payload should contain sanitized values
    assert "[REDACTED:EMAIL]" in redacted["user"]["email"]
    assert "[REDACTED:BEARER]" in redacted["headers"]["Authorization"]
    assert redacted["level"] == "ERROR"
    assert "[REDACTED:API_KEY]" in redacted["tags"][0]
    assert redacted["tags"][1] == "normal-tag"

def test_redact_dict_disabled_returns_unchanged():
    r = build_default_redactor(enabled=False)
    data = {"email": "alice@example.com"}
    r.redact_dict(data)
    assert data["email"] == "alice@example.com"


def test_empty_text():
    r = build_default_redactor()
    assert r.redact("") == ""
    assert r.redact(None) is None

from utils.redaction import REDACTION_METRICS


def reset_metrics():
    REDACTION_METRICS["total_redactions"] = 0
    REDACTION_METRICS["payloads_sanitized"] = 0


def test_redaction_metrics_increment():
    reset_metrics()

    r = build_default_redactor()

    result = r.redact_with_summary(
        "Contact admin@example.com immediately"
    )

    assert "[REDACTED:EMAIL]" in result.text

    assert REDACTION_METRICS["total_redactions"] == 1
    assert REDACTION_METRICS["payloads_sanitized"] == 1


def test_multiple_redaction_types_tracking():
    reset_metrics()

    r = build_default_redactor()

    text = (
        "Email alice@example.com "
        "used key sk-1234567890abcdefghij"
    )

    result = r.redact_with_summary(text)

    assert result.matches["EMAIL"] == 1
    assert result.matches["API_KEY"] == 1

    assert REDACTION_METRICS["total_redactions"] == 2
    assert REDACTION_METRICS["payloads_sanitized"] == 1


def test_redaction_result_contains_match_summary():
    reset_metrics()

    r = build_default_redactor()

    result = r.redact_with_summary(
        "Bearer abc123def456ghi789jkl012"
    )

    assert result.matches["BEARER"] == 1


def test_no_redactions_do_not_increment_metrics():
    reset_metrics()

    r = build_default_redactor()

    result = r.redact_with_summary(
        "Normal application log"
    )

    assert result.matches == {}

    assert REDACTION_METRICS["total_redactions"] == 0
    assert REDACTION_METRICS["payloads_sanitized"] == 0

def test_redact_dict_does_not_mutate_original_payload():
    r = build_default_redactor()

    original = {
        "user": {
            "email": "alice@example.com"
        }
    }

    original_snapshot = {
        "user": {
            "email": "alice@example.com"
        }
    }

    redacted = r.redact_dict(original)

    # Original object must remain unchanged
    assert original == original_snapshot

    # Returned structure must contain redacted value
    assert "[REDACTED:EMAIL]" in redacted["user"]["email"]


def test_redact_dict_returns_new_object():
    r = build_default_redactor()

    data = {
        "email": "alice@example.com"
    }

    redacted = r.redact_dict(data)

    assert redacted is not data


def test_redact_dict_nested_lists_preserve_immutability():
    r = build_default_redactor()

    original = {
        "items": [
            {"token": "sk-abcdef1234567890abcdef"}
        ]
    }

    snapshot = {
        "items": [
            {"token": "sk-abcdef1234567890abcdef"}
        ]
    }

    redacted = r.redact_dict(original)

    assert original == snapshot

    assert (
        "[REDACTED:API_KEY]"
        in redacted["items"][0]["token"]
    )