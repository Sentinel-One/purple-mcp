"""Unit tests for alerts client."""

from string import Template
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from respx import MockRouter

from purple_mcp.libs.alerts.client import AlertsClient
from purple_mcp.libs.alerts.config import AlertsConfig
from purple_mcp.libs.alerts.exceptions import AlertsClientError, AlertsGraphQLError
from purple_mcp.libs.alerts.models import FilterInput, InFilterStringInput, ViewType
from purple_mcp.type_defs import JsonDict


class TestExecuteQuery:
    """Test execute_query method."""

    @pytest.fixture
    def config(self) -> AlertsConfig:
        """Create test configuration."""
        return AlertsConfig(
            graphql_url="https://console.test/graphql",
            auth_token="test-token",
        )

    @pytest.mark.asyncio
    async def test_successful_query(self, config: AlertsConfig, respx_mock: MockRouter) -> None:
        """Test successful GraphQL query execution."""
        client = AlertsClient(config)
        mock_response = {"data": {"alert": {"id": "test-1"}}}

        respx_mock.post(config.graphql_url).mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        result = await client.execute_query("query { alert { id } }")

        assert result == {"alert": {"id": "test-1"}}

    @pytest.mark.asyncio
    async def test_timeout_error(self, config: AlertsConfig, respx_mock: MockRouter) -> None:
        """Test timeout error handling."""
        client = AlertsClient(config)

        respx_mock.post(config.graphql_url).mock(side_effect=httpx.TimeoutException("Timeout"))

        with pytest.raises(AlertsClientError) as exc_info:
            await client.execute_query("query { test }")

        assert "timed out" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_network_error(self, config: AlertsConfig, respx_mock: MockRouter) -> None:
        """Test network error handling."""
        client = AlertsClient(config)

        respx_mock.post(config.graphql_url).mock(side_effect=httpx.RequestError("Network error"))

        with pytest.raises(AlertsClientError) as exc_info:
            await client.execute_query("query { test }")

        assert "Network error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_http_error(self, config: AlertsConfig, respx_mock: MockRouter) -> None:
        """Test HTTP error handling."""
        client = AlertsClient(config)

        respx_mock.post(config.graphql_url).mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )

        with pytest.raises(AlertsClientError) as exc_info:
            await client.execute_query("query { test }")

        assert "HTTP error" in str(exc_info.value)
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_json_parse_error(self, config: AlertsConfig, respx_mock: MockRouter) -> None:
        """Test JSON parsing error handling."""
        client = AlertsClient(config)

        respx_mock.post(config.graphql_url).mock(
            return_value=httpx.Response(200, content=b"Invalid JSON")
        )

        with pytest.raises(AlertsClientError) as exc_info:
            await client.execute_query("query { test }")

        assert "Failed to parse JSON" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_graphql_errors(self, config: AlertsConfig, respx_mock: MockRouter) -> None:
        """Test GraphQL error handling."""
        client = AlertsClient(config)
        mock_response = {
            "errors": [{"message": "Field not found"}],
            "data": None,
        }

        respx_mock.post(config.graphql_url).mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        with pytest.raises(AlertsGraphQLError) as exc_info:
            await client.execute_query("query { test }")

        assert "GraphQL errors" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_missing_data_field(self, config: AlertsConfig, respx_mock: MockRouter) -> None:
        """Test missing data field in response."""
        client = AlertsClient(config)
        mock_response: JsonDict = {}

        respx_mock.post(config.graphql_url).mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        with pytest.raises(AlertsGraphQLError) as exc_info:
            await client.execute_query("query { test }")

        assert "No data field" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_timeout_retry_then_success(
        self, config: AlertsConfig, respx_mock: MockRouter
    ) -> None:
        """Test that timeout is retried and eventually succeeds."""
        client = AlertsClient(config)
        mock_response = {"data": {"alert": {"id": "test-1"}}}

        # First 2 calls raise timeout, third succeeds
        request_mock = respx_mock.post(config.graphql_url).mock(
            side_effect=[
                httpx.TimeoutException("Timeout"),
                httpx.TimeoutException("Timeout"),
                httpx.Response(200, json=mock_response),
            ]
        )

        result = await client.execute_query("query { alert { id } }")

        assert result == {"alert": {"id": "test-1"}}
        assert request_mock.call_count == 3  # Verify 3 attempts were made

    @pytest.mark.asyncio
    async def test_network_error_retry_then_success(
        self, config: AlertsConfig, respx_mock: MockRouter
    ) -> None:
        """Test that network error is retried and eventually succeeds."""
        client = AlertsClient(config)
        mock_response = {"data": {"alert": {"id": "test-1"}}}

        # First 2 calls raise network error, third succeeds
        request_mock = respx_mock.post(config.graphql_url).mock(
            side_effect=[
                httpx.NetworkError("Network error"),
                httpx.NetworkError("Network error"),
                httpx.Response(200, json=mock_response),
            ]
        )

        result = await client.execute_query("query { alert { id } }")

        assert result == {"alert": {"id": "test-1"}}
        assert request_mock.call_count == 3  # Verify 3 attempts were made


