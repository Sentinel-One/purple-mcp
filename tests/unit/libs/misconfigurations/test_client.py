"""Tests for misconfigurations client."""

from string import Template
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from respx import MockRouter

from purple_mcp.libs.misconfigurations.client import MisconfigurationsClient
from purple_mcp.libs.misconfigurations.config import MisconfigurationsConfig
from purple_mcp.libs.misconfigurations.exceptions import (
    MisconfigurationsClientError,
    MisconfigurationsGraphQLError,
    MisconfigurationsSchemaError,
)
from purple_mcp.libs.misconfigurations.models import FilterInput, InFilterStringInput, ViewType
from purple_mcp.type_defs import JsonDict


class TestCheckForSchemaErrors:
    """Test _check_for_schema_errors method."""

    def test_double_quoted_field_name(self) -> None:
        """Test that double-quoted field names are correctly extracted.

        This is the actual format returned by the API.
        """
        errors: list[JsonDict] = [{"message": 'Cannot query field "viewType" on type "Query"'}]

        field_name = MisconfigurationsClient._check_for_schema_errors(errors)

        assert field_name == "viewType"

    def test_single_quoted_field_name(self) -> None:
        """Test that single-quoted field names are correctly extracted."""
        errors: list[JsonDict] = [{"message": "Cannot query field 'viewType' on type 'Query'"}]

        field_name = MisconfigurationsClient._check_for_schema_errors(errors)

        assert field_name == "viewType"

    def test_double_quoted_unknown_argument(self) -> None:
        """Test double-quoted format for unknown argument errors."""
        errors: list[JsonDict] = [
            {"message": 'Unknown argument "viewType" on field "Query.misconfigurations"'}
        ]

        field_name = MisconfigurationsClient._check_for_schema_errors(errors)

        assert field_name == "viewType"

    def test_single_quoted_unknown_argument(self) -> None:
        """Test single-quoted format for unknown argument errors."""
        errors: list[JsonDict] = [
            {"message": "Unknown argument 'viewType' on field 'Query.misconfigurations'"}
        ]

        field_name = MisconfigurationsClient._check_for_schema_errors(errors)

        assert field_name == "viewType"

    def test_no_schema_error(self) -> None:
        """Test that non-schema errors return None."""
        errors: list[JsonDict] = [{"message": "Some other error"}]

        field_name = MisconfigurationsClient._check_for_schema_errors(errors)

        assert field_name is None

    def test_empty_errors_list(self) -> None:
        """Test that empty errors list returns None."""
        errors: list[JsonDict] = []

        field_name = MisconfigurationsClient._check_for_schema_errors(errors)

        assert field_name is None

    def test_schema_error_without_quotes(self) -> None:
        """Test schema error without field name in quotes returns empty string.

        This ensures the fallback mechanism is triggered even when the API
        doesn't quote the field name in the error message.
        """
        errors: list[JsonDict] = [{"message": "Cannot query field on type Query"}]

        field_name = MisconfigurationsClient._check_for_schema_errors(errors)

        # Should return empty string since we detected the schema error
        # but couldn't extract the field name
        assert field_name == ""

    def test_case_insensitive_matching(self) -> None:
        """Test that error matching is case-insensitive."""
        errors: list[JsonDict] = [{"message": 'CANNOT QUERY FIELD "viewType" ON TYPE "Query"'}]

        field_name = MisconfigurationsClient._check_for_schema_errors(errors)

        assert field_name == "viewType"

    def test_mixed_case_error_message(self) -> None:
        """Test error message with mixed case is handled correctly."""
        errors: list[JsonDict] = [{"message": 'Cannot Query Field "viewType" on type "Query"'}]

        field_name = MisconfigurationsClient._check_for_schema_errors(errors)

        assert field_name == "viewType"

    def test_unknown_directive_error(self) -> None:
        """Test 'Unknown directive' error type."""
        errors: list[JsonDict] = [{"message": 'Unknown directive "deprecated"'}]

        field_name = MisconfigurationsClient._check_for_schema_errors(errors)

        assert field_name == "deprecated"

    def test_non_dict_error_ignored(self) -> None:
        """Test that errors with missing message keys are ignored."""
        # Test that the function handles errors without proper structure
        errors: list[JsonDict] = [
            {},  # Empty dict - no message field
            {"message": 'Cannot query field "viewType" on type "Query"'},
        ]

        field_name = MisconfigurationsClient._check_for_schema_errors(errors)

        assert field_name == "viewType"

    def test_error_without_message_key(self) -> None:
        """Test that errors without message key are handled gracefully."""
        errors: list[JsonDict] = [
            {"error": "some error"},
            {"message": 'Cannot query field "viewType" on type "Query"'},
        ]

        field_name = MisconfigurationsClient._check_for_schema_errors(errors)

        assert field_name == "viewType"


