"""Tests for the shared bounded fields-parameter validator."""

import json

import pytest

from purple_mcp.tools.fields_validation import (
    MAX_FIELD_LENGTH,
    MAX_FIELDS_COUNT,
    MAX_FIELDS_JSON_LENGTH,
    parse_fields_parameter,
)


def test_none_returns_none() -> None:
    """Test that None input returns None."""
    assert parse_fields_parameter(None) is None


def test_valid_list_parsed() -> None:
    """Test that valid JSON field list is parsed correctly."""
    assert parse_fields_parameter(json.dumps(["id", "name"])) == ["id", "name"]


def test_too_many_fields_rejected() -> None:
    """Test that field lists exceeding MAX_FIELDS_COUNT are rejected."""
    payload = json.dumps([f"f{i}" for i in range(MAX_FIELDS_COUNT + 1)])
    with pytest.raises(ValueError, match="Too many fields"):
        parse_fields_parameter(payload)


def test_payload_too_large_rejected() -> None:
    """Test that payloads exceeding MAX_FIELDS_JSON_LENGTH are rejected."""
    payload = "x" * (MAX_FIELDS_JSON_LENGTH + 1)
    with pytest.raises(ValueError, match="too large"):
        parse_fields_parameter(payload)


def test_field_too_long_rejected() -> None:
    """Test that individual fields exceeding MAX_FIELD_LENGTH are rejected."""
    payload = json.dumps(["a" * (MAX_FIELD_LENGTH + 1)])
    with pytest.raises(ValueError, match="too long"):
        parse_fields_parameter(payload)


def test_non_list_rejected() -> None:
    """Test that non-list JSON structures are rejected."""
    with pytest.raises(ValueError, match="must be an array"):
        parse_fields_parameter(json.dumps({"not": "a list"}))


def test_non_string_element_rejected() -> None:
    """Test that non-string field elements are rejected."""
    with pytest.raises(ValueError, match="must be strings"):
        parse_fields_parameter(json.dumps(["ok", 123]))


def test_invalid_json_rejected() -> None:
    """Test that malformed JSON is rejected."""
    with pytest.raises(ValueError, match="Invalid JSON"):
        parse_fields_parameter("{not json")
