"""Object catalog, state simulation, and manual-render lint support."""

import os
import re

import yaml

import validation.shared_toolkit.emit
import validation.shared_toolkit.findings
import validation.shared_toolkit.paths


def load_yaml(path: object) -> object:
	"""Load and return parsed YAML."""
	with open(path, encoding="utf-8") as handle:
		data = yaml.safe_load(handle)
	return data


#============================================
class ObjectCatalog:
	"""
	Object library loader. Provides label, state-field unit, default, and
	capability lookups. Subpart-aware: dotted targets like
	well_plate_96.B1 resolve through the parent object's declared kind.
	"""

	def __init__(self) -> None:
		"""Read every object YAML and index by object_name."""
		self.objects = {}
		# Recursively scan OBJECTS_DIR and subdirectories for YAML files.
		for root, dirs, files in os.walk(validation.shared_toolkit.paths.OBJECTS_DIR):
			for filename in sorted(files):
				if not filename.endswith(".yaml"):
					continue
				path = os.path.join(root, filename)
				obj = load_yaml(path)
				name = obj["object_name"]
				self.objects[name] = obj

	#--------------------------------------------
	def label(self, target: object) -> object:
		"""
		Display label for a target. Handles dotted subparts by composing
		the subpart name with the parent's semantic kind.
		"""
		if "." in target:
			parent, subpart = target.split(".", 1)
			parent_obj = self.objects.get(parent)
			if parent_obj is None:
				return target
			parent_label = parent_obj.get("label", parent)
			kind = parent_obj.get("kind", "")
			if kind == "plate":
				# well_plate_96.B1 -> "well B1 of the 96-well plate"
				return f"well {subpart} of the {parent_label}"
			if kind == "rack":
				# dilution_tube_rack_8.tube_A -> "tube A of the rack"
				readable_subpart = subpart.replace("tube_", "tube ")
				return f"{readable_subpart} of the {parent_label}"
			return f"{subpart} of the {parent_label}"
		obj = self.objects.get(target)
		if obj is None:
			return target
		return obj.get("label", target)

	#--------------------------------------------
	def unit_for_field(self, target: object, field_name: object) -> object:
		"""
		Return declared unit for object.field. Walks through subpart
		parent's state_fields and subparts.state_fields to resolve units
		for structured objects.
		"""
		object_name = target.split(".", 1)[0] if "." in target else target
		obj = self.objects.get(object_name)
		if obj is None:
			return ""
		for entry in obj.get("state_fields", []) or []:
			if entry.get("field_name") == field_name:
				return entry.get("unit", "") or ""
		subparts_def = obj.get("subparts", {}) or {}
		for entry in subparts_def.get("state_fields", []) or []:
			if entry.get("field_name") == field_name:
				return entry.get("unit", "") or ""
		return ""

	#--------------------------------------------
	def default_for_field(self, target: object, field_name: object) -> object:
		"""Return declared default for object.field."""
		object_name = target.split(".", 1)[0] if "." in target else target
		obj = self.objects.get(object_name)
		if obj is None:
			return None
		for entry in obj.get("state_fields", []) or []:
			if entry.get("field_name") == field_name:
				return entry.get("default")
		subparts_def = obj.get("subparts", {}) or {}
		for entry in subparts_def.get("state_fields", []) or []:
			if entry.get("field_name") == field_name:
				return entry.get("default")
		return None

	#--------------------------------------------
	def kind(self, target: object) -> object:
		"""Return declared kind for an object."""
		object_name = target.split(".", 1)[0] if "." in target else target
		obj = self.objects.get(object_name)
		if obj is None:
			return ""
		return obj.get("kind", "")


#============================================
def load_material_labels(protocol_name: object) -> object:
	"""Load this protocol's materials.yaml; return name -> label dict."""
	path = os.path.join(validation.shared_toolkit.paths.PROTOCOLS_DIR, protocol_name, "materials.yaml")
	if not os.path.isfile(path):
		return {}
	data = load_yaml(path)
	materials = data.get("materials", {}) or {}
	labels = {}
	for name, material in materials.items():
		labels[name] = material.get("label", name)
	return labels


#============================================
def label_for_material(material_name: object, material_labels: object) -> object:
	"""Display label for a material; sentinels translated to prose."""
	if material_name == "empty":
		return "nothing"
	if material_name == "mixed":
		return "the mixture"
	return material_labels.get(material_name, material_name or "")


