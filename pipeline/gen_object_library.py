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
import math
import re

# PIP3 modules
import yaml
import lxml.etree

# local repo modules
import pipeline.entity_decode


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
	Collect all SVG files under assets/**/*.svg.
	Returns {asset_name: absolute_path}.
	"""
	assets_dir = os.path.join(repo_root, "assets")
	svg_files = {}

	for root, dirs, files in os.walk(assets_dir):
		for file in files:
			if file.endswith(".svg"):
				abs_path = os.path.join(root, file)
				# Asset name is filename without .svg
				asset_name = file[:-4]
				svg_files[asset_name] = abs_path

	return svg_files


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

# Recorded PATH-B geometry parameters for structured grid objects, keyed by
# object_name. Base SVG art does not always expose a convenient semantic shape
# element, so this is the one generated-geometry calibration seam. It is not
# authored YAML: a structured object's exterior remains layout-managed, while
# these regions describe only its declared internal subparts.
#
# Geometry may be a regular circle grid (the well plate) or a regular rect
# grid (the eight visible tube interiors). The derivation remains generic:
# object-specific evidence lives in this calibration table, not in emitted
# runtime behavior.
#
# well_plate_96 (asset 96well_pcr_plate.svg, viewBox 0 0 393.3275 278.5243):
#   origin_x/origin_y are the center of well A1 (top-left), measured directly
#     from the inline fill-disc path (45.010, 49.260).
#   x_spacing/y_spacing are the uniform center-to-center pitch, equal to the
#     column-label glyph pitch (28.347) and the row-disc pitch (28.346); the
#     grid is square. col 12 center = 45.010 + 11*28.347 = 356.83 and
#     row H center = 49.260 + 7*28.347 = 247.69 both land on the measured wells.
#   radius is the rendered disc radius (inner fill 10.57, outer ring 12.68);
#     11.0 sits inside the gray ring so the tint disc reads as the well.
RECORDED_SUBPART_GRIDS = {
	"well_plate_96": {
		"origin_x": 45.010,
		"origin_y": 49.260,
		"row_dx": 0.0,
		"row_dy": 28.347,
		"col_dx": 28.347,
		"col_dy": 0.0,
		"radius": 11.0,
		"view_box": {
			"min_x": 0.0,
			"min_y": 0.0,
			"width": 393.3275,
			"height": 278.5243,
		},
	},
	# dilution_tube_rack_8 (asset dilution_tube_rack.svg, viewBox 0 0 80 50):
	# each front-row tube body spans x=5..9, x=14..18, ... x=68..72. The
	# material region deliberately stays in the straight body (y=10..28),
	# avoiding the cap and tapered tip while still reading as liquid in the
	# protocol-addressed tube.
	"dilution_tube_rack_8": {
		"shape": "rect",
		"origin_x": 5.0,
		"origin_y": 10.0,
		# The YAML's eight declared row entries are drawn as a horizontal row in
		# this asset. A row/column basis keeps that recorded orientation explicit.
		"row_dx": 9.0,
		"row_dy": 0.0,
		"col_dx": 0.0,
		"col_dy": 0.0,
		"width": 4.0,
		"height": 18.0,
		"view_box": {
			"min_x": 0.0,
			"min_y": 0.0,
			"width": 80.0,
			"height": 50.0,
		},
	},
	# gel_cassette (asset gel_cassette.svg, viewBox 0 0 214 308): the ten
	# lanes are a horizontal row across the resolving gel. Each 16 x 228 rect
	# stays inside its visible lane and leaves a small gutter for the lane walls.
	"gel_cassette": {
		"shape": "rect",
		"origin_x": 19.0,
		"origin_y": 57.0,
		"row_dx": 0.0,
		"row_dy": 0.0,
		"col_dx": 18.0,
		"col_dy": 0.0,
		"width": 16.0,
		"height": 228.0,
		"view_box": {
			"min_x": 0.0,
			"min_y": 0.0,
			"width": 214.0,
			"height": 308.0,
		},
	},
	# hemocytometer_slide (asset hemocytometer_slide.svg, viewBox 0 0 400 220):
	# the central ruled mixing chamber and the right-side loading chamber are
	# physically distinct, non-grid regions.  Record their real liquid areas so
	# both the visual tint and exact click surface match the depicted hardware.
	"hemocytometer_slide": {
		"explicit_geometry": {
			"diamond": {"shape": "rect", "x": 153.0, "y": 82.0, "w": 94.0, "h": 54.0},
			"semicircle": {"shape": "rect", "x": 282.0, "y": 82.0, "w": 55.0, "h": 54.0},
		},
		"view_box": {
			"min_x": 0.0,
			"min_y": 0.0,
			"width": 400.0,
			"height": 220.0,
		},
	},
	# microtube_rack_8 (asset microtube_rack_8.svg, viewBox 0 0 320 210):
	# measured circular tube interiors, row-major to match slot_A1..slot_B4.
	"microtube_rack_8": {
		"origin_x": 67.0,
		"origin_y": 67.0,
		"row_dx": 0.0,
		"row_dy": 58.0,
		"col_dx": 60.0,
		"col_dy": 0.0,
		"radius": 20.0,
		"view_box": {
			"min_x": 0.0,
			"min_y": 0.0,
			"width": 320.0,
			"height": 210.0,
		},
	},
}


#============================================

def row_letter(row_index: int) -> str:
	"""Return the row letter for a 0-based row index (0 -> 'A', top row)."""
	letter = chr(ord("A") + row_index)
	return letter


#============================================

def derive_grid_geometry(object_name: str, structure: dict) -> tuple:
	"""
	Derive a typed SubpartGeometryMap from recorded PATH-B grid parameters.

	Reads rows/cols/name_pattern from structure and the recorded calibration for
	the object. Computes one circle or rect per declared subpart, ordered by the
	same row-major expansion as derive_subpart_names. Returns
	(geometry_map, view_box) or (None, None) when no geometry is recorded.
	"""
	grid = RECORDED_SUBPART_GRIDS.get(object_name)
	if grid is None:
		return None, None

	layout = structure.get("layout")
	if layout != "grid":
		raise ValueError(
			f"recorded subpart geometry for {object_name} but structure.layout"
			f" is {layout!r}, expected 'grid'"
		)

	cols = int(structure["cols"])
	# Named instrument chambers use measured geometry rather than a uniform pitch.
	# They still emit through the same declaration-owned subpart rendering path.
	if "explicit_geometry" in grid:
		subpart_names = derive_subpart_names(object_name, structure)
		explicit_geometry = grid["explicit_geometry"]
		if set(explicit_geometry) != set(subpart_names):
			raise ValueError(
				f"recorded explicit subpart geometry for {object_name} must match "
				"the declared subpart vocabulary"
			)
		return explicit_geometry, grid["view_box"]
	origin_x = grid["origin_x"]
	origin_y = grid["origin_y"]
	row_dx = grid["row_dx"]
	row_dy = grid["row_dy"]
	col_dx = grid["col_dx"]
	col_dy = grid["col_dy"]
	shape = grid.get("shape", "circle")
	if shape not in ("circle", "rect"):
		raise ValueError(
			f"recorded subpart geometry for {object_name} has unsupported "
			f"shape {shape!r}"
		)

	# Preserve declared row-major order for all structured grids. It matters for
	# both plate wells and tube racks: sorting strings would make A10 precede A2.
	subpart_names = derive_subpart_names(object_name, structure)
	geometry_map = {}
	for index, subpart_name in enumerate(subpart_names):
		row = index // cols
		col = index % cols
		cx = origin_x + row * row_dx + col * col_dx
		cy = origin_y + row * row_dy + col * col_dy
		if shape == "circle":
			geometry_map[subpart_name] = {
				"shape": "circle",
				"cx": round(cx, 4),
				"cy": round(cy, 4),
				"r": round(grid["radius"], 4),
			}
		else:
			geometry_map[subpart_name] = {
				"shape": "rect",
				"x": round(cx, 4),
				"y": round(cy, 4),
				"w": round(grid["width"], 4),
				"h": round(grid["height"], 4),
			}

	view_box = grid["view_box"]
	return geometry_map, view_box


#============================================

def derive_subpart_names(object_name: str, structure: dict) -> list:
	"""
	Enumerate every declared subpart name from a grid structure block.

	Reads rows/cols and name_pattern from the object's structure block and
	expands the pattern row-major (top-left first) into the full ordered list of
	subpart instance names. Supports the pattern tokens the corpus uses:
	{row_letter} (0 -> 'A'), {row} (1-based row number), {col} (1-based column
	number). Returns [] for a non-grid or structure-less object.

	The list is the complete declared subpart vocabulary the runtime validates
	authored "<object>.<subpart>" targets against; it is not geometry.
	"""
	if not structure:
		return []
	layout = structure.get("layout")
	if layout != "grid":
		return []
	rows = int(structure["rows"])
	cols = int(structure["cols"])
	explicit_names = structure.get("subpart_names")
	if explicit_names is not None:
		if not isinstance(explicit_names, list) or len(explicit_names) != rows * cols:
			raise ValueError(
				f"structure.subpart_names for {object_name} must name exactly "
				f"{rows * cols} grid subparts"
			)
		if not all(isinstance(name, str) and name for name in explicit_names):
			raise ValueError(
				f"structure.subpart_names for {object_name} must contain non-empty strings"
			)
		if len(set(explicit_names)) != len(explicit_names):
			raise ValueError(f"structure.subpart_names for {object_name} must be unique")
		return explicit_names
	name_pattern = structure["name_pattern"]
	names = []
	# Row-major expansion so the emitted order is stable and reads top-left first.
	for row in range(rows):
		for col in range(cols):
			name = name_pattern
			name = name.replace("{row_letter}", row_letter(row))
			name = name.replace("{row}", str(row + 1))
			name = name.replace("{col}", str(col + 1))
			names.append(name)
	return names


#============================================

def derive_subpart_groups(
	object_name: str,
	structure: dict,
	subpart_names: list,
) -> dict:
	"""
	Flatten structure.subpart_groups into one {group_name: [members]} map.

	Every group_kind block (rows, columns, plate_region, blocks, ...) is merged
	into a single flat map keyed by group name (row_A, col_1, all_wells,
	block_A_1_6, ...). Group names must be unique across kinds and every member
	must be a declared subpart, so a group write always fans out to real
	subparts. Returns {} when the structure declares no groups.
	"""
	groups = structure.get("subpart_groups", {})
	if not groups:
		return {}
	declared = set(subpart_names)
	result = {}
	for group_kind_key in sorted(groups.keys()):
		group_def = groups[group_kind_key]
		for member in group_def.get("members", []):
			name = member["name"]
			if name in result:
				raise ValueError(
					f"duplicate subpart_group name {name!r} on object"
					f" {object_name!r}"
				)
			if name in declared:
				raise ValueError(
					f"subpart_group name {name!r} on object {object_name!r}"
					f" collides with a declared subpart name"
				)
			contains = list(member["contains"])
			for well in contains:
				if well not in declared:
					raise ValueError(
						f"subpart_group {name!r} on object {object_name!r}"
						f" names undeclared subpart {well!r}"
					)
			result[name] = contains
	return result


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

# Closed render-effect vocabulary (MATERIAL_CONVENTION.md D12). A material-driven
# visual state declares one of these effects plus a target instead of a
# kind/cases shape. Kept in sync with RenderEffect/RenderEffectTarget in
# src/scene_runtime/layout/types.ts.
RENDER_EFFECTS = ("material_tint", "fill_height")
RENDER_TARGETS = ("subpart_geometry", "anchor_liquid_bounds", "anchor_liquid_clip")
FILL_HEIGHT_FORMULA = re.compile(
	r"fill_height\(state\((?P<field>[A-Za-z_][A-Za-z0-9_]*)\), "
	r"(?P<capacity_key>capacity_(?:ul|ml))=(?P<capacity>"
	r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)\)"
)


#============================================

def parse_visual_states(data: dict, yaml_path: str) -> dict:
	"""
	Parse visual_states mapping from YAML into a structured Python dict.

	Two shapes are accepted per field:
	- kind-based (svg/overlay/composite) with cases/formula, the existing form;
	- render-effect-based (MATERIAL_CONVENTION.md D12) with render_effect +
	  target, the declarative material form, which omits kind.
	Returns {field_name: {applies_to, kind?, cases?, formula?, render_effect?,
	target?, clip?, capacity_ul?, capacity_ml?}}.
	"""
	raw_vs = data.get("visual_states", {})
	if not raw_vs:
		return {}

	result = {}
	for field_name, vs_def in raw_vs.items():
		if not isinstance(vs_def, dict):
			raise ValueError(
				f"visual_states.{field_name} must be a mapping: {yaml_path}"
			)
		applies_to = vs_def.get("applies_to", "object")
		entry = {"applies_to": applies_to}

		# Render-effect form: declarative material_tint/fill_height. The field
		# names an effect + target; it carries no kind/cases.
		if "render_effect" in vs_def:
			render_effect = vs_def["render_effect"]
			if render_effect not in RENDER_EFFECTS:
				raise ValueError(
					f"visual_states.{field_name}.render_effect"
					f" '{render_effect}' not in {RENDER_EFFECTS}: {yaml_path}"
				)
			target = vs_def["target"]
			if target not in RENDER_TARGETS:
				raise ValueError(
					f"visual_states.{field_name}.target"
					f" '{target}' not in {RENDER_TARGETS}: {yaml_path}"
				)
			entry["render_effect"] = render_effect
			entry["target"] = target
			# Optional anchor clip + capacity for fill_height; pass through if set.
			if "clip" in vs_def:
				clip = vs_def["clip"]
				if clip not in RENDER_TARGETS:
					raise ValueError(
						f"visual_states.{field_name}.clip"
						f" '{clip}' not in {RENDER_TARGETS}: {yaml_path}"
					)
				entry["clip"] = clip
			if "capacity_ul" in vs_def:
				entry["capacity_ul"] = vs_def["capacity_ul"]
			if "capacity_ml" in vs_def:
				entry["capacity_ml"] = vs_def["capacity_ml"]
			if render_effect == "fill_height":
				capacities = [key for key in ("capacity_ul", "capacity_ml") if key in entry]
				if len(capacities) != 1:
					raise ValueError(
						f"visual_states.{field_name}.fill_height must declare exactly one "
						f"of capacity_ul/capacity_ml: {yaml_path}"
					)
				capacity = entry[capacities[0]]
				if not isinstance(capacity, (int, float)) or isinstance(capacity, bool) or capacity <= 0:
					raise ValueError(
						f"visual_states.{field_name}.{capacities[0]} must be a positive number: "
						f"{yaml_path}"
					)
			result[field_name] = entry
			continue

		# Kind-based form: svg/overlay/composite with cases/formula.
		entry["kind"] = vs_def["kind"]

		if "cases" in vs_def:
			entry["cases"] = vs_def["cases"]

		if "formula" in vs_def:
			entry["formula"] = vs_def["formula"]

		result[field_name] = entry

	return result


#============================================

def parse_fill_height_formula(formula: object, yaml_path: str, field_name: str) -> tuple:
	"""Parse one closed fill-height formula without accepting near matches."""
	if not isinstance(formula, str):
		raise ValueError(
			f"visual_states.{field_name}.formula must be a string: {yaml_path}"
		)
	match = FILL_HEIGHT_FORMULA.fullmatch(formula)
	if match is None:
		raise ValueError(
			f"visual_states.{field_name}.formula must be an exact fill_height "
			f"formula with capacity_ul or capacity_ml: {yaml_path}"
		)
	capacity = float(match.group("capacity"))
	if not math.isfinite(capacity) or capacity <= 0:
		raise ValueError(
			f"visual_states.{field_name}.formula capacity must be finite and positive: "
			f"{yaml_path}"
		)
	return match.group("field"), match.group("capacity_key"), capacity


#============================================

def paired_identity_field(volume_field: str) -> str | None:
	"""Return the runtime's conventional shared-prefix material identity field."""
	if not volume_field.endswith("_volume"):
		return None
	base = volume_field[:-len("_volume")]
	if base == "material":
		return "material_name"
	if base.endswith("_material"):
		return base + "_name"
	return base + "_material_name"


