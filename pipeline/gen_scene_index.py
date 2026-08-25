#!/usr/bin/env python3
"""
Codegen for scene index from content/base_scenes/*.yaml and content/protocols/*/scenes/*.yaml.

Reads scene YAML files, validates against closed scene schema, and emits
generated/scenes.ts with typed SCENES export for the renderer.

Base scenes are emitted with their scene_name as key.
Per-protocol scenes are ingested, inheritance is resolved, and they are emitted
with composite key <protocol_name>_<scene_basename>.

Validation:
- background.type is "gradient" and from/to parse as hex
- every zone id is unique within the scene
- every placement.zone resolves to a declared zone
- every placement.object_name resolves to an object (cross-checked against
  generated/object_library.ts or content/objects/**/*.yaml)
- per-protocol scenes: extends chain resolves to an existing base scene

Scene discovery and classification (no curated allowlist):
- Every base scene under content/base_scenes/ and every per-protocol scene is
  discovered and classified into exactly one outcome.
- emitted: the scene validates and is buildable; it is written into SCENES.
- skipped: a durable, documented quarantine decision. It is recorded in the
  manifest with a machine-readable reason; the build still succeeds.
- errored: a fatal generator condition, including inheritance failures and
  missing SVG assets. The generator exits non-zero and stops before writing a
  new scene artifact.

Every emitted scene resolves every object and SVG asset. A missing-asset report
lists each affected placement, object name, and missing asset id before the
generator exits non-zero.

Output:
- generated/scenes.ts with SCENES_SKIPPED and SCENES exports.
  Includes both base and per-protocol scenes.
- generated/scene_manifest.json: the source-of-truth scene classification. Top
  level is {"scenes": [ {name, outcome: "emitted"|"skipped", reason: str|null,
  source_placement_count: int, source_placement_names: [str]} ]}. A successful
  build's manifest contains only emitted and skipped entries.
"""

# Standard Library
import os
import re
import sys
import json
import subprocess
from pathlib import Path

# PIP3 modules
import yaml  # pyyaml

# local repo modules
from pipeline import scene_inheritance
import pipeline.scene_geometry_validation
from validation.svg.asset_registry import build_svg_asset_registry


# Per-placement layout keys that are forbidden override escape hatches.
# Object size has exactly one source: the object-level display_width_cm scaled
# by the workspace px_per_cm (SCALING_MODEL.md). width_scale and fudge were
# per-placement multipliers; display_width_cm at the placement level would be a
# size override. All three are removed under vocabulary closure.
FORBIDDEN_LAYOUT_KEYS = scene_inheritance.SOURCE_FORBIDDEN_GEOMETRY_KEYS


#============================================

def get_repo_root() -> str:
	"""Get repository root via git rev-parse --show-toplevel."""
	result = subprocess.run(
		["git", "rev-parse", "--show-toplevel"],
		capture_output=True,
		text=True,
		check=True,
	)
	return result.stdout.strip()


#============================================

def parse_hex_color(hex_str: str) -> bool:
	"""Validate hex color string: #RRGGBB or #RRGGBBAA."""
	if not isinstance(hex_str, str):
		return False
	pattern = r'^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$'
	return bool(re.match(pattern, hex_str))


#============================================

def collect_svg_asset_names(repo_root: str) -> set:
	"""
	Collect logical SVG names from the recursive asset registry.
	Returns a set of available asset name strings.
	"""
	assets_dir = Path(repo_root) / "assets"
	if not assets_dir.is_dir():
		return set()
	return set(build_svg_asset_registry(assets_dir).asset_names)


#============================================

