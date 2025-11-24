"""Tests for purple_mcp.cli module.

This module tests the CLI interface, command-line argument parsing,
configuration validation, and server startup in different modes.
"""

import os
from collections.abc import Generator
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from purple_mcp.cli import _run_mode, main
from purple_mcp.config import ENV_PREFIX


@pytest.fixture(autouse=True)
def _isolate_cli_environment() -> Generator[None, None, None]:
    """Isolate CLI tests from environment pollution.

    This fixture ensures that CLI tests which call _apply_environment_overrides
    (or otherwise mutate os.environ) do not leak state to other tests running
    in the same xdist worker. It:

    1. Saves the current environment state
    2. Clears the Settings cache before the test
    3. Yields control to the test
    4. Restores the environment to its original state
    5. Clears the Settings cache again to prevent cached pollution

    This prevents issues where CLI tests set PURPLEMCP_CONSOLE_GRAPHQL_ENDPOINT
    (or other env vars) and subsequent tests (like TestPurpleAIRealClient) pick
    up those values from the cached Settings instance.
    """
    from purple_mcp.config import get_settings

    # Save original environment
    original_env = os.environ.copy()

    # Clear settings cache before test to ensure fresh settings
    get_settings.cache_clear()

    try:
        yield
    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)

        # Clear settings cache after test to prevent pollution
        get_settings.cache_clear()


class TestCLIArgumentParsing:
    """Tests for command-line argument parsing and validation."""

    def test_default_options(self) -> None:
        """Test CLI with default options."""
        runner = CliRunner()

        with (
            patch("purple_mcp.cli.Settings") as mock_settings,
            patch("purple_mcp.server.app") as mock_app,
        ):
            # Mock successful configuration
            mock_settings.return_value = Mock()
            mock_settings.return_value.graphql_full_url = "https://test.test/graphql"

            result = runner.invoke(main, [])

            # Should attempt to start in stdio mode (default)
            mock_app.run.assert_called_once_with(transport="stdio", show_banner=False)
            assert result.exit_code == 0

    def test_sse_mode_options(self) -> None:
        """Test CLI with SSE mode and custom host/port."""
        runner = CliRunner()

        with (
            patch("purple_mcp.cli.Settings") as mock_settings,
            patch("purple_mcp.cli.uvicorn.run") as mock_uvicorn,
            patch("purple_mcp.server.app") as mock_app,
        ):
            # Mock successful configuration
            mock_settings.return_value = Mock()
            mock_settings.return_value.graphql_full_url = "https://test.test/graphql"
            mock_app.http_app.return_value = Mock()

            result = runner.invoke(
                main,
                [
                    "--mode",
                    "sse",
                    "--host",
                    "0.0.0.0",
                    "--port",
                    "9000",
                    "--allow-remote-access",
                ],
            )

            # Should start uvicorn with SSE transport
            mock_uvicorn.assert_called_once()
            call_args = mock_uvicorn.call_args
            assert call_args[1]["host"] == "0.0.0.0"
            assert call_args[1]["port"] == 9000
            assert call_args[1]["log_level"] == "warning"

            mock_app.http_app.assert_called_once_with(transport="sse", stateless_http=False)
            assert result.exit_code == 0

    def test_streamable_http_mode_options(self) -> None:
        """Test CLI with streamable-http mode."""
        runner = CliRunner()

        with (
            patch("purple_mcp.cli.Settings") as mock_settings,
            patch("purple_mcp.cli.uvicorn.run") as mock_uvicorn,
            patch("purple_mcp.server.app") as mock_app,
        ):
            # Mock successful configuration
            mock_settings.return_value = Mock()
            mock_settings.return_value.graphql_full_url = "https://test.test/graphql"
            mock_app.http_app.return_value = Mock()

            result = runner.invoke(
                main,
                [
                    "--mode",
                    "streamable-http",
                    "--host",
                    "localhost",
                    "--port",
                    "8080",
                    "--verbose",
                ],
            )

            # Should start uvicorn with streamable-http transport
            mock_uvicorn.assert_called_once()
            call_args = mock_uvicorn.call_args
            assert call_args[1]["host"] == "localhost"
            assert call_args[1]["port"] == 8080
            assert call_args[1]["log_level"] == "info"  # verbose mode

            mock_app.http_app.assert_called_once_with(transport="streamable-http", stateless_http=False)
            assert result.exit_code == 0

    def test_verbose_logging_setup(self) -> None:
        """Test verbose logging configuration."""
        runner = CliRunner()

        with (
            patch("purple_mcp.cli.Settings") as mock_settings,
            patch("purple_mcp.server.app") as _,
            patch("logging.basicConfig") as mock_logging,
        ):
            # Mock successful configuration
            mock_settings.return_value = Mock()
            mock_settings.return_value.graphql_full_url = "https://test.test/graphql"

            result = runner.invoke(main, ["--verbose"])

            # Should configure logging
            import logging

            mock_logging.assert_called_once_with(level=logging.DEBUG)
            assert result.exit_code == 0