#============================================

def single_case_asset(
	identity: dict,
	yaml_path: str,
	field_name: str,
) -> str:
	"""Require a legacy identity table to select one unambiguous base asset."""
	cases = identity.get("cases")
	if not isinstance(cases, list) or not cases:
		raise ValueError(
			f"visual_states.{field_name}.cases must be a non-empty list: {yaml_path}"
		)
	assets = []
	seen_when = set()
	for case in cases:
		if not isinstance(case, dict) or "when" not in case:
			raise ValueError(
				f"visual_states.{field_name}.cases has an invalid case: {yaml_path}"
			)
		when = case["when"]
		if when in seen_when:
			raise ValueError(
				f"visual_states.{field_name}.cases repeats {when!r}: {yaml_path}"
			)
		seen_when.add(when)
		output = case.get("output")
		if not isinstance(output, dict) or set(output) != {"asset_name"}:
			raise ValueError(
				f"visual_states.{field_name}.cases must each select one asset_name: "
				f"{yaml_path}"
			)
		asset_name = output["asset_name"]
		if not isinstance(asset_name, str) or not asset_name:
			raise ValueError(
				f"visual_states.{field_name}.cases has an invalid asset_name: {yaml_path}"
			)
		assets.append(asset_name)
	if len(set(assets)) != 1:
		raise ValueError(
			f"visual_states.{field_name}.cases must use one base asset for "
			f"a paired fill-height material: {yaml_path}"
		)
	return assets[0]


