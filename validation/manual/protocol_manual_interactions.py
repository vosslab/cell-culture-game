"""Render interaction sequences into pedagogically ordered manual prose."""

import re

import validation.manual.protocol_manual_state


VERIFY_PROMPT_KEYWORDS = ("verify", "confirm", "review", "check", "inspect")


def render_step(step: object, catalog: object, material_labels: object, sim: object, touched_objects: object, lint: object=None) -> object:
	"""
	Render one step. Walks the sequence applying multi-interaction
	grouping where patterns match, with per-step touched-object tracking
	for the verify-vs-pickup fallback heuristic. When lint is not None,
	collects authoring warnings.
	"""
	lines = []
	step_name = step["step_name"]
	prompt = step.get("prompt", "") or ""
	sequence = step.get("sequence", []) or []

	pretty = _first_char_upper(step_name.replace("_", " "))
	lines.append(f"### {pretty}")
	lines.append("")
	lines.append(prompt)
	lines.append("")

	# L-PROMPT: check for click-centric verbs at prompt start.
	if lint is not None:
		tokens = prompt.split()
		if tokens:
			first_token = tokens[0]
			if first_token in ("Click", "Tap", "Press"):
				msg = f"prompt starts with click-centric verb: {first_token!r}"
				lint.record(step_name, "L-PROMPT", msg)

	# L-ASPIRATE: check for "aspirate" in prompt when pipette draws to non-waste dest.
	if lint is not None:
		# Regex matches "aspirate", "aspirates", "aspirated", "aspirating".
		# Word boundaries prevent substring matches: "reaspirate", "aspirator", "aspirational" are excluded.
		aspirate_found = re.search(r"\baspirate(s|d|ing)?\b", prompt, re.IGNORECASE)
		if aspirate_found:
			has_nonwaste_pipette_draw = validation.manual.protocol_manual_state._has_nonwaste_pipette_draw(sequence, catalog, sim)
			# Suppress L-ASPIRATE when step only performs vacuum-removal to waste; "aspirate" is correct in that context.
			if has_nonwaste_pipette_draw:
				aspirate_token = aspirate_found.group()
				msg = f"prompt uses {aspirate_token!r} for pipette loading (reserved for vacuum-removal to waste); use 'draw' or 'pipette up' instead"
				lint.record(step_name, "L-ASPIRATE", msg)

	if not sequence:
		lines.append("*(no interactions)*")
		lines.append("")
		return lines

	prompt_says_verify = any(
		prompt.lower().lstrip().startswith(kw) for kw in VERIFY_PROMPT_KEYWORDS
	)
	step_touched = set()

	index = 0
	seen_sentences = set()
	while index < len(sequence):
		consumed, sentences = render_group_at(
			sequence, index, catalog, material_labels, sim,
			touched_objects, step_touched, prompt_says_verify, step_name, lint,
		)
		for sentence in sentences:
			if sentence not in seen_sentences:
				lines.append(sentence)
				seen_sentences.add(sentence)
		index += consumed

	lines.append("")
	return lines