class TestSchemaErrorFallback:
    """Test that schema errors trigger the fallback mechanism."""

    @pytest.mark.asyncio
    async def test_unquoted_schema_error_triggers_fallback(self) -> None:
        """Test that unquoted schema errors trigger the fallback mechanism.

        This verifies the complete flow: when the API returns a schema error
        without quotes (e.g. 'Cannot query field viewType on type Query'),
        execute_compatible_query should:
        1. Detect the schema error and raise MisconfigurationsSchemaError
        2. Catch the exception and retry with fallback query
        """
        config = MisconfigurationsConfig(
            graphql_url="https://console.test/graphql",
            auth_token="test-token",
            supports_view_type=True,
        )
        client = MisconfigurationsClient(config)

        query_template = Template(
            """
            query TestQuery($first: Int!$view_type_param) {
                misconfigurations(first: $first$view_type_arg) {
                    edges { node { id } }
                }
            }
            """
        )

        # First call raises schema error without quotes
        schema_error = MisconfigurationsSchemaError(
            "Schema compatibility error in misconfigurations API response",
            field_name="",
            details="Cannot query field viewType on type Query",
        )

        # Second call (fallback) succeeds
        success_response: JsonDict = {"misconfigurations": {"edges": []}}

        with patch.object(
            client, "execute_query", new=AsyncMock(side_effect=[schema_error, success_response])
        ) as mock_execute:
            # Call execute_compatible_query which should handle the fallback
            result = await client.execute_compatible_query(
                query_template, {"first": 10, "viewType": "ALL"}
            )

            # Verify the fallback was triggered
            assert mock_execute.call_count == 2

            # First call should include viewType
            first_call_query = mock_execute.call_args_list[0][0][0]
            assert "$viewType: ViewType" in first_call_query
            assert "viewType: $viewType" in first_call_query

            # Second call should not include viewType
            second_call_query = mock_execute.call_args_list[1][0][0]
            assert "$viewType" not in second_call_query
            assert "viewType:" not in second_call_query

            # Should return the success response
            assert result == {"misconfigurations": {"edges": []}}

    @pytest.mark.asyncio
    async def test_quoted_schema_error_triggers_fallback(self) -> None:
        """Test that quoted schema errors also trigger the fallback mechanism."""
        config = MisconfigurationsConfig(
            graphql_url="https://console.test/graphql",
            auth_token="test-token",
            supports_view_type=True,
        )
        client = MisconfigurationsClient(config)

        query_template = Template(
            """
            query TestQuery($first: Int!$view_type_param) {
                misconfigurations(first: $first$view_type_arg) {
                    edges { node { id } }
                }
            }
            """
        )

        # First call raises schema error with double quotes
        schema_error = MisconfigurationsSchemaError(
            "Schema compatibility error in misconfigurations API response",
            field_name="viewType",
            details='Cannot query field "viewType" on type "Query"',
        )

        # Second call (fallback) succeeds
        success_response: JsonDict = {"misconfigurations": {"edges": []}}

        with patch.object(
            client, "execute_query", new=AsyncMock(side_effect=[schema_error, success_response])
        ) as mock_execute:
            result = await client.execute_compatible_query(
                query_template, {"first": 10, "viewType": "ALL"}
            )

            # Verify the fallback was triggered
            assert mock_execute.call_count == 2

            # Should return the success response
            assert result == {"misconfigurations": {"edges": []}}

    @pytest.mark.asyncio
    async def test_schema_error_disables_view_type_support(self) -> None:
        """Test that schema errors disable supports_view_type flag.

        This prevents repeated failed attempts and log flooding in regions
        that haven't rolled out viewType yet. After the first failure,
        subsequent calls should skip directly to the fallback path.
        """
        config = MisconfigurationsConfig(
            graphql_url="https://console.test/graphql",
            auth_token="test-token",
            supports_view_type=True,
        )
        client = MisconfigurationsClient(config)

        query_template = Template(
            """
            query TestQuery($first: Int!$view_type_param) {
                misconfigurations(first: $first$view_type_arg) {
                    edges { node { id } }
                }
            }
            """
        )

        # First call raises schema error
        schema_error = MisconfigurationsSchemaError(
            "Schema compatibility error in misconfigurations API response",
            field_name="viewType",
            details='Cannot query field "viewType" on type "Query"',
        )

        # Subsequent calls succeed
        success_response: JsonDict = {"misconfigurations": {"edges": []}}

        with patch.object(
            client,
            "execute_query",
            new=AsyncMock(side_effect=[schema_error, success_response, success_response]),
        ) as mock_execute:
            # First call should try with viewType, fail, then retry without it
            result1 = await client.execute_compatible_query(
                query_template, {"first": 10, "viewType": "ALL"}
            )

            # Verify flag was disabled after first failure
            assert config.supports_view_type is False

            # Verify first call made 2 requests (initial + fallback)
            assert mock_execute.call_count == 2

            # Second call should skip directly to fallback (only 1 request)
            result2 = await client.execute_compatible_query(
                query_template, {"first": 10, "viewType": "ALL"}
            )

            # Verify second call only made 1 additional request
            assert mock_execute.call_count == 3

            # Third call should use only the fallback query (no viewType)
            third_call_query = mock_execute.call_args_list[2][0][0]
            assert "$viewType" not in third_call_query
            assert "viewType:" not in third_call_query

            # Both calls should succeed
            assert result1 == {"misconfigurations": {"edges": []}}
            assert result2 == {"misconfigurations": {"edges": []}}


