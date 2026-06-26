"""Utility functions for SDL integration."""

from datetime import UTC, datetime, timedelta
from typing import assert_never


def parse_time_param(time_param: datetime | timedelta) -> str:
    """Parses a datetime or timedelta object and returns a string representation of the time in milliseconds since epoch.

    Args:
        time_param: A datetime object or a timedelta object representing the time.

    Returns:
        The time in milliseconds since epoch as a string.
    """
    if isinstance(time_param, datetime):
        ms = str(int(time_param.timestamp() * 1_000))
        return ms
    elif isinstance(time_param, timedelta):
        now = datetime.now(UTC)
        target_time = now - time_param
        ms = str(int(target_time.timestamp() * 1_000))
        return ms
    assert_never(time_param)
