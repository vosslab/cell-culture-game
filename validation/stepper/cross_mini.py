"""Cross-mini material production check for sequence runners."""

from validation.stepper.findings import Finding, Level


def build_upstream_materials(
	tree: object,
	sequence_runner_minis: list[str],
	emitter: object,
) -> tuple[set, dict]:
	"""
	Build the set of upstream-produced materials and declared input materials.

	Walks through all minis M in sequence_runner_minis and returns:
	  - produced_materials: set of material names written via ObjectStateChange
	  - declared_materials: dict mapping mini_index -> set of declared input material names

	Args:
		tree: LoadedContentTree instance.
		sequence_runner_minis: Ordered list of mini protocol names.
		emitter: FindingEmitter for diagnostics.

	Returns:
		(produced_materials: set[str], declared_materials_by_mini: dict[int, set[str]])
	"""
	produced_materials = set()
	declared_materials_by_mini = {}

	for mini_index, mini_name in enumerate(sequence_runner_minis):
		# Collect materials declared as inputs in this mini's materials.yaml
		declared_in_mini = set()
		materials = tree.get_protocol_materials(mini_name)
		for material_name, material_data in materials.items():
			# Treat all declared materials as potentially produced upstream
			# (they are inputs to this mini)
			declared_in_mini.add(material_name)

		declared_materials_by_mini[mini_index] = declared_in_mini

		# Collect materials produced (written) via ObjectStateChange in this mini
		protocol = tree.get_protocol(mini_name)
		steps = protocol.get("steps", [])
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
					# Only ObjectStateChange writes material state
					if scene_op.get("type") == "ObjectStateChange":
						state_block = scene_op.get("state", {})
						if not isinstance(state_block, dict):
							continue
						# Collect write-side material names
						for field_name in ("material_name", "held_material_name"):
							value = state_block.get(field_name)
							if value and isinstance(value, str):
								# Exclude sentinels
								if value not in ("empty", "mixed"):
									produced_materials.add(value)

	return produced_materials, declared_materials_by_mini


def check_cross_mini_material_references(
	tree: object,
	mini_name: str,
	mini_index: int,
	sequence_runner_minis: list[str],
	produced_materials: set,
	declared_materials_by_mini: dict,
	emitter: object,
) -> None:
	"""
	Check all material references in mini_index against upstream production.

	For each non-sentinel material reference in mini_index, verify:
	  - It was produced (via ObjectStateChange) in some upstream mini (< mini_index), OR
	  - It is declared in materials.yaml of some upstream mini (< mini_index), OR
	  - It is declared in this mini's own materials.yaml

	Emits ERROR for unresolved material references.

	Args:
		tree: LoadedContentTree instance.
		mini_name: Name of the mini being checked.
		mini_index: Position in the sequence_runner's mini_protocols list (0-indexed).
		sequence_runner_minis: Ordered list of mini protocol names.
		produced_materials: Set of materials produced by all minis up to mini_index (exclusive).
		declared_materials_by_mini: Dict[int -> set[str]] of declared input materials per mini.
		emitter: FindingEmitter for diagnostics.
	"""
	protocol = tree.get_protocol(mini_name)
	protocol_path = protocol.get("_file_path", "<unknown>")
	steps = protocol.get("steps", [])

	# Build the set of materials available upstream and in this mini's own materials.yaml
	available_materials = set(produced_materials)
	for idx in range(mini_index):
		available_materials.update(declared_materials_by_mini.get(idx, set()))

	# Add this mini's declared materials
	this_mini_materials = tree.get_protocol_materials(mini_name)
	available_materials.update(this_mini_materials.keys())

	# Scan all references
	for step_index, step in enumerate(steps):
		if not isinstance(step, dict):
			continue
		step_name = step.get("step_name")
		sequence = step.get("sequence", [])
		if not isinstance(sequence, list):
			continue
		for interaction_index, interaction in enumerate(sequence):
			if not isinstance(interaction, dict):
				continue

			# (a) Check material_name / held_material_name in ObjectStateChange.state (read-side)
			response = interaction.get("response", {})
			if not isinstance(response, dict):
				continue
			scene_ops = response.get("scene_operations", [])
			if not isinstance(scene_ops, list):
				continue
			for scene_op in scene_ops:
				if not isinstance(scene_op, dict):
					continue
				if scene_op.get("type") == "ObjectStateChange":
					state_block = scene_op.get("state", {})
					if not isinstance(state_block, dict):
						continue
					# Check read-side references (any usage that is not a write)
					for field_name in ("material_name", "held_material_name"):
						value = state_block.get(field_name)
						if value and isinstance(value, str):
							if value not in ("empty", "mixed"):
								if value not in available_materials:
									emitter.emit_finding(Finding(
										level=Level.ERROR,
										protocol_name=mini_name,
										step_name=step_name,
										interaction_index=interaction_index,
										target=None,
										file_path=protocol_path,
										code="cross_mini_unknown_material",
										message=f"material_name '{value}' in ObjectStateChange.state not produced or declared in upstream minis or this mini's materials.yaml",
										spec_cite="docs/PRIMARY_SPEC.md Targets and the scene boundary",
									))

			# (b) Check material_name / held_material_name in validator.preset = target_with_value value field
			validator = interaction.get("validator", {})
			if isinstance(validator, dict):
				preset = validator.get("preset")
				if preset == "target_with_value":
					value_data = validator.get("value")
					if isinstance(value_data, dict):
						for field_name in ("material_name", "held_material_name"):
							value = value_data.get(field_name)
							if value and isinstance(value, str):
								if value not in ("empty", "mixed"):
									if value not in available_materials:
										emitter.emit_finding(Finding(
											level=Level.ERROR,
											protocol_name=mini_name,
											step_name=step_name,
											interaction_index=interaction_index,
											target=None,
											file_path=protocol_path,
											code="cross_mini_unknown_material",
											message=f"material_name '{value}' in validator.preset=target_with_value not produced or declared in upstream minis or this mini's materials.yaml",
											spec_cite="docs/specs/PROTOCOL_STEPS.md Validators",
										))

		# (c) Check material_name / held_material_name in step_validator.preset = final_state_matches contains clause
		step_validator = step.get("step_validator", {})
		if isinstance(step_validator, dict):
			preset = step_validator.get("preset")
			if preset == "final_state_matches":
				contains_list = step_validator.get("contains", [])
				if isinstance(contains_list, list):
					for contains_item in contains_list:
						if isinstance(contains_item, dict):
							for field_name in ("material_name", "held_material_name"):
								value = contains_item.get(field_name)
								if value and isinstance(value, str):
									if value not in ("empty", "mixed"):
										if value not in available_materials:
											emitter.emit_finding(Finding(
												level=Level.ERROR,
												protocol_name=mini_name,
												step_name=step_name,
												interaction_index=None,
												target=None,
												file_path=protocol_path,
												code="cross_mini_unknown_material",
												message=f"material_name '{value}' in step_validator.preset=final_state_matches not produced or declared in upstream minis or this mini's materials.yaml",
												spec_cite="docs/specs/PROTOCOL_STEPS.md Step validators",
											))
