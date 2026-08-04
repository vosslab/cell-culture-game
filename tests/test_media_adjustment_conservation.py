"""Behavioral checks for visible Day-2 plate-media adjustment."""

from pathlib import Path

import yaml

from validation.stepper.findings import Level
from validation.stepper.loader import load_content_tree
from validation.stepper.runner import walk_protocol, walk_sequence_runner


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = (
	REPO_ROOT / "content/protocols/cell_culture/plate_drug_treatment_media_adjustment/protocol.yaml"
)


def _protocol() -> dict:
	return yaml.safe_load(PROTOCOL_PATH.read_text(encoding="utf-8"))


def test_media_adjustment_keeps_plate_state_in_visible_actions() -> None:
	"""Every concrete-well write follows a plate interaction and remains a legal volume."""
	writes = [
		(interaction["target"], operation["state"])
		for step in _protocol()["steps"]
		for interaction in step["sequence"]
		for operation in interaction["response"]["scene_operations"]
		if operation["type"] == "ObjectStateChange"
		and operation["target"].startswith("well_plate_96.")
	]

	assert writes and all(target.startswith("well_plate_96") for target, _ in writes)
	assert all(state.get("material_volume", 0) <= 300 for _, state in writes)


def test_media_adjustment_is_executable_directly_and_in_its_runner_context() -> None:
	"""The protocol neither loses conservation nor needs a hidden reset in the full sequence."""
	tree = load_content_tree(REPO_ROOT)
	_, _, direct = walk_protocol(tree, "plate_drug_treatment_media_adjustment", quiet=True)
	_, _, runner = walk_sequence_runner(tree, "cell_culture_full", quiet=True)
	runner_errors = [
		finding
		for finding in runner.findings
		if finding.level == Level.ERROR and finding.protocol_name == "plate_drug_treatment_media_adjustment"
	]

	assert not [finding for finding in direct.findings if finding.level == Level.ERROR]
	assert not runner_errors
