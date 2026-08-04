# Behavioral tests for subpart-aware state in the stepper (WP-STEPPER / D1).
#
# These tests exercise the mechanism, not constants: that an object-level write
# validates against the object-level field decl, a subpart write validates
# against the applies_to: subpart decl, per-subpart state is independent, a
# subpart-group cascade reaches the named member wells, and an unregistered
# material still fails. Fixtures are built in-memory so the tests stay fast and
# do not touch the real content tree.

# local repo modules
from pathlib import Path

import file_utils
from validation.yaml_schema.database import ContentDatabase
from validation.stepper.loader import LoadedContentTree
from validation.stepper.findings import FindingEmitter, Level
from validation.stepper.state import StateMap
from validation.stepper.scene_ops import apply_scene_operation

file_utils.get_repo_root()


#============================================
# Fixture construction (in-memory content tree)
#============================================

PLATE_OBJECT = {
	"object_name": "mini_plate",
	"kind": "plate",
	"structure": {
		"subpart_kind": "well",
		"layout": "grid",
		"rows": 1,
		"cols": 3,
		"name_pattern": "{row_letter}{col}",
		"subpart_groups": {
			"rows": {
				"group_kind": "row",
				"members": [
					{"name": "row_A", "contains": ["A1", "A2", "A3"]},
				],
			},
		},
	},
	"state_fields": [
		{
			"field_name": "inspection_status",
			"type": "enum",
			"allowed": ["not_inspected", "cells_healthy"],
			"default": "not_inspected",
			"applies_to": "object",
		},
		{
			"field_name": "material_name",
			"type": "enum",
			# A leftover object-level allowed list that must NOT gate subpart
			# writes (D1 registry-backed membership replaces it for subparts).
			"allowed": ["empty"],
			"default": "empty",
			"applies_to": "subpart",
		},
		{
			"field_name": "material_volume",
			"type": "float",
			"unit": "ul",
			"min": 0,
			"max": 1000,
			"default": 0,
			"applies_to": "subpart",
		},
	],
	"capabilities": ["clickable", "structured_surface", "material_container"],
}

BASE_SCENE = {
	"scene_name": "bench",
	"placements": [
		{"placement_name": "plate_1", "object_name": "mini_plate"},
	],
}

PROTOCOL = {
	"protocol_name": "p1",
	"protocol_type": "mini_protocol",
	"entry_step": "s1",
	"steps": [],
}

MATERIALS = {
	"carboplatin": {"label": "Carboplatin", "display_color": "#a719db"},
	"media": {"label": "Media", "display_color": "#6c6c00"},
}


def build_state_map() -> tuple[StateMap, FindingEmitter]:
	"""Build a StateMap over the in-memory plate fixture and set the scene."""
	db = ContentDatabase()
	db.objects["mini_plate"] = PLATE_OBJECT
	db.base_scenes["bench"] = BASE_SCENE
	db.protocols["p1"] = PROTOCOL
	db.materials_by_protocol["p1"] = MATERIALS

	tree = LoadedContentTree(db, root_path=None)
	emitter = FindingEmitter()
	state_map = StateMap(tree, "p1", emitter)
	state_map.set_active_scene("bench", "content/base_scenes/bench.yaml")
	return state_map, emitter


def error_codes(emitter: FindingEmitter) -> list[str]:
	"""Collect the codes of ERROR-level findings."""
	codes = [f.code for f in emitter.findings if f.level == Level.ERROR]
	return codes


def state_change_op(target: str, state: dict) -> dict:
	"""Build an ObjectStateChange scene_operation dict."""
	op = {"type": "ObjectStateChange", "target": target, "state": state}
	return op


def apply(state_map: StateMap, emitter: FindingEmitter, op: dict) -> bool:
	"""Apply one scene op through the real scene_ops dispatch."""
	tree = state_map.tree
	result = apply_scene_operation(op, state_map, "p1", "s1", 0, emitter, tree)
	return result


#============================================
# Object-level vs subpart-level schema selection
#============================================

def test_object_level_write_validates_against_object_field():
	# A bare-object write of an object-scoped enum must succeed against the
	# object decl and land in the object-level record.
	state_map, emitter = build_state_map()
	ok = apply(state_map, emitter, state_change_op("mini_plate", {"inspection_status": "cells_healthy"}))
	assert ok is True
	assert error_codes(emitter) == []
	object_state = state_map.get_placement_state("plate_1")["state"]
	assert object_state["inspection_status"] == "cells_healthy"


def test_object_level_enum_still_rejects_bad_value():
	# The object-scoped enum gate still fires for an out-of-enum object write.
	state_map, emitter = build_state_map()
	ok = apply(state_map, emitter, state_change_op("mini_plate", {"inspection_status": "glowing"}))
	assert ok is False
	assert "state_value_not_allowed" in error_codes(emitter)


