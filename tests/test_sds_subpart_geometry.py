"""Regression checks for exact interactive SDS-PAGE structured-object geometry."""

from pathlib import Path

import yaml

import pipeline.gen_object_library as gen_object_library


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_structure(relative_path: str) -> dict:
	"""Load the production structured-object declaration."""
	with (REPO_ROOT / relative_path).open() as handle:
		data = yaml.safe_load(handle)
	return data["structure"]


def load_yaml(relative_path: str) -> dict:
	"""Load a production SDS-PAGE YAML document."""
	with (REPO_ROOT / relative_path).open() as handle:
		return yaml.safe_load(handle)


def test_gel_lanes_are_horizontal_rects_inside_the_asset_view_box() -> None:
	"""Each lane has its own non-overlapping visual hit region."""
	geometry, view_box = gen_object_library.derive_grid_geometry(
		"gel_cassette", load_structure("content/objects/equipment/gel_cassette.yaml")
	)
	assert geometry is not None
	assert view_box == {"min_x": 0.0, "min_y": 0.0, "width": 214.0, "height": 308.0}
	assert list(geometry) == [f"lane_{index}" for index in range(1, 11)]
	assert geometry["lane_1"] == {"shape": "rect", "x": 19.0, "y": 57.0, "w": 16.0, "h": 228.0}
	assert geometry["lane_10"]["x"] == 181.0


def test_sds_microtube_rack_geometry_uses_measured_two_by_four_centers() -> None:
	"""Slot targets map exactly to the drawn tube interiors, row-major."""
	geometry, view_box = gen_object_library.derive_grid_geometry(
		"microtube_rack_8", load_structure("content/objects/rack/microtube_rack_8.yaml")
	)
	assert geometry is not None
	assert view_box == {"min_x": 0.0, "min_y": 0.0, "width": 320.0, "height": 210.0}
	assert geometry["slot_A1"] == {"shape": "circle", "cx": 67.0, "cy": 67.0, "r": 20.0}
	assert geometry["slot_A4"] == {"shape": "circle", "cx": 247.0, "cy": 67.0, "r": 20.0}
	assert geometry["slot_B1"] == {"shape": "circle", "cx": 67.0, "cy": 125.0, "r": 20.0}
	assert geometry["slot_B4"] == {"shape": "circle", "cx": 247.0, "cy": 125.0, "r": 20.0}


def test_sds_batch_protocols_are_clustered_leaf_minis_with_required_learning_prefixes() -> None:
	"""Batch workflows are real SDS leaves, not repeated sequence runners."""
	for protocol_name in ("sdspage_prepare_sample_mix_batch", "sdspage_load_samples_batch"):
		relative_path = f"content/protocols/sdspage/{protocol_name}/protocol.yaml"
		protocol = load_yaml(relative_path)
		assert protocol["protocol_type"] == "mini_protocol"
		assert protocol["learning"]["objectives"].startswith(
			"Students completing this mini-protocol will have achieved"
		)
		assert protocol["learning"]["outcomes"].startswith(
			"Students completing this mini-protocol will be able to"
		)
		assert protocol["learning"]["goals"].startswith(
			"Overall, this mini-protocol aims to accomplish"
		)
		assert (REPO_ROOT / f"content/protocols/sdspage/{protocol_name}/scenes/workspace.yaml").is_file()
		assert not (REPO_ROOT / "content/protocols/runners" / protocol_name).exists()


def test_full_sds_runner_has_sixteen_unique_leaf_minis_and_loads_before_lid() -> None:
	"""The full pathway has one unambiguous, safe electrical-setup order."""
	protocol = load_yaml("content/protocols/runners/sdspage_full/protocol.yaml")
	leaves = protocol["mini_protocols"]
	assert len(leaves) == 16
	assert len(leaves) == len(set(leaves))
	assert leaves.index("sdspage_load_protein_ladder") < leaves.index("sdspage_attach_lid_and_leads")
	assert leaves.index("sdspage_load_samples_batch") < leaves.index("sdspage_attach_lid_and_leads")
	assert "16 focused mini-protocols" in protocol["learning"]["goals"]


