"""Behavioral coverage for object-library state lowering."""

# Third Party
import pytest

# local repo modules
import pipeline.gen_object_library as gen_object_library
import pipeline.object_library_visual_states as object_library_visual_states


#============================================

def test_parse_visual_states_rejects_unknown_render_effect_keys() -> None:
	"""A misspelled render-effect key cannot disappear during lowering."""
	data = {
		"visual_states": {
			"held_material_volume": {
				"applies_to": "object",
				"render_effect": "fill_height",
				"target": "anchor_liquid_bounds",
				"clip": "anchor_liquid_clip",
				"capacity_ml": 10.0,
				"capacity_milliliters": 10.0,
			},
		},
	}

	with pytest.raises(ValueError, match="unknown render-effect keys"):
		object_library_visual_states.parse_visual_states(data, "inline_object.yaml")


#============================================

def test_parse_state_fields_separates_object_and_subpart_state() -> None:
	"""Subpart state cannot leak into the object's whole-item state schema."""
	data = {
		"state_fields": [
			{"field_name": "running", "type": "bool"},
			{
				"field_name": "material_name",
				"type": "enum",
				"applies_to": "subpart",
			},
		],
	}

	object_fields, subpart_fields = gen_object_library.parse_state_fields(
		data,
		"inline_object.yaml",
	)

	assert "running" in object_fields and "running" not in subpart_fields
	assert "material_name" in subpart_fields and "material_name" not in object_fields
