"""Regression coverage for authored production cell-culture assay content."""

from pathlib import Path

import yaml

from validation.stepper.loader import load_content_tree
from validation.stepper.runner import walk_protocol, walk_sequence_runner


REPO_ROOT = Path(__file__).resolve().parents[1]
CELL_CULTURE = REPO_ROOT / "content" / "protocols" / "cell_culture"


def load_protocol(name: str) -> dict:
	"""Load the real curriculum protocol named by its production directory."""
	with (CELL_CULTURE / name / "protocol.yaml").open(encoding="utf-8") as handle:
		return yaml.safe_load(handle)


def interaction_with_target(protocol: dict, target: str) -> dict:
	"""Return the unique authored interaction that targets ``target``."""
	matches = [
		interaction
		for step in protocol["steps"]
		for interaction in step["sequence"]
		if interaction["target"] == target
	]
	assert len(matches) == 1, f"expected one interaction for {target}, found {len(matches)}"
	return matches[0]


def state_change(interaction: dict, target: str) -> dict:
	"""Return the unique state write to ``target`` from an interaction."""
	matches = [
		op
		for op in interaction["response"]["scene_operations"]
		if op["type"] == "ObjectStateChange" and op["target"] == target
	]
	assert len(matches) == 1, f"expected one state write to {target}, found {len(matches)}"
	return matches[0]["state"]


def test_drug_addition_uses_the_visible_well_it_writes() -> None:
	protocol = load_protocol("plate_drug_treatment_drug_addition")
	well_writes = []
	for step in protocol["steps"]:
		for interaction in step["sequence"]:
			for op in interaction["response"]["scene_operations"]:
				if op["type"] == "ObjectStateChange" and op["target"].startswith("well_plate_96."):
					well_writes.append((interaction["target"], op["target"]))

	assert len(well_writes) == 132
	assert all(click_target == response_target for click_target, response_target in well_writes)


def test_mtt_reagent_prep_authors_the_complete_4_ml_reagent() -> None:
	protocol = load_protocol("mtt_reagent_prep")
	assert protocol["initial_state"] == [
		{
			"target": "mtt_powder_container",
			"state": {"material_name": "mtt_powder", "material_volume": 20},
		},
		{
			"target": "pbs_bottle",
			"state": {"material_name": "pbs", "material_volume": 496},
		},
	]

	prepare = next(step for step in protocol["steps"] if step["step_name"] == "prepare_solution_tube")
	assert [interaction["target"] for interaction in prepare["sequence"][:2]] == [
		"serological_pipette",
		"serological_pipette",
	]
	assert prepare["sequence"][1]["validator"]["value"] == {"set_volume": 4.0}
	pbs_aspirate = interaction_with_target(protocol, "pbs_bottle")
	assert state_change(pbs_aspirate, "pbs_bottle") == {
		"material_name": "pbs",
		"material_volume": 492,
	}
	assert state_change(pbs_aspirate, "serological_pipette") == {
		"held_material_name": "pbs",
		"held_material_volume": 4.0,
	}
	assert state_change(prepare["sequence"][-1], "mtt_solution_tube") == {
		"material_name": "pbs",
		"material_volume": 4.0,
	}
	assert state_change(prepare["sequence"][-1], "serological_pipette") == {
		"held_material_name": "empty",
		"held_material_volume": 0,
	}

	dissolve = next(step for step in protocol["steps"] if step["step_name"] == "dissolve_and_mix")
	final_write = state_change(dissolve["sequence"][-1], "mtt_solution_tube")
	assert final_write == {"material_name": "mtt_solution_12mm", "material_volume": 4.0}


