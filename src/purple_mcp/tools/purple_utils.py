"""Purple MCP utility tools.

This module provides general-purpose utility tools for the Purple MCP server.
These tools support common tasks like datetime conversions and formatting.

Key Components:
    - iso_to_unix_timestamp(): Converts ISO 8601 datetime strings to UNIX timestamps.

Usage:
    The tools are automatically registered when `purple_mcp.server` is imported
    but can also be called directly for testing:

    ```python
    from purple_mcp.tools.purple_utils import iso_to_unix_timestamp

    timestamp = await iso_to_unix_timestamp("2025-10-30T12:00:00Z")
    print(timestamp)  # 1761825600000
    ```

Dependencies:
    - datetime: Standard library for datetime parsing and manipulation.
"""

from datetime import datetime, timezone
from textwrap import dedent
from typing import Final

ISO_TO_UNIX_TIMESTAMP_DESCRIPTION: Final[str] = dedent(
    """
    Convert an ISO 8601 datetime string to a UNIX timestamp in milliseconds (UTC).

    This tool accepts datetime strings in ISO 8601 format and converts them to
    UNIX timestamps (milliseconds since epoch: January 1, 1970 00:00:00 UTC).
    This is essential for datetime filter queries in Purple Alert, Vulnerability,
    Misconfiguration, and Inventory searches.

    IMPORTANT: You should provide datetime inputs in the user's preferred timezone.
    This tool will automatically convert them to UTC timestamps for use in API queries.
    For example, if the user asks for "October 30, 2024 at 8 AM Eastern Time",
    you should submit "2024-10-30T08:00:00-04:00" (not convert it yourself to UTC).

    Args:
        iso_datetime (str): An ISO 8601 formatted datetime string. Examples:
            - "2025-10-30T12:00:00Z" (UTC with 'Z' suffix)
            - "2025-10-30T12:00:00+00:00" (UTC with explicit offset)
            - "2025-10-30T08:00:00-04:00" (Eastern Time with offset)
            - "2025-10-30T17:00:00+05:00" (IST/Pakistan Time with offset)
            - "2025-10-30T12:00:00" (no timezone - treated as UTC)

    Returns:
        str: The UNIX timestamp in milliseconds (UTC) as a JSON number string.
            Example: "1761825600000"

    Common Use Cases:
        - Converting user-friendly datetime inputs to UNIX timestamps for API queries
        - Handling datetimes across different time zones automatically
        - Preparing datetime filters for Alert, Vulnerability, Misconfiguration, and Inventory searches

    Examples:
        Input: "2025-10-30T12:00:00Z" (noon UTC)
        Output: "1761825600000"

        Input: "2025-10-30T08:00:00-04:00" (8 AM EDT = noon UTC)
        Output: "1761825600000"

        Input: "2025-10-30T17:00:00+05:00" (5 PM PKT = noon UTC)
        Output: "1761825600000"

    Raises:
        ValueError: If the input string is not a valid ISO 8601 datetime format.

    Notes:
        - All timestamps are returned in milliseconds (not seconds or nanoseconds)
        - All timestamps represent UTC time regardless of input timezone
        - If no timezone is specified in input, UTC is assumed
        - The tool handles timezone conversion automatically - provide times in the user's local timezone
    """
).strip()


async def iso_to_unix_timestamp(iso_datetime: str) -> str:
    """Convert an ISO 8601 datetime string to UNIX timestamp in milliseconds.

    Args:
        iso_datetime: ISO 8601 formatted datetime string.

    Returns:
        UNIX timestamp in milliseconds as a string.

    Raises:
        ValueError: If the datetime string is not a valid ISO 8601 format.
    """
    try:
        # Parse the ISO 8601 datetime string
        dt = datetime.fromisoformat(iso_datetime.replace("Z", "+00:00"))

        # If no timezone info, assume UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        # Convert to UNIX timestamp in milliseconds
        timestamp_ms = int(dt.timestamp() * 1000)

        return str(timestamp_ms)

    except ValueError as e:
        raise ValueError(
            f"Invalid ISO 8601 datetime format: '{iso_datetime}'. "
            f"Expected format like '2025-10-30T12:00:00Z'. Error: {e}"
        ) from e
    except Exception as e:
        raise ValueError(
            f"Failed to convert datetime '{iso_datetime}' to UNIX timestamp: {e}"
        ) from e