#============================================

def lower_legacy_subpart_material_effects(
	visual_states: dict,
	yaml_path: str,
	has_subpart_geometry: bool,
) -> dict:
	"""
	Lower paired legacy subpart SVG/formula declarations to render effects.

	The source schema remains the compatibility surface. Once a structured object
	has generated subpart regions, an eligible pair is recognized only by its
	declaration: a subpart composite fill_height formula and the matching
	shared-prefix subpart SVG identity field. No object name, material spelling,
	or subpart spelling participates in the emitted behavior.
	"""
	if not has_subpart_geometry:
		return visual_states

	lowered = dict(visual_states)
	for amount_field, amount in visual_states.items():
		if amount.get("applies_to") != "subpart" or amount.get("kind") != "composite":
			continue
		formula = amount.get("formula")
		if not isinstance(formula, str) or not formula.startswith("fill_height("):
			continue

		driver_field, capacity_key, capacity = parse_fill_height_formula(
			formula, yaml_path, amount_field
		)
		if driver_field != amount_field:
			raise ValueError(
				f"visual_states.{amount_field}.formula must drive its own field, "
				f"not {driver_field!r}: {yaml_path}"
			)
		identity_field = paired_identity_field(driver_field)
		if identity_field is None:
			raise ValueError(
				f"visual_states.{amount_field}.formula field {driver_field!r} has no "
				f"shared-prefix identity pairing: {yaml_path}"
			)
		identity = visual_states.get(identity_field)
		if identity is None:
			raise ValueError(
				f"visual_states.{amount_field} needs paired identity "
				f"visual_states.{identity_field}: {yaml_path}"
			)
		if identity.get("applies_to") != "subpart" or identity.get("kind") != "svg":
			raise ValueError(
				f"visual_states.{identity_field} must be a subpart svg identity "
				f"for visual_states.{amount_field}: {yaml_path}"
			)
		# Validate the original table before replacing it. extract_primary_asset
		# runs on the authored table, preserving base-asset selection compatibility.
		single_case_asset(identity, yaml_path, identity_field)
		lowered[identity_field] = {
			"applies_to": "subpart",
			"render_effect": "material_tint",
			"target": "subpart_geometry",
		}
		lowered[amount_field] = {
			"applies_to": "subpart",
			"render_effect": "fill_height",
			"target": "subpart_geometry",
			capacity_key: capacity,
		}
	return lowered


