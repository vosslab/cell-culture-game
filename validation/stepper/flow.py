"""Flow engine for stepping through protocol entry and next_step chains."""

import validation.stepper.findings


def walk_mini_protocol(protocol: dict, emitter: validation.stepper.findings.FindingEmitter) -> None:
	"""
	Walk a mini-protocol from entry_step through next_step chain.

	Yields (step, interaction_index, interaction) triples in entry_step -> next_step order.
	Emits ERROR findings on:
	  - Missing or unresolved entry_step
	  - Broken next_step references
	  - Cycles (detected via visited set on step_name)
	  - Unreachable steps (declared in steps list but never reached)
	  - Multiple terminal steps (more than one step with next_step: null)

	Args:
		protocol: Protocol dict with keys: protocol_name, entry_step, steps (list of dicts)
		emitter: FindingEmitter for recording findings

	Yields:
		(step_dict, interaction_index: int, interaction_dict) tuples
	"""
	protocol_name = protocol.get("protocol_name", "unknown")
	entry_step_name = protocol.get("entry_step")
	steps_list = protocol.get("steps", [])

	# Build name -> step dict for fast lookup
	steps_by_name = {}
	for step in steps_list:
		step_name = step.get("step_name")
		if step_name:
			steps_by_name[step_name] = step

	# Check: entry_step exists and is resolvable
	if not entry_step_name:
		finding = validation.stepper.findings.Finding(
			level=validation.stepper.findings.Level.ERROR,
			protocol_name=protocol_name,
			step_name=None,
			interaction_index=None,
			target=None,
			file_path=protocol.get("_file_path", "<unknown>"),
			code="entry_step_missing",
			message="entry_step not declared or is empty",
			spec_cite="docs/specs/PROTOCOL_VOCABULARY.md entry_step"
		)
		emitter.emit_finding(finding)
		return

	if entry_step_name not in steps_by_name:
		finding = validation.stepper.findings.Finding(
			level=validation.stepper.findings.Level.ERROR,
			protocol_name=protocol_name,
			step_name=entry_step_name,
			interaction_index=None,
			target=None,
			file_path=protocol.get("_file_path", "<unknown>"),
			code="entry_step_not_found",
			message=f"entry_step '{entry_step_name}' not found in steps list",
			spec_cite="docs/specs/PROTOCOL_VOCABULARY.md entry_step"
		)
		emitter.emit_finding(finding)
		return

	# Walk the flow: entry_step -> next_step chain
	visited = set()
	current_step_name = entry_step_name
	terminal_steps = set()

	while current_step_name is not None:
		# Cycle detection
		if current_step_name in visited:
			finding = validation.stepper.findings.Finding(
				level=validation.stepper.findings.Level.ERROR,
				protocol_name=protocol_name,
				step_name=current_step_name,
				interaction_index=None,
				target=None,
				file_path=protocol.get("_file_path", "<unknown>"),
				code="flow_cycle",
				message=f"step '{current_step_name}' forms a cycle in next_step chain",
				spec_cite="docs/specs/PROTOCOL_VOCABULARY.md next_step"
			)
			emitter.emit_finding(finding)
			return

		visited.add(current_step_name)

		# Get the current step
		if current_step_name not in steps_by_name:
			finding = validation.stepper.findings.Finding(
				level=validation.stepper.findings.Level.ERROR,
				protocol_name=protocol_name,
				step_name=current_step_name,
				interaction_index=None,
				target=None,
				file_path=protocol.get("_file_path", "<unknown>"),
				code="broken_next_step",
				message=f"next_step references '{current_step_name}' which is not in steps list",
				spec_cite="docs/specs/PROTOCOL_VOCABULARY.md next_step"
			)
			emitter.emit_finding(finding)
			return

		current_step = steps_by_name[current_step_name]

		# Yield each interaction in this step's sequence
		sequence = current_step.get("sequence", [])
		for interaction_index, interaction in enumerate(sequence):
			yield (current_step, interaction_index, interaction)

		# Get the next step
		next_step_name = current_step.get("next_step")
		if next_step_name is None:
			terminal_steps.add(current_step_name)

		current_step_name = next_step_name

	# Check for unreachable steps (in list but never visited)
	unreachable = set(steps_by_name.keys()) - visited
	if unreachable:
		for unreachable_step_name in sorted(unreachable):
			finding = validation.stepper.findings.Finding(
				level=validation.stepper.findings.Level.ERROR,
				protocol_name=protocol_name,
				step_name=unreachable_step_name,
				interaction_index=None,
				target=None,
				file_path=protocol.get("_file_path", "<unknown>"),
				code="flow_unreachable_step",
				message=f"step '{unreachable_step_name}' is declared but unreachable from entry_step",
				spec_cite="docs/specs/PROTOCOL_VOCABULARY.md next_step"
			)
			emitter.emit_finding(finding)

	# Check for multiple terminal steps
	if len(terminal_steps) != 1:
		term_list = ", ".join(sorted(terminal_steps)) if terminal_steps else "(none)"
		finding = validation.stepper.findings.Finding(
			level=validation.stepper.findings.Level.ERROR,
			protocol_name=protocol_name,
			step_name=None,
			interaction_index=None,
			target=None,
			file_path=protocol.get("_file_path", "<unknown>"),
			code="flow_multi_terminal",
			message=f"protocol has {len(terminal_steps)} terminal step(s): {term_list} (expected exactly 1)",
			spec_cite="docs/specs/PROTOCOL_VOCABULARY.md next_step"
		)
		emitter.emit_finding(finding)
