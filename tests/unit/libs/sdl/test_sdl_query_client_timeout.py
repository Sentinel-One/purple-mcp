"""Unit tests for SDLQueryClient timeout configuration.

These tests verify that the httpx client is properly configured with
max_timeout_seconds for long-running read/write operations and http_timeout
for connection/pool timeouts.
"""

from collections.abc import AsyncGenerator

import pytest

from purple_mcp.libs.sdl import SDLQueryClient, create_sdl_settings
from purple_mcp.libs.sdl.config import SDLSettings


@pytest.fixture
def sdl_settings() -> SDLSettings:
    """Create test SDL settings."""
    return create_sdl_settings(
        base_url="https://test.example.test/sdl",
        auth_token="Bearer test-token",
        http_timeout=10,
        max_timeout_seconds=60,
        http_max_retries=3,
    )


@pytest.fixture
def custom_timeout_settings() -> SDLSettings:
    """Create SDL settings with custom timeout values."""
    return create_sdl_settings(
        base_url="https://test.example.test/sdl",
        auth_token="Bearer test-token",
        http_timeout=5,
        max_timeout_seconds=120,
        http_max_retries=2,
    )


@pytest.fixture
async def client(sdl_settings: SDLSettings) -> AsyncGenerator[SDLQueryClient, None]:
    """Yield an SDLQueryClient that closes after the test."""
    client = SDLQueryClient("https://test.example.test/sdl", sdl_settings)
    try:
        yield client
    finally:
        if not client.is_closed():
            await client.close()


@pytest.fixture
async def custom_client(
    custom_timeout_settings: SDLSettings,
) -> AsyncGenerator[SDLQueryClient, None]:
    """Yield an SDLQueryClient with custom settings that closes after the test."""
    client = SDLQueryClient("https://test.example.test/sdl", custom_timeout_settings)
    try:
        yield client
    finally:
        if not client.is_closed():
            await client.close()


class TestSDLQueryClientTimeoutConfiguration:
    """Test suite for httpx timeout configuration."""

    def test_timeout_uses_max_timeout_seconds_for_read(self, client: SDLQueryClient) -> None:
        """Test that read timeout uses max_timeout_seconds, not http_timeout."""
        assert client.http_client is not None
        timeout = client.http_client.timeout

        # Read timeout should use max_timeout_seconds (60s)
        assert timeout.read == 60.0
        # Should NOT use http_timeout for read
        assert timeout.read != 10.0

    def test_timeout_uses_max_timeout_seconds_for_write(self, client: SDLQueryClient) -> None:
        """Test that write timeout uses max_timeout_seconds, not http_timeout."""
        assert client.http_client is not None
        timeout = client.http_client.timeout

        # Write timeout should use max_timeout_seconds (60s)
        assert timeout.write == 60.0
        # Should NOT use http_timeout for write
        assert timeout.write != 10.0

    def test_timeout_uses_http_timeout_for_connect(self, client: SDLQueryClient) -> None:
        """Test that connect timeout uses http_timeout."""
        assert client.http_client is not None
        timeout = client.http_client.timeout

        # Connect timeout should use http_timeout (10s)
        assert timeout.connect == 10.0

    def test_timeout_uses_http_timeout_for_pool(self, client: SDLQueryClient) -> None:
        """Test that pool timeout uses http_timeout."""
        assert client.http_client is not None
        timeout = client.http_client.timeout

        # Pool timeout should use http_timeout (10s)
        assert timeout.pool == 10.0

    def test_timeout_configuration_with_custom_values(self, custom_client: SDLQueryClient) -> None:
        """Test timeout configuration with different custom values."""
        assert custom_client.http_client is not None
        timeout = custom_client.http_client.timeout

        # Verify custom values are applied correctly
        assert timeout.connect == 5.0  # http_timeout
        assert timeout.read == 120.0  # max_timeout_seconds
        assert timeout.write == 120.0  # max_timeout_seconds
        assert timeout.pool == 5.0  # http_timeout

    def test_timeout_all_parameters_set_explicitly(self, client: SDLQueryClient) -> None:
        """Test that all four timeout parameters are set (not using default)."""
        assert client.http_client is not None
        timeout = client.http_client.timeout

        # All four parameters should be set explicitly
        assert timeout.connect is not None
        assert timeout.read is not None
        assert timeout.write is not None
        assert timeout.pool is not None

    def test_long_running_queries_wont_timeout_prematurely(
        self, client: SDLQueryClient, sdl_settings: SDLSettings
    ) -> None:
        """Test that long-running read operations can exceed http_timeout.

        This test verifies the fix for the bug where http_timeout was used
        for all operations, causing long-running queries to timeout prematurely.
        """
        # Settings: http_timeout=10s, max_timeout_seconds=60s
        assert client.http_client is not None
        timeout = client.http_client.timeout

        # Read operations can run up to 60 seconds (max_timeout_seconds)
        # not just 10 seconds (http_timeout)
        assert timeout.read == 60.0
        assert timeout.read > sdl_settings.http_timeout

        # This ensures queries that take longer than http_timeout
        # but less than max_timeout_seconds won't fail
        assert timeout.read == sdl_settings.max_timeout_seconds

    def test_client_attributes_match_settings(
        self, client: SDLQueryClient, sdl_settings: SDLSettings
    ) -> None:
        """Test that client instance variables match the provided settings."""
        # Verify client attributes are set correctly
        assert client.http_timeout == sdl_settings.http_timeout
        assert client.max_timeout_seconds == sdl_settings.max_timeout_seconds

    def test_timeout_prevents_infinite_wait(self, client: SDLQueryClient) -> None:
        """Test that timeouts are set and not infinite."""
        assert client.http_client is not None
        timeout = client.http_client.timeout

        # None of the timeouts should be None (infinite)
        assert timeout.connect is not None
        assert timeout.read is not None
        assert timeout.write is not None
        assert timeout.pool is not None

        # All timeouts should be positive values
        assert timeout.connect > 0
        assert timeout.read > 0
        assert timeout.write > 0
        assert timeout.pool > 0


