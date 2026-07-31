"""Scene operation handlers for protocol stepping."""

from validation.stepper.state import StateMap
from validation.stepper.findings import Finding, Level, FindingEmitter
from validation.stepper.loader import LoadedContentTree
from validation.stepper.sentinels import NON_RENDERING_MATERIAL_SENTINELS, BUILTIN_VISIBLE_MATERIALS
from validation.shared_toolkit.discovery import construct_protocol_scene_path


def apply_scene_operation(
	scene_op: dict,
	state_map: StateMap,
	protocol_name: str,
	step_name: str,
	interaction_index: int,
	emitter: FindingEmitter,
	tree: LoadedContentTree | None = None,
) -> bool:
	"""
	Apply a single scene operation.

	Operations are applied top-to-bottom in the response. State changes from
	operation N are visible to operation N+1 inside the same response.

	Args:
		scene_op: The scene_operation dict with 'type' and other fields.
		state_map: The StateMap being mutated.
		protocol_name: The active protocol name.
		step_name: The step name for error context.
		interaction_index: The interaction index for error context.
		emitter: The FindingEmitter for recording findings.
		tree: The LoadedContentTree (required for SceneChange resolution).

	Returns:
		True if the operation succeeded, False if an error was emitted.
	"""
	op_type = scene_op.get("type")

	if op_type == "CursorAttach":
		return _handle_cursor_attach(scene_op, state_map, protocol_name, step_name, interaction_index, emitter)
	elif op_type == "ObjectStateChange":
		return _handle_object_state_change(scene_op, state_map, protocol_name, step_name, interaction_index, emitter, tree)
	elif op_type == "SceneChange":
		return _handle_scene_change(scene_op, state_map, protocol_name, step_name, interaction_index, emitter, tree)
	elif op_type == "TimedWait":
		return _handle_timed_wait(scene_op, state_map, protocol_name, step_name, interaction_index, emitter, tree)
	elif op_type == "LayoutMove":
		# Stepper treats LayoutMove as a no-op; layout position is a rendering concern, not semantic state.
		return True
	else:
		emitter.emit_finding(Finding(
			level=Level.ERROR,
			protocol_name=protocol_name,
			step_name=step_name,
			interaction_index=interaction_index,
			target=None,
			file_path="unknown",
			code="unknown_scene_operation_type",
			message=f"scene_operation type '{op_type}' is not ratified",
			spec_cite="docs/specs/PROTOCOL_STEPS.md scene_operations",
		))
		return False

#============================================

