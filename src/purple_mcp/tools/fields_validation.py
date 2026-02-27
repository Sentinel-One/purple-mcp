"""Shared validation for tool `fields` parameters."""

import json
from typing import Final

MAX_FIELDS_COUNT: Final = 50
MAX_FIELD_LENGTH: Final = 1024
MAX_FIELDS_JSON_LENGTH: Final = 8192


def parse_fields_parameter(fields: str | None) -> list[str] | None:
    """Parse and validate a JSON-encoded fields list.

    Args:
        fields: JSON string containing an array of field names, or None.

    Returns:
        Parsed list of field names, or None if no fields were provided.

    Raises:
        ValueError: If the payload is too large, malformed, or exceeds configured limits.
    """
    if fields is None:
        return None

    if len(fields) > MAX_FIELDS_JSON_LENGTH:
        raise ValueError(
            f"Fields payload is too large: {len(fields)} characters. "
            f"Maximum allowed: {MAX_FIELDS_JSON_LENGTH}"
        )

    try:
        parsed = json.loads(fields)
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in fields parameter: {error}") from error

    if not isinstance(parsed, list):
        raise ValueError("Fields must be an array of field names")

    if len(parsed) > MAX_FIELDS_COUNT:
        raise ValueError(f"Too many fields: {len(parsed)}. Maximum allowed: {MAX_FIELDS_COUNT}")

    for index, item in enumerate(parsed):
        if not isinstance(item, str):
            raise ValueError(
                f"All field names must be strings, but element at index {index} "
                f"is {type(item)}: {item!r}"
            )
        if len(item) > MAX_FIELD_LENGTH:
            raise ValueError(
                f"Field at index {index} is too long: {len(item)} characters. "
                f"Maximum allowed: {MAX_FIELD_LENGTH}"
            )

    return parsed
