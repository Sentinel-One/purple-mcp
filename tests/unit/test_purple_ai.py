"""Tests for purple_mcp.libs.purple_ai module."""

import re
import string
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import httpx
import pytest
from pydantic import ValidationError
from respx import MockRouter

from purple_mcp.libs.purple_ai import (
    PurpleAIClient,
    PurpleAIConfig,
    PurpleAIConsoleDetails,
    PurpleAIResultType,
    PurpleAIUserDetails,
    ask_purple,
    client,
    sync_ask_purple,
)
from purple_mcp.libs.purple_ai.client import _random_conv_id


@pytest.fixture
def purple_ai_config() -> PurpleAIConfig:
    """Return a valid PurpleAIConfig instance for testing."""
    return PurpleAIConfig(
        auth_token="TEST_AUTH_TOKEN",
        user_details=PurpleAIUserDetails(
            session_id=uuid.uuid4().hex,
            email_address="test@example.test",
            user_agent="TestClient/1.0",
            build_date="2025-01-01",
            build_hash="testhash",
        ),
        console_details=PurpleAIConsoleDetails(
            base_url="https://test.example.test",
            version="1.0.0",
        ),
    )


async def test_ask_purple_success_message(
    purple_ai_config: PurpleAIConfig, respx_mock: MockRouter, purple_ai_env: None
) -> None:
    """Test successful 'MESSAGE' response from ask_purple."""
    mock_response = {
        "data": {
            "purpleLaunchQuery": {
                "resultType": "MESSAGE",
                "result": {"message": "Hello, world!"},
                "status": {"error": None},
            }
        }
    }
    respx_mock.post(purple_ai_config.graphql_url).mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    result_type, response = await ask_purple(purple_ai_config, "test query")

    assert result_type == PurpleAIResultType.MESSAGE
    assert response == "Hello, world!"


async def test_ask_purple_success_power_query(
    purple_ai_config: PurpleAIConfig, respx_mock: MockRouter, purple_ai_env: None
) -> None:
    """Test successful 'POWER_QUERY' response from ask_purple."""
    mock_response = {
        "data": {
            "purpleLaunchQuery": {
                "resultType": "POWER_QUERY",
                "result": {"powerQuery": {"query": "Test PowerQuery"}},
                "status": {"error": None},
            }
        }
    }
    respx_mock.post(purple_ai_config.graphql_url).mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    result_type, response = await ask_purple(purple_ai_config, "test query")

    assert result_type == PurpleAIResultType.POWER_QUERY
    assert response == "Test PowerQuery"


def test_sync_ask_purple(
    purple_ai_config: PurpleAIConfig, respx_mock: MockRouter, purple_ai_env: None
) -> None:
    """Test synchronous wrapper sync_ask_purple."""
    mock_response = {
        "data": {
            "purpleLaunchQuery": {
                "resultType": "MESSAGE",
                "result": {"message": "Sync success!"},
                "status": {"error": None},
            }
        }
    }
    respx_mock.post(purple_ai_config.graphql_url).mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    response = sync_ask_purple(purple_ai_config, "test query")

    assert response == "Sync success!"


async def test_ask_purple_http_error(
    purple_ai_config: PurpleAIConfig, respx_mock: MockRouter, purple_ai_env: None
) -> None:
    """Test error handling for HTTP error responses."""
    respx_mock.post(purple_ai_config.graphql_url).mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )

    result_type, response = await ask_purple(purple_ai_config, "test query")

    assert result_type is None
    assert "HTTP error from Purple AI" in response
    assert "500" in response


async def test_ask_purple_empty_response(
    purple_ai_config: PurpleAIConfig, respx_mock: MockRouter, purple_ai_env: None
) -> None:
    """Test error handling for empty response content."""
    respx_mock.post(purple_ai_config.graphql_url).mock(
        return_value=httpx.Response(200, content=b"")
    )

    result_type, response = await ask_purple(purple_ai_config, "test query")

    assert result_type is None
    assert "Failed to parse JSON response from Purple AI" in response


async def test_ask_purple_invalid_json(
    purple_ai_config: PurpleAIConfig, respx_mock: MockRouter, purple_ai_env: None
) -> None:
    """Test error handling for invalid JSON responses."""
    respx_mock.post(purple_ai_config.graphql_url).mock(
        return_value=httpx.Response(200, text="not json")
    )

    # JSON decode errors should be handled gracefully
    result_type, response = await ask_purple(purple_ai_config, "test query")

    assert result_type is None
    assert "Failed to parse JSON response from Purple AI" in response