class TestExecuteQuery:
    """Test execute_query method."""

    @pytest.fixture
    def config(self) -> MisconfigurationsConfig:
        """Create test configuration."""
        return MisconfigurationsConfig(
            graphql_url="https://console.test/graphql",
            auth_token="test-token",
        )

    @pytest.mark.asyncio
    async def test_successful_query(
        self, config: MisconfigurationsConfig, respx_mock: MockRouter
    ) -> None:
        """Test successful GraphQL query execution."""
        client = MisconfigurationsClient(config)
        mock_response = {"data": {"misconfiguration": {"id": "test-1"}}}

        respx_mock.post(config.graphql_url).mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        result = await client.execute_query("query { misconfiguration { id } }")

        assert result == {"misconfiguration": {"id": "test-1"}}

    @pytest.mark.asyncio
    async def test_timeout_error(
        self, config: MisconfigurationsConfig, respx_mock: MockRouter
    ) -> None:
        """Test timeout error handling."""
        client = MisconfigurationsClient(config)

        respx_mock.post(config.graphql_url).mock(side_effect=httpx.TimeoutException("Timeout"))

        with pytest.raises(MisconfigurationsClientError) as exc_info:
            await client.execute_query("query { test }")

        assert "timed out" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_network_error(
        self, config: MisconfigurationsConfig, respx_mock: MockRouter
    ) -> None:
        """Test network error handling."""
        client = MisconfigurationsClient(config)

        respx_mock.post(config.graphql_url).mock(side_effect=httpx.RequestError("Network error"))

        with pytest.raises(MisconfigurationsClientError) as exc_info:
            await client.execute_query("query { test }")

        assert "Network error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_http_error(
        self, config: MisconfigurationsConfig, respx_mock: MockRouter
    ) -> None:
        """Test HTTP error handling."""
        client = MisconfigurationsClient(config)

        respx_mock.post(config.graphql_url).mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )

        with pytest.raises(MisconfigurationsClientError) as exc_info:
            await client.execute_query("query { test }")

        assert "HTTP error" in str(exc_info.value)
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_json_parse_error(
        self, config: MisconfigurationsConfig, respx_mock: MockRouter
    ) -> None:
        """Test JSON parsing error handling."""
        client = MisconfigurationsClient(config)

        respx_mock.post(config.graphql_url).mock(
            return_value=httpx.Response(200, content=b"Invalid JSON")
        )

        with pytest.raises(MisconfigurationsClientError) as exc_info:
            await client.execute_query("query { test }")

        assert "Failed to parse JSON" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_graphql_errors(
        self, config: MisconfigurationsConfig, respx_mock: MockRouter
    ) -> None:
        """Test GraphQL error handling."""
        client = MisconfigurationsClient(config)
        mock_response = {
            "errors": [{"message": "Field not found"}],
            "data": None,
        }

        respx_mock.post(config.graphql_url).mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        with pytest.raises(MisconfigurationsGraphQLError) as exc_info:
            await client.execute_query("query { test }")

        assert "GraphQL errors" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_missing_data_field(
        self, config: MisconfigurationsConfig, respx_mock: MockRouter
    ) -> None:
        """Test missing data field in response."""
        client = MisconfigurationsClient(config)
        mock_response: JsonDict = {}

        respx_mock.post(config.graphql_url).mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        with pytest.raises(MisconfigurationsGraphQLError) as exc_info:
            await client.execute_query("query { test }")

        assert "No data field" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_non_dict_data_field(
        self, config: MisconfigurationsConfig, respx_mock: MockRouter
    ) -> None:
        """Test non-dict data field in response."""
        client = MisconfigurationsClient(config)
        mock_response = {"data": "not a dict"}

        respx_mock.post(config.graphql_url).mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        with pytest.raises(MisconfigurationsGraphQLError) as exc_info:
            await client.execute_query("query { test }")

        assert "not a dictionary" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_timeout_retry_then_success(
        self, config: MisconfigurationsConfig, respx_mock: MockRouter
    ) -> None:
        """Test that timeout is retried and eventually succeeds."""
        client = MisconfigurationsClient(config)
        mock_response = {"data": {"misconfiguration": {"id": "test-1"}}}

        # First 2 calls raise timeout, third succeeds
        request_mock = respx_mock.post(config.graphql_url).mock(
            side_effect=[
                httpx.TimeoutException("Timeout"),
                httpx.TimeoutException("Timeout"),
                httpx.Response(200, json=mock_response),
            ]
        )

        result = await client.execute_query("query { misconfiguration { id } }")

        assert result == {"misconfiguration": {"id": "test-1"}}
        assert request_mock.call_count == 3  # Verify 3 attempts were made

    @pytest.mark.asyncio
    async def test_network_error_retry_then_success(
        self, config: MisconfigurationsConfig, respx_mock: MockRouter
    ) -> None:
        """Test that network error is retried and eventually succeeds."""
        client = MisconfigurationsClient(config)
        mock_response = {"data": {"misconfiguration": {"id": "test-1"}}}

        # First 2 calls raise network error, third succeeds
        request_mock = respx_mock.post(config.graphql_url).mock(
            side_effect=[
                httpx.NetworkError("Network error"),
                httpx.NetworkError("Network error"),
                httpx.Response(200, json=mock_response),
            ]
        )

        result = await client.execute_query("query { misconfiguration { id } }")

        assert result == {"misconfiguration": {"id": "test-1"}}
        assert request_mock.call_count == 3  # Verify 3 attempts were made