class TestEnvironmentVariableHandling:
    """Tests for environment variable handling from CLI arguments."""

    def test_cli_args_set_environment_variables(self) -> None:
        """Test that CLI arguments properly set environment variables."""
        runner = CliRunner()

        with (
            patch("purple_mcp.cli.Settings") as mock_settings,
            patch("purple_mcp.server.app") as _,
        ):
            # Mock successful configuration
            mock_settings.return_value = Mock()
            mock_settings.return_value.graphql_full_url = "https://test.test/graphql"

            result = runner.invoke(
                main,
                [
                    "--sdl-api-token",
                    "test-sdl-token",
                    "--graphql-service-token",
                    "test-graphql-token",
                    "--console-base-url",
                    "https://test-console.test",
                    "--graphql-endpoint",
                    "/custom/graphql",
                ],
            )

            # Check environment variables were set
            assert os.environ.get(f"{ENV_PREFIX}SDL_READ_LOGS_TOKEN") == "test-sdl-token"
            assert os.environ.get(f"{ENV_PREFIX}CONSOLE_TOKEN") == "test-graphql-token"
            assert os.environ.get(f"{ENV_PREFIX}CONSOLE_BASE_URL") == "https://test-console.test"
            assert os.environ.get(f"{ENV_PREFIX}CONSOLE_GRAPHQL_ENDPOINT") == "/custom/graphql"

            assert result.exit_code == 0

    def test_environment_variables_from_env(self) -> None:
        """Test that environment variables are used when CLI args not provided."""
        runner = CliRunner()

        with (
            patch("purple_mcp.cli.Settings") as mock_settings,
            patch("purple_mcp.server.app") as _,
        ):
            # Mock successful configuration
            mock_settings.return_value = Mock()
            mock_settings.return_value.graphql_full_url = "https://test.test/graphql"

            # Set environment variables
            with runner.isolated_filesystem():
                env = {
                    f"{ENV_PREFIX}SDL_READ_LOGS_TOKEN": "env-sdl-token",
                    f"{ENV_PREFIX}CONSOLE_TOKEN": "env-console-token",
                    f"{ENV_PREFIX}CONSOLE_BASE_URL": "https://env-console.test",
                }

                result = runner.invoke(main, [], env=env)

                assert result.exit_code == 0