def test_mtt_reaction_preserves_standalone_prerequisites_and_mass_balance() -> None:
	protocol = load_protocol("mtt_plate_reaction")
	assert protocol["initial_state"] == [
		{
			"target": "mtt_solution_tube",
			"state": {"material_name": "mtt_solution_12mm", "material_volume": 4.0},
		},
		{
			"target": "well_plate_96.all_wells",
			"state": {"material_name": "treated_cell_culture", "material_volume": 200},
		},
	]

	assert "mtt_stock_tube" not in str(protocol)
	add_mtt = next(step for step in protocol["steps"] if step["step_name"] == "add_mtt_to_wells")
	source_interaction = next(
		interaction for interaction in add_mtt["sequence"] if interaction["target"] == "mtt_solution_tube"
	)
	assert state_change(source_interaction, "mtt_solution_tube") == {
		"material_name": "mtt_solution_12mm",
		"material_volume": 1.6,
	}
	assert state_change(source_interaction, "multichannel_pipette") == {
		"held_material_name": "mtt_solution_12mm",
		"held_material_volume": 25,
	}
	assert state_change(add_mtt["sequence"][-1], "well_plate_96.all_wells") == {
		"material_name": "mtt_reaction_mixture",
		"material_volume": 225,
	}

	incubate = next(step for step in protocol["steps"] if step["step_name"] == "incubate_formazan_conversion")
	wait = incubate["sequence"][-1]["response"]["scene_operations"][0]
	assert wait == {
		"type": "TimedWait",
		"target": "incubator",
		"duration_min": 90,
		"display": "formazan conversion (1.5 hours)",
	}
	assert state_change(incubate["sequence"][-1], "well_plate_96.all_wells") == {
		"material_name": "formazan_crystals",
		"material_volume": 225,
	}

	decant = next(step for step in protocol["steps"] if step["step_name"] == "decant_mtt_to_waste")
	assert state_change(decant["sequence"][-1], "well_plate_96.all_wells") == {
		"material_name": "formazan_crystals",
		"material_volume": 0,
	}
	assert state_change(decant["sequence"][-1], "biohazard_decant_bin") == {
		"material_name": "waste_mtt",
		"material_volume": 21.6,
	}


def test_mtt_solubilization_starts_with_crystals_and_uses_19_2_ml_dmso() -> None:
	protocol = load_protocol("mtt_solubilization_readout")
	assert protocol["initial_state"] == [
		{
			"target": "well_plate_96.all_wells",
			"state": {"material_name": "formazan_crystals", "material_volume": 0},
		},
		{
			"target": "dmso_tube",
			"state": {"material_name": "dmso", "material_volume": 50.0},
		},
	]

	add_dmso = next(step for step in protocol["steps"] if step["step_name"] == "add_dmso_to_wells")
	assert [interaction["target"] for interaction in add_dmso["sequence"]] == [
		"multichannel_pipette",
		"multichannel_pipette",
		"dmso_tube",
		"well_plate_96.all_wells",
	]
	assert state_change(add_dmso["sequence"][2], "dmso_tube") == {
		"material_name": "dmso",
		"material_volume": 30.8,
	}
	assert state_change(add_dmso["sequence"][2], "multichannel_pipette") == {
		"held_material_name": "dmso",
		"held_material_volume": 200,
	}
	assert state_change(add_dmso["sequence"][-1], "well_plate_96.all_wells") == {
		"material_name": "formazan_dmso_solution",
		"material_volume": 200,
	}
	assert state_change(add_dmso["sequence"][-1], "multichannel_pipette") == {
		"held_material_name": "empty",
		"held_material_volume": 0,
	}

	trituration = next(step for step in protocol["steps"] if step["step_name"] == "trituration_to_dissolve")
	assert [interaction["target"] for interaction in trituration["sequence"]] == [
		"multichannel_pipette",
		"well_plate_96.all_wells",
	]
	bench_scene = yaml.safe_load(
		(CELL_CULTURE / "mtt_solubilization_readout" / "scenes" / "bench_workspace.yaml").read_text(
			encoding="utf-8"
		)
	)
	assert {placement["object_name"] for placement in bench_scene["add_placements"]} >= {
		"dmso_tube",
		"multichannel_pipette",
	}

	read = next(step for step in protocol["steps"] if step["step_name"] == "read_absorbance")
	assert read["sequence"][1]["validator"]["value"] == {"wavelength_nm": 560}


def test_full_cell_culture_runner_seeds_mtt_pbs_at_its_root() -> None:
	with (REPO_ROOT / "content" / "protocols" / "runners" / "cell_culture_full" / "protocol.yaml").open(
		encoding="utf-8"
	) as handle:
		runner = yaml.safe_load(handle)
	assert runner["initial_state"] == [
		{
			"target": "pbs_bottle",
			"state": {"material_name": "pbs", "material_volume": 500},
		},
	]


def test_mtt_transfers_are_strict_stepper_clean_direct_and_in_the_runner() -> None:
	tree = load_content_tree(REPO_ROOT)
	_, _, direct_emitter = walk_protocol(tree, "mtt_reagent_prep", quiet=True)
	assert [finding for finding in direct_emitter.findings if finding.level.value == "ERROR"] == []

	_, _, runner_emitter = walk_sequence_runner(tree, "cell_culture_full", quiet=True)
	mtt_errors = [
		finding
		for finding in runner_emitter.findings
		if finding.level.value == "ERROR" and finding.protocol_name == "mtt_reagent_prep"
	]
	assert mtt_errors == []
