"""Emit TypeScript object-library definitions from validated object data."""

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
			if "capacity_mg" in vs_def:
				lines.append(f"{indent}\t\tcapacity_mg: {vs_def['capacity_mg']},")
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