class TestConfigurationValidation:
    """Tests for configuration validation and error handling."""

    def test_configuration_validation_success(self) -> None:
        """Test successful configuration validation."""
        runner = CliRunner()

        with (
            patch("purple_mcp.cli.Settings") as mock_settings,
            patch("purple_mcp.server.app") as _,
        ):
            # Mock successful configuration
            mock_config = Mock()
            mock_config.graphql_full_url = "https://test.test/graphql"
            mock_settings.return_value = mock_config

            result = runner.invoke(main, ["--verbose"])

            # Should show success message
            assert "✓ Configuration validated successfully" in result.stderr
            assert "GraphQL URL: https://test.test/graphql" in result.stderr
            assert "Mode: stdio" in result.stderr
            assert result.exit_code == 0

    def test_configuration_validation_failure(self) -> None:
        """Test configuration validation failure."""
        runner = CliRunner()

        with patch("purple_mcp.cli.Settings") as mock_settings:
            # Mock configuration failure
            mock_settings.side_effect = ValueError("Missing required configuration")

            result = runner.invoke(main, [])

            # Should show error message and exit with code 1
            assert "✗ Configuration error: Missing required configuration" in result.stderr
            assert "Required environment variables or CLI options:" in result.stderr
            assert f"--graphql-service-token or {ENV_PREFIX}CONSOLE_TOKEN" in result.stderr
            assert "used for both Console and SDL" in result.stderr
            assert f"--console-base-url or {ENV_PREFIX}CONSOLE_BASE_URL" in result.stderr
            assert "Token must have Account or Site level permissions" in result.stderr
            assert result.exit_code == 1

    def test_pydantic_validation_error(self) -> None:
        """Test handling of Pydantic validation errors."""
        runner = CliRunner()

        with patch("purple_mcp.cli.Settings") as mock_settings:
            # Mock pydantic validation error
            mock_settings.side_effect = Exception("Validation failed")

            result = runner.invoke(main, [])

            # Should handle the error gracefully
            assert "✗ Configuration error:" in result.stderr
            assert result.exit_code == 1

    def test_create_settings_comprehensive_error_handling(self) -> None:
        """Test comprehensive error handling in _create_settings with all expected messages."""
        runner = CliRunner()

        with patch("purple_mcp.cli.Settings") as mock_settings:
            # Mock Settings to raise a generic exception
            mock_settings.side_effect = RuntimeError("Invalid configuration detected")

            result = runner.invoke(main, ["--mode", "stdio"])

            # Verify exit code
            assert result.exit_code == 1

            # Verify all expected error messages are present
            assert "✗ Configuration error: Invalid configuration detected" in result.stderr
            assert "Required environment variables or CLI options:" in result.stderr
            assert f"--graphql-service-token or {ENV_PREFIX}CONSOLE_TOKEN" in result.stderr
            assert "used for both Console and SDL" in result.stderr
            assert f"--console-base-url or {ENV_PREFIX}CONSOLE_BASE_URL" in result.stderr
            assert "Token must have Account or Site level permissions" in result.stderr

            # Verify Settings was called once
            mock_settings.assert_called_once()

            # Verify the success message is NOT present since configuration failed
            assert "✓ Configuration validated successfully" not in result.stderr