def _handle_subpart_group_cascade(
	target: str,
	placement_name: str,
	state_dict: dict,
	state_map: StateMap,
	protocol_name: str,
	step_name: str,
	interaction_index: int,
	emitter: FindingEmitter,
	tree: LoadedContentTree | None = None,
) -> bool:
	"""
	Handle ObjectStateChange targeting a subpart group.

	Per OBJECT_YAML_FORMAT.md "Cascade-write rule", when target names a
	subpart group (e.g. "well_plate_96.col_1"), propagate declared state
	fields to every cell in the group's `contains` list AND write the
	group's record.

	Args:
		target: The semantic target string (e.g. "well_plate_96.col_1").
		placement_name: The resolved placement_name of the parent object.
		state_dict: The state fields to apply.
		state_map: The StateMap being mutated.
		protocol_name: The active protocol name.
		step_name: The step name for error context.
		interaction_index: The interaction index for error context.
		emitter: The FindingEmitter for recording findings.
		tree: The LoadedContentTree (for object metadata).

	Returns:
		True if all mutations succeeded, False if any error was emitted.
	"""
	# Split target into object_name and subpart_name
	object_name_part, subpart_name = target.split(".", 1)

	# Get the object to retrieve its structure.subpart_groups
	if not tree:
		emitter.emit_finding(Finding(
			level=Level.ERROR,
			protocol_name=protocol_name,
			step_name=step_name,
			interaction_index=interaction_index,
			target=target,
			file_path="unknown",
			code="subpart_group_internal_error",
			message="Subpart group cascade handler called without LoadedContentTree",
			spec_cite="docs/specs/OBJECT_YAML_FORMAT.md Cascade-write rule",
		))
		return False

	placement_data = state_map.get_placement_state(placement_name)
	if not placement_data:
		emitter.emit_finding(Finding(
			level=Level.ERROR,
			protocol_name=protocol_name,
			step_name=step_name,
			interaction_index=interaction_index,
			target=target,
			file_path="unknown",
			code="unknown_placement",
			message=f"Resolved placement '{placement_name}' not found in state map",
			spec_cite="docs/specs/OBJECT_YAML_FORMAT.md Cascade-write rule",
		))
		return False

	object_name = placement_data["object_name"]
	obj = tree.get_object(object_name)
	if not obj:
		emitter.emit_finding(Finding(
			level=Level.ERROR,
			protocol_name=protocol_name,
			step_name=step_name,
			interaction_index=interaction_index,
			target=target,
			file_path="unknown",
			code="unknown_object_in_scene",
			message=f"object_name '{object_name}' not found",
			spec_cite="docs/specs/OBJECT_YAML_FORMAT.md Cascade-write rule",
		))
		return False

	# Get subpart_groups from object structure
	structure = obj.get("structure", {})
	subpart_groups = structure.get("subpart_groups")

	# Search for the group in subpart_groups (can be nested under group_kind key)
	group_members = None
	if subpart_groups:
		for group_key, group_data in subpart_groups.items():
			if isinstance(group_data, dict):
				members_list = group_data.get("members", [])
				for member in members_list:
					if isinstance(member, dict) and member.get("name") == subpart_name:
						group_members = member.get("contains", [])
						break
			if group_members:
				break

	if not group_members:
		# Not a declared subpart group; treat as a canonical cell (e.g.
		# well_plate_96.A1). Write to the cell's own per-subpart record so the
		# state lives at the address the student acted on, not the whole object.
		all_succeeded = True
		for field_name, new_value in state_dict.items():
			success = state_map.mutate_state_field(
				placement_name,
				field_name,
				new_value,
				subpart_name=subpart_name,
				step_name=step_name,
				interaction_index=interaction_index,
				file_path="unknown",
			)
			if not success:
				all_succeeded = False
		return all_succeeded

	# Apply state fields to each cell in contains + the group member itself.
	all_succeeded = True

	# Write the group member's OWN subpart-state record (e.g. row_A), per the
	# Cascade-write rule: the group member is updated AND each contained cell.
	for field_name, new_value in state_dict.items():
		success = state_map.mutate_state_field(
			placement_name,
			field_name,
			new_value,
			subpart_name=subpart_name,
			step_name=step_name,
			interaction_index=interaction_index,
			file_path="unknown",
		)
		if not success:
			all_succeeded = False

	# Write each canonical cell named in the group member's contains list. The
	# cell name is the subpart name; it resolves to the same parent placement.
	for cell_name in group_members:
		cell_target = f"{object_name_part}.{cell_name}"
		cell_placement_name, cell_subpart_name = state_map.resolve_target(
			cell_target, step_name, interaction_index
		)

		if not cell_placement_name:
			# Error already emitted by resolve_target
			all_succeeded = False
			continue

		# Apply the same state fields to the cell's own per-subpart record.
		for field_name, new_value in state_dict.items():
			success = state_map.mutate_state_field(
				cell_placement_name,
				field_name,
				new_value,
				subpart_name=cell_subpart_name,
				step_name=step_name,
				interaction_index=interaction_index,
				file_path="unknown",
			)
			if not success:
				all_succeeded = False

	return all_succeeded

#============================================

def _check_material_registration(
	material_names: list[str],
	protocol_name: str,
	step_name: str,
	interaction_index: int,
	tree: LoadedContentTree | None,
	emitter: FindingEmitter,
) -> None:
	"""
	Check if material names are registered in the protocol's materials.yaml.

	Emits S-UNREGISTERED findings for unregistered materials (excluding the
	closed built-in names "empty" and "mixed").
	Uses dedup logic: one finding per (protocol, material_name) pair, recording
	the first occurrence location.

	Args:
		material_names: List of material name values to check.
		protocol_name: Name of the active protocol.
		step_name: Name of the current step.
		interaction_index: Index of the current interaction.
		tree: LoadedContentTree for material lookups.
		emitter: FindingEmitter for recording findings.
	"""
	if not tree:
		return

	declared_materials = tree.get_protocol_materials(protocol_name)

	for material_name in material_names:
		if not material_name:
			continue

		# Skip the closed built-in material names ("empty", "mixed"); every other
		# name must be registered in the active protocol's materials.yaml.
		if material_name in NON_RENDERING_MATERIAL_SENTINELS:
			continue
		if material_name in BUILTIN_VISIBLE_MATERIALS:
			continue

		# Dedup key: (protocol, material_name)
		dedup_key = (protocol_name, material_name)

		# Check if already reported; first-occurrence-preservation: skip if we've seen this before
		if dedup_key in emitter._unregistered_dedup:
			continue

		# Check if registered; emit one finding per (protocol, material_name)
		if material_name not in declared_materials:
			# Mark as reported to prevent duplicate findings
			emitter._unregistered_dedup.add(dedup_key)

			emitter.emit_finding(Finding(
				level=Level.WARNING,
				protocol_name=protocol_name,
				step_name=step_name,
				interaction_index=interaction_index,
				target=None,
				file_path=f"content/protocols/{protocol_name}/protocol.yaml",
				code="s-unregistered",
				message=f"material '{material_name}' written to object state but not declared in materials.yaml",
				spec_cite="docs/specs/MATERIAL_CONVENTION.md",
			))


#============================================