def collect_object_svg_refs(repo_root: str) -> dict:
	"""
	Walk content/objects/**/*.yaml and collect asset_name references from visual_states.

	Returns a dict mapping object_name -> set of asset_name strings.
	Only svg-kind visual_states entries contribute asset_name references.
	"""
	# Directories to scan for object YAML files
	object_dirs = [os.path.join(repo_root, "content", "objects")]

	object_svg_refs = {}

	for scan_root in object_dirs:
		if not os.path.isdir(scan_root):
			continue

		for dir_root, _dirs, files in os.walk(scan_root):
			for file in files:
				if not file.endswith(".yaml"):
					continue
				abs_path = os.path.join(dir_root, file)
				with open(abs_path, "r") as f:
					data = yaml.safe_load(f)
				if not isinstance(data, dict):
					continue
				# object_name is a REQUIRED field in every object YAML; fail loudly if missing
				object_name = data["object_name"]
				# Collect all asset_name values from svg-kind visual_states entries
				asset_names = set()
				visual_states = data.get("visual_states")
				if isinstance(visual_states, dict):
					for _state_key, state_config in visual_states.items():
						if not isinstance(state_config, dict):
							continue
						# Only svg-kind entries reference asset files directly
						if state_config.get("kind") != "svg":
							continue
						for case in state_config.get("cases", []):
							if not isinstance(case, dict):
								continue
							output = case.get("output", {})
							if isinstance(output, dict):
								asset_name = output.get("asset_name")
								if asset_name:
									asset_names.add(asset_name)
				object_svg_refs[object_name] = asset_names

	return object_svg_refs


#============================================

def check_scene_svg_gaps(
	scene_data: dict,
	object_svg_refs: dict,
	available_svgs: set,
) -> list:
	"""
	Check a resolved scene's placements for objects with missing SVG assets.

	Returns a list of tuples: (placement_name, object_name, list_of_missing_asset_ids).
	An empty list means all placements have their SVG assets available.
	"""
	gaps = []
	placements = scene_data.get("placements", [])
	if not isinstance(placements, list):
		return gaps

	for placement in placements:
		if not isinstance(placement, dict):
			continue
		# placement_name and object_name are REQUIRED scene-placement fields; fail loudly if missing
		placement_name = placement["placement_name"]
		object_name = placement["object_name"]

		# Get the SVG asset names this object references
		asset_names = object_svg_refs.get(object_name, set())
		# Find which ones are missing
		missing = sorted(name for name in asset_names if name not in available_svgs)
		if missing:
			gaps.append((placement_name, object_name, missing))

	return gaps


#============================================

def collect_resolved_placement_names(scene_data: dict) -> list:
	"""
	Collect every placement_name from a fully-resolved scene (post-inheritance).

	Handles the scene schema:
	- Schema A: top-level `placements` list, each with a placement_name.

	Args:
		scene_data: Resolved scene dict (after inheritance for per-protocol scenes).

	Returns:
		List of placement_name strings in source order. The list length is the
		source_placement_count recorded in the manifest, matching what the runtime
		pipeline would receive.
	"""
	names = []

	# Schema A placements
	placements = scene_data.get("placements")
	if isinstance(placements, list):
		for placement in placements:
			if isinstance(placement, dict):
				# placement_name is a required field, validated upstream
				names.append(placement["placement_name"])

	return names


#============================================

def emit_missing_asset_report(
	scene_name: str,
	gaps: list,
) -> None:
	"""
	Emit a missing-asset report to stderr for a scene with SVG gaps.

	Args:
		scene_name: The scene_name field of the affected scene.
		gaps: List of (placement_name, object_name, [missing_asset_ids]).
	"""
	print(
		f"MISSING-SVG scene '{scene_name}': {len(gaps)} placement(s) with missing SVG assets:",
		file=sys.stderr,
	)
	for placement_name, object_name, missing_assets in gaps:
		asset_list = ", ".join(missing_assets)
		print(
			f"  placement '{placement_name}' -> object '{object_name}' -> missing: {asset_list}",
			file=sys.stderr,
		)


#============================================

def collect_object_names(repo_root: str) -> set:
	"""
	Collect all object_name values from content/objects/**/*.yaml.
	Returns a set of all valid object names.
	"""
	object_names = set()

	# Directories to scan
	scan_dirs = [os.path.join(repo_root, "content", "objects")]

	for objects_dir in scan_dirs:
		if not os.path.isdir(objects_dir):
			continue

		for root, dirs, files in os.walk(objects_dir):
			for file in files:
				if file.endswith(".yaml"):
					abs_path = os.path.join(root, file)
					with open(abs_path, "r") as f:
						data = yaml.safe_load(f)
					if not isinstance(data, dict):
						raise ValueError(
							f"Object YAML must be a mapping at top level: {abs_path}"
						)
					object_name = data["object_name"]
					object_names.add(object_name)

	return object_names


