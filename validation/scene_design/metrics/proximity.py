"""Proximity metrics: related things near each other.

Implements two proximity metrics defined in SCENE_DESIGN_LINT_PLAN.md
section "Proximity - related things near each other":

  support_distance        - mean Euclidean distance from supporting placements to primary center
  protocol_step_affinity  - SKELETON ONLY (returns None; protocol vocab access not yet wired)

Each function accepts the scene YAML dict and dump_data dict produced by
validation.scene_calc.dump.dump_scene_geometry, and returns a float in [0, 100]
or None when required data is absent (NotReady semantics).

Dump schema reference:
  dump_data['placements'] list of dicts with keys:
    placement_name, kind, footprint_bbox ({x, y, w, h}), etc.
  dump_data['scene_bounds'] {left, right, top, bottom} in scene-%.
"""

import math


#============================================
# Internal helpers
#============================================

def _footprint_area(bbox: dict[str, float]) -> float:
	"""Return footprint area (w * h) from a {x, y, w, h} bbox dict.

	Args:
		bbox: Dict with keys x, y, w, h in scene-%.

	Returns:
		Area as w * h.
	"""
	return bbox['w'] * bbox['h']


def _bbox_center(bbox: dict[str, float]) -> tuple[float, float]:
	"""Return the (cx, cy) center of a {x, y, w, h} bbox dict.

	Args:
		bbox: Dict with keys x, y, w, h in scene-%.

	Returns:
		Tuple (cx, cy) where cx = x + w/2, cy = y + h/2.
	"""
	cx = bbox['x'] + bbox['w'] / 2.0
	cy = bbox['y'] + bbox['h'] / 2.0
	return cx, cy


def _scene_diagonal(scene_bounds: dict[str, float]) -> float:
	"""Compute the diagonal length of the scene in scene-% units.

	Args:
		scene_bounds: Dict with left, right, top, bottom in scene-%.

	Returns:
		Euclidean diagonal: sqrt((right-left)^2 + (bottom-top)^2).
	"""
	width = scene_bounds['right'] - scene_bounds['left']
	height = scene_bounds['bottom'] - scene_bounds['top']
	return math.sqrt(width * width + height * height)


def _identify_primary(scene: dict[str, object], dump_data: dict[str, object]) -> dict[str, object] | None:
	"""Identify the primary placement from scene YAML.

	Detection order:
	  1. Placement with data-primary == True in scene YAML (explicit tag).
	  2. Largest footprint_bbox area in dump_data (heuristic fallback).

	Args:
		scene: Parsed scene YAML dict.
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


#============================================
# Metric: support_distance
#============================================

def support_distance(scene: dict[str, object], dump_data: dict[str, object]) -> float | None:
	"""Mean Euclidean distance from supporting placements to primary center, 0-100.

	Definition (SCENE_DESIGN_LINT_PLAN.md "Proximity"):
	  Mean Euclidean distance from supporting placements to primary center,
	  normalized by scene diagonal. Target: <=0.30.

	Score: normalized distance in [0, 1] mapped to [0, 100].
	  distance_normalized = mean_distance / scene_diagonal
	  score = max(0, 100 - distance_normalized * 200.0)
	    distance 0.0 -> score 100
	    distance 0.30 -> score 40
	    distance 0.50 -> score 0

	Returns None if:
	  - dump_data has no placements
	  - fewer than 2 placements (no supporter)
	  - scene_bounds is missing
	  - scene diagonal is zero

	Args:
		scene: Parsed scene YAML dict.
		dump_data: Dump dict from dump_scene_geometry.

	Returns:
		Float in [0, 100], or None if required data is absent.
	"""
	scene_bounds = dump_data.get('scene_bounds')
	dump_placements = dump_data.get('placements')

	if not scene_bounds or not dump_placements or len(dump_placements) < 2:
		return None

	diagonal = _scene_diagonal(scene_bounds)
	if diagonal <= 0.0:
		return None

	primary = _identify_primary(scene, dump_data)
	if primary is None:
		return None

	primary_cx, primary_cy = _bbox_center(primary['footprint_bbox'])

	# Compute distance from each supporter to the primary center.
	distances: list[float] = []
	for dp in dump_placements:
		if dp['placement_name'] == primary['placement_name']:
			continue
		# Skip zero-size placements (skipped_error sentinel).
		if dp['footprint_bbox']['w'] <= 0.0 or dp['footprint_bbox']['h'] <= 0.0:
			continue
		cx, cy = _bbox_center(dp['footprint_bbox'])
		dist = math.sqrt((cx - primary_cx) ** 2 + (cy - primary_cy) ** 2)
		distances.append(dist)

	if not distances:
		return None

	mean_distance = sum(distances) / len(distances)
	# Normalize by scene diagonal.
	distance_normalized = mean_distance / diagonal
	# Score: target <= 0.30; higher distance -> lower score.
	score = max(0.0, 100.0 - distance_normalized * 200.0)
	return score


#============================================
# Metric: protocol_step_affinity (SKELETON)
#============================================

def protocol_step_affinity(scene: dict[str, object]) -> float | None:
	"""SKELETON: fraction of step-co-used items in same or adjacent zones.

	Definition (SCENE_DESIGN_LINT_PLAN.md "Proximity"):
	  For protocol-linked scenes, fraction of step-co-used items in same or
	  adjacent zones. Target: >=0.80.

	This function is a skeleton only. It always returns None because
	protocol vocabulary access (linking a scene to its protocol step
	co-usage data) is not yet wired. This metric will be implemented
	in a follow-up work package once protocol vocab access is available.

	Args:
		scene: Parsed scene YAML dict. (Not used in skeleton.)

	Returns:
		None always (NotReady semantics; aggregate_score will skip this metric).
	"""
	# Skeleton: protocol vocab not yet wired.
	# Implement when protocol_step -> co-used placement mapping is available.
	return None
