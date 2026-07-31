"""Stable coverage for structured-grid subpart expansion in the SVG audit."""

import pytest

import validation.svg.asset_audit as asset_audit


def test_lettered_grid_expands_every_rack_slot() -> None:
	"""A 2x4 lettered rack names its visible slots row-major as A then B."""
	object_data = {
		"structure": {
			"layout": "grid",
			"rows": 2,
			"cols": 4,
			"name_pattern": "slot_{row_letter}{col}",
		}
	}
	expected = {
		"slot_A1", "slot_A2", "slot_A3", "slot_A4",
		"slot_B1", "slot_B2", "slot_B3", "slot_B4",
	}
	assert asset_audit.get_expected_subparts("microtube_rack_8", object_data) == expected


def test_numeric_grid_patterns_keep_their_existing_names() -> None:
	"""Numeric row and column patterns retain the prior one-based expansion."""
	object_data = {
		"structure": {
			"layout": "grid",
			"rows": 2,
			"cols": 3,
			"name_pattern": "lane_{row}_{col}",
		}
	}
	expected = {"lane_1_1", "lane_1_2", "lane_1_3", "lane_2_1", "lane_2_2", "lane_2_3"}
	assert asset_audit.get_expected_subparts("numeric_grid", object_data) == expected


def test_lettered_grid_rejects_rows_outside_the_authoring_vocabulary() -> None:
	"""The audit gives an author-facing error instead of emitting punctuation."""
	object_data = {
		"structure": {
			"layout": "grid",
			"rows": 27,
			"cols": 1,
			"name_pattern": "slot_{row_letter}{col}",
		}
	}
	with pytest.raises(ValueError, match="at most 26 rows"):
		asset_audit.get_expected_subparts("oversized_rack", object_data)
