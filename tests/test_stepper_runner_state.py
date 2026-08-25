"""Behavioral coverage for shared runner state and material transfer accounting."""

import copy

import file_utils
from validation.stepper.findings import FindingEmitter, Level
from validation.stepper.loader import LoadedContentTree
from validation.stepper.runner import walk_protocol, walk_sequence_runner
import validation.stepper.material_ledger
import validation.stepper.scene_ops
from validation.stepper.state import StateMap
from validation.yaml_schema.database import ContentDatabase

file_utils.get_repo_root()


#============================================
# In-memory content tree
#============================================

VESSEL = {
	"object_name": "source_tube",
	"kind": "tube",
	"capabilities": ["material_container"],
	"state_fields": [
		{"field_name": "material_name", "type": "enum", "default": "empty"},
		{"field_name": "material_volume", "type": "float", "unit": "ul", "min": 0, "default": 0},
	],
}

PIPETTE = {
	"object_name": "test_pipette",
	"kind": "pipette",
	"capabilities": ["material_container", "cursor_attachable"],
	"state_fields": [
		{"field_name": "held_material_name", "type": "enum", "default": "empty"},
		{"field_name": "held_material_volume", "type": "float", "unit": "ul", "min": 0, "default": 0},
	],
}

DESTINATION = {
	"object_name": "destination_tube",
	"kind": "tube",
	"capabilities": ["material_container"],
	"state_fields": VESSEL["state_fields"],
}

DESTINATION_TWO = {
	"object_name": "destination_tube_two",
	"kind": "tube",
	"capabilities": ["material_container"],
	"state_fields": VESSEL["state_fields"],
}


def operation(target: str, state: dict) -> dict:
	"""Build a single object-state response operation."""
	return {"type": "ObjectStateChange", "target": target, "state": state}


def mini(name: str, operations: list[dict], initial_state: list[dict] | None = None) -> dict:
	"""Build a minimal one-step mini protocol for runner behavior tests."""
	protocol = {
		"protocol_name": name,
		"protocol_type": "mini_protocol",
		"entry_step": "transfer",
		"steps": [{
			"step_name": "transfer",
			"sequence": [{"response": {"scene_operations": operations}}],
			"next_step": None,
		}],
	}
	if initial_state is not None:
		protocol["initial_state"] = initial_state
	return protocol


def build_tree(protocols: dict) -> LoadedContentTree:
	"""Construct a deterministic content tree with one shared bench scene."""
	database = ContentDatabase()
	database.objects = {
		"source_tube": copy.deepcopy(VESSEL),
		"destination_tube": copy.deepcopy(DESTINATION),
		"destination_tube_two": copy.deepcopy(DESTINATION_TWO),
		"test_pipette": copy.deepcopy(PIPETTE),
	}
	database.base_scenes["bench"] = {
		"scene_name": "bench",
		"placements": [
			{"placement_name": "source", "object_name": "source_tube"},
			{"placement_name": "destination", "object_name": "destination_tube"},
			{"placement_name": "destination_two", "object_name": "destination_tube_two"},
			{"placement_name": "pipette", "object_name": "test_pipette"},
		],
	}
	database.protocols = protocols
	for protocol_name in protocols:
		database.materials_by_protocol[protocol_name] = {
			"buffer": {"label": "Buffer", "display_color": "#123456"},
		}
	return LoadedContentTree(database, root_path=None)


def errors(emitter: FindingEmitter) -> list[str]:
	"""Return error codes from one semantic run."""
	return [finding.code for finding in emitter.findings if finding.level == Level.ERROR]


#============================================
# Shared sequence-runner session
#============================================

