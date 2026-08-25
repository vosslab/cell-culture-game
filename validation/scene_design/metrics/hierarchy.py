"""Hierarchy metrics: primary placement stands out from supporting placements.

Implements three hierarchy metrics defined in SCENE_DESIGN_LINT_PLAN.md
section "Hierarchy - primary stands out":

  primary_area_ratio           - primary footprint_bbox area / total footprint area
  primary_prominence           - primary footprint area / largest supporting footprint area
  primary_detection_confidence - confidence score for primary identification method

Each function accepts the scene YAML dict and dump_data dict produced by
validation.scene_calc.dump.dump_scene_geometry, and returns a float in [0, 100]
or None when required data is absent (NotReady semantics).

Dump schema reference:
  dump_data['placements'] is a list of dicts with keys:
    placement_name, kind, asset_path, visual_bbox, footprint_bbox,
    placement_bbox, label_bbox, aspect_delta_pct, scale_source
  Each bbox is {x, y, w, h} (placement-level; x=left, y=top, w=width, h=height).
  dump_data['scene_bounds'] is {left, right, top, bottom} in scene-%.
"""



#============================================
# Internal helpers
#============================================

def _footprint_area(bbox: dict[str, float]) -> float:
	"""Return footprint area (w * h) from a {x, y, w, h} bbox dict.

	Args:
		bbox: Dict with keys x, y, w, h in scene-%.

	Returns:
		Area as scene-% squared (w * h).
	"""
	return bbox['w'] * bbox['h']


def _scene_area(scene_bounds: dict[str, float]) -> float:
	"""Return scene area from scene_bounds {left, right, top, bottom}.

	Args:
		scene_bounds: Dict with left, right, top, bottom in scene-%.

	Returns:
		Area as (right - left) * (bottom - top).
	"""
	width = scene_bounds['right'] - scene_bounds['left']
	height = scene_bounds['bottom'] - scene_bounds['top']
	return width * height


def _identify_primary(scene: dict[str, object], dump_data: dict[str, object]) -> dict[str, object] | None:
	"""Identify the primary placement from scene YAML.

	Detection order:
	  1. Placement with data-primary == True in scene YAML (explicit tag).
	  2. Largest footprint_bbox area in dump_data (heuristic fallback).

	Args:
		scene: Parsed scene YAML dict (placements list with optional data-primary field).
		dump_data: Dump dict from dump_scene_geometry.

	Returns:
		The dump placement entry for the primary, or None if no placements.
	"""
	scene_placements = scene.get('placements', [])
	dump_placements = dump_data.get('placements', [])

	if not dump_placements:
		return None

	# Build index from placement_name -> dump entry.
	dump_by_name: dict[str, dict[str, object]] = {}
	for dp in dump_placements:
		dump_by_name[dp['placement_name']] = dp

	# Step 1: explicit data-primary tag.
	for sp in scene_placements:
		if sp.get('data-primary') is True:
			name = sp.get('placement_name', '')
			if name in dump_by_name:
				return dump_by_name[name]

	# Step 2: heuristic - largest footprint area.
	best: dict[str, object] | None = None
	best_area = -1.0
	for dp in dump_placements:
		area = _footprint_area(dp['footprint_bbox'])
		if area > best_area:
			best_area = area
			best = dp

	return best


def _is_primary_explicit(scene: dict[str, object]) -> bool:
	"""Return True if any placement has data-primary explicitly set to True.

	Args:
		scene: Parsed scene YAML dict.

	Returns:
		True if an explicit data-primary tag is present.
	"""
	for sp in scene.get('placements', []):
		if sp.get('data-primary') is True:
			return True
	return False


#============================================
# Metric: primary_area_ratio
#============================================

def primary_area_ratio(scene: dict[str, object], dump_data: dict[str, object]) -> float | None:
	"""Ratio of primary placement footprint area to total footprint area, 0-100.

	Definition (SCENE_DESIGN_LINT_PLAN.md "Hierarchy"):
	  primary footprint_bbox area / sum of all footprint_bbox areas

	Returns a value in [0, 100] where 100 means the primary occupies all area.
	Returns None if dump_data has no placements or scene_bounds is missing.

	Args:
		scene: Parsed scene YAML dict.
		dump_data: Dump dict from dump_scene_geometry.

	Returns:
		Float in [0, 100], or None if required data is absent.
	"""
	dump_placements = dump_data.get('placements')
	if not dump_placements:
		return None

	# Identify primary placement.
	primary = _identify_primary(scene, dump_data)
	if primary is None:
		return None

	# Sum all footprint areas.
	total_area = sum(_footprint_area(dp['footprint_bbox']) for dp in dump_placements)
	if total_area <= 0.0:
		return None

	primary_area = _footprint_area(primary['footprint_bbox'])
	# Express as 0-100 score.
	ratio_score = (primary_area / total_area) * 100.0
	return ratio_score


#============================================
# Metric: primary_prominence
#============================================

def primary_prominence(scene: dict[str, object], dump_data: dict[str, object]) -> float | None:
	"""Score combining primary area ratio and primary zone position, 0-100.

	Definition (SCENE_DESIGN_LINT_PLAN.md "Hierarchy"):
	  primary footprint / largest supporting footprint, normalized to [0, 100].

	A ratio of >=2.0 (primary is twice the largest supporter) earns 100.
	A ratio of 1.0 (same size) earns 50. A ratio of 0 earns 0.
	Normalized as: min(ratio / 2.0, 1.0) * 100.

	Returns None if dump_data has no placements or fewer than 2 placements
	(no supporter exists).

	Args:
		scene: Parsed scene YAML dict.
		dump_data: Dump dict from dump_scene_geometry.

	Returns:
		Float in [0, 100], or None if required data is absent.
	"""
	dump_placements = dump_data.get('placements')
	if not dump_placements or len(dump_placements) < 2:
		return None

	primary = _identify_primary(scene, dump_data)
	if primary is None:
		return None

	primary_area = _footprint_area(primary['footprint_bbox'])

	# Find the largest supporting (non-primary) placement area.
	largest_support_area = 0.0
	for dp in dump_placements:
		if dp['placement_name'] == primary['placement_name']:
			continue
		area = _footprint_area(dp['footprint_bbox'])
		if area > largest_support_area:
			largest_support_area = area

	if largest_support_area <= 0.0:
		# All supporters have zero area; primary can't be compared.
		return None

	# Ratio of primary to largest supporter.
	ratio = primary_area / largest_support_area
	# Normalize: target >= 2.0 earns 100.
	score = min(ratio / 2.0, 1.0) * 100.0
	return score


#============================================
# Metric: primary_detection_confidence
#============================================

def primary_detection_confidence(scene: dict[str, object]) -> float | None:
	"""Confidence score for primary identification method.

	Definition (SCENE_DESIGN_LINT_PLAN.md "Hierarchy"):
	  'data-primary' tagged vs fallback (tagged preferred).

	Returns:
	  100.0 if any placement has data-primary=True (explicit tag).
	   50.0 if primary is heuristically derived (fallback to largest footprint).
	  None if scene has no placements at all.

	Args:
		scene: Parsed scene YAML dict.

	Returns:
		Float (100.0 or 50.0), or None if no placements present.
	"""
	placements = scene.get('placements', [])
	if not placements:
		return None

	if _is_primary_explicit(scene):
		return 100.0

	# Heuristic fallback: lower confidence.
	return 50.0