async def test_ask_purple_graphql_errors(
    purple_ai_config: PurpleAIConfig, respx_mock: MockRouter, purple_ai_env: None
) -> None:
    """Test error handling for GraphQL errors in response."""
    mock_response = {"errors": [{"message": "GraphQL error"}], "data": None}
    respx_mock.post(purple_ai_config.graphql_url).mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    result_type, response = await ask_purple(purple_ai_config, "test query")

    assert result_type is None
    assert "GraphQL errors in Purple AI response" in response


async def test_ask_purple_missing_data(
    purple_ai_config: PurpleAIConfig, respx_mock: MockRouter, purple_ai_env: None
) -> None:
    """Test error handling for missing data in response."""
    mock_response = {"data": None}
    respx_mock.post(purple_ai_config.graphql_url).mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    result_type, response = await ask_purple(purple_ai_config, "test query")

    assert result_type is None
    assert "No data field in Purple AI response" in response


async def test_ask_purple_missing_purple_launch_query(
    purple_ai_config: PurpleAIConfig, respx_mock: MockRouter, purple_ai_env: None
) -> None:
    """Test error handling for missing purpleLaunchQuery in response."""
    mock_response = {"data": {"someOtherField": "value"}}
    respx_mock.post(purple_ai_config.graphql_url).mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    result_type, response = await ask_purple(purple_ai_config, "test query")

    assert result_type is None
    assert "Missing purpleLaunchQuery in response" in response


async def test_ask_purple_status_error(
    purple_ai_config: PurpleAIConfig, respx_mock: MockRouter, purple_ai_env: None
) -> None:
    """Test error handling for status errors in Purple AI response."""
    mock_response = {
        "data": {
            "purpleLaunchQuery": {
                "resultType": "MESSAGE",
                "result": {"message": "This won't be returned"},
                "status": {"error": "Something went wrong"},
            }
        }
    }
    respx_mock.post(purple_ai_config.graphql_url).mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    result_type, response = await ask_purple(purple_ai_config, "test query")

    assert result_type is None
    assert "Error from Purple AI: Something went wrong" in response


async def test_ask_purple_invalid_result_type(
    purple_ai_config: PurpleAIConfig, respx_mock: MockRouter, purple_ai_env: None
) -> None:
    """Test error handling for invalid result types."""
    mock_response = {
        "data": {
            "purpleLaunchQuery": {
                "resultType": "UNKNOWN_TYPE",
                "result": {"message": "Test message"},
                "status": {"error": None},
            }
        }
    }
    respx_mock.post(purple_ai_config.graphql_url).mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    result_type, response = await ask_purple(purple_ai_config, "test query")

    assert result_type is None
    assert "Unexpected result type from Purple AI: UNKNOWN_TYPE" in response


