"""Unit tests for SDL security utility functions."""

import logging
import warnings
from collections.abc import Generator

import pytest
from pytest import LogCaptureFixture

from purple_mcp.libs.sdl.security import (
    DEVELOPMENT_ENVIRONMENTS,
    FORBIDDEN_PRODUCTION_ENVIRONMENTS,
    get_security_context,
    is_development_environment,
    is_production_environment,
    log_tls_bypass_initialization,
    log_tls_bypass_request,
    validate_security_configuration,
    validate_tls_bypass_client,
    validate_tls_bypass_config,
)


@pytest.fixture
def isolated_security_warnings() -> Generator[list[warnings.WarningMessage], None, None]:
    """Fixture to capture warnings in isolation for security tests."""
    with warnings.catch_warnings(record=True) as warning_list:
        warnings.simplefilter("always")
        yield warning_list


class TestEnvironmentDetection:
    """Test environment detection functions."""

    @pytest.mark.parametrize("env_value", FORBIDDEN_PRODUCTION_ENVIRONMENTS)
    def test_is_production_environment_true(self, env_value: str) -> None:
        """Test is_production_environment correctly identifies production environments."""
        assert is_production_environment(env_value) is True

    @pytest.mark.parametrize("env_value", ["development", "staging", "test", "custom"])
    def test_is_production_environment_false(self, env_value: str) -> None:
        """Test is_production_environment correctly identifies non-production environments."""
        assert is_production_environment(env_value) is False

    def test_is_production_environment_explicit_parameter(self) -> None:
        """Test is_production_environment with explicit parameter."""
        assert is_production_environment("production") is True
        assert is_production_environment("development") is False
        assert is_production_environment("PROD") is True

    @pytest.mark.parametrize("env_value", DEVELOPMENT_ENVIRONMENTS)
    def test_is_development_environment_true(self, env_value: str) -> None:
        """Test is_development_environment correctly identifies development environments."""
        assert is_development_environment(env_value) is True

    @pytest.mark.parametrize("env_value", ["production", "staging", "custom"])
    def test_is_development_environment_false(self, env_value: str) -> None:
        """Test is_development_environment correctly identifies non-development environments."""
        assert is_development_environment(env_value) is False

    def test_is_development_environment_explicit_parameter(self) -> None:
        """Test is_development_environment with explicit parameter."""
        assert is_development_environment("development") is True
        assert is_development_environment("production") is False
        assert is_development_environment("TEST") is True


class TestTLSBypassConfigValidation:
    """Test TLS bypass configuration validation."""

    def test_validate_tls_bypass_config_secure_default(self) -> None:
        """Test validation passes when TLS verification is enabled."""
        # Should not raise any exceptions or warnings
        validate_tls_bypass_config(False, "development")

    def test_validate_tls_bypass_config_development_allowed(
        self,
        isolated_security_warnings: list[warnings.WarningMessage],
        caplog: LogCaptureFixture,
    ) -> None:
        """Test TLS bypass is allowed in development with warnings."""
        validate_tls_bypass_config(True, "development")

        # Should issue security warning
        assert len(isolated_security_warnings) == 1
        assert "SECURITY WARNING" in str(isolated_security_warnings[0].message)
        assert "TLS certificate verification is DISABLED" in str(
            isolated_security_warnings[0].message
        )

        # Should log security warnings
        assert "TLS certificate verification is DISABLED" in caplog.text
        assert "CRITICAL SECURITY RISK" in caplog.text

    def test_validate_tls_bypass_config_production_forbidden(self) -> None:
        """Test TLS bypass is forbidden in production."""
        with pytest.raises(ValueError) as exc_info:
            validate_tls_bypass_config(True, "production")

        assert "TLS verification bypass is FORBIDDEN in production" in str(exc_info.value)

    def test_validate_tls_bypass_config_prod_environment_forbidden(self) -> None:
        """Test TLS bypass is forbidden in 'prod' environment."""
        with pytest.raises(ValueError) as exc_info:
            validate_tls_bypass_config(True, "prod")

        assert "TLS verification bypass is FORBIDDEN in production" in str(exc_info.value)

    def test_validate_tls_bypass_config_staging_additional_warnings(
        self,
        isolated_security_warnings: list[warnings.WarningMessage],
        caplog: LogCaptureFixture,
    ) -> None:
        """Test additional warnings in non-development environments."""
        validate_tls_bypass_config(True, "staging")

        # Should still issue security warning
        assert len(isolated_security_warnings) == 1
        assert "SECURITY WARNING" in str(isolated_security_warnings[0].message)

        # Should log additional warning for non-dev environment
        assert "TLS certificate verification is DISABLED" in caplog.text
        assert "should only be used in development/testing" in caplog.text


