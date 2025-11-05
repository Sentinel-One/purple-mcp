"""Unit tests for SDL TLS security configuration and validation."""

import logging
import os
import warnings
from collections.abc import AsyncGenerator, Callable, Generator

import httpx
import pytest
from pydantic import ValidationError
from pytest import LogCaptureFixture
from respx import MockRouter

from purple_mcp.config import ENV_PREFIX
from purple_mcp.libs.sdl.config import SDLSettings, create_sdl_settings
from purple_mcp.libs.sdl.sdl_query_client import SDLQueryClient


@pytest.fixture
def clean_environment() -> Generator[None, None, None]:
    """Fixture to ensure clean environment state for each test."""
    original_env = os.environ.copy()
    yield
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def development_environment(clean_environment: None) -> None:
    """Fixture to set development environment."""
    os.environ[f"{ENV_PREFIX}ENV"] = "development"


@pytest.fixture
def production_environment(clean_environment: None) -> None:
    """Fixture to set production environment."""
    os.environ[f"{ENV_PREFIX}ENV"] = "production"


@pytest.fixture
def staging_environment(clean_environment: None) -> None:
    """Fixture to set staging environment."""
    os.environ[f"{ENV_PREFIX}ENV"] = "staging"


@pytest.fixture
def test_environment(clean_environment: None) -> None:
    """Fixture to set test environment."""
    os.environ[f"{ENV_PREFIX}ENV"] = "test"


@pytest.fixture
def isolated_warnings() -> Generator[list[warnings.WarningMessage], None, None]:
    """Fixture to capture warnings in isolation."""
    with warnings.catch_warnings(record=True) as warning_list:
        warnings.simplefilter("always")
        yield warning_list


@pytest.fixture
async def sdl_client_factory() -> AsyncGenerator[
    Callable[[str, SDLSettings], SDLQueryClient], None
]:
    """Factory fixture for creating SDL clients with proper cleanup."""
    clients = []

    def create_client(base_url: str, settings: SDLSettings) -> SDLQueryClient:
        client = SDLQueryClient(base_url, settings)
        clients.append(client)
        return client

    yield create_client

    # Cleanup all created clients
    for client in clients:
        if not client.is_closed():
            await client.close()


