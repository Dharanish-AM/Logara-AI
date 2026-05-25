"""
test_timestamp.py - Unit tests for timestamp normalization utility.
Tests ISO 8601 timestamps with timezone offsets, UTC timestamps, and legacy formats.
"""

import pytest
from utils.timestamp import normalize_timestamp


class TestTimestampNormalization:
    """Test suite for normalize_timestamp function."""

    # ===== ISO 8601 with Positive Timezone Offsets =====
    def test_positive_timezone_offset_plus_5_30(self):
        """Test ISO 8601 timestamp with +05:30 timezone offset (IST)."""
        result = normalize_timestamp("2026-05-20T20:10:15+05:30")
        assert result == "2026-05-20T20:10:15+05:30"

    def test_positive_timezone_offset_plus_9_30(self):
        """Test ISO 8601 timestamp with +09:30 timezone offset (ACST)."""
        result = normalize_timestamp("2026-05-20T14:45:30+09:30")
        assert result == "2026-05-20T14:45:30+09:30"

    # ===== ISO 8601 with Negative Timezone Offsets =====
    def test_negative_timezone_offset_minus_7_00(self):
        """Test ISO 8601 timestamp with -07:00 timezone offset (PDT)."""
        result = normalize_timestamp("2026-05-20T08:12:41-07:00")
        assert result == "2026-05-20T08:12:41-07:00"

    def test_negative_timezone_offset_minus_5_00(self):
        """Test ISO 8601 timestamp with -05:00 timezone offset (CDT)."""
        result = normalize_timestamp("2026-05-20T12:30:00-05:00")
        assert result == "2026-05-20T12:30:00-05:00"

    # ===== UTC / Zulu Time =====
    def test_zulu_timestamp_with_z_suffix(self):
        """Test Zulu/UTC timestamp with Z suffix (normalized to +00:00)."""
        result = normalize_timestamp("2026-05-20T20:10:15Z")
        assert result == "2026-05-20T20:10:15+00:00"

    def test_utc_timestamp_with_explicit_offset(self):
        """Test UTC timestamp with explicit +00:00 offset."""
        result = normalize_timestamp("2026-05-20T20:10:15+00:00")
        assert result == "2026-05-20T20:10:15+00:00"

    # ===== Legacy Naive Timestamps (Backward Compatibility) =====
    def test_legacy_space_separated_timestamp(self):
        """Test space-separated format (legacy support)."""
        result = normalize_timestamp("2026-05-16 14:24:49")
        assert result == "2026-05-16T14:24:49"

    def test_legacy_iso_format_without_timezone(self):
        """Test ISO format without timezone (naive datetime)."""
        result = normalize_timestamp("2026-05-16T14:24:49")
        assert result == "2026-05-16T14:24:49"

    def test_legacy_zulu_via_strptime(self):
        """Test Zulu format as handled by legacy strptime."""
        result = normalize_timestamp("2026-05-16T14:24:49Z")
        # When parsed by strptime with %Z, it becomes naive
        # When first tried with fromisoformat after Z→+00:00 replacement
        assert result == "2026-05-16T14:24:49+00:00"

    def test_timestamp_with_microseconds(self):
        """Test timestamps with fractional seconds."""
        result = normalize_timestamp("2026-05-16 14:24:49.123456")
        assert result == "2026-05-16T14:24:49.123456"

    def test_iso_timestamp_with_microseconds(self):
        """Test ISO format with fractional seconds."""
        result = normalize_timestamp("2026-05-16T14:24:49.123456")
        assert result == "2026-05-16T14:24:49.123456"

    def test_iso_zulu_with_microseconds(self):
        """Test Zulu format with fractional seconds."""
        result = normalize_timestamp("2026-05-16T14:24:49.123456Z")
        assert result == "2026-05-16T14:24:49.123456+00:00"

    # ===== Timezone Offset with Microseconds =====
    def test_iso_with_microseconds_and_positive_offset(self):
        """Test ISO format with fractional seconds and positive offset."""
        result = normalize_timestamp("2026-05-20T20:10:15.500000+05:30")
        assert result == "2026-05-20T20:10:15.500000+05:30"

    def test_iso_with_microseconds_and_negative_offset(self):
        """Test ISO format with fractional seconds and negative offset."""
        result = normalize_timestamp("2026-05-20T08:12:41.250000-07:00")
        assert result == "2026-05-20T08:12:41.250000-07:00"

    # ===== Malformed Inputs (Fallback to Raw Value) =====
    def test_malformed_timestamp_returns_raw_value(self):
        """Test that malformed timestamp is returned as-is."""
        result = normalize_timestamp("not-a-time")
        assert result == "not-a-time"

    def test_invalid_date_returns_raw_value(self):
        """Test that invalid date is returned as-is."""
        result = normalize_timestamp("2026-13-45T25:99:99")
        assert result == "2026-13-45T25:99:99"

    def test_partial_timestamp_returns_raw_value(self):
        """Test that incomplete timestamp is returned as-is."""
        result = normalize_timestamp("2026-05")
        assert result == "2026-05"

    def test_random_text_returns_raw_value(self):
        """Test that random text is returned as-is."""
        result = normalize_timestamp("hello world")
        assert result == "hello world"

    # ===== Edge Cases =====
    def test_empty_string_returns_none(self):
        """Test that empty string returns None."""
        result = normalize_timestamp("")
        assert result is None

    def test_whitespace_only_returns_none(self):
        """Test that whitespace-only string returns None."""
        result = normalize_timestamp("   ")
        assert result is None

    def test_none_input_returns_none(self):
        """Test that None input returns None."""
        result = normalize_timestamp(None)
        assert result is None

    def test_timestamp_with_leading_trailing_whitespace(self):
        """Test that whitespace is stripped before parsing."""
        result = normalize_timestamp("  2026-05-20T20:10:15+05:30  ")
        assert result == "2026-05-20T20:10:15+05:30"

    def test_timestamp_with_leading_trailing_whitespace_naive(self):
        """Test that whitespace is stripped for naive timestamps."""
        result = normalize_timestamp("  2026-05-16 14:24:49  ")
        assert result == "2026-05-16T14:24:49"

    # ===== Real-World Examples =====
    def test_real_world_india_timezone(self):
        """Test real-world India Standard Time example."""
        # IST is UTC+05:30
        result = normalize_timestamp("2026-05-25T18:45:30+05:30")
        assert result == "2026-05-25T18:45:30+05:30"

    def test_real_world_us_pacific_timezone(self):
        """Test real-world US Pacific Daylight Time example."""
        # PDT is UTC-07:00
        result = normalize_timestamp("2026-05-25T10:30:45-07:00")
        assert result == "2026-05-25T10:30:45-07:00"

    def test_real_world_uk_timezone(self):
        """Test real-world UK/GMT timezone."""
        # BST is UTC+01:00
        result = normalize_timestamp("2026-05-25T15:30:00+01:00")
        assert result == "2026-05-25T15:30:00+01:00"

    def test_real_world_tokyo_timezone(self):
        """Test real-world Tokyo timezone."""
        # JST is UTC+09:00
        result = normalize_timestamp("2026-05-25T23:15:00+09:00")
        assert result == "2026-05-25T23:15:00+09:00"

    def test_real_world_sydney_timezone(self):
        """Test real-world Sydney timezone."""
        # AEST is UTC+10:00
        result = normalize_timestamp("2026-05-25T04:20:00+10:00")
        assert result == "2026-05-25T04:20:00+10:00"

    # ===== Regression Tests for Existing Functionality =====
    def test_existing_parser_integration_legacy_format(self):
        """Test that legacy parser format still works correctly."""
        # This mirrors test_timestamp_normalization from test_parser.py
        result = normalize_timestamp("2026-05-16 14:24:49")
        assert result == "2026-05-16T14:24:49"

    def test_existing_iso_format_support(self):
        """Test that ISO format support is maintained."""
        # This mirrors test_iso_timestamp_normalization from test_parser.py
        result = normalize_timestamp("2026-05-16T14:24:49")
        assert result == "2026-05-16T14:24:49"

    def test_existing_zulu_format_support(self):
        """Test that Zulu format support is maintained."""
        # This mirrors test_zulu_timestamp_normalization from test_parser.py
        result = normalize_timestamp("2026-05-16T14:24:49Z")
        assert result == "2026-05-16T14:24:49+00:00"


