"""Composition health metrics: structural variety and authoring quality.

Implements three composition health metrics defined in SCENE_DESIGN_LINT_PLAN.md
section "Composition health":

  tab_stops_symmetry  - distribution evenness of placement left-edges
  depth_tier_usage    - fraction of available z/depth tiers used
  aspect_fidelity     - mean inverse of predicted aspect distortion

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

def _bbox_valid(bbox: dict[str, float]) -> bool:
	"""Return True if bbox has positive area (not a zero-sentinel).

	Args:
		bbox: Dict with keys x, y, w, h.

	Returns:
		True if w > 0 and h > 0.
	"""
	return bbox['w'] > 0.0 and bbox['h'] > 0.0


#============================================
# Metric: tab_stops_symmetry
#============================================

def tab_stops_symmetry(scene: dict[str, object], dump_data: dict[str, object]) -> float | None:
	"""Distribution evenness of placement left-edges, as 0-100.

	Definition (SCENE_DESIGN_LINT_PLAN.md "Composition health"):
	  for zones using tab-stops, max/min of left/center/right footprint sums;
	  target <=3x.

	Measures how evenly placement left-edges (tab-stops) are distributed
	across the scene width. Divides the scene width into three equal columns
	(left, center, right) and sums the footprint width of placements whose
	left-edge falls in each column. Score penalizes imbalance between columns.

	Formula:
	  Divide scene width into thirds: left, center, right.
	  For each populated column, sum footprint widths of placements
	  whose footprint_bbox.x falls within that column.
	  ratio = max_sum / min_sum over populated columns.
	  score = max(0, 100 - (ratio - 1.0) * 20.0)
	    ratio 1.0 (perfect) -> 100
	    ratio 3.0 (target boundary) -> 60
	    ratio 6.0 -> 0

	Returns None if fewer than 2 populated columns exist (symmetry is
	undefined with fewer than 2 groups).

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

	scene_left = scene_bounds['left']
	scene_right = scene_bounds['right']
	scene_width = scene_right - scene_left

	if scene_width <= 0.0:
		return None

	# Divide scene width into three equal thirds.
	third = scene_width / 3.0
	left_boundary = scene_left + third
	right_boundary = scene_left + 2 * third

	# Sum footprint widths per column based on placement left-edge.
	column_sums = [0.0, 0.0, 0.0]  # left, center, right

	for dp in dump_placements:
		foot = dp['footprint_bbox']
		if not _bbox_valid(foot):
			# Skip zero-area (skipped_error) placements.
			continue
		foot_left = foot['x']
		foot_width = foot['w']
		# Assign to column based on which third contains the left edge.
		if foot_left < left_boundary:
			column_sums[0] += foot_width
		elif foot_left < right_boundary:
			column_sums[1] += foot_width
		else:
			column_sums[2] += foot_width

	# Only consider populated columns.
	populated = [s for s in column_sums if s > 0.0]

	if len(populated) < 2:
		# Fewer than 2 populated columns: symmetry is undefined.
		return None

	max_sum = max(populated)
	min_sum = min(populated)

	if min_sum <= 0.0:
		return 0.0

	# Ratio of most to least loaded column.
	ratio = max_sum / min_sum
	# Score: 100 at ratio=1, decreasing 20 per unit above 1.
	score = max(0.0, 100.0 - (ratio - 1.0) * 20.0)
	return score


#============================================
# Metric: depth_tier_usage
#============================================