def _handle_cursor_attach(
	scene_op: dict,
	state_map: StateMap,
	protocol_name: str,
	step_name: str,
	interaction_index: int,
	emitter: FindingEmitter,
) -> bool:
	"""
	Handle CursorAttach operation.

	Updates the cursor to the target placement.

	Args:
		scene_op: The scene_operation dict with 'target'.
		state_map: The StateMap being mutated.
		protocol_name: The active protocol name.
		step_name: The step name for error context.
		interaction_index: The interaction index for error context.
		emitter: The FindingEmitter for recording findings.

	Returns:
		True if successful, False if an error was emitted.
	"""
	target = scene_op.get("target")
	if not target:
		emitter.emit_finding(Finding(
			level=Level.ERROR,
			protocol_name=protocol_name,
			step_name=step_name,
			interaction_index=interaction_index,
			target=None,
			file_path="unknown",
			code="cursor_attach_missing_target",
			message="CursorAttach missing 'target' field",
			spec_cite="docs/specs/PROTOCOL_STEPS.md CursorAttach",
		))
		return False

	# Resolve semantic target to placement_name
	placement_name, subpart_name = state_map.resolve_target(target, step_name, interaction_index)
	if not placement_name:
		# Error already emitted by resolve_target
		return False

	# Verify the resolved placement exists
	placement_state = state_map.get_placement_state(placement_name)
	if not placement_state:
		emitter.emit_finding(Finding(
			level=Level.ERROR,
			protocol_name=protocol_name,
			step_name=step_name,
			interaction_index=interaction_index,
			target=target,
			file_path="unknown",
			code="unknown_placement",
			message=f"Resolved placement '{placement_name}' from target '{target}' not found in state map",
			spec_cite="docs/specs/PROTOCOL_STEPS.md CursorAttach",
		))
		return False

	# Update cursor
	state_map.set_cursor(placement_name)
	return True

#============================================

def _handle_object_state_change(
	scene_op: dict,
	state_map: StateMap,
	protocol_name: str,
	step_name: str,
	interaction_index: int,
	emitter: FindingEmitter,
	tree: LoadedContentTree | None = None,
) -> bool:
	"""
	Handle ObjectStateChange operation.

	Mutates one or more state fields on the target object.

	Args:
		scene_op: The scene_operation dict with 'target' and 'state'.
		state_map: The StateMap being mutated.
		protocol_name: The active protocol name.
		step_name: The step name for error context.
		interaction_index: The interaction index for error context.
		emitter: The FindingEmitter for recording findings.
		tree: The LoadedContentTree (for object metadata and channel_addressing).

	Returns:
		True if all mutations succeeded, False if any error was emitted.
	"""
	target = scene_op.get("target")
	state_dict = scene_op.get("state", {})

	if not target:
		emitter.emit_finding(Finding(
			level=Level.ERROR,
			protocol_name=protocol_name,
			step_name=step_name,
			interaction_index=interaction_index,
			target=None,
			file_path="unknown",
			code="object_state_change_missing_target",
			message="ObjectStateChange missing 'target' field",
			spec_cite="docs/specs/PROTOCOL_STEPS.md ObjectStateChange",
		))
		return False

	if not isinstance(state_dict, dict):
		emitter.emit_finding(Finding(
			level=Level.ERROR,
			protocol_name=protocol_name,
			step_name=step_name,
			interaction_index=interaction_index,
			target=target,
			file_path="unknown",
			code="object_state_change_invalid_state",
			message="ObjectStateChange 'state' field must be a dict",
			spec_cite="docs/specs/PROTOCOL_STEPS.md ObjectStateChange",
		))
		return False

	# Resolve semantic target to placement_name
	placement_name, subpart_name = state_map.resolve_target(target, step_name, interaction_index)
	if not placement_name:
		# Error already emitted by resolve_target
		return False

	# Verify the resolved placement exists
	placement_state = state_map.get_placement_state(placement_name)
	if not placement_state:
		emitter.emit_finding(Finding(
			level=Level.ERROR,
			protocol_name=protocol_name,
			step_name=step_name,
			interaction_index=interaction_index,
			target=target,
			file_path="unknown",
			code="unknown_placement",
			message=f"Resolved placement '{placement_name}' from target '{target}' not found in state map",
			spec_cite="docs/specs/PROTOCOL_STEPS.md ObjectStateChange",
		))
		return False

	# Check material registration and track referenced materials
	# S-UNREGISTERED: material_name and held_material_name must be registered or in allowlist
	material_names_to_check = []
	if "material_name" in state_dict:
		material_names_to_check.append(state_dict["material_name"])
	if "held_material_name" in state_dict:
		material_names_to_check.append(state_dict["held_material_name"])

	_check_material_registration(
		material_names_to_check,
		protocol_name,
		step_name,
		interaction_index,
		tree,
		emitter,
	)

	# Track all materials encountered (including sentinels) for S-UNUSED detection
	for material_name in material_names_to_check:
		if material_name:
			emitter.track_referenced_material(material_name)

	# Check channel_addressing capability if target is a subpart group
	# and a pipette is attached (per OBJECT_YAML_FORMAT.md "Channel addressing").
	# This validation must precede the cascade-write operation below so that capability
	# rejection gates state mutation; otherwise an invalid pipette could mutate cells
	# before the error fires and prevents further progress.
	if "." in target:
		cursor_object_name = state_map.get_cursor_object_name()
		if cursor_object_name:
			channel_addressing = state_map.get_channel_addressing(cursor_object_name)
			if channel_addressing:
				# Extract group_kind from the target
				object_name_part, subpart_name = target.split(".", 1)
				obj = tree.get_object(object_name_part) if tree else None
				if obj:
					structure = obj.get("structure", {})
					subpart_groups = structure.get("subpart_groups")
					if subpart_groups:
						# Find the group_kind for this subpart
						group_kind = None
						for group_key, group_data in subpart_groups.items():
							if isinstance(group_data, dict):
								members_list = group_data.get("members", [])
								for member in members_list:
									if isinstance(member, dict) and member.get("name") == subpart_name:
										group_kind = group_data.get("group_kind")
										break
							if group_kind:
								break

						# Check if pipette can address this group_kind
						if group_kind:
							addressable_subpart_kinds = channel_addressing.get("addressable_subpart_kinds", [])
							if group_kind not in addressable_subpart_kinds:
								emitter.emit_finding(Finding(
									level=Level.ERROR,
									protocol_name=protocol_name,
									step_name=step_name,
									interaction_index=interaction_index,
									target=target,
									file_path="unknown",
									code="pipette_channel_mismatch",
									message=f"pipette '{cursor_object_name}' with addressable_subpart_kinds {addressable_subpart_kinds} cannot address group_kind '{group_kind}' in target '{target}'",
									spec_cite="docs/specs/OBJECT_YAML_FORMAT.md Channel addressing",
								))
								return False

	# Check if this is a subpart group target (contains a dot)
	# If so, apply cascade-write rule: write to every contained cell + the group itself
	if "." in target:
		all_succeeded = _handle_subpart_group_cascade(
			target,
			placement_name,
			state_dict,
			state_map,
			protocol_name,
			step_name,
			interaction_index,
			emitter,
			tree,
		)
	else:
		# Single object mutation
		all_succeeded = True
		for field_name, new_value in state_dict.items():
			success = state_map.mutate_state_field(
				placement_name,
				field_name,
				new_value,
				step_name=step_name,
				interaction_index=interaction_index,
				file_path="unknown",
			)
			if not success:
				all_succeeded = False

	return all_succeeded