#============================================
def render_group_at(sequence: object, index: object, catalog: object, material_labels: object, sim: object,
		touched_objects: object, step_touched: object, prompt_says_verify: object, step_name: object="", lint: object=None) -> object:
	"""
	Try to match a multi-interaction pattern starting at sequence[index].
	Returns (consumed_count, sentences_list).
	"""
	interaction = sequence[index]
	target = interaction.get("target", "")
	gesture = interaction.get("gesture", "click")

	# Multi-well dispense pattern: pipette aspirate then N consecutive
	# dispenses into related plate wells.
	if gesture == "click" and validation.manual.protocol_manual_state.is_pipette(catalog, target):
		multi = match_multi_well_dispense(sequence, index, catalog)
		if multi is not None:
			consumed, sentence = multi
			for offset in range(consumed):
				_mark_touched(sequence[index + offset], touched_objects, step_touched)
				validation.manual.protocol_manual_state.apply_state_changes(sequence[index + offset], sim)
			return consumed, [sentence]

	# 4-interaction pipette transfer (pickup -> adjust -> source -> dest)
	if gesture == "click" and validation.manual.protocol_manual_state.is_pipette(catalog, target):
		if index + 3 < len(sequence):
			adjust_i = sequence[index + 1]
			source_i = sequence[index + 2]
			dest_i = sequence[index + 3]
			if (
				adjust_i.get("target") == target
				and adjust_i.get("gesture") == "adjust"
				and source_i.get("gesture") == "click"
				and dest_i.get("gesture") == "click"
			):
				sentence = render_pipette_transfer(
					target, adjust_i, source_i, dest_i,
					catalog, material_labels, sim, step_name, lint,
				)

				# F10: Try to absorb consecutive well dispenses into a distribute sentence.
				extra_count = 0
				final_sentence = sentence
				absorb_result = _absorb_consecutive_well_dispenses(
					sequence, index + 4, dest_i, catalog, sim
				)
				if absorb_result is not None:
					extra_count, wells_range, plate_label = absorb_result

					# Compute volume from adjust if available.
					adjust_volume = None
					adjust_unit = ""
					validator = adjust_i.get("validator", {}) or {}
					value = validator.get("value", {}) or {}
					for vol_key in ("held_material_volume", "set_volume"):
						if vol_key in value:
							adjust_volume = value[vol_key]
							adjust_unit = catalog.unit_for_field(target, vol_key)
							break

					if adjust_volume is not None:
						vol_str = validation.manual.protocol_manual_state.format_volume(adjust_volume, adjust_unit)
						final_sentence = (
							f"- Using the {_lower_first(catalog.label(target))}, "
							f"distribute {vol_str} to each of {wells_range} of the "
							f"{plate_label} ({1 + extra_count} wells)."
						)
					else:
						final_sentence = (
							f"- Using the {_lower_first(catalog.label(target))}, "
							f"distribute to each of {wells_range} of the {plate_label} "
							f"({1 + extra_count} wells)."
						)

				# Mark touched and apply state changes for all interactions (base 4 + any extra).
				_mark_touched(interaction, touched_objects, step_touched)
				validation.manual.protocol_manual_state.apply_state_changes(interaction, sim)
				_mark_touched(adjust_i, touched_objects, step_touched)
				validation.manual.protocol_manual_state.apply_state_changes(adjust_i, sim)
				_mark_touched(source_i, touched_objects, step_touched)
				validation.manual.protocol_manual_state.apply_state_changes(source_i, sim)
				_mark_touched(dest_i, touched_objects, step_touched)
				validation.manual.protocol_manual_state.apply_state_changes(dest_i, sim)
				for offset in range(extra_count):
					_mark_touched(sequence[index + 4 + offset], touched_objects, step_touched)
					validation.manual.protocol_manual_state.apply_state_changes(sequence[index + 4 + offset], sim)

				return 4 + extra_count, [final_sentence]

	# 3-interaction pipette transfer (no adjust)
	if gesture == "click" and validation.manual.protocol_manual_state.is_pipette(catalog, target):
		if index + 2 < len(sequence):
			source_i = sequence[index + 1]
			dest_i = sequence[index + 2]
			if (
				source_i.get("gesture") == "click"
				and dest_i.get("gesture") == "click"
				and source_i.get("target") != target
				and dest_i.get("target") != target
				and (source_i.get("response", {}) or {}).get("scene_operations")
				and (dest_i.get("response", {}) or {}).get("scene_operations")
			):
				sentence = render_pipette_transfer(
					target, None, source_i, dest_i,
					catalog, material_labels, sim, step_name, lint,
				)
				for sub in (interaction, source_i, dest_i):
					_mark_touched(sub, touched_objects, step_touched)
					validation.manual.protocol_manual_state.apply_state_changes(sub, sim)
				return 3, [sentence]

	# Aspirate-to-waste pattern: pipette click + click on flask that empties.
	if gesture == "click" and validation.manual.protocol_manual_state.is_pipette(catalog, target):
		if index + 1 < len(sequence):
			next_i = sequence[index + 1]
			next_change = validation.manual.protocol_manual_state.find_first_op_of_type(
				(next_i.get("response", {}) or {}).get("scene_operations"),
				"ObjectStateChange",
			)
			if next_change is not None:
				new_state = next_change.get("state", {}) or {}
				if new_state.get("material_name") == "empty":
					dest_label = catalog.label(next_i.get("target", ""))
					sentence = (
						f"- Use the {_lower_first(catalog.label(target))} "
						f"to aspirate and remove the contents of the {dest_label}."
					)
					for sub in (interaction, next_i):
						_mark_touched(sub, touched_objects, step_touched)
						validation.manual.protocol_manual_state.apply_state_changes(sub, sim)
					return 2, [sentence]

	# No group: single interaction
	sentences = render_single_interaction(
		interaction, catalog, material_labels, sim,
		touched_objects, step_touched, prompt_says_verify,
	)
	_mark_touched(interaction, touched_objects, step_touched)
	validation.manual.protocol_manual_state.apply_state_changes(interaction, sim)
	return 1, sentences