class TestTransportModes:
    """Tests for different transport mode behaviors."""

    def test_stdio_mode(self) -> None:
        """Test STDIO transport mode."""
        runner = CliRunner()

        with (
            patch("purple_mcp.cli.Settings") as mock_settings,
            patch("purple_mcp.server.app") as mock_app,
        ):
            mock_settings.return_value = Mock()
            mock_settings.return_value.graphql_full_url = "https://test.test/graphql"

            result = runner.invoke(main, ["--mode", "stdio"])

            mock_app.run.assert_called_once_with(transport="stdio", show_banner=False)
            assert "Starting Purple MCP server in STDIO mode..." in result.stderr
            assert result.exit_code == 0

    def test_sse_mode(self) -> None:
        """Test SSE transport mode."""
        runner = CliRunner()

        with (
            patch("purple_mcp.cli.Settings") as mock_settings,
            patch("purple_mcp.cli.uvicorn.run") as mock_uvicorn,
            patch("purple_mcp.server.app") as mock_app,
        ):
            mock_settings.return_value = Mock()
            mock_settings.return_value.graphql_full_url = "https://test.test/graphql"
            mock_app.http_app.return_value = Mock()

            result = runner.invoke(
                main, ["--mode", "sse", "--host", "127.0.0.1", "--port", "8001"]
            )

            mock_app.http_app.assert_called_once_with(transport="sse", stateless_http=False)
            mock_uvicorn.assert_called_once()

            # Check uvicorn call arguments
            call_args = mock_uvicorn.call_args
            assert call_args[1]["host"] == "127.0.0.1"
            assert call_args[1]["port"] == 8001

            assert "Starting Purple MCP server in SSE mode on 127.0.0.1:8001..." in result.stderr
            assert result.exit_code == 0

    def test_streamable_http_mode(self) -> None:
        """Test streamable-http transport mode."""
        runner = CliRunner()

        with (
            patch("purple_mcp.cli.Settings") as mock_settings,
            patch("purple_mcp.cli.uvicorn.run") as mock_uvicorn,
            patch("purple_mcp.server.app") as mock_app,
        ):
            mock_settings.return_value = Mock()
            mock_settings.return_value.graphql_full_url = "https://test.test/graphql"
            mock_app.http_app.return_value = Mock()

            result = runner.invoke(main, ["--mode", "streamable-http"])

            mock_app.http_app.assert_called_once_with(transport="streamable-http", stateless_http=False)
            mock_uvicorn.assert_called_once()

            assert (
                "Starting Purple MCP server in STREAMABLE-HTTP mode on localhost:8000..."
                in result.stderr
            )
            assert result.exit_code == 0

    def test_invalid_mode(self) -> None:
        """Test handling of invalid transport mode."""
        runner = CliRunner()

        # Invalid mode should be caught by Click choice validation
        result = runner.invoke(main, ["--mode", "invalid"])

        # Click should reject invalid choice before our code runs
        assert result.exit_code != 0
        assert "Invalid value for '--mode'" in result.output

    def test_case_insensitive_mode(self) -> None:
        """Test that transport mode is case insensitive."""
        runner = CliRunner()

        with (
            patch("purple_mcp.cli.Settings") as mock_settings,
            patch("purple_mcp.server.app") as mock_app,
        ):
            mock_settings.return_value = Mock()
            mock_settings.return_value.graphql_full_url = "https://test.test/graphql"

            result = runner.invoke(main, ["--mode", "STDIO"])

            mock_app.run.assert_called_once_with(transport="stdio", show_banner=False)
            assert result.exit_code == 0


class TestModeDispatcher:
    """Tests for the _run_mode dispatcher function."""

    def test_stdio_mode_dispatch(self) -> None:
        """Test that stdio mode dispatches to _run_stdio correctly."""
        with patch("purple_mcp.cli._run_stdio") as mock_run_stdio:
            _run_mode("stdio", host="localhost", port=8000, verbose=True)

            mock_run_stdio.assert_called_once_with(True, False)

    def test_sse_mode_dispatch(self) -> None:
        """Test that sse mode dispatches to _run_uvicorn with sse transport."""
        with patch("purple_mcp.cli._run_uvicorn") as mock_run_uvicorn:
            _run_mode("sse", host="127.0.0.1", port=8001, verbose=False)

            mock_run_uvicorn.assert_called_once_with(
                "sse", host="127.0.0.1", port=8001, verbose=False, allow_remote_access=False, stateless_http=False
            )

    def test_streamable_http_mode_dispatch(self) -> None:
        """Test that streamable-http mode dispatches to _run_uvicorn with streamable-http transport."""
        with patch("purple_mcp.cli._run_uvicorn") as mock_run_uvicorn:
            _run_mode(
                "streamable-http",
                host="0.0.0.0",
                port=9000,
                verbose=True,
                allow_remote_access=True,
                stateless_http=False
            )

            mock_run_uvicorn.assert_called_once_with(
                "streamable-http",
                host="0.0.0.0",
                port=9000,
                verbose=True,
                allow_remote_access=True,
                stateless_http=False
            )

    def test_case_insensitive_mode_dispatch(self) -> None:
        """Test that mode dispatch is case insensitive."""
        with patch("purple_mcp.cli._run_stdio") as mock_run_stdio:
            _run_mode("STDIO", host="localhost", port=8000, verbose=False)

            mock_run_stdio.assert_called_once_with(False, False)

        with patch("purple_mcp.cli._run_uvicorn") as mock_run_uvicorn:
            _run_mode("SSE", host="localhost", port=8000, verbose=False)

            mock_run_uvicorn.assert_called_once_with(
                "sse", host="localhost", port=8000, verbose=False, allow_remote_access=False, stateless_http=False
            )


