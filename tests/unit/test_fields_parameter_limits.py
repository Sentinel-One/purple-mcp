"""Functional tests for `fields` parameter DoS limits across tool modules."""

import json
from collections.abc import Callable

import pytest

from purple_mcp.tools import alerts, misconfigurations, vulnerabilities
from purple_mcp.tools.fields_validation import (
    MAX_FIELD_LENGTH,
    MAX_FIELDS_COUNT,
    MAX_FIELDS_JSON_LENGTH,
)


def test_fields_limits_constants_are_consistent_across_tools() -> None:
    """All tools should enforce the same fields limits."""
    assert (
        alerts.MAX_FIELDS_COUNT
        == misconfigurations.MAX_FIELDS_COUNT
        == vulnerabilities.MAX_FIELDS_COUNT
    )
    assert alerts.MAX_FIELDS_COUNT == MAX_FIELDS_COUNT == 50
    assert (
        alerts.MAX_FIELD_LENGTH
        == misconfigurations.MAX_FIELD_LENGTH
        == vulnerabilities.MAX_FIELD_LENGTH
    )
    assert alerts.MAX_FIELD_LENGTH == MAX_FIELD_LENGTH == 1024
    assert (
        alerts.MAX_FIELDS_JSON_LENGTH
        == misconfigurations.MAX_FIELDS_JSON_LENGTH
        == vulnerabilities.MAX_FIELDS_JSON_LENGTH
    )
    assert alerts.MAX_FIELDS_JSON_LENGTH == MAX_FIELDS_JSON_LENGTH == 8192


@pytest.mark.parametrize(
    "parse_fields",
    [
        pytest.param(alerts._parse_fields, id="alerts"),
        pytest.param(misconfigurations._parse_fields, id="misconfigurations"),
        pytest.param(vulnerabilities._parse_fields, id="vulnerabilities"),
    ],
)
def test_parse_fields_rejects_oversized_raw_json(
    parse_fields: Callable[[str | None], list[str] | None],
) -> None:
    """Raw fields JSON should be rejected before parsing when too large."""
    oversized_payload = '["' + ("a" * MAX_FIELDS_JSON_LENGTH) + '"]'
    with pytest.raises(ValueError, match="Fields payload is too large"):
        parse_fields(oversized_payload)


@pytest.mark.parametrize(
    "parse_fields",
    [
        pytest.param(alerts._parse_fields, id="alerts"),
        pytest.param(misconfigurations._parse_fields, id="misconfigurations"),
        pytest.param(vulnerabilities._parse_fields, id="vulnerabilities"),
    ],
)
def test_parse_fields_rejects_too_many_fields(
    parse_fields: Callable[[str | None], list[str] | None],
) -> None:
    """Field count over the limit should be rejected."""
    payload = json.dumps(["id"] * (MAX_FIELDS_COUNT + 1))
    with pytest.raises(ValueError, match="Too many fields"):
        parse_fields(payload)


@pytest.mark.parametrize(
    "parse_fields",
    [
        pytest.param(alerts._parse_fields, id="alerts"),
        pytest.param(misconfigurations._parse_fields, id="misconfigurations"),
        pytest.param(vulnerabilities._parse_fields, id="vulnerabilities"),
    ],
)
def test_parse_fields_rejects_field_string_over_max_length(
    parse_fields: Callable[[str | None], list[str] | None],
) -> None:
    """Individual field values over max length should be rejected."""
    payload = json.dumps(["id", "a" * (MAX_FIELD_LENGTH + 1)])
    with pytest.raises(ValueError, match="is too long"):
        parse_fields(payload)


@pytest.mark.parametrize(
    "parse_fields",
    [
        pytest.param(alerts._parse_fields, id="alerts"),
        pytest.param(misconfigurations._parse_fields, id="misconfigurations"),
        pytest.param(vulnerabilities._parse_fields, id="vulnerabilities"),
    ],
)
def test_parse_fields_accepts_max_field_count(
    parse_fields: Callable[[str | None], list[str] | None],
) -> None:
    """Exactly max field count should be accepted."""
    payload = json.dumps(["id"] * MAX_FIELDS_COUNT)
    parsed = parse_fields(payload)
    assert parsed is not None
    assert len(parsed) == MAX_FIELDS_COUNT


@pytest.mark.parametrize(
    "parse_fields",
    [
        pytest.param(alerts._parse_fields, id="alerts"),
        pytest.param(misconfigurations._parse_fields, id="misconfigurations"),
        pytest.param(vulnerabilities._parse_fields, id="vulnerabilities"),
    ],
)
def test_parse_fields_accepts_max_field_length(
    parse_fields: Callable[[str | None], list[str] | None],
) -> None:
    """Exactly max field length should be accepted."""
    payload = json.dumps(["a" * MAX_FIELD_LENGTH])
    parsed = parse_fields(payload)
    assert parsed == ["a" * MAX_FIELD_LENGTH]