#============================================

def _handle_scene_change(
	scene_op: dict,
	state_map: StateMap,
	protocol_name: str,
	step_name: str,
	interaction_index: int,
	emitter: FindingEmitter,
	tree: LoadedContentTree | None = None,
) -> bool:
	"""
	Handle SceneChange operation.

	Validates that the target scene exists in base scenes or protocol-local
	scenes, and updates the active scene.

	Args:
		scene_op: The scene_operation dict with 'to_scene'.
		state_map: The StateMap being mutated (for active scene tracking).
		protocol_name: The active protocol name.
		step_name: The step name for error context.
		interaction_index: The interaction index for error context.
		emitter: The FindingEmitter for recording findings.
		tree: The LoadedContentTree for scene resolution.

	Returns:
		True if the scene was found and set, False if an error was emitted.
	"""
	to_scene = scene_op.get("to_scene")
	if not to_scene:
		emitter.emit_finding(Finding(
			level=Level.ERROR,
			protocol_name=protocol_name,
			step_name=step_name,
			interaction_index=interaction_index,
			target=None,
			file_path="unknown",
			code="scene_change_missing_to_scene",
			message="SceneChange missing 'to_scene' field",
			spec_cite="docs/specs/PROTOCOL_STEPS.md SceneChange",
		))
		return False

	if not tree:
		emitter.emit_finding(Finding(
			level=Level.ERROR,
			protocol_name=protocol_name,
			step_name=step_name,
			interaction_index=interaction_index,
			target=to_scene,
			file_path="unknown",
			code="scene_change_internal_error",
			message="SceneChange handler called without LoadedContentTree",
			spec_cite="docs/specs/PROTOCOL_STEPS.md SceneChange",
		))
		return False

	# Check base scenes
	if to_scene in tree.base_scenes:
		state_map.set_active_scene(to_scene, f"content/base_scenes/{to_scene}.yaml")
		return True

	# Check protocol-local scenes
	protocol_local_scenes = tree.protocol_local_scenes.get(protocol_name, {})
	if to_scene in protocol_local_scenes:
		try:
			scene_path = construct_protocol_scene_path(tree.root_path / "content" / "protocols", protocol_name, to_scene)
			state_map.set_active_scene(to_scene, scene_path)
			return True
		except RuntimeError as e:
			emitter.emit_finding(Finding(
				level=Level.ERROR,
				protocol_name=protocol_name,
				step_name=step_name,
				interaction_index=interaction_index,
				target=to_scene,
				file_path="unknown",
				code="scene_path_resolution_failed",
				message=str(e),
				spec_cite="docs/specs/SCENE_YAML_FORMAT.md scene_name",
			))
			return False

	# Check for protocol-prefixed variant in protocol-local scenes
	prefixed_scene_name = f"{protocol_name}_{to_scene}"
	if prefixed_scene_name in protocol_local_scenes:
		try:
			scene_path = construct_protocol_scene_path(tree.root_path / "content" / "protocols", protocol_name, prefixed_scene_name)
			state_map.set_active_scene(prefixed_scene_name, scene_path)
			return True
		except RuntimeError as e:
			emitter.emit_finding(Finding(
				level=Level.ERROR,
				protocol_name=protocol_name,
				step_name=step_name,
				interaction_index=interaction_index,
				target=prefixed_scene_name,
				file_path="unknown",
				code="scene_path_resolution_failed",
				message=str(e),
				spec_cite="docs/specs/SCENE_YAML_FORMAT.md scene_name",
			))
			return False

	# Scene not found
	emitter.emit_finding(Finding(
		level=Level.ERROR,
		protocol_name=protocol_name,
		step_name=step_name,
		interaction_index=interaction_index,
		target=to_scene,
		file_path="unknown",
		code="scene_change_unresolved",
		message=f"SceneChange to_scene '{to_scene}' not found in base scenes or protocol-local scenes",
		spec_cite="docs/specs/SCENE_YAML_FORMAT.md scene_name",
	))
	return False

