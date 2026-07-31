"""Focused schema tests for protocol-level durable initial state seeds."""

from pathlib import Path

import pipeline.gen_protocols as gen_protocols
from validation.yaml_schema.database import ContentDatabase
from validation.yaml_schema.protocol_validator import ProtocolValidator


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_validator() -> ProtocolValidator:
	"""Load the production object and material registries for target resolution."""
	db = ContentDatabase()
	db.load_from_tree(REPO_ROOT)
	return ProtocolValidator(db=db)


def initial_state_findings(entries: list[dict], protocol_name: str = "dilution_series") -> list:
	"""Validate one deliberately small initial-state surface against real objects."""
	validator = load_validator()
	protocol = {
		"protocol_name": protocol_name,
		"protocol_type": "mini_protocol",
		"initial_state": entries,
	}
	return validator._validate_initial_state(protocol, "inline/protocol.yaml")


def test_initial_state_expands_declared_group_without_overlap() -> None:
	"""A group seed expands to every concrete well and accepts subpart fields."""
	findings = initial_state_findings([
		{
			"target": "well_plate_96.all_wells",
			"state": {"material_name": "empty", "material_volume": 0},
		},
	])
	assert findings == []


def test_initial_state_rejects_overlapping_group_and_concrete_subpart() -> None:
	"""A group cannot silently overwrite a separately seeded member."""
	findings = initial_state_findings([
		{
			"target": "well_plate_96.all_wells",
			"state": {"material_name": "empty"},
		},
		{
			"target": "well_plate_96.A1",
			"state": {"material_name": "empty"},
		},
	])
	assert any(finding.tag == "initial_state_overlap" for finding in findings)


def test_initial_state_rejects_unknown_field_bad_type_and_unknown_material() -> None:
	"""Seeds have the same closed state-field and material semantics as writes."""
	findings = initial_state_findings([
		{
			"target": "well_plate_96.A1",
			"state": {
				"not_declared": 1,
				"material_volume": "five",
				"material_name": "not_in_materials",
			},
		},
	])
	tags = {finding.tag for finding in findings}
	assert "T1_STATE_FIELD" in tags
	assert "initial_state_type" in tags
	assert "T1_MATERIAL_REF" in tags


def test_initial_state_accepts_registry_backed_material_not_in_plate_enum() -> None:
	"""A protocol-local material is accepted without widening the shared plate enum."""
	findings = initial_state_findings([
		{
			"target": "well_plate_96.all_wells",
			"state": {"material_name": "formazan_crystals", "material_volume": 0},
		},
	], protocol_name="mtt_solubilization_readout")
	assert findings == []


def test_initial_state_rejects_registered_material_on_whole_object() -> None:
	"""Registry membership cannot override a whole object's closed material enum."""
	findings = initial_state_findings([
		{
			"target": "mtt_powder_container",
			"state": {"material_name": "formazan_crystals"},
		},
	], protocol_name="mtt_solubilization_readout")
	tags = {finding.tag for finding in findings}
	assert "T1_ENUM" in tags
	assert "T1_MATERIAL_REF" not in tags


def test_object_state_change_rejects_registered_material_on_whole_object() -> None:
	"""Normal writes use the same object-versus-subpart material boundary."""
	validator = load_validator()
	step = {
		"sequence": [{
			"target": "mtt_powder_container",
			"gesture": "click",
			"validator": {"preset": "correct_target"},
			"response": {"scene_operations": [{
				"type": "ObjectStateChange",
				"target": "mtt_powder_container",
				"state": {"material_name": "formazan_crystals"},
			}]},
		}],
	}
	findings = validator._validate_sequence(
		step,
		"content/protocols/cell_culture/mtt_solubilization_readout/protocol.yaml.steps[0]",
	)
	tags = {finding.tag for finding in findings}
	assert "T1_ENUM" in tags
	assert "T1_MATERIAL_REF" not in tags


