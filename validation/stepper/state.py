"""StateMap: per-protocol object-state tracker keyed by placement_name."""

from validation.stepper.loader import LoadedContentTree
from validation.stepper.findings import Finding, Level, FindingEmitter
from validation.stepper.sentinels import NON_RENDERING_MATERIAL_SENTINELS, BUILTIN_VISIBLE_MATERIALS
from validation.shared_toolkit.discovery import construct_protocol_scene_path
import validation.stepper.state_scene_resolution


class StateMap(validation.stepper.state_scene_resolution.SceneResolutionMixin):
	"""
	Tracks object and material state across a protocol walk.

	Objects are keyed by placement_name (the global instance identifier).
	Each placement maps to:
	  - object_name: the object class
	  - state: dict of field_name -> value
	  - held_material_name: current material in the object (for material_container objects)
	  - held_material_volume: volume of held material

	Placement-name collisions (same name across scenes with different object_name)
	are detected at load and emitted as ERROR.
	"""

	def __init__(
		self,
		tree: LoadedContentTree,
		protocol_name: str,
		emitter: FindingEmitter,
		declared_materials_union: set | None = None,
		produced_materials_set: set | None = None,
		scene_protocol_names: list[str] | None = None,
		material_protocol_names: list[str] | None = None,
	) -> None:
		"""
		Initialize the StateMap for a protocol.

		Args:
			tree: LoadedContentTree from the loader.
			protocol_name: Name of the active protocol.
			emitter: FindingEmitter for recording findings.
			declared_materials_union: Optional union of declared materials from all upstream minis (for sequence runners).
			produced_materials_set: Optional set of materials produced by upstream minis (for sequence runners).

		Raises:
			No exception; collision errors are emitted to the emitter.
		"""
		self.tree = tree
		self.protocol_name = protocol_name
		self.emitter = emitter
		self._state: dict = {}
		self._cursor_placement = None
		self._active_scene = None
		self._cursor_object_name = None  # For channel_addressing checks
		self.declared_materials_union = declared_materials_union or set()
		self.produced_materials_set = produced_materials_set or set()
		self.scene_protocol_names = scene_protocol_names or [protocol_name]
		self.material_protocol_names = material_protocol_names or [protocol_name]
		self._execution_protocol_name = protocol_name
		self._object_state_keys: dict[str, str] = {}

		# Build per-protocol scenes registry (maps object_name -> [(placement_name, scene_name), ...])
		self._scenes_registry: dict = {}

		# Load and validate placements from all scenes
		self._load_placements()
		self._build_scenes_registry()

	#============================================

	def _load_placements(self) -> None:
		"""
		Load placements from base scenes and protocol-local scenes.
		Detect placement-name collisions.
		"""
		placement_registry: dict[tuple[str, str], str] = {}

		# Load from base scenes
		for scene_name, scene_data in self.tree.base_scenes.items():
			self._register_placements(scene_data, placement_registry, f"content/base_scenes/{scene_name}.yaml")

		# Load from protocol-local scenes
		for scene_protocol_name in self.scene_protocol_names:
			protocol_local_scenes = self.tree.protocol_local_scenes.get(scene_protocol_name, {})
			for scene_name, scene_data in protocol_local_scenes.items():
				try:
					rel_path = construct_protocol_scene_path(
						self.tree.root_path / "content" / "protocols", scene_protocol_name, scene_name
					)
					self._register_placements(scene_data, placement_registry, rel_path)
				except RuntimeError as e:
					self.emitter.emit_finding(Finding(
						level=Level.ERROR,
						protocol_name=self.protocol_name,
						step_name=None,
						interaction_index=None,
						target=scene_name,
						file_path="unknown",
						code="scene_path_resolution_failed",
						message=str(e),
						spec_cite="docs/specs/SCENE_YAML_FORMAT.md scene_name",
					))

		# Initialize state for each placement
		for (placement_name, object_name), file_path in placement_registry.items():
			if object_name in self._object_state_keys:
				continue
			obj = self.tree.get_object(object_name)
			if not obj:
				self.emitter.emit_finding(Finding(
					level=Level.ERROR,
					protocol_name=self.protocol_name,
					step_name=None,
					interaction_index=None,
					target=object_name,
					file_path=file_path,
					code="unknown_object_in_scene",
					message=f"object_name '{object_name}' at placement '{placement_name}' not found",
					spec_cite="docs/specs/SCENE_YAML_FORMAT.md placement",
				))
				continue

			state_key = placement_name
			if state_key in self._state:
				state_key = f"{placement_name}::{object_name}"
			self._object_state_keys[object_name] = state_key
			self._state[state_key] = {
				"object_name": object_name,
				"state": {},
				"file_path": file_path,
			}

			# Initialize OBJECT-level state fields with defaults. Subpart-scoped
			# fields (applies_to: subpart) are seeded lazily per subpart in
			# _ensure_subpart_record, so the object record never carries per-
			# subpart material/volume placeholders.
			state_fields = obj.get("state_fields", [])
			for field_decl in state_fields:
				if not isinstance(field_decl, dict):
					continue
				if field_decl.get("applies_to") == "subpart":
					continue
				field_name = field_decl["field_name"]
				default = field_decl.get("default")
				self._state[state_key]["state"][field_name] = default

	def _register_placements(
		self,
		scene_data: dict,
		placement_registry: dict,
		file_path: str,
	) -> None:
		"""
		Register placements from a scene and detect collisions.

		For protocol-local scenes that extend base scenes, resolve the inheritance.

		Args:
			scene_data: The scene YAML dict.
			placement_registry: Mutable dict {placement_name: (object_name, file_path)}.
			file_path: File path for error context.
		"""
		# Start with placements from the scene
		placements = scene_data.get("placements", [])
		if not isinstance(placements, list):
			placements = []

		# If this scene extends a base scene, start with base placements
		extends = scene_data.get("extends")
		if extends and extends in self.tree.base_scenes:
			base_scene = self.tree.base_scenes[extends]
			base_placements = base_scene.get("placements", [])
			placements = list(base_placements) if isinstance(base_placements, list) else []

		# Apply remove_placements (by name)
		# Removal applies to inherited placements before same-name local additions,
		# matching the runtime scene resolver. This lets a derived scene replace a
		# base placement deliberately instead of deleting its own replacement.
		remove_placements = scene_data.get("remove_placements", [])
		if isinstance(remove_placements, list):
			# Handle string entries (the YAML format) as well as legacy dict entries
			removed_names: set[str] = set()
			for p in remove_placements:
				if isinstance(p, str):
					removed_names.add(p)
				elif isinstance(p, dict):
					name = p.get("placement_name")
					if name:
						removed_names.add(name)
			placements = [p for p in placements if not (isinstance(p, dict) and p.get("placement_name") in removed_names)]

		# Apply add_placements after inherited removals so a local replacement with
		# the same placement_name remains visible and addressable.
		add_placements = scene_data.get("add_placements", [])
		if isinstance(add_placements, list):
			placements.extend(add_placements)

		# Register all placements
		for placement in placements:
			if not isinstance(placement, dict):
				continue
			placement_name = placement.get("placement_name")
			object_name = placement.get("object_name")
			if not placement_name or not object_name:
				continue

			# placement_name is a scene-local DOM identity.  A later scene may
			# reuse it for another object without colliding with semantic state.
			placement_registry[(placement_name, object_name)] = file_path

	def set_cursor(self, placement_name: str) -> None:
		"""Update the cursor to a new placement."""
		self._cursor_placement = placement_name
		# Track the object_name for channel_addressing checks
		if placement_name in self._state:
			self._cursor_object_name = self._state[placement_name].get("object_name")
		else:
			self._cursor_object_name = None

	def set_execution_protocol(self, protocol_name: str) -> None:
		"""Set the leaf whose YAML is currently being executed by a shared runner state."""
		if protocol_name not in self.scene_protocol_names:
			raise ValueError(f"protocol '{protocol_name}' is not a member of this state map")
		self._execution_protocol_name = protocol_name

	def get_execution_protocol(self) -> str:
		"""Return the leaf protocol currently supplying operations and scenes."""
		return self._execution_protocol_name

	def get_cursor(self) -> str | None:
		"""Retrieve the current cursor placement."""
		return self._cursor_placement

	def get_cursor_object_name(self) -> str | None:
		"""Retrieve the object_name of the current cursor."""
		return self._cursor_object_name

	def get_channel_addressing(self, object_name: str) -> dict | None:
		"""
		Retrieve channel_addressing info for an object.

		Args:
			object_name: The object name.

		Returns:
			channel_addressing dict if declared, else None.
		"""
		obj = self.tree.get_object(object_name)
		if obj:
			return obj.get("channel_addressing")
		return None

	def set_active_scene(self, scene_name: str, active_scene_file_path: str) -> None:
		"""Set the active scene."""
		self._active_scene = scene_name

	def get_active_scene(self) -> str | None:
		"""Get the active scene."""
		return self._active_scene

	#============================================

	def get_placement_state(self, placement_name: str) -> dict | None:
		"""
		Retrieve state for a placement.

		Args:
			placement_name: The placement name.

		Returns:
			Dict with 'object_name' and 'state' keys, or None if not found.
		"""
		return self._state.get(placement_name)

	def get_subpart_state(self, placement_name: str, subpart_name: str) -> dict | None:
		"""
		Retrieve per-subpart state for a (placement, subpart) pair.

		Per-subpart state is stored independently of the object-level state under
		a composite key 'placement_name.subpart_name'. Returns None if the subpart
		has never been written.

		Args:
			placement_name: The parent placement name.
			subpart_name: The subpart identifier (e.g. 'A1').

		Returns:
			Dict with 'object_name' and 'state' keys, or None if not present.
		"""
		return self._state.get(self._subpart_key(placement_name, subpart_name))

	@staticmethod
	def _subpart_key(placement_name: str, subpart_name: str) -> str:
		"""
		Build the composite state key for a (placement, subpart) pair.

		The dotted form is what detect_state_jumps already expects when it scans
		for subpart records ('.' in placement_name), so per-subpart state slots
		into the existing snapshot/jump machinery without a parallel structure.
		"""
		return f"{placement_name}.{subpart_name}"

	def _ensure_subpart_record(self, placement_name: str, subpart_name: str) -> dict:
		"""
		Return the per-subpart state record, creating it on first write.

		The record mirrors an object-level record ('object_name' + 'state') so the
		same snapshot and state-jump code reads both. New subpart records seed each
		declared subpart field with its default the first time the subpart is
		touched, so an initial write is not mistaken for a transfer.

		Args:
			placement_name: The parent placement name.
			subpart_name: The subpart identifier.

		Returns:
			The mutable per-subpart record dict.
		"""
		key = self._subpart_key(placement_name, subpart_name)
		if key in self._state:
			return self._state[key]

		parent_record = self._state[placement_name]
		object_name = parent_record["object_name"]
		subpart_state: dict = {}

		# Seed declared subpart fields with their defaults so the first real write
		# is distinguishable from initialization (mirrors object-level seeding).
		obj = self.tree.get_object(object_name)
		if obj:
			for field_decl in obj.get("state_fields", []):
				if not isinstance(field_decl, dict):
					continue
				if field_decl.get("applies_to") != "subpart":
					continue
				subpart_state[field_decl["field_name"]] = field_decl.get("default")

		self._state[key] = {
			"object_name": object_name,
			"state": subpart_state,
			"file_path": parent_record["file_path"],
		}
		return self._state[key]

	def mutate_state_field(
		self,
		placement_name: str,
		field_name: str,
		new_value: object,
		subpart_name: str | None = None,
		step_name: str | None = None,
		interaction_index: int | None = None,
		file_path: str = "unknown",
	) -> bool:
		"""
		Mutate a state field with validation.

		When subpart_name is None this mutates the object-level state and validates
		against the object-level field decl. When subpart_name is provided this
		mutates an independent per-subpart record and validates against the
		applies_to: subpart field decl, leaving object-level state untouched.

		Validates that:
		  - The placement exists.
		  - The object declares the field in the requested scope (object vs subpart).
		  - The new value matches the field's type and allowed constraints.
		  - For a subpart material_name (registry-backed, D1), the value is a
		    sentinel or a material registered in the active protocol; an enum
		    'allowed' list on the subpart material field is not applied (the
		    universal vessel does not enumerate every curriculum material).
		  - For object-level material fields, the material is declared (unless a
		    sentinel) and the object has 'material_container' capability.

		Args:
			placement_name: The placement name.
			field_name: The field name to mutate.
			new_value: The new value.
			subpart_name: When set, mutate this subpart's record instead of the object.
			step_name: Optional step name for context.
			interaction_index: Optional interaction index for context.
			file_path: File path for error context.

		Returns:
			True if mutation succeeded, False if an error was emitted.
		"""
		# Verify placement exists
		if placement_name not in self._state:
			self.emitter.emit_finding(Finding(
				level=Level.ERROR,
				protocol_name=self.protocol_name,
				step_name=step_name,
				interaction_index=interaction_index,
				target=placement_name,
				file_path=file_path,
				code="unknown_placement",
				message=f"placement_name '{placement_name}' not found in any scene",
				spec_cite="docs/specs/SCENE_YAML_FORMAT.md placement",
			))
			return False

		placement_data = self._state[placement_name]
		object_name = placement_data["object_name"]

		# A subpart target selects the applies_to: subpart decl; a bare target
		# selects the object-level decl. The error target string keeps the
		# subpart suffix so findings point at the exact well.
		is_subpart = subpart_name is not None
		error_target = self._subpart_key(placement_name, subpart_name) if is_subpart else placement_name

		# Verify field is declared on the object in the requested scope
		field_decl = self.tree.get_state_field(object_name, field_name, subpart_targeted=is_subpart)
		if not field_decl:
			scope_word = "subpart" if is_subpart else "object"
			self.emitter.emit_finding(Finding(
				level=Level.ERROR,
				protocol_name=self.protocol_name,
				step_name=step_name,
				interaction_index=interaction_index,
				target=error_target,
				file_path=file_path,
				code="undeclared_state_field",
				message=f"{scope_word} state field '{field_name}' not declared on object '{object_name}'",
				spec_cite="docs/specs/OBJECT_YAML_FORMAT.md state_fields",
			))
			return False

		# Check field type and allowed values
		field_type = field_decl.get("type")
		allowed = field_decl.get("allowed")

		# D1: a structured-container subpart material_name validates by
		# sentinel-or-registry membership, NOT against an object-declared enum.
		# Skip the enum 'allowed' gate for that case; the registry check below
		# (and the s-unregistered gate in scene_ops) owns its validity.
		is_subpart_material_name = is_subpart and field_name in ("material_name", "held_material_name")

		if field_type == "enum" and allowed and not is_subpart_material_name:
			if new_value not in allowed:
				self.emitter.emit_finding(Finding(
					level=Level.ERROR,
					protocol_name=self.protocol_name,
					step_name=step_name,
					interaction_index=interaction_index,
					target=error_target,
					file_path=file_path,
					code="state_value_not_allowed",
					message=f"field '{field_name}' value '{new_value}' not in allowed: {allowed}",
					spec_cite="docs/specs/OBJECT_YAML_FORMAT.md state_fields",
				))
				return False

		# Validate type
		if field_type == "float":
			if not isinstance(new_value, (int, float)):
				self.emitter.emit_finding(Finding(
					level=Level.ERROR,
					protocol_name=self.protocol_name,
					step_name=step_name,
					interaction_index=interaction_index,
					target=error_target,
					file_path=file_path,
					code="state_value_type_mismatch",
					message=f"field '{field_name}' expects float, got {type(new_value).__name__}",
					spec_cite="docs/specs/OBJECT_YAML_FORMAT.md state_fields",
				))
				return False
		elif field_type == "int":
			if not isinstance(new_value, int) or isinstance(new_value, bool):
				self.emitter.emit_finding(Finding(
					level=Level.ERROR,
					protocol_name=self.protocol_name,
					step_name=step_name,
					interaction_index=interaction_index,
					target=error_target,
					file_path=file_path,
					code="state_value_type_mismatch",
					message=f"field '{field_name}' expects int, got {type(new_value).__name__}",
					spec_cite="docs/specs/OBJECT_YAML_FORMAT.md state_fields",
				))
				return False
		elif field_type == "boolean":
			if not isinstance(new_value, bool):
				self.emitter.emit_finding(Finding(
					level=Level.ERROR,
					protocol_name=self.protocol_name,
					step_name=step_name,
					interaction_index=interaction_index,
					target=error_target,
					file_path=file_path,
					code="state_value_type_mismatch",
					message=f"field '{field_name}' expects boolean, got {type(new_value).__name__}",
					spec_cite="docs/specs/OBJECT_YAML_FORMAT.md state_fields",
				))
				return False

		if field_type in ("float", "int") and isinstance(new_value, (int, float)):
			minimum = field_decl.get("min")
			maximum = field_decl.get("max")
			if minimum is not None and new_value < minimum:
				self.emitter.emit_finding(Finding(
					level=Level.ERROR, protocol_name=self.protocol_name, step_name=step_name,
					interaction_index=interaction_index, target=error_target, file_path=file_path,
					code="state_value_below_minimum",
					message=f"field '{field_name}' value {new_value} is below declared minimum {minimum}",
					spec_cite="docs/specs/OBJECT_YAML_FORMAT.md state_fields",
				))
				return False
			if maximum is not None and new_value > maximum:
				self.emitter.emit_finding(Finding(
					level=Level.ERROR, protocol_name=self.protocol_name, step_name=step_name,
					interaction_index=interaction_index, target=error_target, file_path=file_path,
					code="state_value_above_maximum",
					message=f"field '{field_name}' value {new_value} is above declared maximum {maximum}",
					spec_cite="docs/specs/OBJECT_YAML_FORMAT.md state_fields",
				))
				return False

		# Special validation for material fields
		if field_name in ("material_name", "held_material_name"):
			# Check capability gate (applies to both object and subpart writes;
			# the parent object must be a material_container either way).
			obj = self.tree.get_object(object_name)
			if obj:
				capabilities = obj.get("capabilities", [])
				if "material_container" not in capabilities:
					self.emitter.emit_finding(Finding(
						level=Level.ERROR,
						protocol_name=self.protocol_name,
						step_name=step_name,
						interaction_index=interaction_index,
						target=error_target,
						file_path=file_path,
						code="capability_mismatch",
						message=f"cannot write {field_name} to '{object_name}' which lacks 'material_container' capability",
						spec_cite="docs/specs/OBJECT_YAML_FORMAT.md capabilities",
					))
					return False

			# D1 validity for a written material value: a non-rendering sentinel
			# ("empty"), a built-in visible material ("mixed"), or a name in the
			# active protocol's registry (materials.yaml, plus upstream/produced
			# for sequence runners). The two built-in sets are closed; every other
			# name -- including cells, formazan, mtt, and the waste_* streams --
			# must be registered. A subpart material_name routes a miss to the
			# existing s-unregistered gate (emitted in scene_ops), so it returns
			# False here without raising a second error code. An object-level miss
			# keeps the historical unknown_material ERROR.
			is_builtin = (
				new_value in NON_RENDERING_MATERIAL_SENTINELS
				or new_value in BUILTIN_VISIBLE_MATERIALS
			)
			if not is_builtin:
				material = None
				for material_protocol_name in self.material_protocol_names:
					material = self.tree.get_material(material_protocol_name, new_value)
					if material:
						break
				in_upstream = (
					new_value in self.declared_materials_union
					or new_value in self.produced_materials_set
				)
				if not material and not in_upstream:
					if not is_subpart_material_name:
						# Object-level miss: historical loud error.
						self.emitter.emit_finding(Finding(
							level=Level.ERROR,
							protocol_name=self.protocol_name,
							step_name=step_name,
							interaction_index=interaction_index,
							target=error_target,
							file_path=file_path,
							code="unknown_material",
							message=f"material_name '{new_value}' not declared in materials.yaml for protocol '{self.protocol_name}'",
							spec_cite="docs/specs/MATERIAL_YAML_FORMAT.md D1 registry-backed membership",
						))
					# Subpart miss: the s-unregistered gate (scene_ops) owns the
					# finding; do not store an unregistered material value.
					return False

		# Apply the mutation to the correct record: a per-subpart record when a
		# subpart was targeted, the object-level record otherwise.
		if is_subpart:
			target_record = self._ensure_subpart_record(placement_name, subpart_name)
		else:
			target_record = placement_data
		target_record["state"][field_name] = new_value
		return True

	#============================================

	def snapshot_state(self) -> dict:
		"""
		Create a snapshot of all placement state.

		Returns:
			Dict mapping placement_name -> {object_name, state fields}.
			Used for state-jump detection before/after interaction.
		"""
		snapshot = {}
		for placement_name, placement_data in self._state.items():
			snapshot[placement_name] = {
				"object_name": placement_data["object_name"],
				"state": dict(placement_data["state"]),
			}
		return snapshot

	#============================================

	def get_state_field_unit(self, placement_key: str, field_name: str) -> str | None:
		"""Return the declared unit for a state field on an object or subpart record."""
		is_subpart = "." in placement_key
		parent_key = placement_key.split(".", 1)[0]
		placement = self._state.get(parent_key)
		if not placement:
			return None
		field_decl = self.tree.get_state_field(
			placement["object_name"], field_name, subpart_targeted=is_subpart
		)
		return field_decl.get("unit") if field_decl else None

	def get_state_field_default(self, placement_key: str, field_name: str) -> object:
		"""Return the declared default for an object/subpart state field."""
		is_subpart = "." in placement_key
		parent_key = placement_key.split(".", 1)[0]
		placement = self._state.get(parent_key)
		if not placement:
			return None
		field_decl = self.tree.get_state_field(
			placement["object_name"], field_name, subpart_targeted=is_subpart
		)
		return field_decl.get("default") if field_decl else None

	def is_subpart_group_record(self, placement_key: str) -> bool:
		"""Return whether a dotted state record is a cascade summary rather than material volume."""
		if "." not in placement_key:
			return False
		parent_key, subpart_name = placement_key.split(".", 1)
		placement = self._state.get(parent_key)
		if not placement:
			return False
		object_data = self.tree.get_object(placement["object_name"])
		structure = object_data.get("structure", {}) if object_data else {}
		for group_data in structure.get("subpart_groups", {}).values():
			for member in group_data.get("members", []) if isinstance(group_data, dict) else []:
				if isinstance(member, dict) and member.get("name") == subpart_name:
					return True
		return False

	def _expanded_subpart_targets(self, placement_name: str, subpart_name: str) -> list[str]:
		"""Expand a declared group target to concrete subparts, retaining a single subpart."""
		placement = self._state[placement_name]
		object_data = self.tree.get_object(placement["object_name"])
		structure = object_data.get("structure", {}) if object_data else {}
		for group_data in structure.get("subpart_groups", {}).values():
			for member in group_data.get("members", []) if isinstance(group_data, dict) else []:
				if isinstance(member, dict) and member.get("name") == subpart_name:
					return list(member.get("contains", []))
		return [subpart_name]

	def group_member_count(self, target: str) -> int:
		"""Return concrete member count for a declared group target, otherwise one."""
		object_name, separator, subpart_name = target.partition(".")
		if not separator:
			return 1
		object_data = self.tree.get_object(object_name)
		if not object_data:
			return 1
		structure = object_data.get("structure", {})
		for group_data in structure.get("subpart_groups", {}).values():
			for member in group_data.get("members", []) if isinstance(group_data, dict) else []:
				if isinstance(member, dict) and member.get("name") == subpart_name:
					return len(member.get("contains", []))
		return 1

	def explicit_state_keys_for_target(self, target: str) -> set[str]:
		"""Return canonical state keys mutated by one authored ObjectStateChange."""
		object_name, separator, subpart_name = target.partition(".")
		state_key = self._object_state_keys.get(object_name)
		if not state_key:
			return set()
		if not separator:
			return {state_key}
		keys = {self._subpart_key(state_key, subpart_name)}
		for member in self._expanded_subpart_targets(state_key, subpart_name):
			keys.add(self._subpart_key(state_key, member))
		return keys

	def apply_initial_state(self, entries: object, step_name: str = "initial_state") -> bool:
		"""Apply root initial state once, rejecting malformed, unknown, and overlapping writes."""
		if entries is None:
			return True
		if not isinstance(entries, list):
			self.emitter.emit_finding(Finding(
				level=Level.ERROR, protocol_name=self.protocol_name, step_name=step_name,
				interaction_index=None, target=None, file_path="unknown", code="initial_state_invalid",
				message="initial_state must be a list of target/state entries",
				spec_cite="docs/PRIMARY_SPEC.md Protocol YAML top-level fields",
			))
			return False
		seen_addresses: set[tuple[str, str | None]] = set()
		resolved_entries: list[tuple[str, str | None, dict]] = []
		for entry_index, entry in enumerate(entries):
			if not isinstance(entry, dict) or set(entry) != {"target", "state"}:
				self.emitter.emit_finding(Finding(
					level=Level.ERROR, protocol_name=self.protocol_name, step_name=step_name,
					interaction_index=entry_index, target=None, file_path="unknown", code="initial_state_invalid",
					message="each initial_state entry must contain exactly target and state",
					spec_cite="docs/PRIMARY_SPEC.md Protocol YAML top-level fields",
				))
				return False
			target = entry["target"]
			state = entry["state"]
			if not isinstance(target, str) or not isinstance(state, dict) or not state:
				self.emitter.emit_finding(Finding(
					level=Level.ERROR, protocol_name=self.protocol_name, step_name=step_name,
					interaction_index=entry_index, target=target if isinstance(target, str) else None,
					file_path="unknown", code="initial_state_invalid",
					message="initial_state target must be a string and state must be a non-empty mapping",
					spec_cite="docs/PRIMARY_SPEC.md Protocol YAML top-level fields",
				))
				return False
			placement_name, subpart_name = self._resolve_seed_target(target, step_name, entry_index)
			if not placement_name:
				return False
			addresses = [subpart_name] if subpart_name is None else self._expanded_subpart_targets(placement_name, subpart_name)
			for address in addresses:
				key = (placement_name, address)
				if key in seen_addresses:
					self.emitter.emit_finding(Finding(
						level=Level.ERROR, protocol_name=self.protocol_name, step_name=step_name,
						interaction_index=entry_index, target=target, file_path="unknown",
						code="initial_state_overlap",
						message=f"initial_state overlaps prior write at '{placement_name}.{address}'",
						spec_cite="docs/PRIMARY_SPEC.md Protocol YAML top-level fields",
					))
					return False
				seen_addresses.add(key)
			for address in addresses:
				resolved_entries.append((placement_name, address, state))
		for placement_name, subpart_name, state in resolved_entries:
			for field_name, value in state.items():
				if not self.mutate_state_field(
					placement_name, field_name, value, subpart_name=subpart_name,
					step_name=step_name, file_path="unknown",
				):
					return False
		return True

	def _resolve_seed_target(
		self, target: str, step_name: str, interaction_index: int
	) -> tuple[str | None, str | None]:
		"""Resolve initial state by stable object identity, independent of active scene placement."""
		object_name, separator, subpart_name = target.partition(".")
		object_data = self.tree.get_object(object_name)
		if object_data and object_name in self._object_state_keys:
			if separator and not self.tree.database.subpart_matches(object_data, subpart_name):
				self.emitter.emit_finding(Finding(
					level=Level.ERROR, protocol_name=self.protocol_name, step_name=step_name,
					interaction_index=interaction_index, target=target, file_path="unknown",
					code="unknown_authored_subpart", message=f"target '{target}' names no declared subpart",
					spec_cite="docs/PRIMARY_SPEC.md Targets and the scene boundary",
				))
				return None, subpart_name
			return self._object_state_keys[object_name], subpart_name if separator else None
		return self.resolve_target(target, step_name, interaction_index)