async def test_ask_purple_unhandled_result_type(
    purple_ai_config: PurpleAIConfig,
    respx_mock: MockRouter,
    purple_ai_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test error handling for unhandled result types."""
    # Create a mock response with a valid enum value but unhandled case
    mock_response = {
        "data": {
            "purpleLaunchQuery": {
                "resultType": "MESSAGE",  # This will be handled, need to test other path
                "result": {"message": "Test message"},
                "status": {"error": None},
            }
        }
    }

    # Mock the response to return a different result type to test the else case
    # Create a mock enum value that's not MESSAGE or POWER_QUERY
    mock_result_type = Mock()
    mock_result_type.name = "UNKNOWN_HANDLED_TYPE"
    mock_enum = Mock(return_value=mock_result_type)

    monkeypatch.setattr(client, PurpleAIResultType.__name__, mock_enum)

    respx_mock.post(purple_ai_config.graphql_url).mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    result_type, response = await ask_purple(purple_ai_config, "test query")

    assert result_type is None
    assert "Unhandled result type from Purple AI:" in response


def test_sync_ask_purple_error_handling(
    purple_ai_config: PurpleAIConfig, respx_mock: MockRouter, purple_ai_env: None
) -> None:
    """Test sync_ask_purple with error response."""
    respx_mock.post(purple_ai_config.graphql_url).mock(
        return_value=httpx.Response(500, text="Server Error")
    )

    response = sync_ask_purple(purple_ai_config, "test query")

    assert "HTTP error from Purple AI" in response
    assert "500" in response


async def test_ask_purple_non_dict_json_response(
    purple_ai_config: PurpleAIConfig, respx_mock: MockRouter, purple_ai_env: None
) -> None:
    """Test error handling for non-dict JSON responses."""
    respx_mock.post(purple_ai_config.graphql_url).mock(
        return_value=httpx.Response(200, json=["not", "a", "dict"])
    )

    result_type, response = await ask_purple(purple_ai_config, "test query")

    assert result_type is None
    assert "Invalid JSON response from Purple AI" in response
    assert "expected dict, got list" in response


async def test_ask_purple_null_json_response(
    purple_ai_config: PurpleAIConfig, respx_mock: MockRouter, purple_ai_env: None
) -> None:
    """Test error handling for null JSON responses from transient console hiccups."""
    # Return a response with literal "null" in JSON body
    respx_mock.post(purple_ai_config.graphql_url).mock(
        return_value=httpx.Response(200, content=b"null")
    )

    result_type, response = await ask_purple(purple_ai_config, "test query")

    assert result_type is None
    assert "Invalid JSON response from Purple AI" in response
    assert "expected dict, got NoneType" in response


async def test_ask_purple_data_field_list_response(
    purple_ai_config: PurpleAIConfig, respx_mock: MockRouter, purple_ai_env: None
) -> None:
    """Test error handling when data field is a list instead of dict (e.g., {"data": []})."""
    # Return a response with data field as a list instead of dict
    respx_mock.post(purple_ai_config.graphql_url).mock(
        return_value=httpx.Response(200, json={"data": []})
    )

    result_type, response = await ask_purple(purple_ai_config, "test query")

    assert result_type is None
    assert "Invalid data field in Purple AI response" in response
    assert "expected dict, got list" in response


async def test_ask_purple_auth_token_in_config(
    purple_ai_config: PurpleAIConfig, respx_mock: MockRouter
) -> None:
    """Test that auth_token from config is used in API requests."""
    mock_response = {
        "data": {
            "purpleLaunchQuery": {
                "resultType": "MESSAGE",
                "result": {"message": "Test message"},
                "status": {"error": None},
            }
        }
    }

    # Mock the GraphQL request and capture headers
    request_mock = respx_mock.post(purple_ai_config.graphql_url).mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    result_type, response = await ask_purple(purple_ai_config, "test query")

    # Verify the auth token from config was used in the Authorization header
    assert request_mock.called
    request = request_mock.calls[0].request
    assert request.headers.get("Authorization") == f"ApiToken {purple_ai_config.auth_token}"
    assert result_type == PurpleAIResultType.MESSAGE
    assert response == "Test message"


def test_generate_query_with_conversation_id_override(purple_ai_config: PurpleAIConfig) -> None:
    """Test conversation ID override in _generate_query function."""
    client = PurpleAIClient(purple_ai_config)

    # Test with custom conversation ID
    query_string = client._generate_query(
        "test query", conversation_id_for_tests="TEST_CONVERSATION_ID"
    )

    # Extract conversation ID from the generated GraphQL query string
    assert 'id: "TEST_CONVERSATION_ID"' in query_string

    # Test without custom conversation ID (should generate random one)
    query_string_default = client._generate_query("test query")

    # Find the conversation ID in the GraphQL string

    match = re.search(r'id: "([^"]+)"', query_string_default)
    assert match is not None, "Should find conversation ID in GraphQL query"

    default_conversation_id = match.group(1)
    assert default_conversation_id.startswith("PURPLE-MCP")
    assert len(default_conversation_id) == 20  # "PURPLE-MCP" (10) + random string (10)


async def test_ask_purple_timeout_retry_then_success(
    purple_ai_config: PurpleAIConfig, respx_mock: MockRouter, purple_ai_env: None
) -> None:
    """Test that timeout is retried and eventually succeeds."""
    mock_response = {
        "data": {
            "purpleLaunchQuery": {
                "resultType": "MESSAGE",
                "result": {"message": "Success after retries!"},
                "status": {"error": None},
            }
        }
    }

    # First 2 calls raise timeout, third succeeds
    request_mock = respx_mock.post(purple_ai_config.graphql_url).mock(
        side_effect=[
            httpx.TimeoutException("Timeout"),
            httpx.TimeoutException("Timeout"),
            httpx.Response(200, json=mock_response),
        ]
    )

    result_type, response = await ask_purple(purple_ai_config, "test query")

    # Verify 3 attempts were made (2 failures + 1 success)
    assert request_mock.call_count == 3
    assert result_type == PurpleAIResultType.MESSAGE
    assert response == "Success after retries!"


async def test_ask_purple_network_error_retry_then_success(
    purple_ai_config: PurpleAIConfig, respx_mock: MockRouter, purple_ai_env: None
) -> None:
    """Test that network error is retried and eventually succeeds."""
    mock_response = {
        "data": {
            "purpleLaunchQuery": {
                "resultType": "MESSAGE",
                "result": {"message": "Success after network errors!"},
                "status": {"error": None},
            }
        }
    }

    # First 2 calls raise network error, third succeeds
    request_mock = respx_mock.post(purple_ai_config.graphql_url).mock(
        side_effect=[
            httpx.NetworkError("Network error"),
            httpx.NetworkError("Network error"),
            httpx.Response(200, json=mock_response),
        ]
    )

    result_type, response = await ask_purple(purple_ai_config, "test query")

    # Verify 3 attempts were made (2 failures + 1 success)
    assert request_mock.call_count == 3
    assert result_type == PurpleAIResultType.MESSAGE
    assert response == "Success after network errors!"


def test_sync_ask_purple_no_loop(
    purple_ai_config: PurpleAIConfig, respx_mock: MockRouter, purple_ai_env: None
) -> None:
    """Test sync_ask_purple works when there's no running event loop."""
    mock_response = {
        "data": {
            "purpleLaunchQuery": {
                "resultType": "MESSAGE",
                "result": {"message": "Success without loop!"},
                "status": {"error": None},
            }
        }
    }
    respx_mock.post(purple_ai_config.graphql_url).mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    # This should work fine since there's no running event loop
    response = sync_ask_purple(purple_ai_config, "test query")

    assert response == "Success without loop!"


async def test_sync_ask_purple_with_running_loop(
    purple_ai_config: PurpleAIConfig, respx_mock: MockRouter, purple_ai_env: None
) -> None:
    """Test sync_ask_purple raises error when called from within a running event loop."""
    mock_response = {
        "data": {
            "purpleLaunchQuery": {
                "resultType": "MESSAGE",
                "result": {"message": "This should not be reached"},
                "status": {"error": None},
            }
        }
    }
    respx_mock.post(purple_ai_config.graphql_url).mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    # When called from within an async function (which has a running loop),
    # sync_ask_purple should raise a descriptive error
    with pytest.raises(RuntimeError) as exc_info:
        sync_ask_purple(purple_ai_config, "test query")

    # Verify the error message is descriptive
    error_msg = str(exc_info.value)
    assert "cannot be called from a running event loop" in error_msg
    assert "await ask_purple(config, raw_query)" in error_msg


# Config validation tests
def test_purple_ai_config_graphql_url_requires_https() -> None:
    """Test that graphql_url must use HTTPS protocol."""
    with pytest.raises(ValidationError, match="graphql_url must use HTTPS protocol"):
        PurpleAIConfig(
            graphql_url="http://insecure.example.test/graphql",
            auth_token="TEST_TOKEN",
            user_details=PurpleAIUserDetails(
                session_id=uuid.uuid4().hex,
                email_address="test@example.test",
                user_agent="TestClient/1.0",
                build_date="2025-01-01",
                build_hash="testhash",
            ),
            console_details=PurpleAIConsoleDetails(
                base_url="https://test.example.test",
                version="1.0.0",
            ),
        )


def test_purple_ai_config_graphql_url_strips_whitespace() -> None:
    """Test that graphql_url strips trailing whitespace."""
    config = PurpleAIConfig(
        graphql_url="https://test.example.test/graphql  \n",
        auth_token="TEST_TOKEN",
        user_details=PurpleAIUserDetails(
            session_id=uuid.uuid4().hex,
            email_address="test@example.test",
            user_agent="TestClient/1.0",
            build_date="2025-01-01",
            build_hash="testhash",
        ),
        console_details=PurpleAIConsoleDetails(
            base_url="https://test.example.test",
            version="1.0.0",
        ),
    )
    assert config.graphql_url == "https://test.example.test/graphql"


def test_purple_ai_config_graphql_url_strips_leading_whitespace() -> None:
    """Test that graphql_url strips leading whitespace before validation."""
    config = PurpleAIConfig(
        graphql_url="  \n\thttps://test.example.test/graphql",
        auth_token="TEST_TOKEN",
        user_details=PurpleAIUserDetails(
            session_id=uuid.uuid4().hex,
            email_address="test@example.test",
            user_agent="TestClient/1.0",
            build_date="2025-01-01",
            build_hash="testhash",
        ),
        console_details=PurpleAIConsoleDetails(
            base_url="https://test.example.test",
            version="1.0.0",
        ),
    )
    assert config.graphql_url == "https://test.example.test/graphql"


def test_purple_ai_config_auth_token_cannot_be_empty() -> None:
    """Test that auth_token cannot be empty or whitespace-only."""
    with pytest.raises(ValidationError, match="auth_token cannot be empty"):
        PurpleAIConfig(
            auth_token="   ",
            user_details=PurpleAIUserDetails(
                session_id=uuid.uuid4().hex,
                email_address="test@example.test",
                user_agent="TestClient/1.0",
                build_date="2025-01-01",
                build_hash="testhash",
            ),
            console_details=PurpleAIConsoleDetails(
                base_url="https://test.example.test",
                version="1.0.0",
            ),
        )


def test_purple_ai_config_auth_token_strips_whitespace() -> None:
    """Test that auth_token strips leading/trailing whitespace."""
    config = PurpleAIConfig(
        auth_token="  TEST_TOKEN  ",
        user_details=PurpleAIUserDetails(
            session_id=uuid.uuid4().hex,
            email_address="test@example.test",
            user_agent="TestClient/1.0",
            build_date="2025-01-01",
            build_hash="testhash",
        ),
        console_details=PurpleAIConsoleDetails(
            base_url="https://test.example.test",
            version="1.0.0",
        ),
    )
    assert config.auth_token == "TEST_TOKEN"


def test_purple_ai_config_timeout_must_be_positive() -> None:
    """Test that timeout must be greater than 0."""
    with pytest.raises(ValidationError, match="timeout must be greater than 0"):
        PurpleAIConfig(
            auth_token="TEST_TOKEN",
            timeout=0.0,
            user_details=PurpleAIUserDetails(
                session_id=uuid.uuid4().hex,
                email_address="test@example.test",
                user_agent="TestClient/1.0",
                build_date="2025-01-01",
                build_hash="testhash",
            ),
            console_details=PurpleAIConsoleDetails(
                base_url="https://test.example.test",
                version="1.0.0",
            ),
        )


def test_purple_ai_config_timeout_cannot_be_negative() -> None:
    """Test that timeout cannot be negative."""
    with pytest.raises(ValidationError, match="timeout must be greater than 0"):
        PurpleAIConfig(
            auth_token="TEST_TOKEN",
            timeout=-10.0,
            user_details=PurpleAIUserDetails(
                session_id=uuid.uuid4().hex,
                email_address="test@example.test",
                user_agent="TestClient/1.0",
                build_date="2025-01-01",
                build_hash="testhash",
            ),
            console_details=PurpleAIConsoleDetails(
                base_url="https://test.example.test",
                version="1.0.0",
            ),
        )


def test_purple_ai_config_accepts_valid_timeout() -> None:
    """Test that valid positive timeout values are accepted."""
    config = PurpleAIConfig(
        auth_token="TEST_TOKEN",
        timeout=60.5,
        user_details=PurpleAIUserDetails(
            session_id=uuid.uuid4().hex,
            email_address="test@example.test",
            user_agent="TestClient/1.0",
            build_date="2025-01-01",
            build_hash="testhash",
        ),
        console_details=PurpleAIConsoleDetails(
            base_url="https://test.example.test",
            version="1.0.0",
        ),
    )
    assert config.timeout == 60.5


def test_purple_ai_console_details_base_url_requires_https() -> None:
    """Test that console base_url must use HTTPS protocol."""
    with pytest.raises(ValidationError, match="base_url must use HTTPS protocol"):
        PurpleAIConsoleDetails(
            base_url="http://insecure.example.test",
        )


def test_purple_ai_console_details_accepts_valid_https_url() -> None:
    """Test that console base_url accepts valid HTTPS URLs."""
    console = PurpleAIConsoleDetails(
        base_url="https://secure.example.test",
    )
    assert console.base_url == "https://secure.example.test"


def test_purple_ai_console_details_base_url_strips_leading_whitespace() -> None:
    """Test that console base_url strips leading whitespace before validation."""
    console = PurpleAIConsoleDetails(
        base_url="  \thttps://secure.example.test",
    )
    assert console.base_url == "https://secure.example.test"


def test_random_conv_id_format() -> None:
    """Test that _random_conv_id generates IDs with correct format and length."""
    # Generate multiple IDs to test consistency
    for _ in range(10):
        conv_id = _random_conv_id(10)

        # Check length
        assert len(conv_id) == 10

        # Check all characters are alphanumeric (ASCII letters + digits)
        valid_chars = set(string.ascii_letters + string.digits)
        assert all(c in valid_chars for c in conv_id)


def test_random_conv_id_uniqueness() -> None:
    """Test that _random_conv_id generates unique IDs (high probability with cryptographic randomness)."""
    # Generate many IDs and verify they're all unique
    # With cryptographic randomness, the probability of collision is astronomically low
    num_ids = 1000
    ids = {_random_conv_id(10) for _ in range(num_ids)}

    # All IDs should be unique
    assert len(ids) == num_ids


@pytest.mark.parametrize("scope_field", ["tenant_id", "account_id", "site_id"])
@pytest.mark.parametrize("bad_value", ["", "   ", "\t\n"])
def test_purple_ai_console_details_rejects_empty_scope_id(
    scope_field: str, bad_value: str
) -> None:
    """Empty / whitespace-only scope IDs are rejected at the basemodel layer."""
    kwargs: dict[str, str | None] = {"base_url": "https://example.test"}
    kwargs[scope_field] = bad_value
    with pytest.raises(ValidationError, match=r"scope ID must be a non-empty string"):
        PurpleAIConsoleDetails(**kwargs)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "scope_field,good_value",
    [
        ("tenant_id", "acc-abc-123"),  # non-numeric is fine by design
        ("account_id", "9876543210987654321"),
        ("site_id", "  1111111111111111111  "),  # stripped
    ],
)
def test_purple_ai_console_details_accepts_valid_scope_id(
    scope_field: str, good_value: str
) -> None:
    """Non-empty scope IDs pass validation; whitespace is stripped."""
    kwargs: dict[str, str | None] = {"base_url": "https://example.test"}
    kwargs[scope_field] = good_value
    console = PurpleAIConsoleDetails(**kwargs)  # type: ignore[arg-type]
    assert getattr(console, scope_field) == good_value.strip()


