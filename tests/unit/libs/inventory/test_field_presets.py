"""Unit tests for inventory field presets."""

from typing import get_args

import pytest

from purple_mcp.libs.inventory.field_presets import (
    InventoryFetchFieldsPreset,
    InventoryFetchFieldsPresetName,
)


class TestFieldPresets:
    """Test field preset constants."""

    @pytest.mark.parametrize(
        "preset",
        [
            InventoryFetchFieldsPreset.MINIMAL,
            InventoryFetchFieldsPreset.STANDARD,
        ],
    )
    def test_preset_fields_in_all_fields(self, preset: InventoryFetchFieldsPreset) -> None:
        """Test that all elements of preset fields are in ALL preset."""
        all_fields_set = set(InventoryFetchFieldsPreset.ALL.value)
        preset_fields_set = set(preset.value)

        missing_fields = preset_fields_set - all_fields_set
        assert not missing_fields, (
            f"The following fields in {preset.name} are not in ALL preset: {missing_fields}"
        )

    def test_minimal_fields_subset_of_standard_fields(self) -> None:
        """Test that MINIMAL is a subset of STANDARD."""
        minimal_fields_set = set(InventoryFetchFieldsPreset.MINIMAL.value)
        standard_fields_set = set(InventoryFetchFieldsPreset.STANDARD.value)

        assert minimal_fields_set.issubset(standard_fields_set), (
            f"Some fields in MINIMAL are not in STANDARD: "
            f"{minimal_fields_set - standard_fields_set}"
        )

    @pytest.mark.parametrize(
        "preset",
        [
            InventoryFetchFieldsPreset.MINIMAL,
            InventoryFetchFieldsPreset.STANDARD,
        ],
    )
    def test_field_preset_not_empty(self, preset: InventoryFetchFieldsPreset) -> None:
        """Test that field preset is not empty."""
        assert len(preset.value) > 0, f"{preset.name} should not be empty"

    @pytest.mark.parametrize(
        "preset",
        [
            InventoryFetchFieldsPreset.MINIMAL,
            InventoryFetchFieldsPreset.STANDARD,
        ],
    )
    def test_field_preset_contains_strings(self, preset: InventoryFetchFieldsPreset) -> None:
        """Test that field preset contains only strings."""
        all_valid = all(isinstance(field, str) for field in preset.value)
        assert all_valid, f"{preset.name} should contain only strings"

    def test_all_fields_not_empty(self) -> None:
        """Test that ALL preset is not empty."""
        assert len(InventoryFetchFieldsPreset.ALL.value) > 0, "ALL preset should not be empty"

    def test_all_fields_contains_strings(self) -> None:
        """Test that ALL preset contains only strings."""
        all_valid = all(isinstance(field, str) for field in InventoryFetchFieldsPreset.ALL.value)
        assert all_valid, "ALL preset should contain only strings"

    def test_string_literal_type_matches_enum(self) -> None:
        """Test that string literal definition is in sync with enum definition."""
        assert set(get_args(InventoryFetchFieldsPresetName)) == {
            preset.name for preset in InventoryFetchFieldsPreset
        }
