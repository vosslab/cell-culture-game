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


def test_gel_loading_targets_are_exact_top_well_mouths() -> None:
	"""Each lane target is its narrow, painted loading well rather than its gel body."""
	geometry, view_box = gen_object_library.derive_grid_geometry(
		"gel_cassette", load_structure("content/objects/equipment/gel_cassette.yaml")
	)
	assert geometry is not None
	assert view_box == {"min_x": 0.0, "min_y": 0.0, "width": 214.0, "height": 308.0}
	assert list(geometry) == [f"lane_{index}" for index in range(1, 11)]
	assert geometry["lane_1"] == {"shape": "rect", "x": 36.0, "y": 33.0, "w": 11.0, "h": 20.0}
	assert geometry["lane_10"] == {"shape": "rect", "x": 162.0, "y": 33.0, "w": 11.0, "h": 20.0}
	assert all(region["y"] < 57.0 for region in geometry.values())
	assert all(region["h"] <= 20.0 for region in geometry.values())


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
		assert "batch" in protocol["learning"]["goals"].lower()
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


def test_sds_batch_mixes_have_complete_visible_transfer_ledgers() -> None:
	"""One batch lesson retains the three complete and distinct sample transfers."""
	protocol = load_yaml("content/protocols/sdspage/sdspage_prepare_sample_mix_batch/protocol.yaml")
	assert [step["step_name"] for step in protocol["steps"]] == ["prepare_batch"]
	sequence = protocol["steps"][0]["sequence"]
	for index, laemmli_remaining, bme_remaining in (
		(1, 0.9925, 0.9985), (2, 0.985, 0.997), (3, 0.9775, 0.9955)
	):
		source = next(item for item in sequence if item["target"] == f"microtube_rack_8.slot_A{index}")
		assert _state_write(source["response"]["scene_operations"], f"microtube_rack_8.slot_A{index}") == {"material_name": "empty", "material_volume": 0}
		assert _state_write(source["response"]["scene_operations"], "p200_micropipette")["held_material_volume"] == 21
		final = [item for item in sequence if item["target"] == f"microtube_rack_8.slot_B{index}"][-1]
		assert _state_write(final["response"]["scene_operations"], f"microtube_rack_8.slot_B{index}") == {"material_name": "protein_sample_mixed", "material_volume": 30}
		laemmli = [item for item in sequence if item["target"] == "laemmli_4x_tube"][index - 1]
		bme = [item for item in sequence if item["target"] == "bme_tube"][index - 1]
		assert _state_write(laemmli["response"]["scene_operations"], "laemmli_4x_tube")["material_volume"] == laemmli_remaining
		assert _state_write(bme["response"]["scene_operations"], "bme_tube")["material_volume"] == bme_remaining


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

	sequence = protocol["steps"][0]["sequence"]
	setpoints = [
		(interaction["target"], interaction["validator"]["value"]["set_volume"])
		for interaction in sequence
		if interaction["validator"]["preset"] == "target_with_value"
		and "set_volume" in interaction["validator"].get("value", {})
	]
	assert setpoints == [
		("p200_micropipette", 21), ("p10_micropipette", 7.5), ("p10_micropipette", 1.5),
		("p200_micropipette", 21), ("p10_micropipette", 7.5), ("p10_micropipette", 1.5),
		("p200_micropipette", 21), ("p10_micropipette", 7.5), ("p10_micropipette", 1.5),
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
	carboy_writes = []
	for step in fill["steps"]:
		for interaction in step["sequence"]:
			for operation in interaction["response"]["scene_operations"]:
				if operation.get("type") == "ObjectStateChange" and operation.get("target") == "running_buffer_preparation_carboy":
					carboy_writes.append(operation["state"])
	assert carboy_writes
	assert all(write["material_name"] == "running_buffer_1x" for write in carboy_writes)
	assert carboy_writes[-1]["material_volume"] == 300

	chamber_volumes = {}
	for step in fill["steps"]:
		for interaction in step["sequence"]:
			for operation in interaction["response"]["scene_operations"]:
				if operation.get("type") == "ObjectStateChange" and operation.get("target") in {
					"electrophoresis_inner_chamber", "electrophoresis_outer_chamber",
				}:
					chamber_volumes[operation["target"]] = operation["state"]["material_volume"]
	assert chamber_volumes == {
		"electrophoresis_inner_chamber": 200,
		"electrophoresis_outer_chamber": 500,
	}
	assert sum(chamber_volumes.values()) == 700
	assert runner["initial_state"][0] == prepared["initial_state"][0]


def test_sds_stain_and_destain_rinses_debit_water_and_preserve_waste_volume() -> None:
	"""Rinses visibly move their stated volumes from water source through tray to waste."""
	stain = load_yaml("content/protocols/sdspage/sdspage_stain_gel/protocol.yaml")
	destain = load_yaml("content/protocols/sdspage/sdspage_destain_gel_setup/protocol.yaml")
	image = load_yaml("content/protocols/sdspage/sdspage_image_gel/protocol.yaml")
	rock = load_yaml("content/protocols/sdspage/sdspage_destain_gel_rock/protocol.yaml")

	def volume_writes(protocol: dict, target: str) -> list[float]:
		return [
			operation["state"]["material_volume"]
			for step in protocol["steps"]
			for interaction in step["sequence"]
			for operation in interaction["response"]["scene_operations"]
			if operation.get("type") == "ObjectStateChange"
			and operation.get("target") == target
			and "material_volume" in operation.get("state", {})
		]

	assert volume_writes(stain, "ddh2o_bottle")[-1] == 500
	assert volume_writes(destain, "ddh2o_bottle")[-2:] == [300, 100]
	# The rock/disposal block leaves the tray empty; imaging therefore performs
	# one measured 100 mL water rinse rather than fabricating residual destain.
	assert image["initial_state"][0]["state"]["material_volume"] == 0
	assert volume_writes(image, "ddh2o_bottle")[-1] == 0
	assert volume_writes(image, "waste_container")[-1] == 100
	assert volume_writes(rock, "destain_waste_bottle")[-1] == 250


def test_sds_destain_recycle_and_image_preserve_the_visible_learning_decisions() -> None:
	"""The revised post-run path has observable safety and interpretation states."""
	setup = load_yaml("content/protocols/sdspage/sdspage_destain_gel_setup/protocol.yaml")
	rock = load_yaml("content/protocols/sdspage/sdspage_destain_gel_rock/protocol.yaml")
	recycle = load_yaml("content/protocols/sdspage/sdspage_recycle_buffer/protocol.yaml")
	image = load_yaml("content/protocols/sdspage/sdspage_image_gel/protocol.yaml")

	remove_wipes = next(step for step in setup["steps"] if step["step_name"] == "remove_kimwipes_before_rocking")
	assert remove_wipes["next_step"] == "transfer_to_rocker"
	assert all(step["step_name"] != "remove_kimwipes" for step in rock["steps"])

	inspect = recycle["steps"][0]
	assert inspect["sequence"][-1]["target"] == "recycle_buffer_bottle"
	assert inspect["sequence"][-1]["gesture"] == "click"
	assert inspect["sequence"][-1]["validator"] == {"preset": "correct_target"}
	recycle_complete = recycle["steps"][1]
	assert recycle_complete["step_name"] == "recycle_complete_tank"
	assert [item["target"] for item in recycle_complete["sequence"]] == [
		"electrophoresis_inner_chamber", "recycle_buffer_bottle",
		"electrophoresis_outer_chamber", "recycle_buffer_bottle",
	]
	final_recovery = recycle_complete["sequence"][-1]["response"]["scene_operations"]
	assert _state_write(final_recovery, "recycle_buffer_bottle") == {
		"material_name": "running_buffer_1x_used", "material_volume": 700,
		"label_status": "running_buffer_recycle",
		"buffer_identity_status": "running_buffer_1x",
		"date_status": "date_recorded",
		"course_batch_status": "course_batch_recorded",
		"use_count": 1,
		"cap_status": "closed",
		"storage_status": "designated_buffer_storage",
	}
	assert "hazardous_liquid_waste_container" in (
		REPO_ROOT / "content/protocols/sdspage/sdspage_recycle_buffer/scenes/sdspage_recycle_buffer_workspace.yaml"
	).read_text()
	recycle_scene = load_yaml(
		"content/protocols/sdspage/sdspage_recycle_buffer/scenes/sdspage_recycle_buffer_workspace.yaml"
	)
	funnel_placement = next(
		placement
		for placement in recycle_scene["add_placements"]
		if placement["object_name"] == "recycle_buffer_funnel"
	)
	assert funnel_placement["zone"] == "rear_left"
	assert funnel_placement["depth_tier"] == 2

	capture = next(step for step in image["steps"] if step["step_name"] == "capture")
	assert capture["next_step"] == "interpret_ladder_and_sample_lanes"
	interpret = image["steps"][-1]
	assert interpret["step_name"] == "interpret_ladder_and_sample_lanes"
	assert _state_write(interpret["sequence"][0]["response"]["scene_operations"], "lightbox") == {
		"result_state": "molecular_weight_interpreted"
	}
