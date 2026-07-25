"""Gate test: verify every object YAML asset_name resolves to assets/equipment/*.svg."""

import pathlib

import yaml

import file_utils

REPO_ROOT = pathlib.Path(file_utils.get_repo_root())
OBJECTS_DIR = REPO_ROOT / "content" / "objects"
ASSETS_DIR = REPO_ROOT / "assets" / "equipment"


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
	"""Return basenames (without .svg) of every file in assets/equipment/."""
	return {p.stem for p in ASSETS_DIR.glob("*.svg")}


def test_every_authored_asset_ref_resolves() -> None:
	"""Behavioral gate: every visual_states asset_name must point at a real SVG."""
	refs = _collect_asset_refs()
	existing = _existing_assets()
	missing = sorted(name for name in refs if name not in existing)
	assert missing == [], (
		f"Object YAML references {len(missing)} asset_name value(s) with no SVG file: "
		f"{missing}. Either author the missing SVG under assets/equipment/ or update "
		f"the visual_states asset_name to an existing asset."
	)
