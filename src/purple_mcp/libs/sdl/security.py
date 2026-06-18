"""Shared TLS security validation utilities for SDL components.

This module provides centralized TLS security validation logic to ensure
consistency across SDL configuration and client initialization.

All functions in this module accept an explicit environment parameter rather
than reading from global environment variables, following library design
principles of explicit configuration.
"""

import logging
import os
import warnings
from typing import Final

logger = logging.getLogger(__name__)

# Security-related constants
RELEASE_ENVIRONMENTS: Final[tuple[str, ...]] = ("release", "production", "prod")
TESTING_ENVIRONMENTS: Final[tuple[str, ...]] = ("testing", "test", "staging", "stage")
DEVELOPMENT_ENVIRONMENTS: Final[tuple[str, ...]] = ("development", "dev")

# Standard security messages
TLS_BYPASS_VALIDATION_ERROR: Final[str] = (
    "TLS verification bypass is FORBIDDEN in release environments. "
    "This is a critical security risk that could expose sensitive data."
)

TLS_BYPASS_WARNING_MESSAGE: Final[str] = (
    "SECURITY WARNING: TLS certificate verification is DISABLED! "
    "This creates a security vulnerability allowing man-in-the-middle attacks. "
    "Only use this in development/testing environments with trusted networks."
)

TLS_BYPASS_CRITICAL_LOG: Final[str] = (
    "TLS CERTIFICATE VERIFICATION IS DISABLED! "
    "This is a CRITICAL SECURITY RISK that should NEVER be used in release environments. "
    "All HTTPS connections are vulnerable to man-in-the-middle attacks."
)

TLS_BYPASS_CLIENT_LOG: Final[str] = (
    "SDL Query Client initialized with TLS verification DISABLED! "
    "This is a CRITICAL SECURITY RISK - all HTTPS connections are vulnerable to interception."
)

TLS_CLIENT_INIT_WARNING: Final[str] = (
    "SECURITY WARNING: Creating SDL client for {target_url} with TLS verification DISABLED! "
    "This creates a security vulnerability allowing man-in-the-middle attacks. "
    "Only use this in development/testing environments with trusted networks."
)

NON_DEV_ENVIRONMENT_WARNING: Final[str] = (
    "TLS verification disabled in this environment! "
    "This configuration should only be used in development/testing."
)


def is_release_environment(environment: str | None = None) -> bool:
    """Check if the specified environment is a release environment.

    Args:
        environment: Environment string to check. If None, reads from PURPLEMCP_ENV
            environment variable (defaults to "release" if not set).

    Returns:
        True if the environment is considered a release environment.

    Note:
        For library usage, prefer passing environment explicitly rather than
        relying on the implicit environment variable lookup.
    """
    if environment is None:
        environment = os.getenv("PURPLEMCP_ENV", "release")
    return environment.lower() in RELEASE_ENVIRONMENTS


def is_testing_environment(environment: str | None = None) -> bool:
    """Check if the specified environment is testing-like.

    Args:
        environment: Environment string to check. If None, reads from PURPLEMCP_ENV
            environment variable (defaults to "release" if not set).

    Returns:
        True if the environment is considered a testing environment.

    Note:
        For library usage, prefer passing environment explicitly rather than
        relying on the implicit environment variable lookup.
    """
    if environment is None:
        environment = os.getenv("PURPLEMCP_ENV", "release")
    return environment.lower() in TESTING_ENVIRONMENTS


def is_development_environment(environment: str | None = None) -> bool:
    """Check if the specified environment is development-like.

    Args:
        environment: Environment string to check. If None, reads from PURPLEMCP_ENV
            environment variable (defaults to "release" if not set).

    Returns:
        True if the environment is considered a development environment.

    Note:
        For library usage, prefer passing environment explicitly rather than
        relying on the implicit environment variable lookup.
    """
    if environment is None:
        environment = os.getenv("PURPLEMCP_ENV", "release")
    return environment.lower() in DEVELOPMENT_ENVIRONMENTS


def is_non_release_environment(environment: str | None = None) -> bool:
    """Check if the specified environment is non-release (development or testing).

    Args:
        environment: Environment string to check. If None, reads from PURPLEMCP_ENV
            environment variable (defaults to "release" if not set).

    Returns:
        True if the environment is development or testing (non-release).

    Note:
        For library usage, prefer passing environment explicitly rather than
        relying on the implicit environment variable lookup.
    """
    return is_development_environment(environment) or is_testing_environment(environment)


def validate_tls_bypass_config(skip_tls_verify: bool, environment: str | None = None) -> None:
    """Validate TLS bypass configuration with security checks.

    This function performs comprehensive validation of TLS bypass settings,
    including environment checks, warnings, and logging.

    Args:
        skip_tls_verify: Whether TLS verification bypass is requested.
        environment: The environment string to validate against. If None, reads from
            PURPLEMCP_ENV environment variable (defaults to "release" if not set).

    Raises:
        ValueError: If TLS bypass is attempted in release environments.

    Note:
        For library usage, prefer passing environment explicitly rather than
        relying on the implicit environment variable lookup.
    """
    if not skip_tls_verify:
        return

    # Get environment if not provided
    if environment is None:
        environment = os.getenv("PURPLEMCP_ENV", "release")

    # Strict release environment protection
    if is_release_environment(environment):
        raise ValueError(TLS_BYPASS_VALIDATION_ERROR)

    # Issue strong security warning
    warnings.warn(
        TLS_BYPASS_WARNING_MESSAGE,
        UserWarning,
        stacklevel=6,  # Adjust stack level to point to user's create_sdl_settings() call
    )

    # Log critical security warning
    logger.warning(
        "TLS certificate verification is DISABLED - SECURITY RISK! "
        "This should NEVER be used in release environments."
    )

    # Log comprehensive security information
    logger.critical(TLS_BYPASS_CRITICAL_LOG, extra={"environment": environment})

    # Additional warning for non-development environments
    if not is_development_environment(environment):
        logger.error(NON_DEV_ENVIRONMENT_WARNING, extra={"environment": environment})