class TestGetMisconfiguration:
    """Test get_misconfiguration method."""

    @pytest.fixture
    def config(self) -> MisconfigurationsConfig:
        """Create test configuration."""
        return MisconfigurationsConfig(
            graphql_url="https://console.test/graphql",
            auth_token="test-token",
        )

    @pytest.mark.asyncio
    async def test_successful_get(self, config: MisconfigurationsConfig) -> None:
        """Test successful misconfiguration retrieval."""
        client = MisconfigurationsClient(config)
        misconfig_data: JsonDict = {
            "id": "misconfig-123",
            "externalId": "ext-123",
            "name": "Test Misconfiguration",
            "severity": "HIGH",
            "status": "NEW",
            "asset": {
                "id": "asset-1",
                "name": "Asset 1",
                "type": "endpoint",
                "category": "computer",
                "subcategory": "laptop",
            },
            "scope": {"account": {"id": "acc-1", "name": "Account 1"}},
            "scopeLevel": "account",
            "product": "Test Product",
            "vendor": "Test Vendor",
            "detectedAt": "2024-01-01T00:00:00Z",
            "eventTime": "2024-01-01T00:00:00Z",
            "environment": "production",
            "compliance": {"standards": [], "requirements": []},
            "remediation": {"mitigable": False},
            "findingData": {},
        }

        with patch.object(
            client,
            "execute_query",
            new=AsyncMock(return_value={"misconfiguration": misconfig_data}),
        ):
            result = await client.get_misconfiguration("misconfig-123")

        assert result is not None
        assert result.id == "misconfig-123"
        assert result.name == "Test Misconfiguration"

    @pytest.mark.asyncio
    async def test_misconfiguration_not_found(self, config: MisconfigurationsConfig) -> None:
        """Test when misconfiguration is not found."""
        client = MisconfigurationsClient(config)

        with patch.object(
            client, "execute_query", new=AsyncMock(return_value={"misconfiguration": None})
        ):
            result = await client.get_misconfiguration("nonexistent")

        assert result is None