def test_runner_carries_pipette_material_between_minis() -> None:
	first = mini("aspirate", [
		operation("source", {"material_name": "buffer", "material_volume": 5}),
		operation("test_pipette", {"held_material_name": "buffer", "held_material_volume": 5}),
	], initial_state=[{"target": "source", "state": {"material_name": "buffer", "material_volume": 0}}])
	second = mini("dispense", [
		operation("destination", {"material_name": "buffer", "material_volume": 5}),
		operation("test_pipette", {"held_material_name": "empty", "held_material_volume": 0}),
	])
	runner = {
		"protocol_name": "session", "protocol_type": "sequence_runner",
		"mini_protocols": ["aspirate", "dispense"],
		"initial_state": [{"target": "source", "state": {"material_name": "buffer", "material_volume": 10}}],
	}
	leaves, interactions, emitter = walk_sequence_runner(build_tree({"session": runner, "aspirate": first, "dispense": second}), "session", quiet=True)
	assert (leaves, interactions) == (2, 2)
	assert errors(emitter) == []
	assert emitter.final_state["source"]["state"]["material_volume"] == 5
	assert emitter.final_state["destination"]["state"]["material_volume"] == 5
	assert emitter.final_state["pipette"]["state"] == {"held_material_name": "empty", "held_material_volume": 0}


def test_runner_rejects_duplicate_and_nested_constituents() -> None:
	nested = {"protocol_name": "nested", "protocol_type": "sequence_runner", "mini_protocols": ["leaf"]}
	leaf = mini("leaf", [])
	runner = {"protocol_name": "session", "protocol_type": "sequence_runner", "mini_protocols": ["nested", "nested"]}
	_, _, emitter = walk_sequence_runner(build_tree({"session": runner, "nested": nested, "leaf": leaf}), "session", quiet=True)
	assert "duplicate_runner_constituent" in errors(emitter)


#============================================
# Ledger behavior
#============================================

def build_state_map() -> tuple[StateMap, FindingEmitter]:
	"""Build a state map positioned in the in-memory bench scene."""
	tree = build_tree({"p": mini("p", [])})
	emitter = FindingEmitter()
	state_map = StateMap(tree, "p", emitter)
	state_map.set_active_scene("bench", "content/base_scenes/bench.yaml")
	return state_map, emitter


def test_state_map_rejects_material_underflow() -> None:
	state_map, emitter = build_state_map()
	underflow = operation("source", {"material_name": "buffer", "material_volume": -1})
	ok = validation.stepper.scene_ops.apply_scene_operation(underflow, state_map, "p", "transfer", 0, emitter, state_map.tree)
	assert ok is False
	assert "state_value_below_minimum" in errors(emitter)


def test_ledger_rejects_mass_unit_for_pipette_transfer() -> None:
	state_map, emitter = build_state_map()
	state_map.tree.objects["test_pipette"]["state_fields"][1]["unit"] = "mg"
	before = state_map.snapshot_state()
	validation.stepper.scene_ops.apply_scene_operation(
		operation("pipette", {"held_material_name": "buffer", "held_material_volume": 1}),
		state_map, "p", "transfer", 0, emitter, state_map.tree,
	)
	validation.stepper.material_ledger.validate_material_ledger(before, state_map.snapshot_state(), state_map, "p", "transfer", 0, emitter)
	assert "material_unit_mismatch" in errors(emitter)


def test_ledger_requires_pipette_clear_after_dispense() -> None:
	state_map, emitter = build_state_map()
	state_map.apply_initial_state([
		{"target": "pipette", "state": {"held_material_name": "buffer", "held_material_volume": 5}},
		{"target": "source", "state": {"material_name": "buffer", "material_volume": 0}},
	])
	before = state_map.snapshot_state()
	validation.stepper.scene_ops.apply_scene_operation(operation("source", {"material_name": "buffer", "material_volume": 5}), state_map, "p", "transfer", 0, emitter, state_map.tree)
	validation.stepper.scene_ops.apply_scene_operation(operation("pipette", {"held_material_name": "buffer", "held_material_volume": 0}), state_map, "p", "transfer", 0, emitter, state_map.tree)
	validation.stepper.material_ledger.validate_material_ledger(before, state_map.snapshot_state(), state_map, "p", "transfer", 0, emitter)
	assert "pipette_not_cleared" in errors(emitter)


