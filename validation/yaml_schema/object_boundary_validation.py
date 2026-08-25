"""Path, material-render, and SVG-anchor checks for object schemas."""

import validation.shared_toolkit.repo_root
import validation.svg.asset_registry
import validation.yaml_schema.findings


class ObjectBoundaryValidationMixin:
	def _validate_path_kind_consistency(self, obj: dict, path: str) -> list:
		"""
		Validate that file path matches the declared kind field.

		Rule (per docs/specs/OBJECT_YAML_FORMAT.md:28-31):
		- A file at content/objects/<kind>/<name>.yaml must declare kind: <kind>.

		Returns list of validation.yaml_schema.findings.Finding objects (empty if valid).
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
			findings.append(validation.yaml_schema.findings.Finding(
				path=path,
				lineno=None,
				severity=validation.yaml_schema.findings.Severity.ERROR,
				message="object file lives directly under content/objects/ but must live in content/objects/<kind>/ (see docs/specs/OBJECT_YAML_FORMAT.md:28-31)",
			))
		elif len(remaining_parts) == 2:
			# Depth 2: content/objects/<kind>/<name>.yaml
			parent_folder = remaining_parts[0]

			# Extract declared kind from object
			declared_kind = obj.get('kind')
			if declared_kind != parent_folder:
				findings.append(validation.yaml_schema.findings.Finding(
					path=path,
					lineno=None,
					severity=validation.yaml_schema.findings.Severity.ERROR,
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

		# Check for variant fan-out (multiple distinct asset_name values).
		if len(asset_names) > 1:
			# The authored material vocabulary requires one compiled material form.
			# Reject fan-out here at the object boundary so invalid content cannot
			# depend on a later taxonomy pass to become an error.
			findings.append(validation.yaml_schema.findings.Finding(
				path=path,
				lineno=None,
				severity=validation.yaml_schema.findings.Severity.ERROR,
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
			asset_registry = validation.svg.asset_registry.build_svg_asset_registry(repo_root / 'assets')
			svg_path = asset_registry.asset_path(asset_name)
		except validation.svg.asset_registry.SvgAssetRegistryError as exc:
			findings.append(validation.yaml_schema.findings.Finding(
				path=path,
				lineno=None,
				severity=validation.yaml_schema.findings.Severity.ERROR,
				code='invalid-asset-registry',
				message=str(exc),
			))
			return
		except KeyError:
			svg_path = None

		# Literal category: the referenced material form is absent on disk.
		if svg_path is None:
			findings.append(validation.yaml_schema.findings.Finding(
				path=path,
				lineno=None,
				severity=validation.yaml_schema.findings.Severity.WARNING,
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
			findings.append(validation.yaml_schema.findings.Finding(
				path=path,
				lineno=None,
				severity=validation.yaml_schema.findings.Severity.WARNING,
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