class TestListMisconfigurations:
    """Test list_misconfigurations method."""

    @pytest.fixture
    def config(self) -> MisconfigurationsConfig:
        """Create test configuration."""
        return MisconfigurationsConfig(
            graphql_url="https://console.test/graphql",
            auth_token="test-token",
        )

    @pytest.mark.asyncio
    async def test_successful_list(self, config: MisconfigurationsConfig) -> None:
        """Test successful misconfigurations listing."""
        client = MisconfigurationsClient(config)
        response_data: JsonDict = {
            "misconfigurations": {
                "edges": [
                    {
                        "node": {
                            "id": "misconfig-1",
                            "externalId": "ext-1",
                            "name": "Misconfig 1",
                            "severity": "HIGH",
                            "status": "NEW",
                            "asset": {
                                "id": "asset-1",
                                "name": "Asset 1",
                                "type": "endpoint",
                                "category": "computer",
                                "subcategory": "laptop",
                            },
                            "scope": {"account": {"id": "acc-1", "name": "Account 1"}},
                            "scopeLevel": "account",
                            "product": "Test",
                            "vendor": "Test",
                            "detectedAt": "2024-01-01T00:00:00Z",
                            "eventTime": "2024-01-01T00:00:00Z",
                            "environment": "prod",
                            "compliance": {"standards": [], "requirements": []},
                            "remediation": {"mitigable": False},
                            "findingData": {},
                        },
                        "cursor": "cursor1",
                    }
                ],
                "pageInfo": {
                    "hasNextPage": False,
                    "hasPreviousPage": False,
                    "startCursor": None,
                    "endCursor": None,
                },
            }
        }

        with patch.object(
            client, "execute_compatible_query", new=AsyncMock(return_value=response_data)
        ):
            result = await client.list_misconfigurations(first=10)

        assert len(result.edges) == 1
        assert result.edges[0].node.id == "misconfig-1"

    @pytest.mark.asyncio
    async def test_list_with_view_type(self, config: MisconfigurationsConfig) -> None:
        """Test listing with view type filter."""
        config.supports_view_type = True
        client = MisconfigurationsClient(config)
        response_data: JsonDict = {
            "misconfigurations": {
                "edges": [],
                "pageInfo": {
                    "hasNextPage": False,
                    "hasPreviousPage": False,
                    "startCursor": None,
                    "endCursor": None,
                },
            }
        }

        with patch.object(
            client, "execute_compatible_query", new=AsyncMock(return_value=response_data)
        ) as mock_execute:
            await client.list_misconfigurations(first=10, view_type=ViewType.ALL)

            # Verify viewType was passed
            call_args = mock_execute.call_args
            assert call_args[0][1]["viewType"] == "ALL"

    @pytest.mark.asyncio
    async def test_list_empty_response(self, config: MisconfigurationsConfig) -> None:
        """Test listing when no misconfigurations returned."""
        client = MisconfigurationsClient(config)

        with patch.object(client, "execute_compatible_query", new=AsyncMock(return_value={})):
            result = await client.list_misconfigurations()

        assert len(result.edges) == 0
        assert result.page_info.has_next_page is False