#============================================

def extract_primary_asset(visual_states: dict, data: dict) -> str | None:
	"""
	Extract the primary asset_name from the object.
	Tries explicit 'asset' field first, then scans visual_states cases.
	Returns asset_name string or None if not found.
	"""
	# Explicit asset override field
	asset_name = data.get("asset")
	if asset_name:
		return asset_name

	# Scan visual_states for the first svg case output
	for field_name, vs_def in visual_states.items():
		if vs_def.get("kind") == "svg":
			for case in vs_def.get("cases", []):
				output = case.get("output", {})
				if isinstance(output, dict) and "asset_name" in output:
					return output["asset_name"]

	return None


#============================================

def emit_state_field_ts(field: dict, indent: str) -> list:
	"""
	Emit TypeScript lines for a single StateFieldDef.
	Returns list of strings (without trailing newline per line).
	"""
	lines = []
	lines.append(indent + "{")
	lines.append(f"{indent}\tfield_name: {repr(field['field_name'])},")
	lines.append(f"{indent}\ttype: {repr(field['type'])},")

	default_val = field["default"]
	if isinstance(default_val, bool):
		lines.append(f"{indent}\tdefault: {str(default_val).lower()},")
	elif isinstance(default_val, str):
		lines.append(f"{indent}\tdefault: {repr(default_val)},")
	else:
		lines.append(f"{indent}\tdefault: {default_val},")

	applies_to = field.get("applies_to", "object")
	lines.append(f"{indent}\tapplies_to: {repr(applies_to)},")

	# enum-specific
	if field["type"] == "enum" and "allowed" in field:
		allowed = field["allowed"]
		allowed_str = "[" + ", ".join(repr(v) for v in allowed) + "]"
		lines.append(f"{indent}\tallowed: {allowed_str},")

	# numeric-specific
	for key in ["unit", "min", "max", "step"]:
		if key in field:
			val = field[key]
			if isinstance(val, str):
				lines.append(f"{indent}\t{key}: {repr(val)},")
			else:
				lines.append(f"{indent}\t{key}: {val},")

	if "description" in field:
		lines.append(f"{indent}\tdescription: {repr(field['description'])},")

	lines.append(indent + "}")
	return lines