class TestErrorHandling:
    """Tests for error handling scenarios."""

    def test_server_import_error(self) -> None:
        """Test handling of server import errors."""
        runner = CliRunner()

        with patch("purple_mcp.cli.Settings") as mock_settings:
            mock_settings.return_value = Mock()
            mock_settings.return_value.graphql_full_url = "https://test.test/graphql"

            # Mock import error when importing server
            original_import = __import__

            def mock_import(
                name: str,
                globals: dict[str, object] | None = None,
                locals: dict[str, object] | None = None,
                fromlist: tuple[str, ...] = (),
                level: int = 0,
            ) -> object:
                if name == "purple_mcp.server":
                    raise ImportError("Cannot import server")
                return original_import(name, globals, locals, fromlist, level)

            with patch("builtins.__import__", side_effect=mock_import):
                result = runner.invoke(main, [])

                # Should fail with import error
                assert result.exit_code != 0

    def test_uvicorn_startup_error(self) -> None:
        """Test handling of uvicorn startup errors."""
        runner = CliRunner()

        with (
            patch("purple_mcp.cli.Settings") as mock_settings,
            patch("purple_mcp.cli.uvicorn.run") as mock_uvicorn,
            patch("purple_mcp.server.app") as mock_app,
        ):
            mock_settings.return_value = Mock()
            mock_settings.return_value.graphql_full_url = "https://test.test/graphql"
            mock_app.http_app.return_value = Mock()

            # Mock uvicorn startup error
            mock_uvicorn.side_effect = Exception("Uvicorn startup failed")

            result = runner.invoke(main, ["--mode", "sse"])

            # Should exit with status 1 and show clear error message
            assert result.exit_code == 1
            assert "✗ Failed to start server: Uvicorn startup failed" in result.stderr

    def test_app_run_error(self) -> None:
        """Test handling of app.run errors in stdio mode."""
        runner = CliRunner()

        with (
            patch("purple_mcp.cli.Settings") as mock_settings,
            patch("purple_mcp.server.app") as mock_app,
        ):
            mock_settings.return_value = Mock()
            mock_settings.return_value.graphql_full_url = "https://test.test/graphql"

            # Mock app.run error
            mock_app.run.side_effect = Exception("STDIO server startup failed")

            result = runner.invoke(main, ["--mode", "stdio"])

            # Should exit with status 1 and show clear error message
            assert result.exit_code == 1
            assert "✗ Failed to start server: STDIO server startup failed" in result.stderr


class TestCLIIntegration:
    """Integration tests for the complete CLI workflow."""

    def test_full_workflow_with_all_options(self) -> None:
        """Test complete workflow with all CLI options."""
        runner = CliRunner()

        with (
            patch("purple_mcp.cli.Settings") as mock_settings,
            patch("purple_mcp.cli.uvicorn.run") as mock_uvicorn,
            patch("purple_mcp.server.app") as mock_app,
            patch("logging.basicConfig") as mock_logging,
        ):
            mock_settings.return_value = Mock()
            mock_settings.return_value.graphql_full_url = "https://test.test/graphql"
            mock_app.http_app.return_value = Mock()

            result = runner.invoke(
                main,
                [
                    "--mode",
                    "sse",
                    "--host",
                    "0.0.0.0",
                    "--port",
                    "9000",
                    "--sdl-api-token",
                    "test-sdl",
                    "--graphql-service-token",
                    "test-graphql",
                    "--console-base-url",
                    "https://test.test",
                    "--graphql-endpoint",
                    "/test/graphql",
                    "--verbose",
                    "--allow-remote-access",
                ],
            )

            # Should configure logging
            mock_logging.assert_called_once()

            # Should validate configuration
            mock_settings.assert_called_once()

            # Should start server
            mock_app.http_app.assert_called_once_with(transport="sse", stateless_http=False)
            mock_uvicorn.assert_called_once()

            assert result.exit_code == 0

    def test_help_output(self) -> None:
        """Test CLI help output."""
        runner = CliRunner()

        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "Purple MCP Server - AI monitoring and analysis tool" in result.output
        assert "--mode" in result.output
        assert "--host" in result.output
        assert "--port" in result.output
        assert "--verbose" in result.output

    @pytest.mark.parametrize("mode", ["stdio", "sse", "streamable-http"])
    def test_all_modes_with_valid_config(self, mode: str) -> None:
        """Test all transport modes with valid configuration."""
        runner = CliRunner()

        with (
            patch("purple_mcp.cli.Settings") as mock_settings,
            patch("purple_mcp.cli.uvicorn.run") as mock_uvicorn,
            patch("purple_mcp.server.app") as mock_app,
        ):
            mock_settings.return_value = Mock()
            mock_settings.return_value.graphql_full_url = "https://test.test/graphql"
            mock_app.http_app.return_value = Mock()

            result = runner.invoke(main, ["--mode", mode])

            if mode == "stdio":
                mock_app.run.assert_called_once_with(transport="stdio", show_banner=False)
            else:
                mock_uvicorn.assert_called_once()
                if mode == "sse":
                    mock_app.http_app.assert_called_once_with(transport="sse", stateless_http=False)
                else:  # streamable-http
                    mock_app.http_app.assert_called_once_with(transport="streamable-http", stateless_http=False)

            assert result.exit_code == 0