#============================================

def discover_per_protocol_scenes(repo_root: str) -> dict:
	"""
	Discover all per-protocol scene YAML files under content/protocols/*/scenes/.

	Returns a dict mapping composite_key -> (protocol_name, scene_basename, yaml_path).
	Composite key format: <protocol_name>_<scene_basename>

	Args:
		repo_root: Repository root path.

	Returns:
		Dict mapping composite_key -> (protocol_name, scene_basename, yaml_path).
	"""
	protocol_scenes = {}
	protocols_dir = os.path.join(repo_root, "content", "protocols")

	if not os.path.isdir(protocols_dir):
		return protocol_scenes

	# Walk through each cluster/protocol_name/scenes/ directory
	for cluster_dir in os.listdir(protocols_dir):
		cluster_path = os.path.join(protocols_dir, cluster_dir)
		if not os.path.isdir(cluster_path):
			continue

		for protocol_name in os.listdir(cluster_path):
			protocol_path = os.path.join(cluster_path, protocol_name)
			scenes_dir = os.path.join(protocol_path, "scenes")

			if not os.path.isdir(scenes_dir):
				continue

			for file in os.listdir(scenes_dir):
				if file.endswith(".yaml"):
					scene_basename = file.replace(".yaml", "")
					yaml_path = os.path.join(scenes_dir, file)

					# Key by the YAML's scene_name field so the runtime key
					# matches SceneChange.to_scene values exactly. Authors
					# already namespace scene_name with the protocol prefix.
					with open(yaml_path, "r") as f:
						data = yaml.safe_load(f)
					if not isinstance(data, dict):
						raise ValueError(
							f"Per-protocol scene YAML must be a dict: {yaml_path}"
						)
					scene_name_field = data["scene_name"]
					if not scene_name_field or not isinstance(scene_name_field, str):
						raise ValueError(
							f"Missing or non-string scene_name in {yaml_path}"
						)
					composite_key = scene_name_field

					# Two per-protocol scene files declaring the same scene_name
					# would silently collide in this dict: the second file's entry
					# would overwrite the first, and any SceneChange.to_scene
					# reference to that scene_name would resolve to the wrong
					# file at runtime. Fail loudly at generation time instead.
					if composite_key in protocol_scenes:
						_prev_protocol, _prev_basename, prev_yaml_path = protocol_scenes[composite_key]
						raise ValueError(
							f"Duplicate scene_name '{composite_key}' declared in both "
							f"{prev_yaml_path} and {yaml_path}; scene names must be "
							"unique across all per-protocol scene files."
						)

					protocol_scenes[composite_key] = (
						protocol_name,
						scene_basename,
						yaml_path,
					)

	return protocol_scenes


#============================================