def test_subpart_write_validates_against_subpart_field_not_object_enum():
	# A subpart material write of a registered material must pass even though the
	# object-level material decl carries a narrow allowed list. The D1 predicate
	# (sentinel-or-registry) governs the subpart, not the leftover enum.
	state_map, emitter = build_state_map()
	ok = apply(state_map, emitter, state_change_op("mini_plate.A1", {"material_name": "carboplatin"}))
	assert ok is True
	assert "state_value_not_allowed" not in error_codes(emitter)
	subpart_state = state_map.get_subpart_state("plate_1", "A1")["state"]
	assert subpart_state["material_name"] == "carboplatin"


#============================================
# Per-subpart independence
#============================================

def test_two_wells_hold_different_values_simultaneously():
	# Independent subpart records: A1 and A2 keep distinct materials at once.
	state_map, emitter = build_state_map()
	apply(state_map, emitter, state_change_op("mini_plate.A1", {"material_name": "carboplatin"}))
	apply(state_map, emitter, state_change_op("mini_plate.A2", {"material_name": "media"}))
	a1 = state_map.get_subpart_state("plate_1", "A1")["state"]["material_name"]
	a2 = state_map.get_subpart_state("plate_1", "A2")["state"]["material_name"]
	assert a1 == "carboplatin"
	assert a2 == "media"


def test_later_write_does_not_overwrite_object_or_other_well():
	# A write to A2 must not change A1's record nor the object-level record.
	state_map, emitter = build_state_map()
	apply(state_map, emitter, state_change_op("mini_plate", {"inspection_status": "cells_healthy"}))
	apply(state_map, emitter, state_change_op("mini_plate.A1", {"material_name": "carboplatin"}))
	apply(state_map, emitter, state_change_op("mini_plate.A2", {"material_name": "media"}))

	# Object-level record carries no per-well material; its own field is intact.
	object_state = state_map.get_placement_state("plate_1")["state"]
	assert object_state["inspection_status"] == "cells_healthy"
	assert "material_name" not in object_state

	# A1 is untouched by the later A2 write.
	assert state_map.get_subpart_state("plate_1", "A1")["state"]["material_name"] == "carboplatin"


#============================================
# Subpart-group cascade
#============================================

def test_group_cascade_reaches_each_member_well():
	# A row write must color every member well in place (A1, A2, A3).
	state_map, emitter = build_state_map()
	ok = apply(state_map, emitter, state_change_op("mini_plate.row_A", {"material_name": "carboplatin"}))
	assert ok is True
	for well in ("A1", "A2", "A3"):
		record = state_map.get_subpart_state("plate_1", well)
		assert record is not None
		assert record["state"]["material_name"] == "carboplatin"


#============================================
# Invalid material still fails
#============================================

def test_unregistered_subpart_material_does_not_store():
	# An unregistered, non-sentinel material must not land in the subpart record;
	# the write fails (the s-unregistered gate owns the surfaced finding).
	state_map, emitter = build_state_map()
	ok = apply(state_map, emitter, state_change_op("mini_plate.A1", {"material_name": "unobtanium"}))
	assert ok is False
	assert state_map.get_subpart_state("plate_1", "A1") is None


def test_sentinel_subpart_material_is_accepted():
	# A sentinel value (empty) is always valid for a subpart material write.
	state_map, emitter = build_state_map()
	ok = apply(state_map, emitter, state_change_op("mini_plate.A1", {"material_name": "empty"}))
	assert ok is True
	assert state_map.get_subpart_state("plate_1", "A1")["state"]["material_name"] == "empty"


#============================================
# Closed built-in names vs registry-required names (sentinel allowlist narrowing)
#============================================
#
# After narrowing the stepper allowlist to exactly {empty, mixed}, the only
# material names that bypass the registry are the non-rendering sentinel "empty"
# and the built-in visible material "mixed". Every other name -- including the
# biological identity "cells", the assay product "formazan", and the disposal
# streams "waste_*" -- must be registered. These tests prove the gate now bites
# for those names when unregistered and lets them through once registered.


def build_state_map_with_materials(extra_materials: dict) -> tuple[StateMap, FindingEmitter]:
	"""Build a StateMap whose registry adds extra_materials to the base set."""
	db = ContentDatabase()
	db.objects["mini_plate"] = PLATE_OBJECT
	db.base_scenes["bench"] = BASE_SCENE
	db.protocols["p1"] = PROTOCOL
	merged_materials = dict(MATERIALS)
	merged_materials.update(extra_materials)
	db.materials_by_protocol["p1"] = merged_materials

	tree = LoadedContentTree(db, root_path=None)
	emitter = FindingEmitter()
	state_map = StateMap(tree, "p1", emitter)
	state_map.set_active_scene("bench", "content/base_scenes/bench.yaml")
	return state_map, emitter