#============================================

def _handle_timed_wait(
	scene_op: dict,
	state_map: StateMap,
	protocol_name: str,
	step_name: str,
	interaction_index: int,
	emitter: FindingEmitter,
	tree: LoadedContentTree | None = None,
) -> bool:
	"""
	Handle TimedWait operation.

	Validates that the wait has a positive duration and optionally checks
	that the host step exists (if step_name is tracked in state_map).

	No target resolution; TimedWait has no target per spec. No step-kind check.

	Args:
		scene_op: The scene_operation dict with 'duration_min' or similar.
		state_map: The StateMap (unused for TimedWait).
		protocol_name: The active protocol name.
		step_name: The step name for error context.
		interaction_index: The interaction index for error context.
		emitter: The FindingEmitter for recording findings.
		tree: The LoadedContentTree (unused).

	Returns:
		True if duration is valid, False if an error was emitted.
	"""
	# Check for duration_min field
	duration_min = scene_op.get("duration_min")

	if duration_min is None:
		emitter.emit_finding(Finding(
			level=Level.ERROR,
			protocol_name=protocol_name,
			step_name=step_name,
			interaction_index=interaction_index,
			target=None,
			file_path="unknown",
			code="timed_wait_missing_duration",
			message="TimedWait missing 'duration_min' field",
			spec_cite="docs/specs/PROTOCOL_STEPS.md TimedWait",
		))
		return False

	# Validate duration is positive
	if not isinstance(duration_min, (int, float)) or duration_min <= 0:
		emitter.emit_finding(Finding(
			level=Level.ERROR,
			protocol_name=protocol_name,
			step_name=step_name,
			interaction_index=interaction_index,
			target=None,
			file_path="unknown",
			code="timed_wait_invalid_duration",
			message=f"TimedWait duration_min must be positive, got {duration_min}",
			spec_cite="docs/specs/PROTOCOL_STEPS.md TimedWait",
		))
		return False

	return True


#============================================

def _normalise_volume(value: object, unit: str | None) -> float | None:
	"""Convert compatible liquid amounts to uL; reject mass and unknown dimensions."""
	if not isinstance(value, (int, float)) or isinstance(value, bool):
		return None
	if unit == "ul":
		return float(value)
	if unit == "ml":
		return float(value) * 1000.0
	return None


def _material_identity(state: dict) -> str | None:
	"""Read either vessel or pipette material identity from a state record."""
	return state.get("held_material_name", state.get("material_name"))


def _volume_field(state: dict) -> str | None:
	"""Return the tracked material amount field used by this state record."""
	if "held_material_volume" in state:
		return "held_material_volume"
	if "material_volume" in state:
		return "material_volume"
	return None


def _emit_ledger_error(
	emitter: FindingEmitter,
	protocol_name: str,
	step_name: str,
	interaction_index: int,
	target: str,
	code: str,
	message: str,
) -> None:
	"""Emit one contextual material-accounting failure."""
	emitter.emit_finding(Finding(
		level=Level.ERROR, protocol_name=protocol_name, step_name=step_name,
		interaction_index=interaction_index, target=target, file_path="unknown",
		code=code, message=message,
		spec_cite="docs/specs/OBJECT_YAML_FORMAT.md Material containers",
	))