def validate_tls_bypass_client(
    skip_tls_verify: bool, target_url: str, environment: str | None = None
) -> None:
    """Validate TLS bypass for client initialization with runtime checks.

    This function performs runtime validation when creating SDL clients,
    with specific logging for the target URL.

    Args:
        skip_tls_verify: Whether TLS verification bypass is requested.
        target_url: The target URL for the client connection.
        environment: The environment string to validate against. If None, reads from
            PURPLEMCP_ENV environment variable (defaults to "release" if not set).

    Raises:
        ValueError: If TLS bypass is attempted in release environments.

    Note:
        For library usage, prefer passing environment explicitly rather than
        relying on the implicit environment variable lookup.
    """
    if not skip_tls_verify:
        return

    # Get environment if not provided
    if environment is None:
        environment = os.getenv("PURPLEMCP_ENV", "release")

    # Runtime release environment protection
    if is_release_environment(environment):
        raise ValueError(
            f"SECURITY ERROR: TLS verification bypass is FORBIDDEN in release environments. "
            f"Current environment: {environment}. This is a critical security vulnerability."
        )

    # Issue runtime security warning
    warnings.warn(
        TLS_CLIENT_INIT_WARNING.format(target_url=target_url),
        UserWarning,
        stacklevel=4,  # Adjust stack level to point to user's SDLQueryClient() call
    )

    # Log client-specific security warning
    logger.critical(
        TLS_BYPASS_CLIENT_LOG,
        extra={"target_url": target_url, "environment": environment},
    )


def log_tls_bypass_initialization(target_url: str, environment: str | None = None) -> None:
    """Log TLS bypass during HTTP client initialization.

    Args:
        target_url: The target URL for the HTTP client.
        environment: The environment string for logging context. If None, reads from
            PURPLEMCP_ENV environment variable (defaults to "release" if not set).

    Note:
        For library usage, prefer passing environment explicitly rather than
        relying on the implicit environment variable lookup.
    """
    if environment is None:
        environment = os.getenv("PURPLEMCP_ENV", "release")

    logger.critical(
        "Initializing HTTP client with TLS verification DISABLED - vulnerable to man-in-the-middle attacks",
        extra={"target_url": target_url, "environment": environment},
    )


def log_tls_bypass_request(method: str, path: str) -> None:
    """Log TLS bypass for individual HTTP requests.

    Args:
        method: HTTP method (GET, POST, etc.).
        path: Request path.
    """
    logger.warning("TLS bypass request made", extra={"method": method, "path": path})


def get_security_context(environment: str | None = None) -> dict[str, str]:
    """Get security context information for a given environment.

    Args:
        environment: The environment string to generate context for. If None, reads from
            PURPLEMCP_ENV environment variable (defaults to "release" if not set).

    Returns:
        Dictionary containing security-relevant environment information.

    Note:
        For library usage, prefer passing environment explicitly rather than
        relying on the implicit environment variable lookup.
    """
    if environment is None:
        environment = os.getenv("PURPLEMCP_ENV", "release")

    return {
        "environment": environment,
        "is_release": str(is_release_environment(environment)).lower(),
        "is_testing": str(is_testing_environment(environment)).lower(),
        "is_development": str(is_development_environment(environment)).lower(),
        "tls_bypass_allowed": str(not is_release_environment(environment)).lower(),
    }


def validate_security_configuration(environment: str | None = None) -> None:
    """Validate security configuration and log status for a given environment.

    This function can be called during application startup to validate
    and log the security configuration.

    Args:
        environment: The environment string to validate. If None, reads from
            PURPLEMCP_ENV environment variable (defaults to "release" if not set).

    Note:
        For library usage, prefer passing environment explicitly rather than
        relying on the implicit environment variable lookup.
    """
    if environment is None:
        environment = os.getenv("PURPLEMCP_ENV", "release")

    context = get_security_context(environment)

    logger.info("SDL Security Configuration:")
    logger.info("Environment configured", extra={"environment": context["environment"]})
    logger.info("Release Environment configured", extra={"is_release": context["is_release"]})
    logger.info(
        "Development Environment configured", extra={"is_development": context["is_development"]}
    )
    logger.info(
        "TLS Bypass Allowed configured",
        extra={"tls_bypass_allowed": context["tls_bypass_allowed"]},
    )

    if context["is_release"] == "true":
        logger.info("Release environment detected - TLS bypass is FORBIDDEN")
    else:
        logger.warning("Non-release environment - TLS bypass allowed with warnings")