def _state_write(operations: list[dict], target: str) -> dict:
	"""Return the one explicit state write for a transfer participant."""
	matches = [
		operation["state"]
		for operation in operations
		if operation["type"] == "ObjectStateChange" and operation["target"] == target
	]
	assert len(matches) == 1
	return matches[0]


def _assert_sample_mix_cycle(
	sequence: list[dict], source_slot: str, destination_slot: str, cycle_index: int
) -> None:
	"""Require every batch sample to conserve its three visible transfers."""
	interactions = {interaction["target"]: [] for interaction in sequence}
	for interaction in sequence:
		interactions.setdefault(interaction["target"], []).append(interaction)

	raw_draw = interactions[source_slot][0]["response"]["scene_operations"]
	assert _state_write(raw_draw, source_slot) == {"material_name": "empty", "material_volume": 0}
	assert _state_write(raw_draw, "p200_micropipette") == {
		"held_material_name": "protein_sample_raw",
		"held_material_volume": 21,
	}

	raw_dispense = interactions[destination_slot][0]["response"]["scene_operations"]
	assert _state_write(raw_dispense, destination_slot) == {
		"material_name": "protein_sample_raw",
		"material_volume": 21,
	}
	assert _state_write(raw_dispense, "p200_micropipette") == {
		"held_material_name": "empty",
		"held_material_volume": 0,
	}

	laemmli_draw = interactions["laemmli_4x_tube"][0]["response"]["scene_operations"]
	assert _state_write(laemmli_draw, "laemmli_4x_tube")["material_volume"] == 1 - cycle_index * 0.0075
	assert _state_write(laemmli_draw, "p10_micropipette") == {
		"held_material_name": "laemmli_4x",
		"held_material_volume": 7.5,
	}
	bme_draw = interactions["bme_tube"][0]["response"]["scene_operations"]
	assert _state_write(bme_draw, "bme_tube")["material_volume"] == 1 - cycle_index * 0.0015
	assert _state_write(bme_draw, "p10_micropipette") == {
		"held_material_name": "bme",
		"held_material_volume": 1.5,
	}

	destination_writes = interactions[destination_slot]
	assert _state_write(destination_writes[1]["response"]["scene_operations"], destination_slot)[
		"material_volume"
	] == 28.5
	final_operations = destination_writes[2]["response"]["scene_operations"]
	assert _state_write(final_operations, destination_slot) == {
		"material_name": "protein_sample_mixed",
		"material_volume": 30,
	}
	assert _state_write(final_operations, "p10_micropipette") == {
		"held_material_name": "empty",
		"held_material_volume": 0,
	}


def test_sds_batch_mixes_have_complete_visible_transfer_ledgers() -> None:
	"""Every 30 uL batch mix debits, holds, dispenses, and clears visibly."""
	protocol = load_yaml("content/protocols/sdspage/sdspage_prepare_sample_mix_batch/protocol.yaml")
	for index, step in enumerate(protocol["steps"], start=1):
		_assert_sample_mix_cycle(
			step["sequence"],
			f"microtube_rack_8.slot_A{index}",
			f"microtube_rack_8.slot_B{index}",
			index,
		)


