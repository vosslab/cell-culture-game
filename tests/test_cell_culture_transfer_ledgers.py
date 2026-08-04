"""Behavioral checks for physically plausible cell-culture transfers."""

from pathlib import Path

import yaml

from validation.stepper.findings import Level
from validation.stepper.loader import load_content_tree
from validation.stepper.runner import walk_protocol


REPO_ROOT = Path(__file__).resolve().parents[1]
CELL_CULTURE = REPO_ROOT / "content/protocols/cell_culture"


def _protocol(name: str) -> dict:
	return yaml.safe_load((CELL_CULTURE / name / "protocol.yaml").read_text(encoding="utf-8"))


def _operations(protocol: dict) -> list[tuple[str, dict]]:
	return [
		(interaction["target"], operation)
		for step in protocol["steps"]
		for interaction in step["sequence"]
		for operation in interaction["response"]["scene_operations"]
		if operation["type"] == "ObjectStateChange"
	]


def test_cell_transfers_show_fresh_then_used_pipette_states() -> None:
	"""Handling a biological sample requires a visible fresh-tip and used-tip lifecycle."""
	states = {
		operation["state"].get("tip_status")
		for protocol_name in ("trypan_blue_counting", "cell_seeding_plate_setup", "drug_dilution_setup")
		for _, operation in _operations(_protocol(protocol_name))
		if "tip_status" in operation["state"]
	}

	assert {"fresh", "used"} <= states


def test_trypan_counting_keeps_the_stained_sample_visible_through_loading() -> None:
	"""The hemocytometer contains a named mixed sample rather than an invisible count state."""
	mixed_sample_writes = [
		operation["state"]
		for target, operation in _operations(_protocol("trypan_blue_counting"))
		if target.startswith("hemocytometer_slide.")
		and operation["state"].get("material_name") == "trypan_blue_mixture"
	]

	assert mixed_sample_writes and any(state.get("material_volume", 0) > 0 for state in mixed_sample_writes)


def test_trypan_counting_makes_tip_hygiene_mixing_and_loading_quality_observable() -> None:
	"""The count preparation exposes the decisions that make its result trustworthy."""
	protocol = _protocol("trypan_blue_counting")
	steps = {step["step_name"]: step for step in protocol["steps"]}
	trypan_step = steps["add_trypan_blue_to_chamber"]
	cell_step = steps["add_cell_suspension_to_chamber"]
	mix_step = steps["mix_by_pipetting"]
	load_step = steps["load_semicircle_chamber"]

	def state_writes(step: dict, target: str) -> list[dict]:
		return [
			operation["state"]
			for interaction in step["sequence"]
			for operation in interaction["response"]["scene_operations"]
			if operation["type"] == "ObjectStateChange" and operation["target"] == target
		]

	# Each source-contact transfer visibly begins with a fresh tip and ends used.
	for step in (trypan_step, cell_step):
		tip_states = [state["tip_status"] for state in state_writes(step, "p20_micropipette") if "tip_status" in state]
		assert tip_states[0] == "fresh"
		assert tip_states[-1] == "used"

	mix_cycles = [state["mix_cycles"] for state in state_writes(mix_step, "hemocytometer_slide") if "mix_cycles" in state]
	assert mix_cycles == [1, 2, 3]
	assert any(state.get("mixture_homogeneous") is True for state in state_writes(mix_step, "hemocytometer_slide"))
	assert any(state.get("chamber_load_quality") == "bubble_free" for state in state_writes(load_step, "hemocytometer_slide"))
	assert "strictly greater than 90%" in steps["verify_viability_gate"]["prompt"]


def test_direct_cell_transfer_protocols_complete_without_stepper_errors() -> None:
	"""A student can finish each transfer workflow from its own visible starting state."""
	tree = load_content_tree(REPO_ROOT)
	errors = []
	for protocol_name in (
		"trypan_blue_counting",
		"cell_seeding_plate_setup",
		"passage_hood_detachment",
		"passage_pellet_reseed",
		"drug_dilution_setup",
	):
		_, _, emitter = walk_protocol(tree, protocol_name, quiet=True)
		errors.extend(finding for finding in emitter.findings if finding.level == Level.ERROR)

	assert not errors