#============================================
def _mark_touched(interaction: object, touched_objects: object, step_touched: object) -> None:
	"""Record this interaction's target in both touched sets."""
	target = interaction.get("target", "")
	if target:
		touched_objects.add(target)
		step_touched.add(target)


#============================================
def _lower_first(text: object) -> object:
	"""Lowercase only the first character of a label for mid-sentence use."""
	if not text:
		return text
	return text[0].lower() + text[1:]


#============================================
def _first_char_upper(text: object) -> object:
	"""Uppercase only the first character, leaving the rest untouched."""
	if not text:
		return text
	return text[0].upper() + text[1:]


#============================================
def match_multi_well_dispense(sequence: object, index: object, catalog: object) -> object:
	"""
	Detect: pipette click + N consecutive clicks on plate wells whose
	material_name and (constant) addition volume match across the run.
	Returns (consumed_count, rendered_sentence) or None.

	Minimum 2 well dispenses required to call it a multi-dispense; only
	groups when all destinations are subparts of the same parent plate
	and all add the same material.
	"""
	if index + 2 >= len(sequence):
		return None
	pipette_i = sequence[index]
	pipette = pipette_i.get("target", "")
	dispenses = []
	cursor = index + 1
	parent_plate = None
	material_name = None
	while cursor < len(sequence):
		dispense_i = sequence[cursor]
		if dispense_i.get("gesture") != "click":
			break
		dest = dispense_i.get("target", "")
		if not validation.manual.protocol_manual_state.is_plate_subpart(dest):
			break
		parent = dest.split(".", 1)[0]
		if parent_plate is None:
			parent_plate = parent
		elif parent != parent_plate:
			break
		change = validation.manual.protocol_manual_state.find_first_op_of_type(
			(dispense_i.get("response", {}) or {}).get("scene_operations"),
			"ObjectStateChange",
		)
		if change is None:
			break
		state = change.get("state", {}) or {}
		if "material_name" not in state:
			break
		if material_name is None:
			material_name = state["material_name"]
		elif state["material_name"] != material_name:
			break
		dispenses.append(dest.split(".", 1)[1])
		cursor += 1
	if len(dispenses) < 2:
		return None
	add_vol = None
	add_unit = ""
	# Backward iteration with first-match break: earliest matching adjust in the
	# 4-interaction window wins.
	for check_index in range(max(0, index - 4), index):
		prior = sequence[check_index]
		if prior.get("gesture") == "adjust" and prior.get("target") == pipette:
			value = (prior.get("validator", {}) or {}).get("value", {}) or {}
			for key in ("held_material_volume", "set_volume"):
				if key in value:
					add_vol = value[key]
					add_unit = catalog.unit_for_field(pipette, key)
					break
			if add_vol is not None:
				break
	wells_range = _summarize_well_list(dispenses)
	plate_label = catalog.label(parent_plate)
	if add_vol is not None:
		vol_str = validation.manual.protocol_manual_state.format_volume(add_vol, add_unit)
		sentence = (
			f"- Dispense {vol_str} into each of {wells_range} of the "
			f"{plate_label} ({len(dispenses)} wells)."
		)
	else:
		sentence = (
			f"- Dispense into each of {wells_range} of the {plate_label} "
			f"({len(dispenses)} wells)."
		)
	consumed = 1 + len(dispenses)
	return consumed, sentence


#============================================
def _summarize_well_list(wells: object) -> object:
	"""
	Render a contiguous well list as a range ("B1-B12") or a comma list
	if discontiguous. Groups by row letter.
	"""
	if not wells:
		return ""
	by_row = {}
	for well in wells:
		match = re.match(r"^([A-H])(\d+)$", well)
		if match is None:
			by_row.setdefault("_other", []).append(well)
			continue
		row, col = match.group(1), int(match.group(2))
		by_row.setdefault(row, []).append(col)
	row_strs = []
	for row, cols in by_row.items():
		if row == "_other":
			row_strs.extend(by_row["_other"])
			continue
		cols_sorted = sorted(cols)
		if cols_sorted == list(range(cols_sorted[0], cols_sorted[-1] + 1)):
			row_strs.append(f"wells {row}{cols_sorted[0]}-{row}{cols_sorted[-1]}")
		else:
			row_strs.append(", ".join(f"{row}{c}" for c in cols_sorted))
	return " + ".join(row_strs)