class TestTimeoutConfigurationRegression:
    """Regression tests to prevent timeout configuration bugs."""

    def test_regression_max_timeout_seconds_not_ignored(self, sdl_settings: SDLSettings) -> None:
        """Regression test: max_timeout_seconds must be used for read/write.

        Previously, the client was configured with:
            timeout=httpx.Timeout(timeout=self.http_timeout)

        This caused max_timeout_seconds to be ignored, making long-running
        queries timeout prematurely at http_timeout seconds.
        """
        # Create settings with clearly different values
        settings = create_sdl_settings(
            base_url="https://test.example.test/sdl",
            auth_token="Bearer test-token",
            http_timeout=5,  # Short timeout for connections
            max_timeout_seconds=300,  # Long timeout for operations (5 minutes)
        )

        client = SDLQueryClient("https://test.example.test/sdl", settings)

        try:
            timeout = client.http_client.timeout

            # This would fail with the old bug where http_timeout was used for everything
            assert timeout.read == 300.0, (
                "REGRESSION: read timeout using http_timeout instead of max_timeout_seconds! "
                "This will cause long-running queries to fail."
            )

            assert timeout.write == 300.0, (
                "REGRESSION: write timeout using http_timeout instead of max_timeout_seconds!"
            )

            # Connect and pool should use the shorter http_timeout
            assert timeout.connect == 5.0
            assert timeout.pool == 5.0
        finally:
            if not client.is_closed():
                import asyncio

                asyncio.run(client.close())

    def test_regression_all_timeout_parameters_must_be_set(self, client: SDLQueryClient) -> None:
        """Regression test: httpx.Timeout requires all parameters or a default.

        Previously, only connect, read, and write were set, which caused:
        ValueError: httpx.Timeout must either include a default,
                    or set all four parameters explicitly.
        """
        # This should not raise ValueError
        timeout = client.http_client.timeout

        # Verify all four required parameters are set
        assert hasattr(timeout, "connect")
        assert hasattr(timeout, "read")
        assert hasattr(timeout, "write")
        assert hasattr(timeout, "pool")

        # All should have actual values
        assert timeout.connect is not None
        assert timeout.read is not None
        assert timeout.write is not None
        assert timeout.pool is not None