class TestSearchMisconfigurations:
    """Test search_misconfigurations method."""

    @pytest.fixture
    def config(self) -> MisconfigurationsConfig:
        """Create test configuration."""
        return MisconfigurationsConfig(
            graphql_url="https://console.test/graphql",
            auth_token="test-token",
        )

    @pytest.mark.asyncio
    async def test_successful_search(self, config: MisconfigurationsConfig) -> None:
        """Test successful misconfiguration search."""
        client = MisconfigurationsClient(config)
        response_data: JsonDict = {
            "misconfigurations": {
                "edges": [
                    {
                        "node": {
                            "id": "misconfig-1",
                            "externalId": "ext-1",
                            "name": "Critical Misconfig",
                            "severity": "CRITICAL",
                            "status": "NEW",
                            "asset": {
                                "id": "asset-1",
                                "name": "Asset 1",
                                "type": "endpoint",
                                "category": "computer",
                                "subcategory": "laptop",
                            },
                            "scope": {"account": {"id": "acc-1", "name": "Account 1"}},
                            "scopeLevel": "account",
                            "product": "Test",
                            "vendor": "Test",
                            "detectedAt": "2024-01-01T00:00:00Z",
                            "eventTime": "2024-01-01T00:00:00Z",
                            "environment": "prod",
                            "compliance": {"standards": [], "requirements": []},
                            "remediation": {"mitigable": False},
                            "findingData": {},
                        },
                        "cursor": "cursor1",
                    }
                ],
                "pageInfo": {
                    "hasNextPage": False,
                    "hasPreviousPage": False,
                    "startCursor": None,
                    "endCursor": None,
                },
            }
        }

        filters = [
            FilterInput(fieldId="severity", stringIn=InFilterStringInput(values=["CRITICAL"]))
        ]

        with patch.object(
            client, "execute_compatible_query", new=AsyncMock(return_value=response_data)
        ) as mock_execute:
            result = await client.search_misconfigurations(filters=filters, first=10)

            # Verify filters were serialized
            call_args = mock_execute.call_args
            assert "filters" in call_args[0][1]

        assert len(result.edges) == 1
        assert result.edges[0].node.severity == "CRITICAL"

    @pytest.mark.asyncio
    async def test_search_without_filters(self, config: MisconfigurationsConfig) -> None:
        """Test search without filters."""
        client = MisconfigurationsClient(config)
        response_data: JsonDict = {
            "misconfigurations": {
                "edges": [],
                "pageInfo": {
                    "hasNextPage": False,
                    "hasPreviousPage": False,
                    "startCursor": None,
                    "endCursor": None,
                },
            }
        }

        with patch.object(
            client, "execute_compatible_query", new=AsyncMock(return_value=response_data)
        ):
            result = await client.search_misconfigurations(first=10)

        assert len(result.edges) == 0


