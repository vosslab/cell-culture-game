"""
Scene inheritance resolver for zone-based scenes.

Handles extends-chain resolution and placement operations:
remove_placements, deactivate_placements, reposition_placements, add_placements.

Reusable helper for generator scripts that need to resolve scene inheritance.
"""

from typing import Any, Dict, List


# Source scenes name semantic groups. The renderer owns numeric geometry.
SOURCE_ZONE_ALLOWED_KEYS = {'zone_name', 'label', 'align'}
SOURCE_PLACEMENT_ALLOWED_KEYS = {
	'placement_name', 'object_name', 'zone', 'depth_tier', 'depth', 'align_stop', 'layout'
}
SOURCE_LAYOUT_ALLOWED_KEYS = {'label_placement', 'anchor_y'}
SOURCE_FORBIDDEN_GEOMETRY_KEYS = {
	'scene_bounds', 'bounds', 'baseline', 'baseline_override',
	'x', 'y', 'left', 'right', 'top', 'bottom',
	'width_scale', 'fudge', 'display_width_cm', 'scale', 'scale_x', 'scale_y',
	'default_width', 'label_width', 'anchor_y_offset', 'position',
}

#============================================

def get_placement_name_dict(placements: list[dict]) -> Dict[str, int]:
	"""
	Build a dict mapping placement_name -> index in the placements list.

	Args:
		placements: List of placement dicts.

	Returns:
		Dict mapping placement_name -> index.

	Raises:
		RuntimeError: If duplicate placement_name values exist.
	"""
	result = {}
	for i, placement in enumerate(placements):
		name = placement.get("placement_name")
		if not name:
			raise RuntimeError(f"Placement {i} missing placement_name")

		if name in result:
			raise RuntimeError(f"Duplicate placement_name '{name}'")

		result[name] = i

	return result


#============================================

def apply_remove_placements(
	placements: list[dict],
	remove_list: List[str],
	scene_name: str,
) -> list[dict]:
	"""
	Remove placements by placement_name.

	Args:
		placements: List of placement dicts.
		remove_list: List of placement_name values to remove.
		scene_name: Scene name (for error messages).

	Returns:
		New placements list with removed items.

	Raises:
		RuntimeError: If unknown placement_name is referenced.
	"""
	name_dict = get_placement_name_dict(placements)

	for remove_name in remove_list:
		if remove_name not in name_dict:
			raise RuntimeError(
				f"Scene '{scene_name}' remove_placements: "
				f"unknown placement_name '{remove_name}'"
			)

	# Keep placements not in remove_list
	result = [p for p in placements if p.get("placement_name") not in remove_list]
	return result


#============================================

def apply_deactivate_placements(
	placements: list[dict],
	deactivate_list: List[str],
	scene_name: str,
) -> list[dict]:
	"""
	Deactivate placements by marking them with deactivated=True.

	Args:
		placements: List of placement dicts.
		deactivate_list: List of placement_name values to deactivate.
		scene_name: Scene name (for error messages).

	Returns:
		New placements list with deactivated flags set.

	Raises:
		RuntimeError: If unknown placement_name is referenced.
	"""
	name_dict = get_placement_name_dict(placements)

	for deactivate_name in deactivate_list:
		if deactivate_name not in name_dict:
			raise RuntimeError(
				f"Scene '{scene_name}' deactivate_placements: "
				f"unknown placement_name '{deactivate_name}'"
			)

	# Mark deactivated placements
	result = []
	for placement in placements:
		if placement.get("placement_name") in deactivate_list:
			new_placement = placement.copy()
			new_placement["deactivated"] = True
			result.append(new_placement)
		else:
			result.append(placement)

	return result


#============================================

def apply_reposition_placements(
	placements: list[dict],
	reposition_list: list[dict],
	scene_name: str,
) -> list[dict]:
	"""
	Reposition placements by updating zone, position, depth, anchor.

	Args:
		placements: List of placement dicts.
		reposition_list: List of reposition operation dicts.
		scene_name: Scene name (for error messages).

	Returns:
		New placements list with repositioned fields.

	Raises:
		RuntimeError: If unknown placement_name or locked field is referenced.
	"""
	name_dict = get_placement_name_dict(placements)
	allowed_fields = {"placement_name", "zone", "depth", "depth_tier", "align_stop"}

	result = []
	for placement in placements:
		placement_name = placement.get("placement_name")

		# Find matching reposition operation
		reposition_op = None
		for op in reposition_list:
			if op.get("placement_name") == placement_name:
				reposition_op = op
				break

		if not reposition_op:
			# No reposition operation for this placement
			result.append(placement)
			continue

		# Validate fields in reposition operation
		unknown_fields = set(reposition_op.keys()) - allowed_fields
		if unknown_fields:
			raise RuntimeError(
				f"Scene '{scene_name}' reposition_placements: "
				f"locked or unknown fields in '{placement_name}': {unknown_fields}"
			)

		# Apply updates
		new_placement = placement.copy()
		for key, value in reposition_op.items():
			if key != "placement_name":
				new_placement[key] = value

		result.append(new_placement)

	# Check all reposition names exist
	for op in reposition_list:
		op_name = op.get("placement_name")
		if op_name not in name_dict:
			raise RuntimeError(
				f"Scene '{scene_name}' reposition_placements: "
				f"unknown placement_name '{op_name}'"
			)

	return result


