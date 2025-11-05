"""Utility helpers for Singularity Data Lake.

A small collection of helper functions that are shared across SDL
components.  Keeping them in one lightweight module avoids repeated
implementations and circular import issues.

Key Components:
    - parse_time_param(): Convert `datetime` or `timedelta` objects into the
      millisecond timestamp strings expected by the SDL APIs.

Usage:
    ```python
    from purple_mcp.libs.sdl.utils import parse_time_param

    # Absolute time (timezone-aware datetime required)
    now_ms = parse_time_param(datetime.now(timezone.utc))

    # Relative offset (last 15 minutes)
    since_ms = parse_time_param(timedelta(minutes=15))
    ```

Architecture:
    Pure functions with no external side-effects so they can be imported
    from any layer (handlers, models, CLI) without risk.

Dependencies:
    datetime: Used for time manipulation and epoch conversion.
    typing.assert_never: Helps mypy ensure exhaustive `isinstance` checks.
"""

from datetime import datetime, timedelta, timezone

from typing_extensions import assert_never


def parse_time_param(time_param: datetime | timedelta) -> str:
    """Parses a datetime or timedelta object and returns a string representation of the time in milliseconds since epoch.

    Args:
        time_param: A timezone-aware datetime object or a timedelta object representing the time.
            For datetime objects, timezone information is required.

    Returns:
        The time in milliseconds since epoch as a string.

    Raises:
        ValueError: If time_param is a timezone-naive datetime object.
    """
    if isinstance(time_param, datetime):
        if time_param.tzinfo is None:
            raise ValueError("Timezone-naive time_param is not allowed.")
        return str(int(time_param.timestamp() * 1_000))
    if isinstance(time_param, timedelta):
        now = datetime.now(timezone.utc)
        target_time = now - time_param
        return str(int(target_time.timestamp() * 1_000))
    assert_never(time_param)