def test_purple_ai_console_details_accepts_none_scope_ids() -> None:
    """All scope IDs default to None when unset."""
    console = PurpleAIConsoleDetails(base_url="https://example.test")
    assert console.console_id is None
    assert console.tenant_id is None
    assert console.account_id is None
    assert console.site_id is None


def test_purple_ai_user_details_user_time_defaults_to_now_local() -> None:
    """user_time defaults to a timezone-aware timestamp at the current local time."""
    before = datetime.now().astimezone()
    user = PurpleAIUserDetails(session_id="abc", user_agent="agent")
    after = datetime.now().astimezone()

    assert user.user_time is not None
    # Timezone-aware (local offset present), not a naive datetime.
    assert user.user_time.tzinfo is not None
    assert user.user_time.utcoffset() is not None
    # Captured at construction time, between the two reference reads.
    assert before <= user.user_time <= after


def test_purple_ai_user_details_user_time_accepts_explicit_value() -> None:
    """An explicit user_time is preserved rather than overwritten by the default."""
    explicit = datetime(2026, 5, 12, 14, 30, 0, tzinfo=timezone(timedelta(hours=-7)))
    user = PurpleAIUserDetails(session_id="abc", user_agent="agent", user_time=explicit)
    assert user.user_time == explicit


def test_purple_ai_user_details_user_time_accepts_none() -> None:
    """user_time may be explicitly suppressed with None."""
    user = PurpleAIUserDetails(session_id="abc", user_agent="agent", user_time=None)
    assert user.user_time is None