#============================================

def emit_visual_state_case_ts(case: dict, indent: str) -> list:
	"""Emit TypeScript lines for one VisualStateCase."""
	lines = []
	lines.append(indent + "{")

	when_val = case["when"]
	if isinstance(when_val, bool):
		lines.append(f"{indent}\twhen: {str(when_val).lower()},")
	elif isinstance(when_val, str):
		lines.append(f"{indent}\twhen: {repr(when_val)},")
	else:
		lines.append(f"{indent}\twhen: {when_val},")

	# Emit output
	output = case["output"]
	lines.extend(emit_visual_state_output_ts(output, indent + "\t", key="output"))

	lines.append(indent + "},")
	return lines


#============================================

def emit_visual_state_output_ts(output: dict, indent: str, key: str = "output") -> list:
	"""Emit TypeScript lines for a VisualStateOutput mapping."""
	lines = []
	if "asset_name" in output:
		lines.append(f"{indent}{key}: {{ asset_name: {repr(output['asset_name'])} }},")
	elif "overlay_name" in output:
		lines.append(f"{indent}{key}: {{ overlay_name: {repr(output['overlay_name'])} }},")
	elif "composite" in output:
		lines.append(f"{indent}{key}: {{ composite: [")
		for sub_output in output["composite"]:
			# Inline emit of each composite sub-output as an object literal
			lines.append(indent + "\t\t{")
			if "asset_name" in sub_output:
				lines.append(f"{indent}\t\t\tasset_name: {repr(sub_output['asset_name'])},")
			elif "overlay_name" in sub_output:
				lines.append(f"{indent}\t\t\toverlay_name: {repr(sub_output['overlay_name'])},")
			lines.append(indent + "\t\t},")
		lines.append(indent + "\t] },")
	else:
		# Empty composite (kind: composite with no cases)
		lines.append(f"{indent}{key}: {{ composite: [] }},")
	return lines


