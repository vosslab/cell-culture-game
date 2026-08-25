"""Protocol stepper runner: orchestrates loader, flow, state, and scene_ops."""

import validation.stepper.findings
import validation.stepper.loader
import validation.stepper.flow
import validation.stepper.state
import validation.stepper.scene_ops
import validation.stepper.material_ledger
import validation.stepper.cross_mini
from validation.shared_toolkit.discovery import construct_protocol_scene_path


def _try_construct_scene_path(
	tree: validation.stepper.loader.LoadedContentTree,
	protocol_name: str,
	scene_name: str,
) -> str | None:
	"""
	Attempt to construct a scene path, returning None if resolution fails.

	Helper to reduce try/except duplication in _seed_initial_active_scene.
	"""
	try:
		return construct_protocol_scene_path(tree.root_path / "content" / "protocols", protocol_name, scene_name)
	except RuntimeError:
		return None


def _activate_declared_scene(
	tree: validation.stepper.loader.LoadedContentTree,
	protocol_name: str,
	step: dict,
	state_map: validation.stepper.state.StateMap,
) -> bool:
	"""Activate a step's declared scene using the same entry rule as runtime."""
	scene_name = step.get("scene")
	if not isinstance(scene_name, str) or not scene_name:
		return False
	if scene_name in tree.base_scenes:
		state_map.set_active_scene(scene_name, f"content/base_scenes/{scene_name}.yaml")
		return True
	protocol_local_scenes = tree.protocol_local_scenes.get(protocol_name, {})
	if scene_name not in protocol_local_scenes:
		return False
	scene_path = _try_construct_scene_path(tree, protocol_name, scene_name)
	if scene_path is None:
		return False
	state_map.set_active_scene(scene_name, scene_path)
	return True


def _check_flow_integrity_mini(
	protocol: dict,
	protocol_path: str,
	emitter: validation.stepper.findings.FindingEmitter,
) -> bool:
	"""
	Check for S-UNREACHABLE and S-CYCLE in a mini-protocol.

	Performs a linear walk from entry_step through next_step chain,
	tracking visited steps. Emits S-CYCLE on revisit (and halts further
	checks for this protocol). Emits S-UNREACHABLE post-walk for any
	declared steps not visited (only if S-CYCLE did not fire).

	Args:
		protocol: Protocol dict with entry_step and steps list.
		protocol_path: Path to the protocol YAML file.
		emitter: FindingEmitter for recording findings.

	Returns:
		True if S-CYCLE was detected, False otherwise.
	"""
	protocol_name = protocol["protocol_name"]
	entry_step_name = protocol.get("entry_step")
	steps_list = protocol.get("steps", [])

	# Build name -> step dict for fast lookup
	steps_by_name = {}
	for step in steps_list:
		step_name = step.get("step_name")
		if step_name:
			steps_by_name[step_name] = step

	# Exit early if entry_step is invalid (flow.py will emit entry_step errors)
	if not entry_step_name or entry_step_name not in steps_by_name:
		return False

	# Walk the chain tracking visited steps
	visited = set()
	current_step_name = entry_step_name
	cycle_detected = False

	while current_step_name is not None:
		# Check for cycle
		if current_step_name in visited:
			finding = validation.stepper.findings.Finding(
				level=validation.stepper.findings.Level.ERROR,
				protocol_name=protocol_name,
				step_name=current_step_name,
				interaction_index=None,
				target=None,
				file_path=protocol_path,
				code="s-cycle",
				message=f"step '{current_step_name}' forms a cycle in next_step chain",
				spec_cite="docs/PRIMARY_SPEC.md Protocol step structure"
			)
			emitter.emit_finding(finding)
			cycle_detected = True
			break

		visited.add(current_step_name)

		# Get next step
		if current_step_name not in steps_by_name:
			# Should not happen if entry_step validation passed, but be safe
			break
		current_step = steps_by_name[current_step_name]
		current_step_name = current_step.get("next_step")

	# Emit S-UNREACHABLE for steps not visited (only if no cycle)
	if not cycle_detected:
		unreachable = set(steps_by_name.keys()) - visited
		for unreachable_step_name in sorted(unreachable):
			finding = validation.stepper.findings.Finding(
				level=validation.stepper.findings.Level.ERROR,
				protocol_name=protocol_name,
				step_name=unreachable_step_name,
				interaction_index=None,
				target=None,
				file_path=protocol_path,
				code="s-unreachable",
				message=f"step '{unreachable_step_name}' is declared but unreachable from entry_step",
				spec_cite="docs/PRIMARY_SPEC.md Entry step"
			)
			emitter.emit_finding(finding)

	return cycle_detected