class TestSecurityValidation:
    """Tests for HTTP binding security validation."""

    def test_loopback_localhost_allowed_without_flag(self) -> None:
        """Test that localhost is allowed without --allow-remote-access flag."""
        runner = CliRunner()

        with (
            patch("purple_mcp.cli.Settings") as mock_settings,
            patch("purple_mcp.cli.uvicorn.run") as mock_uvicorn,
            patch("purple_mcp.server.app") as mock_app,
        ):
            mock_settings.return_value = Mock()
            mock_settings.return_value.graphql_full_url = "https://test.test/graphql"
            mock_app.http_app.return_value = Mock()

            result = runner.invoke(main, ["--mode", "sse", "--host", "localhost"])

            # Should succeed without --allow-remote-access
            assert result.exit_code == 0
            mock_uvicorn.assert_called_once()

    def test_loopback_127_0_0_1_allowed_without_flag(self) -> None:
        """Test that 127.0.0.1 is allowed without --allow-remote-access flag."""
        runner = CliRunner()

        with (
            patch("purple_mcp.cli.Settings") as mock_settings,
            patch("purple_mcp.cli.uvicorn.run") as mock_uvicorn,
            patch("purple_mcp.server.app") as mock_app,
        ):
            mock_settings.return_value = Mock()
            mock_settings.return_value.graphql_full_url = "https://test.test/graphql"
            mock_app.http_app.return_value = Mock()

            result = runner.invoke(main, ["--mode", "sse", "--host", "127.0.0.1"])

            # Should succeed without --allow-remote-access
            assert result.exit_code == 0
            mock_uvicorn.assert_called_once()

    def test_loopback_ipv6_allowed_without_flag(self) -> None:
        """Test that ::1 (IPv6 loopback) is allowed without --allow-remote-access flag."""
        runner = CliRunner()

        with (
            patch("purple_mcp.cli.Settings") as mock_settings,
            patch("purple_mcp.cli.uvicorn.run") as mock_uvicorn,
            patch("purple_mcp.server.app") as mock_app,
        ):
            mock_settings.return_value = Mock()
            mock_settings.return_value.graphql_full_url = "https://test.test/graphql"
            mock_app.http_app.return_value = Mock()

            result = runner.invoke(main, ["--mode", "sse", "--host", "::1"])

            # Should succeed without --allow-remote-access
            assert result.exit_code == 0
            mock_uvicorn.assert_called_once()

    def test_non_loopback_refused_without_flag(self) -> None:
        """Test that non-loopback addresses are refused without --allow-remote-access flag."""
        runner = CliRunner()

        with (
            patch("purple_mcp.cli.Settings") as mock_settings,
            patch("purple_mcp.server.app") as mock_app,
        ):
            mock_settings.return_value = Mock()
            mock_settings.return_value.graphql_full_url = "https://test.test/graphql"
            mock_app.http_app.return_value = Mock()

            result = runner.invoke(main, ["--mode", "sse", "--host", "0.0.0.0"])

            # Should fail with security error
            assert result.exit_code == 1
            assert "SECURITY ERROR" in result.stderr
            assert "Refusing to bind to non-loopback interface" in result.stderr
            assert "0.0.0.0" in result.stderr
            assert "--allow-remote-access" in result.stderr

    def test_public_ip_refused_without_flag(self) -> None:
        """Test that public IP addresses are refused without --allow-remote-access flag."""
        runner = CliRunner()

        with (
            patch("purple_mcp.cli.Settings") as mock_settings,
            patch("purple_mcp.server.app") as mock_app,
        ):
            mock_settings.return_value = Mock()
            mock_settings.return_value.graphql_full_url = "https://test.test/graphql"
            mock_app.http_app.return_value = Mock()

            result = runner.invoke(main, ["--mode", "sse", "--host", "192.168.1.100"])

            # Should fail with security error
            assert result.exit_code == 1
            assert "SECURITY ERROR" in result.stderr
            assert "192.168.1.100" in result.stderr

    def test_non_loopback_allowed_with_flag(self) -> None:
        """Test that non-loopback addresses are allowed with --allow-remote-access flag."""
        runner = CliRunner()

        with (
            patch("purple_mcp.cli.Settings") as mock_settings,
            patch("purple_mcp.cli.uvicorn.run") as mock_uvicorn,
            patch("purple_mcp.server.app") as mock_app,
        ):
            mock_settings.return_value = Mock()
            mock_settings.return_value.graphql_full_url = "https://test.test/graphql"
            mock_app.http_app.return_value = Mock()

            result = runner.invoke(
                main, ["--mode", "sse", "--host", "0.0.0.0", "--allow-remote-access"]
            )

            # Should succeed with flag
            assert result.exit_code == 0
            mock_uvicorn.assert_called_once()
            # Should display security warning
            assert "WARNING: RUNNING IN REMOTE ACCESS MODE" in result.stderr

    def test_security_warning_displayed_for_non_loopback(self) -> None:
        """Test that security warning banner is displayed for non-loopback binding."""
        runner = CliRunner()

        with (
            patch("purple_mcp.cli.Settings") as mock_settings,
            patch("purple_mcp.cli.uvicorn.run"),
            patch("purple_mcp.server.app") as mock_app,
        ):
            mock_settings.return_value = Mock()
            mock_settings.return_value.graphql_full_url = "https://test.test/graphql"
            mock_app.http_app.return_value = Mock()

            result = runner.invoke(
                main, ["--mode", "sse", "--host", "0.0.0.0", "--allow-remote-access"]
            )

            # Check that warning banner is displayed
            assert "WARNING: RUNNING IN REMOTE ACCESS MODE" in result.stderr
            assert "SECURITY RISKS:" in result.stderr
            assert "unauthenticated HTTP/SSE interface" in result.stderr
            assert "Data exfiltration is possible" in result.stderr
            assert "RECOMMENDED PROTECTIONS:" in result.stderr
            assert result.exit_code == 0

    def test_streamable_http_mode_security_validation(self) -> None:
        """Test security validation works for streamable-http mode."""
        runner = CliRunner()

        with (
            patch("purple_mcp.cli.Settings") as mock_settings,
            patch("purple_mcp.server.app") as mock_app,
        ):
            mock_settings.return_value = Mock()
            mock_settings.return_value.graphql_full_url = "https://test.test/graphql"
            mock_app.http_app.return_value = Mock()

            result = runner.invoke(main, ["--mode", "streamable-http", "--host", "0.0.0.0"])

            # Should fail without --allow-remote-access
            assert result.exit_code == 1
            assert "SECURITY ERROR" in result.stderr

    def test_stdio_mode_ignores_host_validation(self) -> None:
        """Test that stdio mode doesn't perform host validation."""
        runner = CliRunner()

        with (
            patch("purple_mcp.cli.Settings") as mock_settings,
            patch("purple_mcp.server.app") as mock_app,
        ):
            mock_settings.return_value = Mock()
            mock_settings.return_value.graphql_full_url = "https://test.test/graphql"

            # stdio mode should work regardless of host setting
            result = runner.invoke(main, ["--mode", "stdio", "--host", "0.0.0.0"])

            # Should succeed because stdio doesn't use the host parameter
            assert result.exit_code == 0
            mock_app.run.assert_called_once()

    def test_case_insensitive_localhost(self) -> None:
        """Test that LOCALHOST is recognized as loopback."""
        runner = CliRunner()

        with (
            patch("purple_mcp.cli.Settings") as mock_settings,
            patch("purple_mcp.cli.uvicorn.run") as mock_uvicorn,
            patch("purple_mcp.server.app") as mock_app,
        ):
            mock_settings.return_value = Mock()
            mock_settings.return_value.graphql_full_url = "https://test.test/graphql"
            mock_app.http_app.return_value = Mock()

            result = runner.invoke(main, ["--mode", "sse", "--host", "LOCALHOST"])

            # Should succeed without --allow-remote-access
            assert result.exit_code == 0
            mock_uvicorn.assert_called_once()