class TestSchemaCompatibility:
    """Test schema compatibility features."""

    @pytest.fixture
    def config(self) -> AlertsConfig:
        """Create test configuration."""
        return AlertsConfig(
            graphql_url="https://console.test/graphql",
            auth_token="test-token",
            supports_data_sources=True,
            supports_view_type=True,
        )

    def test_is_schema_error(self, config: AlertsConfig) -> None:
        """Test schema error detection."""
        client = AlertsClient(config)

        # Test various schema error messages
        error1 = AlertsGraphQLError("Cannot query field 'dataSources' on type 'Alert'")
        assert client._is_schema_error(error1)

        error2 = AlertsGraphQLError("Unknown argument 'viewType' on field")
        assert client._is_schema_error(error2)

        error3 = AlertsGraphQLError("Field does not exist")
        assert client._is_schema_error(error3)

        # Test non-schema error
        error4 = AlertsGraphQLError("Some other error")
        assert not client._is_schema_error(error4)

    @pytest.mark.asyncio
    async def test_non_schema_graphql_error_not_caught(self, config: AlertsConfig) -> None:
        """Test that non-schema GraphQL errors are not caught by fallback logic.

        The schema compatibility logic should only fall back to a simpler query
        when it detects a schema-related error. Other GraphQL errors (like
        permission denied, invalid ID format, etc.) should be raised directly
        without triggering the fallback mechanism.
        """
        client = AlertsClient(config)

        # Create a non-schema GraphQL error
        non_schema_error = AlertsGraphQLError("Permission Denied")

        query_template = Template(
            """
            query GetAlert($id: ID!) {
                alert(id: $id) {
                    ${data_sources_field}
                    id
                    name
                }
            }
            """
        )
        variables: JsonDict = {"id": "alert-123"}

        # Mock execute_query to raise a non-schema GraphQL error
        with (
            patch.object(
                client, "execute_query", new=AsyncMock(side_effect=non_schema_error)
            ) as mock_execute,
            patch.object(client, "_execute_fallback_query", new=AsyncMock()) as mock_fallback,
        ):
            # Attempt to execute the query and expect the original error
            with pytest.raises(AlertsGraphQLError) as exc_info:
                await client.execute_compatible_query(query_template, variables, {})

            # Verify the original error is raised
            assert "Permission Denied" in str(exc_info.value)
            assert not client._is_schema_error(exc_info.value)

            # Verify the fallback method was never called
            mock_fallback.assert_not_called()

            # Verify execute_query was called once
            assert mock_execute.call_count == 1

    @pytest.mark.asyncio
    async def test_non_schema_error_types(self, config: AlertsConfig) -> None:
        """Test various non-schema error types are not caught by fallback.

        This test ensures that legitimate application-level errors from the API
        are not accidentally swallowed by the compatibility logic.
        """
        client = AlertsClient(config)

        query_template = Template(
            """
            query TestQuery {
                alerts {
                    ${data_sources_field}
                    id
                }
            }
            """
        )

        # Test various non-schema error messages
        non_schema_errors = [
            "Permission Denied",
            "Invalid alert ID format",
            "Authentication failed",
            "Rate limit exceeded",
            "Internal server error",
            "Forbidden",
        ]

        for error_message in non_schema_errors:
            error = AlertsGraphQLError(error_message)

            with (
                patch.object(client, "execute_query", new=AsyncMock(side_effect=error)),
                patch.object(client, "_execute_fallback_query", new=AsyncMock()) as mock_fallback,
            ):
                with pytest.raises(AlertsGraphQLError) as exc_info:
                    await client.execute_compatible_query(query_template, {}, {})

                # Verify the original error is raised
                assert error_message in str(exc_info.value)

                # Verify fallback was never called for non-schema errors
                mock_fallback.assert_not_called()

    @pytest.mark.asyncio
    async def test_fallback_query_execution(self, config: AlertsConfig) -> None:
        """Test fallback query execution removes optional fields."""
        client = AlertsClient(config)
        query_template = Template(
            """
            query Test($viewType: ViewType) {
                alerts(viewType: $viewType) {
                    ${data_sources_field}
                    id
                }
            }
            """
        )

        variables: JsonDict = {"viewType": "ALL"}

        with patch.object(
            client, "execute_query", new=AsyncMock(return_value={"alerts": []})
        ) as mock_execute:
            await client._execute_fallback_query(query_template, variables, {})

            # Verify viewType was removed from variables
            call_args = mock_execute.call_args
            assert "viewType" not in call_args[0][1]

    def test_query_syntax_with_view_type_disabled(self, config: AlertsConfig) -> None:
        """Test that generated queries are syntactically valid when view_type is disabled.

        This verifies the fix for issue #151: when supports_view_type is False,
        the query should not have a trailing comma in the parameter list.
        """
        from purple_mcp.libs.alerts.client import (
            LIST_ALERTS_QUERY_TEMPLATE,
            SEARCH_ALERTS_QUERY_TEMPLATE,
        )

        config.supports_view_type = False
        config.supports_data_sources = False

        # Test LIST_ALERTS query
        list_params = {
            "data_sources_field": "",
            "view_type_param": "",
            "view_type_arg": "",
        }
        list_query = LIST_ALERTS_QUERY_TEMPLATE.safe_substitute(**list_params)

        # Verify the query doesn't have syntax errors like trailing commas
        # The parameter list should be: ($first: Int!, $after: String)
        # NOT: ($first: Int!, $after: String, )
        assert "($first: Int!, $after: String)" in list_query
        assert ", )" not in list_query

        # Test SEARCH_ALERTS query
        search_query = SEARCH_ALERTS_QUERY_TEMPLATE.safe_substitute(**list_params)

        # Verify the query doesn't have syntax errors
        # The parameter list should be: ($filters: [FilterInput!], $first: Int!, $after: String)
        # NOT: ($filters: [FilterInput!], $first: Int!, $after: String, )
        assert "($filters: [FilterInput!], $first: Int!, $after: String)" in search_query
        assert ", )" not in search_query

    def test_query_syntax_with_view_type_enabled(self, config: AlertsConfig) -> None:
        """Test that generated queries include view_type when enabled.

        This verifies that when supports_view_type is True, the comma is correctly
        included in the substitution value.
        """
        from purple_mcp.libs.alerts.client import (
            LIST_ALERTS_QUERY_TEMPLATE,
            SEARCH_ALERTS_QUERY_TEMPLATE,
        )

        config.supports_view_type = True
        config.supports_data_sources = False

        # Test LIST_ALERTS query
        list_params = {
            "data_sources_field": "",
            "view_type_param": ", $viewType: ViewType",
            "view_type_arg": ", viewType: $viewType",
        }
        list_query = LIST_ALERTS_QUERY_TEMPLATE.safe_substitute(**list_params)

        # Verify the query includes viewType parameter with comma
        assert "($first: Int!, $after: String, $viewType: ViewType)" in list_query
        assert "alerts(first: $first, after: $after, viewType: $viewType)" in list_query

        # Test SEARCH_ALERTS query
        search_query = SEARCH_ALERTS_QUERY_TEMPLATE.safe_substitute(**list_params)

        # Verify the query includes viewType parameter with comma
        assert (
            "($filters: [FilterInput!], $first: Int!, $after: String, $viewType: ViewType)"
            in search_query
        )
        assert (
            "alerts(filters: $filters, first: $first, after: $after, viewType: $viewType)"
            in search_query
        )


