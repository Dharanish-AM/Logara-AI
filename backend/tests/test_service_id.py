import pytest

from utils.service_id import extract_service_id, normalize_service_id, validate_service_id


def test_normalize_service_id_accepts_valid_values():
    assert normalize_service_id("payments-api") == "payments-api"
    assert normalize_service_id("service.name") == "service.name"
    assert normalize_service_id("tenant:auth_service") == "tenant:auth_service"


def test_normalize_service_id_rejects_invalid_values():
    assert normalize_service_id("") is None
    assert normalize_service_id("   ") is None
    assert normalize_service_id("bad service") is None
    assert normalize_service_id("../../etc/passwd") is None


def test_validate_service_id_raises_for_invalid_value():
    with pytest.raises(ValueError):
        validate_service_id("bad service")


def test_extract_service_id_prefers_top_level_value():
    service_id = extract_service_id(
        parsed={"service_id": "payments-api"},
        metadata={"service_id": "auth-service"},
    )

    assert service_id == "payments-api"


def test_extract_service_id_supports_otel_service_name():
    service_id = extract_service_id(
        metadata={"service.name": "checkout-api"},
    )

    assert service_id == "checkout-api"


def test_extract_service_id_uses_default():
    assert extract_service_id(default="unknown_service") == "unknown_service"
