from utils.timestamp import normalize_timestamp

def test_epoch_seconds():
    result = normalize_timestamp("1716800000")
    assert result is not None
    assert "2024-05-27" in result

def test_epoch_milliseconds():
    result = normalize_timestamp("1716800000000")
    assert result is not None
    assert "2024-05-27" in result

def test_normal_format_still_works():
    result = normalize_timestamp("2024-05-27 10:13:20")
    assert result is not None

def test_invalid_returns_raw():
    result = normalize_timestamp("not-a-timestamp")
    assert result == "not-a-timestamp"