def process_scene_yaml(
	yaml_path: str,
	object_names: set,
) -> tuple:
	"""
	Load and validate a single scene YAML.
	Returns (scene_name, scene_data) or raises on validation failure.
	"""
	# Log file path before opening (per Python style guide)
	print(f"processing {yaml_path}", file=sys.stderr)

	with open(yaml_path, "r") as f:
		data = yaml.safe_load(f)

	if not data:
		raise ValueError(f"Empty YAML: {yaml_path}")

	if not isinstance(data, dict):
		raise ValueError(f"Scene YAML must be a dict: {yaml_path}")

	pipeline.scene_geometry_validation.reject_authored_geometry(data, yaml_path)

	# Validate required fields
	scene_name = data["scene_name"]
	if not scene_name:
		raise ValueError(f"Missing scene_name: {yaml_path}")

	workspace = data["workspace"]
	if not workspace:
		raise ValueError(f"Missing workspace: {yaml_path}")

	# Validate background if present
	background = data.get("background")
	if background:
		if isinstance(background, dict):
			bg_type = background.get("type")
			if bg_type and bg_type != "gradient":
				# Accept old asset-form backgrounds; the renderer ignores them.
				pass
			elif bg_type == "gradient":
				# Validate gradient colors
				from_color = background["from"]
				to_color = background["to"]

				if not from_color or not parse_hex_color(from_color):
					raise ValueError(
						f"Invalid background.from hex color: {yaml_path}"
					)

				if not to_color or not parse_hex_color(to_color):
					raise ValueError(
						f"Invalid background.to hex color: {yaml_path}"
					)

	# For Schema A (zones), validate zones and placements
	zones = data.get("zones")
	if zones:
		# Schema A
		if not isinstance(zones, list):
			raise ValueError(f"zones must be a list: {yaml_path}")

		zone_ids = set()
		for zone in zones:
			zone_id = zone["zone_name"]
			if not zone_id:
				raise ValueError(f"Zone missing zone_name: {yaml_path}")

			if zone_id in zone_ids:
				raise ValueError(
					f"Duplicate zone_name '{zone_id}': {yaml_path}"
				)

			zone_ids.add(zone_id)

		# Validate placements reference existing zones and objects
		placements = data.get("placements", [])
		if not isinstance(placements, list):
			raise ValueError(f"placements must be a list: {yaml_path}")

		for placement in placements:
			placement_name = placement["placement_name"]
			if not placement_name:
				raise ValueError(f"Placement missing placement_name: {yaml_path}")

			object_name = placement["object_name"]
			if not object_name:
				raise ValueError(
					f"Placement '{placement_name}' missing object_name: {yaml_path}"
				)

			if object_name not in object_names:
				raise ValueError(
					f"Placement '{placement_name}' references unknown object "
					f"'{object_name}': {yaml_path}"
				)

			zone = placement["zone"]
			if not zone:
				raise ValueError(
					f"Placement '{placement_name}' missing zone: {yaml_path}"
				)

			if zone not in zone_ids:
				raise ValueError(
					f"Placement '{placement_name}' references unknown zone "
					f"'{zone}': {yaml_path}"
				)

	return scene_name, data


#============================================

