"""Gate test: verify every object YAML asset_name resolves in the recursive registry."""

import pathlib

import pytest
import yaml

import file_utils
import pipeline.gen_object_library as gen_object_library
from validation.svg.asset_registry import build_svg_asset_registry

REPO_ROOT = pathlib.Path(file_utils.get_repo_root())
OBJECTS_DIR = REPO_ROOT / "content" / "objects"
ASSETS_DIR = REPO_ROOT / "assets"


def _collect_asset_refs() -> dict:
	"""Walk content/objects/<kind>/*.yaml and collect asset_name -> [refs]."""
	refs = {}
	for kind_dir in sorted(OBJECTS_DIR.iterdir()):
		if not kind_dir.is_dir():
			continue
		for yaml_file in sorted(kind_dir.glob("*.yaml")):
			with open(yaml_file) as f:
				data = yaml.safe_load(f)
			if not data or "visual_states" not in data:
				continue
			for state_config in data["visual_states"].values():
				if state_config.get("kind") != "svg":
					continue
				for case in state_config.get("cases", []):
					output = case.get("output", {})
					name = output.get("asset_name")
					if name:
						refs.setdefault(name, []).append(str(yaml_file.relative_to(REPO_ROOT)))
	return refs


def _existing_assets() -> set:
	"""Return every logical name from the recursive SVG registry."""
	return set(build_svg_asset_registry(ASSETS_DIR).asset_names)


def test_every_authored_asset_ref_resolves() -> None:
	"""Behavioral gate: every visual_states asset_name must point at a real SVG."""
	refs = _collect_asset_refs()
	existing = _existing_assets()
	missing = sorted(name for name in refs if name not in existing)
	assert missing == [], (
		f"Object YAML references {len(missing)} asset_name value(s) with no SVG file: "
		f"{missing}. Either author the missing SVG under assets/equipment/<behavior>/ or update "
		f"the visual_states asset_name to an existing asset."
	)


def test_object_library_svg_collection_rejects_duplicate_logical_names(
	tmp_path: pathlib.Path,
) -> None:
	"""The generator shares the recursive registry's no-ambiguous-stem rule."""
	for behavior in ("static", "binary_state"):
		asset_dir = tmp_path / "assets" / "equipment" / behavior
		asset_dir.mkdir(parents=True, exist_ok=True)
		(asset_dir / "duplicate.svg").write_text("<svg/>", encoding="utf-8")

	with pytest.raises(ValueError, match="duplicate logical SVG basename 'duplicate'"):
		gen_object_library.collect_svg_files(str(tmp_path))