#============================================

def walk_protocol(
	tree: validation.stepper.loader.LoadedContentTree,
	protocol_name: str,
	verbose: bool = False,
	quiet: bool = False,
) -> tuple[int, int, validation.stepper.findings.FindingEmitter]:
	"""
	Walk a single protocol through the entire flow.

	Loads the protocol, initializes StateMap and FindingEmitter,
	walks all interactions via flow.walk_mini_protocol(), applies
	scene operations, and returns interaction count and the emitter.

	Args:
		tree: LoadedContentTree instance.
		protocol_name: Name of the protocol to walk.
		verbose: If True, emit per-step state deltas.
		quiet: If True, suppress the per-protocol summary line and the
			inline finding dump. The CLI uses this when it intends to
			render findings via the grouped dashboard instead.

	Returns:
		(step_count, interaction_count, emitter) tuple.
	"""
	protocol = tree.get_protocol(protocol_name)
	# Construct path from protocol name if not set
	protocol_path = protocol.get("_file_path", f"content/protocols/{protocol_name}/protocol.yaml")

	emitter = validation.stepper.findings.FindingEmitter(verbose=verbose)
	state_map = validation.stepper.state.StateMap(tree, protocol_name, emitter)

	# Seed the initial active scene
	_seed_initial_active_scene(tree, protocol_name, state_map, emitter)
	state_map.apply_initial_state(protocol.get("initial_state"))

	emitter.emit_protocol_start(protocol_name, protocol_path)

	# Check flow integrity (S-UNREACHABLE, S-CYCLE) early
	_check_flow_integrity_mini(protocol, protocol_path, emitter)

	step_count = 0
	interaction_count = 0
	visited_steps = set()

	for step, interaction_index, interaction in validation.stepper.flow.walk_mini_protocol(protocol, emitter):
		step_name = step.get("step_name")

		# Count unique steps
		if step_name not in visited_steps:
			visited_steps.add(step_name)
			step_count += 1
			_activate_declared_scene(tree, protocol_name, step, state_map)
			emitter.emit_step_transition(step_name)

		interaction_count += 1

		# Apply scene operations in the interaction's response
		response = interaction.get("response", {})
		scene_ops = response.get("scene_operations", [])

		# Snapshot state before applying ops (for S-STATE-JUMP detection)
		state_before = state_map.snapshot_state()

		for scene_op in scene_ops:
			op_type = scene_op.get("type")
			emitter.emit_scene_operation(op_type)

			validation.stepper.scene_ops.apply_scene_operation(
				scene_op,
				state_map,
				protocol_name,
				step_name,
				interaction_index,
				emitter,
				tree,
			)

		# Snapshot state after applying ops and detect state jumps
		state_after = state_map.snapshot_state()
		validation.stepper.scene_ops.detect_state_jumps(
			state_before,
			state_after,
			scene_ops,
			state_map,
			protocol_name,
			step_name,
			interaction_index,
			emitter,
		)
		validation.stepper.material_ledger.validate_material_ledger(
			state_before, state_after, state_map, protocol_name, step_name, interaction_index, emitter, scene_ops
		)
		validation.stepper.material_ledger.detect_material_volume_creation(
			state_before, state_after, scene_ops, state_map, protocol_name, step_name, interaction_index, emitter
		)

	# Count errors and warnings from emitter
	emitter.final_state = state_map.snapshot_state()
	error_findings = [f for f in emitter.findings if f.level == validation.stepper.findings.Level.ERROR]
	warning_findings = [f for f in emitter.findings if f.level == validation.stepper.findings.Level.WARNING]
	error_count = len(error_findings)
	warning_count = len(warning_findings)

	if not quiet:
		emitter.emit_protocol_summary(protocol_name, protocol_path, step_count, interaction_count, error_count, warning_count)
		emitter.print_findings()

	return step_count, interaction_count, emitter