#============================================

def emit_visual_states_ts(visual_states: dict, indent: str) -> list:
	"""Emit TypeScript lines for the visual_states block on an ObjectDef."""
	lines = []
	lines.append(f"{indent}visual_states: " + "{")
	for field_name, vs_def in sorted(visual_states.items()):
		lines.append(f"{indent}\t{repr(field_name)}: " + "{")
		# kind is present only on the svg/overlay/composite form. The
		# render-effect form omits it.
		if "kind" in vs_def:
			lines.append(f"{indent}\t\tkind: {repr(vs_def['kind'])},")
		lines.append(f"{indent}\t\tapplies_to: {repr(vs_def['applies_to'])},")
		if "cases" in vs_def:
			lines.append(f"{indent}\t\tcases: [")
			for case in vs_def["cases"]:
				case_lines = emit_visual_state_case_ts(case, indent + "\t\t\t")
				lines.extend(case_lines)
			lines.append(f"{indent}\t\t],")
		if "formula" in vs_def:
			lines.append(f"{indent}\t\tformula: {repr(vs_def['formula'])},")
		# Render-effect declarative form (material_tint / fill_height).
		if "render_effect" in vs_def:
			lines.append(f"{indent}\t\trender_effect: {repr(vs_def['render_effect'])},")
			lines.append(f"{indent}\t\ttarget: {repr(vs_def['target'])},")
			if "clip" in vs_def:
				lines.append(f"{indent}\t\tclip: {repr(vs_def['clip'])},")
			if "capacity_ul" in vs_def:
				lines.append(f"{indent}\t\tcapacity_ul: {vs_def['capacity_ul']},")
			if "capacity_ml" in vs_def:
				lines.append(f"{indent}\t\tcapacity_ml: {vs_def['capacity_ml']},")
		lines.append(f"{indent}\t" + "},")
	lines.append(f"{indent}" + "},")
	return lines


#============================================

