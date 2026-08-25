#!/usr/bin/env python3
"""
Codegen for object library from content/objects/**/*.yaml.

Reads object YAML files, validates against closed KINDS enum, layout sizing
fields, and asset references. Emits generated/object_library.ts with typed
ObjectLibrary, AssetSpecs, OBJECT_STATE_SCHEMAS, and OBJECT_SUBPART_STATE_SCHEMAS.

Validation:
- Every object.kind is in the closed KINDS enum.
- Every asset_name in visual_states resolves to an SVG file under assets/**/*.svg.
- Every layout.aspect (if set) is positive.
- Sizing fields (default_width, label_width) are positive numbers.

Output: generated/object_library.ts with:
  OBJECT_LIBRARY       - ObjectDef per object (now includes state_schema, visual_states, subpart_state_schema)
  ASSET_SPECS          - AssetSpec per asset name (aspect ratio, sizing)
  OBJECT_STATE_SCHEMAS - object-level state_fields schema per object (for store validation)
  OBJECT_SUBPART_STATE_SCHEMAS - subpart-level state_fields schema per object (for store validation)
"""

# Standard Library
import os
import sys
import subprocess
from pathlib import Path

# PIP3 modules
import yaml
import lxml.etree

# local repo modules
import pipeline.entity_decode
import pipeline.object_library_geometry
import pipeline.object_library_ts_emit
import pipeline.object_library_visual_states
from validation.svg.asset_registry import SvgAssetRegistryError, build_svg_asset_registry


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

def read_kinds_enum(repo_root: str) -> list:
	"""Read KINDS closed enum from src/scene_runtime/layout/constants.ts."""
	constants_path = os.path.join(
		repo_root,
		"src",
		"scene_runtime",
		"layout",
		"constants.ts",
	)
	with open(constants_path, "r") as f:
		content = f.read()

	# Find the KINDS array: export const KINDS = [
	start = content.find('export const KINDS = [')
	if start == -1:
		raise ValueError("KINDS enum not found in constants.ts")

	start += len('export const KINDS = [')
	end = content.find('] as const;', start)
	if end == -1:
		raise ValueError("KINDS enum closing bracket not found")

	kinds_section = content[start:end]
	# Extract quoted strings
	kinds = []
	for line in kinds_section.split('\n'):
		line = line.strip()
		if not line or line.startswith('//'):
			continue
		# Extract quoted string (may have trailing comma)
		if '"' in line:
			first_quote = line.find('"')
			last_quote = line.rfind('"')
			if first_quote != -1 and last_quote != -1 and first_quote < last_quote:
				kind = line[first_quote + 1:last_quote]
				if kind:
					kinds.append(kind)

	if not kinds:
		raise ValueError("Failed to parse KINDS enum")

	return kinds


#============================================

def collect_svg_files(repo_root: str) -> dict:
	"""
	Collect every SVG through the authoritative recursive logical-name registry.
	Returns {asset_name: absolute_path} and rejects duplicate basenames rather
	than allowing filesystem walk order to choose one source silently.
	"""
	try:
		registry = build_svg_asset_registry(Path(repo_root) / "assets")
	except SvgAssetRegistryError as exc:
		raise ValueError(str(exc)) from exc
	return {entry.asset_name: str(entry.source_path) for entry in registry.entries}


#============================================

def get_svg_aspect(svg_path: str) -> float:
	"""
	Extract aspect ratio from SVG viewBox.
	Returns width/height ratio. Fails loud if viewBox is missing or invalid.
	"""
	# Hardened lxml parser: resolve_entities=False blocks XXE entity expansion,
	# no_network=True blocks external DTD/entity network fetches. First-party
	# repo asset, but the parser stays hardened regardless of source trust.
	parser = lxml.etree.XMLParser(resolve_entities=False, no_network=True)
	tree = lxml.etree.parse(svg_path, parser)
	root = tree.getroot()

	viewbox = root.get("viewBox")
	if not viewbox:
		raise ValueError(f"SVG missing viewBox: {svg_path}")

	parts = viewbox.split()
	if len(parts) != 4:
		raise ValueError(f"Invalid viewBox format: {svg_path}")

	try:
		x, y, width, height = map(float, parts)
	except ValueError:
		raise ValueError(f"Non-numeric viewBox values: {svg_path}")

	if width <= 0 or height <= 0:
		raise ValueError(f"Invalid viewBox dimensions: {svg_path}")

	return width / height


#============================================