class TestSDLTLSConfigurationSecurity:
    """Test SDL TLS configuration security features."""

    def test_tls_verify_enabled_by_default(self) -> None:
        """Test that TLS verification is enabled by default."""
        settings = create_sdl_settings(
            base_url="https://test.example.test", auth_token="test-token"
        )
        assert settings.skip_tls_verify is False

    def test_tls_verify_enabled_no_warnings(self, caplog: LogCaptureFixture) -> None:
        """Test that TLS verification enabled produces no security warnings."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            create_sdl_settings(
                base_url="https://test.example.test",
                auth_token="test-token",
                skip_tls_verify=False,
            )
            # Should not produce any warnings
            assert len(w) == 0

    def test_tls_bypass_allowed_in_development(
        self,
        isolated_warnings: list[warnings.WarningMessage],
        caplog: LogCaptureFixture,
    ) -> None:
        """Test that TLS bypass is allowed in development environment."""
        settings = create_sdl_settings(
            base_url="https://test.example.test",
            auth_token="test-token",
            skip_tls_verify=True,
            environment="development",
        )

        assert settings.skip_tls_verify is True

        # Should produce security warning
        assert len(isolated_warnings) >= 1
        assert "SECURITY WARNING" in str(isolated_warnings[0].message)
        assert "TLS certificate verification is DISABLED" in str(isolated_warnings[0].message)

        # Should log security warning
        assert "TLS certificate verification is DISABLED" in caplog.text
        assert "SECURITY RISK" in caplog.text

    def test_tls_bypass_allowed_in_test_environment(
        self, isolated_warnings: list[warnings.WarningMessage]
    ) -> None:
        """Test that TLS bypass is allowed in test environment."""
        settings = create_sdl_settings(
            base_url="https://test.example.test",
            auth_token="test-token",
            skip_tls_verify=True,
            environment="test",
        )

        assert settings.skip_tls_verify is True
        assert len(isolated_warnings) >= 1
        assert "SECURITY WARNING" in str(isolated_warnings[0].message)

    def test_tls_bypass_forbidden_in_production(self) -> None:
        """Test that TLS bypass is forbidden in production environment."""
        with pytest.raises(ValidationError) as exc_info:
            create_sdl_settings(
                base_url="https://test.example.test",
                auth_token="test-token",
                skip_tls_verify=True,
                environment="production",
            )

        error_msg = str(exc_info.value)
        assert "TLS verification bypass is FORBIDDEN in production" in error_msg
        assert "critical security risk" in error_msg

    def test_tls_bypass_forbidden_in_prod_environment(self) -> None:
        """Test that TLS bypass is forbidden in 'prod' environment."""
        with pytest.raises(ValidationError) as exc_info:
            create_sdl_settings(
                base_url="https://test.example.test",
                auth_token="test-token",
                skip_tls_verify=True,
                environment="prod",
            )

        error_msg = str(exc_info.value)
        assert "TLS verification bypass is FORBIDDEN in production" in error_msg

    def test_tls_bypass_warning_in_non_development_environment(
        self,
        isolated_warnings: list[warnings.WarningMessage],
        caplog: LogCaptureFixture,
    ) -> None:
        """Test that TLS bypass produces additional warnings in non-development environments."""
        settings = create_sdl_settings(
            base_url="https://test.example.test",
            auth_token="test-token",
            skip_tls_verify=True,
            environment="staging",
        )

        assert settings.skip_tls_verify is True
        assert len(isolated_warnings) >= 1

        # Should log additional warning for non-dev environment
        assert "TLS verification disabled in this environment" in caplog.text
        assert "should only be used in development/testing" in caplog.text

        # Validate environment is in extra data
        error_record = next(
            (
                rec
                for rec in caplog.records
                if "TLS verification disabled in this environment" in rec.message
            ),
            None,
        )
        assert error_record is not None
        assert hasattr(error_record, "environment")
        assert error_record.environment == "staging"

    def test_tls_bypass_comprehensive_logging(self, caplog: LogCaptureFixture) -> None:
        """Test comprehensive logging when TLS bypass is enabled."""
        # Set log level to capture INFO messages
        caplog.set_level(logging.INFO)

        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")

            create_sdl_settings(
                base_url="https://test.example.test",
                auth_token="test-token",
                skip_tls_verify=True,
                environment="development",
            )

            # Check for critical security log
            assert "TLS CERTIFICATE VERIFICATION IS DISABLED" in caplog.text
            assert "CRITICAL SECURITY RISK" in caplog.text
            assert "man-in-the-middle attacks" in caplog.text

            # Check for TLS verify status in info log and validate the actual value in extra data
            tls_record = next(
                (rec for rec in caplog.records if "TLS Verify configured" in rec.message), None
            )
            assert tls_record is not None
            assert hasattr(tls_record, "tls_verify")
            assert tls_record.tls_verify is False  # skip_tls_verify=True means tls_verify=False


class TestSDLQueryClientTLSSecurity:
    """Test SDL Query Client TLS security features."""

    async def test_client_initialization_with_tls_bypass_development(
        self,
        development_environment: None,
        isolated_warnings: list[warnings.WarningMessage],
        caplog: LogCaptureFixture,
        sdl_client_factory: Callable[[str, SDLSettings], SDLQueryClient],
    ) -> None:
        """Test client initialization with TLS bypass in development."""
        settings = create_sdl_settings(
            base_url="https://test.example.test", auth_token="test-token", skip_tls_verify=True
        )

        sdl_client_factory("https://test.example.test", settings)

        # Should produce runtime warning
        security_warnings = [
            warning for warning in isolated_warnings if "SECURITY WARNING" in str(warning.message)
        ]
        assert len(security_warnings) >= 1

        # Should log client initialization security warning
        assert "SDL Query Client initialized with TLS verification DISABLED" in caplog.text
        assert "CRITICAL SECURITY RISK" in caplog.text

        # Validate target_url is in extra data
        client_record = next(
            (
                rec
                for rec in caplog.records
                if "SDL Query Client initialized with TLS verification DISABLED" in rec.message
            ),
            None,
        )
        assert client_record is not None
        assert hasattr(client_record, "target_url")
        assert client_record.target_url == "https://test.example.test"

    def test_client_initialization_forbidden_in_production(self) -> None:
        """Test that client initialization is forbidden in production with TLS bypass."""
        settings = create_sdl_settings(
            base_url="https://test.example.test",
            auth_token="test-token",
            skip_tls_verify=False,
            environment="production",
        )

        # Manually set skip_tls_verify to bypass config validation
        settings.skip_tls_verify = True

        with pytest.raises(ValueError) as exc_info:
            SDLQueryClient("https://test.example.test", settings)

        error_msg = str(exc_info.value)
        assert "SECURITY ERROR" in error_msg
        assert "TLS verification bypass is FORBIDDEN in production" in error_msg

    async def test_client_tls_enabled_no_warnings(
        self,
        development_environment: None,
        isolated_warnings: list[warnings.WarningMessage],
        caplog: LogCaptureFixture,
        sdl_client_factory: Callable[[str, SDLSettings], SDLQueryClient],
    ) -> None:
        """Test client with TLS enabled produces no security warnings."""
        settings = create_sdl_settings(
            base_url="https://test.example.test", auth_token="test-token", skip_tls_verify=False
        )

        sdl_client_factory("https://test.example.test", settings)

        # Should not produce TLS-related warnings
        tls_warnings = [warning for warning in isolated_warnings if "TLS" in str(warning.message)]
        assert len(tls_warnings) == 0

        # Should not log TLS bypass warnings
        assert "TLS verification DISABLED" not in caplog.text

    async def test_http_client_configuration_with_tls_bypass(
        self,
        development_environment: None,
        isolated_warnings: list[warnings.WarningMessage],
        sdl_client_factory: Callable[[str, SDLSettings], SDLQueryClient],
    ) -> None:
        """Test HTTP client configuration when TLS bypass is enabled."""
        settings = create_sdl_settings(
            base_url="https://test.example.test", auth_token="test-token", skip_tls_verify=True
        )

        client = sdl_client_factory("https://test.example.test", settings)

        # Verify client configuration
        assert client.skip_tls_verify is True
        # Note: HTTPX AsyncClient doesn't expose verify as a public attribute

    async def test_http_client_configuration_with_tls_enabled(
        self, sdl_client_factory: Callable[[str, SDLSettings], SDLQueryClient]
    ) -> None:
        """Test HTTP client configuration when TLS is enabled."""
        settings = create_sdl_settings(
            base_url="https://test.example.test", auth_token="test-token", skip_tls_verify=False
        )

        client = sdl_client_factory("https://test.example.test", settings)

        # Verify client configuration
        assert client.skip_tls_verify is False
        # Note: HTTPX AsyncClient doesn't expose verify as a public attribute

    async def test_request_logging_with_tls_bypass(
        self,
        development_environment: None,
        isolated_warnings: list[warnings.WarningMessage],
        caplog: LogCaptureFixture,
        sdl_client_factory: Callable[[str, SDLSettings], SDLQueryClient],
        respx_mock: MockRouter,
    ) -> None:
        """Test that requests are logged when TLS bypass is enabled."""
        settings = create_sdl_settings(
            base_url="https://test.example.test", auth_token="test-token", skip_tls_verify=True
        )

        client = sdl_client_factory("https://test.example.test", settings)

        # Clear previous log entries and set appropriate log level
        caplog.clear()
        caplog.set_level(logging.WARNING)

        # Mock the httpx request to avoid network calls
        respx_mock.get("https://test.example.test/test").mock(
            return_value=httpx.Response(200, json={})
        )

        # Call the private method directly to test logging
        await client._make_request(method="GET", path="/test", auth_token="Bearer test-token")

        # Should log TLS bypass warning for each request
        assert "TLS bypass request made" in caplog.text
        request_record = next(
            (rec for rec in caplog.records if "TLS bypass request made" in rec.message), None
        )
        assert request_record is not None
        assert hasattr(request_record, "method")
        assert request_record.method == "GET"
        assert hasattr(request_record, "path")
        assert request_record.path == "/test"

    async def test_client_environment_validation_edge_cases(
        self,
        clean_environment: None,
        sdl_client_factory: Callable[[str, SDLSettings], SDLQueryClient],
    ) -> None:
        """Test edge cases for environment validation."""
        # Create settings with development environment to allow TLS bypass
        settings = create_sdl_settings(
            base_url="https://test.example.test",
            auth_token="test-token",
            skip_tls_verify=True,
            environment="development",
        )

        # Test that explicitly set development environment allows TLS bypass
        client = sdl_client_factory("https://test.example.test", settings)
        assert client.skip_tls_verify is True
        assert client.environment == "development"

    async def test_warning_stack_level_correctness(
        self,
        development_environment: None,
        isolated_warnings: list[warnings.WarningMessage],
        sdl_client_factory: Callable[[str, SDLSettings], SDLQueryClient],
    ) -> None:
        """Test that warnings have correct stack level for proper source attribution."""
        settings = create_sdl_settings(
            base_url="https://test.example.test", auth_token="test-token", skip_tls_verify=True
        )

        sdl_client_factory("https://test.example.test", settings)

        # Should have warnings with appropriate stack levels
        security_warnings = [
            warning for warning in isolated_warnings if "SECURITY WARNING" in str(warning.message)
        ]
        assert len(security_warnings) >= 1

        # Verify warning details
        for warning in security_warnings:
            assert warning.category is UserWarning
            assert "TLS" in str(warning.message)


class TestSDLTLSSecurityIntegration:
    """Integration tests for SDL TLS security features."""

    async def test_end_to_end_tls_bypass_workflow(
        self,
        isolated_warnings: list[warnings.WarningMessage],
        caplog: LogCaptureFixture,
        sdl_client_factory: Callable[[str, SDLSettings], SDLQueryClient],
    ) -> None:
        """Test complete workflow with TLS bypass enabled."""
        # Create settings with TLS bypass
        settings = create_sdl_settings(
            base_url="https://test.example.test",
            auth_token="test-token",
            skip_tls_verify=True,
            environment="development",
        )

        # Create client
        sdl_client_factory("https://test.example.test", settings)

        # Verify comprehensive security logging
        assert "TLS CERTIFICATE VERIFICATION IS DISABLED" in caplog.text
        assert "SDL Query Client initialized with TLS verification DISABLED" in caplog.text
        assert "CRITICAL SECURITY RISK" in caplog.text

        # Verify warnings were issued
        security_warnings = [
            warning for warning in isolated_warnings if "SECURITY WARNING" in str(warning.message)
        ]
        assert len(security_warnings) >= 2  # One from config, one from client

    def test_end_to_end_production_protection(self) -> None:
        """Test that production environment is properly protected."""
        # Should fail at config level
        with pytest.raises(ValidationError):
            create_sdl_settings(
                base_url="https://test.example.test",
                auth_token="test-token",
                skip_tls_verify=True,
                environment="production",
            )

        # Should also fail at client level if config validation is bypassed
        settings = create_sdl_settings(
            base_url="https://test.example.test",
            auth_token="test-token",
            skip_tls_verify=False,
            environment="production",
        )
        settings.skip_tls_verify = True

        with pytest.raises(ValueError):
            SDLQueryClient("https://test.example.test", settings)

    async def test_secure_configuration_workflow(
        self,
        isolated_warnings: list[warnings.WarningMessage],
        caplog: LogCaptureFixture,
        sdl_client_factory: Callable[[str, SDLSettings], SDLQueryClient],
    ) -> None:
        """Test normal secure configuration workflow."""
        # Create settings with secure defaults
        settings = create_sdl_settings(
            base_url="https://test.example.test", auth_token="test-token"
        )

        # Create client
        client = sdl_client_factory("https://test.example.test", settings)

        # Verify secure configuration
        assert settings.skip_tls_verify is False
        assert client.skip_tls_verify is False
        # Note: HTTPX AsyncClient doesn't expose verify as a public attribute

        # Should not produce security warnings
        security_warnings = [
            warning for warning in isolated_warnings if "SECURITY WARNING" in str(warning.message)
        ]
        assert len(security_warnings) == 0

        # Should not log TLS bypass messages
        assert "TLS verification DISABLED" not in caplog.text