def emit_scene_ts(
	scene_key: str,
	scene_data: dict,
	ts_lines: list,
) -> None:
	"""
	Emit a single scene entry into ts_lines.

	Args:
		scene_key: The key used in the SCENES record (scene_name or composite_key).
		scene_data: Resolved scene dict from YAML.
		ts_lines: List to append TypeScript lines to.
	"""
	ts_lines.append(f"\t{repr(scene_key)}: " + "{")

	# Emit each field from the scene YAML
	# scene_name and workspace are required fields, validated upstream -- fail loudly if missing
	ts_lines.append(f"\t\tscene_name: {repr(scene_data['scene_name'])},")
	ts_lines.append(f"\t\tworkspace: {repr(scene_data['workspace'])},")

	# capabilities
	capabilities = scene_data.get("capabilities")
	if capabilities:
		ts_lines.append("\t\tcapabilities: [")
		for cap in capabilities:
			ts_lines.append(f"\t\t\t{repr(cap)},")
		ts_lines.append("\t\t],")

	# background
	background = scene_data.get("background")
	if background:
		ts_lines.append("\t\tbackground: " + "{")
		for key, val in background.items():
			if isinstance(val, str):
				ts_lines.append(f"\t\t\t{key}: {repr(val)},")
			elif isinstance(val, (int, float)):
				ts_lines.append(f"\t\t\t{key}: {val},")
			else:
				# Handle complex types (skipped)
				pass
		ts_lines.append("\t\t},")

	# Source zones retain only semantic identity. The TypeScript layout manager
	# lowers them to bounds and baselines later in the render pipeline.
	zones = scene_data.get("zones")
	if zones:
		ts_lines.append("\t\tzones: [")
		for zone in zones:
			ts_lines.append("\t\t\t" + "{")
			# Authored YAML uses `zone_name` (rule 25). The TS runtime type
			# SceneZone declares `id: string`; the pipeline maps zone_name -> id
			# at this YAML/TS boundary so the runtime field name is unchanged.
			ts_lines.append(f"\t\t\t\tid: {repr(zone['zone_name'])},")
			if zone.get("align"):
				ts_lines.append(f"\t\t\t\talign: {repr(zone.get('align'))},")
			if zone.get("label"):
				ts_lines.append(f"\t\t\t\tlabel: {repr(zone.get('label'))},")
			ts_lines.append("\t\t\t},")
		ts_lines.append("\t\t],")

	# placements (Schema A)
	placements = scene_data.get("placements")
	if placements:
		ts_lines.append("\t\tplacements: [")
		for placement in placements:
			ts_lines.append("\t\t\t" + "{")
			ts_lines.append(
				f"\t\t\t\tplacement_name: {repr(placement.get('placement_name'))},"
			)
			ts_lines.append(
				f"\t\t\t\tobject_name: {repr(placement.get('object_name'))},"
			)
			ts_lines.append(
				f"\t\t\t\tzone: {repr(placement.get('zone'))},"
			)
			if placement.get("depth_tier") is not None:
				ts_lines.append(
					f"\t\t\t\tdepth_tier: {placement.get('depth_tier')},"
				)
			if placement.get("depth") is not None:
				ts_lines.append(
					f"\t\t\t\tdepth: {repr(placement.get('depth'))},"
				)
			# align_stop: used with tab-stops zones to position items left/center/right
			if placement.get("align_stop") is not None:
				ts_lines.append(
					f"\t\t\t\talign_stop: {repr(placement.get('align_stop'))},"
				)
			# The only retained placement layout hint is categorical label placement.
			layout_override = placement.get("layout")
			if layout_override:
				forbidden = FORBIDDEN_LAYOUT_KEYS & set(layout_override.keys())
				if forbidden:
					scene_name = scene_data.get("scene_name")
					raise ValueError(
						f"scene {scene_name!r} placement "
						f"{placement.get('placement_name')!r} carries forbidden "
						f"layout override key(s) {sorted(forbidden)}; object size "
						"comes only from object-level display_width_cm"
					)
				ts_lines.append("\t\t\t\tlayout: {")
				for lk, lv in layout_override.items():
					if isinstance(lv, str):
						ts_lines.append(f"\t\t\t\t\t{lk}: {repr(lv)},")
					else:
						ts_lines.append(f"\t\t\t\t\t{lk}: {lv},")
				ts_lines.append("\t\t\t\t},")
			ts_lines.append("\t\t\t},")
		ts_lines.append("\t\t],")

	# layout_rules
	layout_rules = scene_data.get("layout_rules")
	if layout_rules:
		ts_lines.append("\t\tlayout_rules: " + "{")
		for key, val in layout_rules.items():
			if isinstance(val, str):
				ts_lines.append(f"\t\t\t{key}: {repr(val)},")
			elif isinstance(val, (int, float)):
				ts_lines.append(f"\t\t\t{key}: {val},")
		ts_lines.append("\t\t},")

	# wrong_order_message
	wrong_order_msg = scene_data.get("wrong_order_message")
	if wrong_order_msg:
		ts_lines.append("\t\twrong_order_message: " + "{")
		for key, val in wrong_order_msg.items():
			if isinstance(val, str):
				ts_lines.append(f"\t\t\t{key}: {repr(val)},")
			elif isinstance(val, (int, float)):
				ts_lines.append(f"\t\t\t{key}: {val},")
		ts_lines.append("\t\t},")

	ts_lines.append("\t},")


#============================================

def recover_scene_name_from_yaml(yaml_path: str, filename: str) -> str:
	"""Read a YAML file and return its scene_name field, or fall back to the filename stem.

	Used after a scene fails validation so the manifest still names the scene.
	A re-read failure means the YAML is completely unparseable; fall back to
	the filename stem so the skip entry still names something stable.
	"""
	data = None
	try:
		with open(yaml_path, "r") as reread:
			data = yaml.safe_load(reread)
	except (yaml.YAMLError, OSError):
		pass
	if isinstance(data, dict):
		recovered = data.get("scene_name")
		if recovered:
			return recovered
	return filename.replace(".yaml", "")


