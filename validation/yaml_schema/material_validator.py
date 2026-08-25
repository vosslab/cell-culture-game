"""
MaterialValidator: closure check for content/protocols/<name>/materials.yaml.

Spec: docs/specs/MATERIAL_YAML_FORMAT.md "Material entry schema" and
"Scalar display_color"; lint rule L5 in docs/specs/MATERIAL_LINT.md.

Schema:
- Top-level key `materials:` -> mapping (snake_case material_name -> entry).
- Each entry is a closed dict with exactly two required keys:
  - `label`: string
  - `display_color`: a single scalar hex string matching ^#[0-9a-f]{6}$
- Unknown top-level keys and unknown per-entry keys are rejected.

display_color validation (L5):
- Scalar display_color is required; it must match ^#[0-9a-f]{6}$ exactly
  (lowercase, six digits). Uppercase hex, three-digit shorthand, eight-digit
  alpha, named colors, and rgb()/hsl() syntax are rejected (tag: PALETTE_MALFORMED).
- Nested display_color (a mapping with 'light'/'dark') is rejected (tag:
  PALETTE_NESTED). The project targets light scientific workspaces only; there
  is no theme split.
- Cross-protocol consistency is checked via validate_cross_protocol() on the
  scalar (label, display_color) pair.

Reference resolution (T1_MATERIAL_REF) lives in ProtocolValidator; this
validator only enforces the materials.yaml schema itself.
"""

import re

from validation.yaml_schema.findings import Finding, Severity
from validation.yaml_schema.constants import MATERIAL_REQUIRED_KEYS, MATERIAL_ALL_KEYS


SNAKE_CASE_RE = re.compile(r'^[a-z][a-z0-9_]*$')
# Scalar display_color: exactly six lowercase hex digits (MATERIAL_YAML_FORMAT.md).
HEX_COLOR_RE = re.compile(r'^#[0-9a-f]{6}$')

# Sentinel names must NOT appear in materials.yaml (MATERIAL_YAML_FORMAT.md,
# "Sentinels do not appear in materials.yaml"). The closed allowlist is exactly
# {empty, mixed} per MATERIAL_VOCABULARY.md.
MATERIAL_SENTINEL_NAMES = frozenset({"empty", "mixed"})