#============================================

def apply_add_placements(
	placements: list[dict],
	add_list: list[dict],
	scene_name: str,
) -> list[dict]:
	"""
	Add new placements to the list.

	Args:
		placements: Current placements list.
		add_list: List of new placement dicts to add.
		scene_name: Scene name (for error messages).

	Returns:
		New placements list with added items.

	Raises:
		RuntimeError: If duplicate placement_name or missing required fields.
	"""
	result = list(placements)
	existing_names = {p.get("placement_name") for p in placements}
	required_fields = {"placement_name", "object_name", "zone"}

	for new_placement in add_list:
		if not isinstance(new_placement, dict):
			raise RuntimeError(
				f"Scene '{scene_name}' add_placements: entry is not a dict"
			)

		# Validate required fields
		for field in required_fields:
			if field not in new_placement:
				raise RuntimeError(
					f"Scene '{scene_name}' add_placements: "
					f"missing required field '{field}'"
				)

		new_name = new_placement.get("placement_name")

		if new_name in existing_names:
			raise RuntimeError(
				f"Scene '{scene_name}' add_placements: "
				f"duplicate placement_name '{new_name}'"
			)

		result.append(new_placement)
		existing_names.add(new_name)

	return result


#============================================

def resolve_protocol_scene(
	scene_name: str,
	protocol_scene_data: Dict[str, Any],
	base_scenes: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
	"""
	Resolve a protocol scene by applying inheritance from its base scene.

	Steps:
	1. Validate that the protocol scene has scene_name and extends.
	2. Look up the base scene.
	3. Copy locked fields from base (workspace, zones, background, etc.).
	4. Start with placements from base.
	5. Apply operations in order: remove, deactivate, reposition, add.
	6. Return fully resolved scene dict.

	Args:
		scene_name: Scene name (for error messages).
		protocol_scene_data: Parsed protocol scene YAML.
		base_scenes: Dict mapping base scene_name -> parsed YAML.

	Returns:
		Fully resolved scene dict with all inheritance applied.

	Raises:
		RuntimeError: If inheritance resolution fails.
	"""
	# Validate protocol scene schema
	required_fields = ["scene_name", "extends"]
	for field in required_fields:
		if field not in protocol_scene_data:
			raise RuntimeError(
				f"Protocol scene '{scene_name}' missing required field: {field}"
			)

	allowed_keys = {
		"scene_name",
		"extends",
		"add_placements",
		"remove_placements",
		"deactivate_placements",
		"reposition_placements",
		"scene_notes",
	}
	unknown_keys = set(protocol_scene_data.keys()) - allowed_keys
	if unknown_keys:
		raise RuntimeError(
			f"Protocol scene '{scene_name}' has unknown keys: {unknown_keys}"
		)

	base_scene_name = protocol_scene_data.get("extends")
	if base_scene_name not in base_scenes:
		raise RuntimeError(
			f"Protocol scene '{scene_name}' extends unknown base '{base_scene_name}'"
		)

	base_data = base_scenes[base_scene_name]

	# Start with locked fields from base
	result = {
		"scene_name": scene_name,
		"workspace": base_data["workspace"],
		"capabilities": base_data["capabilities"],
		"zones": base_data["zones"],
	}
	if "background" in base_data:
		result["background"] = base_data["background"]

	# Optional locked fields
	if "layout_rules" in base_data:
		result["layout_rules"] = base_data["layout_rules"]

	if "wrong_order_message" in base_data:
		result["wrong_order_message"] = base_data["wrong_order_message"]

	# Start with placements from base
	placements = [p.copy() for p in base_data.get("placements", [])]

	# Apply operations in fixed order
	if "remove_placements" in protocol_scene_data:
		placements = apply_remove_placements(
			placements, protocol_scene_data["remove_placements"], scene_name
		)

	if "deactivate_placements" in protocol_scene_data:
		placements = apply_deactivate_placements(
			placements, protocol_scene_data["deactivate_placements"], scene_name
		)

	if "reposition_placements" in protocol_scene_data:
		placements = apply_reposition_placements(
			placements, protocol_scene_data["reposition_placements"], scene_name
		)

	if "add_placements" in protocol_scene_data:
		placements = apply_add_placements(
			placements, protocol_scene_data["add_placements"], scene_name
		)

	result["placements"] = placements

	return result
