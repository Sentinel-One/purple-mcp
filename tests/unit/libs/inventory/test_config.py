"""Tests for inventory configuration."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pydantic import ValidationError

from purple_mcp.libs.inventory.client import InventoryClient
from purple_mcp.libs.inventory.config import InventoryConfig


class TestInventoryConfig:
    """Test InventoryConfig class."""

    def test_config_initialization_with_all_fields(self) -> None:
        """Test that config initializes correctly with all required fields."""
        config = InventoryConfig(
            base_url="https://console.test",
            api_endpoint="/web/api/v2.1/xdr/assets",
            api_token="test-token-123",
        )

        assert config.base_url == "https://console.test"
        assert config.api_endpoint == "/web/api/v2.1/xdr/assets"
        assert config.api_token == "test-token-123"

    def test_config_missing_base_url(self) -> None:
        """Test that missing base_url raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            InventoryConfig(
                api_endpoint="/web/api/v2.1/xdr/assets",
                api_token="test-token",
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "missing"
        assert errors[0]["loc"] == ("base_url",)

    def test_config_missing_api_endpoint(self) -> None:
        """Test that missing api_endpoint raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            InventoryConfig(
                base_url="https://console.test",
                api_token="test-token",
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "missing"
        assert errors[0]["loc"] == ("api_endpoint",)

    def test_config_missing_api_token(self) -> None:
        """Test that missing api_token raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            InventoryConfig(
                base_url="https://console.test",
                api_endpoint="/web/api/v2.1/xdr/assets",
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "missing"
        assert errors[0]["loc"] == ("api_token",)

    def test_config_missing_all_fields(self) -> None:
        """Test that missing all required fields raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            InventoryConfig()

        errors = exc_info.value.errors()
        assert len(errors) == 3
        error_locs = {error["loc"] for error in errors}
        assert ("base_url",) in error_locs
        assert ("api_endpoint",) in error_locs
        assert ("api_token",) in error_locs

    def test_full_url_property(self) -> None:
        """Test that full_url property correctly combines base_url and api_endpoint."""
        config = InventoryConfig(
            base_url="https://console.test",
            api_endpoint="/web/api/v2.1/xdr/assets",
            api_token="test-token",
        )

        assert config.full_url == "https://console.test/web/api/v2.1/xdr/assets"

    def test_full_url_property_with_trailing_slash(self) -> None:
        """Test full_url property when base_url has trailing slash.

        The validator should strip trailing slashes from base_url,
        preventing double slashes in the full URL.
        """
        config = InventoryConfig(
            base_url="https://console.test/",
            api_endpoint="/web/api/v2.1/xdr/assets",
            api_token="test-token",
        )

        # Trailing slash should be stripped from base_url
        assert config.base_url == "https://console.test"
        assert config.full_url == "https://console.test/web/api/v2.1/xdr/assets"

    def test_full_url_property_without_leading_slash(self) -> None:
        """Test full_url property when api_endpoint lacks leading slash.

        The validator should ensure api_endpoint starts with a single slash,
        preventing concatenation issues.
        """
        config = InventoryConfig(
            base_url="https://console.test",
            api_endpoint="web/api/v2.1/xdr/assets",
            api_token="test-token",
        )

        # Leading slash should be added to api_endpoint
        assert config.api_endpoint == "/web/api/v2.1/xdr/assets"
        assert config.full_url == "https://console.test/web/api/v2.1/xdr/assets"

    def test_config_allows_modification(self) -> None:
        """Test that config allows modification after creation.

        Note: InventoryConfig now uses BaseSettings instead of frozen BaseModel,
        making it consistent with other library configurations (alerts, misconfigurations, etc.).
        """
        config = InventoryConfig(
            base_url="https://console.test",
            api_endpoint="/web/api/v2.1/xdr/assets",
            api_token="test-token",
        )

        # Modification is allowed with BaseSettings
        config.api_token = "new-token"
        assert config.api_token == "new-token"

    def test_config_different_base_urls(self) -> None:
        """Test config with different base URL formats."""
        # HTTP URL should be rejected
        with pytest.raises(ValidationError) as exc_info:
            InventoryConfig(
                base_url="http://console.test",
                api_endpoint="/api",
                api_token="token1",
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "value_error"
        assert "HTTPS" in str(errors[0]["msg"])

        # HTTPS URL with port
        config2 = InventoryConfig(
            base_url="https://console.test:8443",
            api_endpoint="/api",
            api_token="token2",
        )
        assert config2.base_url == "https://console.test:8443"

        # URL with subdomain
        config3 = InventoryConfig(
            base_url="https://us1.console.test",
            api_endpoint="/api",
            api_token="token3",
        )
        assert config3.base_url == "https://us1.console.test"

    def test_config_different_endpoints(self) -> None:
        """Test config with different API endpoint formats."""
        # Short endpoint
        config1 = InventoryConfig(
            base_url="https://console.test",
            api_endpoint="/api",
            api_token="token",
        )
        assert config1.api_endpoint == "/api"
        assert config1.full_url == "https://console.test/api"

        # Long endpoint
        config2 = InventoryConfig(
            base_url="https://console.test",
            api_endpoint="/web/api/v2.1/xdr/assets/surface/cloud",
            api_token="token",
        )
        assert config2.full_url == "https://console.test/web/api/v2.1/xdr/assets/surface/cloud"

    def test_config_with_empty_strings(self) -> None:
        """Test that empty strings are rejected by validators."""
        # Empty base_url should be rejected
        with pytest.raises(ValidationError) as exc_info:
            InventoryConfig(
                base_url="",
                api_endpoint="/api",
                api_token="token",
            )
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("base_url",) for error in errors)

        # Empty api_endpoint should be rejected
        with pytest.raises(ValidationError) as exc_info:
            InventoryConfig(
                base_url="https://console.test",
                api_endpoint="",
                api_token="token",
            )
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("api_endpoint",) for error in errors)

    def test_base_url_with_multiple_trailing_slashes(self) -> None:
        """Test that multiple trailing slashes are all stripped."""
        config = InventoryConfig(
            base_url="https://console.test///",
            api_endpoint="/api",
            api_token="token",
        )
        assert config.base_url == "https://console.test"
        assert config.full_url == "https://console.test/api"

    def test_api_endpoint_with_multiple_leading_slashes(self) -> None:
        """Test that multiple leading slashes are normalized to one."""
        config = InventoryConfig(
            base_url="https://console.test",
            api_endpoint="///api/v2.1/xdr",
            api_token="token",
        )
        assert config.api_endpoint == "/api/v2.1/xdr"
        assert config.full_url == "https://console.test/api/v2.1/xdr"

    def test_combined_trailing_and_leading_slashes(self) -> None:
        """Test normalization when both base_url and api_endpoint have slashes."""
        config = InventoryConfig(
            base_url="https://console.test//",
            api_endpoint="//api",
            api_token="token",
        )
        assert config.base_url == "https://console.test"
        assert config.api_endpoint == "/api"
        assert config.full_url == "https://console.test/api"

    def test_base_url_without_https(self) -> None:
        """Test that non-HTTPS URLs are rejected."""
        # Test with no protocol
        with pytest.raises(ValidationError) as exc_info:
            InventoryConfig(
                base_url="console.test",
                api_endpoint="/api",
                api_token="token",
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "HTTPS" in str(errors[0]["msg"])

        # Test with ftp protocol
        with pytest.raises(ValidationError) as exc_info:
            InventoryConfig(
                base_url="ftp://console.test",
                api_endpoint="/api",
                api_token="token",
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "HTTPS" in str(errors[0]["msg"])

    def test_api_endpoint_with_trailing_slashes(self) -> None:
        """Test that trailing slashes are stripped from api_endpoint.

        This prevents double slashes when building surface-specific endpoints
        like /surface/cloud, which would otherwise result in .../assets//surface/cloud
        and cause 404 errors from gateways that treat it as a different resource.
        """
        config = InventoryConfig(
            base_url="https://console.test",
            api_endpoint="/web/api/v2.1/xdr/assets/",
            api_token="token",
        )
        # Trailing slash should be stripped
        assert config.api_endpoint == "/web/api/v2.1/xdr/assets"
        assert config.full_url == "https://console.test/web/api/v2.1/xdr/assets"

        # Multiple trailing slashes should also be stripped
        config2 = InventoryConfig(
            base_url="https://console.test",
            api_endpoint="/web/api/v2.1/xdr/assets///",
            api_token="token",
        )
        assert config2.api_endpoint == "/web/api/v2.1/xdr/assets"
        assert config2.full_url == "https://console.test/web/api/v2.1/xdr/assets"


class TestInventoryConfigIntegration:
    """Integration tests for InventoryConfig with mocked client."""

    @pytest.fixture
    def mock_httpx_client(self) -> AsyncMock:
        """Create mock httpx AsyncClient."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        # Setup successful mock response
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.text = '{"data": [], "pagination": {"totalCount": 0}}'
        mock_response.json.return_value = {"data": [], "pagination": {"totalCount": 0}}

        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.post = AsyncMock(return_value=mock_response)

        return mock_client

    @pytest.mark.asyncio
    async def test_normalized_url_used_in_list_inventory(
        self, mock_httpx_client: AsyncMock
    ) -> None:
        """Test that normalized URLs are used in actual list_inventory HTTP calls."""
        # Create config with trailing slash in base_url
        config = InventoryConfig(
            base_url="https://console.test/",
            api_endpoint="/web/api/v2.1/xdr/assets",
            api_token="test-token",
        )

        # Verify normalization happened
        assert config.base_url == "https://console.test"
        assert config.full_url == "https://console.test/web/api/v2.1/xdr/assets"

        client = InventoryClient(config)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            async with client:
                await client.list_inventory()

        # Verify the correct normalized URL was used
        call_args = mock_httpx_client.get.call_args
        assert call_args[0][0] == "https://console.test/web/api/v2.1/xdr/assets"

    @pytest.mark.asyncio
    async def test_normalized_url_used_in_search_inventory(
        self, mock_httpx_client: AsyncMock
    ) -> None:
        """Test that normalized URLs are used in actual search_inventory HTTP calls."""
        # Create config without leading slash in api_endpoint
        config = InventoryConfig(
            base_url="https://console.test",
            api_endpoint="web/api/v2.1/xdr/assets",
            api_token="test-token",
        )

        # Verify normalization happened
        assert config.api_endpoint == "/web/api/v2.1/xdr/assets"
        assert config.full_url == "https://console.test/web/api/v2.1/xdr/assets"

        client = InventoryClient(config)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            async with client:
                await client.search_inventory(filters={})

        # Verify the correct normalized URL was used
        call_args = mock_httpx_client.post.call_args
        assert call_args[0][0] == "https://console.test/web/api/v2.1/xdr/assets"

    @pytest.mark.asyncio
    async def test_normalized_url_with_both_issues(self, mock_httpx_client: AsyncMock) -> None:
        """Test normalization when both base_url has trailing slash and api_endpoint lacks leading slash."""
        # Create config with both issues
        config = InventoryConfig(
            base_url="https://console.test//",
            api_endpoint="web/api/v2.1/xdr/assets",
            api_token="test-token",
        )

        # Verify normalization happened
        assert config.base_url == "https://console.test"
        assert config.api_endpoint == "/web/api/v2.1/xdr/assets"
        assert config.full_url == "https://console.test/web/api/v2.1/xdr/assets"

        client = InventoryClient(config)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            async with client:
                await client.list_inventory()
                await client.search_inventory(filters={})

        # Verify the correct normalized URL was used in both calls
        get_call_args = mock_httpx_client.get.call_args
        assert get_call_args[0][0] == "https://console.test/web/api/v2.1/xdr/assets"

        post_call_args = mock_httpx_client.post.call_args
        assert post_call_args[0][0] == "https://console.test/web/api/v2.1/xdr/assets"

    @pytest.mark.asyncio
    async def test_surface_endpoint_with_normalized_url(
        self, mock_httpx_client: AsyncMock
    ) -> None:
        """Test that surface-specific endpoints use normalized base URL."""
        from purple_mcp.libs.inventory.models import Surface

        # Create config with trailing slashes
        config = InventoryConfig(
            base_url="https://console.test///",
            api_endpoint="/web/api/v2.1/xdr/assets",
            api_token="test-token",
        )

        # Verify normalization
        assert config.base_url == "https://console.test"

        client = InventoryClient(config)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            async with client:
                await client.list_inventory(surface=Surface.CLOUD)

        # Verify the surface endpoint uses the normalized base URL
        call_args = mock_httpx_client.get.call_args
        expected_url = "https://console.test/web/api/v2.1/xdr/assets/surface/cloud"
        assert call_args[0][0] == expected_url

    @pytest.mark.asyncio
    async def test_surface_endpoint_with_trailing_slash_in_api_endpoint(
        self, mock_httpx_client: AsyncMock
    ) -> None:
        """Test that trailing slashes in api_endpoint don't cause double slashes in surface URLs.

        This regression test ensures that when api_endpoint has a trailing slash
        (e.g., /web/api/v2.1/xdr/assets/), building surface endpoints doesn't
        result in .../assets//surface/cloud which causes 404 errors.
        """
        from purple_mcp.libs.inventory.models import Surface

        # Create config with trailing slash in api_endpoint
        config = InventoryConfig(
            base_url="https://console.test",
            api_endpoint="/web/api/v2.1/xdr/assets/",
            api_token="test-token",
        )

        # Verify trailing slash was stripped
        assert config.api_endpoint == "/web/api/v2.1/xdr/assets"
        assert config.full_url == "https://console.test/web/api/v2.1/xdr/assets"

        client = InventoryClient(config)

        with patch("httpx.AsyncClient", return_value=mock_httpx_client):
            async with client:
                await client.list_inventory(surface=Surface.CLOUD)

        # Verify no double slash in the surface endpoint
        call_args = mock_httpx_client.get.call_args
        expected_url = "https://console.test/web/api/v2.1/xdr/assets/surface/cloud"
        actual_url = call_args[0][0]
        assert actual_url == expected_url
        # Explicitly verify no double slash
        assert "assets//surface" not in actual_url
