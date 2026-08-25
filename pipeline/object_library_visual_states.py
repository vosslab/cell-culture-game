"""Parse and lower closed object visual-state declarations."""

# Standard Library
import math
import re

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
