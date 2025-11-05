"""Unit tests for Purple AI GraphQL request builder.

This test suite verifies that the _build_graphql_request function properly
escapes special characters to prevent GraphQL injection vulnerabilities.
"""

import json

from purple_mcp.libs.purple_ai.client import _build_graphql_request


def test_build_graphql_request_with_quotes() -> None:
    """Test that double quotes in values are properly escaped."""
    query = _build_graphql_request(
        start_time=1000,
        end_time=2000,
        base_url="https://example.test",
        version="1.0.0",
        account_id="TEST_ACCOUNT",
        team_token="TEST_TEAM",
        email_address='test"user@example.test',  # Contains quote
        user_agent="TestAgent/1.0",
        build_date="2025-01-01",
        build_hash="abc123",
        conversation_id="CONV123",
    )

    # Verify the email address with quote is properly escaped
    # json.dumps will escape it as \"
    assert r'"test\"user@example.test"' in query or '"test\\"user@example.test"' in query

    # Verify the query is valid GraphQL by checking structure
    assert "query SimpleTestQuery($input: String!)" in query
    assert "purpleLaunchQuery" in query
    assert "emailAddress:" in query


def test_build_graphql_request_with_backslashes() -> None:
    """Test that backslashes in values are properly escaped."""
    query = _build_graphql_request(
        start_time=1000,
        end_time=2000,
        base_url="https://example.test",
        version="1.0.0",
        account_id="TEST_ACCOUNT",
        team_token="TEST_TEAM",
        email_address="test@example.test",
        user_agent="Test\\Agent\\1.0",  # Contains backslashes
        build_date="2025-01-01",
        build_hash="abc123",
        conversation_id="CONV123",
    )

    # Verify the user agent with backslashes is properly escaped
    # json.dumps will escape backslashes as \\
    assert r'"Test\\Agent\\1.0"' in query or '"Test\\\\Agent\\\\1.0"' in query

    # Verify the query is valid GraphQL by checking structure
    assert "query SimpleTestQuery($input: String!)" in query
    assert "userAgent:" in query


def test_build_graphql_request_with_unicode() -> None:
    """Test that Unicode characters are properly handled."""
    query = _build_graphql_request(
        start_time=1000,
        end_time=2000,
        base_url="https://example.test",
        version="1.0.0",
        account_id="TEST_ACCOUNT",
        team_token="TEST_TEAM",
        email_address="user@例え.test",  # Contains Unicode
        user_agent="TestAgent/1.0",
        build_date="2025-01-01",
        build_hash="abc123",
        conversation_id="CONV123",
    )

    # Verify Unicode is preserved (json.dumps handles this correctly)
    # The Unicode characters should be in the query
    assert "user@例え.test" in query or "\\u" in query  # May be escaped or not

    # Verify the query is valid GraphQL by checking structure
    assert "query SimpleTestQuery($input: String!)" in query
    assert "emailAddress:" in query


def test_build_graphql_request_with_newlines() -> None:
    """Test that newline characters are properly escaped."""
    query = _build_graphql_request(
        start_time=1000,
        end_time=2000,
        base_url="https://example.test",
        version="1.0.0",
        account_id="TEST_ACCOUNT",
        team_token="TEST_TEAM",
        email_address="test@example.test",
        user_agent="TestAgent/1.0",
        build_date="2025-01-01",
        build_hash="hash\nwith\nnewlines",  # Contains newlines
        conversation_id="CONV123",
    )

    # Verify newlines are escaped
    assert r"\n" in query

    # Verify the query is valid GraphQL by checking structure
    assert "query SimpleTestQuery($input: String!)" in query
    assert "buildHash:" in query


def test_build_graphql_request_with_single_quotes() -> None:
    """Test that single quotes are handled correctly (no escaping needed for GraphQL strings)."""
    query = _build_graphql_request(
        start_time=1000,
        end_time=2000,
        base_url="https://example.test",
        version="1.0.0",
        account_id="TEST_ACCOUNT",
        team_token="TEST_TEAM",
        email_address="test'user@example.test",  # Contains single quote
        user_agent="TestAgent/1.0",
        build_date="2025-01-01",
        build_hash="abc123",
        conversation_id="CONV123",
    )

    # Single quotes don't need escaping in double-quoted strings
    assert "test'user@example.test" in query

    # Verify the query is valid GraphQL by checking structure
    assert "query SimpleTestQuery($input: String!)" in query
    assert "emailAddress:" in query


