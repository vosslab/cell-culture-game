"""Interaction guidance and operation-shape validation for protocols."""

import math
import re

import validation.yaml_schema.constants
import validation.yaml_schema.findings


class ProtocolInteractionValidationMixin:
	@staticmethod
	def _normalize_guidance_text(value: str) -> str:
		"""Normalize only formatting differences when comparing authored guidance."""
		return value.strip().casefold()

	@staticmethod
	def _normalize_identity_literal(value: str) -> str:
		"""Make a known identifier comparable with its ordinary prose spelling."""
		return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()

	@staticmethod
	def _contains_literal(text: str, literal: str) -> bool:
		"""Match a literal without treating it as a substring of a larger token."""
		if not literal:
			return False
		return re.search(
			rf"(?<![a-z0-9]){re.escape(literal)}(?![a-z0-9])", text.casefold()
		) is not None

	def _guidance_identity_literals(self, target: str) -> set[str]:
		"""Return literal target identities available from the loaded content registry.

		The checks intentionally stop at canonical identifiers, placement names, and
		object-library labels. They do not claim to recognize scientific synonyms.
		"""
		prefix, _separator, suffix = target.partition('.')
		values = {target, prefix}
		if self.db is None:
			return {self._normalize_identity_literal(value) for value in values}

		resolved = self.db.resolve_target(target)
		if resolved is None:
			return {self._normalize_identity_literal(value) for value in values}
		object_data, _subpart = resolved
		object_name = object_data.get('object_name')
		label = object_data.get('label')
		for value in (object_name, label):
			if isinstance(value, str):
				values.add(value)
		if isinstance(object_name, str):
			for placement_name, placed_object_name in self.db.placements.items():
				if placed_object_name == object_name:
					values.add(placement_name + (f".{suffix}" if suffix else ""))
		return {
			self._normalize_identity_literal(value)
			for value in values
			if self._normalize_identity_literal(value)
		}

	def _validate_interaction_guidance(self, interaction: dict, path: str) -> list:
		"""Validate required non-empty guidance and bounded pre-answer safety."""
		findings = []
		guidance_keys = {"instruction", "hint"}
		present = guidance_keys & set(interaction)
		if present != guidance_keys:
			findings.append(validation.yaml_schema.findings.Finding(
				path=path,
				lineno=None,
				severity=validation.yaml_schema.findings.Severity.ERROR,
				message="instruction and hint are required on every interaction",
				tag="guidance_pair",
			))
			return findings

		for key in sorted(guidance_keys):
			value = interaction.get(key)
			if not isinstance(value, str) or not value.strip():
				findings.append(validation.yaml_schema.findings.Finding(
					path=f"{path}.{key}",
					lineno=None,
					severity=validation.yaml_schema.findings.Severity.ERROR,
					message="must be a non-empty plain string",
					tag="guidance_string",
				))
		if findings:
			return findings

		gesture = interaction.get('gesture')
		target = interaction.get('target')
		if gesture == 'select' and isinstance(target, str):
			identities = self._guidance_identity_literals(target)
			for key in sorted(guidance_keys):
				text = self._normalize_identity_literal(interaction[key])
				for identity in identities:
					if self._contains_literal(text, identity):
						findings.append(validation.yaml_schema.findings.Finding(
							path=f"{path}.{key}",
							lineno=None,
							severity=validation.yaml_schema.findings.Severity.ERROR,
							message=(
								"select guidance must not reveal the correct target's "
								"canonical identity, placement identity, or learner label"
							),
							tag="guidance_select_answer_leak",
						))
						break

		validator = interaction.get('validator')
		if (
			gesture == 'type'
			and isinstance(validator, dict)
			and validator.get('preset') == 'target_with_value'
		):
			values = validator.get('value')
			if isinstance(values, dict):
				for key in sorted(guidance_keys):
					text = self._normalize_guidance_text(interaction[key])
					for expected in values.values():
						if isinstance(expected, (str, int, float, bool)):
							literal_value = (
								str(expected).lower() if isinstance(expected, bool) else str(expected)
							)
							literal = self._normalize_guidance_text(literal_value)
							if self._contains_literal(text, literal):
								findings.append(validation.yaml_schema.findings.Finding(
									path=f"{path}.{key}",
									lineno=None,
									severity=validation.yaml_schema.findings.Severity.ERROR,
									message="type guidance must not reveal a target_with_value expected literal",
									tag="guidance_type_answer_leak",
								))
								break
		return findings

	def _validate_repeated_interaction_guidance(self, sequence: list, step_path: str) -> list:
		"""Require distinct guidance when an action signature repeats."""
		findings = []
		groups: dict[tuple[str, str], list[tuple[int, dict]]] = {}
		for index, interaction in enumerate(sequence):
			if not isinstance(interaction, dict):
				continue
			target = interaction.get('target')
			gesture = interaction.get('gesture')
			if isinstance(target, str) and isinstance(gesture, str):
				groups.setdefault((target, gesture), []).append((index, interaction))
		for (target, gesture), entries in groups.items():
			if len(entries) < 2:
				continue
			for key in ("instruction", "hint"):
				values = [
					self._normalize_guidance_text(interaction[key])
					for _index, interaction in entries
					if isinstance(interaction.get(key), str) and interaction[key].strip()
				]
				if len(values) == len(entries) and len(set(values)) != len(values):
					findings.append(validation.yaml_schema.findings.Finding(
						path=step_path,
						lineno=None,
						severity=validation.yaml_schema.findings.Severity.ERROR,
						message=(
							f"repeated ({target!r}, {gesture!r}) interactions require "
							f"distinct {key} values after trim/case normalization"
						),
						tag="repeated_interaction_guidance",
					))
		return findings

	@staticmethod
	def _coerce_finite_numeric(value: object) -> int | float | None:
		"""Match the runtime's finite-number acceptance for authored values."""
		if isinstance(value, bool):
			return None
		if isinstance(value, (int, float)):
			return value if math.isfinite(value) else None
		if isinstance(value, str) and value.strip():
			try:
				parsed = float(value)
			except ValueError:
				return None
			return parsed if math.isfinite(parsed) else None
		return None

	def _validate_validator_shape(self, validator: dict, path: str, scope: str) -> list:
		"""
		Validate validator preset field shape per validation.yaml_schema.constants.VALIDATOR_PRESET_SCHEMA.
		scope: 'interaction' or 'step'
		"""
		findings = []
		preset = validator.get('preset')

		if not preset:
			findings.append(validation.yaml_schema.findings.Finding(
				path=path,
				lineno=None,
				severity=validation.yaml_schema.findings.Severity.ERROR,
				message="missing required field 'preset'",
			))
			return findings

		if preset not in validation.yaml_schema.constants.VALIDATOR_PRESET_SCHEMA:
			# Unrecognized preset is caught elsewhere; skip field-shape check
			return findings

		schema = validation.yaml_schema.constants.VALIDATOR_PRESET_SCHEMA[preset]

		# Check that the preset scope matches the context
		if schema['scope'] != scope:
			findings.append(validation.yaml_schema.findings.Finding(
				path=path,
				lineno=None,
				severity=validation.yaml_schema.findings.Severity.ERROR,
				message=f"preset '{preset}' is for '{schema['scope']}' scope, not '{scope}' scope",
			))

		# Check required fields are present
		for required_field in schema['required']:
			if required_field not in validator:
				findings.append(validation.yaml_schema.findings.Finding(
					path=path,
					lineno=None,
					severity=validation.yaml_schema.findings.Severity.ERROR,
					message=f"preset '{preset}' missing required field '{required_field}'",
				))

		# Check for unknown fields
		known_fields = schema['required'] | schema['optional']
		for field in validator.keys():
			if field not in known_fields:
				findings.append(validation.yaml_schema.findings.Finding(
					path=path,
					lineno=None,
					severity=validation.yaml_schema.findings.Severity.ERROR,
					message=f"preset '{preset}' does not allow unknown field '{field}'",
				))

		return findings

	def _validate_scene_operation_shape(self, op: dict, path: str) -> list:
		"""Validate scene_operation field shape per validation.yaml_schema.constants.SCENE_OPERATION_SCHEMA."""
		findings = []
		op_type = op.get('type')

		if not op_type:
			findings.append(validation.yaml_schema.findings.Finding(
				path=path,
				lineno=None,
				severity=validation.yaml_schema.findings.Severity.ERROR,
				message="missing required field 'type'",
			))
			return findings

		if op_type not in validation.yaml_schema.constants.SCENE_OPERATION_SCHEMA:
			# Unrecognized type is caught elsewhere; skip field-shape check
			return findings

		schema = validation.yaml_schema.constants.SCENE_OPERATION_SCHEMA[op_type]

		# Check required fields are present
		for required_field in schema['required']:
			if required_field not in op:
				findings.append(validation.yaml_schema.findings.Finding(
					path=path,
					lineno=None,
					severity=validation.yaml_schema.findings.Severity.ERROR,
					message=f"'{op_type}' missing required field '{required_field}'",
				))

		# Check for unknown fields
		known_fields = schema['required'] | schema['optional']
		for field in op.keys():
			if field not in known_fields:
				findings.append(validation.yaml_schema.findings.Finding(
					path=path,
					lineno=None,
					severity=validation.yaml_schema.findings.Severity.ERROR,
					message=f"'{op_type}' does not allow unknown field '{field}'",
				))

		return findings

	def _validate_numeric_constraints(self, field: dict, field_name: str, field_value: object, op_target: str, op_path: str) -> list:
		"""
		V3 gate: Check numeric field (int or float) value against declared min/max/step constraints.
		Emits ERROR with code: state_value_out_of_range.
		"""
		findings = []
		field_type = field.get('type')
		if field_type not in ('int', 'float'):
			return findings

		# Extract constraints
		min_val = field.get('min')
		max_val = field.get('max')
		step_val = field.get('step')
		unit = field.get('unit', '')

		# Check min constraint
		if min_val is not None and field_value < min_val:
			unit_str = f" {unit}" if unit else ""
			findings.append(validation.yaml_schema.findings.Finding(
				path=op_path,
				lineno=None,
				severity=validation.yaml_schema.findings.Severity.ERROR,
				message=f"state field '{field_name}' on '{op_target}' value {field_value}{unit_str} below declared minimum {min_val}{unit_str}",
				tag="state_value_out_of_range",
			))

		# Check max constraint
		if max_val is not None and field_value > max_val:
			unit_str = f" {unit}" if unit else ""
			findings.append(validation.yaml_schema.findings.Finding(
				path=op_path,
				lineno=None,
				severity=validation.yaml_schema.findings.Severity.ERROR,
				message=f"state field '{field_name}' on '{op_target}' value {field_value}{unit_str} exceeds declared maximum {max_val}{unit_str}",
				tag="state_value_out_of_range",
			))

		# Check step constraint (value must be min + k*step for integer k)
		if step_val is not None and min_val is not None:
			offset = field_value - min_val
			remainder = offset % step_val
			# Use small epsilon for float comparison
			if abs(remainder) > 1e-9 and abs(remainder - step_val) > 1e-9:
				unit_str = f" {unit}" if unit else ""
				findings.append(validation.yaml_schema.findings.Finding(
					path=op_path,
					lineno=None,
					severity=validation.yaml_schema.findings.Severity.ERROR,
					message=f"state field '{field_name}' on '{op_target}' value {field_value}{unit_str} does not align to step {step_val}{unit_str} from minimum {min_val}{unit_str}",
					tag="state_value_out_of_range",
				))

		return findings

	def _validate_subpart_target(self, op_target: str, op_path: str, field_name: str) -> list:
		"""
		V5 gate: Check that if a field is declared applies_to: subpart,
		the ObjectStateChange target must use dotted form (object.subpart),
		not bare object name.
		Emits ERROR with code: subpart_target_required.
		"""
		findings = []

		# If target contains a dot, it is already in subpart form
		if '.' in op_target:
			return findings

		# Target is bare object name, but field requires subpart form
		findings.append(validation.yaml_schema.findings.Finding(
			path=op_path,
			lineno=None,
			severity=validation.yaml_schema.findings.Severity.ERROR,
			message=f"state field '{field_name}' is declared applies_to: subpart but ObjectStateChange target '{op_target}' is bare object (should be 'object.subpart' form)",
			tag="subpart_target_required",
		))

		return findings
