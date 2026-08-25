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
import validation.yaml_schema.object_boundary_validation


class ObjectValidator(validation.yaml_schema.object_boundary_validation.ObjectBoundaryValidationMixin):
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
