"""Presets for the set of fields to return from Inventory listings / searches.

This module defines three field presets for controlling the amount of data returned
from inventory API queries:

MINIMAL (7 fields):
    Core identification and classification fields. Use for high-volume queries,
    browsing, or when you only need basic asset information.
    Fields: id, idSecondary, name, category, resourceType, assetStatus, surfaces

STANDARD (13 fields):
    MINIMAL plus operational context fields. Balanced preset for most use cases
    requiring security and operational status information.
    Additional fields: lastActiveDt, infectionStatus, assetCriticality,
                       activeCoverage, missingCoverage, riskFactors

ALL (~200+ fields):
    All available fields from the InventoryItem model. Use when you need complete
    asset information. Note: Larger payload size impacts performance.

Performance note:
    Requesting fewer fields reduces network transfer, JSON parsing overhead, and
    memory usage. Prefer MINIMAL for list/search operations; use ALL only when
    retrieving specific items or when comprehensive data is required.

Field name format:
    All field names use camelCase (API format), e.g., 'resourceType', 'assetStatus'.
"""

from enum import Enum
from typing import Final, Literal, TypeAlias, final

from purple_mcp.libs.inventory.models import InventoryItem

_ALL_FIELDS: Final = tuple(
    field if (field := InventoryItem.model_fields[item_name].alias) is not None else item_name
    for item_name in InventoryItem.model_fields
)


_MINIMAL_FIELDS: Final = (
    "id",
    "idSecondary",
    "name",
    "category",
    "resourceType",
    "assetStatus",
    "surfaces",
)

_STANDARD_EXTRA_FIELDS: Final = (
    "lastActiveDt",
    "infectionStatus",
    "assetCriticality",
    "activeCoverage",
    "missingCoverage",
    "riskFactors",
)

_STANDARD_FIELDS: Final = _MINIMAL_FIELDS + _STANDARD_EXTRA_FIELDS


@final
class InventoryFetchFieldsPreset(Enum):
    """Suggested field-sets to return from Inventory queries.

    Attributes:
        MINIMAL: 7 core fields (id, name, category, resourceType, assetStatus, etc.)
        STANDARD: MINIMAL + 6 operational fields (lastActiveDt, infectionStatus, etc.)
        ALL: All available fields from InventoryItem model (~200+ fields)

    Example:
        >>> preset = InventoryFetchFieldsPreset.MINIMAL
        >>> fields = list(preset.value)
        >>> print(fields)
        ['id', 'idSecondary', 'name', 'category', 'resourceType', 'assetStatus', 'surfaces']
    """

    MINIMAL = _MINIMAL_FIELDS
    STANDARD = _STANDARD_FIELDS
    ALL = _ALL_FIELDS


InventoryFetchFieldsPresetName: TypeAlias = Literal["MINIMAL", "STANDARD", "ALL"]