#============================================

def _seed_initial_active_scene(
	tree: validation.stepper.loader.LoadedContentTree,
	protocol_name: str,
	state_map: validation.stepper.state.StateMap,
	emitter: validation.stepper.findings.FindingEmitter,
) -> None:
	"""
	Seed the initial active scene for a protocol.

	Strategy:
	  1. Use the entry step's declared scene, matching browser runtime entry.
	  2. Otherwise scan the first SceneChange operation for an explicit scene.
	  3. If no explicit SceneChange, try protocol-local scenes:
	     a. If protocol has exactly one local scene, use it.
	     b. If protocol has multiple local scenes, try to find one that contains targets from the first step.
	  4. Fall back to the first base scene.
	  5. If no scene found, emit a WARNING but leave active_scene unset
	     (subsequent target resolutions will emit errors).

	Args:
		tree: LoadedContentTree instance.
		protocol_name: Name of the active protocol.
		state_map: StateMap to seed with active scene.
		emitter: FindingEmitter for recording warnings.
	"""
	protocol = tree.get_protocol(protocol_name)
	if not protocol:
		return

	steps = protocol.get("steps", [])
	entry_step_name = protocol.get("entry_step")
	for step in steps:
		if isinstance(step, dict) and step.get("step_name") == entry_step_name:
			if _activate_declared_scene(tree, protocol_name, step, state_map):
				return
			break

	# Strategy 2: Look for the first SceneChange in the protocol
	for step in steps:
		if not isinstance(step, dict):
			continue
		sequence = step.get("sequence", [])
		if not isinstance(sequence, list):
			continue
		for interaction in sequence:
			if not isinstance(interaction, dict):
				continue
			response = interaction.get("response", {})
			if not isinstance(response, dict):
				continue
			scene_ops = response.get("scene_operations", [])
			if not isinstance(scene_ops, list):
				continue
			for scene_op in scene_ops:
				if not isinstance(scene_op, dict):
					continue
				if scene_op.get("type") == "SceneChange":
					to_scene = scene_op.get("to_scene")
					if to_scene:
						# Found an explicit scene
						if to_scene in tree.base_scenes:
							state_map.set_active_scene(to_scene, f"content/base_scenes/{to_scene}.yaml")
							return
						else:
							protocol_local_scenes = tree.protocol_local_scenes.get(protocol_name, {})
							if to_scene in protocol_local_scenes:
								scene_path = _try_construct_scene_path(tree, protocol_name, to_scene)
								if scene_path:
									state_map.set_active_scene(to_scene, scene_path)
									return

	# Strategy 3: Check protocol-local scenes
	protocol_local_scenes = tree.protocol_local_scenes.get(protocol_name, {})
	if protocol_local_scenes:
		# If exactly one local scene, use it
		if len(protocol_local_scenes) == 1:
			scene_name = list(protocol_local_scenes.keys())[0]
			scene_path = _try_construct_scene_path(tree, protocol_name, scene_name)
			if scene_path:
				state_map.set_active_scene(scene_name, scene_path)
				return

		# If multiple local scenes, try to find one with targets from the first step
		if len(protocol_local_scenes) > 1:
			# Collect targets from the first step
			first_targets = set()
			for step in steps:
				if isinstance(step, dict) and step.get("step_name") == entry_step_name:
					sequence = step.get("sequence", [])
					if isinstance(sequence, list):
						for interaction in sequence:
							if isinstance(interaction, dict):
								target = interaction.get("target")
								if target:
									# Strip subpart (e.g., "well_plate_96.A1" -> "well_plate_96")
									first_targets.add(target.split(".")[0])
					break

			# Find a scene that contains at least one target
			for scene_name, scene_data in protocol_local_scenes.items():
				placements = scene_data.get("placements", [])
				if not isinstance(placements, list):
					placements = []
				extends = scene_data.get("extends")
				if extends and extends in tree.base_scenes:
					base_placements = tree.base_scenes[extends].get("placements", [])
					if isinstance(base_placements, list):
						placements = list(base_placements) + placements

				# Check for matching object_names
				scene_objects = {p.get("object_name") for p in placements if isinstance(p, dict)}
				if first_targets & scene_objects:  # Intersection found
					scene_path = _try_construct_scene_path(tree, protocol_name, scene_name)
					if scene_path:
						state_map.set_active_scene(scene_name, scene_path)
						return

			# No matching scene found; use the first local scene
			scene_name = sorted(protocol_local_scenes.keys())[0]
			scene_path = _try_construct_scene_path(tree, protocol_name, scene_name)
			if scene_path:
				state_map.set_active_scene(scene_name, scene_path)
				return

	# Strategy 4: Use the first base scene
	if tree.base_scenes:
		first_scene_name = sorted(tree.base_scenes.keys())[0]
		state_map.set_active_scene(first_scene_name, f"content/base_scenes/{first_scene_name}.yaml")
		return

	# No default scene found
	emitter.emit_finding(validation.stepper.findings.Finding(
		level=validation.stepper.findings.Level.WARNING,
		protocol_name=protocol_name,
		step_name=None,
		interaction_index=None,
		target=None,
		file_path=protocol.get("_file_path", "unknown"),
		code="no_initial_scene_found",
		message=f"Could not determine initial active scene for protocol '{protocol_name}': no explicit SceneChange found and no scenes available",
		spec_cite="docs/PRIMARY_SPEC.md Entry step",
	))

