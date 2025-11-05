"""Common type definitions used throughout the purple-mcp package.

This module contains globally-shared type aliases that are used across
multiple subpackages. Following Python best practices, this module uses
the name type_defs.py to avoid shadowing the standard library types module.
"""

from typing import TypeAlias

from pydantic import JsonValue

JsonDict: TypeAlias = dict[str, JsonValue]

__all__ = ["JsonDict"]