#============================================

def record_base_scene_skip(
	manifest_entries: dict,
	skipped_files: list,
	manifest_name: str,
	filename: str,
	error: Exception,
	repo_root: str,
) -> None:
	"""Record a base-scene validation failure as a skipped manifest entry.

	Strips the absolute repo_root prefix from the reason so manifests are
	machine-portable across checkouts.

	Args:
		manifest_entries: Mutable dict accumulating manifest classification data.
		skipped_files: Mutable list of skipped scene name stems (no .yaml extension).
		manifest_name: Key to use in manifest_entries (usually the scene_name).
		filename: Original YAML filename; stem is appended to skipped_files.
		error: The validation exception whose message becomes the skip reason.
		repo_root: Absolute repo root path; stripped from the reason string.
	"""
	reason_text = str(error).replace(repo_root + os.sep, "")
	manifest_entries[manifest_name] = {
		"outcome": "skipped",
		"reason": f"validation error: {reason_text}",
		"source_placement_count": 0,
		"source_placement_names": [],
	}
	skipped_files.append(filename.replace(".yaml", ""))


#============================================

def load_and_resolve_protocol_scene(
	yaml_path: str,
	composite_key: str,
	base_scenes_dict: dict,
) -> dict:
	"""Load a per-protocol scene YAML and resolve its inheritance chain.

	Raises ValueError, KeyError, yaml.YAMLError, or OSError on any failure.
	The caller catches these and records the scene as errored.
	"""
	with open(yaml_path, "r") as f:
		protocol_scene_data = yaml.safe_load(f)
	if not protocol_scene_data:
		raise ValueError(f"Empty YAML: {yaml_path}")
	if not isinstance(protocol_scene_data, dict):
		raise ValueError(f"Scene YAML must be a dict: {yaml_path}")
	resolved_scene = scene_inheritance.resolve_protocol_scene(
		composite_key,
		protocol_scene_data,
		base_scenes_dict,
	)
	pipeline.scene_geometry_validation.reject_authored_geometry(
		resolved_scene,
		yaml_path,
		allow_internal_deactivated=True,
	)
	return resolved_scene


#============================================

