"""Behavioral checks for the visible plate-treatment workflow."""

from pathlib import Path

import yaml

from validation.stepper.findings import Level
from validation.stepper.loader import load_content_tree
from validation.stepper.runner import walk_protocol


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = REPO_ROOT / "content/protocols/cell_culture/plate_drug_treatment_drug_addition/protocol.yaml"


def _protocol() -> dict:
	return yaml.safe_load(PROTOCOL_PATH.read_text(encoding="utf-8"))


def _well_writes(protocol: dict) -> list[tuple[str, dict]]:
	return [
		(interaction["target"], operation["state"])
		for step in protocol["steps"]
		for interaction in step["sequence"]
		for operation in interaction["response"]["scene_operations"]
		if operation["type"] == "ObjectStateChange"
		and operation["target"].startswith("well_plate_96.")
	]


def test_drug_conditions_are_written_by_the_visible_plate_action() -> None:
	"""A batch dispense changes visible wells without hiding the biological condition."""
	writes = _well_writes(_protocol())
	condition_names = {
		state["material_name"]
		for _, state in writes
		if state.get("material_name", "").startswith("cells_in_growth_media_carboplatin_")
	}

	assert writes and all(target == "well_plate_96" for target, _ in writes)
	assert any(name.endswith("_metformin_5mmol") for name in condition_names) and any(
		not name.endswith("_metformin_5mmol") for name in condition_names
	)


def test_drug_addition_completes_with_valid_tip_and_material_state() -> None:
	"""The authored visible workflow is strictly executable, including dispenser-tip lifecycle."""
	protocol = _protocol()
	tip_states = {
		operation["state"].get("tip_status")
		for step in protocol["steps"]
		for interaction in step["sequence"]
		for operation in interaction["response"]["scene_operations"]
		if operation["type"] == "ObjectStateChange" and operation["target"] == "repeat_dispenser"
	}
	_, _, emitter = walk_protocol(load_content_tree(REPO_ROOT), "plate_drug_treatment_drug_addition", quiet=True)

	assert {"fresh", "used"} <= tip_states
	assert not [finding for finding in emitter.findings if finding.level == Level.ERROR]
