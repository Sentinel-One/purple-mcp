"""SDL enumeration types and constants.

This module centralises *all* enumerations used by the Singularity Data
Lake (SDL) integration.  Providing a single, authoritative place for these
values guarantees parity with the backend API and prevents magic strings
from leaking throughout the codebase.

Key Components:
    - SDLQueryType: Discriminates high-level query categories returned by
      the `/analytics/queries` endpoint.
    - SDLPQResultType: Output representation for PowerQuery runs.
    - PQColumnType: Concrete value type of each column in a tabular result
      set.
    - SDLQueryPriority: Queue priority used by the scheduler.
    - SDLPQFrequency: Sampling frequency controlling aggregation granularity.
"""

from enum import StrEnum


class SDLQueryType(StrEnum):
    """Enum for SDL query types."""

    LOG = "LOG"
    TOP_FACETS = "TOP_FACETS"
    FACET_VALUES = "FACET_VALUES"
    PLOT = "PLOT"
    PQ = "PQ"
    DISTRIBUTION = "DISTRIBUTION"


class SDLPQResultType(StrEnum):
    """Enum for SDL PQ result types."""

    TABLE = "TABLE"
    PLOT = "PLOT"


class PQColumnType(StrEnum):
    """Enum for PQ column types."""

    NUMBER = "NUMBER"
    PERCENTAGE = "PERCENTAGE"
    STRING = "STRING"
    TIMESTAMP = "TIMESTAMP"


class SDLQueryPriority(StrEnum):
    """Enum for SDL query status."""

    LOW = "LOW"
    HIGH = "HIGH"


class SDLPQFrequency(StrEnum):
    """Enum for SDL PQ frequency."""

    LOW = "LOW"
    HIGH = "HIGH"
