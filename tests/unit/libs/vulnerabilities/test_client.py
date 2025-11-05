"""Unit tests for vulnerabilities client."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest
from respx import MockRouter

from purple_mcp.libs.vulnerabilities.client import VulnerabilitiesClient
from purple_mcp.libs.vulnerabilities.config import VulnerabilitiesConfig
from purple_mcp.libs.vulnerabilities.exceptions import (
    VulnerabilitiesClientError,
    VulnerabilitiesGraphQLError,
)
from purple_mcp.libs.vulnerabilities.models import FilterInput, InFilterStringInput
from purple_mcp.type_defs import JsonDict


class TestExecuteQuery:
    """Test execute_query method."""

    @pytest.fixture
    def config(self) -> VulnerabilitiesConfig:
        """Create test configuration."""
        return VulnerabilitiesConfig(
            graphql_url="https://console.test/graphql",
            auth_token="test-token",
        )

    @pytest.mark.asyncio
    async def test_successful_query(
        self, config: VulnerabilitiesConfig, respx_mock: MockRouter
    ) -> None:
        """Test successful GraphQL query execution."""
        client = VulnerabilitiesClient(config)
        mock_response = {"data": {"vulnerability": {"id": "test-1"}}}

        respx_mock.post(config.graphql_url).mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        result = await client.execute_query("query { vulnerability { id } }")

        assert result == {"vulnerability": {"id": "test-1"}}

    @pytest.mark.asyncio
    async def test_timeout_error(
        self, config: VulnerabilitiesConfig, respx_mock: MockRouter
    ) -> None:
        """Test timeout error handling."""
        client = VulnerabilitiesClient(config)

        respx_mock.post(config.graphql_url).mock(side_effect=httpx.TimeoutException("Timeout"))

        with pytest.raises(VulnerabilitiesClientError) as exc_info:
            await client.execute_query("query { test }")

        assert "timed out" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_network_error(
        self, config: VulnerabilitiesConfig, respx_mock: MockRouter
    ) -> None:
        """Test network error handling."""
        client = VulnerabilitiesClient(config)

        respx_mock.post(config.graphql_url).mock(side_effect=httpx.RequestError("Network error"))

        with pytest.raises(VulnerabilitiesClientError) as exc_info:
            await client.execute_query("query { test }")

        assert "Network error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_http_error(self, config: VulnerabilitiesConfig, respx_mock: MockRouter) -> None:
        """Test HTTP error handling."""
        client = VulnerabilitiesClient(config)

        respx_mock.post(config.graphql_url).mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )

        with pytest.raises(VulnerabilitiesClientError) as exc_info:
            await client.execute_query("query { test }")

        assert "HTTP error" in str(exc_info.value)
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_json_parse_error(
        self, config: VulnerabilitiesConfig, respx_mock: MockRouter
    ) -> None:
        """Test JSON parsing error handling."""
        client = VulnerabilitiesClient(config)

        respx_mock.post(config.graphql_url).mock(
            return_value=httpx.Response(200, content=b"Invalid JSON")
        )

        with pytest.raises(VulnerabilitiesClientError) as exc_info:
            await client.execute_query("query { test }")

        assert "Failed to parse JSON" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_graphql_errors(
        self, config: VulnerabilitiesConfig, respx_mock: MockRouter
    ) -> None:
        """Test GraphQL error handling."""
        client = VulnerabilitiesClient(config)
        mock_response = {
            "errors": [{"message": "Field not found"}],
            "data": None,
        }

        respx_mock.post(config.graphql_url).mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        with pytest.raises(VulnerabilitiesGraphQLError) as exc_info:
            await client.execute_query("query { test }")

        assert "GraphQL errors" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_missing_data_field(
        self, config: VulnerabilitiesConfig, respx_mock: MockRouter
    ) -> None:
        """Test missing data field in response."""
        client = VulnerabilitiesClient(config)
        mock_response: JsonDict = {}

        respx_mock.post(config.graphql_url).mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        with pytest.raises(VulnerabilitiesGraphQLError) as exc_info:
            await client.execute_query("query { test }")

        assert "No data field" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_non_dict_data_field(
        self, config: VulnerabilitiesConfig, respx_mock: MockRouter
    ) -> None:
        """Test non-dict data field in response."""
        client = VulnerabilitiesClient(config)
        mock_response = {"data": "not a dict"}

        respx_mock.post(config.graphql_url).mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        with pytest.raises(VulnerabilitiesGraphQLError) as exc_info:
            await client.execute_query("query { test }")

        assert "not a dictionary" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_timeout_retry_then_success(
        self, config: VulnerabilitiesConfig, respx_mock: MockRouter
    ) -> None:
        """Test that timeout is retried and eventually succeeds."""
        client = VulnerabilitiesClient(config)
        mock_response = {"data": {"vulnerability": {"id": "test-1"}}}

        # First 2 calls raise timeout, third succeeds
        request_mock = respx_mock.post(config.graphql_url).mock(
            side_effect=[
                httpx.TimeoutException("Timeout"),
                httpx.TimeoutException("Timeout"),
                httpx.Response(200, json=mock_response),
            ]
        )

        result = await client.execute_query("query { vulnerability { id } }")

        assert result == {"vulnerability": {"id": "test-1"}}
        assert request_mock.call_count == 3  # Verify 3 attempts were made

    @pytest.mark.asyncio
    async def test_network_error_retry_then_success(
        self, config: VulnerabilitiesConfig, respx_mock: MockRouter
    ) -> None:
        """Test that network error is retried and eventually succeeds."""
        client = VulnerabilitiesClient(config)
        mock_response = {"data": {"vulnerability": {"id": "test-1"}}}

        # First 2 calls raise network error, third succeeds
        request_mock = respx_mock.post(config.graphql_url).mock(
            side_effect=[
                httpx.NetworkError("Network error"),
                httpx.NetworkError("Network error"),
                httpx.Response(200, json=mock_response),
            ]
        )

        result = await client.execute_query("query { vulnerability { id } }")

        assert result == {"vulnerability": {"id": "test-1"}}
        assert request_mock.call_count == 3  # Verify 3 attempts were made


class TestGetVulnerability:
    """Test get_vulnerability method."""

    @pytest.fixture
    def config(self) -> VulnerabilitiesConfig:
        """Create test configuration."""
        return VulnerabilitiesConfig(
            graphql_url="https://console.test/graphql",
            auth_token="test-token",
        )

    @pytest.mark.asyncio
    async def test_successful_get(self, config: VulnerabilitiesConfig) -> None:
        """Test successful vulnerability retrieval."""
        client = VulnerabilitiesClient(config)
        vuln_data: JsonDict = {
            "id": "vuln-123",
            "externalId": "ext-123",
            "name": "Test Vulnerability",
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
            "cve": {"id": "CVE-2024-1234", "description": "Test CVE"},
            "software": {"name": "Test Software", "version": "1.0"},
            "product": "Test Product",
            "vendor": "Test Vendor",
            "detectedAt": "2024-01-01T00:00:00Z",
            "findingData": {},
            "paidScope": False,
            "remediationInsightsAvailable": False,
        }

        with patch.object(
            client, "execute_query", new=AsyncMock(return_value={"vulnerability": vuln_data})
        ):
            result = await client.get_vulnerability("vuln-123")

        assert result is not None
        assert result.id == "vuln-123"
        assert result.name == "Test Vulnerability"

    @pytest.mark.asyncio
    async def test_vulnerability_not_found(self, config: VulnerabilitiesConfig) -> None:
        """Test when vulnerability is not found."""
        client = VulnerabilitiesClient(config)

        with patch.object(
            client, "execute_query", new=AsyncMock(return_value={"vulnerability": None})
        ):
            result = await client.get_vulnerability("nonexistent")

        assert result is None


class TestListVulnerabilities:
    """Test list_vulnerabilities method."""

    @pytest.fixture
    def config(self) -> VulnerabilitiesConfig:
        """Create test configuration."""
        return VulnerabilitiesConfig(
            graphql_url="https://console.test/graphql",
            auth_token="test-token",
        )

    @pytest.mark.asyncio
    async def test_successful_list(self, config: VulnerabilitiesConfig) -> None:
        """Test successful vulnerabilities listing."""
        client = VulnerabilitiesClient(config)
        response_data: JsonDict = {
            "vulnerabilities": {
                "edges": [
                    {
                        "node": {
                            "id": "vuln-1",
                            "externalId": "ext-1",
                            "name": "Vuln 1",
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
                            "cve": {"id": "CVE-2024-1", "description": "Test CVE"},
                            "software": {"name": "Test", "version": "1.0"},
                            "product": "Test",
                            "vendor": "Test",
                            "detectedAt": "2024-01-01T00:00:00Z",
                            "findingData": {},
                            "paidScope": False,
                            "remediationInsightsAvailable": False,
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
            result = await client.list_vulnerabilities(first=10)

        assert len(result.edges) == 1
        assert result.edges[0].node.id == "vuln-1"

    @pytest.mark.asyncio
    async def test_list_with_pagination(self, config: VulnerabilitiesConfig) -> None:
        """Test listing with pagination cursor."""
        client = VulnerabilitiesClient(config)
        response_data: JsonDict = {
            "vulnerabilities": {
                "edges": [],
                "pageInfo": {
                    "hasNextPage": False,
                    "hasPreviousPage": True,
                    "startCursor": "cursor1",
                    "endCursor": "cursor2",
                },
            }
        }

        with patch.object(
            client, "execute_query", new=AsyncMock(return_value=response_data)
        ) as mock_execute:
            result = await client.list_vulnerabilities(first=20, after="cursor1")

            # Verify pagination parameters were passed
            call_args = mock_execute.call_args
            assert call_args[0][1]["first"] == 20
            assert call_args[0][1]["after"] == "cursor1"

        assert result.page_info.has_previous_page is True

    @pytest.mark.asyncio
    async def test_list_empty_response(self, config: VulnerabilitiesConfig) -> None:
        """Test listing when no vulnerabilities returned."""
        client = VulnerabilitiesClient(config)

        with patch.object(client, "execute_query", new=AsyncMock(return_value={})):
            result = await client.list_vulnerabilities()

        assert len(result.edges) == 0
        assert result.page_info.has_next_page is False


class TestSearchVulnerabilities:
    """Test search_vulnerabilities method."""

    @pytest.fixture
    def config(self) -> VulnerabilitiesConfig:
        """Create test configuration."""
        return VulnerabilitiesConfig(
            graphql_url="https://console.test/graphql",
            auth_token="test-token",
        )

    @pytest.mark.asyncio
    async def test_successful_search(self, config: VulnerabilitiesConfig) -> None:
        """Test successful vulnerability search."""
        client = VulnerabilitiesClient(config)
        response_data: JsonDict = {
            "vulnerabilities": {
                "edges": [
                    {
                        "node": {
                            "id": "vuln-1",
                            "externalId": "ext-1",
                            "name": "Critical Vuln",
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
                            "cve": {"id": "CVE-2024-1", "description": "Test CVE"},
                            "software": {"name": "Test", "version": "1.0"},
                            "product": "Test",
                            "vendor": "Test",
                            "detectedAt": "2024-01-01T00:00:00Z",
                            "findingData": {},
                            "paidScope": False,
                            "remediationInsightsAvailable": False,
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
            client, "execute_query", new=AsyncMock(return_value=response_data)
        ) as mock_execute:
            result = await client.search_vulnerabilities(filters=filters, first=10)

            # Verify filters were serialized
            call_args = mock_execute.call_args
            assert "filters" in call_args[0][1]

        assert len(result.edges) == 1
        assert result.edges[0].node.severity == "CRITICAL"

    @pytest.mark.asyncio
    async def test_search_without_filters(self, config: VulnerabilitiesConfig) -> None:
        """Test search without filters."""
        client = VulnerabilitiesClient(config)
        response_data: JsonDict = {
            "vulnerabilities": {
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
            client, "execute_query", new=AsyncMock(return_value=response_data)
        ) as mock_execute:
            result = await client.search_vulnerabilities(first=10)

            # Verify no filters were passed
            call_args = mock_execute.call_args
            assert "filters" not in call_args[0][1] or call_args[0][1].get("filters") is None

        assert len(result.edges) == 0


class TestGetVulnerabilityNotes:
    """Test get_vulnerability_notes method."""

    @pytest.fixture
    def config(self) -> VulnerabilitiesConfig:
        """Create test configuration."""
        return VulnerabilitiesConfig(
            graphql_url="https://console.test/graphql",
            auth_token="test-token",
        )

    @pytest.mark.asyncio
    async def test_successful_get_notes(self, config: VulnerabilitiesConfig) -> None:
        """Test successful notes retrieval."""
        client = VulnerabilitiesClient(config)
        response_data: JsonDict = {
            "vulnerabilityNotes": {
                "edges": [
                    {
                        "node": {
                            "id": "note-1",
                            "vulnerabilityId": "vuln-123",
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
            result = await client.get_vulnerability_notes("vuln-123")

        assert len(result.edges) == 1
        assert result.edges[0].node.text == "Test note"

    @pytest.mark.asyncio
    async def test_get_notes_empty(self, config: VulnerabilitiesConfig) -> None:
        """Test getting notes when none exist."""
        client = VulnerabilitiesClient(config)

        with patch.object(client, "execute_query", new=AsyncMock(return_value={})):
            result = await client.get_vulnerability_notes("vuln-123")

        assert len(result.edges) == 0


class TestGetVulnerabilityHistory:
    """Test get_vulnerability_history method."""

    @pytest.fixture
    def config(self) -> VulnerabilitiesConfig:
        """Create test configuration."""
        return VulnerabilitiesConfig(
            graphql_url="https://console.test/graphql",
            auth_token="test-token",
        )

    @pytest.mark.asyncio
    async def test_successful_get_history(self, config: VulnerabilitiesConfig) -> None:
        """Test successful history retrieval."""
        client = VulnerabilitiesClient(config)
        response_data: JsonDict = {
            "vulnerabilityHistory": {
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
            result = await client.get_vulnerability_history("vuln-123", first=5)

        assert len(result.edges) == 1
        assert result.edges[0].node.event_type == "STATUS"
        assert result.page_info.has_next_page is True

    @pytest.mark.asyncio
    async def test_get_history_with_pagination(self, config: VulnerabilitiesConfig) -> None:
        """Test getting history with pagination."""
        client = VulnerabilitiesClient(config)
        response_data: JsonDict = {
            "vulnerabilityHistory": {
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
            result = await client.get_vulnerability_history("vuln-123", first=10, after="cursor1")

            # Verify pagination parameters
            call_args = mock_execute.call_args
            assert call_args[0][1]["first"] == 10
            assert call_args[0][1]["after"] == "cursor1"

        assert result.page_info.has_previous_page is True
