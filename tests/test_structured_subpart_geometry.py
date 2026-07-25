"""Behavioral coverage for recorded structured-object material regions."""

import pipeline.gen_object_library as gen_object_library


#============================================

def test_legacy_subpart_pair_lowers_by_shared_prefix_not_object_name() -> None:
	"""A differently named pair receives the same typed subpart render contract."""
	visual_states = {
		"culture_material_name": {
			"applies_to": "subpart",
			"kind": "svg",
			"cases": [
				{"when": "empty", "output": {"asset_name": "rack_asset"}},
				{"when": "media", "output": {"asset_name": "rack_asset"}},
			],
		},
		"culture_material_volume": {
			"applies_to": "subpart",
			"kind": "composite",
			"formula": "fill_height(state(culture_material_volume), capacity_ul=1000)",
		},
	}

	lowered = gen_object_library.lower_legacy_subpart_material_effects(
		visual_states, "inline.yaml", has_subpart_geometry=True
	)

	tint_effect = lowered["culture_material_name"]
	fill_effect = lowered["culture_material_volume"]
	assert tint_effect["render_effect"] == "material_tint" and tint_effect["target"] == "subpart_geometry"
	assert fill_effect["render_effect"] == "fill_height" and fill_effect["capacity_ul"] == 1000.0
