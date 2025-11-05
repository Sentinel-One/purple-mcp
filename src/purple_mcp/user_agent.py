"""User-Agent string generation for HTTP requests.

This module provides functionality to build consistent User-Agent headers
for HTTP requests, including version information for request tracking and
debugging in production environments.
"""

import logging
from functools import cache

logger = logging.getLogger(__name__)


@cache
def get_version() -> str:
    """Retrieve the package version string.

    Returns the version from the purple_mcp package's __version__ attribute,
    falling back to "unknown" if the version cannot be determined. This
    implementation is platform-agnostic and works with all installation methods.

    Returns:
        Semantic version string (e.g., "0.1.0"), or "unknown" if unavailable.
    """
    try:
        from purple_mcp import __version__

        logger.debug("Retrieved version from __version__", extra={"version": __version__})
        return __version__

    except (ImportError, AttributeError):
        logger.debug("Could not retrieve __version__ from purple_mcp package")
        return "unknown"
    except Exception:
        logger.exception("Error retrieving __version__ from purple_mcp package")
        return "unknown"


@cache
def get_user_agent() -> str:
    """Construct the User-Agent header value for HTTP requests.

    Builds a formatted User-Agent string following the pattern:
    sentinelone/purple-mcp (version <version>)

    Returns:
        Formatted User-Agent header value.
    """
    version = get_version()
    user_agent = f"sentinelone/purple-mcp (version {version})"
    logger.debug("Built User-Agent string", extra={"user_agent": user_agent})
    return user_agent