def validate_material_ledger(
	before_state: dict,
	after_state: dict,
	state_map: StateMap,
	protocol_name: str,
	step_name: str,
	interaction_index: int,
	emitter: FindingEmitter,
	scene_ops: list[dict] | None = None,
) -> None:
	"""Validate explicit pipette-mediated material transfers for one interaction.

	The YAML remains the source of the state transition.  This checker compares
	the declared before/after delta: aspiration fills the attached tool only when
	a compatible source falls by the same amount; dispensing clears that tool only
	when concrete destination writes rise by the same total.  A group cascade
	naturally appears as several destination deltas, so the source is charged for
	the complete fanout rather than one representative well.
	"""
	fanout_members = 1
	for scene_op in scene_ops or []:
		if scene_op.get("type") != "ObjectStateChange":
			continue
		state = scene_op.get("state", {})
		if isinstance(state, dict) and "material_volume" in state:
			fanout_members = max(fanout_members, state_map.group_member_count(scene_op.get("target", "")))
	for placement_name, after_record in after_state.items():
		after_values = after_record.get("state", {})
		before_values = before_state.get(placement_name, {}).get("state", {})
		field_name = _volume_field(after_values)
		if field_name != "held_material_volume":
			continue
		unit = state_map.get_state_field_unit(placement_name, field_name)
		old_amount = _normalise_volume(
			before_values.get(field_name), unit
		)
		new_amount = _normalise_volume(
			after_values.get(field_name), unit
		)
		if old_amount is None or new_amount is None:
			if before_values.get(field_name) != after_values.get(field_name):
				_emit_ledger_error(
					emitter, protocol_name, step_name, interaction_index, placement_name,
					"material_unit_mismatch",
					f"pipette material volume uses incompatible unit '{unit}'",
				)
			continue
		if old_amount == new_amount:
			continue
		old_material = _material_identity(before_values)
		new_material = _material_identity(after_values)
		if new_amount == 0 and new_material != "empty":
			_emit_ledger_error(
				emitter, protocol_name, step_name, interaction_index, placement_name,
				"pipette_not_cleared", "empty pipette volume must be paired with held_material_name: empty",
			)
		if new_amount > old_amount:
			required = new_amount - old_amount
			matching_source = False
			tool_channels = state_map.get_channel_addressing(after_record["object_name"])
			minimum_channels = tool_channels.get("channels", 1) if tool_channels else 1
			for source_name, source_after in after_state.items():
				if state_map.is_subpart_group_record(source_name):
					continue
				source_before_values = before_state.get(source_name, {}).get("state", {})
				source_after_values = source_after.get("state", {})
				source_field = _volume_field(source_after_values)
				if source_field != "material_volume":
					continue
				before_source = _normalise_volume(
					source_before_values.get(source_field), state_map.get_state_field_unit(source_name, source_field)
				)
				after_source = _normalise_volume(
					source_after_values.get(source_field), state_map.get_state_field_unit(source_name, source_field)
				)
				if before_source is None or after_source is None:
					continue
				if before_source < after_source:
					_emit_ledger_error(
						emitter, protocol_name, step_name, interaction_index, source_name,
						"material_amount_drift", "source material volume increased during aspiration",
					)
				decrement = before_source - after_source
				is_single_transfer = abs(decrement - required) < 1e-8
				is_channel_batch = (
					tool_channels is not None and decrement > required
					and abs((decrement / required) - round(decrement / required)) < 1e-8
					and decrement / required >= minimum_channels
				)
				if is_single_transfer or is_channel_batch:
					if _material_identity(source_before_values) == new_material:
						matching_source = True
					else:
						_emit_ledger_error(
							emitter, protocol_name, step_name, interaction_index, source_name,
							"material_identity_mismatch",
							f"aspirated '{new_material}' from source holding '{_material_identity(source_before_values)}'",
						)
			if not matching_source:
				_emit_ledger_error(
					emitter, protocol_name, step_name, interaction_index, placement_name,
					"unbalanced_aspiration",
					f"pipette gained {required:g} uL without an equal compatible source decrement",
				)
		elif new_amount < old_amount:
			dispensed = (old_amount - new_amount) * fanout_members
			destination_total = 0.0
			for destination_name, destination_after in after_state.items():
				if state_map.is_subpart_group_record(destination_name):
					continue
				destination_before_values = before_state.get(destination_name, {}).get("state", {})
				destination_after_values = destination_after.get("state", {})
				destination_field = _volume_field(destination_after_values)
				if destination_field != "material_volume":
					continue
				before_destination = _normalise_volume(
					destination_before_values.get(
						destination_field,
						state_map.get_state_field_default(destination_name, destination_field),
					),
					state_map.get_state_field_unit(destination_name, destination_field),
				)
				after_destination = _normalise_volume(
					destination_after_values.get(destination_field),
					state_map.get_state_field_unit(destination_name, destination_field),
				)
				if before_destination is None or after_destination is None:
					continue
				if after_destination > before_destination:
					# A non-empty destination may form a declared mixture or reaction
					# product; an empty destination may only receive the held material.
					# This distinguishes chemistry from an unexplained wrong-material fill.
					before_identity = _material_identity(destination_before_values)
					after_identity = _material_identity(destination_after_values)
					if after_identity not in (old_material, "mixed") and before_identity in (None, "empty"):
						_emit_ledger_error(
							emitter, protocol_name, step_name, interaction_index, destination_name,
							"material_identity_mismatch",
							f"dispensed '{old_material}' into destination declared as '{_material_identity(destination_after_values)}'",
						)
					destination_total += after_destination - before_destination
			if abs(destination_total - dispensed) >= 1e-8:
				_emit_ledger_error(
					emitter, protocol_name, step_name, interaction_index, placement_name,
					"material_amount_drift",
					f"pipette dispensed {dispensed:g} uL but destinations changed by {destination_total:g} uL",
				)


