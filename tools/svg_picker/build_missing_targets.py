#!/usr/bin/env python3
"""
Build missing targets JSON for SVG picker.

Walks content/objects/<kind>/*.yaml and extracts every asset_name value
from visual_states.<state>.cases[].output.asset_name. Diffs against the
recursive logical SVG registry. Emits missing_targets.json grouped by
state_family with behavior placement and variant_looking metadata.

Reference: content/objects/bottle/bme_tube.yaml, flask/t75_flask.yaml,
equipment/electrophoresis_tank.yaml

Known variant suffixes (case-insensitive):
	_empty, _filled, _idle, _spinning, _running, _open, _closed,
	_on, _off, _loading, _ready, _with_sample, _with_ladder,
	_v1, _v2, _v3, _v4

Deduplicates asset_names across multiple object YAMLs.
"""

import argparse
import json
import os
import subprocess
from pathlib import Path

import yaml

from validation.svg.asset_registry import build_svg_asset_registry
from validation.svg.asset_taxonomy_validator import derive_requested_asset_behavior_categories


def get_repo_root() -> str:
	"""Get repository root via git rev-parse."""
	result = subprocess.run(
		["git", "rev-parse", "--show-toplevel"],
		capture_output=True,
		text=True,
		check=True
	)
	return result.stdout.strip()


def extract_asset_names(yaml_path: str) -> list:
	"""Extract all asset_name values from a single object YAML.

	Raises yaml.YAMLError on malformed YAML and FileNotFoundError on missing
	files; silent skips would mask data loss in the picker pipeline.
	"""
	asset_names = []
	with open(yaml_path, 'r') as f:
		data = yaml.safe_load(f)

	if not data or 'visual_states' not in data:
		return asset_names

	visual_states = data['visual_states']
	for state_name, state_config in visual_states.items():
		# kind is optional per schema; skip non-svg visual states.
		if state_config.get('kind') != 'svg':
			continue
		# An svg-kind visual state has required cases/output/asset_name shape.
		for case in state_config['cases']:
			asset_name = case['output'].get('asset_name')
			if asset_name:
				asset_names.append(asset_name)

	return asset_names


def get_existing_assets(assets_dir: str) -> set[str]:
	"""Get stable logical names from the recursive asset source tree."""
	return set(build_svg_asset_registry(Path(assets_dir)).asset_names)


def extract_variant_suffix(asset_name: str) -> tuple:
	"""
	Extract variant suffix from asset_name.

	Returns (variant_suffix, state_family).
	If asset_name ends in a known variant (case-insensitive, longest match),
	return the suffix and the family (asset_name minus suffix).
	Otherwise return ("", asset_name).

	Known suffixes: _empty, _filled, _idle, _spinning, _running, _open,
	_closed, _on, _off, _loading, _ready, _with_sample, _with_ladder,
	_v1, _v2, _v3, _v4.
	"""
	known_suffixes = [
		"_with_sample",
		"_with_ladder",
		"_with_media",
		"_with_pbs",
		"_with_trypsin",
		"_with_cell_suspension",
		"_with_lid",
		"_with_module",
		"_without_lid",
		"_without_module",
		"_loading",
		"_spinning",
		"_running",
		"_closed",
		"_ready",
		"_empty",
		"_filled",
		"_idle",
		"_open",
		"_on",
		"_off",
		"_v1",
		"_v2",
		"_v3",
		"_v4",
	]

	asset_lower = asset_name.lower()
	best_match = ""
	best_len = 0

	for suffix in known_suffixes:
		if asset_lower.endswith(suffix.lower()):
			if len(suffix) > best_len:
				best_match = suffix
				best_len = len(suffix)

	if best_match:
		state_family = asset_name[:-len(best_match)]
		return (best_match, state_family)
	else:
		return ("", asset_name)


def main() -> None:
	"""Main entry point."""
	parser = argparse.ArgumentParser(
		description="Build missing targets JSON for SVG picker."
	)
	parser.add_argument(
		'--output',
		default='tools/svg_picker/missing_targets.json',
		help='Output file path for missing_targets.json'
	)
	parser.add_argument(
		'--verbose',
		action='store_true',
		help='Print progress messages'
	)
	args = parser.parse_args()

	repo_root = get_repo_root()
	content_dir = os.path.join(repo_root, 'content', 'objects')
	assets_dir = os.path.join(repo_root, 'assets', 'equipment')

	if args.verbose:
		print(f"Scanning content directory: {content_dir}")

	all_asset_names = {}
	total_refs = 0

	for kind_dir in sorted(os.listdir(content_dir)):
		kind_path = os.path.join(content_dir, kind_dir)
		if not os.path.isdir(kind_path):
			continue

		for yaml_file in sorted(os.listdir(kind_path)):
			if not yaml_file.endswith('.yaml'):
				continue

			yaml_path = os.path.join(kind_path, yaml_file)
			object_label = yaml_file[:-5]
			asset_names = extract_asset_names(yaml_path)

			for asset_name in asset_names:
				total_refs += 1
				if asset_name not in all_asset_names:
					all_asset_names[asset_name] = {
						'kind': kind_dir,
						'object_label': object_label,
						'referenced_by': []
					}
				all_asset_names[asset_name]['referenced_by'].append(yaml_path)

	existing_assets = get_existing_assets(assets_dir)
	requested_categories = derive_requested_asset_behavior_categories(Path(content_dir))

	if args.verbose:
		print(f"Total asset_name refs: {total_refs}")
		print(f"Unique asset_names: {len(all_asset_names)}")
		print(f"Existing assets: {len(existing_assets)}")

	missing_records = []

	for asset_name in sorted(all_asset_names.keys()):
		if asset_name not in existing_assets:
			info = all_asset_names[asset_name]
			variant_suffix, state_family = extract_variant_suffix(asset_name)
			variant_looking = (variant_suffix != "")
			behavior_category = requested_categories[asset_name]

			record = {
				"asset_name": asset_name,
				"referenced_by": sorted(info['referenced_by']),
				"kind": info['kind'],
				"object_label": info['object_label'],
				"state_family": state_family,
				"variant_suffix": variant_suffix,
				"variant_looking": variant_looking,
				"behavior_category": behavior_category,
				"expected_path": os.path.join(
					"assets/equipment", behavior_category, f"{asset_name}.svg"
				)
			}
			missing_records.append(record)

	if args.verbose:
		print(f"Missing assets: {len(missing_records)}")

	output_path = os.path.join(repo_root, args.output)
	os.makedirs(os.path.dirname(output_path), exist_ok=True)

	with open(output_path, 'w') as f:
		json.dump(missing_records, f, indent=2)

	if args.verbose:
		print(f"Wrote {len(missing_records)} missing targets to {output_path}")
		print(f"{len(missing_records)} missing of {total_refs} total asset_name refs")


if __name__ == '__main__':
	main()
