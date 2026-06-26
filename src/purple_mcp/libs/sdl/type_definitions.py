"""Type definitions for SDL API integration."""

from typing import Final, TypeAlias

from pydantic import JsonValue

JsonDict: TypeAlias = dict[str, JsonValue]

SDL_QUERY_ORIGIN_PATTERN: Final = r"^[a-z0-9]([a-z0-9_-]{0,62}[a-z0-9])?$"