#============================================
def _absorb_consecutive_well_dispenses(sequence: object, index_after_transfer: object, dest_i: object,
		catalog: object, sim: object) -> object:
	"""
	Detect and absorb consecutive plate-subpart dispenses with matching
	material and volume deltas into a multi-well distribute sentence.
	Returns (extra_count, distribute_sentence) or None if no absorption.

	Called from the 4-interaction pipette transfer branch to check whether
	the destination is a plate subpart and whether subsequent interactions
	are consecutive well dispenses with matching material and volume.
	Intent: collapse "dispense to well A1, A2, A3..." into one sentence
	covering all wells when the volume and material are constant.
	"""
	dest_target = dest_i.get("target", "")
	if not validation.manual.protocol_manual_state.is_plate_subpart(dest_target):
		return None

	dest_parent = dest_target.split(".", 1)[0]
	dest_change = validation.manual.protocol_manual_state.find_first_op_of_type(
		(dest_i.get("response", {}) or {}).get("scene_operations"),
		"ObjectStateChange",
	)
	if dest_change is None:
		return None

	dest_state = dest_change.get("state", {}) or {}
	dest_material = dest_state.get("material_name")
	dest_volume_delta = dest_state.get("material_volume")

	# Peek ahead for consecutive well clicks with same parent, material, volume.
	extra_wells = []
	cursor = index_after_transfer
	while cursor < len(sequence):
		cont_i = sequence[cursor]
		if cont_i.get("gesture") != "click":
			break
		cont_target = cont_i.get("target", "")
		if not validation.manual.protocol_manual_state.is_plate_subpart(cont_target):
			break
		cont_parent = cont_target.split(".", 1)[0]
		if cont_parent != dest_parent:
			break
		cont_change = validation.manual.protocol_manual_state.find_first_op_of_type(
			(cont_i.get("response", {}) or {}).get("scene_operations"),
			"ObjectStateChange",
		)
		if cont_change is None:
			break
		cont_state = cont_change.get("state", {}) or {}
		cont_material = cont_state.get("material_name")
		cont_volume = cont_state.get("material_volume")

		# Check material match and volume match
		if cont_material != dest_material:
			break
		if not validation.manual.protocol_manual_state._volume_match(dest_volume_delta, cont_volume):
			break

		extra_wells.append(cont_target.split(".", 1)[1])
		cursor += 1

	if not extra_wells:
		return None

	all_wells = [dest_target.split(".", 1)[1]] + extra_wells
	wells_range = _summarize_well_list(all_wells)
	plate_label = catalog.label(dest_parent)
	return len(extra_wells), wells_range, plate_label