class MaterialValidator:
	"""Validates one materials.yaml file against the closed schema."""

	def validate(self, data: object, path: str) -> list:
		"""Return list of Finding for the supplied materials.yaml data."""
		findings = []

		if not isinstance(data, dict):
			findings.append(Finding(
				path=path,
				lineno=None,
				severity=Severity.ERROR,
				message="materials.yaml top level must be a mapping",
				tag="CLOSURE",
			))
			return findings

		# Closure on top-level keys: only `materials:` allowed.
		for key in data.keys():
			if key != 'materials':
				findings.append(Finding(
					path=path,
					lineno=None,
					severity=Severity.ERROR,
					message=f"unknown top-level key '{key}'; only 'materials:' is allowed",
					tag="CLOSURE",
				))

		materials = data.get('materials')
		if materials is None:
			findings.append(Finding(
				path=path,
				lineno=None,
				severity=Severity.ERROR,
				message="materials.yaml missing required top-level 'materials:' key",
				tag="CLOSURE",
			))
			return findings

		if not isinstance(materials, dict):
			findings.append(Finding(
				path=path,
				lineno=None,
				severity=Severity.ERROR,
				message="'materials:' must be a mapping of material_name -> entry",
				tag="CLOSURE",
			))
			return findings

		for material_name, entry in materials.items():
			findings.extend(self._validate_entry(material_name, entry, path))

		return findings

	def _validate_entry(self, material_name: object, entry: object, path: str) -> list:
		"""Validate one material entry (key + body)."""
		findings = []
		entry_path = f"{path}::materials.{material_name}"

		# Sentinels must not appear in materials.yaml (MATERIAL_YAML_FORMAT.md
		# "Sentinels do not appear in materials.yaml"; MATERIAL_VOCABULARY.md
		# sentinel section). Reject early; do not validate the entry body.
		if material_name in MATERIAL_SENTINEL_NAMES:
			findings.append(Finding(
				path=entry_path,
				lineno=None,
				severity=Severity.ERROR,
				message=(
					f"sentinel name '{material_name}' must not appear in materials.yaml; "
					f"sentinels (empty, mixed) are exempt from registration and have no "
					f"registry entry"
				),
				tag="SENTINEL_IN_REGISTRY",
			))
			return findings

		# Material name must be snake_case.
		if not isinstance(material_name, str) or not SNAKE_CASE_RE.match(material_name):
			findings.append(Finding(
				path=entry_path,
				lineno=None,
				severity=Severity.ERROR,
				message=f"material name '{material_name}' must be snake_case (lowercase, digits, underscores)",
				tag="CLOSURE",
			))

		if not isinstance(entry, dict):
			findings.append(Finding(
				path=entry_path,
				lineno=None,
				severity=Severity.ERROR,
				message=f"material '{material_name}' must be a mapping with 'label' and 'display_color'",
				tag="CLOSURE",
			))
			return findings

		# Required keys present.
		missing = MATERIAL_REQUIRED_KEYS - set(entry.keys())
		for key in sorted(missing):
			findings.append(Finding(
				path=entry_path,
				lineno=None,
				severity=Severity.ERROR,
				message=f"material '{material_name}' missing required key '{key}'",
				tag="CLOSURE",
			))

		# Unknown keys.
		for key in entry.keys():
			if key not in MATERIAL_ALL_KEYS:
				findings.append(Finding(
					path=entry_path,
					lineno=None,
					severity=Severity.ERROR,
					message=f"material '{material_name}' has unknown key '{key}'; closed schema rejects extras",
					tag="CLOSURE",
				))

		# Type checks.
		label = entry.get('label')
		if label is not None and not isinstance(label, str):
			findings.append(Finding(
				path=entry_path,
				lineno=None,
				severity=Severity.ERROR,
				message=f"material '{material_name}' field 'label' must be a string",
				tag="CLOSURE",
			))

		color = entry.get('display_color')
		if color is not None:
			findings.extend(self._validate_display_color(material_name, color, entry_path))

		return findings

	def _validate_display_color(self, material_name: object, color: object, entry_path: str) -> list:
		"""Validate display_color as a single scalar hex string.

		Per MATERIAL_YAML_FORMAT.md, display_color is a scalar matching
		^#[0-9a-f]{6}$. The nested light/dark mapping form is rejected (L5).
		"""
		findings = []

		# Reject the nested mapping form (light/dark). No theme split exists.
		if isinstance(color, dict):
			findings.append(Finding(
				path=entry_path,
				lineno=None,
				severity=Severity.ERROR,
				message=f"material '{material_name}' field 'display_color' must be a single scalar hex string like '#a719db', not a nested 'light'/'dark' mapping",
				tag="PALETTE_NESTED",
			))
			return findings

		# Require a scalar string matching exactly six lowercase hex digits.
		if not isinstance(color, str) or not HEX_COLOR_RE.match(color):
			findings.append(Finding(
				path=entry_path,
				lineno=None,
				severity=Severity.ERROR,
				message=f"material '{material_name}' field 'display_color' must be a scalar hex string matching ^#[0-9a-f]{{6}}$ (lowercase, six digits), got '{color}'",
				tag="PALETTE_MALFORMED",
			))

		return findings

	def validate_cross_protocol(self, material_rows: list) -> list:
		"""
		Validate cross-protocol material consistency.

		Args:
			material_rows: list of (path, yaml_data) tuples from all materials.yaml files.

		Returns:
			List of Finding objects for divergences.

		Cross-protocol rule: For any material_name appearing in 2+ files, the
		label and the scalar display_color must be identical across all files.
		Divergences are reported with tag PALETTE_DIVERGENT.
		"""
		findings = []

		# Index: material_name -> set of (path, label, display_color) tuples.
		material_index = {}

		for path, yaml_data in material_rows:
			if not isinstance(yaml_data, dict):
				continue

			materials = yaml_data.get('materials')
			if not isinstance(materials, dict):
				continue

			for material_name, entry in materials.items():
				if not isinstance(entry, dict):
					continue

				label = entry.get('label', '')
				color = entry.get('display_color')

				# Skip entries without a scalar color (caught by single-file validation).
				if not isinstance(color, str):
					continue

				key = material_name
				if key not in material_index:
					material_index[key] = set()

				material_index[key].add((path, label, color))

		# Check for divergences.
		for material_name, entries in material_index.items():
			if len(entries) < 2:
				# Only one occurrence or all invalid; no divergence to report.
				continue

			# Collect all variants to detect which fields diverge.
			entry_list = sorted(list(entries))

			# Extract unique values for each field.
			labels = set(e[1] for e in entry_list)
			colors = set(e[2] for e in entry_list)

			# Determine which fields diverge.
			divergent_fields = []
			if len(labels) > 1:
				divergent_fields.append('label')
			if len(colors) > 1:
				divergent_fields.append('display_color')

			if divergent_fields:
				# Divergence found.
				paths_involved = sorted(set(e[0] for e in entry_list))
				field_details = ', '.join(divergent_fields)
				message = f"material '{material_name}' diverges in {field_details} across protocols. "
				message += f"Found in: {', '.join(paths_involved)}"

				findings.append(Finding(
					path='<cross-protocol>',
					lineno=None,
					severity=Severity.ERROR,
					message=message,
					tag="PALETTE_DIVERGENT",
				))

		return findings
