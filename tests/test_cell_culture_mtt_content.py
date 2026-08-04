"""Behavioral contracts for the MTT assay's visible experimental states."""

from pathlib import Path

import yaml

from validation.stepper.findings import Level
from validation.stepper.loader import load_content_tree
from validation.stepper.runner import walk_protocol, walk_sequence_runner


REPO_ROOT = Path(__file__).resolve().parents[1]
CELL_CULTURE = REPO_ROOT / "content/protocols/cell_culture"


def _protocol(name: str) -> dict:
	return yaml.safe_load((CELL_CULTURE / name / "protocol.yaml").read_text(encoding="utf-8"))


def _states(protocol: dict) -> list[tuple[str, dict]]:
	return [
		(operation["target"], operation["state"])
		for step in protocol["steps"]
		for interaction in step["sequence"]
		for operation in interaction["response"]["scene_operations"]
		if operation["type"] == "ObjectStateChange"
	]


def test_mtt_conversion_and_solubilization_preserve_treatment_identity() -> None:
	"""The condition label survives crystals, decanting, and DMSO dissolution."""
	reaction = _protocol("mtt_plate_reaction")
	readout = _protocol("mtt_solubilization_readout")
	reaction_names = {
		state["material_name"]
		for target, state in _states(reaction)
		if target.startswith("well_plate_96.") and state.get("material_name", "").startswith("formazan_")
	}
	decanted_names = {
		state["material_name"]
		for target, state in _states(reaction)
		if target.startswith("well_plate_96.")
		and state.get("material_name", "").startswith("formazan_")
		and state.get("material_volume") == 0
	}
	direct_entry_names = {
		entry["state"]["material_name"]
		for entry in readout["initial_state"]
		if entry["target"].startswith("well_plate_96.") and "material_name" in entry["state"]
	}
	dissolved_names = {
		state["material_name"]
		for target, state in _states(readout)
		if target.startswith("well_plate_96.") and state.get("material_name", "").startswith("formazan_dmso_")
	}
	converted_conditions = {name.removeprefix("formazan_") for name in reaction_names}
	dissolved_conditions = {name.removeprefix("formazan_dmso_") for name in dissolved_names}

	assert any("carboplatin" in name for name in converted_conditions) and any(
		"metformin" in name for name in converted_conditions
	)
	assert direct_entry_names == decanted_names
	assert converted_conditions <= dissolved_conditions


def test_mtt_assay_states_and_readout_are_visible_and_executable() -> None:
	"""The assay shows retained crystals, a dissolved plate, and a plate-reader outcome."""
	readout_states = _states(_protocol("mtt_solubilization_readout"))
	statuses = {
		state["assay_status"]
		for target, state in _states(_protocol("mtt_plate_reaction")) + readout_states
		if target == "well_plate_96" and "assay_status" in state
	}
	reader_states = [state for target, state in readout_states if target == "plate_reader"]
	tree = load_content_tree(REPO_ROOT)
	_, _, direct = walk_protocol(tree, "mtt_solubilization_readout", quiet=True)
	_, _, runner = walk_sequence_runner(tree, "cell_culture_full", quiet=True)

	assert {"crystals_retained", "dissolved"} <= statuses and reader_states
	assert not [finding for finding in direct.findings if finding.level == Level.ERROR]
	assert not [
		finding
		for finding in runner.findings
		if finding.level == Level.ERROR and finding.protocol_name.startswith("mtt_")
	]