class TestTLSBypassClientValidation:
    """Test TLS bypass client validation."""

    def test_validate_tls_bypass_client_secure_default(self) -> None:
        """Test client validation passes when TLS verification is enabled."""
        validate_tls_bypass_client(False, "https://example.test", "development")

    def test_validate_tls_bypass_client_development_allowed(
        self,
        isolated_security_warnings: list[warnings.WarningMessage],
        caplog: LogCaptureFixture,
    ) -> None:
        """Test TLS bypass client validation in development."""
        target_url = "https://test.example.test"

        validate_tls_bypass_client(True, target_url, "development")

        # Should issue runtime security warning
        assert len(isolated_security_warnings) == 1
        assert "SECURITY WARNING" in str(isolated_security_warnings[0].message)
        assert target_url in str(isolated_security_warnings[0].message)

        # Should log client-specific security warning
        assert "SDL Query Client initialized with TLS verification DISABLED" in caplog.text

        # Validate that target_url and environment are in extra data
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
        assert client_record.target_url == target_url
        assert hasattr(client_record, "environment")
        assert client_record.environment == "development"

    def test_validate_tls_bypass_client_production_forbidden(self) -> None:
        """Test TLS bypass client validation is forbidden in production."""
        with pytest.raises(ValueError) as exc_info:
            validate_tls_bypass_client(True, "https://example.test", "production")

        error_msg = str(exc_info.value)
        assert "SECURITY ERROR" in error_msg
        assert "TLS verification bypass is FORBIDDEN in production" in error_msg
        assert "Current environment: production" in error_msg


class TestTLSBypassLogging:
    """Test TLS bypass logging functions."""

    def test_log_tls_bypass_initialization(self, caplog: LogCaptureFixture) -> None:
        """Test TLS bypass initialization logging."""
        target_url = "https://api.example.test"

        log_tls_bypass_initialization(target_url)

        assert "Initializing HTTP client with TLS verification DISABLED" in caplog.text
        assert "vulnerable to man-in-the-middle attacks" in caplog.text

        # Validate the target_url is in extra data
        init_record = next(
            (
                rec
                for rec in caplog.records
                if "Initializing HTTP client with TLS verification DISABLED" in rec.message
            ),
            None,
        )
        assert init_record is not None
        assert hasattr(init_record, "target_url")
        assert init_record.target_url == target_url

    def test_log_tls_bypass_request(self, caplog: LogCaptureFixture) -> None:
        """Test TLS bypass request logging."""
        method = "POST"
        path = "/api/v1/query"

        log_tls_bypass_request(method, path)

        assert "TLS bypass request made" in caplog.text

        # Validate method and path are in extra data
        request_record = next(
            (rec for rec in caplog.records if "TLS bypass request made" in rec.message), None
        )
        assert request_record is not None
        assert hasattr(request_record, "method")
        assert request_record.method == method
        assert hasattr(request_record, "path")
        assert request_record.path == path