#============================================
def render_pipette_transfer(pipette_name: object, adjust_i: object, source_i: object, dest_i: object,
		catalog: object, material_labels: object, sim: object, step_name: object="", lint: object=None) -> object:
	"""
	Render one combined sentence for a pipette transfer. Resolves volume
	in priority: adjust value -> source delta -> dest delta. Resolves
	material in priority: source's tracked material_name -> dest's new
	material_name. Suppresses redundant material phrase when source label
	already overlaps with material label. When lint is not None, collects
	authoring warnings about material drift and volume mismatches.
	"""
	pipette_label = catalog.label(pipette_name)
	source_name = source_i.get("target", "")
	dest_name = dest_i.get("target", "")
	source_label = catalog.label(source_name)
	dest_label = catalog.label(dest_name)

	volume = None
	unit = ""
	adjust_volume = None
	adjust_unit = ""

	if adjust_i is not None:
		validator = adjust_i.get("validator", {}) or {}
		value = validator.get("value", {}) or {}
		for vol_key in ("held_material_volume", "set_volume"):
			if vol_key in value:
				volume = value[vol_key]
				adjust_volume = volume
				unit = catalog.unit_for_field(pipette_name, vol_key)
				adjust_unit = unit
				break

	source_change = validation.manual.protocol_manual_state.find_first_op_of_type(
		(source_i.get("response", {}) or {}).get("scene_operations"),
		"ObjectStateChange",
	)
	dest_change = validation.manual.protocol_manual_state.find_first_op_of_type(
		(dest_i.get("response", {}) or {}).get("scene_operations"),
		"ObjectStateChange",
	)

	if volume is None and source_change is not None:
		new_state = source_change.get("state", {}) or {}
		# When the source-click writes held_material_volume to the pipette
		# itself, that IS the per-aspirate loaded volume; use it directly
		# instead of computing a delta. This matches the case where the
		# pipette's loaded state is the authored signal for the dispense
		# size, and avoids falling through to dest_delta (which would
		# return the well-total under Q5 well-total state-field semantics).
		if "held_material_volume" in new_state:
			volume = new_state["held_material_volume"]
			unit = catalog.unit_for_field(
				source_change.get("target"), "held_material_volume"
			)
		elif "material_volume" in new_state:
			old = sim.get(source_change.get("target"), "material_volume")
			try:
				delta = float(old) - float(new_state["material_volume"])
				if delta > 0:
					volume = delta
					unit = catalog.unit_for_field(
						source_change.get("target"), "material_volume"
					)
			except (TypeError, ValueError):
				pass

	dest_delta = None
	dest_delta_unit = ""
	if volume is None and dest_change is not None:
		new_state = dest_change.get("state", {}) or {}
		if "material_volume" in new_state:
			old = sim.get(dest_change.get("target"), "material_volume")
			try:
				old_val = float(old) if old is not None else 0.0
				delta = float(new_state["material_volume"]) - old_val
			except (TypeError, ValueError):
				pass
			else:
				if delta > 0:
					volume = delta
					dest_delta = delta
					dest_delta_unit = catalog.unit_for_field(
						dest_change.get("target"), "material_volume"
					)
					unit = dest_delta_unit
	elif dest_change is not None:
		# Compute dest_delta even when volume is already known, for use in
		# L-VOLMISMATCH lint check below to verify adjust matches the destination
		# volume change.
		new_state = dest_change.get("state", {}) or {}
		if "material_volume" in new_state:
			old = sim.get(dest_change.get("target"), "material_volume")
			try:
				old_val = float(old) if old is not None else 0.0
				delta = float(new_state["material_volume"]) - old_val
			except (TypeError, ValueError):
				pass
			else:
				if delta > 0:
					dest_delta = delta
					dest_delta_unit = catalog.unit_for_field(
						dest_change.get("target"), "material_volume"
					)

	# L-VOLMISMATCH: check if adjust value and dest delta mismatch by > 1%.
	# When units differ (e.g., uL vs mL), convert both to uL for comparison.
	# Suppress this check for plate subparts (dotted notation) where multi-well
	# aggregation can cause false positives (e.g., 100 uL per well x 96 wells = 9600 uL).
	if lint is not None and adjust_volume is not None and dest_delta is not None:
		if "." not in dest_name:
			try:
				adjust_val = float(adjust_volume)
				dest_val = float(dest_delta)
			except (TypeError, ValueError):
				pass
			else:
				if adjust_val > 0 and dest_val > 0:
					# Normalize both to uL for unit-agnostic comparison.
					adjust_ul = adjust_val * (1000 if adjust_unit == "ml" else 1)
					dest_ul = dest_val * (1000 if dest_delta_unit == "ml" else 1)
					max_val = max(adjust_ul, dest_ul)
					pct_diff = abs(adjust_ul - dest_ul) / max_val
					if pct_diff > 0.01:
						lint.record(
							step_name, "L-VOLMISMATCH",
							f"pipette set to {adjust_val} {adjust_unit}, dest delta is {dest_val} {dest_delta_unit}"
						)

	material_name = sim.get(source_name, "material_name")
	if not material_name or material_name == "empty":
		material_name = None

	# L-MATDRIFT: check if source material is undefined/empty.
	if lint is not None and not material_name:
		if dest_change is not None:
			dest_state = dest_change.get("state", {}) or {}
			dest_material = dest_state.get("material_name")
			if dest_material:
				lint.record(
					step_name, "L-MATDRIFT",
					f"source material undefined; dest material {dest_material!r} assumed by author"
				)

	material_label = validation.manual.protocol_manual_state.label_for_material(material_name or "", material_labels) if material_name else ""

	# Verb choice: "draw" for pipette loading FROM a source; "aspirate" is
	# reserved for vacuum-removal-to-waste (handled in the aspirate-to-waste
	# pattern elsewhere). Lab convention: "aspirate" implies a vacuum line
	# pulling content to waste, not a pipette drawing reagent for transfer.
	parts = [f"- Using the {_lower_first(pipette_label)},"]
	if volume is not None:
		parts.append("draw")
		parts.append(validation.manual.protocol_manual_state.format_volume(volume, unit))
		if material_name and material_name != "empty":
			if not validation.manual.protocol_manual_state.labels_overlap(source_label, material_label):
				parts.append(f"of {material_label}")
		parts.append(f"from the {source_label}")
		parts.append(f"and dispense into the {dest_label}.")
	else:
		parts.append("transfer")
		if material_name and material_name != "empty":
			if not validation.manual.protocol_manual_state.labels_overlap(source_label, material_label):
				parts.append(material_label)
		parts.append(f"from the {source_label}")
		parts.append(f"into the {dest_label}.")
	return " ".join(parts)