def parse_state_fields(data: dict, yaml_path: str) -> tuple:
	"""
	Parse state_fields list into (object_level, subpart_level) dicts.
	Keys are field_name. Each value is the field mapping from YAML.
	Returns ({field_name: field_def}, {field_name: field_def}).
	"""
	raw_fields = data.get("state_fields", [])
	object_fields = {}
	subpart_fields = {}

	for field in raw_fields:
		field_name = field["field_name"]
		# applies_to defaults to "object"
		applies_to = field.get("applies_to", "object")
		if applies_to == "subpart":
			subpart_fields[field_name] = field
		else:
			object_fields[field_name] = field

	# Also pick up subpart_state_fields from structure block if present
	structure = data.get("structure", {})
	if structure:
		for field in structure.get("subpart_state_fields", []):
			field_name = field["field_name"]
			subpart_fields[field_name] = field

	return object_fields, subpart_fields


#============================================

def process_object_yaml(
	yaml_path: str,
	svg_files: dict,
	kinds_enum: list,
) -> tuple:
	"""
	Load and validate a single object YAML.
	Returns (object_def, asset_spec) or raises on validation failure.
	"""
	# Log file path before opening
	print(f"processing {yaml_path}", file=sys.stderr)

	with open(yaml_path, "r") as f:
		data = yaml.safe_load(f)

	if not data:
		raise ValueError(f"Empty YAML: {yaml_path}")
	# Normalize every authored string value at the parsed-YAML boundary. Object
	# labels, enum defaults/allowed values, descriptions, formulas, and visual
	# cases must all use the same Unicode runtime vocabulary as protocol codegen.
	data = pipeline.entity_decode.decode_entity_values(data)

	# Validate required identity fields
	object_name = data["object_name"]
	kind = data["kind"]
	label = data["label"]

	if kind not in kinds_enum:
		raise ValueError(
			f"Invalid kind '{kind}' not in KINDS enum: {yaml_path}"
		)

	# Parse state fields (object-level vs subpart-level)
	object_state_fields, subpart_state_fields = parse_state_fields(data, yaml_path)

	# Parse visual_states into structured form
	visual_states = pipeline.object_library_visual_states.parse_visual_states(data, yaml_path)

	# Extract primary asset_name (for layout engine asset lookup)
	asset_name = pipeline.object_library_visual_states.extract_primary_asset(visual_states, data)
	if not asset_name:
		raise ValueError(f"Missing asset_name: {yaml_path}")

	# Resolve SVG file - required for the primary asset
	if asset_name not in svg_files:
		raise ValueError(
			f"Asset '{asset_name}' not found in SVG registry: {yaml_path}"
		)

	svg_path = svg_files[asset_name]

	# Validate capabilities
	capabilities = data.get("capabilities", [])
	if not isinstance(capabilities, list):
		raise ValueError(f"capabilities must be a list: {yaml_path}")

	# Get layout hints
	layout = data["layout"]
	if not isinstance(layout, dict):
		raise ValueError(f"layout must be a dict: {yaml_path}")

	default_width = float(layout["default_width"])
	if default_width <= 0:
		raise ValueError(
			f"layout.default_width must be positive: {yaml_path}"
		)

	label_width = float(layout["label_width"])
	if label_width <= 0:
		raise ValueError(f"layout.label_width must be positive: {yaml_path}")

	# Optional: custom aspect ratio override
	aspect_override = layout.get("aspect")
	if aspect_override is not None:
		aspect = float(aspect_override)
		if aspect <= 0:
			raise ValueError(f"layout.aspect must be positive: {yaml_path}")
	else:
		# Derive from SVG viewBox
		aspect = get_svg_aspect(svg_path)

	# Build layout dict
	layout_dict = {
		"default_width": default_width,
		"label_width": label_width,
	}
	# Preserve other layout fields (anchor_y, anchor_y_offset, width_scale, etc.)
	for key in [
		"anchor_y",
		"anchor_y_offset",
		"width_scale",
		"display_width_cm",
		"fudge",
	]:
		if key in layout:
			layout_dict[key] = layout[key]

	# Derive recorded subpart geometry once per object def, never per scene or
	# placement. It covers only the internal regions of a structured object.
	structure = data.get("structure", {})
	subpart_geometry, view_box = pipeline.object_library_geometry.derive_grid_geometry(object_name, structure)
	# The source's legacy SVG case table still selected the primary asset above.
	# Structured legacy material pairs lower into the typed render-effect contract
	# only after their internal target geometry is known.
	visual_states = pipeline.object_library_visual_states.lower_legacy_subpart_material_effects(
		visual_states,
		yaml_path,
		subpart_geometry is not None,
	)

	# Declared subpart vocabulary for structured objects: every subpart instance
	# name (tube_A, lane_1, A1..H12) plus the flattened subpart_groups map
	# (all_wells, row_A, col_1, ...). The runtime validates authored
	# "<object>.<subpart>" targets against these and fans a group write out to
	# its members. Empty for non-structured objects.
	subpart_names = pipeline.object_library_geometry.derive_subpart_names(object_name, structure)
	subpart_groups = pipeline.object_library_geometry.derive_subpart_groups(object_name, structure, subpart_names)

	# Build full object definition including state schema and visual_states
	object_def = {
		"object_name": object_name,
		"kind": kind,
		"label": label,
		"asset": asset_name,
		"capabilities": capabilities,
		"layout": layout_dict,
		"object_state_fields": object_state_fields,
		"subpart_state_fields": subpart_state_fields,
		"visual_states": visual_states,
		"subpart_geometry": subpart_geometry,
		"view_box": view_box,
		"subparts": subpart_names,
		"subpart_groups": subpart_groups,
	}

	# Build asset spec
	asset_spec = {
		"default_width": default_width,
		"label_width": label_width,
		"aspect": aspect,
	}

	return object_def, asset_spec