#============================================

def detect_material_volume_creation(
	before_state: dict,
	after_state: dict,
	scene_ops: list,
	state_map: StateMap,
	protocol_name: str,
	step_name: str,
	interaction_index: int,
	emitter: FindingEmitter,
) -> None:
	"""Reject liquid-volume creation outside an explicit transfer or timed chemistry.

	This complements the pipette ledger: it covers direct ObjectStateChange
	writes to containers and structured subparts even when an author omitted the
	held-pipette mutation.  A non-empty-to-different-identity write is a declared
	mix/transformation, and TimedWait owns time-driven chemistry.  Every other
	material-volume increase must be balanced by a compatible decrease in the
	same response (including a fanout-scaled pipette decrease).
	"""
	if any(scene_op.get("type") == "TimedWait" for scene_op in scene_ops):
		return

	fanout_members = 1
	for scene_op in scene_ops:
		if scene_op.get("type") != "ObjectStateChange":
			continue
		state = scene_op.get("state", {})
		if isinstance(state, dict) and "material_volume" in state:
			fanout_members = max(fanout_members, state_map.group_member_count(scene_op.get("target", "")))

	increase_total = 0.0
	decrease_total = 0.0
	increase_targets: list[str] = []
	for state_key, after_record in after_state.items():
		if state_map.is_subpart_group_record(state_key):
			continue
		after_values = after_record.get("state", {})
		before_values = before_state.get(state_key, {}).get("state", {})
		volume_field = _volume_field(after_values)
		if volume_field is None:
			continue
		unit = state_map.get_state_field_unit(state_key, volume_field)
		before_amount = _normalise_volume(
			before_values.get(volume_field, state_map.get_state_field_default(state_key, volume_field)), unit
		)
		after_amount = _normalise_volume(after_values.get(volume_field), unit)
		if before_amount is None or after_amount is None:
			continue
		delta = after_amount - before_amount
		if delta < 0:
			factor = fanout_members if volume_field == "held_material_volume" else 1
			decrease_total += -delta * factor
			continue
		if delta <= 0 or volume_field != "material_volume":
			continue
		before_identity = _material_identity(before_values)
		after_identity = _material_identity(after_values)
		# A vessel that already contains material may legitimately become a
		# mixture/reaction product; its identity is explicit authoring, not a
		# fabricated liquid transfer.
		if before_identity not in (None, "empty") and before_identity != after_identity:
			continue
		increase_total += delta
		increase_targets.append(state_key)

	if increase_total > decrease_total + 1e-8:
		for target in increase_targets:
			_emit_ledger_error(
				emitter, protocol_name, step_name, interaction_index, target,
				"unbalanced_material_volume_creation",
				f"material volume increased by {increase_total:g} uL with only {decrease_total:g} uL of explicit source/tool decrease",
			)


#============================================

