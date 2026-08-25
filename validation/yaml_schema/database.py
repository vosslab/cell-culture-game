"""ContentDatabase: relational registry of all content across content tree."""

from pathlib import Path
import re

from validation.shared_toolkit.yaml_io import load_yaml
from validation.yaml_schema.findings import Finding, Severity
from pipeline.scene_inheritance import resolve_protocol_scene


class ContentDatabase:
	"""Holds all loaded content as a relational registry."""

	def __init__(self) -> None:
		"""Initialize empty registry."""
		self.objects: dict = {}
		self.base_scenes: dict = {}
		self.protocols: dict = {}
		self.materials_by_protocol: dict = {}
		# placement_name -> object_name, gathered from every resolved scene
		# (base scenes and every protocol scene under content/protocols/**/scenes/).
		# This mirrors the runtime identity model (src/scene_runtime/protocol/
		# target_adapter.ts): a protocol target resolves to either a scene
		# placement_name or an object_name, never only the latter.
		self.placements: dict = {}
		self.findings: list[Finding] = []

	def load_from_tree(self, root: Path) -> None:
		"""
		Walk content tree and load all YAML files into registry.
		Populates objects, base_scenes, protocols, materials_by_protocol.
		Errors are collected in self.findings.
		"""
		root_path = Path(root)

		# Load objects
		objects_dir = root_path / 'content' / 'objects'
		if objects_dir.exists():
			for obj_file in sorted(objects_dir.glob('**/*.yaml')):
				try:
					obj_data = load_yaml(obj_file)
					obj_name = obj_data.get('object_name')
					if obj_name:
						self.objects[obj_name] = obj_data
				except RuntimeError as e:
					rel_path = str(obj_file.relative_to(root_path))
					self.findings.append(Finding(
						path=rel_path,
						lineno=None,
						severity=Severity.ERROR,
						message=str(e),
						tool="yaml_parser",
						code="yaml_parse_error",
					))

		# Load base scenes
		scenes_dir = root_path / 'content' / 'base_scenes'
		if scenes_dir.exists():
			for scene_file in sorted(scenes_dir.glob('*.yaml')):
				try:
					scene_data = load_yaml(scene_file)
					scene_name = scene_data.get('scene_name')
					if scene_name:
						self.base_scenes[scene_name] = scene_data
						self._register_placements(scene_data.get('placements', []))
				except RuntimeError as e:
					rel_path = str(scene_file.relative_to(root_path))
					self.findings.append(Finding(
						path=rel_path,
						lineno=None,
						severity=Severity.ERROR,
						message=str(e),
						tool="yaml_parser",
						code="yaml_parse_error",
					))

		# Load protocols and their contents
		protocols_dir = root_path / 'content' / 'protocols'
		if protocols_dir.exists():
			# Use rglob to find protocol.yaml at any depth (handles both flat and clustered layouts)
			for protocol_file in sorted(protocols_dir.rglob('protocol.yaml')):
				protocol_dir = protocol_file.parent
				try:
					protocol_data = load_yaml(protocol_file)
					protocol_name = protocol_data.get('protocol_name')
					if protocol_name:
						self.protocols[protocol_name] = protocol_data
				except RuntimeError as e:
					rel_path = str(protocol_file.relative_to(root_path))
					self.findings.append(Finding(
						path=rel_path,
						lineno=None,
						severity=Severity.ERROR,
						message=str(e),
						tool="yaml_parser",
						code="yaml_parse_error",
					))

				# Load materials.yaml
				materials_file = protocol_dir / 'materials.yaml'
				if materials_file.exists():
					try:
						materials_data = load_yaml(materials_file)
						protocol_name = protocol_dir.name
						materials_dict = materials_data.get('materials', {})
						if isinstance(materials_dict, dict):
							self.materials_by_protocol[protocol_name] = materials_dict
					except RuntimeError as e:
						rel_path = str(materials_file.relative_to(root_path))
						self.findings.append(Finding(
							path=rel_path,
							lineno=None,
							severity=Severity.ERROR,
							message=str(e),
							tool="yaml_parser",
							code="yaml_parse_error",
						))

				# Load per-protocol scenes (content/protocols/.../scenes/*.yaml).
				# Each protocol scene extends a base scene; resolving the
				# inheritance chain gathers every placement_name a protocol's
				# interaction targets may legitimately name (M7 placement-name
				# identity model), not just declared object_names.
				scenes_subdir = protocol_dir / 'scenes'
				if scenes_subdir.exists():
					for protocol_scene_file in sorted(scenes_subdir.glob('*.yaml')):
						try:
							protocol_scene_data = load_yaml(protocol_scene_file)
							scene_name = protocol_scene_data.get('scene_name', protocol_scene_file.stem)
							resolved_scene = resolve_protocol_scene(
								scene_name, protocol_scene_data, self.base_scenes
							)
							self._register_placements(resolved_scene.get('placements', []))
						except RuntimeError as e:
							rel_path = str(protocol_scene_file.relative_to(root_path))
							self.findings.append(Finding(
								path=rel_path,
								lineno=None,
								severity=Severity.ERROR,
								message=str(e),
								tool="yaml_parser",
								code="yaml_parse_error",
							))

	def _register_placements(self, placements: list) -> None:
		"""Record placement_name -> object_name bindings from a resolved scene.

		Mirrors src/scene_runtime/protocol/target_adapter.ts: placement_name is
		the unique DOM/target key, object_name is the non-unique capability key.
		A placement_name may legitimately repeat across scenes (each scene is a
		separate DOM), so this registry is a validator-time union used only to
		check that an authored target names SOME known placement, not to
		enforce cross-scene uniqueness.
		"""
		if not isinstance(placements, list):
			return
		for placement in placements:
			if not isinstance(placement, dict):
				continue
			placement_name = placement.get('placement_name')
			object_name = placement.get('object_name')
			if placement_name and object_name:
				self.placements[placement_name] = object_name

	# ============================================
	# LOOKUP METHODS
	# ============================================

	def resolve_object(self, name: str) -> dict | None:
		"""Resolve object by name. Returns dict or None."""
		return self.objects.get(name)

	def resolve_target_prefix(self, prefix: str) -> dict | None:
		"""
		Resolve a target prefix to its object data.

		A prefix is either a declared object_name (direct lookup) or a
		placement_name (the M7 identity model's DOM/target key; resolved
		through self.placements to the object it renders). This mirrors
		src/scene_runtime/protocol/target_adapter.ts, which accepts both
		an explicit placement_name and an object_name as a valid target prefix.
		"""
		obj = self.resolve_object(prefix)
		if obj:
			return obj
		object_name = self.placements.get(prefix)
		if object_name:
			return self.resolve_object(object_name)
		return None

	def resolve_target(self, target: str) -> tuple | None:
		"""
		Resolve a target (bare or dotted form).
		Returns (object_data, subpart_name) or None.
		Examples:
		  - "well_plate" -> (well_plate_object, None)
		  - "well_plate.A1" -> (well_plate_object, "A1")
		  - "front_microtube_rack" -> (microtube_rack_object, None), resolved
		    via placement_name since front_microtube_rack is a placement, not
		    an object_name.
		"""
		if '.' not in target:
			# Bare target
			obj = self.resolve_target_prefix(target)
			return (obj, None) if obj else None

		# Dotted form: object.subpart (or placement.subpart)
		parts = target.split('.', 1)
		obj_name = parts[0]
		subpart_name = parts[1]

		obj = self.resolve_target_prefix(obj_name)
		if not obj:
			return None

		# Check if subpart_name matches the object's structure
		if self.subpart_matches(obj, subpart_name):
			return (obj, subpart_name)

		return None

	def subpart_matches(self, obj: dict, subpart_name: str) -> bool:
		"""
		Check if subpart_name is valid for this object.
		Matches canonical subparts (from name_pattern), declared subparts,
		and subpart_groups (rows, columns, regions introduced in Patch 4).
		"""
		structure = obj.get('structure', {})
		if not structure:
			return False

		# Check if subpart_name matches declared subparts or pattern
		subparts = structure.get('subparts', [])
		for sp in subparts:
			if isinstance(sp, dict) and sp.get('name') == subpart_name:
				return True
		explicit_names = structure.get('subpart_names', [])
		if isinstance(explicit_names, list) and subpart_name in explicit_names:
			return True

		# Check name_pattern regex; let re.error surface as a real failure
		# (a malformed name_pattern is an object-spec bug, not a hidden case).
		name_pattern = structure.get('name_pattern')
		if name_pattern:
			regex = self._pattern_to_regex(name_pattern)
			if regex.fullmatch(subpart_name):
				return True

		# Check subpart_groups (rows, columns, regions).
		# subpart_groups is a mapping like:
		#   subpart_groups:
		#     rows:
		#       members: [{ name: row_A, ... }, { name: row_B, ... }, ...]
		#     columns:
		#       members: [{ name: col_1, ... }, { name: col_2, ... }, ...]
		#     plate_region:
		#       members: [{ name: all_wells, ... }]
		subpart_groups = structure.get('subpart_groups', {})
		if isinstance(subpart_groups, dict):
			for group_name, group_data in subpart_groups.items():
				if isinstance(group_data, dict):
					members = group_data.get('members', [])
					if isinstance(members, list):
						for member in members:
							if isinstance(member, dict) and member.get('name') == subpart_name:
								return True

		return False

	@staticmethod
	def _pattern_to_regex(pattern: str) -> re.Pattern:
		"""
		Convert OBJECT_YAML_FORMAT.md name_pattern template to regex.
		Examples:
		  - "{row_letter}{col}" -> regex matching [A-Z][0-9]+
		  - "{index}" -> regex matching [0-9]+
		"""
		# Map template tokens to regex pieces
		token_map = {
			'row_letter': '[A-Z]',
			'col': '[0-9]+',
			'column': '[0-9]+',
			'col_letter': '[A-Z]',
			'index': '[0-9]+',
			'row': '[0-9]+',
		}

		regex_pattern = pattern
		for token, regex_piece in token_map.items():
			regex_pattern = regex_pattern.replace(f'{{{token}}}', regex_piece)

		# Escape any remaining {token} literals not covered by token_map so
		# they match as plain text rather than as regex syntax.
		unknown_tokens = re.findall(r'\{([^}]+)\}', regex_pattern)
		for token in unknown_tokens:
			regex_pattern = regex_pattern.replace(f'{{{token}}}', re.escape(f'{{{token}}}'))

		return re.compile(f'^{regex_pattern}$')

	def resolve_state_field(
		self,
		object_name: str,
		field_name: str,
		subpart_targeted: bool = False,
	) -> dict | None:
		"""
		Resolve a state field declaration for an object, scoped by applies_to.

		A structured object may declare the same field_name twice: once at the
		object level (applies_to: object or unset) and once at the subpart level
		(applies_to: subpart). The caller selects the scope:

		  - subpart_targeted=False (default): return the object-level decl, i.e.
		    the entry whose applies_to is not 'subpart' (covers 'object' and the
		    unset case). This preserves every existing caller that resolves a bare
		    target.
		  - subpart_targeted=True: return the subpart-level decl, i.e. the entry
		    whose applies_to == 'subpart'.

		Args:
			object_name: The object class name (or a placement_name naming it;
				see resolve_target_prefix for the M7 identity model).
			field_name: The state field name to resolve.
			subpart_targeted: Select the subpart-scoped decl when True.

		Returns:
			The matching field dict, or None if no entry matches the scope.
		"""
		obj = self.resolve_target_prefix(object_name)
		if not obj:
			return None

		state_fields = obj.get('state_fields', [])
		for field in state_fields:
			if not isinstance(field, dict):
				continue
			if field.get('field_name') != field_name:
				continue
			# applies_to defaults to object scope when unset.
			applies_to = field.get('applies_to', 'object')
			is_subpart_decl = applies_to == 'subpart'
			if subpart_targeted == is_subpart_decl:
				return field

		return None

	def resolve_material(self, protocol_name: str, material_name: str) -> dict | None:
		"""Resolve material entry by protocol and material name."""
		protocol_materials = self.materials_by_protocol.get(protocol_name, {})
		return protocol_materials.get(material_name)