class TestGetMisconfigurationNotes:
    """Test get_misconfiguration_notes method."""

    @pytest.fixture
    def config(self) -> MisconfigurationsConfig:
        """Create test configuration."""
        return MisconfigurationsConfig(
            graphql_url="https://console.test/graphql",
            auth_token="test-token",
        )

    @pytest.mark.asyncio
    async def test_successful_get_notes(self, config: MisconfigurationsConfig) -> None:
        """Test successful notes retrieval."""
        client = MisconfigurationsClient(config)
        response_data: JsonDict = {
            "misconfigurationNotes": {
                "edges": [
                    {
                        "node": {
                            "id": "note-1",
                            "misconfigurationId": "misconfig-123",
                            "text": "Test note",
                            "author": {
                                "id": "user-1",
                                "email": "test@test.test",
                                "fullName": "Test User",
                            },
                            "createdAt": "2024-01-01T00:00:00Z",
                        },
                        "cursor": "cursor1",
                    }
                ],
                "pageInfo": {
                    "hasNextPage": False,
                    "hasPreviousPage": False,
                    "startCursor": None,
                    "endCursor": None,
                },
            }
        }

        with patch.object(client, "execute_query", new=AsyncMock(return_value=response_data)):
            result = await client.get_misconfiguration_notes("misconfig-123")

        assert len(result.edges) == 1
        assert result.edges[0].node.text == "Test note"

    @pytest.mark.asyncio
    async def test_get_notes_empty(self, config: MisconfigurationsConfig) -> None:
        """Test getting notes when none exist."""
        client = MisconfigurationsClient(config)

        with patch.object(client, "execute_query", new=AsyncMock(return_value={})):
            result = await client.get_misconfiguration_notes("misconfig-123")

        assert len(result.edges) == 0


class TestGetMisconfigurationHistory:
    """Test get_misconfiguration_history method."""

    @pytest.fixture
    def config(self) -> MisconfigurationsConfig:
        """Create test configuration."""
        return MisconfigurationsConfig(
            graphql_url="https://console.test/graphql",
            auth_token="test-token",
        )

    @pytest.mark.asyncio
    async def test_successful_get_history(self, config: MisconfigurationsConfig) -> None:
        """Test successful history retrieval."""
        client = MisconfigurationsClient(config)
        response_data: JsonDict = {
            "misconfigurationHistory": {
                "edges": [
                    {
                        "node": {
                            "eventType": "STATUS",
                            "eventText": "Status changed",
                            "createdAt": "2024-01-01T00:00:00Z",
                        },
                        "cursor": "cursor1",
                    }
                ],
                "pageInfo": {
                    "hasNextPage": True,
                    "hasPreviousPage": False,
                    "startCursor": "cursor1",
                    "endCursor": "cursor2",
                },
            }
        }

        with patch.object(client, "execute_query", new=AsyncMock(return_value=response_data)):
            result = await client.get_misconfiguration_history("misconfig-123", first=5)

        assert len(result.edges) == 1
        assert result.edges[0].node.event_type == "STATUS"
        assert result.page_info.has_next_page is True

    @pytest.mark.asyncio
    async def test_get_history_with_pagination(self, config: MisconfigurationsConfig) -> None:
        """Test getting history with pagination."""
        client = MisconfigurationsClient(config)
        response_data: JsonDict = {
            "misconfigurationHistory": {
                "edges": [],
                "pageInfo": {
                    "hasNextPage": False,
                    "hasPreviousPage": True,
                    "startCursor": None,
                    "endCursor": None,
                },
            }
        }

        with patch.object(
            client, "execute_query", new=AsyncMock(return_value=response_data)
        ) as mock_execute:
            result = await client.get_misconfiguration_history(
                "misconfig-123", first=10, after="cursor1"
            )

            # Verify pagination parameters
            call_args = mock_execute.call_args
            assert call_args[0][1]["first"] == 10
            assert call_args[0][1]["after"] == "cursor1"

        assert result.page_info.has_previous_page is True