#============================================
def labels_overlap(label_a: object, label_b: object) -> object:
	"""
	Detect tautology: do these two labels meaningfully overlap?
	Used to drop redundant material phrase when source object label
	already names the material (PBS bottle labeled "PBS", material
	labeled "PBS" -> "from the PBS" without "of PBS").
	"""
	if not label_a or not label_b:
		return False
	a = label_a.lower().strip()
	b = label_b.lower().strip()
	if a == b:
		return True
	if a in b or b in a:
		return True
	a_tokens = re.findall(r"[a-z0-9]+", a)
	b_tokens = re.findall(r"[a-z0-9]+", b)
	if a_tokens and b_tokens and a_tokens[0] == b_tokens[0]:
		return True
	return False


#============================================
def format_volume(value: object, unit: object) -> object:
	"""Format numeric volume with unit, dropping trailing .0."""
	if value is None:
		return "?"
	try:
		numeric = float(value)
	except (TypeError, ValueError):
		return f"**{value}**"
	unit_str = unit if unit else ""
	# Format as integer if it's a whole number.
	if numeric == int(numeric):
		value_str = str(int(numeric))
	else:
		value_str = f"{numeric:g}"
	# Convert lowercase ul/ml to Title case.
	if unit_str in ("ul", "ml"):
		unit_str = unit_str[0] + "L"
	if unit_str:
		return f"**{value_str} {unit_str}**"
	return f"**{value_str}**"


#============================================
class StateSimulator:
	"""Track per-object/per-subpart state across a protocol."""

	def __init__(self, catalog: object) -> None:
		"""Initialize empty state map."""
		self.catalog = catalog
		self.state = {}

	#--------------------------------------------
	def get(self, target: object, field_name: object) -> object:
		"""Return current value, falling back to declared default."""
		object_state = self.state.get(target, {})
		if field_name in object_state:
			return object_state[field_name]
		return self.catalog.default_for_field(target, field_name)

	#--------------------------------------------
	def set(self, target: object, field_name: object, value: object) -> None:
		"""Write a new value into the state map."""
		if target not in self.state:
			self.state[target] = {}
		self.state[target][field_name] = value


#============================================
# Lint severity mapping: check_class -> Severity
LINT_SEVERITY = {
	"L-ASPIRATE": validation.shared_toolkit.findings.Severity.WARNING,
	"L-MATDRIFT": validation.shared_toolkit.findings.Severity.WARNING,
	"L-VOLMISMATCH": validation.shared_toolkit.findings.Severity.WARNING,
	"L-PROMPT": validation.shared_toolkit.findings.Severity.INFO,
}


#============================================
class LintCollector:
	"""
	Collects authoring lint warnings during protocol render. Stores unique
	(step_name, check_class, message) triples and emits them deduplicated
	and sorted to stderr or as structured findings.
	"""

	def __init__(self) -> None:
		"""Initialize empty warning set."""
		self.warnings = set()

	#--------------------------------------------
	def record(self, step_name: object, check_class: object, message: object) -> None:
		"""Record a lint warning, deduplicating by (step_name, check_class, message)."""
		self.warnings.add((step_name, check_class, message))

	#--------------------------------------------
	def emit_text(self, stderr_stream: object) -> None:
		"""Print all collected warnings to stderr, sorted by (step_name, check_class, message)."""
		if not self.warnings:
			return
		sorted_warnings = sorted(self.warnings)
		for step_name, check_class, message in sorted_warnings:
			stderr_stream.write(f"{step_name}: {check_class}: {message}\n")

	#--------------------------------------------
	def emit_findings(self, protocol_name: object, path: object) -> object:
		"""
		Convert collected warnings to a list of Finding objects.

		Args:
			protocol_name: Name of the protocol being linted.
			path: Repo-relative file path to the protocol.yaml.

		Returns:
			List of validation.shared_toolkit.findings.Finding objects.
		"""
		if not self.warnings:
			return []

		findings = []
		sorted_warnings = sorted(self.warnings)
		for step_name, check_class, message in sorted_warnings:
			severity = LINT_SEVERITY.get(check_class, validation.shared_toolkit.findings.Severity.INFO)
			code = check_class.lower()  # "L-ASPIRATE" -> "l-aspirate"
			finding = validation.shared_toolkit.findings.Finding(
				severity=severity,
				tool="manual",
				code=code,
				message=message,
				path=path,
				line=None,
				protocol=protocol_name,
				scene=None,
				step=step_name,
				target=None,
				extras=None,
			)
			findings.append(finding)
		return findings


