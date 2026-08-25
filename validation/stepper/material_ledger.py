"""Material-conservation checks for protocol stepper state transitions."""

import validation.stepper.findings
import validation.stepper.state


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
	emitter: validation.stepper.findings.FindingEmitter,
	protocol_name: str,
	step_name: str,
	interaction_index: int,
	target: str,
	code: str,
	message: str,
) -> None:
	"""Emit one contextual material-accounting failure."""
	emitter.emit_finding(validation.stepper.findings.Finding(
		level=validation.stepper.findings.Level.ERROR, protocol_name=protocol_name, step_name=step_name,
		interaction_index=interaction_index, target=target, file_path="unknown",
		code=code, message=message,
		spec_cite="docs/specs/OBJECT_YAML_FORMAT.md Material containers",
	))


def validate_material_ledger(
	before_state: dict,
	after_state: dict,
	state_map: validation.stepper.state.StateMap,
	protocol_name: str,
	step_name: str,
	interaction_index: int,
	emitter: validation.stepper.findings.FindingEmitter,
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
	state_map: validation.stepper.state.StateMap,
	protocol_name: str,
	step_name: str,
	interaction_index: int,
	emitter: validation.stepper.findings.FindingEmitter,
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