#============================================

def discover_mini_protocols(tree: validation.stepper.loader.LoadedContentTree) -> list[str]:
	"""
	Discover all mini_protocol-type protocols in the loaded tree.

	Returns:
		Sorted list of protocol names with protocol_type: mini_protocol.
	"""
	mini_protocols = []
	for protocol_name, protocol_data in tree.protocols.items():
		protocol_type = protocol_data.get("protocol_type")
		if protocol_type == "mini_protocol":
			mini_protocols.append(protocol_name)
	return sorted(mini_protocols)


#============================================

def discover_sequence_runners(tree: validation.stepper.loader.LoadedContentTree) -> list[str]:
	"""
	Discover all sequence_runner-type protocols in the loaded tree.

	Returns:
		Sorted list of protocol names with protocol_type: sequence_runner.
	"""
	sequence_runners = []
	for protocol_name, protocol_data in tree.protocols.items():
		protocol_type = protocol_data.get("protocol_type")
		if protocol_type == "sequence_runner":
			sequence_runners.append(protocol_name)
	return sorted(sequence_runners)


#============================================

def walk_sequence_runner(
	tree: validation.stepper.loader.LoadedContentTree,
	protocol_name: str,
	verbose: bool = False,
	quiet: bool = False,
) -> tuple[int, int, validation.stepper.findings.FindingEmitter]:
	"""
	Walk a sequence runner by executing its constituent minis in order.

	Threads a single StateMap across all constituent minis so state persists
	from one mini to the next. Detects runner-of-runner and checks cross-mini
	material production gaps via the generalized production check.

	Args:
		tree: LoadedContentTree instance.
		protocol_name: Name of the sequence runner to walk.
		verbose: If True, emit per-step state deltas.

	Returns:
		(total_leaf_count, total_interaction_count, emitter) tuple.
	"""
	protocol = tree.get_protocol(protocol_name)
	# Construct path from protocol name if not set
	protocol_path = protocol.get("_file_path", f"content/protocols/{protocol_name}/protocol.yaml")

	emitter = validation.stepper.findings.FindingEmitter(verbose=verbose)

	# Validate protocol_type is sequence_runner
	protocol_type = protocol.get("protocol_type")
	if protocol_type != "sequence_runner":
		emitter.emit_finding(validation.stepper.findings.Finding(
			level=validation.stepper.findings.Level.ERROR,
			protocol_name=protocol_name,
			step_name=None,
			interaction_index=None,
			target=None,
			file_path=protocol_path,
			code="not_sequence_runner",
			message=f"protocol_type is '{protocol_type}', not 'sequence_runner'",
			spec_cite="docs/PRIMARY_SPEC.md Protocol types",
		))
		return 0, 0, emitter

	# A runner is an ordered, non-empty list of unique direct mini leaves.  The
	# runtime has the same requirement; retain it here so validation remains
	# trustworthy when invoked without the schema gate.
	mini_protocols = protocol.get("mini_protocols")
	if not isinstance(mini_protocols, list) or not mini_protocols:
		emitter.emit_finding(validation.stepper.findings.Finding(
			level=validation.stepper.findings.Level.ERROR,
			protocol_name=protocol_name, step_name=None, interaction_index=None,
			target=None, file_path=protocol_path, code="invalid_sequence_runner_members",
			message="sequence_runner mini_protocols must be a non-empty ordered list",
			spec_cite="docs/PRIMARY_SPEC.md Sequence runners",
		))
		return 0, 0, emitter
	if any(not isinstance(mini_name, str) or not mini_name for mini_name in mini_protocols):
		emitter.emit_finding(validation.stepper.findings.Finding(
			level=validation.stepper.findings.Level.ERROR,
			protocol_name=protocol_name, step_name=None, interaction_index=None,
			target=None, file_path=protocol_path, code="invalid_sequence_runner_members",
			message="sequence_runner mini_protocols must contain only non-empty protocol names",
			spec_cite="docs/PRIMARY_SPEC.md Sequence runners",
		))
		return 0, 0, emitter
	duplicates = sorted({name for name in mini_protocols if mini_protocols.count(name) > 1})
	if duplicates:
		emitter.emit_finding(validation.stepper.findings.Finding(
			level=validation.stepper.findings.Level.ERROR,
			protocol_name=protocol_name, step_name=None, interaction_index=None,
			target=duplicates[0], file_path=protocol_path, code="duplicate_runner_constituent",
			message=f"sequence_runner repeats constituent mini-protocol(s): {', '.join(duplicates)}",
			spec_cite="docs/PRIMARY_SPEC.md Sequence runners",
		))
		return 0, 0, emitter

	# Reject unknown and nested constituents before walking.  Continuing would
	# manufacture a partial runner result that looks like a successful check.
	invalid_members = False
	for mini_name in mini_protocols:
		try:
			mini_proto = tree.get_protocol(mini_name)
		except validation.stepper.loader.ProtocolNotFoundError:
			emitter.emit_finding(validation.stepper.findings.Finding(
				level=validation.stepper.findings.Level.ERROR,
				protocol_name=protocol_name,
				step_name=None,
				interaction_index=None,
				target=mini_name,
				file_path=protocol_path,
				code="unknown_mini_protocol",
				message=f"mini_protocols list references unknown protocol '{mini_name}'",
				spec_cite="docs/PRIMARY_SPEC.md Sequence runners",
			))
			invalid_members = True
			continue

		mini_type = mini_proto.get("protocol_type")
		if mini_type == "sequence_runner":
			emitter.emit_finding(validation.stepper.findings.Finding(
				level=validation.stepper.findings.Level.ERROR,
				protocol_name=protocol_name,
				step_name=None,
				interaction_index=None,
				target=mini_name,
				file_path=protocol_path,
				code="runner_of_runner",
				message=f"sequence runner '{protocol_name}' references another sequence_runner '{mini_name}' in mini_protocols list",
				spec_cite="docs/PRIMARY_SPEC.md Sequence runners",
			))
			invalid_members = True
		elif mini_type != "mini_protocol":
			emitter.emit_finding(validation.stepper.findings.Finding(
				level=validation.stepper.findings.Level.ERROR,
				protocol_name=protocol_name, step_name=None, interaction_index=None,
				target=mini_name, file_path=protocol_path, code="invalid_runner_constituent",
				message=f"runner constituent '{mini_name}' has protocol_type '{mini_type}', not 'mini_protocol'",
				spec_cite="docs/PRIMARY_SPEC.md Sequence runners",
			))
			invalid_members = True
	if invalid_members:
		return 0, 0, emitter

	emitter.emit_protocol_start(protocol_name, protocol_path, is_sequence_runner=True, leaf_count=len(mini_protocols))

	# Build upstream materials once, then thread through each mini
	produced_materials, declared_materials_by_mini = validation.stepper.cross_mini.build_upstream_materials(
		tree,
		mini_protocols,
		emitter,
	)

	total_leaf_count = len(mini_protocols)
	total_interaction_count = 0
	total_step_count = 0
	accumulated_produced_materials = set()
	declared_union = set().union(*declared_materials_by_mini.values())
	state_map = validation.stepper.state.StateMap(
		tree, protocol_name, emitter, declared_materials_union=declared_union,
		scene_protocol_names=mini_protocols, material_protocol_names=mini_protocols,
	)
	state_map.set_execution_protocol(mini_protocols[0])
	_seed_initial_active_scene(tree, mini_protocols[0], state_map, emitter)
	state_map.apply_initial_state(protocol.get("initial_state"))

	# Walk each mini in order, threading state and materials
	for mini_index, mini_name in enumerate(mini_protocols):
		try:
			mini_protocol = tree.get_protocol(mini_name)
		except validation.stepper.loader.ProtocolNotFoundError:
			continue

		state_map.set_execution_protocol(mini_name)
		state_map.produced_materials_set = accumulated_produced_materials
		# Constituent initial_state is deliberately ignored: runner root state is
		# the only seed for a multi-mini session.
		_seed_initial_active_scene(tree, mini_name, state_map, emitter)

		step_count = 0
		interaction_count = 0
		visited_steps = set()

		for step, interaction_index, interaction in validation.stepper.flow.walk_mini_protocol(mini_protocol, emitter):
			step_name = step.get("step_name")

			# Count unique steps
			if step_name not in visited_steps:
				visited_steps.add(step_name)
				step_count += 1
				_activate_declared_scene(tree, mini_name, step, state_map)
				emitter.emit_step_transition(step_name)

			interaction_count += 1

			# Apply scene operations
			response = interaction.get("response", {})
			scene_ops = response.get("scene_operations", [])

			state_before = state_map.snapshot_state()
			for scene_op in scene_ops:
				op_type = scene_op.get("type")
				emitter.emit_scene_operation(op_type)

				validation.stepper.scene_ops.apply_scene_operation(
					scene_op,
					state_map,
					mini_name,
					step_name,
					interaction_index,
					emitter,
					tree,
				)

				# Track produced materials
				if op_type == "ObjectStateChange":
					state_block = scene_op.get("state", {})
					if isinstance(state_block, dict):
						for field_name in ("material_name", "held_material_name"):
							value = state_block.get(field_name)
							if value and isinstance(value, str) and value not in ("empty", "mixed"):
								accumulated_produced_materials.add(value)

			state_after = state_map.snapshot_state()
			validation.stepper.scene_ops.detect_state_jumps(
				state_before, state_after, scene_ops, state_map, mini_name, step_name,
				interaction_index, emitter,
			)
			validation.stepper.material_ledger.validate_material_ledger(
				state_before, state_after, state_map, mini_name, step_name, interaction_index, emitter, scene_ops
			)
			validation.stepper.material_ledger.detect_material_volume_creation(
				state_before, state_after, scene_ops, state_map, mini_name, step_name, interaction_index, emitter
			)

		# Check cross-mini material references for this mini
		validation.stepper.cross_mini.check_cross_mini_material_references(
			tree,
			mini_name,
			mini_index,
			mini_protocols,
			accumulated_produced_materials,
			declared_materials_by_mini,
			emitter,
		)

		total_step_count += step_count
		total_interaction_count += interaction_count

		# Emit per-mini result
		error_findings = [f for f in emitter.findings if f.level == validation.stepper.findings.Level.ERROR]
		warning_findings = [f for f in emitter.findings if f.level == validation.stepper.findings.Level.WARNING]
		error_count = len(error_findings)
		warning_count = len(warning_findings)

		if not quiet:
			emitter.emit_leaf_summary(mini_name, step_count, interaction_count, error_count, warning_count)

	# Final summary for the sequence runner
	emitter.final_state = state_map.snapshot_state()
	error_findings = [f for f in emitter.findings if f.level == validation.stepper.findings.Level.ERROR]
	warning_findings = [f for f in emitter.findings if f.level == validation.stepper.findings.Level.WARNING]
	error_count = len(error_findings)
	warning_count = len(warning_findings)

	if not quiet:
		emitter.emit_sequence_runner_summary(protocol_name, protocol_path, total_leaf_count, total_step_count, total_interaction_count, error_count, warning_count)
		emitter.print_findings()

	return total_leaf_count, total_interaction_count, emitter