#============================================

def main() -> None:
	"""Main entry point for the object-library generator."""
	repo_root = get_repo_root()

	# Read KINDS enum
	kinds_enum = read_kinds_enum(repo_root)

	# Collect SVG files
	svg_files = collect_svg_files(repo_root)

	# Find all object YAML files
	objects_dir = os.path.join(repo_root, "content", "objects")
	if not os.path.isdir(objects_dir):
		raise ValueError(f"Objects directory not found: {objects_dir}")

	object_files = []
	for root, dirs, files in os.walk(objects_dir):
		for file in files:
			if file.endswith(".yaml"):
				abs_path = os.path.join(root, file)
				object_files.append(abs_path)

	object_files.sort()

	# Process each curriculum object YAML (strict hard-fail). No try/except:
	# a malformed curriculum object is a real build error and must surface
	# loudly (fix the design, not the symptom). process_object_yaml raises
	# ValueError on validation failure and KeyError on a missing required
	# field; both should abort the build with a full traceback naming the file.
	object_library = {}
	asset_specs = {}

	for yaml_path in object_files:
		obj_def, asset_spec = process_object_yaml(
			yaml_path,
			svg_files,
			kinds_enum,
		)
		object_name = obj_def["object_name"]
		object_library[object_name] = obj_def
		asset_specs[obj_def["asset"]] = asset_spec

	# Generate TypeScript output
	output_path = os.path.join(repo_root, "generated", "object_library.ts")

	# Create generated directory if needed
	os.makedirs(os.path.dirname(output_path), exist_ok=True)

	# Build TypeScript code
	ts_lines = [
		"// AUTO-GENERATED. Do not edit by hand.",
		"",
		"import type {",
		"\tAssetSpecs,",
		"\tObjectLibrary,",
		"\tObjectStateSchemas,",
		"\tObjectSubpartStateSchemas,",
		"} from '../src/scene_runtime/layout/types.js';",
		"",
		"export const OBJECT_LIBRARY: ObjectLibrary = {",
	]

	for object_name in sorted(object_library.keys()):
		obj = object_library[object_name]
		ts_lines.extend(pipeline.object_library_ts_emit.emit_object_def_ts(object_name, obj))

	ts_lines.append("};")
	ts_lines.append("")
	ts_lines.append("export const ASSET_SPECS: AssetSpecs = {")

	for asset_name in sorted(asset_specs.keys()):
		spec = asset_specs[asset_name]
		ts_lines.append(f"\t{repr(asset_name)}: " + "{")
		ts_lines.append(f"\t\tdefault_width: {spec['default_width']},")
		ts_lines.append(f"\t\tlabel_width: {spec['label_width']},")
		ts_lines.append(f"\t\taspect: {spec['aspect']},")
		ts_lines.append("\t},")

	ts_lines.append("};")
	ts_lines.append("")

	# Build OBJECT_STATE_SCHEMAS (object-level fields only)
	object_state_registry = {
		name: obj["object_state_fields"]
		for name, obj in object_library.items()
	}
	ts_lines.extend(
		pipeline.object_library_ts_emit.emit_schema_registry_ts(
			object_state_registry,
			"OBJECT_STATE_SCHEMAS",
			"ObjectStateSchemas",
		)
	)
	ts_lines.append("")

	# Build OBJECT_SUBPART_STATE_SCHEMAS (subpart-level fields only)
	subpart_state_registry = {
		name: obj["subpart_state_fields"]
		for name, obj in object_library.items()
	}
	ts_lines.extend(
		pipeline.object_library_ts_emit.emit_schema_registry_ts(
			subpart_state_registry,
			"OBJECT_SUBPART_STATE_SCHEMAS",
			"ObjectSubpartStateSchemas",
		)
	)

	ts_code = "\n".join(ts_lines)

	# Write output file
	with open(output_path, "w") as f:
		f.write(ts_code)

	print(
		f"Generated {output_path} with {len(object_library)} objects"
		f" and {len(asset_specs)} asset specs",
		file=sys.stderr,
	)


#============================================

if __name__ == "__main__":
	main()
