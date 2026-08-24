"""Focused closure, repeat, and answer-safety tests for interaction guidance."""

from functools import lru_cache
from pathlib import Path

import pytest

import pipeline.gen_protocols as gen_protocols
from validation.yaml_schema.database import ContentDatabase
from validation.yaml_schema.protocol_validator import ProtocolValidator


REPO_ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def load_content_database() -> ContentDatabase:
	"""Load real object and placement data once for registry-bound checks."""
	db = ContentDatabase()
	db.load_from_tree(REPO_ROOT)
	return db


def interaction(
	target: str = "p10_micropipette",
	gesture: str = "click",
	**extra: object,
) -> dict:
	"""Build the smallest structurally valid interaction for one focused check."""
	result = {
		"target": target,
		"gesture": gesture,
		"instruction": "Click the highlighted control.",
		"hint": "Use the visible highlighted control to continue.",
		"validator": {"preset": "correct_target"},
		"response": {"scene_operations": []},
	}
	result.update(extra)
	return result


def validate_sequence(sequence: list[dict], *, use_registry: bool = False) -> list:
	"""Run one validator sequence, loading registry data only when required."""
	db = load_content_database() if use_registry else None
	return ProtocolValidator(db=db)._validate_sequence(
		{"sequence": sequence}, "inline/protocol.yaml.steps[0]"
	)


def step(sequence: list[dict]) -> dict:
	"""Build a minimal codegen-valid step around an interaction sequence."""
	return {
		"step_name": "guided_step",
		"prompt": "Complete the guided action.",
		"sequence": sequence,
		"step_validator": {"preset": "sequence_complete"},
		"outcome": {"on_success": "complete", "on_failure": "retry"},
		"next_step": None,
	}


def test_generator_and_validator_share_closed_interaction_keys() -> None:
	"""An escape-hatch key fails both production schema entry points."""
	bad = interaction(extra_instruction="not a declared field")
	with pytest.raises(ValueError, match="unknown keys"):
		gen_protocols.validate_interaction(bad, "inline")
	findings = validate_sequence([bad])
	assert any(finding.tag == "CLOSURE" for finding in findings)


@pytest.mark.parametrize("missing_key", ["instruction", "hint"])
def test_generator_rejects_missing_required_guidance(missing_key: str) -> None:
	"""The build gate rejects every interaction without both authored guidance fields."""
	bad = interaction()
	del bad[missing_key]
	with pytest.raises(ValueError, match="missing slots"):
		gen_protocols.validate_interaction(bad, "inline")


@pytest.mark.parametrize("guidance", [
	{"instruction": "  ", "hint": "Use the outlined control."},
	{"instruction": "Click the control.", "hint": "  "},
])
def test_guidance_is_a_required_nonempty_plain_string_contract(guidance: dict) -> None:
	"""Blank authored guidance fails rather than falling back to generic copy."""
	findings = validate_sequence([interaction(**guidance)])
	assert any(finding.tag == "guidance_string" for finding in findings)


@pytest.mark.parametrize("missing_key", ["instruction", "hint"])
def test_validator_rejects_missing_required_guidance(missing_key: str) -> None:
	"""The content validator reports every missing required guidance field."""
	bad = interaction()
	del bad[missing_key]
	findings = validate_sequence([bad])
	assert any(finding.tag == "guidance_pair" for finding in findings)


def test_repeated_signature_requires_distinct_guidance_for_both_live_surfaces() -> None:
	"""Repeated actions update both the primary message and an already-open hint."""
	duplicate = [
		interaction("heat_block", "click", instruction="Open the lid.", hint="Use the lid."),
		interaction("heat_block", "click", instruction=" open the lid. ", hint="Use the lid."),
	]
	duplicate_findings = validate_sequence(duplicate)
	assert sum(finding.tag == "repeated_interaction_guidance" for finding in duplicate_findings) == 2

	distinct = [
		interaction("heat_block", "click", instruction="Open the lid.", hint="Lift the front edge."),
		interaction("heat_block", "click", instruction="Close the lid.", hint="Lower the lid to start incubation."),
	]
	assert not any(finding.tag == "repeated_interaction_guidance" for finding in validate_sequence(distinct))

	with pytest.raises(ValueError, match="distinct instruction"):
		gen_protocols.validate_repeated_interaction_guidance(
			duplicate, "inline", "guided_step"
		)


def test_select_guidance_cannot_reveal_placement_or_learner_label() -> None:
	"""The real content registry supplies both placement and label leak evidence."""
	placement_leak = interaction(
		"rear_right_heat_block",
		"select",
		instruction="Choose the rear right heat block.",
		hint="Use the blue outlined item.",
		validator={"preset": "correct_choice"},
	)
	label_leak = interaction(
		"p10_micropipette",
		"select",
		instruction="Choose the P10 micropipette.",
		hint="Use the blue outlined item.",
		validator={"preset": "correct_choice"},
	)
	for findings in (
		validate_sequence([placement_leak], use_registry=True),
		validate_sequence([label_leak], use_registry=True),
	):
		assert any(finding.tag == "guidance_select_answer_leak" for finding in findings)


def test_type_guidance_cannot_reveal_target_with_value_literal() -> None:
	"""Typed values stay unavailable until the learner enters them."""
	entry = interaction(
		"p10_micropipette",
		"type",
		instruction="Enter 7.5 in the visible field.",
		hint="Use the requested set point.",
		validator={"preset": "target_with_value", "value": {"set_volume": 7.5}},
	)
	findings = validate_sequence([entry])
	assert any(finding.tag == "guidance_type_answer_leak" for finding in findings)


def test_codegen_uses_registry_backed_guidance_safety() -> None:
	"""The build gate rejects the same pre-answer leak as the content validator."""
	db = load_content_database()
	leaking_select = interaction(
		"rear_right_heat_block",
		"select",
		instruction="Choose the rear right heat block.",
		hint="Use the blue outlined item.",
		validator={"preset": "correct_choice"},
	)
	with pytest.raises(ValueError, match="guidance violation"):
		gen_protocols.validate_step(step([leaking_select]), "inline", set(), db)