def depth_tier_usage(scene: dict[str, object], dump_data: dict[str, object]) -> float | None:
	"""Fraction of available depth tiers used by placements, as 0-100.

	Definition (SCENE_DESIGN_LINT_PLAN.md "Composition health"):
	  does the scene exercise tiers 1/2/3 or is it flat;
	  scenes with >=5 placements should use >=2 tiers.

	Depth tiers are inferred from the z value in scene YAML placements, or
	from zone association (rear zones = tier 1, center/front zones = tier 2,
	explicit foreground = tier 3). Three total tiers are assumed.

	Implementation uses z values from scene YAML placements when present.
	A unique z value counts as a distinct tier. When z values are absent,
	zone names are used as a proxy (rear* = 1, front*/foreground* = 3,
	else = 2). The score rewards using more of the 3 available tiers.

	Formula:
	  distinct_tiers = count of unique depth levels used
	  tier_fraction = distinct_tiers / 3
	  score = min(100.0, tier_fraction * 100.0)
	    1 tier -> 33.3
	    2 tiers -> 66.7
	    3 tiers -> 100.0

	Returns None if scene has no placements.

	Args:
		scene: Parsed scene YAML dict.
		dump_data: Dump dict from dump_scene_geometry.

	Returns:
		Float in [0, 100], or None if required data is absent.
	"""
	scene_placements = scene.get('placements', [])
	if not scene_placements:
		return None

	# Collect z values or zone-derived tier values.
	tiers: set[int] = set()

	for sp in scene_placements:
		# Prefer explicit z value when present.
		z_value = sp.get('z')
		if z_value is not None:
			# Clamp to tier range 1-3.
			clamped = max(1, min(3, int(z_value)))
			tiers.add(clamped)
		else:
			# Derive tier from zone name.
			zone_id = sp.get('zone', '').lower()
			if zone_id.startswith('rear') or 'background' in zone_id:
				tiers.add(1)
			elif zone_id.startswith('front') or 'foreground' in zone_id:
				tiers.add(3)
			else:
				tiers.add(2)

	distinct_tiers = len(tiers)
	# Three total tiers assumed (background/mid/foreground).
	total_tiers = 3
	tier_fraction = distinct_tiers / total_tiers
	# Score: fraction of tiers used, 0-100.
	score = min(100.0, tier_fraction * 100.0)
	return score


#============================================
# Metric: aspect_fidelity
#============================================

def aspect_fidelity(scene: dict[str, object], dump_data: dict[str, object]) -> float | None:
	"""Mean inverse of predicted aspect distortion across placements, as 0-100.

	Definition (SCENE_DESIGN_LINT_PLAN.md "Composition health"):
	  mean inverse of predicted aspect distortion across placements;
	  target >=95%.

	The render predictor computes aspect_delta_pct per placement (binary:
	>5% -> ESCAPE_REQUIRED). This metric uses the same value but averages
	it as a continuous score component. A scene where all placements have
	0% distortion scores 100; distortion reduces the score proportionally.

	Formula:
	  aspect_fidelity = 100 - mean(aspect_delta_pct over valid placements)
	  score = max(0, aspect_fidelity)
	    all placements at 0% delta -> 100.0
	    mean 5% delta (all at target boundary) -> 95.0
	    mean 100% delta -> 0.0

	Skips placements with scale_source == 'skipped_error' (no reliable
	aspect data).

	Returns None if no valid aspect data exists (all placements skipped or
	dump placements key missing).

	Args:
		scene: Parsed scene YAML dict. (Not used; included for API uniformity.)
		dump_data: Dump dict from dump_scene_geometry.

	Returns:
		Float in [0, 100], or None if required data is absent.
	"""
	dump_placements = dump_data.get('placements')
	if not dump_placements:
		return None

	# Collect aspect_delta_pct for placements with reliable aspect data.
	delta_pcts: list[float] = []
	for dp in dump_placements:
		scale_source = dp.get('scale_source', '')
		if scale_source == 'skipped_error':
			# No reliable aspect data for this placement; skip.
			continue
		delta_pct = dp.get('aspect_delta_pct', 0.0)
		delta_pcts.append(float(delta_pct))

	if not delta_pcts:
		return None

	mean_delta = sum(delta_pcts) / len(delta_pcts)
	# Score: 100 minus mean distortion percentage.
	score = max(0.0, 100.0 - mean_delta)
	return score