def test_empty_passes_without_registration():
	# "empty" is the non-rendering sentinel: valid for a subpart write with no
	# registry entry. Its transparent/null resolution is the color resolver's job
	# (see tests/test_material_color.mjs), not the stepper's.
	state_map, emitter = build_state_map()
	ok = apply(state_map, emitter, state_change_op("mini_plate.A1", {"material_name": "empty"}))
	assert ok is True
	assert state_map.get_subpart_state("plate_1", "A1")["state"]["material_name"] == "empty"


def test_mixed_passes_without_registration():
	# "mixed" is the only built-in visible material: valid for a subpart write
	# with no registry entry. The built-in color (#686868) is resolved at the
	# color-resolver layer (tests/test_material_color.mjs), not in the stepper.
	state_map, emitter = build_state_map()
	ok = apply(state_map, emitter, state_change_op("mini_plate.A1", {"material_name": "mixed"}))
	assert ok is True
	assert state_map.get_subpart_state("plate_1", "A1")["state"]["material_name"] == "mixed"


def test_cells_fail_when_not_registered():
	# "cells" is no longer in the allowlist; an unregistered write fails and the
	# value is not stored (the s-unregistered gate owns the surfaced finding).
	state_map, emitter = build_state_map()
	ok = apply(state_map, emitter, state_change_op("mini_plate.A1", {"material_name": "cells"}))
	assert ok is False
	assert state_map.get_subpart_state("plate_1", "A1") is None


def test_formazan_fail_when_not_registered():
	# "formazan" (the MTT assay product) is registry-required; unregistered fails.
	state_map, emitter = build_state_map()
	ok = apply(state_map, emitter, state_change_op("mini_plate.A1", {"material_name": "formazan"}))
	assert ok is False
	assert state_map.get_subpart_state("plate_1", "A1") is None


def test_waste_stream_fails_when_not_registered():
	# A disposal stream ("waste_mtt") is registry-required, not a sentinel;
	# unregistered fails and stores nothing.
	state_map, emitter = build_state_map()
	ok = apply(state_map, emitter, state_change_op("mini_plate.A1", {"material_name": "waste_mtt"}))
	assert ok is False
	assert state_map.get_subpart_state("plate_1", "A1") is None


def test_cells_pass_when_registered_with_scalar_color():
	# Once "cells" is registered with a scalar display_color, the write succeeds
	# and the value lands in the subpart record (validates via the registry).
	registered = {"cells": {"label": "Cells", "display_color": "#33aa55"}}
	state_map, emitter = build_state_map_with_materials(registered)
	ok = apply(state_map, emitter, state_change_op("mini_plate.A1", {"material_name": "cells"}))
	assert ok is True
	assert state_map.get_subpart_state("plate_1", "A1")["state"]["material_name"] == "cells"


def test_formazan_and_waste_pass_when_registered():
	# "formazan" and "waste_mtt", once registered with scalar colors, validate
	# through the registry like any other named substance.
	registered = {
		"formazan": {"label": "Formazan", "display_color": "#5522aa"},
		"waste_mtt": {"label": "MTT waste", "display_color": "#444444"},
	}
	state_map, emitter = build_state_map_with_materials(registered)
	ok_formazan = apply(state_map, emitter, state_change_op("mini_plate.A1", {"material_name": "formazan"}))
	ok_waste = apply(state_map, emitter, state_change_op("mini_plate.A2", {"material_name": "waste_mtt"}))
	assert ok_formazan is True
	assert ok_waste is True
	assert state_map.get_subpart_state("plate_1", "A1")["state"]["material_name"] == "formazan"
	assert state_map.get_subpart_state("plate_1", "A2")["state"]["material_name"] == "waste_mtt"


def test_derived_scene_replacement_survives_inherited_removal() -> None:
	"""Stepper scene inheritance keeps a same-name local replacement clickable."""
	db = ContentDatabase()
	db.objects["mini_plate"] = PLATE_OBJECT
	db.objects["replacement_plate"] = {**PLATE_OBJECT, "object_name": "replacement_plate"}
	db.base_scenes["bench"] = BASE_SCENE
	db.protocols["p1"] = PROTOCOL
	db.materials_by_protocol["p1"] = MATERIALS
	tree = LoadedContentTree(db, root_path=Path(__file__).resolve().parents[1])
	tree.protocol_local_scenes["p1"] = {
		"derived_bench": {
			"scene_name": "derived_bench",
			"extends": "bench",
			"remove_placements": ["plate_1"],
			"add_placements": [
				{"placement_name": "plate_1", "object_name": "replacement_plate"},
			],
		},
	}
	emitter = FindingEmitter()
	state_map = StateMap(tree, "p1", emitter)
	effective = state_map._get_effective_placements(tree.protocol_local_scenes["p1"]["derived_bench"])
	assert effective == [{"placement_name": "plate_1", "object_name": "replacement_plate"}]