def detect_state_jumps(
	before_state: dict,
	after_state: dict,
	scene_ops: list,
	state_map: StateMap,
	protocol_name: str,
	step_name: str,
	interaction_index: int,
	emitter: FindingEmitter,
) -> None:
	"""
	Detect S-STATE-JUMP violations: field increases with no matching decrease.

	Compares before_state and after_state snapshots. For each field that
	increased, checks whether any scene_op in the same interaction decremented
	that field on ANY placement. Emits WARNING if increase found with no
	corresponding decrease.

	Suppressions:
	  - TimedWait ops (skip S-STATE-JUMP if ANY op in the interaction is TimedWait)
	  - Initial state writes (old == declared default, skip the check)
	  - Plate-subpart dotted targets (well_plate_96.A1) when parent is conserved

	Args:
		before_state: Snapshot before interaction (placement -> {state fields}).
		after_state: Snapshot after interaction (placement -> {state fields}).
		scene_ops: List of scene operations in the interaction.
		state_map: StateMap (for field defaults and object metadata).
		protocol_name: Protocol name for finding.
		step_name: Step name for finding.
		interaction_index: Interaction index for finding.
		emitter: FindingEmitter for recording findings.
	"""
	# Suppression 1: skip if ANY op is TimedWait
	# Incubator-driven state change (e.g., formazan conversion) is intentional, not a transfer bug
	has_timed_wait = any(op.get("type") == "TimedWait" for op in scene_ops)
	if has_timed_wait:
		return

	# Operations name semantic object/subpart targets, while snapshots use the
	# stable state key.  Normalize once so an explicit write never becomes a
	# spurious implicit state jump merely because its scene placement differs.
	explicit_state_keys: set[str] = set()
	for scene_op in scene_ops:
		if scene_op.get("type") == "ObjectStateChange":
			target = scene_op.get("target")
			if isinstance(target, str):
				explicit_state_keys.update(state_map.explicit_state_keys_for_target(target))

	# Iterate through all placements to detect increases
	for placement_name in after_state.keys():
		if placement_name in explicit_state_keys:
			continue
		old_state = before_state.get(placement_name, {}).get("state", {})
		new_state = after_state.get(placement_name, {}).get("state", {})

		for field_name, new_value in new_state.items():
			old_value = old_state.get(field_name)

			# Suppression 2: skip initial state writes (old == default)
			# Initialization is not a transfer; the field starts uninitialized in the simulator's eyes.
			# A subpart record (composite key 'placement.subpart') resolves the
			# applies_to: subpart decl so its default is read from the right scope.
			object_name = after_state[placement_name]["object_name"]
			is_subpart_record = "." in placement_name
			field_decl = state_map.tree.get_state_field(
				object_name, field_name, subpart_targeted=is_subpart_record
			)
			if field_decl and old_value == field_decl.get("default"):
				continue

			# Check for volume increase
			if field_name in ("material_volume", "held_material_volume"):
				if isinstance(old_value, (int, float)) and isinstance(new_value, (int, float)):
					if new_value > old_value:
						# Volume increased. Check if any placement had a decrement
						has_decrement = False
						for other_placement in after_state.keys():
							other_old = before_state.get(other_placement, {}).get("state", {}).get(field_name)
							other_new = after_state.get(other_placement, {}).get("state", {}).get(field_name)
							if isinstance(other_old, (int, float)) and isinstance(other_new, (int, float)):
								if other_new < other_old:
									has_decrement = True
									break

						if not has_decrement:
							# Suppression 3: check if this is a plate subpart
							# Subpart writes partition a parent total across wells; suppressing when the parent total stays conserved
							is_plate_subpart = "." in placement_name
							if is_plate_subpart:
								# Extract parent object name
								parent_name = placement_name.split(".")[0]
								# Check if parent was conserved (no volume change)
								parent_conserved = True
								for p in after_state.keys():
									if p == parent_name or p.startswith(parent_name + "."):
										p_old = before_state.get(p, {}).get("state", {}).get(field_name)
										p_new = after_state.get(p, {}).get("state", {}).get(field_name)
										if isinstance(p_old, (int, float)) and isinstance(p_new, (int, float)):
											if p_old != p_new and p != placement_name:
												parent_conserved = False
												break
								if parent_conserved:
									continue

							# Emit S-STATE-JUMP finding
							# WARNING (not ERROR) pending zero false positives across two consecutive validate.py runs; see plan promotion condition
							emitter.emit_finding(Finding(
								level=Level.WARNING,
								protocol_name=protocol_name,
								step_name=step_name,
								interaction_index=interaction_index,
								target=placement_name,
								file_path="unknown",
								code="s-state-jump",
								message=f"placement '{placement_name}' field '{field_name}' increased from {old_value} to {new_value} with no matching decrement in same interaction",
								spec_cite="docs/specs/MATERIAL_CONVENTION.md material conservation",
							))

			# Check for material identity change (material_name or held_material_name)
			elif field_name in ("material_name", "held_material_name"):
				if old_value != new_value and old_value is not None:
					# Suppression: initialization is not a transfer; the field starts
					# uninitialized in the simulator's eyes. A subpart record resolves
					# the applies_to: subpart decl so its default is the right scope.
					field_decl = state_map.tree.get_state_field(
						object_name, field_name, subpart_targeted=is_subpart_record
					)
					if field_decl and old_value == field_decl.get("default"):
						continue

					# This branch now covers only changes without a normalized explicit
					# ObjectStateChange target.
					if placement_name not in explicit_state_keys:
						# Emit S-STATE-JUMP finding
						emitter.emit_finding(Finding(
							level=Level.WARNING,
							protocol_name=protocol_name,
							step_name=step_name,
							interaction_index=interaction_index,
							target=placement_name,
							file_path="unknown",
							code="s-state-jump",
							message=f"placement '{placement_name}' field '{field_name}' changed from '{old_value}' to '{new_value}' without transfer op",
							spec_cite="docs/specs/MATERIAL_CONVENTION.md material identity",
						))