def test_build_graphql_request_valid_graphql_structure() -> None:
    """Test that the generated query has valid GraphQL structure."""
    query = _build_graphql_request(
        start_time=1000,
        end_time=2000,
        base_url="https://example.test",
        version="1.0.0",
        account_id="TEST_ACCOUNT",
        team_token="TEST_TEAM",
        email_address="test@example.test",
        user_agent="TestAgent/1.0",
        build_date="2025-01-01",
        build_hash="abc123",
        conversation_id="CONV123",
    )

    # Check for key GraphQL elements
    assert "query SimpleTestQuery($input: String!)" in query
    assert "purpleLaunchQuery" in query
    assert "request:" in query
    assert "consoleDetails:" in query
    assert "userDetails:" in query
    assert "inputContent:" in query

    # Check that all fields are present
    assert "baseUrl:" in query
    assert "version:" in query
    assert "accountId:" in query
    assert "teamToken:" in query
    assert "emailAddress:" in query
    assert "userAgent:" in query
    assert "buildDate:" in query
    assert "buildHash:" in query
    assert "conversation:" in query

    # Check for the variable placeholder (should not be escaped)
    assert "$input" in query
    assert "userInput: $input" in query


def test_build_graphql_request_numeric_values() -> None:
    """Test that numeric values (timestamps) are not quoted."""
    query = _build_graphql_request(
        start_time=1234567890123,
        end_time=1234567899999,
        base_url="https://example.test",
        version="1.0.0",
        account_id="TEST_ACCOUNT",
        team_token="TEST_TEAM",
        email_address="test@example.test",
        user_agent="TestAgent/1.0",
        build_date="2025-01-01",
        build_hash="abc123",
        conversation_id="CONV123",
    )

    # Numeric values should appear without quotes in GraphQL
    assert "start: 1234567890123" in query
    assert "end: 1234567899999" in query

    # But string values should have quotes
    assert '"https://example.test"' in query
    assert '"1.0.0"' in query


def test_build_graphql_request_with_all_special_chars() -> None:
    """Test handling of multiple special characters in a single value."""
    email_with_specials = 'test"\\user\n@example.test'

    query = _build_graphql_request(
        start_time=1000,
        end_time=2000,
        base_url="https://example.test",
        version="1.0.0",
        account_id="TEST_ACCOUNT",
        team_token="TEST_TEAM",
        email_address=email_with_specials,
        user_agent="TestAgent/1.0",
        build_date="2025-01-01",
        build_hash="abc123",
        conversation_id="CONV123",
    )

    # Verify all special characters are escaped
    # json.dumps should produce: "test\"\\user\n@example.test"
    escaped_email = json.dumps(email_with_specials)
    assert escaped_email in query

    # Verify the query structure is intact
    assert "query SimpleTestQuery($input: String!)" in query
    assert "emailAddress:" in query


def test_build_graphql_request_empty_strings() -> None:
    """Test handling of empty string values."""
    query = _build_graphql_request(
        start_time=1000,
        end_time=2000,
        base_url="https://example.test",
        version="1.0.0",
        account_id="TEST_ACCOUNT",
        team_token="TEST_TEAM",
        email_address="",  # Empty string
        user_agent="",  # Empty string
        build_date="",  # Empty string
        build_hash="",  # Empty string
        conversation_id="CONV123",
    )

    # Empty strings should appear as ""
    assert 'emailAddress: ""' in query
    assert 'userAgent: ""' in query
    assert 'buildDate: ""' in query
    assert 'buildHash: ""' in query

    # Verify the query structure is intact
    assert "query SimpleTestQuery($input: String!)" in query


def test_build_graphql_request_no_injection_via_closing_braces() -> None:
    """Test that closing braces in values don't break GraphQL structure."""
    # Attempt to inject GraphQL by using closing braces
    malicious_value = "test } } query { malicious"

    query = _build_graphql_request(
        start_time=1000,
        end_time=2000,
        base_url="https://example.test",
        version="1.0.0",
        account_id="TEST_ACCOUNT",
        team_token="TEST_TEAM",
        email_address="test@example.test",
        user_agent=malicious_value,
        build_date="2025-01-01",
        build_hash="abc123",
        conversation_id="CONV123",
    )

    # The value should be safely escaped within quotes
    assert json.dumps(malicious_value) in query

    # Verify there's no injection - should only have one query definition
    assert query.count("query SimpleTestQuery") == 1

    # Verify structure integrity
    assert "purpleLaunchQuery" in query

    # Verify the malicious content is safely contained within the string value
    # and not parsed as GraphQL structure
    assert '"test } } query { malicious"' in query


def test_build_graphql_request_returns_string() -> None:
    """Test that the function returns a string."""
    result = _build_graphql_request(
        start_time=1000,
        end_time=2000,
        base_url="https://example.test",
        version="1.0.0",
        account_id="TEST_ACCOUNT",
        team_token="TEST_TEAM",
        email_address="test@example.test",
        user_agent="TestAgent/1.0",
        build_date="2025-01-01",
        build_hash="abc123",
        conversation_id="CONV123",
    )

    assert isinstance(result, str)
    assert len(result) > 0