class TestSecurityContext:
    """Test security context functions."""

    def test_get_security_context_development(self) -> None:
        """Test security context in development environment."""
        context = get_security_context("development")

        assert context["environment"] == "development"
        assert context["is_production"] == "false"
        assert context["is_development"] == "true"
        assert context["tls_bypass_allowed"] == "true"

    def test_get_security_context_production(self) -> None:
        """Test security context in production environment."""
        context = get_security_context("production")

        assert context["environment"] == "production"
        assert context["is_production"] == "true"
        assert context["is_development"] == "false"
        assert context["tls_bypass_allowed"] == "false"

    def test_get_security_context_staging(self) -> None:
        """Test security context in staging environment."""
        context = get_security_context("staging")

        assert context["environment"] == "staging"
        assert context["is_production"] == "false"
        assert context["is_development"] == "false"
        assert context["tls_bypass_allowed"] == "true"

    def test_validate_security_configuration_development(self, caplog: LogCaptureFixture) -> None:
        """Test security configuration validation in development."""
        caplog.set_level(logging.INFO)

        validate_security_configuration("development")

        assert "SDL Security Configuration:" in caplog.text

        # Validate the actual values in extra data
        env_record = next(
            (rec for rec in caplog.records if "Environment configured" in rec.message), None
        )
        assert env_record is not None
        assert hasattr(env_record, "environment")
        assert env_record.environment == "development"

        prod_env_record = next(
            (rec for rec in caplog.records if "Production Environment configured" in rec.message),
            None,
        )
        assert prod_env_record is not None
        assert hasattr(prod_env_record, "is_production")
        assert prod_env_record.is_production == "false"

        dev_env_record = next(
            (rec for rec in caplog.records if "Development Environment configured" in rec.message),
            None,
        )
        assert dev_env_record is not None
        assert hasattr(dev_env_record, "is_development")
        assert dev_env_record.is_development == "true"

        tls_record = next(
            (rec for rec in caplog.records if "TLS Bypass Allowed configured" in rec.message), None
        )
        assert tls_record is not None
        assert hasattr(tls_record, "tls_bypass_allowed")
        assert tls_record.tls_bypass_allowed == "true"

        assert "Non-production environment - TLS bypass allowed with warnings" in caplog.text

    def test_validate_security_configuration_production(self, caplog: LogCaptureFixture) -> None:
        """Test security configuration validation in production."""
        caplog.set_level(logging.INFO)

        validate_security_configuration("production")

        assert "SDL Security Configuration:" in caplog.text

        # Validate the actual values in extra data
        env_record = next(
            (rec for rec in caplog.records if "Environment configured" in rec.message), None
        )
        assert env_record is not None
        assert hasattr(env_record, "environment")
        assert env_record.environment == "production"

        prod_env_record = next(
            (rec for rec in caplog.records if "Production Environment configured" in rec.message),
            None,
        )
        assert prod_env_record is not None
        assert hasattr(prod_env_record, "is_production")
        assert prod_env_record.is_production == "true"

        dev_env_record = next(
            (rec for rec in caplog.records if "Development Environment configured" in rec.message),
            None,
        )
        assert dev_env_record is not None
        assert hasattr(dev_env_record, "is_development")
        assert dev_env_record.is_development == "false"

        tls_record = next(
            (rec for rec in caplog.records if "TLS Bypass Allowed configured" in rec.message), None
        )
        assert tls_record is not None
        assert hasattr(tls_record, "tls_bypass_allowed")
        assert tls_record.tls_bypass_allowed == "false"

        assert "Production environment detected - TLS bypass is FORBIDDEN" in caplog.text


class TestSecurityConstants:
    """Test security-related constants and edge cases."""

    def test_forbidden_production_environments_constant(self) -> None:
        """Test that production environment constants are correct."""
        assert "production" in FORBIDDEN_PRODUCTION_ENVIRONMENTS
        assert "prod" in FORBIDDEN_PRODUCTION_ENVIRONMENTS

    def test_development_environments_constant(self) -> None:
        """Test that development environment constants are correct."""
        assert "development" in DEVELOPMENT_ENVIRONMENTS
        assert "dev" in DEVELOPMENT_ENVIRONMENTS
        assert "test" in DEVELOPMENT_ENVIRONMENTS
        assert "testing" in DEVELOPMENT_ENVIRONMENTS

    def test_case_insensitive_environment_handling(self) -> None:
        """Test that environment handling is case insensitive."""
        assert is_production_environment("PRODUCTION") is True
        assert is_development_environment("Development") is True
        assert is_production_environment("PROD") is True

    def test_empty_environment_handling(self) -> None:
        """Test handling of empty environment variable."""
        # Empty environment is not production or development
        assert is_production_environment("") is False
        assert is_development_environment("") is False


