"""Reject scene YAML fields that would bypass layout-engine ownership."""

# local repo modules
import pipeline.scene_inheritance


#============================================

def reject_authored_geometry(
	scene_data: dict,
	yaml_path: str,
	allow_internal_deactivated: bool = False,
) -> None:
	"""Fail loudly when a source scene tries to own renderer geometry."""
	for key in scene_data:
		if key in pipeline.scene_inheritance.SOURCE_FORBIDDEN_GEOMETRY_KEYS:
			raise ValueError(
				f"Forbidden authored geometry '{key}' in {yaml_path}; "
				"semantic zones are sized by the layout manager"
			)

	background = scene_data.get('background')
	if isinstance(background, dict):
		for key in background:
			if key in pipeline.scene_inheritance.SOURCE_FORBIDDEN_GEOMETRY_KEYS:
				raise ValueError(
					f"Forbidden authored geometry 'background.{key}' in {yaml_path}; "
					"semantic zones are sized by the layout manager"
				)

	for index, zone in enumerate(scene_data.get('zones', [])):
		if not isinstance(zone, dict):
			continue
		for key in zone:
			if key in pipeline.scene_inheritance.SOURCE_FORBIDDEN_GEOMETRY_KEYS:
				raise ValueError(
					f"Forbidden authored geometry 'zones[{index}].{key}' in {yaml_path}; "
					"semantic zones may declare only zone_name, label, and align"
				)
			if key not in pipeline.scene_inheritance.SOURCE_ZONE_ALLOWED_KEYS:
				raise ValueError(f"Unknown source-zone key 'zones[{index}].{key}' in {yaml_path}")

	for index, placement in enumerate(scene_data.get('placements', [])):
		if not isinstance(placement, dict):
			continue
		for key in placement:
			if allow_internal_deactivated and key == 'deactivated':
				continue
			if key in pipeline.scene_inheritance.SOURCE_FORBIDDEN_GEOMETRY_KEYS:
				raise ValueError(
					f"Forbidden authored geometry 'placements[{index}].{key}' in {yaml_path}; "
					"placements keep semantic identity and zone membership only"
				)
			if key not in pipeline.scene_inheritance.SOURCE_PLACEMENT_ALLOWED_KEYS:
				raise ValueError(f"Unknown source-placement key 'placements[{index}].{key}' in {yaml_path}")
		layout = placement.get('layout')
		if isinstance(layout, dict):
			for key in layout:
				if key in pipeline.scene_inheritance.SOURCE_FORBIDDEN_GEOMETRY_KEYS:
					raise ValueError(
						f"Forbidden authored geometry 'placements[{index}].layout.{key}' "
						f"in {yaml_path}; layout sizing belongs to the manager"
					)
				if key not in pipeline.scene_inheritance.SOURCE_LAYOUT_ALLOWED_KEYS:
					raise ValueError(
						f"Unknown source-placement layout key 'placements[{index}].layout.{key}' "
						f"in {yaml_path}"
					)