def test_ledger_rejects_wrong_material_in_empty_destination() -> None:
	state_map, emitter = build_state_map()
	state_map.tree.database.materials_by_protocol["p"]["other"] = {
		"label": "Other", "display_color": "#654321",
	}
	state_map.apply_initial_state([
		{"target": "pipette", "state": {"held_material_name": "buffer", "held_material_volume": 5}},
		{"target": "destination", "state": {"material_name": "empty", "material_volume": 0}},
	])
	before = state_map.snapshot_state()
	validation.stepper.scene_ops.apply_scene_operation(operation("destination", {"material_name": "other", "material_volume": 5}), state_map, "p", "transfer", 0, emitter, state_map.tree)
	validation.stepper.scene_ops.apply_scene_operation(operation("pipette", {"held_material_name": "empty", "held_material_volume": 0}), state_map, "p", "transfer", 0, emitter, state_map.tree)
	validation.stepper.material_ledger.validate_material_ledger(before, state_map.snapshot_state(), state_map, "p", "transfer", 0, emitter)
	assert "material_identity_mismatch" in errors(emitter)


def test_group_fanout_charges_total_source_volume() -> None:
	# A fanout is represented by two destination deltas in one interaction; the
	# ledger accepts it only when their total equals the emptied pipette.
	state_map, emitter = build_state_map()
	state_map.apply_initial_state([
		{"target": "pipette", "state": {"held_material_name": "buffer", "held_material_volume": 10}},
		{"target": "source", "state": {"material_name": "buffer", "material_volume": 0}},
	])
	before = state_map.snapshot_state()
	validation.stepper.scene_ops.apply_scene_operation(operation("destination", {"material_name": "buffer", "material_volume": 5}), state_map, "p", "transfer", 0, emitter, state_map.tree)
	validation.stepper.scene_ops.apply_scene_operation(operation("destination_two", {"material_name": "buffer", "material_volume": 5}), state_map, "p", "transfer", 0, emitter, state_map.tree)
	validation.stepper.scene_ops.apply_scene_operation(operation("pipette", {"held_material_name": "empty", "held_material_volume": 0}), state_map, "p", "transfer", 0, emitter, state_map.tree)
	validation.stepper.material_ledger.validate_material_ledger(before, state_map.snapshot_state(), state_map, "p", "transfer", 0, emitter)
	assert "material_amount_drift" not in errors(emitter)


def test_declared_group_multiplies_per_channel_dispense_amount() -> None:
	state_map, emitter = build_state_map()
	state_map.tree.objects["destination_tube"]["structure"] = {
		"subpart_groups": {"all": {"members": [{"name": "all", "contains": ["A1", "A2", "A3"]}]}},
	}
	before = state_map.snapshot_state()
	before["pipette"]["state"] = {"held_material_name": "buffer", "held_material_volume": 3}
	after = state_map.snapshot_state()
	after["pipette"]["state"] = {"held_material_name": "empty", "held_material_volume": 0}
	after["destination"]["state"] = {"material_name": "buffer", "material_volume": 9}
	validation.stepper.material_ledger.validate_material_ledger(
		before, after, state_map, "p", "transfer", 0, emitter,
		[operation("destination_tube.all", {"material_name": "buffer", "material_volume": 9})],
	)
	assert "material_amount_drift" not in errors(emitter)


def test_ledger_counts_new_subpart_destination_from_declared_zero() -> None:
	state_map, emitter = build_state_map()
	destination = state_map.tree.objects["destination_tube"]
	destination["structure"] = {"subparts": [{"name": "A1"}]}
	destination["state_fields"] = [
		{"field_name": "material_name", "type": "enum", "default": "empty", "applies_to": "subpart"},
		{"field_name": "material_volume", "type": "float", "unit": "ul", "min": 0, "default": 0, "applies_to": "subpart"},
	]
	before = state_map.snapshot_state()
	before["pipette"]["state"] = {"held_material_name": "buffer", "held_material_volume": 5}
	after = copy.deepcopy(before)
	after["pipette"]["state"] = {"held_material_name": "empty", "held_material_volume": 0}
	after["destination.A1"] = {
		"object_name": "destination_tube", "state": {"material_name": "buffer", "material_volume": 5},
	}
	validation.stepper.material_ledger.validate_material_ledger(before, after, state_map, "p", "transfer", 0, emitter)
	assert "material_amount_drift" not in errors(emitter)