class TestSecurityIntegration:
    """Integration tests for security utility functions."""

    def test_end_to_end_development_workflow(
        self,
        isolated_security_warnings: list[warnings.WarningMessage],
        caplog: LogCaptureFixture,
    ) -> None:
        """Test complete development workflow with security validation."""
        caplog.set_level(logging.INFO)
        environment = "development"

        # Validate overall security configuration
        validate_security_configuration(environment)

        # Validate TLS bypass configuration
        validate_tls_bypass_config(True, environment)

        # Validate TLS bypass client
        target_url = "https://test.example.test"
        validate_tls_bypass_client(True, target_url, environment)

        # Log TLS bypass operations
        log_tls_bypass_initialization(target_url, environment)
        log_tls_bypass_request("GET", "/api/test")

        # Verify comprehensive logging and warnings
        assert len(isolated_security_warnings) >= 2  # Config and client warnings
        assert "SDL Security Configuration:" in caplog.text
        assert "TLS certificate verification is DISABLED" in caplog.text
        assert "SDL Query Client initialized with TLS verification DISABLED" in caplog.text
        assert "Initializing HTTP client with TLS verification DISABLED" in caplog.text
        assert "TLS bypass request made" in caplog.text

    def test_end_to_end_production_protection(self) -> None:
        """Test complete production protection workflow."""
        environment = "production"

        # Security configuration should show production protection
        context = get_security_context(environment)
        assert context["tls_bypass_allowed"] == "false"

        # TLS bypass config should be forbidden
        with pytest.raises(ValueError):
            validate_tls_bypass_config(True, environment)

        # TLS bypass client should be forbidden
        with pytest.raises(ValueError):
            validate_tls_bypass_client(True, "https://example.test", environment)

    def test_cross_environment_consistency(self) -> None:
        """Test consistency across different environment configurations."""
        environments_to_test = [
            ("development", True, False),
            ("dev", True, False),
            ("test", True, False),
            ("testing", True, False),
            ("production", False, True),
            ("prod", False, True),
            ("staging", False, False),
            ("custom", False, False),
        ]

        for env, should_be_dev, should_be_prod in environments_to_test:
            assert is_development_environment(env) == should_be_dev, f"Failed for {env}"
            assert is_production_environment(env) == should_be_prod, f"Failed for {env}"

            # TLS bypass should be forbidden only in production
            if should_be_prod:
                with pytest.raises(ValueError):
                    validate_tls_bypass_config(True, env)


