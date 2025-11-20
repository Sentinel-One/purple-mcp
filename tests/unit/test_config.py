"""Tests for purple_mcp.config module."""

import importlib
import logging
import os
import sys
from collections.abc import Generator
from uuid import UUID

import pytest
from pydantic import ValidationError

from purple_mcp import __version__
from purple_mcp.config import ENV_PREFIX, Settings, get_settings


@pytest.fixture(autouse=True)
def clear_env_and_cache(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Clear relevant environment variables and settings cache before each test."""
    for var in (
        f"{ENV_PREFIX}SDL_READ_LOGS_TOKEN",
        f"{ENV_PREFIX}CONSOLE_TOKEN",
        f"{ENV_PREFIX}CONSOLE_BASE_URL",
        f"{ENV_PREFIX}CONSOLE_GRAPHQL_ENDPOINT",
    ):
        monkeypatch.delenv(var, raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def minimal_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set minimal required environment for valid Settings."""
    monkeypatch.setenv(f"{ENV_PREFIX}SDL_READ_LOGS_TOKEN", "token")
    monkeypatch.setenv(f"{ENV_PREFIX}CONSOLE_TOKEN", "token")
    monkeypatch.setenv(f"{ENV_PREFIX}CONSOLE_BASE_URL", "https://console.example.test")


def test_defaults(minimal_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """Defaults for endpoint and tokens should apply (but not base URL)."""
    monkeypatch.setenv(f"{ENV_PREFIX}CONSOLE_BASE_URL", "https://console.example.test")
    settings = Settings()
    assert settings.sdl_api_token == "token"
    assert settings.graphql_service_token == "token"
    assert settings.sentinelone_console_base_url == "https://console.example.test"
    assert settings.sentinelone_console_graphql_endpoint == "/web/api/v2.1/graphql"
    assert settings.purple_ai_account_id == "0"
    assert settings.purple_ai_team_token == "0"
    assert isinstance(UUID(settings.purple_ai_session_id), UUID)
    assert settings.purple_ai_email_address is None
    assert settings.purple_ai_user_agent == f"sentinelone/purple-mcp (version {__version__})"
    assert settings.purple_ai_build_date is None
    assert settings.purple_ai_build_hash is None
    assert settings.purple_ai_console_version == "S"


@pytest.mark.parametrize(
    "env_name,attr,value",
    [
        # Note: sdl_api_token now uses CONSOLE_TOKEN, tested separately below
        (f"{ENV_PREFIX}console_token", "graphql_service_token", "console"),
        (f"{ENV_PREFIX}console_base_url", "sentinelone_console_base_url", "https://example.test"),
        (
            f"{ENV_PREFIX}console_graphql_endpoint",
            "sentinelone_console_graphql_endpoint",
            "/api",
        ),
    ],
)
def test_case_insensitive_env_vars_and_aliases(
    env_name: str, attr: str, value: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ensure environment variable names and aliases are case-insensitive."""
    monkeypatch.setenv(env_name, value)
    # ensure required tokens and base URL
    if not env_name.upper().endswith("CONSOLE_TOKEN"):
        monkeypatch.setenv(
            f"{ENV_PREFIX}CONSOLE_TOKEN", os.getenv(f"{ENV_PREFIX}CONSOLE_TOKEN", "token")
        )
    if not env_name.upper().endswith("CONSOLE_BASE_URL"):
        monkeypatch.setenv(
            f"{ENV_PREFIX}CONSOLE_BASE_URL",
            os.getenv(f"{ENV_PREFIX}CONSOLE_BASE_URL", "https://console.example.test"),
        )
    settings = Settings()
    assert getattr(settings, attr) == value


def test_sdl_token_uses_console_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that sdl_api_token uses the same value as CONSOLE_TOKEN."""
    console_token_value = "shared_console_token"
    monkeypatch.setenv(f"{ENV_PREFIX}CONSOLE_TOKEN", console_token_value)
    monkeypatch.setenv(f"{ENV_PREFIX}CONSOLE_BASE_URL", "https://console.example.test")

    settings = Settings()
    # Both tokens should have the same value
    assert settings.sdl_api_token == console_token_value
    assert settings.graphql_service_token == console_token_value
    assert settings.sdl_api_token == settings.graphql_service_token


@pytest.mark.parametrize(
    "set_console,set_base_url,missing",
    [
        # Note: SDL token now uses CONSOLE_TOKEN, so we only test CONSOLE_TOKEN
        (False, True, (f"{ENV_PREFIX}CONSOLE_TOKEN",)),
        (True, False, (f"{ENV_PREFIX}CONSOLE_BASE_URL",)),
        (
            False,
            False,
            (
                f"{ENV_PREFIX}CONSOLE_TOKEN",
                f"{ENV_PREFIX}CONSOLE_BASE_URL",
            ),
        ),
    ],
)
def test_missing_tokens(
    set_console: bool,
    set_base_url: bool,
    missing: tuple[str, ...],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing required configuration should raise ValidationError."""
    if set_console:
        monkeypatch.setenv(f"{ENV_PREFIX}CONSOLE_TOKEN", "token")
    if set_base_url:
        monkeypatch.setenv(f"{ENV_PREFIX}CONSOLE_BASE_URL", "https://test.example.test")
    with pytest.raises(ValidationError) as exc:
        Settings()
    err = str(exc.value)
    for var in missing:
        assert var in err


@pytest.mark.parametrize(
    "base_url,err_fragment",
    [
        ("http://example.test", "Console base URL must use HTTPS"),
        ("ftp://example.test", "Console base URL must use HTTPS"),
        ("https://example.test/", "Console base URL must not have a trailing slash"),
        ("", "Console base URL must use HTTPS"),
        ("https://", "Console base URL must not have a trailing slash"),
        ("HTTPS://EXAMPLE.TEST", "Console base URL must use HTTPS"),
        ("https://example.test/path/", "Console base URL must not have a trailing slash"),
        ("https://example.test/sdl", "Console base URL must not contain a path"),
        ("https://tenant.example.test/sdl", "Console base URL must not contain a path"),
        ("https://example.test/api/v1", "Console base URL must not contain a path"),
        ("https://example.test/path", "Console base URL must not contain a path"),
        ("https://example.test?foo=bar", "Console base URL must not contain query parameters"),
        (
            "https://tenant.example.test/?foo=bar",
            "Console base URL must not contain a path",
        ),
        (
            "https://example.test?key=value&other=param",
            "Console base URL must not contain query parameters",
        ),
        ("https://example.test#fragment", "Console base URL must not contain a fragment"),
        ("https://tenant.example.test#frag", "Console base URL must not contain a fragment"),
        ("https://example.test#", "Console base URL must not have a trailing hash"),
        ("https://tenant.example.test#", "Console base URL must not have a trailing hash"),
        ("https://tenant.example.test/;foo", "Console base URL must not contain a path"),
        ("https://example.test/path;params", "Console base URL must not contain a path"),
        ("https://example.test;params", "Console base URL must not contain path parameters"),
        ("https://:443", "Console base URL must have a valid hostname"),
        ("https://:8443", "Console base URL must have a valid hostname"),
    ],
)
def test_console_base_url_invalid(
    base_url: str, err_fragment: str, minimal_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Invalid console base URLs should produce validation errors."""
    monkeypatch.setenv(f"{ENV_PREFIX}CONSOLE_BASE_URL", base_url)
    with pytest.raises(ValidationError) as exc:
        Settings()
    assert err_fragment in str(exc.value)


@pytest.mark.parametrize(
    "base_url",
    [
        "https://example.test",
        "https://test.example.test",
        "https://subdomain.example.test",
        "https://localhost:8443",
        "https://192.168.1.100",
        "https://api-v2.example.test",
    ],
)
def test_console_base_url_valid(
    base_url: str, minimal_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Valid HTTPS console base URLs should pass unchanged."""
    monkeypatch.setenv(f"{ENV_PREFIX}CONSOLE_BASE_URL", base_url)
    settings = Settings()
    assert settings.sentinelone_console_base_url == base_url


@pytest.mark.parametrize(
    "endpoint,err_fragment",
    [
        ("api", "Console graphql endpoint must start with a slash"),
        ("", "Console graphql endpoint must start with a slash"),
        ("graphql", "Console graphql endpoint must start with a slash"),
        ("api/v1", "Console graphql endpoint must start with a slash"),
        ("\\api", "Console graphql endpoint must start with a slash"),
    ],
)
def test_console_graphql_endpoint_invalid(
    endpoint: str, err_fragment: str, minimal_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Invalid GraphQL endpoints should produce validation errors."""
    monkeypatch.setenv(f"{ENV_PREFIX}CONSOLE_GRAPHQL_ENDPOINT", endpoint)
    with pytest.raises(ValidationError) as exc:
        Settings()
    assert err_fragment in str(exc.value)


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api",
        "/graphql",
        "/api/v1/graphql",
        "/web/api/v2.1/graphql",
        "/",
        "/a/b/c/d/e/f",
    ],
)
def test_console_graphql_endpoint_valid(
    endpoint: str, minimal_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Valid GraphQL endpoints starting with slash should pass."""
    monkeypatch.setenv(f"{ENV_PREFIX}CONSOLE_GRAPHQL_ENDPOINT", endpoint)
    settings = Settings()
    assert settings.sentinelone_console_graphql_endpoint == endpoint


@pytest.mark.parametrize(
    "endpoint,err_fragment",
    [
        ("api", "Alerts graphql endpoint must start with a slash"),
        ("", "Alerts graphql endpoint must start with a slash"),
        ("graphql", "Alerts graphql endpoint must start with a slash"),
        ("api/v1", "Alerts graphql endpoint must start with a slash"),
        ("\\api", "Alerts graphql endpoint must start with a slash"),
    ],
)
def test_alerts_graphql_endpoint_invalid(
    endpoint: str, err_fragment: str, minimal_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Invalid alerts GraphQL endpoints should produce validation errors."""
    monkeypatch.setenv(f"{ENV_PREFIX}ALERTS_GRAPHQL_ENDPOINT", endpoint)
    with pytest.raises(ValidationError) as exc:
        Settings()
    assert err_fragment in str(exc.value)


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api",
        "/graphql",
        "/api/v1/graphql",
        "/web/api/v2.1/unifiedalerts/graphql",
        "/",
        "/a/b/c/d/e/f",
    ],
)
def test_alerts_graphql_endpoint_valid(
    endpoint: str, minimal_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Valid alerts GraphQL endpoints starting with slash should pass."""
    monkeypatch.setenv(f"{ENV_PREFIX}ALERTS_GRAPHQL_ENDPOINT", endpoint)
    settings = Settings()
    assert settings.sentinelone_alerts_graphql_endpoint == endpoint


@pytest.mark.parametrize(
    "base_url,endpoint,expected",
    [
        ("https://example.test", "/api/v1/graphql", "https://example.test/api/v1/graphql"),
        ("https://example.test", "/graphql", "https://example.test/graphql"),
        ("https://example.test", "/", "https://example.test/"),
        ("https://api.example.test", "/v2/graphql", "https://api.example.test/v2/graphql"),
    ],
)
def test_graphql_full_url_property(
    minimal_env: None, monkeypatch: pytest.MonkeyPatch, base_url: str, endpoint: str, expected: str
) -> None:
    """Various base URL and endpoint combos produce correct full URL."""
    monkeypatch.setenv(f"{ENV_PREFIX}CONSOLE_BASE_URL", base_url)
    monkeypatch.setenv(f"{ENV_PREFIX}CONSOLE_GRAPHQL_ENDPOINT", endpoint)
    settings = Settings()
    assert settings.graphql_full_url == expected


def test_default_graphql_full_url(minimal_env: None) -> None:
    """Default GraphQL full URL should use base URL from env and default endpoint."""
    settings = Settings()
    assert settings.graphql_full_url == ("https://console.example.test/web/api/v2.1/graphql")


@pytest.mark.parametrize(
    "base_url,endpoint,expected",
    [
        (
            "https://example.test",
            "/api/v1/alerts/graphql",
            "https://example.test/api/v1/alerts/graphql",
        ),
        ("https://example.test", "/alerts", "https://example.test/alerts"),
        ("https://example.test", "/", "https://example.test/"),
        ("https://api.example.test", "/v2/alerts", "https://api.example.test/v2/alerts"),
    ],
)
def test_alerts_graphql_url_property(
    minimal_env: None, monkeypatch: pytest.MonkeyPatch, base_url: str, endpoint: str, expected: str
) -> None:
    """Various base URL and alerts endpoint combos produce correct full URL."""
    monkeypatch.setenv(f"{ENV_PREFIX}CONSOLE_BASE_URL", base_url)
    monkeypatch.setenv(f"{ENV_PREFIX}ALERTS_GRAPHQL_ENDPOINT", endpoint)
    settings = Settings()
    assert settings.alerts_graphql_url == expected


def test_default_alerts_graphql_url(minimal_env: None) -> None:
    """Default alerts GraphQL full URL should use base URL from env and default endpoint."""
    settings = Settings()
    assert settings.alerts_graphql_url == (
        "https://console.example.test/web/api/v2.1/unifiedalerts/graphql"
    )


def test_extra_env_vars_are_ignored(minimal_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """Unknown environment variables should be ignored by Settings."""
    monkeypatch.setenv("UNKNOWN_VAR", "ignored")
    monkeypatch.setenv("RANDOM_OTHER_VAR", "also_ignored")
    settings = Settings()
    assert not hasattr(settings, "unknown_var")
    assert not hasattr(settings, "random_other_var")


def test_combined_missing_token_and_invalid_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Both missing token and invalid base URL errors should appear."""
    monkeypatch.setenv(f"{ENV_PREFIX}CONSOLE_BASE_URL", "http://insecure.test/")
    with pytest.raises(ValidationError) as exc:
        Settings()
    err = str(exc.value)
    # Note: SDL token now uses CONSOLE_TOKEN, so we check for CONSOLE_TOKEN instead
    assert f"{ENV_PREFIX}CONSOLE_TOKEN" in err
    assert "Console base URL must use HTTPS" in err


def test_combined_invalid_base_url_and_endpoint(
    minimal_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both invalid base URL and endpoint errors should appear."""
    monkeypatch.setenv(f"{ENV_PREFIX}CONSOLE_BASE_URL", "https://example.test/")
    monkeypatch.setenv(f"{ENV_PREFIX}CONSOLE_GRAPHQL_ENDPOINT", "api")
    with pytest.raises(ValidationError) as exc:
        Settings()
    err = str(exc.value)
    assert "Console base URL must not have a trailing slash" in err
    assert "Console graphql endpoint must start with a slash" in err


def test_model_post_init_logging(minimal_env: None, caplog: pytest.LogCaptureFixture) -> None:
    """Post-init logs config summary without exposing secrets."""
    caplog.set_level(logging.INFO)
    _ = Settings()  # Settings instantiation triggers logging
    messages = [rec.message for rec in caplog.records]
    assert "Application configuration loaded successfully" in messages

    # Check that the extra data contains the expected values
    console_url_record = next(
        (
            rec
            for rec in caplog.records
            if "SentinelOne Console Base URL configured" in rec.message
        ),
        None,
    )
    assert console_url_record is not None
    assert hasattr(console_url_record, "console_base_url")
    assert console_url_record.console_base_url == "https://console.example.test"

    graphql_url_record = next(
        (rec for rec in caplog.records if "Purple AI GraphQL URL configured" in rec.message), None
    )
    assert graphql_url_record is not None
    assert hasattr(graphql_url_record, "graphql_url")
    assert graphql_url_record.graphql_url == "https://console.example.test/web/api/v2.1/graphql"

    # Check that the consolidated token logging message is present
    assert any(
        f"{ENV_PREFIX}CONSOLE_TOKEN is configured" in msg
        and "used for both Console and SDL access" in msg
        for msg in messages
    )


def test_model_post_init_includes_correct_graphql_url(
    minimal_env: None, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """model_post_init logs actual graphql_full_url value."""
    monkeypatch.setenv(f"{ENV_PREFIX}CONSOLE_BASE_URL", "https://custom.example.test")
    monkeypatch.setenv(f"{ENV_PREFIX}CONSOLE_GRAPHQL_ENDPOINT", "/custom/endpoint")
    caplog.set_level(logging.INFO)
    _ = Settings()  # Settings instantiation triggers logging

    # Find the record and check the extra data contains the expected URL
    graphql_url_record = next(
        (rec for rec in caplog.records if "Purple AI GraphQL URL configured" in rec.message), None
    )
    assert graphql_url_record is not None
    assert hasattr(graphql_url_record, "graphql_url")
    assert graphql_url_record.graphql_url == "https://custom.example.test/custom/endpoint"


def test_get_settings_caching(minimal_env: None) -> None:
    """get_settings should cache on success."""
    get_settings.cache_clear()
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2


def test_get_settings_validation_error(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """get_settings should log critical error on ValidationError."""
    get_settings.cache_clear()
    caplog.set_level(logging.CRITICAL)
    # Don't set any env vars, so validation fails
    with pytest.raises(ValidationError):
        get_settings()
    assert any(
        "Failed to initialize application configuration" in rec.message for rec in caplog.records
    )


def test_get_settings_general_exception(
    minimal_env: None, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """get_settings should log critical error on any exception."""
    get_settings.cache_clear()
    caplog.clear()
    caplog.set_level(logging.CRITICAL)

    # Mock Settings to raise a general exception
    def mock_settings(*args: object, **kwargs: object) -> None:
        raise RuntimeError("Unexpected error")

    monkeypatch.setattr("purple_mcp.config.Settings", mock_settings)

    with pytest.raises(RuntimeError):
        get_settings()
    assert any(
        "Failed to initialize application configuration" in rec.message for rec in caplog.records
    )


def _reload_and_get_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Settings | None, type[Settings] | None]:
    """Safely reload config, returning its 'settings' instance and Settings class.

    This helper isolates module reloading to prevent side effects in parallel tests.
    It removes the module from sys.modules, re-imports it, and then restores
    the original module state.
    """
    module_name = "purple_mcp.config"
    original_module = sys.modules.get(module_name)

    # Unload the module to force re-initialization on next import
    if original_module:
        monkeypatch.delitem(sys.modules, module_name)

    try:
        # Re-import the module to trigger its top-level code
        config_module = importlib.import_module(module_name)
        reloaded_settings = getattr(config_module, "settings", None)
        reloaded_settings_class = getattr(config_module, "Settings", None)
        return reloaded_settings, reloaded_settings_class
    finally:
        # Restore the original module to avoid side effects
        if original_module:
            monkeypatch.setitem(sys.modules, module_name, original_module)
        else:
            # If it wasn't there to begin with, remove the newly imported one
            if module_name in sys.modules:
                monkeypatch.delitem(sys.modules, module_name)


def test_module_level_settings_success(minimal_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """Module-level 'settings' should be initialized when env is set."""
    reloaded_settings, reloaded_settings_class = _reload_and_get_settings(monkeypatch)
    assert reloaded_settings is not None
    assert reloaded_settings_class is not None
    assert isinstance(reloaded_settings, reloaded_settings_class)
    assert reloaded_settings.sdl_api_token == "token"


def test_module_level_settings_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Module-level 'settings' should be None when initialization fails."""
    # Clear env vars so initialization fails
    monkeypatch.delenv("SDL_READ_LOGS_TOKEN", raising=False)
    monkeypatch.delenv("CONSOLE_TOKEN", raising=False)

    reloaded_settings, _ = _reload_and_get_settings(monkeypatch)
    assert reloaded_settings is None


def test_settings_config_dict() -> None:
    """Test that SettingsConfigDict is properly configured."""
    assert Settings.model_config["case_sensitive"] is False
    assert Settings.model_config["extra"] == "ignore"


def test_field_descriptions() -> None:
    """Test that all fields have descriptions."""
    fields = Settings.model_fields
    # SDL token now uses Console token, so description reflects this
    assert (
        fields["sdl_api_token"].description
        == "Authentication token for PowerQuery logs API (uses Console Token)"
    )
    assert (
        fields["graphql_service_token"].description
        == "Service token for SentinelOne OpsCenter Console API"
    )
    assert (
        fields["sentinelone_console_base_url"].description
        == "Base URL for Scalyr/SentinelOne console"
    )
    assert (
        fields["sentinelone_console_graphql_endpoint"].description
        == "GraphQL endpoint for Purple AI"
    )
    assert fields["purple_ai_account_id"].description == "Account ID for Purple AI user details"
    assert fields["purple_ai_team_token"].description == "Team token for Purple AI user details"
    assert (
        fields["purple_ai_email_address"].description == "Email address for Purple AI user details"
    )
    assert fields["purple_ai_user_agent"].description == "User agent for Purple AI user details"
    assert fields["purple_ai_build_date"].description == "Build date for Purple AI user details"
    assert fields["purple_ai_build_hash"].description == "Build hash for Purple AI user details"
    assert (
        fields["purple_ai_console_version"].description == "Version for Purple AI console details"
    )


def test_field_aliases() -> None:
    """Test that field validation aliases are correctly set."""
    fields = Settings.model_fields
    # Both SDL and Console tokens now use CONSOLE_TOKEN
    assert fields["sdl_api_token"].validation_alias == f"{ENV_PREFIX}CONSOLE_TOKEN"
    assert fields["graphql_service_token"].validation_alias == f"{ENV_PREFIX}CONSOLE_TOKEN"
    assert (
        fields["sentinelone_console_base_url"].validation_alias == f"{ENV_PREFIX}CONSOLE_BASE_URL"
    )
    assert (
        fields["sentinelone_console_graphql_endpoint"].validation_alias
        == f"{ENV_PREFIX}CONSOLE_GRAPHQL_ENDPOINT"
    )
    assert fields["purple_ai_account_id"].validation_alias == f"{ENV_PREFIX}PURPLE_AI_ACCOUNT_ID"
    assert fields["purple_ai_team_token"].validation_alias == f"{ENV_PREFIX}PURPLE_AI_TEAM_TOKEN"
    assert (
        fields["purple_ai_email_address"].validation_alias
        == f"{ENV_PREFIX}PURPLE_AI_EMAIL_ADDRESS"
    )
    assert fields["purple_ai_user_agent"].validation_alias == f"{ENV_PREFIX}PURPLE_AI_USER_AGENT"
    assert fields["purple_ai_build_date"].validation_alias == f"{ENV_PREFIX}PURPLE_AI_BUILD_DATE"
    assert fields["purple_ai_build_hash"].validation_alias == f"{ENV_PREFIX}PURPLE_AI_BUILD_HASH"
    assert (
        fields["purple_ai_console_version"].validation_alias
        == f"{ENV_PREFIX}PURPLE_AI_CONSOLE_VERSION"
    )


def test_env_var_priority(minimal_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that env vars are used correctly."""
    custom_base = "https://custom.example.test"
    custom_endpoint = "/custom/graphql"
    monkeypatch.setenv(f"{ENV_PREFIX}CONSOLE_BASE_URL", custom_base)
    monkeypatch.setenv(f"{ENV_PREFIX}CONSOLE_GRAPHQL_ENDPOINT", custom_endpoint)

    settings = Settings()
    assert settings.sentinelone_console_base_url == custom_base
    assert settings.sentinelone_console_graphql_endpoint == custom_endpoint
    assert settings.graphql_full_url == f"{custom_base}{custom_endpoint}"


def test_token_values_are_strings(minimal_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that token values are properly stored as strings."""
    console_token = "test_console_token_456"
    monkeypatch.setenv(f"{ENV_PREFIX}CONSOLE_TOKEN", console_token)

    settings = Settings()
    assert isinstance(settings.sdl_api_token, str)
    assert isinstance(settings.graphql_service_token, str)
    # Both tokens now use the same console token value
    assert settings.sdl_api_token == console_token
    assert settings.graphql_service_token == console_token


def test_uppercase_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that uppercase env var names work."""
    monkeypatch.setenv(f"{ENV_PREFIX}CONSOLE_TOKEN", "token2")
    monkeypatch.setenv(f"{ENV_PREFIX}CONSOLE_BASE_URL", "https://upper.example.test")
    monkeypatch.setenv(f"{ENV_PREFIX}CONSOLE_GRAPHQL_ENDPOINT", "/UPPER")

    settings = Settings()
    # Both tokens now use the same console token value
    assert settings.sdl_api_token == "token2"
    assert settings.graphql_service_token == "token2"
    assert settings.sentinelone_console_base_url == "https://upper.example.test"
    assert settings.sentinelone_console_graphql_endpoint == "/UPPER"


def test_mixed_case_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that mixed case env var names work due to case_sensitive=False."""
    monkeypatch.setenv("pUrPlEmCp_CoNsOlE_tOkEn", "mixed2")
    monkeypatch.setenv(f"{ENV_PREFIX}CONSOLE_BASE_URL", "https://mixed.example.test")

    settings = Settings()
    # Both tokens now use the same console token value
    assert settings.sdl_api_token == "mixed2"
    assert settings.graphql_service_token == "mixed2"