#============================================
def find_state_changes(scene_ops: object) -> object:
	"""Return list of ObjectStateChange ops from a scene_ops list."""
	out = []
	for op in scene_ops or []:
		if op.get("type") == "ObjectStateChange":
			out.append(op)
	return out


#============================================
def find_first_op_of_type(scene_ops: object, op_type: object) -> object:
	"""Return the first scene_op of the given type, or None."""
	for op in scene_ops or []:
		if op.get("type") == op_type:
			return op
	return None


#============================================
def apply_state_changes(interaction: object, sim: object) -> None:
	"""Apply every ObjectStateChange in this interaction to the simulator."""
	response = interaction.get("response", {}) or {}
	for op in response.get("scene_operations", []) or []:
		if op.get("type") != "ObjectStateChange":
			continue
		target = op.get("target", "")
		for field, value in (op.get("state", {}) or {}).items():
			sim.set(target, field, value)


#============================================
def is_pipette(catalog: object, target: object) -> object:
	"""Check whether the object is a pipette by declared kind."""
	return catalog.kind(target) == "pipette"


#============================================
def is_plate_subpart(target: object) -> object:
	"""Check whether target is a dotted subpart reference."""
	return "." in target


#============================================
def _volume_match(vol1: object, vol2: object, tolerance: object=0.01) -> object:
	"""
	Check if two volume values match within a tolerance (default 1%).
	Returns True if exact match or if both are within 1% of the larger value.
	"""
	try:
		v1 = float(vol1)
		v2 = float(vol2)
	except (TypeError, ValueError):
		return False
	if v1 == v2:
		return True
	if v1 > 0 and v2 > 0:
		max_val = max(v1, v2)
		pct_diff = abs(v1 - v2) / max_val
		return pct_diff <= tolerance
	return False


#============================================
def _has_nonwaste_pipette_draw(sequence: object, catalog: object, sim: object) -> object:
	"""
	Check if the sequence contains a pipette loading (draw) to a non-waste destination.
	This handles common patterns:
	  1. 4-interaction: pipette click -> adjust -> source click -> dest click
	  2. 3-interaction: pipette click -> source click -> dest click (no adjust)
	  3. adjust -> source click pattern (pipette loading into source, no separate dest)
	Returns True if the sequence has a pipette draw where material is loaded into
	the pipette or a non-waste destination (held_material_name or material_name
	is not "empty"). This is used to detect when "aspirate" in the prompt refers
	to pipette loading (should use "draw") rather than vacuum-removal to waste.
	"""
	for i, interaction in enumerate(sequence):
		target = interaction.get("target", "")
		gesture = interaction.get("gesture", "click")
		if gesture == "click" and is_pipette(catalog, target):
			dest_material = None
			if i + 3 < len(sequence):
				adjust_i = sequence[i + 1]
				source_i = sequence[i + 2]
				dest_i = sequence[i + 3]
				if (
					adjust_i.get("target") == target
					and adjust_i.get("gesture") == "adjust"
					and source_i.get("gesture") == "click"
					and dest_i.get("gesture") == "click"
				):
					dest_change = find_first_op_of_type(
						(dest_i.get("response", {}) or {}).get("scene_operations"),
						"ObjectStateChange",
					)
					if dest_change is not None:
						dest_state = dest_change.get("state", {}) or {}
						dest_material = dest_state.get("material_name")
			elif i + 2 < len(sequence):
				source_i = sequence[i + 1]
				dest_i = sequence[i + 2]
				if (
					source_i.get("gesture") == "click"
					and dest_i.get("gesture") == "click"
					and source_i.get("target") != target
					and dest_i.get("target") != target
				):
					dest_change = find_first_op_of_type(
						(dest_i.get("response", {}) or {}).get("scene_operations"),
						"ObjectStateChange",
					)
					if dest_change is not None:
						dest_state = dest_change.get("state", {}) or {}
						dest_material = dest_state.get("material_name")
			if dest_material and dest_material != "empty":
				return True
		elif gesture == "adjust" and is_pipette(catalog, target):
			if i + 1 < len(sequence):
				next_i = sequence[i + 1]
				if next_i.get("gesture") == "click":
					next_change = find_first_op_of_type(
						(next_i.get("response", {}) or {}).get("scene_operations"),
						"ObjectStateChange",
					)
					if next_change is not None:
						next_state = next_change.get("state", {}) or {}
						held_material = next_state.get("held_material_name")
						if held_material and held_material != "empty":
							return True
	return False


#============================================