def test_sds_batch_uses_declared_pipettes_within_their_physical_ranges() -> None:
	"""The learner visibly switches tools, and every setpoint fits that tool."""
	protocol = load_yaml("content/protocols/sdspage/sdspage_prepare_sample_mix_batch/protocol.yaml")
	scene = load_yaml(
		"content/protocols/sdspage/sdspage_prepare_sample_mix_batch/scenes/workspace.yaml"
	)
	p10 = load_yaml("content/objects/pipette/p10_micropipette.yaml")
	p200 = load_yaml("content/objects/pipette/p200_micropipette.yaml")
	pipette_fields = {
		"p10_micropipette": next(
			field for field in p10["state_fields"] if field["field_name"] == "set_volume"
		),
		"p200_micropipette": next(
			field for field in p200["state_fields"] if field["field_name"] == "set_volume"
		),
	}

	placements = {
		placement["object_name"]: placement["placement_name"]
		for placement in scene["add_placements"]
	}
	assert placements["p10_micropipette"] == "center_p10_reagent_micropipette"
	assert placements["p200_micropipette"] == "center_p200_sample_micropipette"
	assert "center_micropipette" in scene["remove_placements"]

	for step in protocol["steps"]:
		sequence = step["sequence"]
		assert any(
			interaction["target"] == "p10_micropipette"
			and interaction["gesture"] == "click"
			for interaction in sequence
		)
		setpoints = [
			(interaction["target"], interaction["validator"]["value"]["set_volume"])
			for interaction in sequence
			if interaction["validator"]["preset"] == "target_with_value"
			and "set_volume" in interaction["validator"].get("value", {})
		]
		assert setpoints == [
			("p200_micropipette", 21),
			("p10_micropipette", 7.5),
			("p10_micropipette", 1.5),
		]
		for target, value in setpoints:
			field = pipette_fields[target]
			assert field["min"] <= value <= field["max"]


def test_sds_running_buffer_uses_one_carboy_from_preparation_through_tank_fill() -> None:
	"""The prepared 1 L carboy is the only source consumed by both tank chambers."""
	prepared = load_yaml("content/protocols/sdspage/sdspage_prepare_running_buffer/protocol.yaml")
	fill = load_yaml("content/protocols/sdspage/sdspage_fill_tank_buffer/protocol.yaml")
	runner = load_yaml("content/protocols/runners/sdspage_full/protocol.yaml")
	assert prepared["initial_state"][0] == {
		"target": "running_buffer_preparation_carboy",
		"state": {"material_name": "empty", "material_volume": 0},
	}
	assert [
		interaction["target"]
		for step in fill["steps"]
		for interaction in step["sequence"]
		if interaction["target"].endswith("carboy")
	] == ["running_buffer_preparation_carboy", "running_buffer_preparation_carboy"]
	inner_operations = fill["steps"][0]["sequence"][-1]["response"]["scene_operations"]
	outer_operations = fill["steps"][1]["sequence"][-1]["response"]["scene_operations"]
	assert _state_write(inner_operations, "running_buffer_preparation_carboy") == {
		"material_name": "running_buffer_1x",
		"material_volume": 400,
	}
	assert _state_write(outer_operations, "running_buffer_preparation_carboy") == {
		"material_name": "empty",
		"material_volume": 0,
	}
	assert runner["initial_state"][0] == prepared["initial_state"][0]


def test_sds_stain_and_destain_rinses_debit_water_and_preserve_waste_volume() -> None:
	"""Rinses visibly move their stated volumes from water source through tray to waste."""
	stain = load_yaml("content/protocols/sdspage/sdspage_stain_gel/protocol.yaml")
	destain = load_yaml("content/protocols/sdspage/sdspage_destain_gel_setup/protocol.yaml")
	image = load_yaml("content/protocols/sdspage/sdspage_image_gel/protocol.yaml")
	rock = load_yaml("content/protocols/sdspage/sdspage_destain_gel_rock/protocol.yaml")

	assert _state_write(stain["steps"][0]["sequence"][1]["response"]["scene_operations"], "ddh2o_bottle")[
		"material_volume"
	] == 500
	assert _state_write(destain["steps"][0]["sequence"][1]["response"]["scene_operations"], "ddh2o_bottle")[
		"material_volume"
	] == 300
	assert _state_write(destain["steps"][1]["sequence"][0]["response"]["scene_operations"], "ddh2o_bottle")[
		"material_volume"
	] == 100
	assert _state_write(image["steps"][0]["sequence"][4]["response"]["scene_operations"], "ddh2o_bottle")[
		"material_volume"
	] == 0
	assert _state_write(image["steps"][0]["sequence"][-2]["response"]["scene_operations"], "waste_container")[
		"material_volume"
	] == 100
	assert _state_write(rock["steps"][-1]["sequence"][-1]["response"]["scene_operations"], "destain_waste_bottle")[
		"material_volume"
	] == 250
