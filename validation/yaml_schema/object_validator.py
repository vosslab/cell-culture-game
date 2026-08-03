"""ObjectValidator: validates object YAML per OBJECT_YAML_FORMAT.md."""

from validation.yaml_schema.constants import (
	OBJECT_KINDS,
	OBJECT_CAPABILITIES,
	OBJECT_REQUIRED_KEYS,
	OBJECT_ALL_KEYS,
	STATE_FIELD_TYPES,
	STRUCTURE_SUBPART_KINDS,
	STRUCTURE_LAYOUT_TYPES,
	SUBPART_GROUP_KINDS,
	CHANNEL_ADDRESSABLE_KINDS,
	KIND_MATERIAL_FIELD_CONVENTION,
)
from validation.yaml_schema.findings import Finding, Severity
import validation.shared_toolkit.repo_root
from validation.svg.asset_registry import SvgAssetRegistryError, build_svg_asset_registry


class ObjectValidator:
	"""Validates object YAML files per OBJECT_YAML_FORMAT.md."""

	def validate(self, obj: dict, path: str) -> list:
		"""
		Validate an object definition.
		Returns list of Finding objects (empty if valid).
		"""
		findings = []

		# Closure: any top-level key not in the documented whitelist is unknown.
		# This subsumes the retired-key check; no allow-list maintained.
		for key in obj.keys():
			if key not in OBJECT_ALL_KEYS:
				findings.append(Finding(
					path=path,
					lineno=None,
					severity=Severity.ERROR,
					message=f"[CLOSURE] unknown top-level key '{key}' (allowed: {sorted(OBJECT_ALL_KEYS)})",
				))

		# Check required keys
		for key in OBJECT_REQUIRED_KEYS:
			if key not in obj:
				findings.append(Finding(
					path=path,
					lineno=None,
					severity=Severity.ERROR,
					message=f"missing required key '{key}'",
				))
				return findings  # Can't continue validation without required keys

		# Path-kind consistency check
		findings.extend(self._validate_path_kind_consistency(obj, path))

		# Identity validation
		findings.extend(self._validate_identity(obj, path))

		# State fields validation
		findings.extend(self._validate_state_fields(obj, path))

		# Visual states completeness validation
		findings.extend(self._validate_visual_states_completeness(obj, path))

		# Kind-to-material-field convention validation
		findings.extend(self._validate_kind_material_field_convention(obj, path))

		# Variant-collapse gate for material volume renderers paired with material identity.
		findings.extend(self._validate_variant_collapse(obj, path))

		# Capabilities validation
		findings.extend(self._validate_capabilities(obj, path))

		# Structure validation (if present)
		if 'structure' in obj:
			findings.extend(self._validate_structure(obj, path))

		# Structured-well-plate per-subpart material rule (D6 gate)
		findings.extend(self._validate_well_plate_subpart_material(obj, path))

		# Channel addressing validation (if present)
		if 'channel_addressing' in obj:
			findings.extend(self._validate_channel_addressing(obj, path))

		return findings

	def _validate_identity(self, obj: dict, path: str) -> list:
		"""Validate object_name, kind, label per OBJECT_YAML_FORMAT.md."""
		findings = []

		object_name = obj.get('object_name')
		if object_name and not self._is_snake_case(object_name):
			findings.append(Finding(
				path=path,
				lineno=None,
				severity=Severity.ERROR,
				message=f"object_name '{object_name}' is not snake_case",
			))

		kind = obj.get('kind')
		if kind and kind not in OBJECT_KINDS:
			findings.append(Finding(
				path=path,
				lineno=None,
				severity=Severity.ERROR,
				message=f"kind '{kind}' not in allowed set {OBJECT_KINDS}",
			))

		label = obj.get('label')
		if not label or not isinstance(label, str) or not label.strip():
			findings.append(Finding(
				path=path,
				lineno=None,
				severity=Severity.ERROR,
				message="label is required and must be non-empty string",
			))

		return findings

	def _validate_state_fields(self, obj: dict, path: str) -> list:
		"""Validate state_fields per OBJECT_YAML_FORMAT.md."""
		findings = []

		state_fields = obj.get('state_fields')
		if not isinstance(state_fields, list):
			findings.append(Finding(
				path=path,
				lineno=None,
				severity=Severity.ERROR,
				message="state_fields must be a list",
			))
			return findings

		seen_names = set()
		for idx, field in enumerate(state_fields):
			field_path = f"{path}.state_fields[{idx}]"

			if not isinstance(field, dict):
				findings.append(Finding(
					path=field_path,
					lineno=None,
					severity=Severity.ERROR,
					message="state_field entry must be a mapping",
				))
				continue

			# Check required keys
			for required_key in ('field_name', 'type', 'default'):
				if required_key not in field:
					findings.append(Finding(
						path=field_path,
						lineno=None,
						severity=Severity.ERROR,
						message=f"missing required key '{required_key}'",
					))

			field_name = field.get('field_name')
			if field_name:
				if field_name in seen_names:
					findings.append(Finding(
						path=field_path,
						lineno=None,
						severity=Severity.ERROR,
						message=f"duplicate field name '{field_name}'",
					))
				else:
					seen_names.add(field_name)

			field_type = field.get('type')
			if field_type and field_type not in STATE_FIELD_TYPES:
				findings.append(Finding(
					path=field_path,
					lineno=None,
					severity=Severity.ERROR,
					message=f"type '{field_type}' not in {STATE_FIELD_TYPES}",
				))

			if field_type == 'enum' and 'allowed' not in field:
				findings.append(Finding(
					path=field_path,
					lineno=None,
					severity=Severity.ERROR,
					message="enum field missing required 'allowed' list",
				))

		return findings

	def _validate_visual_states_completeness(self, obj: dict, path: str) -> list:
		"""
		Validate that every state_field has a matching visual_states entry (V2 gate).

		Per OBJECT_YAML_FORMAT.md line 299-302:
		"Every key in visual_states must name a declared state_field on this object.
		A visual_states key with no matching state_field is a build-time error. The
		reverse is also enforced: every state_field must have a matching visual_states
		entry. A field whose value never affects the visual is declared with an explicit
		visual_states.<field>.kind: composite and an empty composite list so absence
		stays loud."
		"""
		findings = []

		state_fields = obj.get('state_fields')
		visual_states = obj.get('visual_states')

		# Handle missing visual_states
		if visual_states is None:
			visual_states = {}

		if not isinstance(state_fields, list):
			return findings

		if not isinstance(visual_states, dict):
			findings.append(Finding(
				path=path,
				lineno=None,
				severity=Severity.ERROR,
				message="visual_states must be a mapping",
			))
			return findings

		# Collect all state field names
		state_field_names = set()
		for field in state_fields:
			if isinstance(field, dict) and 'field_name' in field:
				state_field_names.add(field['field_name'])

		# Check that every state_field has a visual_states entry
		for field_name in state_field_names:
			if field_name not in visual_states:
				findings.append(Finding(
					path=path,
					lineno=None,
					severity=Severity.ERROR,
					message=f"state_field '{field_name}' missing visual_states entry (see docs/specs/OBJECT_YAML_FORMAT.md:297-302)",
				))

		# Check that every visual_states key names a declared state_field
		for vs_key in visual_states.keys():
			if vs_key not in state_field_names:
				findings.append(Finding(
					path=path,
					lineno=None,
					severity=Severity.ERROR,
					message=f"visual_states key '{vs_key}' does not match any declared state_field",
				))

		return findings

	def _validate_kind_material_field_convention(self, obj: dict, path: str) -> list:
		"""
		Validate kind-to-material-field convention (V7 gate).

		Per docs/specs/OBJECT_YAML_FORMAT.md lines 253-275:
		- pipette: held_material_name (tool semantics)
		- bottle, flask, waste, rack, plate: material_name (vessel semantics)
		- equipment: case-by-case (emits WARNING for manual review at M4)
		- decoration: no material fields allowed (ERROR if any found)
		"""
		findings = []

		kind = obj.get('kind')
		if not kind or kind not in KIND_MATERIAL_FIELD_CONVENTION:
			# Kind validation already happened; skip here
			return findings

		state_fields = obj.get('state_fields', [])
		if not isinstance(state_fields, list):
			return findings

		# Collect all declared state field names
		declared_field_names = set()
		for field in state_fields:
			if isinstance(field, dict) and 'field_name' in field:
				declared_field_names.add(field['field_name'])

		expected_field = KIND_MATERIAL_FIELD_CONVENTION[kind]

		# Case 1: decoration
		# Decoration objects must not have any material-related fields
		if kind == 'decoration':
			material_fields = {'material_name', 'material_volume', 'held_material_name', 'held_material_volume'}
			found_material_fields = declared_field_names & material_fields
			if found_material_fields:
				findings.append(Finding(
					path=path,
					lineno=None,
					severity=Severity.ERROR,
					message=f"kind '{kind}' (decoration) must not declare material fields, but found: {sorted(found_material_fields)} (see docs/specs/OBJECT_YAML_FORMAT.md:269)",
				))
			return findings

		# Case 2: equipment
		# Equipment is case-by-case. The explicit declaration is the
		# `material_container` capability: if the equipment lists it, the
		# author has affirmed the object is a vessel and `material_name`
		# is the correct field. Without that capability, emit a WARNING so
		# the author either adds the capability or removes the field.
		if kind == 'equipment':
			material_fields = {'material_name', 'material_volume', 'held_material_name', 'held_material_volume'}
			found_material_fields = declared_field_names & material_fields
			capabilities = obj.get('capabilities', [])
			has_material_container = isinstance(capabilities, list) and 'material_container' in capabilities
			if found_material_fields and not has_material_container:
				findings.append(Finding(
					path=path,
					lineno=None,
					severity=Severity.WARNING,
					message=f"kind '{kind}' declares {sorted(found_material_fields)} but lacks 'material_container' capability; add the capability to affirm vessel semantics or remove the material fields (see docs/specs/OBJECT_YAML_FORMAT.md 'Kind-to-material-field convention')",
				))
			return findings

		# Case 3: pipette, bottle, flask, waste, rack, plate (single-field kinds)
		# These have a required material field. Check for presence and correctness.
		if expected_field is None:
			# Should not happen for these kinds, but be safe
			return findings

		# Determine the expected volume field based on the expected material field
		# material_name -> material_volume; held_material_name -> held_material_volume
		if expected_field == 'material_name':
			expected_volume_field = 'material_volume'
		elif expected_field == 'held_material_name':
			expected_volume_field = 'held_material_volume'
		else:
			expected_volume_field = f"{expected_field}_volume"

		# Determine the "wrong" field name(s) based on what this kind should not have
		wrong_field = 'held_material_name' if expected_field == 'material_name' else 'material_name'
		wrong_volume_field = 'held_material_volume' if expected_field == 'material_name' else 'material_volume'

		# Priority: if wrong field is declared, report that (more specific)
		has_wrong_field = wrong_field in declared_field_names or wrong_volume_field in declared_field_names
		has_correct_field = expected_field in declared_field_names
		has_correct_volume_field = expected_volume_field in declared_field_names

		if has_wrong_field:
			# Wrong field declared; this is the primary issue
			findings.append(Finding(
				path=path,
				lineno=None,
				severity=Severity.ERROR,
				message=f"kind '{kind}' must use '{expected_field}' field pair, not '{wrong_field}' (see docs/specs/OBJECT_YAML_FORMAT.md 'Kind-to-material-field convention')",
			))
		else:
			# No wrong field, check if correct field is present
			if not has_correct_field:
				# Field is missing entirely
				findings.append(Finding(
					path=path,
					lineno=None,
					severity=Severity.ERROR,
					message=f"kind '{kind}' must declare state_field '{expected_field}', not found (see docs/specs/OBJECT_YAML_FORMAT.md 'Kind-to-material-field convention')",
				))
			elif not has_correct_volume_field:
				# Field name is correct but volume field is missing
				findings.append(Finding(
					path=path,
					lineno=None,
					severity=Severity.ERROR,
					message=f"kind '{kind}' must declare both '{expected_field}' and '{expected_volume_field}', but missing '{expected_volume_field}'",
				))

		return findings

	def _validate_capabilities(self, obj: dict, path: str) -> list:
		"""Validate capabilities per OBJECT_VOCABULARY.md."""
		findings = []

		capabilities = obj.get('capabilities')
		if not isinstance(capabilities, list):
			findings.append(Finding(
				path=path,
				lineno=None,
				severity=Severity.ERROR,
				message="capabilities must be a list",
			))
			return findings

		has_decoration = 'decoration_only' in capabilities
		other_caps = set(capabilities) - {'decoration_only'}

		if has_decoration and other_caps:
			findings.append(Finding(
				path=path,
				lineno=None,
				severity=Severity.ERROR,
				message="decoration_only is mutually exclusive with other capabilities",
			))

		for cap in capabilities:
			if cap not in OBJECT_CAPABILITIES:
				findings.append(Finding(
					path=path,
					lineno=None,
					severity=Severity.ERROR,
					message=f"unknown capability '{cap}'",
				))

		return findings

	def _validate_structure(self, obj: dict, path: str) -> list:
		"""Validate structure block if present."""
		findings = []

		structure = obj.get('structure', {})
		if not isinstance(structure, dict):
			findings.append(Finding(
				path=path,
				lineno=None,
				severity=Severity.ERROR,
				message="structure must be a mapping",
			))
			return findings

		# Check required keys for structure
		subpart_kind = structure.get('subpart_kind')
		if not subpart_kind:
			findings.append(Finding(
				path=path,
				lineno=None,
				severity=Severity.ERROR,
				message="structure requires 'subpart_kind'",
			))
		elif subpart_kind not in STRUCTURE_SUBPART_KINDS:
			findings.append(Finding(
				path=path,
				lineno=None,
				severity=Severity.ERROR,
				message=f"subpart_kind '{subpart_kind}' not in {STRUCTURE_SUBPART_KINDS}",
			))

		layout = structure.get('layout')
		if not layout:
			findings.append(Finding(
				path=path,
				lineno=None,
				severity=Severity.ERROR,
				message="structure requires 'layout'",
			))
		elif layout not in STRUCTURE_LAYOUT_TYPES:
			findings.append(Finding(
				path=path,
				lineno=None,
				severity=Severity.ERROR,
				message=f"layout '{layout}' not in {STRUCTURE_LAYOUT_TYPES}",
			))

		if layout == 'grid':
			for key in ('rows', 'cols'):
				if key not in structure:
					findings.append(Finding(
						path=path,
						lineno=None,
						severity=Severity.ERROR,
						message=f"structure.layout=grid requires '{key}'",
					))

		if layout == 'list':
			if 'count' not in structure:
				findings.append(Finding(
					path=path,
					lineno=None,
					severity=Severity.ERROR,
					message="structure.layout=list requires 'count'",
				))

		if 'name_pattern' not in structure:
			findings.append(Finding(
				path=path,
				lineno=None,
				severity=Severity.ERROR,
				message="structure requires 'name_pattern'",
			))

		# Validate subpart_groups if present per OBJECT_YAML_FORMAT.md
		if 'subpart_groups' in structure:
			findings.extend(self._validate_subpart_groups(structure, path))

		return findings

	def _validate_subpart_groups(self, structure: dict, path: str) -> list:
		"""Validate subpart_groups block if present per OBJECT_YAML_FORMAT.md."""
		findings = []

		subpart_groups = structure.get('subpart_groups')
		if not isinstance(subpart_groups, dict):
			findings.append(Finding(
				path=path,
				lineno=None,
				severity=Severity.ERROR,
				message="structure.subpart_groups must be a mapping",
			))
			return findings

		# subpart_groups is a mapping where each key is a label (author-chosen)
		# and each value is a group-kind mapping with group_kind and members
		for group_label, group_data in subpart_groups.items():
			if not isinstance(group_data, dict):
				findings.append(Finding(
					path=path,
					lineno=None,
					severity=Severity.ERROR,
					message=f"subpart_groups[{group_label}] must be a mapping",
				))
				continue

			# Check group_kind
			group_kind = group_data.get('group_kind')
			if not group_kind:
				findings.append(Finding(
					path=path,
					lineno=None,
					severity=Severity.ERROR,
					message=f"subpart_groups[{group_label}] requires 'group_kind'",
				))
			elif group_kind not in SUBPART_GROUP_KINDS:
				findings.append(Finding(
					path=path,
					lineno=None,
					severity=Severity.ERROR,
					message=f"subpart_groups[{group_label}].group_kind '{group_kind}' not in {SUBPART_GROUP_KINDS}",
				))

			# Check members
			members = group_data.get('members')
			if not isinstance(members, list):
				findings.append(Finding(
					path=path,
					lineno=None,
					severity=Severity.ERROR,
					message=f"subpart_groups[{group_label}].members must be a list",
				))
				continue

			if not members:
				findings.append(Finding(
					path=path,
					lineno=None,
					severity=Severity.ERROR,
					message=f"subpart_groups[{group_label}].members must be non-empty",
				))

			seen_member_names = set()
			for member in members:
				if not isinstance(member, dict):
					findings.append(Finding(
						path=path,
						lineno=None,
						severity=Severity.ERROR,
						message=f"subpart_groups[{group_label}].members entry must be a mapping",
					))
					continue

				# Check member name
				member_name = member.get('name')
				if not member_name:
					findings.append(Finding(
						path=path,
						lineno=None,
						severity=Severity.ERROR,
						message=f"subpart_groups[{group_label}].members entry requires 'name'",
					))
				else:
					if member_name in seen_member_names:
						findings.append(Finding(
							path=path,
							lineno=None,
							severity=Severity.ERROR,
							message=f"subpart_groups[{group_label}] duplicate member name '{member_name}'",
						))
					else:
						seen_member_names.add(member_name)

				# Check contains
				contains = member.get('contains')
				if not isinstance(contains, list):
					findings.append(Finding(
						path=path,
						lineno=None,
						severity=Severity.ERROR,
						message=f"subpart_groups[{group_label}].members.contains must be a list",
					))
				elif not contains:
					findings.append(Finding(
						path=path,
						lineno=None,
						severity=Severity.ERROR,
						message=f"subpart_groups[{group_label}].members.contains must be non-empty",
					))

		return findings

	def _validate_channel_addressing(self, obj: dict, path: str) -> list:
		"""Validate channel_addressing block if present per OBJECT_YAML_FORMAT.md."""
		findings = []

		channel_addressing = obj.get('channel_addressing')
		if not isinstance(channel_addressing, dict):
			findings.append(Finding(
				path=path,
				lineno=None,
				severity=Severity.ERROR,
				message="channel_addressing must be a mapping",
			))
			return findings

		# Check channels
		channels = channel_addressing.get('channels')
		if channels is None:
			findings.append(Finding(
				path=path,
				lineno=None,
				severity=Severity.ERROR,
				message="channel_addressing requires 'channels'",
			))
		elif not isinstance(channels, int) or channels <= 0:
			findings.append(Finding(
				path=path,
				lineno=None,
				severity=Severity.ERROR,
				message=f"channel_addressing.channels must be a positive integer, got {channels}",
			))

		# Check addressable_subpart_kinds
		addressable_subpart_kinds = channel_addressing.get('addressable_subpart_kinds')
		if addressable_subpart_kinds is None:
			findings.append(Finding(
				path=path,
				lineno=None,
				severity=Severity.ERROR,
				message="channel_addressing requires 'addressable_subpart_kinds'",
			))
		elif not isinstance(addressable_subpart_kinds, list):
			findings.append(Finding(
				path=path,
				lineno=None,
				severity=Severity.ERROR,
				message="channel_addressing.addressable_subpart_kinds must be a list",
			))
		else:
			if not addressable_subpart_kinds:
				findings.append(Finding(
					path=path,
					lineno=None,
					severity=Severity.ERROR,
					message="channel_addressing.addressable_subpart_kinds must be non-empty",
				))

			for kind in addressable_subpart_kinds:
				if kind not in CHANNEL_ADDRESSABLE_KINDS:
					findings.append(Finding(
						path=path,
						lineno=None,
						severity=Severity.ERROR,
						message=f"channel_addressing.addressable_subpart_kinds contains '{kind}' not in {CHANNEL_ADDRESSABLE_KINDS}",
					))

		return findings

	def _validate_well_plate_subpart_material(self, obj: dict, path: str) -> list:
		"""
		Validate per-D6: a structured object with structure.subpart_kind: well
		must declare both material_name and material_volume as per-subpart
		state fields (applies_to: subpart). Reject if either is absent.

		This rule fires ONLY for objects whose structure declares
		subpart_kind: well. It does not apply to rack (tube), gel (lane),
		or any non-well structured object, nor to unstructured plates.
		"""
		findings = []

		# Rule only fires for well-subpart structured objects
		structure = obj.get('structure')
		if not isinstance(structure, dict):
			return findings
		if structure.get('subpart_kind') != 'well':
			return findings

		# Collect all (field_name, applies_to) pairs from state_fields
		state_fields = obj.get('state_fields', [])
		if not isinstance(state_fields, list):
			return findings

		# Build set of field_names that are explicitly applies_to: subpart
		subpart_fields: set[str] = set()
		for field in state_fields:
			if not isinstance(field, dict):
				continue
			applies_to = field.get('applies_to', 'object')
			if applies_to == 'subpart':
				field_name = field.get('field_name', '')
				if field_name:
					subpart_fields.add(field_name)

		# Check for required per-subpart fields
		has_material_name = 'material_name' in subpart_fields
		has_material_volume = 'material_volume' in subpart_fields

		if not has_material_name and not has_material_volume:
			findings.append(Finding(
				path=path,
				lineno=None,
				severity=Severity.ERROR,
				message=(
					"structured well plate (structure.subpart_kind: well) must declare "
					"both material_name and material_volume with applies_to: subpart; "
					"neither is present (see docs/specs/OBJECT_YAML_FORMAT.md 'per-subpart material')"
				),
			))
		elif not has_material_name:
			findings.append(Finding(
				path=path,
				lineno=None,
				severity=Severity.ERROR,
				message=(
					"structured well plate (structure.subpart_kind: well) must declare "
					"material_name with applies_to: subpart; field is absent or declared "
					"with applies_to: object (see docs/specs/OBJECT_YAML_FORMAT.md 'per-subpart material')"
				),
			))
		elif not has_material_volume:
			findings.append(Finding(
				path=path,
				lineno=None,
				severity=Severity.ERROR,
				message=(
					"structured well plate (structure.subpart_kind: well) must declare "
					"material_volume with applies_to: subpart; field is absent or declared "
					"with applies_to: object (see docs/specs/OBJECT_YAML_FORMAT.md 'per-subpart material')"
				),
			))

		return findings

	def _validate_path_kind_consistency(self, obj: dict, path: str) -> list:
		"""
		Validate that file path matches the declared kind field.

		Rule (per docs/specs/OBJECT_YAML_FORMAT.md:28-31):
		- A file at content/objects/<kind>/<name>.yaml must declare kind: <kind>.

		Returns list of Finding objects (empty if valid).
		"""
		findings = []

		# Split the path to check depth and extract parent folder name
		path_parts = path.replace('\\', '/').split('/')
		# Normalize: find content/objects/ index and work from there
		if 'objects' not in path_parts:
			# Not an objects file (or malformed path); skip silently
			return findings
		objects_idx = path_parts.index('objects')

		# Count parts after 'objects/'
		remaining_parts = path_parts[objects_idx + 1:]
		if len(remaining_parts) == 1:
			# Depth 1: content/objects/<name>.yaml
			# Error: files must live in a kind subfolder
			findings.append(Finding(
				path=path,
				lineno=None,
				severity=Severity.ERROR,
				message="object file lives directly under content/objects/ but must live in content/objects/<kind>/ (see docs/specs/OBJECT_YAML_FORMAT.md:28-31)",
			))
		elif len(remaining_parts) == 2:
			# Depth 2: content/objects/<kind>/<name>.yaml
			parent_folder = remaining_parts[0]

			# Extract declared kind from object
			declared_kind = obj.get('kind')
			if declared_kind != parent_folder:
				findings.append(Finding(
					path=path,
					lineno=None,
					severity=Severity.ERROR,
					message=f"path-kind mismatch: file at {path} declares kind '{declared_kind}' but parent folder is '{parent_folder}' (see docs/specs/OBJECT_YAML_FORMAT.md:28-31)",
				))

		return findings

	def _validate_variant_collapse(self, obj: dict, path: str) -> list:
		"""
		Validate the variant-collapse gate per WP-VALIDATOR-1.

		Every visual_state that declares a <prefix>material_volume (or
		<prefix>held_material_volume) with the fill_height render effect must
		be paired with a same-prefix
		<prefix>material_name (or <prefix>held_material_name) visual_state
		whose cases all resolve to a single asset_name. If multiple distinct
		asset_name values are found, this is a vocabulary error.

		Pairing by prefix allows per-chamber validation in multi-chamber
		objects (e.g., inner_chamber_material_name/volume separate from
		outer_chamber_material_name/volume).

		The empty sentinel may share the base asset with non-empty materials;
		the compiled material region remains hidden when identity is empty or
		amount is zero.

		The recursive asset-taxonomy gate is the hard rendering check: an
		object-level fill_height binding must select a material-rendered SVG.
		This validator additionally reports source-form readiness when its
		liquid calibration anchors are absent. That advisory never authorizes
		an ordinary SVG to receive a material effect.
		"""
		findings = []

		visual_states = obj.get('visual_states')
		if not isinstance(visual_states, dict):
			return findings

		# Recognize the object-level declarative shape. Formula recognition only
		# preserves diagnostic context for legacy declarations; it does not make
		# a formula a supported runtime material-rendering contract. Current
		# object YAML must use the compiled material-form contract instead.
		volume_renderers: dict[str, tuple[str, bool]] = {}
		for state_name, state_def in visual_states.items():
			if not isinstance(state_def, dict):
				continue

			render_effect = state_def.get('render_effect')
			formula = state_def.get('formula', '')
			uses_legacy_formula = (
				state_def.get('kind') == 'composite'
				and isinstance(formula, str)
				and formula.startswith('fill_height(')
			)
			if render_effect != 'fill_height' and not uses_legacy_formula:
				continue

			prefix = self._extract_material_prefix(state_name)
			if render_effect == 'fill_height':
				requires_anchors = state_def.get('target') in {
					'anchor_liquid_bounds',
					'anchor_liquid_clip',
				}
			else:
				requires_anchors = state_def.get('applies_to', 'object') == 'object'
			volume_renderers[prefix] = (state_name, requires_anchors)

		# For each volume renderer, check the paired material identity state.
		for prefix, renderer_info in volume_renderers.items():
			volume_state_name, requires_anchors = renderer_info
			pairing_result = self._check_material_name_pairing(
				visual_states,
				prefix,
				volume_state_name,
				requires_anchors,
				path,
			)
			findings.extend(pairing_result)

		return findings

	@staticmethod
	def _extract_material_prefix(state_name: str) -> str:
		"""
		Extract the prefix from a material-related state name.

		Examples:
		  'material_volume' -> ''
		  'material_name' -> ''
		  'inner_chamber_material_volume' -> 'inner_chamber_'
		  'outer_chamber_material_volume' -> 'outer_chamber_'
		  'held_material_volume' -> ''
		  'held_material_name' -> ''

		Return empty string if this is not a material-related field.
		"""
		if state_name.endswith('_material_volume') or state_name.endswith('_material_name'):
			# Strip the suffix
			if state_name.endswith('_material_volume'):
				base = state_name[:-len('_material_volume')]
			else:
				base = state_name[:-len('_material_name')]

			# If base is empty or matches 'held', return empty prefix
			if not base or base == 'held':
				return ''

			# Otherwise return the base as the prefix (with trailing _)
			return base + '_'

		if state_name.endswith('_held_material_volume') or state_name.endswith('_held_material_name'):
			# Strip the suffix
			if state_name.endswith('_held_material_volume'):
				base = state_name[:-len('_held_material_volume')]
			else:
				base = state_name[:-len('_held_material_name')]

			# Return the base as the prefix (with trailing _)
			if base:
				return base + '_'
			return ''

		return ''

	def _check_material_name_pairing(
		self,
		visual_states: dict,
		prefix: str,
		volume_state_name: str,
		requires_anchors: bool,
		path: str,
	) -> list:
		"""
		Check that the material_name (or held_material_name) for a given prefix
		is paired with the volume composite and that all cases resolve to a
		single asset_name.

		prefix: '' for material_* / held_material_*, or 'chamber_' for chamber_material_*
		volume_state_name: the name of the volume composite state (e.g. 'material_volume')
		requires_anchors: whether the compiled material form needs its liquid
			calibration anchors checked by this advisory
		path: the object file path for error reporting
		"""
		findings = []

		# Derive the paired material_name field name
		if prefix:
			# e.g. prefix='inner_chamber_' -> field='inner_chamber_material_name'
			material_name_field = prefix + 'material_name'
			held_material_name_field = prefix + 'held_material_name'
		else:
			# Empty prefix case: could be 'material_name' or 'held_material_name'
			material_name_field = 'material_name'
			held_material_name_field = 'held_material_name'

		# Check which field is present in visual_states
		paired_field = None
		if material_name_field in visual_states:
			paired_field = material_name_field
		elif held_material_name_field in visual_states:
			paired_field = held_material_name_field
		else:
			# This legacy cross-field check has no paired identity to inspect.
			# It does not authorize a fill effect; schema and asset-taxonomy
			# validation still determine whether the authored binding is valid.
			return findings

		# Get the material_name visual state
		material_state = visual_states[paired_field]
		if not isinstance(material_state, dict):
			return findings

		# Collect all asset_name values from the material_name cases
		asset_names = set()
		cases = material_state.get('cases')
		if not isinstance(cases, list):
			return findings

		for case in cases:
			if not isinstance(case, dict):
				continue
			output = case.get('output')
			if isinstance(output, dict):
				asset_name = output.get('asset_name')
				if asset_name:
					asset_names.add(asset_name)

		# Check for variant fan-out (multiple distinct asset_name values)
		if len(asset_names) > 1:
		# Preserve a warning for legacy declarations while historical fixtures
		# remain readable. Current object-level effects are additionally checked
		# by the asset-taxonomy gate, which requires one compiled material form
		# instead of a material-specific SVG fan-out.
			findings.append(Finding(
				path=path,
				lineno=None,
				severity=Severity.WARNING,
				code='variant-collapse',
				message=(
					f"[VARIANT-COLLAPSE] {paired_field} cases for volume composite "
					f"{volume_state_name} resolve to {len(asset_names)} distinct asset_name values: "
					f"{sorted(asset_names)}. All cases must resolve to a single base asset "
					f"(the 'empty' sentinel may share the same compiled material form as "
					f"non-empty materials; see docs/specs/MATERIAL_CONVENTION.md)."
				),
			))
		# Report source-form readiness independently for every referenced form.
		# A fan-out finding must not hide a missing-calibration finding.
		if requires_anchors:
			for base_asset_name in sorted(asset_names):
				self._check_asset_anchors(base_asset_name, path, findings)

		return findings

	def _check_asset_anchors(self, asset_name: str, path: str, findings: list) -> None:
		"""
		Source-form readiness advisory: check calibration anchors required by
		the compiled material form. Missing anchors are a WARNING here because
		this YAML validator does not own rendering-category validation; the
		asset-taxonomy gate rejects an ordinary selected SVG for an
		object-level fill_height binding.

		This method modifies the findings list in-place.
		"""
		# Resolve repo root through the shared resolver. The old code walked up
		# from os.getcwd().parent, which starts ABOVE the repo and reports
		# existing assets as missing.
		repo_root = validation.shared_toolkit.repo_root.REPO_ROOT

		try:
			asset_registry = build_svg_asset_registry(repo_root / 'assets')
			svg_path = asset_registry.asset_path(asset_name)
		except SvgAssetRegistryError as exc:
			findings.append(Finding(
				path=path,
				lineno=None,
				severity=Severity.ERROR,
				code='invalid-asset-registry',
				message=str(exc),
			))
			return
		except KeyError:
			svg_path = None

		# Literal category: the referenced material form is absent on disk.
		if svg_path is None:
			findings.append(Finding(
				path=path,
				lineno=None,
				severity=Severity.WARNING,
				code='missing',
				message=(
					f"material SVG absent on disk for asset_name '{asset_name}': "
					"expected one uniquely named SVG below assets/."
				),
			))
			return

		# A present but unreadable source is a real validation failure, not a
		# condition to hide. Let the filesystem error identify the problem.
		svg_content = svg_path.read_text(encoding='utf-8')

		has_clip = 'id="anchor_liquid_clip"' in svg_content
		has_bounds = 'id="anchor_liquid_bounds"' in svg_content

		if not has_clip or not has_bounds:
			missing = []
			if not has_clip:
				missing.append('anchor_liquid_clip')
			if not has_bounds:
				missing.append('anchor_liquid_bounds')

			# The SVG exists but its source form is missing calibration geometry
			# required by the compiled material contract.
			findings.append(Finding(
				path=path,
				lineno=None,
				severity=Severity.WARNING,
				code='non-normalized',
				message=(
					f"material SVG for asset_name '{asset_name}' "
					f"({svg_path.relative_to(repo_root)}) lacks liquid calibration anchors: "
					f"missing {', '.join(missing)}."
				),
			))

	@staticmethod
	def _is_snake_case(s: str) -> bool:
		"""Check if string is snake_case."""
		if not s:
			return False
		return all(c.isalnum() or c == '_' for c in s) and not s[0].isdigit()
