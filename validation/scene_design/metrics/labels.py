"""Label hygiene metrics: text readable, not packed.

Implements three label hygiene metrics defined in SCENE_DESIGN_LINT_PLAN.md
section "Label hygiene - text readable, not packed":

  predicted_label_overlap    - fraction of placements whose label_bbox intersects
                               another placement's footprint_bbox or label_bbox
  label_to_object_distance   - average gap between label_bbox and footprint_bbox
  label_wrap_rate            - fraction of placements whose label spans multiple lines

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

import math
from typing import Any


# Estimated single-line label height in scene-% units.
# Labels taller than this value are considered wrapped.
_SINGLE_LINE_HEIGHT_SCENE_PCT = 5.0


#============================================
# Internal helpers
#============================================

def _bbox_right(bbox: dict[str, float]) -> float:
	"""Return the right edge of a {x, y, w, h} bbox.

	Args:
		bbox: Dict with keys x, y, w, h.

	Returns:
		x + w.
	"""
	return bbox['x'] + bbox['w']


def _bbox_bottom(bbox: dict[str, float]) -> float:
	"""Return the bottom edge of a {x, y, w, h} bbox.

	Args:
		bbox: Dict with keys x, y, w, h.

	Returns:
		y + h.
	"""
	return bbox['y'] + bbox['h']


def _bboxes_overlap(a: dict[str, float], b: dict[str, float]) -> bool:
	"""Return True if two {x, y, w, h} bboxes overlap (share any area).

	Two bboxes overlap unless one is entirely to the left, right, above,
	or below the other.

	Args:
		a: First bbox {x, y, w, h}.
		b: Second bbox {x, y, w, h}.

	Returns:
		True if the two bboxes intersect.
	"""
	# No overlap if one is completely outside the other.
	if _bbox_right(a) <= b['x']:
		return False
	if _bbox_right(b) <= a['x']:
		return False
	if _bbox_bottom(a) <= b['y']:
		return False
	if _bbox_bottom(b) <= a['y']:
		return False
	return True


def _bbox_center(bbox: dict[str, float]) -> tuple[float, float]:
	"""Return the (cx, cy) center of a {x, y, w, h} bbox.

	Args:
		bbox: Dict with keys x, y, w, h.

	Returns:
		Tuple (cx, cy).
	"""
	cx = bbox['x'] + bbox['w'] / 2.0
	cy = bbox['y'] + bbox['h'] / 2.0
	return cx, cy


def _bbox_valid(bbox: dict[str, float]) -> bool:
	"""Return True if a bbox has positive area (not a zero-sentinel).

	Args:
		bbox: Dict with keys x, y, w, h.

	Returns:
		True if w > 0 and h > 0.
	"""
	return bbox['w'] > 0.0 and bbox['h'] > 0.0


#============================================
# Metric: predicted_label_overlap
#============================================

def predicted_label_overlap(scene: dict[str, Any], dump_data: dict[str, Any]) -> float | None:
	"""Fraction of placements whose label_bbox overlaps another placement's bbox, as 0-100.

	Definition (SCENE_DESIGN_LINT_PLAN.md "Label hygiene"):
	  Stage 9 residual collisions after 3-pass nudge.
	  Target: 0 collisions (score 100).

	A label_bbox is considered overlapping if it intersects with any other
	placement's footprint_bbox or label_bbox (excluding itself). Score is
	100 minus the overlap fraction scaled to 0-100.

	Formula:
	  overlap_fraction = overlapping_count / total_count
	  score = max(0, 100 - overlap_fraction * 100)

	This means any overlap drives the score below 100, and a scene where
	all labels overlap scores 0.

	A single valid label scores 100 because no other label or footprint can
	overlap it. Returns None only when placement or label evidence is absent.

	Args:
		scene: Parsed scene YAML dict. (Not used; included for API uniformity.)
		dump_data: Dump dict from dump_scene_geometry.

	Returns:
		Float in [0, 100], or None if required data is absent.
	"""
	dump_placements = dump_data.get('placements')
	if not dump_placements:
		return None

	# Only consider placements with valid label bboxes.
	valid = [dp for dp in dump_placements if _bbox_valid(dp['label_bbox'])]
	if not valid:
		return None
	if len(valid) == 1:
		return 100.0

	# Count placements whose label overlaps any other placement's footprint or label.
	overlapping_count = 0
	for i, dp in enumerate(valid):
		label = dp['label_bbox']
		has_overlap = False
		for j, other in enumerate(valid):
			if i == j:
				continue
			# Check overlap with the other placement's footprint_bbox.
			if _bbox_valid(other['footprint_bbox']) and _bboxes_overlap(label, other['footprint_bbox']):
				has_overlap = True
				break
			# Check overlap with the other placement's label_bbox.
			if _bbox_valid(other['label_bbox']) and _bboxes_overlap(label, other['label_bbox']):
				has_overlap = True
				break
		if has_overlap:
			overlapping_count += 1

	total = len(valid)
	overlap_fraction = overlapping_count / total
	# Score: 100 when no overlaps, 0 when all labels overlap.
	score = max(0.0, 100.0 - overlap_fraction * 100.0)
	return score


#============================================
# Metric: label_to_object_distance
#============================================

def label_to_object_distance(scene: dict[str, Any], dump_data: dict[str, Any]) -> float | None:
	"""Average gap between label_bbox and the footprint_bbox it labels, as 0-100.

	Definition (SCENE_DESIGN_LINT_PLAN.md "Label hygiene"):
	  mean label-center to placement-center distance; within zone padding.

	Measures the Euclidean distance between the center of label_bbox and the
	center of footprint_bbox for each placement. Normalizes by the scene
	diagonal. Score is 100 at distance 0, decreasing as the average gap grows.

	Formula:
	  for each placement: dist = sqrt((label_cx - foot_cx)^2 + (label_cy - foot_cy)^2)
	  mean_dist = mean(dist) over all valid placements
	  dist_normalized = mean_dist / scene_diagonal
	  score = max(0, 100 - dist_normalized * 400)
	    0.0  normalized -> 100
	    0.25 normalized ->   0

	Returns None if scene_bounds is missing or no valid placements exist.

	Args:
		scene: Parsed scene YAML dict. (Not used; included for API uniformity.)
		dump_data: Dump dict from dump_scene_geometry.

	Returns:
		Float in [0, 100], or None if required data is absent.
	"""
	scene_bounds = dump_data.get('scene_bounds')
	dump_placements = dump_data.get('placements')

	if not scene_bounds or not dump_placements:
		return None

	# Compute scene diagonal for normalization.
	scene_w = scene_bounds['right'] - scene_bounds['left']
	scene_h = scene_bounds['bottom'] - scene_bounds['top']
	scene_diagonal = math.sqrt(scene_w * scene_w + scene_h * scene_h)

	if scene_diagonal <= 0.0:
		return None

	# Compute center-to-center distance for each valid placement pair.
	distances: list[float] = []
	for dp in dump_placements:
		foot = dp['footprint_bbox']
		label = dp['label_bbox']
		# Skip zero-area placements or zero-area labels.
		if not _bbox_valid(foot) or not _bbox_valid(label):
			continue
		foot_cx, foot_cy = _bbox_center(foot)
		label_cx, label_cy = _bbox_center(label)
		dist = math.sqrt((label_cx - foot_cx) ** 2 + (label_cy - foot_cy) ** 2)
		distances.append(dist)

	if not distances:
		return None

	mean_dist = sum(distances) / len(distances)
	# Normalize by scene diagonal.
	dist_normalized = mean_dist / scene_diagonal
	# Score: 100 at distance 0, 0 at dist_normalized >= 0.25.
	score = max(0.0, 100.0 - dist_normalized * 400.0)
	return score


#============================================
# Metric: label_wrap_rate
#============================================

def label_wrap_rate(scene: dict[str, Any], dump_data: dict[str, Any]) -> float | None:
	"""Fraction of placements whose label spans multiple lines, as 0-100.

	Definition (SCENE_DESIGN_LINT_PLAN.md "Label hygiene"):
	  fraction of labels Stage 9 wrapped; target <=0.20.

	Detects multi-line labels by comparing label_bbox height to the estimated
	single-line label height (_SINGLE_LINE_HEIGHT_SCENE_PCT). If the label
	height exceeds the single-line threshold, the label is considered wrapped.

	Formula:
	  wrapped_count = count of placements with label_bbox.h > single_line_height
	  wrap_fraction = wrapped_count / total_valid_count
	  score = max(0, 100 - wrap_fraction * 100)
	    0.0 wrap_fraction -> 100
	    0.20 -> 80 (at target boundary)
	    1.0 -> 0

	Returns None if no valid placements exist.

	Args:
		scene: Parsed scene YAML dict. (Not used; included for API uniformity.)
		dump_data: Dump dict from dump_scene_geometry.

	Returns:
		Float in [0, 100], or None if required data is absent.
	"""
	dump_placements = dump_data.get('placements')
	if not dump_placements:
		return None

	# Filter to placements with valid label bboxes.
	valid = [dp for dp in dump_placements if _bbox_valid(dp['label_bbox'])]
	if not valid:
		return None

	# Count labels that exceed single-line height.
	wrapped_count = 0
	for dp in valid:
		label_h = dp['label_bbox']['h']
		if label_h > _SINGLE_LINE_HEIGHT_SCENE_PCT:
			wrapped_count += 1

	wrap_fraction = wrapped_count / len(valid)
	# Score: 100 at no wrapped labels, 0 at all labels wrapped.
	score = max(0.0, 100.0 - wrap_fraction * 100.0)
	return score