#============================================
#============================================
def _field_to_human_phrase(field_name: object, new_value: object, catalog: object=None, target: object=None) -> object:
	"""
	Translate field-name-and-value pairs to imperative student-facing prose.
	Returns a phrase fragment like "is now empty" or "is now powered on".
	For unknown fields, returns None (fallback to generic template).

	When catalog and target are provided, uses validation.manual.protocol_manual_state.format_volume for volume fields
	and resolves units from object state_fields.
	"""
	value_str = str(new_value).replace("_", " ").lower()
	if field_name == "material_name":
		if new_value == "empty":
			return "is now empty"
		return f"now contains {value_str}"
	if field_name == "held_material_name":
		if new_value == "empty":
			return "is now empty"
		return f"now holds {value_str}"
	if field_name == "material_volume":
		if catalog and target:
			unit = catalog.unit_for_field(target, field_name)
			return f"contains {validation.manual.protocol_manual_state.format_volume(new_value, unit)}"
		return f"contains {value_str}"
	if field_name == "held_material_volume":
		if catalog and target:
			unit = catalog.unit_for_field(target, field_name)
			return f"holds {validation.manual.protocol_manual_state.format_volume(new_value, unit)}"
		return f"holds {value_str}"
	if field_name == "tape_present":
		return "tape removed" if new_value is False else "tape applied"
	if field_name == "running":
		return "is now started" if new_value is True else "is now stopped"
	if field_name == "lid_open":
		return "is now open" if new_value is True else "is now closed"
	if field_name == "powered_on":
		return "is now powered on" if new_value is True else "is now powered off"
	if field_name == "image_captured":
		return "has captured an image" if new_value is True else "has not captured an image"
	if field_name == "cathode_lead_attached":
		return "cathode lead attached" if new_value is True else "cathode lead detached"
	if field_name == "anode_lead_attached":
		return "anode lead attached" if new_value is True else "anode lead detached"
	if field_name == "side_clamps_locked":
		return "side clamps locked" if new_value is True else "side clamps unlocked"
	if field_name == "wing_clamps_locked":
		return "wing clamps locked" if new_value is True else "wing clamps unlocked"
	if field_name == "wing_clamps_open":
		return "wing clamps open" if new_value is True else "wing clamps closed"
	if field_name == "comb_present":
		return "comb in place" if new_value is True else "comb removed"
	if field_name == "top_plate_inserted":
		return "top plate inserted" if new_value is True else "top plate removed"
	if field_name == "glass_plate_inserted":
		return "glass plate inserted" if new_value is True else "glass plate removed"
	if field_name == "mounted":
		return "mounted" if new_value is True else "unmounted"
	if field_name == "cassette_mounted":
		return "cassette mounted" if new_value is True else "cassette removed"
	if field_name == "module_present":
		return "module installed" if new_value is True else "module removed"
	if field_name == "kimwipes_present":
		return "kimwipes added" if new_value is True else "kimwipes removed"
	if field_name == "gel_present":
		return "gel placed" if new_value is True else "gel removed"
	if field_name == "sealed":
		return "sealed" if new_value is True else "opened"
	if field_name == "tray_present":
		return "tray placed" if new_value is True else "tray removed"
	if field_name == "rack_present":
		return "rack placed" if new_value is True else "rack removed"
	if field_name == "door_open":
		return "door open" if new_value is True else "door closed"
	if field_name == "lid_present":
		return "lid placed" if new_value is True else "lid removed"

	# Handle subpart-prefixed material fields (e.g., inner_chamber_material_name,
	# outer_chamber_material_volume). Extract subpart name and produce natural prose.
	# Note: subpart label gets capitalized because the caller wraps it as
	# "The {target_label} {phrase}." so we need to lowercase the subpart part.
	if field_name.endswith("_material_name"):
		subpart = field_name[:-len("_material_name")]
		subpart_label = subpart.replace("_", " ")
		if new_value == "empty":
			return f"{subpart_label} is now empty"
		material_label = str(new_value).replace("_", " ").lower()
		return f"{subpart_label} now contains {material_label}"

	if field_name.endswith("_material_volume"):
		subpart = field_name[:-len("_material_volume")]
		subpart_label = subpart.replace("_", " ")
		if catalog and target:
			unit = catalog.unit_for_field(target, field_name)
			return f"{subpart_label} holds {validation.manual.protocol_manual_state.format_volume(new_value, unit)}"
		return f"{subpart_label} holds {value_str}"

	return None