def emit_state_schema_ts(state_fields: dict, indent: str) -> list:
	"""Emit TypeScript lines for a state schema block (object or subpart level)."""
	lines = []
	lines.append("{")
	for field_name in sorted(state_fields.keys()):
		field = state_fields[field_name]
		field_lines = emit_state_field_ts(field, indent + "\t")
		lines.append(f"{indent}\t{repr(field_name)}: " + field_lines[0].strip())
		for fl in field_lines[1:-1]:
			lines.append(fl)
		lines.append(indent + "\t" + field_lines[-1].strip() + ",")
	lines.append(indent + "}")
	return lines


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

	# Validate required identity fields
	object_name = data["object_name"]
	kind = data["kind"]
	# Decode authored HTML entities (e.g. &micro;) to their Unicode glyph before
	# emission, so generated/object_library.ts carries the real character and
	# the runtime renders it as a normal DOM text node. This label emit point
	# does not route through to_ts_literal (gen_object_library.py uses repr()
	# directly), so decoding happens here instead.
	label = pipeline.entity_decode.decode_entities(data["label"])

	if kind not in kinds_enum:
		raise ValueError(
			f"Invalid kind '{kind}' not in KINDS enum: {yaml_path}"
		)

	# Parse state fields (object-level vs subpart-level)
	object_state_fields, subpart_state_fields = parse_state_fields(data, yaml_path)

	# Parse visual_states into structured form
	visual_states = parse_visual_states(data, yaml_path)

	# Extract primary asset_name (for layout engine asset lookup)
	asset_name = extract_primary_asset(visual_states, data)
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
	subpart_geometry, view_box = derive_grid_geometry(object_name, structure)
	# The source's legacy SVG case table still selected the primary asset above.
	# Structured legacy material pairs lower into the typed render-effect contract
	# only after their internal target geometry is known.
	visual_states = lower_legacy_subpart_material_effects(
		visual_states,
		yaml_path,
		subpart_geometry is not None,
	)

	# Declared subpart vocabulary for structured objects: every subpart instance
	# name (tube_A, lane_1, A1..H12) plus the flattened subpart_groups map
	# (all_wells, row_A, col_1, ...). The runtime validates authored
	# "<object>.<subpart>" targets against these and fans a group write out to
	# its members. Empty for non-structured objects.
	subpart_names = derive_subpart_names(object_name, structure)
	subpart_groups = derive_subpart_groups(object_name, structure, subpart_names)

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

def emit_subpart_geometry_ts(
	subpart_geometry: dict,
	view_box: dict,
	indent: str,
) -> list:
	"""
	Emit TypeScript lines for the subpart_geometry map and view_box on an
	ObjectDef. Iteration order follows the dict insertion order, which
	derive_grid_geometry builds row-major (A1..H12), giving a deterministic,
	stable emit. Numbers are emitted as decimals (no float repr surprises).
	"""
	lines = []
	lines.append(f"{indent}view_box: " + "{")
	lines.append(f"{indent}\tmin_x: {view_box['min_x']},")
	lines.append(f"{indent}\tmin_y: {view_box['min_y']},")
	lines.append(f"{indent}\twidth: {view_box['width']},")
	lines.append(f"{indent}\theight: {view_box['height']},")
	lines.append(f"{indent}" + "},")

	lines.append(f"{indent}subpart_geometry: " + "{")
	# Preserve insertion order (row-major A1..H12). Do not sort: sorting by
	# string key would put A10 before A2, breaking the spatial reading order.
	for subpart_name, geom in subpart_geometry.items():
		shape = geom["shape"]
		if shape == "circle":
			body = (
				f"shape: 'circle', cx: {geom['cx']}, cy: {geom['cy']},"
				f" r: {geom['r']}"
			)
		elif shape == "rect":
			body = (
				f"shape: 'rect', x: {geom['x']}, y: {geom['y']},"
				f" w: {geom['w']}, h: {geom['h']}"
			)
		else:
			raise ValueError(f"Unknown subpart geometry shape: {shape!r}")
		lines.append(f"{indent}\t{repr(subpart_name)}: " + "{ " + body + " },")
	lines.append(f"{indent}" + "},")
	return lines


#============================================