class TestIsLoopbackHost:
    """Tests for the _is_loopback_host helper function."""

    def test_localhost_is_loopback(self) -> None:
        """Test that 'localhost' is identified as loopback."""
        from purple_mcp.cli import _is_loopback_host

        assert _is_loopback_host("localhost") is True

    def test_localhost_uppercase_is_loopback(self) -> None:
        """Test that 'LOCALHOST' is identified as loopback."""
        from purple_mcp.cli import _is_loopback_host

        assert _is_loopback_host("LOCALHOST") is True

    def test_localhost_localdomain_is_loopback(self) -> None:
        """Test that 'localhost.localdomain' is identified as loopback."""
        from purple_mcp.cli import _is_loopback_host

        assert _is_loopback_host("localhost.localdomain") is True

    def test_127_0_0_1_is_loopback(self) -> None:
        """Test that '127.0.0.1' is identified as loopback."""
        from purple_mcp.cli import _is_loopback_host

        assert _is_loopback_host("127.0.0.1") is True

    def test_127_x_x_x_is_loopback(self) -> None:
        """Test that other 127.x.x.x addresses are identified as loopback."""
        from purple_mcp.cli import _is_loopback_host

        assert _is_loopback_host("127.0.0.2") is True
        assert _is_loopback_host("127.255.255.255") is True

    def test_ipv6_loopback_is_loopback(self) -> None:
        """Test that '::1' (IPv6 loopback) is identified as loopback."""
        from purple_mcp.cli import _is_loopback_host

        assert _is_loopback_host("::1") is True

    def test_0_0_0_0_is_not_loopback(self) -> None:
        """Test that '0.0.0.0' is not identified as loopback."""
        from purple_mcp.cli import _is_loopback_host

        assert _is_loopback_host("0.0.0.0") is False

    def test_public_ip_is_not_loopback(self) -> None:
        """Test that public IP addresses are not identified as loopback."""
        from purple_mcp.cli import _is_loopback_host

        assert _is_loopback_host("8.8.8.8") is False
        assert _is_loopback_host("192.168.1.1") is False
        assert _is_loopback_host("10.0.0.1") is False

    def test_ipv6_public_is_not_loopback(self) -> None:
        """Test that public IPv6 addresses are not identified as loopback."""
        from purple_mcp.cli import _is_loopback_host

        assert _is_loopback_host("2001:4860:4860::8888") is False

    def test_invalid_hostname_is_not_loopback(self) -> None:
        """Test that invalid/unknown hostnames are not identified as loopback."""
        from purple_mcp.cli import _is_loopback_host

        assert _is_loopback_host("example.com") is False
        assert _is_loopback_host("not-a-real-host") is False