#============================================
def render_single_interaction(interaction: object, catalog: object, material_labels: object, sim: object,
		touched_objects: object, step_touched: object, prompt_says_verify: object) -> object:
	"""Render one ungrouped interaction. Returns a list of sentences."""
	gesture = interaction.get("gesture", "click")
	target = interaction.get("target", "")
	target_label = catalog.label(target)
	response = interaction.get("response", {}) or {}
	scene_ops = response.get("scene_operations", []) or []

	bullets = []

	# TimedWait
	for op in scene_ops:
		if op.get("type") == "TimedWait":
			minutes = op.get("duration_min", "?")
			display = op.get("display", "") or ""
			seconds = None
			try:
				numeric = float(minutes)
				if 0 < numeric < 1:
					seconds = int(round(numeric * 60))
			except (TypeError, ValueError):
				pass
			wait = f"**{seconds} sec**" if seconds is not None else f"**{minutes} min**"
			if display:
				bullets.append(f"- Wait {wait} ({display}).")
			else:
				bullets.append(f"- Wait {wait}.")

	# SceneChange
	for op in scene_ops:
		if op.get("type") == "SceneChange":
			to_scene = op.get("to_scene", "").replace("_", " ")
			bullets.append(f"- Move to the **{to_scene}**.")

	# adjust gesture
	if gesture == "adjust":
		validator = interaction.get("validator", {}) or {}
		value = validator.get("value", {}) or {}
		# Map known keys to display labels.
		field_map = {
			"held_material_volume": "volume",
			"set_volume": "volume",
			"set_temperature": "temperature",
			"set_rpm": "speed",
			"set_time_s": "timer",
			"set_time_min": "timer",
		}
		# Check if value is a dict with exactly one key.
		if isinstance(value, dict) and len(value) == 1:
			key = list(value.keys())[0]
			# Use hardcoded map if key is in it, else derive from key name.
			if key in field_map:
				field_label = field_map[key]
			elif key.startswith("set_") or key == "held_material_volume":
				# Derive label from key: set_temperature -> temperature.
				prefix_to_strip = "set_" if key.startswith("set_") else "held_material_"
				field_label = key[len(prefix_to_strip):].replace("_", " ")
			else:
				field_label = key.replace("_", " ")
			unit = catalog.unit_for_field(target, key)
			bullets.append(
				f"- Set the {_lower_first(target_label)} {field_label} "
				f"to {validation.manual.protocol_manual_state.format_volume(value[key], unit)}."
			)
			return bullets
		bullets.append(f"- Adjust the {_lower_first(target_label)}.")
		return bullets

	state_changes = validation.manual.protocol_manual_state.find_state_changes(scene_ops)

	# Indirect cause-effect: click on X mutates Y (Y != X).
	for change in state_changes:
		change_target = change.get("target", "")
		if change_target and change_target != target:
			new_state = change.get("state", {}) or {}
			field, value = next(iter(new_state.items()))
			change_label = catalog.label(change_target)
			if "cleanliness" in field and "ethanol" in str(value):
				bullets.append(
					f"- Use the {_lower_first(target_label)} to spray and "
					f"sterilize the {change_label}."
				)
				return bullets
			# Use humanized field names for better readability.
			human_phrase = _field_to_human_phrase(field, value, catalog, change_target)
			if human_phrase:
				bullets.append(
					f"- Use the {_lower_first(target_label)} to update the "
					f"{change_label} ({human_phrase})."
				)
				return bullets
			pretty_field = field.replace("_", " ")
			pretty_value = str(value).replace("_", " ")
			bullets.append(
				f"- Use the {_lower_first(target_label)} to update the "
				f"{change_label} ({pretty_field}: {pretty_value})."
			)
			return bullets

	# State changes on the click target. Render each state change as a bullet.
	found_target_change = False
	for change in state_changes:
		if change.get("target") != target:
			continue
		found_target_change = True
		new_state = change.get("state", {}) or {}
		if "material_name" in new_state:
			new_material = new_state["material_name"]
			if new_material == "empty":
				bullets.append(f"- Aspirate and remove the contents of the {target_label}.")
				continue
			material_label = validation.manual.protocol_manual_state.label_for_material(new_material, material_labels)
			volume = new_state.get("material_volume")
			if volume is not None:
				old_vol = sim.get(target, "material_volume")
				try:
					old_val = float(old_vol) if old_vol is not None else 0.0
					delta = float(volume) - old_val
					if delta > 0:
						unit = catalog.unit_for_field(target, "material_volume")
						# F5 extension: suppress material name when dest is a plate subpart,
						# old state is empty, and source cannot be inferred from this interaction.
						if validation.manual.protocol_manual_state.is_plate_subpart(target) and old_val == 0.0:
							bullets.append(
								f"- Add {validation.manual.protocol_manual_state.format_volume(delta, unit)} to the {target_label}."
							)
							continue
						bullets.append(
							f"- Add {validation.manual.protocol_manual_state.format_volume(delta, unit)} of "
							f"{material_label} to the {target_label}."
						)
						continue
				except (TypeError, ValueError):
					pass
				unit = catalog.unit_for_field(target, "material_volume")
				bullets.append(
					f"- The {target_label} now contains "
					f"{validation.manual.protocol_manual_state.format_volume(volume, unit)} of {material_label}."
				)
				continue
			bullets.append(f"- The {target_label} now contains {material_label}.")
			continue

		if "material_volume" in new_state and "material_name" not in new_state:
			old_vol = sim.get(target, "material_volume")
			new_vol = new_state["material_volume"]
			try:
				old_val = float(old_vol) if old_vol is not None else 0.0
				delta = old_val - float(new_vol)
				if delta > 0:
					unit = catalog.unit_for_field(target, "material_volume")
					bullets.append(
						f"- Draw {validation.manual.protocol_manual_state.format_volume(delta, unit)} from the {target_label}."
					)
					continue
			except (TypeError, ValueError):
				pass
			bullets.append(f"- Draw from the {target_label}.")
			continue

		# Other state field (status, cleanliness, boolean flags).
		field, value = next(iter(new_state.items()))
		human_phrase = _field_to_human_phrase(field, value, catalog, target)
		if human_phrase:
			bullets.append(f"- The {target_label} {human_phrase}.")
			continue
		# Fallback for unmapped fields: humanize without asterisks.
		pretty_field = field.replace("_", " ")
		if isinstance(value, bool):
			if value:
				bullets.append(f"- The {target_label} is now {pretty_field}.")
			else:
				bullets.append(f"- The {target_label} is no longer {pretty_field}.")
		else:
			pretty_value = str(value).replace("_", " ")
			bullets.append(f"- The {target_label} {pretty_field} is now {pretty_value}.")

	if found_target_change and bullets:
		return bullets

	# Bare CursorAttach only -> pickup.
	for op in scene_ops:
		if op.get("type") == "CursorAttach":
			bullets.append(f"- Pick up the {target_label}.")
			return bullets

	# Bare click with no scene_ops: verify or pickup.
	if gesture == "click" and not scene_ops:
		if prompt_says_verify:
			bullets.append(f"- Verify the {target_label}.")
		elif target in touched_objects and target not in step_touched:
			bullets.append(f"- Verify the {target_label}.")
		else:
			bullets.append(f"- Pick up the {target_label}.")
		return bullets

	if bullets:
		return bullets

	return [f"- Interact with the {target_label}."]


#============================================
