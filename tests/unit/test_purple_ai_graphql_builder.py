"""Unit tests for Purple AI GraphQL request builder.

This test suite verifies that the `_build_graphql_request` function emits the
nested `PurpleTenantDetailsRequest` schema correctly and properly escapes dynamic
values to prevent GraphQL injection.
"""

import json
import uuid
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from purple_mcp.libs.purple_ai.client import _build_graphql_request

# Fixed timestamp so equality/escaping assertions don't depend on wall-clock.
_FIXED_USER_TIME = datetime(2026, 5, 12, 14, 30, 0, tzinfo=timezone(timedelta(hours=-7)))


def _default_kwargs(**overrides: Any) -> Mapping[str, Any]:
    """Return a baseline kwargs dict for `_build_graphql_request` call sites."""
    defaults: dict[str, Any] = {
        "start_time": 1000,
        "end_time": 2000,
        "base_url": "https://example.test",
        "version": "1.0.0",
        "session_id": uuid.uuid4().hex,
        "email_address": "test@example.test",
        "user_agent": "TestAgent/1.0",
        "build_date": "2025-01-01",
        "build_hash": "abc123",
        "user_time": _FIXED_USER_TIME,
        "console_id": "1111111111111111111",
        "tenant_id": "2222222222222222222",
        "account_id": "3333333333333333333",
        "site_id": "4444444444444444444",
        "conversation_id": "CONV123",
    }
    defaults.update(overrides)
    return defaults


def test_build_graphql_request_omits_legacy_fields() -> None:
    """Legacy-only schema fields must not appear anywhere in the output.

    `accountId:` deliberately still appears — it is a valid field in the
    nested `consoleDetails` block (scope ID). `teamToken:` is the only field
    that was permanently removed.
    """
    query = _build_graphql_request(**_default_kwargs())
    assert "teamToken:" not in query, "Legacy field 'teamToken:' leaked into output"


def test_build_graphql_request_emits_user_and_console_metadata() -> None:
    """emailAddress, buildDate, buildHash, and version flow through to the request."""
    query = _build_graphql_request(**_default_kwargs())
    assert 'emailAddress: "test@example.test"' in query
    assert 'buildDate: "2025-01-01"' in query
    assert 'buildHash: "abc123"' in query
    assert 'version: "1.0.0"' in query


def test_build_graphql_request_does_not_emit_user_id() -> None:
    """MCP does not emit userId; purple_server reconciles it from the token.

    consoleId, by contrast, IS emitted: service tokens skip server-side
    reconciliation, so the deployment ID must be supplied by the request.
    """
    query = _build_graphql_request(**_default_kwargs())
    assert "userId" not in query


def test_build_graphql_request_emits_all_scope_ids() -> None:
    """Scope IDs flow through from kwargs into the nested consoleDetails."""
    query = _build_graphql_request(**_default_kwargs())
    assert 'consoleId: "1111111111111111111"' in query
    assert 'tenantId: "2222222222222222222"' in query
    assert 'accountId: "3333333333333333333"' in query
    assert 'siteId: "4444444444444444444"' in query
    assert 'baseUrl: "https://example.test"' in query


def test_build_graphql_request_emits_null_for_missing_scope_ids() -> None:
    """Scope IDs passed as None become GraphQL null literals."""
    query = _build_graphql_request(
        **_default_kwargs(
            console_id=None,
            tenant_id=None,
            account_id=None,
            site_id=None,
        )
    )
    assert "consoleId: null" in query
    assert "tenantId: null" in query
    assert "accountId: null" in query
    assert "siteId: null" in query


def test_build_graphql_request_emits_user_time_as_iso_8601_string() -> None:
    """user_time is serialized as a quoted ISO-8601 string (GraphQL DateTime scalar)."""
    query = _build_graphql_request(**_default_kwargs())
    assert f"userTime: {json.dumps(_FIXED_USER_TIME.isoformat())}" in query


def test_build_graphql_request_omits_user_time_when_none() -> None:
    """When user_time is None the userTime field is omitted entirely, not set to null."""
    query = _build_graphql_request(**_default_kwargs(user_time=None))
    assert "userTime" not in query


@pytest.mark.parametrize(
    "field,payload",
    [
        ("user_agent", 'test"user/quote'),
        ("user_agent", "Test\\Agent\\1.0"),
        ("user_agent", "Agent\nwith\nnewlines"),
        ("session_id", "id-with-unicode-例え"),
        ("user_agent", "Agent\twith\ttabs"),
    ],
)
def test_build_graphql_request_escapes_special_characters(field: str, payload: str) -> None:
    """Dynamic values pass through json.dumps(), preventing injection.

    Asserts the json.dumps() form of the payload appears verbatim in the
    output — json.dumps handles quotes, backslashes, newlines, and Unicode
    (ASCII-escaped by default).

    """
    query = _build_graphql_request(**_default_kwargs(**{field: payload}))
    assert json.dumps(payload) in query


def test_build_graphql_request_blocks_injection_via_closing_braces() -> None:
    """Closing braces inside string values do not escape the GraphQL structure."""
    malicious = "test } } query { malicious"
    query = _build_graphql_request(**_default_kwargs(user_agent=malicious))

    # Only one outer query definition present.
    assert query.count("query SimpleTestQuery") == 1
    # Payload is safely contained inside a quoted string.
    assert json.dumps(malicious) in query


def test_build_graphql_request_numeric_time_range_is_unquoted() -> None:
    """Timestamps are numeric literals, not strings."""
    query = _build_graphql_request(
        **_default_kwargs(start_time=1234567890123, end_time=1234567899999)
    )
    assert "start: 1234567890123" in query
    assert "end: 1234567899999" in query


def test_build_graphql_request_structure() -> None:
    """The emitted query has the expected top-level GraphQL scaffolding."""
    query = _build_graphql_request(**_default_kwargs())
    assert "query SimpleTestQuery($input: String!)" in query
    assert "purpleLaunchQuery" in query
    assert "inputContent:" in query
    assert "$input" in query
    assert "userInput: $input" in query


def test_build_graphql_request_repeats_identical_tenant_details_block() -> None:
    """The tenantDetails block is emitted identically at both required locations.

    purple_server requires request.tenantDetails and
    request.inputContent.tenantDetails to be byte-identical, so the builder
    interpolates a single shared fragment. Extract the first rendered block
    from the output and assert the exact same text appears twice.
    """
    query = _build_graphql_request(**_default_kwargs())

    block_start = query.index("tenantDetails:")
    # The first block ends just before the `conversation:` field that follows
    # it in the request body.
    block_end = query.index("conversation:", block_start)
    first_block = query[block_start:block_end].rstrip()

    assert query.count(first_block) == 2


def test_build_graphql_request_returns_non_empty_string() -> None:
    """Smoke test on the return type."""
    result = _build_graphql_request(**_default_kwargs())
    assert isinstance(result, str)
    assert len(result) > 0
