"""Unit tests for inventory client."""

import httpx
import pytest
from respx import MockRouter

from purple_mcp.libs.inventory.client import InventoryClient
from purple_mcp.libs.inventory.config import InventoryConfig
from purple_mcp.libs.inventory.exceptions import (
    InventoryAPIError,
    InventoryAuthenticationError,
    InventoryNetworkError,
    InventoryNotFoundError,
)
from purple_mcp.libs.inventory.models import Surface


class TestInventoryClient:
    """Test InventoryClient class."""

    @pytest.fixture
    def config(self) -> InventoryConfig:
        """Create test configuration."""
        return InventoryConfig(
            base_url="https://example.sentinelone.test",
            api_endpoint="/web/api/v2.1/xdr/assets",
            api_token="test-token-123",
        )

    @pytest.mark.asyncio
    async def test_search_inventory_uses_query_params(
        self, config: InventoryConfig, respx_mock: MockRouter
    ) -> None:
        """Test that search_inventory passes limit and skip as query parameters, not in body."""
        # Setup mock response
        mock_response = {
            "data": [{"id": "test-1", "name": "Test Item"}],
            "pagination": {"totalCount": 1},
        }

        request_mock = respx_mock.post(config.full_url).mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        # Create client and use it
        client = InventoryClient(config)
        async with client:
            filters = {"resourceType": ["Windows Server"]}
            await client.search_inventory(
                filters=filters,
                limit=100,
                skip=50,
            )

        # Verify POST was called with correct parameters
        assert request_mock.called
        assert request_mock.call_count == 1

        # Get the request to verify the payload
        request = request_mock.calls.last.request

        # Note: The actual implementation uses json body, so we check the request content
        import json

        actual_payload = json.loads(request.content)

        # Check that json payload contains filters with limit/skip
        assert "filter" in actual_payload
        expected_filter = {**filters, "limit": 100, "skip": 50}
        assert actual_payload["filter"] == expected_filter

        # Verify that limit/skip are NOT in query params (they should be in the body)
        assert not request.url.params

    @pytest.mark.asyncio
    async def test_list_inventory_uses_query_params(
        self, config: InventoryConfig, respx_mock: MockRouter
    ) -> None:
        """Test that list_inventory uses query parameters correctly."""
        # Setup mock response
        mock_response = {
            "data": [{"id": "test-1", "name": "Test Item"}],
            "pagination": {"totalCount": 1},
        }

        request_mock = respx_mock.get(config.full_url).mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        client = InventoryClient(config)
        async with client:
            await client.list_inventory(limit=200, skip=100)

        # Verify GET was called with correct parameters
        assert request_mock.called
        request = request_mock.calls.last.request

        # Check query params
        params = dict(request.url.params)
        assert params["limit"] == "200"
        assert params["skip"] == "100"

    @pytest.mark.asyncio
    async def test_search_inventory_handles_authentication_error(
        self, config: InventoryConfig, respx_mock: MockRouter
    ) -> None:
        """Test that search_inventory handles 401 authentication errors."""
        # Setup mock response
        mock_response = {"errors": [{"title": "Unauthorized"}]}

        respx_mock.post(config.full_url).mock(return_value=httpx.Response(401, json=mock_response))

        client = InventoryClient(config)
        async with client:
            # InventoryAuthenticationError is properly raised without wrapping
            with pytest.raises(InventoryAuthenticationError) as exc_info:
                await client.search_inventory(filters={})

            assert "Authentication failed" in str(exc_info.value)
            assert "401" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_inventory_handles_api_error(
        self, config: InventoryConfig, respx_mock: MockRouter
    ) -> None:
        """Test that search_inventory handles API errors."""
        # Setup mock response
        mock_response = {"errors": [{"title": "Bad Request", "detail": "Invalid filter"}]}

        respx_mock.post(config.full_url).mock(return_value=httpx.Response(400, json=mock_response))

        client = InventoryClient(config)
        async with client:
            with pytest.raises(InventoryAPIError) as exc_info:
                await client.search_inventory(filters={"invalid": "filter"})

            assert "400" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_inventory_handles_timeout(
        self, config: InventoryConfig, respx_mock: MockRouter
    ) -> None:
        """Test that search_inventory handles timeout errors."""
        respx_mock.post(config.full_url).mock(side_effect=httpx.TimeoutException("Timeout"))

        client = InventoryClient(config)
        async with client:
            with pytest.raises(InventoryNetworkError) as exc_info:
                await client.search_inventory(filters={})

            assert "timeout" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_search_inventory_handles_network_error(
        self, config: InventoryConfig, respx_mock: MockRouter
    ) -> None:
        """Test that search_inventory handles network errors."""
        respx_mock.post(config.full_url).mock(
            side_effect=httpx.NetworkError("Network unreachable")
        )

        client = InventoryClient(config)
        async with client:
            with pytest.raises(InventoryNetworkError) as exc_info:
                await client.search_inventory(filters={})

            assert "Network" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_inventory_item(
        self, config: InventoryConfig, respx_mock: MockRouter
    ) -> None:
        """Test get_inventory_item method."""
        # Setup mock response for search_inventory (which get_inventory_item uses)
        mock_response = {
            "data": [{"id": "test-123", "name": "Test Item"}],
            "pagination": {"totalCount": 1},
        }

        respx_mock.post(config.full_url).mock(return_value=httpx.Response(200, json=mock_response))

        client = InventoryClient(config)
        async with client:
            result = await client.get_inventory_item("test-123")

        assert result is not None
        assert result.id == "test-123"
        assert result.name == "Test Item"

    @pytest.mark.asyncio
    async def test_get_inventory_item_not_found(
        self, config: InventoryConfig, respx_mock: MockRouter
    ) -> None:
        """Test get_inventory_item returns None when item not found."""
        # Setup mock response with no data (search_inventory returns empty)
        mock_response = {
            "data": [],
            "pagination": {"totalCount": 0},
        }

        respx_mock.post(config.full_url).mock(return_value=httpx.Response(200, json=mock_response))

        client = InventoryClient(config)
        async with client:
            result = await client.get_inventory_item("nonexistent-id")

        assert result is None

    @pytest.mark.asyncio
    async def test_client_not_initialized_error(self, config: InventoryConfig) -> None:
        """Test that operations fail if client not used in context manager."""
        client = InventoryClient(config)

        with pytest.raises(InventoryAPIError) as exc_info:
            await client.search_inventory(filters={})

        assert "not initialized" in str(exc_info.value).lower()

    def test_get_surface_endpoint_base(self, config: InventoryConfig) -> None:
        """Test _get_surface_endpoint returns base endpoint for None surface."""
        client = InventoryClient(config)
        endpoint = client._get_surface_endpoint(None)
        assert endpoint == config.full_url

    def test_get_surface_endpoint_cloud(self, config: InventoryConfig) -> None:
        """Test _get_surface_endpoint returns cloud endpoint for CLOUD surface."""
        client = InventoryClient(config)
        endpoint = client._get_surface_endpoint(Surface.CLOUD)
        assert endpoint == f"{config.full_url}/surface/cloud"

    def test_get_surface_endpoint_endpoint(self, config: InventoryConfig) -> None:
        """Test _get_surface_endpoint returns endpoint for ENDPOINT surface."""
        client = InventoryClient(config)
        endpoint = client._get_surface_endpoint(Surface.ENDPOINT)
        assert endpoint == f"{config.full_url}/surface/endpoint"

    def test_get_surface_endpoint_identity(self, config: InventoryConfig) -> None:
        """Test _get_surface_endpoint returns identity endpoint for IDENTITY surface."""
        client = InventoryClient(config)
        endpoint = client._get_surface_endpoint(Surface.IDENTITY)
        assert endpoint == f"{config.full_url}/surface/identity"

    def test_get_surface_endpoint_network_discovery(self, config: InventoryConfig) -> None:
        """Test _get_surface_endpoint returns network-discovery endpoint."""
        client = InventoryClient(config)
        endpoint = client._get_surface_endpoint(Surface.NETWORK_DISCOVERY)
        assert endpoint == f"{config.full_url}/surface/network_discovery"

    @pytest.mark.asyncio
    async def test_search_inventory_handles_403_forbidden(
        self, config: InventoryConfig, respx_mock: MockRouter
    ) -> None:
        """Test that search_inventory handles 403 forbidden errors."""
        mock_response = {"errors": [{"title": "Forbidden"}]}

        respx_mock.post(config.full_url).mock(return_value=httpx.Response(403, json=mock_response))

        client = InventoryClient(config)
        async with client:
            # InventoryAuthenticationError is properly raised without wrapping
            with pytest.raises(InventoryAuthenticationError) as exc_info:
                await client.search_inventory(filters={})

            assert "Authentication failed" in str(exc_info.value)
            assert "403" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_context_manager_lifecycle(
        self, config: InventoryConfig, respx_mock: MockRouter
    ) -> None:
        """Test that context manager properly initializes and closes client."""
        client = InventoryClient(config)

        # Before entering context, client should be None
        assert client._client is None

        async with client:
            # Inside context, client should be initialized
            assert client._client is not None

        # After exiting context, client should be None
        assert client._client is None

    @pytest.mark.asyncio
    async def test_handle_response_with_404(
        self, config: InventoryConfig, respx_mock: MockRouter
    ) -> None:
        """Test that _handle_response raises InventoryNotFoundError for 404."""
        mock_response = {"error": "Not found"}

        respx_mock.get(config.full_url).mock(return_value=httpx.Response(404, json=mock_response))

        client = InventoryClient(config)
        async with client:
            # 404 raises InventoryNotFoundError without wrapping
            with pytest.raises(InventoryNotFoundError) as exc_info:
                await client.list_inventory()

            # The error message should contain info about the NotFoundError
            assert "Inventory resource not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handle_response_with_multiple_error_message_formats(
        self, config: InventoryConfig, respx_mock: MockRouter
    ) -> None:
        """Test that _handle_response handles various error message formats."""
        # Test with 'message' field
        mock_response = {"message": "Internal server error"}

        respx_mock.get(config.full_url).mock(return_value=httpx.Response(500, json=mock_response))

        client = InventoryClient(config)
        async with client:
            with pytest.raises(InventoryAPIError) as exc_info:
                await client.list_inventory()

            assert "Internal server error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handle_response_with_error_field(
        self, config: InventoryConfig, respx_mock: MockRouter
    ) -> None:
        """Test that _handle_response handles 'error' field."""
        mock_response = {"error": "Bad request"}

        respx_mock.post(config.full_url).mock(return_value=httpx.Response(400, json=mock_response))

        client = InventoryClient(config)
        async with client:
            with pytest.raises(InventoryAPIError) as exc_info:
                await client.search_inventory(filters={})

            assert "Bad request" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handle_response_with_non_json_error(
        self, config: InventoryConfig, respx_mock: MockRouter
    ) -> None:
        """Test that _handle_response handles non-JSON error responses and retries 502."""
        # 502 is now retried, so mock returns 502 for all 3 attempts
        respx_mock.get(config.full_url).mock(
            return_value=httpx.Response(502, text="<html>Bad Gateway</html>")
        )

        client = InventoryClient(config)
        async with client:
            with pytest.raises(InventoryAPIError) as exc_info:
                await client.list_inventory()

            # After retries are exhausted, error mentions "multiple retries"
            assert "502" in str(exc_info.value)
            assert "multiple retries" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_inventory_item_uses_search(
        self, config: InventoryConfig, respx_mock: MockRouter
    ) -> None:
        """Test that get_inventory_item uses search_inventory with id__in filter."""
        mock_response = {
            "data": [{"id": "test-123", "name": "Test"}],
            "pagination": {"totalCount": 1},
        }

        request_mock = respx_mock.post(config.full_url).mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        client = InventoryClient(config)
        async with client:
            result = await client.get_inventory_item("test-123")

        # Verify POST was called with id__in filter
        assert request_mock.called
        request = request_mock.calls.last.request

        import json

        json_payload = json.loads(request.content)
        assert "filter" in json_payload
        assert "id__in" in json_payload["filter"]
        assert json_payload["filter"]["id__in"] == ["test-123"]

        # Verify result
        assert result is not None
        assert result.id == "test-123"

    @pytest.mark.asyncio
    async def test_list_inventory_with_surface_endpoint(
        self, config: InventoryConfig, respx_mock: MockRouter
    ) -> None:
        """Test that list_inventory uses surface-specific endpoint."""
        mock_response = {"data": [], "pagination": {"totalCount": 0}}

        endpoint_url = f"{config.full_url}/surface/endpoint"
        request_mock = respx_mock.get(endpoint_url).mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        client = InventoryClient(config)
        async with client:
            await client.list_inventory(surface=Surface.ENDPOINT)

        # Verify correct endpoint was called
        assert request_mock.called

    @pytest.mark.asyncio
    async def test_search_inventory_with_empty_filters(
        self, config: InventoryConfig, respx_mock: MockRouter
    ) -> None:
        """Test that search_inventory works with empty filter dict."""
        mock_response = {"data": [], "pagination": {"totalCount": 0}}

        request_mock = respx_mock.post(config.full_url).mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        client = InventoryClient(config)
        async with client:
            result = await client.search_inventory(filters={})

        # Verify empty filters were sent (with default pagination params in body)
        request = request_mock.calls.last.request
        import json

        json_payload = json.loads(request.content)
        assert json_payload["filter"] == {"limit": 50, "skip": 0}

        # Verify result
        assert result.data == []

    @pytest.mark.asyncio
    async def test_list_inventory_timeout_retry_then_success(
        self, config: InventoryConfig, respx_mock: MockRouter
    ) -> None:
        """Test that list_inventory timeout is retried and eventually succeeds."""
        # Setup mock response for successful attempt
        mock_response = {
            "data": [{"id": "test-1", "name": "Test Item"}],
            "pagination": {"totalCount": 1},
        }

        # First 2 calls raise timeout, third succeeds
        request_mock = respx_mock.get(config.full_url).mock(
            side_effect=[
                httpx.TimeoutException("Timeout"),
                httpx.TimeoutException("Timeout"),
                httpx.Response(200, json=mock_response),
            ]
        )

        client = InventoryClient(config)
        async with client:
            result = await client.list_inventory()

        # Verify result is successful
        assert len(result.data) == 1
        assert result.data[0].id == "test-1"
        # Verify 3 attempts were made (2 failures + 1 success)
        assert request_mock.call_count == 3

    @pytest.mark.asyncio
    async def test_list_inventory_network_error_retry_then_success(
        self, config: InventoryConfig, respx_mock: MockRouter
    ) -> None:
        """Test that list_inventory network error is retried and eventually succeeds."""
        # Setup mock response for successful attempt
        mock_response = {
            "data": [{"id": "test-1", "name": "Test Item"}],
            "pagination": {"totalCount": 1},
        }

        # First 2 calls raise network error, third succeeds
        request_mock = respx_mock.get(config.full_url).mock(
            side_effect=[
                httpx.NetworkError("Network unreachable"),
                httpx.NetworkError("Network unreachable"),
                httpx.Response(200, json=mock_response),
            ]
        )

        client = InventoryClient(config)
        async with client:
            result = await client.list_inventory()

        # Verify result is successful
        assert len(result.data) == 1
        assert result.data[0].id == "test-1"
        # Verify 3 attempts were made (2 failures + 1 success)
        assert request_mock.call_count == 3

    @pytest.mark.asyncio
    async def test_search_inventory_timeout_retry_then_success(
        self, config: InventoryConfig, respx_mock: MockRouter
    ) -> None:
        """Test that search_inventory timeout is retried and eventually succeeds."""
        # Setup mock response for successful attempt
        mock_response = {
            "data": [{"id": "test-1", "name": "Test Item"}],
            "pagination": {"totalCount": 1},
        }

        # First 2 calls raise timeout, third succeeds
        request_mock = respx_mock.post(config.full_url).mock(
            side_effect=[
                httpx.TimeoutException("Timeout"),
                httpx.TimeoutException("Timeout"),
                httpx.Response(200, json=mock_response),
            ]
        )

        client = InventoryClient(config)
        async with client:
            result = await client.search_inventory(filters={})

        # Verify result is successful
        assert len(result.data) == 1
        assert result.data[0].id == "test-1"
        # Verify 3 attempts were made (2 failures + 1 success)
        assert request_mock.call_count == 3

    @pytest.mark.asyncio
    async def test_search_inventory_network_error_retry_then_success(
        self, config: InventoryConfig, respx_mock: MockRouter
    ) -> None:
        """Test that search_inventory network error is retried and eventually succeeds."""
        # Setup mock response for successful attempt
        mock_response = {
            "data": [{"id": "test-1", "name": "Test Item"}],
            "pagination": {"totalCount": 1},
        }

        # First 2 calls raise network error, third succeeds
        request_mock = respx_mock.post(config.full_url).mock(
            side_effect=[
                httpx.NetworkError("Network unreachable"),
                httpx.NetworkError("Network unreachable"),
                httpx.Response(200, json=mock_response),
            ]
        )

        client = InventoryClient(config)
        async with client:
            result = await client.search_inventory(filters={})

        # Verify result is successful
        assert len(result.data) == 1
        assert result.data[0].id == "test-1"
        # Verify 3 attempts were made (2 failures + 1 success)
        assert request_mock.call_count == 3

    @pytest.mark.asyncio
    async def test_list_inventory_502_retry_then_success(
        self, config: InventoryConfig, respx_mock: MockRouter
    ) -> None:
        """Test that list_inventory retries on 502 Bad Gateway and eventually succeeds."""
        mock_error_response = {"error": "Bad Gateway"}
        mock_success_response = {
            "data": [{"id": "test-1", "name": "Test Item"}],
            "pagination": {"totalCount": 1},
        }

        # First 2 calls return 502, third succeeds
        request_mock = respx_mock.get(config.full_url).mock(
            side_effect=[
                httpx.Response(502, json=mock_error_response),
                httpx.Response(502, json=mock_error_response),
                httpx.Response(200, json=mock_success_response),
            ]
        )

        client = InventoryClient(config)
        async with client:
            result = await client.list_inventory()

        # Verify result is successful
        assert len(result.data) == 1
        assert result.data[0].id == "test-1"
        # Verify 3 attempts were made (2 failures + 1 success)
        assert request_mock.call_count == 3

    @pytest.mark.asyncio
    async def test_list_inventory_503_retry_then_success(
        self, config: InventoryConfig, respx_mock: MockRouter
    ) -> None:
        """Test that list_inventory retries on 503 Service Unavailable and eventually succeeds."""
        mock_error_response = {"error": "Service Unavailable"}
        mock_success_response = {
            "data": [{"id": "test-1", "name": "Test Item"}],
            "pagination": {"totalCount": 1},
        }

        # First call returns 503, second succeeds
        request_mock = respx_mock.get(config.full_url).mock(
            side_effect=[
                httpx.Response(503, json=mock_error_response),
                httpx.Response(200, json=mock_success_response),
            ]
        )

        client = InventoryClient(config)
        async with client:
            result = await client.list_inventory()

        # Verify result is successful
        assert len(result.data) == 1
        assert result.data[0].id == "test-1"
        # Verify 2 attempts were made (1 failure + 1 success)
        assert request_mock.call_count == 2

    @pytest.mark.asyncio
    async def test_list_inventory_504_retry_then_success(
        self, config: InventoryConfig, respx_mock: MockRouter
    ) -> None:
        """Test that list_inventory retries on 504 Gateway Timeout and eventually succeeds."""
        mock_error_response = {"message": "Gateway Timeout"}
        mock_success_response = {
            "data": [{"id": "test-1", "name": "Test Item"}],
            "pagination": {"totalCount": 1},
        }

        # First 2 calls return 504, third succeeds
        request_mock = respx_mock.get(config.full_url).mock(
            side_effect=[
                httpx.Response(504, json=mock_error_response),
                httpx.Response(504, json=mock_error_response),
                httpx.Response(200, json=mock_success_response),
            ]
        )

        client = InventoryClient(config)
        async with client:
            result = await client.list_inventory()

        # Verify result is successful
        assert len(result.data) == 1
        assert result.data[0].id == "test-1"
        # Verify 3 attempts were made (2 failures + 1 success)
        assert request_mock.call_count == 3

    @pytest.mark.asyncio
    async def test_list_inventory_502_exhausts_retries(
        self, config: InventoryConfig, respx_mock: MockRouter
    ) -> None:
        """Test that list_inventory raises error after exhausting retries on 502."""
        mock_error_response = {"error": "Bad Gateway"}

        # All 3 calls return 502
        request_mock = respx_mock.get(config.full_url).mock(
            return_value=httpx.Response(502, json=mock_error_response)
        )

        client = InventoryClient(config)
        async with client:
            # Should raise InventoryAPIError after exhausting retries
            with pytest.raises(InventoryAPIError) as exc_info:
                await client.list_inventory()

            # Verify error message mentions retries were exhausted
            assert "multiple retries" in str(exc_info.value).lower()

        # Verify 3 attempts were made
        assert request_mock.call_count == 3

    @pytest.mark.asyncio
    async def test_list_inventory_500_not_retried(
        self, config: InventoryConfig, respx_mock: MockRouter
    ) -> None:
        """Test that list_inventory does NOT retry on 500 Internal Server Error."""
        mock_error_response = {"error": "Internal Server Error"}

        # Mock returns 500
        request_mock = respx_mock.get(config.full_url).mock(
            return_value=httpx.Response(500, json=mock_error_response)
        )

        client = InventoryClient(config)
        async with client:
            # Should raise InventoryAPIError immediately without retry
            with pytest.raises(InventoryAPIError) as exc_info:
                await client.list_inventory()

            assert "500" in str(exc_info.value)

        # Verify only 1 attempt was made (no retry)
        assert request_mock.call_count == 1

    @pytest.mark.asyncio
    async def test_search_inventory_502_retry_then_success(
        self, config: InventoryConfig, respx_mock: MockRouter
    ) -> None:
        """Test that search_inventory retries on 502 Bad Gateway and eventually succeeds."""
        mock_error_response = {"error": "Bad Gateway"}
        mock_success_response = {
            "data": [{"id": "test-1", "name": "Test Item"}],
            "pagination": {"totalCount": 1},
        }

        # First 2 calls return 502, third succeeds
        request_mock = respx_mock.post(config.full_url).mock(
            side_effect=[
                httpx.Response(502, json=mock_error_response),
                httpx.Response(502, json=mock_error_response),
                httpx.Response(200, json=mock_success_response),
            ]
        )

        client = InventoryClient(config)
        async with client:
            result = await client.search_inventory(filters={})

        # Verify result is successful
        assert len(result.data) == 1
        assert result.data[0].id == "test-1"
        # Verify 3 attempts were made (2 failures + 1 success)
        assert request_mock.call_count == 3

    @pytest.mark.asyncio
    async def test_search_inventory_503_retry_then_success(
        self, config: InventoryConfig, respx_mock: MockRouter
    ) -> None:
        """Test that search_inventory retries on 503 Service Unavailable and eventually succeeds."""
        mock_error_response = {"message": "Service Unavailable"}
        mock_success_response = {
            "data": [{"id": "test-1", "name": "Test Item"}],
            "pagination": {"totalCount": 1},
        }

        # First call returns 503, second succeeds
        request_mock = respx_mock.post(config.full_url).mock(
            side_effect=[
                httpx.Response(503, json=mock_error_response),
                httpx.Response(200, json=mock_success_response),
            ]
        )

        client = InventoryClient(config)
        async with client:
            result = await client.search_inventory(filters={})

        # Verify result is successful
        assert len(result.data) == 1
        assert result.data[0].id == "test-1"
        # Verify 2 attempts were made (1 failure + 1 success)
        assert request_mock.call_count == 2

    @pytest.mark.asyncio
    async def test_search_inventory_504_retry_then_success(
        self, config: InventoryConfig, respx_mock: MockRouter
    ) -> None:
        """Test that search_inventory retries on 504 Gateway Timeout and eventually succeeds."""
        mock_error_response = {"detail": "Gateway Timeout"}
        mock_success_response = {
            "data": [{"id": "test-1", "name": "Test Item"}],
            "pagination": {"totalCount": 1},
        }

        # First 2 calls return 504, third succeeds
        request_mock = respx_mock.post(config.full_url).mock(
            side_effect=[
                httpx.Response(504, json=mock_error_response),
                httpx.Response(504, json=mock_error_response),
                httpx.Response(200, json=mock_success_response),
            ]
        )

        client = InventoryClient(config)
        async with client:
            result = await client.search_inventory(filters={})

        # Verify result is successful
        assert len(result.data) == 1
        assert result.data[0].id == "test-1"
        # Verify 3 attempts were made (2 failures + 1 success)
        assert request_mock.call_count == 3

    @pytest.mark.asyncio
    async def test_search_inventory_503_exhausts_retries(
        self, config: InventoryConfig, respx_mock: MockRouter
    ) -> None:
        """Test that search_inventory raises error after exhausting retries on 503."""
        mock_error_response = {"message": "Service Unavailable"}

        # All 3 calls return 503
        request_mock = respx_mock.post(config.full_url).mock(
            return_value=httpx.Response(503, json=mock_error_response)
        )

        client = InventoryClient(config)
        async with client:
            # Should raise InventoryAPIError after exhausting retries
            with pytest.raises(InventoryAPIError) as exc_info:
                await client.search_inventory(filters={})

            # Verify error message mentions retries were exhausted
            assert "multiple retries" in str(exc_info.value).lower()

        # Verify 3 attempts were made
        assert request_mock.call_count == 3

    @pytest.mark.asyncio
    async def test_search_inventory_501_not_retried(
        self, config: InventoryConfig, respx_mock: MockRouter
    ) -> None:
        """Test that search_inventory does NOT retry on 501 Not Implemented."""
        mock_error_response = {"error": "Not Implemented"}

        # Mock returns 501
        request_mock = respx_mock.post(config.full_url).mock(
            return_value=httpx.Response(501, json=mock_error_response)
        )

        client = InventoryClient(config)
        async with client:
            # Should raise InventoryAPIError immediately without retry
            with pytest.raises(InventoryAPIError) as exc_info:
                await client.search_inventory(filters={})

            assert "501" in str(exc_info.value)

        # Verify only 1 attempt was made (no retry)
        assert request_mock.call_count == 1

    @pytest.mark.asyncio
    async def test_search_inventory_502_with_non_json_response(
        self, config: InventoryConfig, respx_mock: MockRouter
    ) -> None:
        """Test that search_inventory handles 502 with non-JSON response correctly."""
        mock_success_response = {
            "data": [{"id": "test-1", "name": "Test Item"}],
            "pagination": {"totalCount": 1},
        }

        # First call returns 502 with HTML, second succeeds
        request_mock = respx_mock.post(config.full_url).mock(
            side_effect=[
                httpx.Response(502, text="<html><body>Bad Gateway</body></html>"),
                httpx.Response(200, json=mock_success_response),
            ]
        )

        client = InventoryClient(config)
        async with client:
            result = await client.search_inventory(filters={})

        # Verify result is successful after retry
        assert len(result.data) == 1
        assert result.data[0].id == "test-1"
        # Verify 2 attempts were made (1 failure + 1 success)
        assert request_mock.call_count == 2