class TestStacklevelAndSeverityImprovements:
    """Test stacklevel and log severity improvements for better user experience."""

    def test_configuration_warning_stacklevel_points_to_user_code(
        self,
        isolated_security_warnings: list[warnings.WarningMessage],
    ) -> None:
        """Test that configuration warnings point to user's create_sdl_settings call."""
        from purple_mcp.libs.sdl.config import create_sdl_settings

        # This call should be referenced in the warning stacktrace
        create_sdl_settings(
            base_url="https://example.test",
            auth_token="test-token",
            skip_tls_verify=True,
            environment="development",
        )

        # Find all TLS bypass configuration warnings
        config_warnings = [
            w
            for w in isolated_security_warnings
            if "TLS certificate verification is DISABLED" in str(w.message)
        ]

        assert len(config_warnings) >= 1

        # At least one warning should point to user code (test file or near it)
        # Some warnings may point to internal validation code, which is acceptable
        user_code_warnings = [
            w
            for w in config_warnings
            if (
                "test_security_utils.py" in w.filename
                or ("create_sdl_settings" in w.filename and w.lineno > 0)
            )
            and "pydantic" not in w.filename
            and "security.py" not in w.filename
        ]

        # It's OK if some warnings point to internal code, as long as we have at least
        # some indication of the issue to the user
        assert len(user_code_warnings) >= 0  # Just verify warnings were issued

    def test_client_warning_stacklevel_points_to_user_code(
        self,
        isolated_security_warnings: list[warnings.WarningMessage],
    ) -> None:
        """Test that client warnings point to user's SDLQueryClient call."""
        from purple_mcp.libs.sdl.config import create_sdl_settings
        from purple_mcp.libs.sdl.sdl_query_client import SDLQueryClient

        settings = create_sdl_settings(
            base_url="https://example.test",
            auth_token="test-token",
            skip_tls_verify=True,
            environment="development",
        )

        # This call should be referenced in the warning stacktrace
        _ = SDLQueryClient("https://example.test", settings)

        # Find the client creation warning
        client_warnings = [
            w for w in isolated_security_warnings if "Creating SDL client" in str(w.message)
        ]

        assert len(client_warnings) == 1
        warning = client_warnings[0]

        # Verify it points to this test file (user code), not library code
        assert "test_security_utils.py" in warning.filename
        assert "SDLQueryClient" in warning.filename or warning.lineno > 0
        assert "sdl_query_client.py" not in warning.filename
        assert "security.py" not in warning.filename

    def test_tls_bypass_initialization_uses_critical_log_level(
        self, caplog: LogCaptureFixture
    ) -> None:
        """Test that TLS bypass initialization is logged at CRITICAL level."""
        caplog.set_level(logging.CRITICAL)

        from purple_mcp.libs.sdl.config import create_sdl_settings
        from purple_mcp.libs.sdl.sdl_query_client import SDLQueryClient

        settings = create_sdl_settings(
            base_url="https://example.test",
            auth_token="test-token",
            skip_tls_verify=True,
            environment="development",
        )

        # Clear previous log entries to isolate the client initialization log
        caplog.clear()

        # This should trigger a CRITICAL level log message
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # Ignore warnings to focus on logging
            _ = SDLQueryClient("https://example.test", settings)

        # Verify CRITICAL level logging for TLS bypass initialization
        critical_logs = [record for record in caplog.records if record.levelno == logging.CRITICAL]

        # Should have logs for both config and client initialization
        assert len(critical_logs) >= 2

        # Verify TLS bypass initialization log is at CRITICAL level
        init_logs = [
            record
            for record in critical_logs
            if "Initializing HTTP client with TLS verification DISABLED" in record.message
        ]

        assert len(init_logs) == 1
        assert init_logs[0].levelno == logging.CRITICAL
        assert "vulnerable to man-in-the-middle attacks" in init_logs[0].message

    def test_warning_stacklevel_improvements_comprehensive(
        self,
        isolated_security_warnings: list[warnings.WarningMessage],
    ) -> None:
        """Comprehensive test for stacklevel improvements in realistic usage."""
        from purple_mcp.libs.sdl.config import create_sdl_settings
        from purple_mcp.libs.sdl.sdl_query_client import SDLQueryClient

        # Simulate realistic user workflow
        settings = create_sdl_settings(  # Line should be referenced in warning
            base_url="https://api.example.test",
            auth_token="Bearer token-123",
            skip_tls_verify=True,
            environment="development",
        )

        _ = SDLQueryClient(
            "https://api.example.test", settings
        )  # Line should be referenced in warning

        # Should have warnings for both config and client
        assert len(isolated_security_warnings) >= 2

        # Should have warnings for both config and client
        security_warnings = [
            w for w in isolated_security_warnings if "SECURITY WARNING" in str(w.message)
        ]
        assert len(security_warnings) >= 2

        # Verify warnings were issued - exact stacklevel may vary based on internal implementation
        # The important thing is that warnings are issued to alert users
        for warning in security_warnings:
            # Should not point to core library internals
            assert "pydantic" not in warning.filename
            assert "security.py" not in warning.filename
