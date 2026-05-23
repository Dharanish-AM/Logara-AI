import pytest
from utils.redaction import build_default_redactor


@pytest.fixture
def redactor():
    return build_default_redactor(enabled=True)


def test_original_dict_not_mutated(redactor):
    original = {"message": "email is test@example.com", "level": "INFO"}
    original_copy = original.copy()
    redactor.redact_dict(original)
    assert original == original_copy


def test_nested_dict_not_mutated(redactor):
    original = {"outer": {"message": "email is test@example.com"}}
    original_msg = original["outer"]["message"]
    redactor.redact_dict(original)
    assert original["outer"]["message"] == original_msg


def test_return_value_is_redacted(redactor):
    data = {"message": "email is test@example.com"}
    result = redactor.redact_dict(data)
    assert "REDACTED" in result["message"]


def test_nested_return_value_is_redacted(redactor):
    data = {"outer": {"message": "email is test@example.com"}}
    result = redactor.redact_dict(data)
    assert "REDACTED" in result["outer"]["message"]


def test_disabled_redactor_returns_original(redactor):
    redactor.enabled = False
    original = {"message": "email is test@example.com"}
    result = redactor.redact_dict(original)
    assert result is original  # no copy made when disabled