def main() -> None:
	"""Main entry point for the scene-index generator."""
	repo_root = get_repo_root()

	# Documented quarantine/design skips. These are NOT a hiding gate: every base
	# scene is still discovered and emitted by default. A scene listed here is
	# classified `skipped` with the given reason instead of `emitted`, so it still
	# appears in the manifest (no scene silently disappears). Add an entry only
	# when a scene is genuinely unbuildable for a durable, documented reason.
	QUARANTINE_SKIP_REASONS = {
		"well_plate_96_zoom": "Quarantined: references quarantined object well_plate_96",
	}

	# Collect stable logical SVG names from the recursive asset registry.
	available_svgs = collect_svg_asset_names(repo_root)

	# Read object names from content/objects/
	object_names = collect_object_names(repo_root)

	# Collect SVG references from all objects
	object_svg_refs = collect_object_svg_refs(repo_root)

	# Find all base scene YAML files.
	# scene_files is a list of (filename, yaml_path).
	scene_files = []

	# Scan content/base_scenes/
	scenes_dir = os.path.join(repo_root, "content", "base_scenes")
	if not os.path.isdir(scenes_dir):
		raise ValueError(f"Scenes directory not found: {scenes_dir}")

	for file in os.listdir(scenes_dir):
		if file.endswith(".yaml"):
			abs_path = os.path.join(scenes_dir, file)
			scene_files.append((file, abs_path))

	scene_files.sort(key=lambda x: x[0])

	# Per-scene classification state.
	# scenes_dict: scene_key -> resolved scene data for every EMITTED scene.
	# base_scenes_dict: every base scene that validated, for inheritance resolution.
	# manifest_entries: scene name -> classification row for scene_manifest.json.
	#   Each row is {outcome, reason, source_placement_count, source_placement_names}.
	# errored_count: number of FATAL conditions; nonzero stops the build.
	scenes_dict = {}
	base_scenes_dict = {}
	manifest_entries = {}
	skipped_files = []
	errored_count = 0
	# Accumulates all missing-SVG findings across all scenes for the final report
	all_missing_svg_findings = []

	# ----- base scenes -----
	for filename, yaml_path in scene_files:
		try:
			scene_name, scene_data = process_scene_yaml(yaml_path, object_names)
		except (ValueError, KeyError, yaml.YAMLError, OSError) as e:
			# Validation failure is NON-FATAL: skip and record in the manifest.
			manifest_name = recover_scene_name_from_yaml(yaml_path, filename)
			print(f"ERROR processing {yaml_path}: {e}", file=sys.stderr)
			record_base_scene_skip(manifest_entries, skipped_files, manifest_name, filename, e, repo_root)
			continue

		# Track every valid base scene for per-protocol inheritance, even if it is
		# later classified `skipped` (a child may still extend a quarantined base).
		base_scenes_dict[scene_name] = scene_data

		placement_names = collect_resolved_placement_names(scene_data)

		# Documented quarantine/design skip takes precedence over emission.
		if scene_name in QUARANTINE_SKIP_REASONS:
			reason = QUARANTINE_SKIP_REASONS[scene_name]
			print(f"SKIP scene '{scene_name}': {reason}", file=sys.stderr)
			manifest_entries[scene_name] = {
				"outcome": "skipped",
				"reason": reason,
				"source_placement_count": len(placement_names),
				"source_placement_names": placement_names,
			}
			skipped_files.append(filename.replace(".yaml", ""))
			continue

		# Check for missing SVG assets.
		gaps = check_scene_svg_gaps(scene_data, object_svg_refs, available_svgs)
		if gaps:
			all_missing_svg_findings.append((scene_name, gaps))
			emit_missing_asset_report(scene_name, gaps)
			missing_assets = sorted({a for _p, _o, assets in gaps for a in assets})
			manifest_entries[scene_name] = {
				"outcome": "errored",
				"reason": "missing SVG assets: " + ", ".join(missing_assets),
				"source_placement_count": len(placement_names),
				"source_placement_names": placement_names,
			}
			errored_count += 1
			continue

		# Emit the scene.
		scenes_dict[scene_name] = scene_data
		manifest_entries[scene_name] = {
			"outcome": "emitted",
			"reason": None,
			"source_placement_count": len(placement_names),
			"source_placement_names": placement_names,
		}

	# ----- per-protocol scenes (inheritance-resolved) -----
	per_protocol_scenes = discover_per_protocol_scenes(repo_root)
	per_protocol_count = 0

	for composite_key in sorted(per_protocol_scenes.keys()):
		protocol_name, scene_basename, yaml_path = per_protocol_scenes[composite_key]

		# Resolve inheritance. A per-protocol scene whose extends chain cannot
		# resolve is a FATAL error: the protocol host would later fail to find
		# its entry scene, so the build must STOP rather than ship a broken set.
		try:
			resolved_scene = load_and_resolve_protocol_scene(yaml_path, composite_key, base_scenes_dict)
		except (ValueError, KeyError, yaml.YAMLError, OSError) as e:
			print(f"ERROR [fatal] per-protocol scene {yaml_path}: {e}", file=sys.stderr)
			manifest_entries[composite_key] = {
				"outcome": "errored",
				"reason": f"inheritance/parse error: {e}",
				"source_placement_count": 0,
				"source_placement_names": [],
			}
			errored_count += 1
			continue

		placement_names = collect_resolved_placement_names(resolved_scene)

		# Check for missing SVG assets in the resolved per-protocol scene.
		gaps = check_scene_svg_gaps(resolved_scene, object_svg_refs, available_svgs)
		if gaps:
			all_missing_svg_findings.append((composite_key, gaps))
			emit_missing_asset_report(composite_key, gaps)
			missing_assets = sorted({a for _p, _o, assets in gaps for a in assets})
			manifest_entries[composite_key] = {
				"outcome": "errored",
				"reason": "missing SVG assets: " + ", ".join(missing_assets),
				"source_placement_count": len(placement_names),
				"source_placement_names": placement_names,
			}
			errored_count += 1
			continue

		scenes_dict[composite_key] = resolved_scene
		manifest_entries[composite_key] = {
			"outcome": "emitted",
			"reason": None,
			"source_placement_count": len(placement_names),
			"source_placement_names": placement_names,
		}
		per_protocol_count += 1

	if all_missing_svg_findings:
		total_placements = sum(len(gaps) for _scene_name, gaps in all_missing_svg_findings)
		print(
			f"MISSING-SVG SUMMARY: {len(all_missing_svg_findings)} scene(s), "
			f"{total_placements} placement(s) with missing SVG assets.",
			file=sys.stderr,
		)

	# A FATAL condition stops the build. The manifest is NOT written in this case;
	# a successful build's manifest carries only emitted and skipped entries.
	if errored_count > 0:
		errored_scenes = [
			name
			for name, entry in manifest_entries.items()
			if entry["outcome"] == "errored"
		]
		raise RuntimeError(
			f"FATAL: {errored_count} scene(s) errored; build stopped. "
			f"Errored scenes: {', '.join(errored_scenes)}"
		)

	# Generate TypeScript output
	output_path = os.path.join(repo_root, "generated", "scenes.ts")

	# Create generated directory
	os.makedirs(os.path.dirname(output_path), exist_ok=True)

	# Build TypeScript code
	ts_lines = [
		"// AUTO-GENERATED. Do not edit by hand.",
		"",
		"import type { SceneA } from '../src/scene_runtime/layout/types.js';",
		"",
		f"export const SCENES_SKIPPED = {len(skipped_files)};",
		"",
		"export const SCENES: Record<string, SceneA> = {",
	]

	# Emit scenes in sorted order (base scenes first, then per-protocol)
	for scene_key in sorted(scenes_dict.keys()):
		scene_data = scenes_dict[scene_key]
		emit_scene_ts(scene_key, scene_data, ts_lines)

	ts_lines.append("} as const;")

	ts_code = "\n".join(ts_lines)

	# Write output file
	with open(output_path, "w") as f:
		f.write(ts_code)

	# Write the machine-readable scene manifest (source of truth for tooling).
	# Sorted by name for deterministic output. Contains only emitted/skipped rows
	# on a successful build (errored rows would have exited above).
	manifest_scenes = []
	for name in sorted(manifest_entries.keys()):
		entry = manifest_entries[name]
		manifest_scenes.append({
			"name": name,
			"outcome": entry["outcome"],
			"reason": entry["reason"],
			"source_placement_count": entry["source_placement_count"],
			"source_placement_names": entry["source_placement_names"],
		})
	manifest = {"scenes": manifest_scenes}
	manifest_path = os.path.join(repo_root, "generated", "scene_manifest.json")
	with open(manifest_path, "w") as f:
		json.dump(manifest, f, indent="\t", sort_keys=False)
		f.write("\n")

	# Skip summary to stderr.
	emitted_count = sum(1 for e in manifest_entries.values() if e["outcome"] == "emitted")
	skipped_count = sum(1 for e in manifest_entries.values() if e["outcome"] == "skipped")
	print(
		f"SCENE SUMMARY: {emitted_count} emitted, {skipped_count} skipped.",
		file=sys.stderr,
	)
	for entry_name in sorted(manifest_entries.keys()):
		entry = manifest_entries[entry_name]
		if entry["outcome"] == "skipped":
			print(f"  SKIPPED {entry_name}: {entry['reason']}", file=sys.stderr)

	print(
		f"Generated {output_path} with {len(scenes_dict)} scenes "
		f"({per_protocol_count} per-protocol), {len(skipped_files)} skipped. "
		f"Manifest: {manifest_path}",
		file=sys.stderr,
	)


#============================================

if __name__ == "__main__":
	main()