class TestTimestampEdgeCasesAndBoundaries:
    """Additional edge case tests for timezone normalization."""

    def test_midnight_with_timezone(self):
        """Test midnight timestamp with timezone offset."""
        result = normalize_timestamp("2026-05-20T00:00:00+05:30")
        assert result == "2026-05-20T00:00:00+05:30"

    def test_end_of_day_with_timezone(self):
        """Test end-of-day timestamp with timezone offset."""
        result = normalize_timestamp("2026-05-20T23:59:59+05:30")
        assert result == "2026-05-20T23:59:59+05:30"

    def test_leap_second_adjacent_timestamp(self):
        """Test timestamp near leap second boundary."""
        result = normalize_timestamp("2026-05-20T23:59:58-07:00")
        assert result == "2026-05-20T23:59:58-07:00"

    def test_zero_hour_offset(self):
        """Test timezone offset that equals UTC (+00:00)."""
        result = normalize_timestamp("2026-05-20T20:10:15+00:00")
        assert result == "2026-05-20T20:10:15+00:00"

    def test_negative_zero_hour_offset(self):
        """Test negative zero timezone offset (-00:00)."""
        # Some systems use -00:00 to indicate unknown timezone, but Python's
        # datetime.fromisoformat() normalizes -00:00 to +00:00 (per ISO 8601)
        result = normalize_timestamp("2026-05-20T20:10:15-00:00")
        assert result == "2026-05-20T20:10:15+00:00"

    def test_half_hour_offset_positive(self):
        """Test half-hour positive offset (+05:30)."""
        result = normalize_timestamp("2026-05-20T20:10:15+05:30")
        assert result == "2026-05-20T20:10:15+05:30"

    def test_half_hour_offset_negative(self):
        """Test half-hour negative offset (-03:30)."""
        result = normalize_timestamp("2026-05-20T20:10:15-03:30")
        assert result == "2026-05-20T20:10:15-03:30"

    def test_quarter_hour_offset(self):
        """Test quarter-hour offset (+05:45)."""
        result = normalize_timestamp("2026-05-20T20:10:15+05:45")
        assert result == "2026-05-20T20:10:15+05:45"

    def test_maximum_positive_offset(self):
        """Test maximum positive offset (+14:00)."""
        result = normalize_timestamp("2026-05-20T20:10:15+14:00")
        assert result == "2026-05-20T20:10:15+14:00"

    def test_maximum_negative_offset(self):
        """Test maximum negative offset (-12:00)."""
        result = normalize_timestamp("2026-05-20T20:10:15-12:00")
        assert result == "2026-05-20T20:10:15-12:00"