def emit_object_def_ts(object_name: str, obj: dict) -> list:
	"""Emit the TypeScript lines for one OBJECT_LIBRARY entry."""
	lines = []
	lines.append(f"\t{repr(object_name)}: " + "{")
	lines.append(f"\t\tobject_name: {repr(obj['object_name'])},")
	lines.append(f"\t\tkind: {repr(obj['kind'])},")
	lines.append(f"\t\tlabel: {repr(obj['label'])},")
	lines.append(f"\t\tasset: {repr(obj['asset'])},")

	# capabilities
	caps = obj["capabilities"]
	lines.append("\t\tcapabilities: [")
	for cap in caps:
		lines.append(f"\t\t\t{repr(cap)},")
	lines.append("\t\t],")

	# layout
	lines.append("\t\tlayout: " + "{")
	layout = obj["layout"]
	for key in [
		"default_width",
		"label_width",
		"anchor_y",
		"anchor_y_offset",
		"width_scale",
		"display_width_cm",
		"fudge",
	]:
		if key in layout:
			val = layout[key]
			if isinstance(val, str):
				lines.append(f"\t\t\t{key}: {repr(val)},")
			else:
				lines.append(f"\t\t\t{key}: {val},")
	lines.append("\t\t},")

	# state_schema (object-level fields only)
	object_fields = obj["object_state_fields"]
	lines.append("\t\tstate_schema: {")
	for field_name in sorted(object_fields.keys()):
		field = object_fields[field_name]
		field_lines = emit_state_field_ts(field, "\t\t\t")
		lines.append(f"\t\t\t{repr(field_name)}: " + "{")
		# Emit the field body (skip first '{' and last '}' lines, add content)
		for fl in field_lines[1:-1]:
			lines.append(fl)
		lines.append("\t\t\t},")
	lines.append("\t\t},")

	# visual_states
	vs_lines = emit_visual_states_ts(obj["visual_states"], "\t\t")
	lines.extend(vs_lines)

	# subpart_state_schema
	subpart_fields = obj["subpart_state_fields"]
	lines.append("\t\tsubpart_state_schema: {")
	for field_name in sorted(subpart_fields.keys()):
		field = subpart_fields[field_name]
		field_lines = emit_state_field_ts(field, "\t\t\t")
		lines.append(f"\t\t\t{repr(field_name)}: " + "{")
		for fl in field_lines[1:-1]:
			lines.append(fl)
		lines.append("\t\t\t},")
	lines.append("\t\t},")

	# subpart_geometry + view_box (only for recorded grid objects). Both are
	# present together or both absent; emit nothing when there is no geometry.
	subpart_geometry = obj["subpart_geometry"]
	view_box = obj["view_box"]
	if subpart_geometry is not None:
		geom_lines = emit_subpart_geometry_ts(subpart_geometry, view_box, "\t\t")
		lines.extend(geom_lines)

	# subparts + subpart_groups (only for structured grid objects). Both are the
	# declared subpart vocabulary the runtime validates targets against; emit
	# nothing for a non-structured object so its ObjectDef stays minimal.
	subparts = obj["subparts"]
	if subparts:
		lines.append("\t\tsubparts: [")
		for subpart_name in subparts:
			lines.append(f"\t\t\t{repr(subpart_name)},")
		lines.append("\t\t],")
	subpart_groups = obj["subpart_groups"]
	if subpart_groups:
		lines.append("\t\tsubpart_groups: {")
		for group_name in sorted(subpart_groups.keys()):
			members = subpart_groups[group_name]
			member_list = ", ".join(repr(m) for m in members)
			lines.append(f"\t\t\t{repr(group_name)}: [{member_list}],")
		lines.append("\t\t},")

	lines.append("\t},")
	return lines


#============================================

def emit_schema_registry_ts(
	registry: dict,
	export_name: str,
	type_name: str,
) -> list:
	"""
	Emit TypeScript lines for OBJECT_STATE_SCHEMAS or OBJECT_SUBPART_STATE_SCHEMAS.
	registry: {object_name: {field_name: field_def}}
	"""
	lines = []
	lines.append(f"export const {export_name}: {type_name} = " + "{")
	for object_name in sorted(registry.keys()):
		fields = registry[object_name]
		lines.append(f"\t{repr(object_name)}: " + "{")
		for field_name in sorted(fields.keys()):
			field = fields[field_name]
			field_lines = emit_state_field_ts(field, "\t\t")
			lines.append(f"\t\t{repr(field_name)}: " + "{")
			for fl in field_lines[1:-1]:
				lines.append(fl)
			lines.append("\t\t},")
		lines.append("\t},")
	lines.append("};")
	return lines


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
		ts_lines.extend(emit_object_def_ts(object_name, obj))

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
		emit_schema_registry_ts(
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
		emit_schema_registry_ts(
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