def test_state_jump_uses_canonical_key_for_explicit_object_state_change() -> None:
	state_map, emitter = build_state_map()
	before = state_map.snapshot_state()
	before["source"]["state"]["material_volume"] = 1
	after = copy.deepcopy(before)
	after["source"]["state"]["material_volume"] = 5
	validation.stepper.scene_ops.detect_state_jumps(
		before, after, [operation("source_tube", {"material_volume": 5})], state_map,
		"p", "transfer", 0, emitter,
	)
	assert "s-state-jump" not in errors(emitter)


def test_state_jump_still_reports_implicit_state_change() -> None:
	state_map, emitter = build_state_map()
	before = state_map.snapshot_state()
	before["source"]["state"]["material_volume"] = 1
	after = copy.deepcopy(before)
	after["source"]["state"]["material_volume"] = 5
	validation.stepper.scene_ops.detect_state_jumps(before, after, [], state_map, "p", "transfer", 0, emitter)
	assert any(finding.code == "s-state-jump" for finding in emitter.findings)


def created_volume_errors(material_name: str, volume: int) -> list[str]:
	"""Run the generic direct-volume rule for one invented container fill."""
	state_map, emitter = build_state_map()
	before = state_map.snapshot_state()
	after = copy.deepcopy(before)
	after["destination"]["state"] = {"material_name": material_name, "material_volume": volume}
	validation.stepper.material_ledger.detect_material_volume_creation(
		before, after, [operation("destination_tube", {"material_name": material_name, "material_volume": volume})],
		state_map, "p", "transfer", 0, emitter,
	)
	return errors(emitter)


def test_generic_conservation_rejects_missing_pbs_source() -> None:
	assert "unbalanced_material_volume_creation" in created_volume_errors("pbs", 5)


def test_generic_conservation_rejects_sds_laemmli_bme_creation() -> None:
	assert "unbalanced_material_volume_creation" in created_volume_errors("laemmli_bme", 30)


def test_generic_conservation_rejects_invented_trypan_volume() -> None:
	assert "unbalanced_material_volume_creation" in created_volume_errors("trypan_blue", 10)


def test_cross_scene_placements_share_object_state_without_ambiguity() -> None:
	tree = build_tree({"p": mini("p", [])})
	tree.base_scenes["bench_b"] = {
		"scene_name": "bench_b",
		"placements": [{"placement_name": "other_source", "object_name": "source_tube"}],
	}
	emitter = FindingEmitter()
	state_map = StateMap(tree, "p", emitter)
	state_map.set_active_scene("bench", "content/base_scenes/bench.yaml")
	validation.stepper.scene_ops.apply_scene_operation(operation("source", {"material_name": "buffer", "material_volume": 7}), state_map, "p", "transfer", 0, emitter, tree)
	state_map.set_active_scene("bench_b", "content/base_scenes/bench_b.yaml")
	state_key, _ = state_map.resolve_target("source_tube", "transfer", 0)
	assert state_map.get_placement_state(state_key)["state"]["material_volume"] == 7


def test_same_scene_duplicate_object_remains_ambiguous() -> None:
	tree = build_tree({"p": mini("p", [])})
	tree.base_scenes["bench"]["placements"].append({"placement_name": "source_two", "object_name": "source_tube"})
	emitter = FindingEmitter()
	state_map = StateMap(tree, "p", emitter)
	state_map.set_active_scene("bench", "content/base_scenes/bench.yaml")
	placement_name, _ = state_map.resolve_target("source_tube", "transfer", 0)
	assert placement_name is not None
	assert "ambiguous_target_in_scene" in errors(emitter)


def test_timed_wait_does_not_skip_following_transformation() -> None:
	mini_protocol = mini("wait_then_change", [
		{"type": "TimedWait", "target": "source", "duration_min": 1, "display": "Wait"},
		operation("source", {"material_name": "buffer", "material_volume": 3}),
	])
	tree = build_tree({"wait_then_change": mini_protocol})
	steps, interactions, emitter = walk_protocol(tree, "wait_then_change", quiet=True)
	assert (steps, interactions) == (1, 1)
	assert errors(emitter) == []
