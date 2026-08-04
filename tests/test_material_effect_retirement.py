"""Regression coverage for visible material effects on laboratory objects."""

from pathlib import Path

import yaml

from validation.svg.asset_taxonomy_validator import validate_asset_taxonomy


REPO_ROOT = Path(__file__).resolve().parents[1]
OBJECTS_DIR = REPO_ROOT / "content" / "objects"
ASSETS_DIR = REPO_ROOT / "assets"


def _object(relative_path: str) -> dict:
	return yaml.safe_load((OBJECTS_DIR / relative_path).read_text(encoding="utf-8"))


def test_plate_wells_can_visibly_show_material_identity_and_fill_level() -> None:
	"""A treated well has state-driven material tint and a finite physical capacity."""
	plate = _object("plate/well_plate_96.yaml")
	fields = {field["field_name"]: field for field in plate["state_fields"]}
	effects = plate["visual_states"]

	assert fields["material_name"]["applies_to"] == "subpart"
	assert effects["material_volume"]["render_effect"] == "fill_height"
	assert effects["material_volume"]["capacity_ul"] > 0


def test_material_assets_validate_without_the_retired_whole_asset_renderer() -> None:
	"""Renderable material states remain valid after retiring the hidden overlay path."""
	result = validate_asset_taxonomy(ASSETS_DIR, OBJECTS_DIR)
	renderer_dir = REPO_ROOT / "src" / "scene_runtime" / "renderer"

	assert result.registry and result.selections
	assert not (renderer_dir / "anchor_material_renderer.ts").exists()
