"""Recorded structured-object geometry and subpart vocabulary derivation."""

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
	# gel_cassette (assets/equipment/multi_state/gel_cassette_empty.svg,
	# viewBox 0 0 214 308): lane state is
	# represented in the resolving gel, but the physical loading target is the
	# narrow well mouth at its top. The source art marks each mouth with a
	# data-subpart-id path: lane_1 spans x=36..47, lane_2 x=50..61, and so on,
	# through lane_10 x=162..173. These exact rectangles prevent a learner from
	# successfully clicking the entire vertical gel lane while loading a sample.
	"gel_cassette": {
		"explicit_geometry": {
			f"lane_{index}": {
				"shape": "rect",
				"x": float(36 + 14 * (index - 1)),
				"y": 33.0,
				"w": 11.0,
				"h": 20.0,
			}
			for index in range(1, 11)
		},
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
	# electrophoresis_tank (asset electrophoresis_tank_lidded.svg,
	# viewBox 0 0 320 220): the two lid terminal discs are the exact physical
	# connection targets.  Their geometry belongs to the tank rather than to
	# standalone cable cards; a protocol can therefore address polarity without
	# pretending that a lead's identity changes when its plug is seated.
	"electrophoresis_tank": {
		"explicit_geometry": {
			"black_terminal": {"shape": "circle", "cx": 67.0, "cy": 60.0, "r": 13.0},
			"red_terminal": {"shape": "circle", "cx": 253.0, "cy": 60.0, "r": 13.0},
		},
		"view_box": {
			"min_x": 0.0,
			"min_y": 0.0,
			"width": 320.0,
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