def test_generator_rejects_duplicate_and_nested_runner_constituents() -> None:
	"""Code generation permits only a unique, direct list of mini-protocol leaves."""
	mini = {
		"protocol_type": "mini_protocol",
		"protocol_name": "mini_leaf",
		"entry_step": "only_step",
		"learning": {"objectives": "x", "outcomes": "x", "goals": "x"},
		"steps": [{
			"step_name": "only_step", "prompt": "x", "sequence": [],
			"step_validator": {"preset": "sequence_complete"},
			"outcome": {"on_success": "complete", "on_failure": "retry"},
			"next_step": None,
		}],
	}
	runner = {
		"protocol_type": "sequence_runner",
		"protocol_name": "runner",
		"entry_step": "only_step",
		"learning": {"objectives": "x", "outcomes": "x", "goals": "x"},
		"mini_protocols": ["mini_leaf", "mini_leaf"],
	}
	all_protocols = {"mini_leaf": (mini, "test"), "runner": (runner, "test")}
	try:
		gen_protocols.validate_protocol(runner, "test", "inline/protocol.yaml", all_protocols)
	except ValueError as error:
		assert "duplicate constituent" in str(error)
	else:
		raise AssertionError("duplicate runner constituent was accepted")

	runner["mini_protocols"] = ["runner"]
	try:
		gen_protocols.validate_protocol(runner, "test", "inline/protocol.yaml", all_protocols)
	except ValueError as error:
		assert "direct mini_protocol leaves" in str(error)
	else:
		raise AssertionError("nested runner constituent was accepted")

	runner["mini_protocols"] = []
	try:
		gen_protocols.validate_protocol(runner, "test", "inline/protocol.yaml", all_protocols)
	except ValueError as error:
		assert "non-empty" in str(error)
	else:
		raise AssertionError("empty runner constituent list was accepted")

	runner["mini_protocols"] = ["unknown_leaf"]
	try:
		gen_protocols.validate_protocol(runner, "test", "inline/protocol.yaml", all_protocols)
	except ValueError as error:
		assert "missing mini-protocol" in str(error)
	else:
		raise AssertionError("unknown runner constituent was accepted")


def test_schema_validator_rejects_duplicate_runner_constituents() -> None:
	"""The content-lint path enforces the same unique-leaf runner rule."""
	db = ContentDatabase()
	db.protocols = {
		"leaf": {"protocol_type": "mini_protocol", "entry_step": "leaf_step"},
	}
	validator = ProtocolValidator(db=db)
	runner = {
		"protocol_type": "sequence_runner",
		"protocol_name": "runner",
		"entry_step": "leaf_step",
		"learning": {
			"objectives": "Students completing this protocol will have achieved x",
			"outcomes": "Students completing this protocol will be able to x",
			"goals": "Overall, this protocol aims to accomplish x",
		},
		"mini_protocols": ["leaf", "leaf"],
	}
	findings = validator.validate(runner, "inline/protocol.yaml")
	assert any(finding.tag == "duplicate_mini_protocol" for finding in findings)


def test_target_with_value_rejects_out_of_range_instrument_setpoint() -> None:
	"""Authored setpoints cannot exceed the selected instrument's real range."""
	validator = load_validator()
	step = {
		"sequence": [{
			"target": "p200_micropipette",
			"gesture": "adjust",
			"validator": {
				"preset": "target_with_value",
				"value": {"set_volume": 7.5},
			},
			"response": {"scene_operations": []},
		}],
	}
	findings = validator._validate_sequence(step, "inline/protocol.yaml.steps[0]")
	assert any(finding.tag == "state_value_out_of_range" for finding in findings)


def test_target_with_value_accepts_in_range_instrument_setpoint() -> None:
	"""The same low-volume setpoint is valid when the protocol selects a P10."""
	validator = load_validator()
	step = {
		"sequence": [{
			"target": "p10_micropipette",
			"gesture": "adjust",
			"validator": {
				"preset": "target_with_value",
				"value": {"set_volume": 7.5},
			},
			"response": {"scene_operations": []},
		}],
	}
	findings = validator._validate_sequence(step, "inline/protocol.yaml.steps[0]")
	assert not any(
		finding.tag in {"T1_TARGET_WITH_VALUE", "state_value_out_of_range"}
		for finding in findings
	)
