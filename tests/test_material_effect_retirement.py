"""M6 gates for retiring the whole-asset liquid-overlay path."""

from pathlib import Path

import yaml

from validation.svg.asset_registry import build_svg_asset_registry
from validation.svg.asset_taxonomy_validator import validate_asset_taxonomy


REPO_ROOT = Path(__file__).resolve().parents[1]
OBJECTS_DIR = REPO_ROOT / "content" / "objects"
ASSETS_DIR = REPO_ROOT / "assets"
VARIABLE_VOLUME_ASSETS = {
	"bottle_medium_pink",
	"falcon_15ml",
	"falcon_50ml",
	"microtube",
	"serological_pipette",
}


def _objects() -> dict[Path, dict]:
	"""Load the authored object declarations indexed by repository path."""
	return {
		path.relative_to(REPO_ROOT): yaml.safe_load(path.read_text(encoding="utf-8"))
		for path in sorted(OBJECTS_DIR.rglob("*.yaml"))
	}


def _selected_assets(definition: dict) -> set[str]:
	"""Return every whole-form asset selected by one object declaration."""
	assets: set[str] = set()
	for state in definition.get("visual_states", {}).values():
		if not isinstance(state, dict):
			continue
		for case in state.get("cases", []):
			output = case.get("output", {})
			if isinstance(output, dict) and isinstance(output.get("asset_name"), str):
				assets.add(output["asset_name"])
	return assets


def test_object_level_amount_effects_select_only_the_five_variable_volume_forms() -> None:
	"""Only the five gravity-part forms may receive object-level fill effects."""
	bindings: dict[Path, set[str]] = {}
	for path, definition in _objects().items():
		states = definition.get("visual_states", {})
		if any(
			state.get("applies_to") == "object"
			and state.get("render_effect") == "fill_height"
			for state in states.values()
			if isinstance(state, dict)
		):
			bindings[path] = _selected_assets(definition)

	result = validate_asset_taxonomy(ASSETS_DIR, OBJECTS_DIR)
	registered_variable_volume_assets = {
		asset_name
		for asset_name, category in result.categories
		if category == "variable_volume"
	}
	assert registered_variable_volume_assets == VARIABLE_VOLUME_ASSETS
	assert set().union(*bindings.values()) == registered_variable_volume_assets
	assert all(assets <= registered_variable_volume_assets for assets in bindings.values())
	assert {
		entry.asset_name
		for entry in build_svg_asset_registry(ASSETS_DIR).entries
		if entry.source_path.parts[-2:] == ("variable_volume", f"{entry.asset_name}.svg")
	} == registered_variable_volume_assets


def test_non_vessel_material_states_are_discrete_or_structured_without_fill_height() -> None:
	"""M6 keeps complete forms and structured tinting out of vessel paint."""
	objects = _objects()
	for path, definition in objects.items():
		for state in definition.get("visual_states", {}).values():
			if not isinstance(state, dict):
				continue
			assert "fill_height(" not in str(state.get("formula", "")), path

	material_tints = {
		(path, state.get("applies_to"), state.get("target"))
		for path, definition in objects.items()
		for state in definition.get("visual_states", {}).values()
		if isinstance(state, dict) and state.get("render_effect") == "material_tint"
	}
	assert material_tints == {
		(Path("content/objects/equipment/hemocytometer_slide.yaml"), "subpart", "subpart_geometry"),
		(Path("content/objects/plate/well_plate_96.yaml"), "subpart", "subpart_geometry"),
	}

	structured_volume_deferrals = {
		path
		for path, definition in objects.items()
		if (definition.get("visual_states", {}).get("material_volume") or {}) == {
			"kind": "composite",
			"applies_to": "subpart",
			"composite": [],
		}
	}
	assert {
		Path("content/objects/equipment/gel_cassette.yaml"),
		Path("content/objects/rack/conical_15ml_rack.yaml"),
		Path("content/objects/rack/dilution_tube_rack_8.yaml"),
		Path("content/objects/rack/microtube_rack_8.yaml"),
	} <= structured_volume_deferrals

	assert _selected_assets(objects[Path("content/objects/flask/t75_flask.yaml")]) == {
		"t75_flask_empty",
		"t75_flask_filled",
	}
	assert _selected_assets(objects[Path("content/objects/flask/t75_flask_new.yaml")]) == {
		"t75_flask_empty",
		"t75_flask_filled",
	}
	assert _selected_assets(objects[Path("content/objects/pipette/aspirating_pipette.yaml")]) == {
		"aspirating_pipette",
	}
	assert _selected_assets(objects[Path("content/objects/equipment/staining_tray.yaml")]) == {
		"staining_tray_empty",
		"staining_tray_buffer",
		"staining_tray_stain",
		"staining_tray_destain",
		"staining_tray_water",
	}


def test_retired_anchor_renderer_has_no_source_path_or_token() -> None:
	"""The old overlay renderer cannot re-enter the runtime source tree."""
	renderer_dir = REPO_ROOT / "src" / "scene_runtime" / "renderer"
	assert not (renderer_dir / "anchor_material_renderer.ts").exists()
	for source in renderer_dir.rglob("*.ts*"):
		assert "anchor_material_renderer" not in source.read_text(encoding="utf-8"), source