class TestGetAlert:
    """Test get_alert method."""

    @pytest.fixture
    def config(self) -> AlertsConfig:
        """Create test configuration."""
        return AlertsConfig(
            graphql_url="https://console.test/graphql",
            auth_token="test-token",
        )

    @pytest.mark.asyncio
    async def test_successful_get(self, config: AlertsConfig) -> None:
        """Test successful alert retrieval."""
        client = AlertsClient(config)
        alert_data: JsonDict = {
            "id": "alert-123",
            "name": "Test Alert",
            "severity": "HIGH",
            "status": "NEW",
            "detectedAt": "2024-01-01T00:00:00Z",
        }

        with patch.object(
            client, "execute_compatible_query", new=AsyncMock(return_value={"alert": alert_data})
        ):
            result = await client.get_alert("alert-123")

        assert result is not None
        assert result.id == "alert-123"
        assert result.name == "Test Alert"

    @pytest.mark.asyncio
    async def test_alert_not_found(self, config: AlertsConfig) -> None:
        """Test when alert is not found."""
        client = AlertsClient(config)

        with patch.object(
            client, "execute_compatible_query", new=AsyncMock(return_value={"alert": None})
        ):
            result = await client.get_alert("nonexistent")

        assert result is None


class TestListAlerts:
    """Test list_alerts method."""

    @pytest.fixture
    def config(self) -> AlertsConfig:
        """Create test configuration."""
        return AlertsConfig(
            graphql_url="https://console.test/graphql",
            auth_token="test-token",
        )

    @pytest.mark.asyncio
    async def test_successful_list(self, config: AlertsConfig) -> None:
        """Test successful alerts listing."""
        client = AlertsClient(config)
        response_data: JsonDict = {
            "alerts": {
                "edges": [
                    {
                        "node": {
                            "id": "alert-1",
                            "name": "Alert 1",
                            "severity": "HIGH",
                            "status": "NEW",
                            "detectedAt": "2024-01-01T00:00:00Z",
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
                "totalCount": 1,
            }
        }

        with patch.object(
            client, "execute_compatible_query", new=AsyncMock(return_value=response_data)
        ):
            result = await client.list_alerts(first=10)

        assert len(result.edges) == 1
        assert result.edges[0].node.id == "alert-1"
        assert result.total_count == 1

    @pytest.mark.asyncio
    async def test_list_with_view_type(self, config: AlertsConfig) -> None:
        """Test listing with view type filter."""
        config.supports_view_type = True
        client = AlertsClient(config)
        response_data: JsonDict = {
            "alerts": {
                "edges": [],
                "pageInfo": {
                    "hasNextPage": False,
                    "hasPreviousPage": False,
                    "startCursor": None,
                    "endCursor": None,
                },
                "totalCount": 0,
            }
        }

        with patch.object(
            client, "execute_compatible_query", new=AsyncMock(return_value=response_data)
        ) as mock_execute:
            await client.list_alerts(first=10, view_type=ViewType.ASSIGNED_TO_ME)

            # Verify viewType was passed
            call_args = mock_execute.call_args
            assert call_args[0][1]["viewType"] == "ASSIGNED_TO_ME"


class TestSearchAlerts:
    """Test search_alerts method."""

    @pytest.fixture
    def config(self) -> AlertsConfig:
        """Create test configuration."""
        return AlertsConfig(
            graphql_url="https://console.test/graphql",
            auth_token="test-token",
        )

    @pytest.mark.asyncio
    async def test_successful_search(self, config: AlertsConfig) -> None:
        """Test successful alert search."""
        client = AlertsClient(config)
        response_data: JsonDict = {
            "alerts": {
                "edges": [
                    {
                        "node": {
                            "id": "alert-1",
                            "name": "Critical Alert",
                            "severity": "CRITICAL",
                            "status": "NEW",
                            "detectedAt": "2024-01-01T00:00:00Z",
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
                "totalCount": 1,
            }
        }

        filters = [
            FilterInput(fieldId="severity", stringIn=InFilterStringInput(values=["CRITICAL"]))
        ]

        with patch.object(
            client, "execute_compatible_query", new=AsyncMock(return_value=response_data)
        ) as mock_execute:
            result = await client.search_alerts(filters=filters, first=10)

            # Verify filters were serialized
            call_args = mock_execute.call_args
            assert "filters" in call_args[0][1]

        assert len(result.edges) == 1
        assert result.edges[0].node.severity == "CRITICAL"

    @pytest.mark.asyncio
    async def test_search_without_filters(self, config: AlertsConfig) -> None:
        """Test search without filters."""
        client = AlertsClient(config)
        response_data: JsonDict = {
            "alerts": {
                "edges": [],
                "pageInfo": {
                    "hasNextPage": False,
                    "hasPreviousPage": False,
                    "startCursor": None,
                    "endCursor": None,
                },
                "totalCount": 0,
            }
        }

        with patch.object(
            client, "execute_compatible_query", new=AsyncMock(return_value=response_data)
        ):
            result = await client.search_alerts(first=10)

        assert len(result.edges) == 0


class TestGetAlertNotes:
    """Test get_alert_notes method."""

    @pytest.fixture
    def config(self) -> AlertsConfig:
        """Create test configuration."""
        return AlertsConfig(
            graphql_url="https://console.test/graphql",
            auth_token="test-token",
        )

    @pytest.mark.asyncio
    async def test_successful_get_notes(self, config: AlertsConfig) -> None:
        """Test successful notes retrieval."""
        client = AlertsClient(config)
        response_data: JsonDict = {
            "alertNotes": {
                "data": [
                    {
                        "id": "note-1",
                        "text": "Test note",
                        "createdAt": "2024-01-01T00:00:00Z",
                        "author": {"userId": "user-1", "email": "test@test.test"},
                        "alertId": "alert-123",
                    }
                ]
            }
        }

        with patch.object(client, "execute_query", new=AsyncMock(return_value=response_data)):
            result = await client.get_alert_notes("alert-123")

        assert len(result.data) == 1
        assert result.data[0].text == "Test note"


class TestGetAlertHistory:
    """Test get_alert_history method."""

    @pytest.fixture
    def config(self) -> AlertsConfig:
        """Create test configuration."""
        return AlertsConfig(
            graphql_url="https://console.test/graphql",
            auth_token="test-token",
        )

    @pytest.mark.asyncio
    async def test_successful_get_history(self, config: AlertsConfig) -> None:
        """Test successful history retrieval."""
        client = AlertsClient(config)
        response_data: JsonDict = {
            "alertHistory": {
                "edges": [
                    {
                        "node": {
                            "createdAt": "2024-01-01T00:00:00Z",
                            "eventText": "Alert status changed",
                            "eventType": "STATUS_CHANGED",
                            "reportUrl": None,
                            "historyItemCreator": {
                                "userId": "user-123",
                                "userType": "MDR",
                            },
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
                "totalCount": 1,
            }
        }

        with patch.object(client, "execute_query", new=AsyncMock(return_value=response_data)):
            result = await client.get_alert_history("alert-123", first=5)

        assert len(result.edges) == 1
        assert result.edges[0].node.event_type == "STATUS_CHANGED"
        assert result.edges[0].node.event_text == "Alert status changed"
        assert result.edges[0].node.created_at == "2024-01-01T00:00:00Z"
        assert result.edges[0].node.history_item_creator is not None
        assert result.edges[0].node.history_item_creator.user_id == "user-123"
        assert result.page_info.has_next_page is True

    @pytest.mark.asyncio
    async def test_get_history_with_system_event(self, config: AlertsConfig) -> None:
        """Test history with system-generated event (no user creator)."""
        client = AlertsClient(config)
        response_data: JsonDict = {
            "alertHistory": {
                "edges": [
                    {
                        "node": {
                            "createdAt": "2024-01-01T00:00:00Z",
                            "eventText": "System automatically updated alert",
                            "eventType": "SYSTEM_UPDATE",
                            "reportUrl": None,
                            "historyItemCreator": {"__typename": "SystemHistoryItemCreator"},
                        },
                        "cursor": "cursor1",
                    },
                    {
                        "node": {
                            "createdAt": "2024-01-02T00:00:00Z",
                            "eventText": "Another system event",
                            "eventType": "SYSTEM_UPDATE",
                            "reportUrl": None,
                            "historyItemCreator": {},
                        },
                        "cursor": "cursor2",
                    },
                ],
                "pageInfo": {
                    "hasNextPage": False,
                    "hasPreviousPage": False,
                    "startCursor": "cursor1",
                    "endCursor": "cursor2",
                },
                "totalCount": 2,
            }
        }

        with patch.object(client, "execute_query", new=AsyncMock(return_value=response_data)):
            result = await client.get_alert_history("alert-123", first=5)

        assert len(result.edges) == 2
        # Both events should have None creator since they're not UserHistoryItemCreator
        assert result.edges[0].node.history_item_creator is None
        assert result.edges[1].node.history_item_creator is None

    @pytest.mark.asyncio
    async def test_get_history_with_pagination(self, config: AlertsConfig) -> None:
        """Test getting history with pagination."""
        client = AlertsClient(config)
        response_data: JsonDict = {
            "alertHistory": {
                "edges": [],
                "pageInfo": {
                    "hasNextPage": False,
                    "hasPreviousPage": True,
                    "startCursor": None,
                    "endCursor": None,
                },
                "totalCount": 0,
            }
        }

        with patch.object(
            client, "execute_query", new=AsyncMock(return_value=response_data)
        ) as mock_execute:
            result = await client.get_alert_history("alert-123", first=10, after="cursor1")

            # Verify pagination parameters
            call_args = mock_execute.call_args
            assert call_args[0][1]["first"] == 10
            assert call_args[0][1]["after"] == "cursor1"

        assert result.page_info.has_previous_page is True
        assert result.total_count == 0
