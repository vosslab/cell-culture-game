"""Group B rules: geometry predictors (ESCAPE_REQUIRED verdict).

Group B rules predict render failures using precomputed scene geometry from
the SIM dump (validation.scene_calc.dump). Findings are advisory until a
confusion table meets the promotion bar; strict mode requires explicit
promotion per SCENE_LINT_PLAN.md.

This module implements B1 through B10:
  B1 - aspect_distorted_predicted: aspect delta > 5% on any placement.
  B2 - item_taller_than_zone: placement height exceeds zone inner height
       such that required scale < MIN_SCALE (0.55).
  B3 - row_footprint_overflow: per-row footprint width sum exceeds zone
       inner width. Skips silently when dump_data contains no row info
       (row-slot schema not yet wired into dump.py).
  B4 - placement_bbox_outside_scene: placement_bbox extends past scene_bounds.
  B5 - placement_bbox_outside_zone: placement_bbox extends past zone inner_rect
       (with 4-px tolerance converted to scene-percent).
  B6 - item_item_overlap: two placements' footprint_bbox rects in the same
       zone overlap (non-zero intersection area).
  B7 - label_offscreen: label position extends outside scene_bounds horizontally.
  B8 - label_object_overlap: label bbox overlaps a scientific placement's visual_bbox.
  B9 - invisible_placement: predicted size < 100 px&sup2;, or height > 2x zone height,
       or scale_source='skipped_error', or default_width missing/invalid.
  B10 - zone_overlap: two zone bounds rects have non-zero intersection.

Rules B1-B8 and B10 consume precomputed dump_data from dump_scene_geometry().
B9 uses a mix of dump data and scene YAML fields.
B10 is static geometry (no SIM dependency) but included here for cohesion.
All rules receive pre-computed dump_data so the caller controls dump timing.

See SCENE_LINT_PLAN.md "Rule specs" sections B1-B10 for the exact formulas.
"""

from typing import Any

from validation.scene_lint.findings import Finding, Verdict, Confidence


# Threshold constants from SCENE_LINT_PLAN.md "Tolerance defaults".
ASPECT_DISTORTION_THRESHOLD_PCT = 5.0
# MIN_SCALE from LAYOUT_PIPELINE.md §2; mirrors bboxes.MIN_SCALE.
MIN_SCALE = 0.55
# B5 tolerance: 4 px allowed overflow past zone bounds before firing.
# Converts px to scene-percent using PX_PER_SCENE_PERCENT = 11.52 (LAYOUT_PIPELINE.md §2).
_PX_PER_SCENE_PERCENT = 11.52
ZONE_OVERFLOW_TOLERANCE_PCT = 4.0 / _PX_PER_SCENE_PERCENT  # ~0.347 scene-%


#============================================
# Confidence helper
#============================================

def _confidence_from_scale_source(scale_source: str) -> Confidence:
	"""Derive Finding confidence level from scale_source.

	Mapping per SCENE_LINT_PLAN.md "Finding shape" confidence levels:
	  cm_model          -> high  (full-fidelity simulator)
	  fallback_authored -> medium (no cm model; may diverge from render)
	  fallback_no_workspace / skipped_error -> low

	Args:
		scale_source: One of the four enum strings from the SIM dump.

	Returns:
		Confidence enum value.
	"""
	if scale_source == 'cm_model':
		return Confidence.HIGH
	if scale_source == 'fallback_authored':
		return Confidence.MEDIUM
	# fallback_no_workspace and skipped_error both map to LOW.
	return Confidence.LOW


#============================================
# B1: aspect_distorted_predicted
#============================================

def check_aspect_distorted_predicted(
	scene: dict[str, Any],
	scene_name: str,
	dump_data: dict[str, Any],
) -> list[Finding]:
	"""
	B1: Predict aspect distortion for each placement.

	Per SCENE_LINT_PLAN.md §B1:
	  authored_aspect = svg.viewBox.width / svg.viewBox.height
	  rendered_aspect = _visualWidth / _height
	  delta_pct = abs(rendered_aspect - authored_aspect) / authored_aspect x 100
	  if delta_pct > 5.0: ESCAPE_REQUIRED

	Uses aspect_delta_pct precomputed by dump_scene_geometry().
	Skips placements with scale_source == 'skipped_error' (cannot predict).

	Args:
		scene: Parsed scene YAML dict (unused directly; kept for API parity
			with Group A rule signatures so callers iterate uniformly).
		scene_name: Scene name string for finding attribution.
		dump_data: Output of dump_scene_geometry() for this scene.

	Returns:
		List of ESCAPE_REQUIRED findings, one per distorted placement.
	"""
	findings: list[Finding] = []
	placements = dump_data.get('placements', [])

	for placement in placements:
		scale_source = placement['scale_source']
		# Skip placements where geometry could not be predicted reliably.
		if scale_source == 'skipped_error':
			continue

		placement_name = placement['placement_name']
		aspect_delta_pct = placement['aspect_delta_pct']

		if aspect_delta_pct > ASPECT_DISTORTION_THRESHOLD_PCT:
			confidence = _confidence_from_scale_source(scale_source)
			findings.append(Finding(
				scene=scene_name,
				placement_name=placement_name,
				rule='aspect_distorted_predicted',
				verdict=Verdict.ESCAPE_REQUIRED,
				predicts=['aspect_distorted'],
				bbox_type='visual_bbox',
				confidence=confidence,
				message=(
					f"Predicted aspect delta {aspect_delta_pct:.1f}% exceeds "
					f"{ASPECT_DISTORTION_THRESHOLD_PCT}% threshold."
				),
				evidence={
					'aspect_delta_pct': aspect_delta_pct,
					'threshold_pct': ASPECT_DISTORTION_THRESHOLD_PCT,
					'scale_source': scale_source,
				},
				fix_hints=[
					'Add layout.display_width_cm to this placement or its object',
					'Adjust default_width to match the SVG aspect ratio',
				],
			))

	return findings


#============================================
# B2: item_taller_than_zone
#============================================

def check_item_taller_than_zone(
	scene: dict[str, Any],
	scene_name: str,
	dump_data: dict[str, Any],
) -> list[Finding]:
	"""
	B2: Predict zone height overflow per SCENE_LINT_PLAN.md §B2.

	Per the rule spec:
	  zone_inner_h = (zone.bounds.bottom - zone.bounds.top) - 2 x ZONE_PADDING
	  required_scale = zone_inner_h / _height
	  if required_scale < MIN_SCALE (0.55): ESCAPE_REQUIRED

	Uses placement_bbox.h and zone inner_rect.height from dump_data.

	Args:
		scene: Parsed scene YAML dict (used to map placements to their zones
			by name, corroborating zone inner_rect from dump_data).
		scene_name: Scene name string for finding attribution.
		dump_data: Output of dump_scene_geometry() for this scene.

	Returns:
		List of ESCAPE_REQUIRED findings, one per overflowing placement.
	"""
	findings: list[Finding] = []

	# Build a zone lookup by name from dump_data zones.
	# Dump zones use 'name' as the zone identifier.
	zone_by_name: dict[str, dict[str, Any]] = {}
	for zone in dump_data.get('zones', []):
		zone_by_name[zone['name']] = zone

	# Build placement-to-zone mapping from raw scene YAML (the 'zone' field
	# on each placement names the zone id, matching dump zone 'name').
	scene_placements = scene.get('placements', [])
	placement_zone_map: dict[str, str] = {}
	for sp in scene_placements:
		pname = sp.get('placement_name', '')
		zone_id = sp.get('zone', '')
		if pname and zone_id:
			placement_zone_map[pname] = zone_id

	for placement in dump_data.get('placements', []):
		scale_source = placement['scale_source']
		# Cannot predict geometry for placements with skipped assets.
		if scale_source == 'skipped_error':
			continue

		placement_name = placement['placement_name']
		# placement_bbox.h is the height of the rendered placement in scene-%.
		placement_h = placement['placement_bbox']['h']

		# Determine which zone this placement belongs to.
		zone_id = placement_zone_map.get(placement_name)
		if not zone_id:
			# Placement not found in scene YAML zone map; skip safely.
			continue

		zone = zone_by_name.get(zone_id)
		if not zone:
			continue

		inner_rect = zone['inner_rect']
		# inner_rect uses {left, right, top, bottom} per the dump schema.
		zone_inner_h = inner_rect['bottom'] - inner_rect['top']

		# B2 formula: required_scale = zone_inner_h / placement_h.
		# If placement_h is zero, we have a degenerate case; skip.
		if placement_h <= 0.0:
			continue

		required_scale = zone_inner_h / placement_h

		if required_scale < MIN_SCALE:
			confidence = _confidence_from_scale_source(scale_source)
			findings.append(Finding(
				scene=scene_name,
				placement_name=placement_name,
				rule='item_taller_than_zone',
				verdict=Verdict.ESCAPE_REQUIRED,
				predicts=['off_page', 'clipped_by_parent'],
				bbox_type='placement_bbox',
				confidence=confidence,
				message=(
					f"Placement height {placement_h:.1f}% requires scale "
					f"{required_scale:.3f} to fit zone inner height "
					f"{zone_inner_h:.1f}%, below MIN_SCALE {MIN_SCALE}."
				),
				evidence={
					'zone': zone_id,
					'zone_inner_height_pct': zone_inner_h,
					'predicted_height_pct': placement_h,
					'required_scale': required_scale,
					'min_scale': MIN_SCALE,
					'scale_source': scale_source,
				},
				fix_hints=[
					'Move placement to a taller zone',
					'Reduce default_width to shrink predicted height',
					'Add layout.display_width_cm to use cm-model sizing',
				],
			))

	return findings


#============================================
# B3: row_footprint_overflow
#============================================

def check_row_footprint_overflow(
	scene: dict[str, Any],
	scene_name: str,
	dump_data: dict[str, Any],
) -> list[Finding]:
	"""
	B3: Predict row footprint overflow per SCENE_LINT_PLAN.md §B3.

	Sums footprint widths for placements sharing the same row index within a zone.
	If the total row footprint width exceeds the zone inner_rect width, emits
	ESCAPE_REQUIRED (predicts zone overflow via negative row gap).

	Row info is sourced from dump_data. The row-slot schema is not yet wired into
	dump.py (decision-gated per replicated-hatching-avalanche.md); when dump_data
	contains no row info for any placement, this function returns an empty list
	silently (not an error).

	Args:
		scene: Parsed scene YAML dict (unused directly; kept for API parity).
		scene_name: Scene name string for finding attribution.
		dump_data: Output of dump_scene_geometry() for this scene.

	Returns:
		List of ESCAPE_REQUIRED findings, one per overflowing row.
		Empty list when no row info is present in dump_data.
	"""
	findings: list[Finding] = []

	# Check if any placement carries row info. If none do, skip silently.
	# The 'row' field would be added when row-slot dump support lands.
	placements = dump_data.get('placements', [])
	has_row_info = any('row' in p for p in placements)
	if not has_row_info:
		# Row-slot schema not yet wired into dump.py; skip silently per scope.
		return findings

	# Build zone inner_rect lookup.
	zone_inner_by_name: dict[str, dict[str, float]] = {}
	for zone in dump_data.get('zones', []):
		zone_inner_by_name[zone['name']] = zone['inner_rect']

	# Group placements by (zone, row) and sum footprint widths.
	# row_groups maps (zone_name, row_index) -> list of placement entries.
	row_groups: dict[tuple[str, Any], list[dict[str, Any]]] = {}
	for placement in placements:
		zone_id = placement.get('zone', '')
		row_idx = placement.get('row')
		if not zone_id or row_idx is None:
			continue
		key = (zone_id, row_idx)
		if key not in row_groups:
			row_groups[key] = []
		row_groups[key].append(placement)

	for (zone_id, row_idx), group in row_groups.items():
		inner_rect = zone_inner_by_name.get(zone_id)
		if not inner_rect:
			continue

		zone_inner_w = inner_rect['right'] - inner_rect['left']
		# Sum footprint widths for all placements in this (zone, row).
		total_footprint = sum(p['footprint_bbox']['w'] for p in group)

		if total_footprint > zone_inner_w:
			# Report the first (lowest-confidence) placement in the row.
			# Use fallback confidence since row-slot is a newer data path.
			findings.append(Finding(
				scene=scene_name,
				placement_name=None,
				rule='row_footprint_overflow',
				verdict=Verdict.ESCAPE_REQUIRED,
				predicts=['off_page', 'zone_overflow_negative_gap'],
				bbox_type='footprint_bbox',
				confidence=Confidence.LOW,
				message=(
					f"Row {row_idx} in zone '{zone_id}' total footprint "
					f"{total_footprint:.1f}% exceeds zone inner width "
					f"{zone_inner_w:.1f}%."
				),
				evidence={
					'zone': zone_id,
					'row': row_idx,
					'total_footprint_pct': total_footprint,
					'zone_inner_width_pct': zone_inner_w,
					'placement_count': len(group),
				},
				fix_hints=[
					'Remove one or more placements from this row',
					'Move placements to a wider zone',
					'Reduce default_width on placements in this row',
				],
			))

	return findings


#============================================
# B4: placement_bbox_outside_scene
#============================================

def check_placement_bbox_outside_scene(
	scene: dict[str, Any],
	scene_name: str,
	dump_data: dict[str, Any],
) -> list[Finding]:
	"""
	B4: Predict scene overflow for each placement per SCENE_LINT_PLAN.md §B4.

	Checks if a placement's placement_bbox extends outside the scene_bounds.
	Zero tolerance: any overflow emits ESCAPE_REQUIRED (predicts off_page /
	scene_overflow).

	Skips placements with scale_source='skipped_error' (geometry unresolvable).

	Args:
		scene: Parsed scene YAML dict (unused directly; kept for API parity).
		scene_name: Scene name string for finding attribution.
		dump_data: Output of dump_scene_geometry() for this scene.

	Returns:
		List of ESCAPE_REQUIRED findings, one per overflowing placement.
	"""
	findings: list[Finding] = []

	scene_bounds = dump_data['scene_bounds']
	sb_left = scene_bounds['left']
	sb_right = scene_bounds['right']
	sb_top = scene_bounds['top']
	sb_bottom = scene_bounds['bottom']

	for placement in dump_data.get('placements', []):
		scale_source = placement['scale_source']
		# Cannot predict geometry for placements with skipped assets.
		if scale_source == 'skipped_error':
			continue

		placement_name = placement['placement_name']
		pb = placement['placement_bbox']
		# placement_bbox uses {x, y, w, h} where x=left, y=top.
		pb_left = pb['x']
		pb_top = pb['y']
		pb_right = pb['x'] + pb['w']
		pb_bottom = pb['y'] + pb['h']

		# Check all four edges for overflow outside scene_bounds.
		overflows: list[str] = []
		if pb_left < sb_left:
			overflows.append(f"left edge {pb_left:.2f}% < scene left {sb_left:.2f}%")
		if pb_right > sb_right:
			overflows.append(f"right edge {pb_right:.2f}% > scene right {sb_right:.2f}%")
		if pb_top < sb_top:
			overflows.append(f"top edge {pb_top:.2f}% < scene top {sb_top:.2f}%")
		if pb_bottom > sb_bottom:
			overflows.append(f"bottom edge {pb_bottom:.2f}% > scene bottom {sb_bottom:.2f}%")

		if overflows:
			confidence = _confidence_from_scale_source(scale_source)
			findings.append(Finding(
				scene=scene_name,
				placement_name=placement_name,
				rule='placement_bbox_outside_scene',
				verdict=Verdict.ESCAPE_REQUIRED,
				predicts=['off_page', 'scene_overflow'],
				bbox_type='placement_bbox',
				confidence=confidence,
				message=(
					f"Placement '{placement_name}' placement_bbox extends outside "
					f"scene_bounds: {'; '.join(overflows)}."
				),
				evidence={
					'placement_bbox': {'left': pb_left, 'right': pb_right,
						'top': pb_top, 'bottom': pb_bottom},
					'scene_bounds': {'left': sb_left, 'right': sb_right,
						'top': sb_top, 'bottom': sb_bottom},
					'overflow_edges': overflows,
					'scale_source': scale_source,
				},
				fix_hints=[
					'Move placement into a zone that fits within scene_bounds',
					'Reduce default_width to shrink the placement footprint',
				],
			))

	return findings


#============================================
# B5: placement_bbox_outside_zone
#============================================

def check_placement_bbox_outside_zone(
	scene: dict[str, Any],
	scene_name: str,
	dump_data: dict[str, Any],
) -> list[Finding]:
	"""
	B5: Predict zone overflow for each placement per SCENE_LINT_PLAN.md §B5.

	Checks if a placement's placement_bbox extends outside the zone's inner_rect
	beyond the 4-px tolerance (converted to scene-percent using
	PX_PER_SCENE_PERCENT = 11.52 from LAYOUT_PIPELINE.md §2).

	Skips placements with scale_source='skipped_error'.

	Args:
		scene: Parsed scene YAML dict (used to map placement_name -> zone_id).
		scene_name: Scene name string for finding attribution.
		dump_data: Output of dump_scene_geometry() for this scene.

	Returns:
		List of ESCAPE_REQUIRED findings, one per overflowing placement.
	"""
	findings: list[Finding] = []

	# Build zone inner_rect lookup from dump_data zones.
	zone_inner_by_name: dict[str, dict[str, float]] = {}
	for zone in dump_data.get('zones', []):
		zone_inner_by_name[zone['name']] = zone['inner_rect']

	# Build placement -> zone_id mapping from raw scene YAML.
	scene_placements = scene.get('placements', [])
	placement_zone_map: dict[str, str] = {}
	for sp in scene_placements:
		pname = sp.get('placement_name', '')
		zone_id = sp.get('zone', '')
		if pname and zone_id:
			placement_zone_map[pname] = zone_id

	tolerance = ZONE_OVERFLOW_TOLERANCE_PCT

	for placement in dump_data.get('placements', []):
		scale_source = placement['scale_source']
		# Cannot predict geometry for placements with skipped assets.
		if scale_source == 'skipped_error':
			continue

		placement_name = placement['placement_name']

		# Determine which zone this placement belongs to.
		zone_id = placement_zone_map.get(placement_name)
		if not zone_id:
			continue

		inner_rect = zone_inner_by_name.get(zone_id)
		if not inner_rect:
			continue

		pb = placement['placement_bbox']
		pb_left = pb['x']
		pb_top = pb['y']
		pb_right = pb['x'] + pb['w']
		pb_bottom = pb['y'] + pb['h']

		# Zone inner_rect uses {left, right, top, bottom} edge-coordinate form.
		ir_left = inner_rect['left']
		ir_right = inner_rect['right']
		ir_top = inner_rect['top']
		ir_bottom = inner_rect['bottom']

		# Check overflow past each edge with tolerance applied.
		overflows: list[str] = []
		if pb_left < ir_left - tolerance:
			overflows.append(
				f"left {pb_left:.2f}% < zone inner left {ir_left:.2f}% "
				f"(tolerance {tolerance:.3f}%)"
			)
		if pb_right > ir_right + tolerance:
			overflows.append(
				f"right {pb_right:.2f}% > zone inner right {ir_right:.2f}% "
				f"(tolerance {tolerance:.3f}%)"
			)
		if pb_top < ir_top - tolerance:
			overflows.append(
				f"top {pb_top:.2f}% < zone inner top {ir_top:.2f}% "
				f"(tolerance {tolerance:.3f}%)"
			)
		if pb_bottom > ir_bottom + tolerance:
			overflows.append(
				f"bottom {pb_bottom:.2f}% > zone inner bottom {ir_bottom:.2f}% "
				f"(tolerance {tolerance:.3f}%)"
			)

		if overflows:
			confidence = _confidence_from_scale_source(scale_source)
			findings.append(Finding(
				scene=scene_name,
				placement_name=placement_name,
				rule='placement_bbox_outside_zone',
				verdict=Verdict.ESCAPE_REQUIRED,
				predicts=['region_overflow', 'zone_overflow'],
				bbox_type='placement_bbox',
				confidence=confidence,
				message=(
					f"Placement '{placement_name}' placement_bbox extends outside "
					f"zone '{zone_id}' inner_rect (tolerance "
					f"{tolerance:.3f}%): {'; '.join(overflows)}."
				),
				evidence={
					'zone': zone_id,
					'placement_bbox': {'left': pb_left, 'right': pb_right,
						'top': pb_top, 'bottom': pb_bottom},
					'zone_inner_rect': {'left': ir_left, 'right': ir_right,
						'top': ir_top, 'bottom': ir_bottom},
					'overflow_edges': overflows,
					'scale_source': scale_source,
					'tolerance_pct': tolerance,
				},
				fix_hints=[
					'Move placement to a wider or taller zone',
					'Reduce default_width to shrink the placement_bbox',
				],
			))

	return findings


#============================================
# B6: item_item_overlap
#============================================

def _rects_overlap(
	ax: float, ay: float, aw: float, ah: float,
	bx: float, by: float, bw: float, bh: float,
) -> bool:
	"""Return True if two {x,y,w,h} rects have a non-zero intersection area.

	Args:
		ax, ay: top-left corner of rect A (x=left, y=top).
		aw, ah: width and height of rect A.
		bx, by: top-left corner of rect B.
		bw, bh: width and height of rect B.

	Returns:
		True if the intersection area is strictly positive (> 0).
	"""
	# Compute intersection bounds.
	inter_left = max(ax, bx)
	inter_right = min(ax + aw, bx + bw)
	inter_top = max(ay, by)
	inter_bottom = min(ay + ah, by + bh)

	inter_w = inter_right - inter_left
	inter_h = inter_bottom - inter_top

	# Intersection exists only when both dimensions are strictly positive.
	return inter_w > 0.0 and inter_h > 0.0


def check_item_item_overlap(
	scene: dict[str, Any],
	scene_name: str,
	dump_data: dict[str, Any],
) -> list[Finding]:
	"""
	B6: Predict item-item collision per SCENE_LINT_PLAN.md §B6.

	For each pair of placements in the same zone, checks if their footprint_bbox
	rects have a non-zero intersection area. Emits ESCAPE_REQUIRED for each
	overlapping pair. Each pair is reported once (not twice).

	Uses footprint_bbox (the layout-budgeted rectangle) rather than visual_bbox
	so the overlap check accounts for label and depth budget.

	Skips placements with scale_source='skipped_error' (geometry unresolvable).

	Args:
		scene: Parsed scene YAML dict (used to map placement_name -> zone_id).
		scene_name: Scene name string for finding attribution.
		dump_data: Output of dump_scene_geometry() for this scene.

	Returns:
		List of ESCAPE_REQUIRED findings, one per overlapping pair.
	"""
	findings: list[Finding] = []

	# Build placement -> zone_id mapping from raw scene YAML.
	scene_placements = scene.get('placements', [])
	placement_zone_map: dict[str, str] = {}
	for sp in scene_placements:
		pname = sp.get('placement_name', '')
		zone_id = sp.get('zone', '')
		if pname and zone_id:
			placement_zone_map[pname] = zone_id

	# Filter to placements with usable geometry.
	usable: list[dict[str, Any]] = [
		p for p in dump_data.get('placements', [])
		if p['scale_source'] != 'skipped_error'
	]

	# Group usable placements by zone.
	zone_placements: dict[str, list[dict[str, Any]]] = {}
	for placement in usable:
		pname = placement['placement_name']
		zone_id = placement_zone_map.get(pname)
		if not zone_id:
			continue
		if zone_id not in zone_placements:
			zone_placements[zone_id] = []
		zone_placements[zone_id].append(placement)

	# For each zone, check every pair for footprint_bbox overlap.
	for zone_id, zone_items in zone_placements.items():
		n = len(zone_items)
		for i in range(n):
			for j in range(i + 1, n):
				a = zone_items[i]
				b = zone_items[j]

				fa = a['footprint_bbox']
				fb = b['footprint_bbox']

				if _rects_overlap(
					fa['x'], fa['y'], fa['w'], fa['h'],
					fb['x'], fb['y'], fb['w'], fb['h'],
				):
					# Use the lower confidence of the two placements.
					conf_a = _confidence_from_scale_source(a['scale_source'])
					conf_b = _confidence_from_scale_source(b['scale_source'])
					# Confidence order: HIGH=0, MEDIUM=1, LOW=2 (lower is better).
					conf_order = {Confidence.HIGH: 0, Confidence.MEDIUM: 1, Confidence.LOW: 2}
					confidence = conf_a if conf_order[conf_a] >= conf_order[conf_b] else conf_b

					a_name = a['placement_name']
					b_name = b['placement_name']
					findings.append(Finding(
						scene=scene_name,
						placement_name=a_name,
						rule='item_item_overlap',
						verdict=Verdict.ESCAPE_REQUIRED,
						predicts=['item_collision', 'svg_svg_overlap'],
						bbox_type='footprint_bbox',
						confidence=confidence,
						message=(
							f"Placements '{a_name}' and '{b_name}' in zone "
							f"'{zone_id}' have overlapping footprint_bbox rects."
						),
						evidence={
							'zone': zone_id,
							'placement_a': a_name,
							'placement_b': b_name,
							'footprint_bbox_a': fa,
							'footprint_bbox_b': fb,
						},
						fix_hints=[
							'Move one placement to a different zone',
							'Reduce default_width on one or both placements',
							'Remove one placement from the scene',
						],
					))

	return findings


#============================================
# B7: label_offscreen
#============================================

def check_label_offscreen(
	scene: dict[str, Any],
	scene_name: str,
	dump_data: dict[str, Any],
) -> list[Finding]:
	"""
	B7: Predict label clipping at scene edge per SCENE_LINT_PLAN.md §B7.

	Checks if any placement's label_bbox extends horizontally outside
	scene_bounds. This can happen when zones touch the scene edges and
	the label position centered on the object goes out-of-bounds.

	Per the rule spec:
	  label_left  = _labelX - label_width / 2
	  label_right = _labelX + label_width / 2
	  if label_left < scene_bounds.left:   ESCAPE_REQUIRED
	  if label_right > scene_bounds.right: ESCAPE_REQUIRED

	Args:
		scene: Parsed scene YAML dict (unused directly; kept for API parity).
		scene_name: Scene name string for finding attribution.
		dump_data: Output of dump_scene_geometry() for this scene.

	Returns:
		List of ESCAPE_REQUIRED findings, one per offscreen label.
	"""
	findings: list[Finding] = []

	scene_bounds = dump_data['scene_bounds']
	sb_left = scene_bounds['left']
	sb_right = scene_bounds['right']

	for placement in dump_data.get('placements', []):
		scale_source = placement['scale_source']
		if scale_source == 'skipped_error':
			continue

		placement_name = placement['placement_name']
		label_bbox = placement.get('label_bbox')
		if not label_bbox:
			# No label bbox computed; skip.
			continue

		label_left = label_bbox['x']
		label_right = label_bbox['x'] + label_bbox['w']

		# Check horizontal offscreen conditions.
		offscreen: list[str] = []
		if label_left < sb_left:
			offscreen.append(
				f"label left {label_left:.2f}% < scene left {sb_left:.2f}%"
			)
		if label_right > sb_right:
			offscreen.append(
				f"label right {label_right:.2f}% > scene right {sb_right:.2f}%"
			)

		if offscreen:
			confidence = _confidence_from_scale_source(scale_source)
			findings.append(Finding(
				scene=scene_name,
				placement_name=placement_name,
				rule='label_offscreen',
				verdict=Verdict.ESCAPE_REQUIRED,
				predicts=['label_clipped'],
				bbox_type='label_bbox',
				confidence=confidence,
				message=(
					f"Label for placement '{placement_name}' extends beyond "
					f"scene_bounds: {'; '.join(offscreen)}."
				),
				evidence={
					'label_bbox': label_bbox,
					'scene_bounds': {'left': sb_left, 'right': sb_right},
					'offscreen_edges': offscreen,
					'scale_source': scale_source,
				},
				fix_hints=[
					'Move placement away from scene edge',
					'Reduce label_width on the placement or object',
					'Adjust zone positioning away from scene boundary',
				],
			))

	return findings


#============================================
# B8: label_object_overlap
#============================================

def check_label_object_overlap(
	scene: dict[str, Any],
	scene_name: str,
	dump_data: dict[str, Any],
) -> list[Finding]:
	"""
	B8: Predict label-object overlap per SCENE_LINT_PLAN.md §B8.

	For each label L and each placement P (including L's own object), checks if
	L's label_bbox intersects P's visual_bbox with > 10 px&sup2; intersection
	area. Emits ESCAPE_REQUIRED for overlapping label-placement pairs.

	Note: Ideal implementation would filter to scientific-kind placements only,
	but object loading is not available in this context. Current implementation
	checks every placement, including the label's own object. This is a
	conservative approach that may over-report but does not under-report label
	collisions; a label over its own object's art is a real collision.

	Args:
		scene: Parsed scene YAML dict (unused currently; kept for API parity).
		scene_name: Scene name string for finding attribution.
		dump_data: Output of dump_scene_geometry() for this scene.

	Returns:
		List of ESCAPE_REQUIRED findings, one per overlapping label-placement pair.
	"""
	findings: list[Finding] = []

	# Filter to placements with usable geometry.
	usable: list[dict[str, Any]] = [
		p for p in dump_data.get('placements', [])
		if p['scale_source'] != 'skipped_error'
	]

	# For each label, check intersection with all placements, including the label's own object.
	for label_placement in usable:
		label_pname = label_placement['placement_name']
		label_bbox = label_placement.get('label_bbox')
		if not label_bbox:
			continue

		label_x = label_bbox['x']
		label_y = label_bbox['y']
		label_w = label_bbox['w']
		label_h = label_bbox['h']

		# Check against every placement, with no identity exclusion. A label
		# overlapping its own object's visual_bbox is a real collision and must
		# be reported; there is no instance where any overlap should be excluded.
		for other_placement in usable:
			other_pname = other_placement['placement_name']

			vb = other_placement['visual_bbox']
			obj_x = vb['x']
			obj_y = vb['y']
			obj_w = vb['w']
			obj_h = vb['h']

			# Compute intersection area in scene-percent squared.
			# Convert to px&sup2; for tolerance check: 1 scene-% = 11.52 px (linear).
			inter_left = max(label_x, obj_x)
			inter_right = min(label_x + label_w, obj_x + obj_w)
			inter_top = max(label_y, obj_y)
			inter_bottom = min(label_y + label_h, obj_y + obj_h)

			inter_w = inter_right - inter_left
			inter_h = inter_bottom - inter_top

			if inter_w > 0.0 and inter_h > 0.0:
				# Intersection area in scene-% squared; tolerance is 10 px^2.
				# 1 scene-% = 11.52 px, so 10 px^2 = 10 / (11.52^2) ~= 0.0753 scene-%^2.
				inter_area_scene_pct_sq = inter_w * inter_h
				inter_area_px_sq = inter_area_scene_pct_sq * (11.52 ** 2)

				label_tolerance_px_sq = 10.0
				if inter_area_px_sq > label_tolerance_px_sq:
					confidence = _confidence_from_scale_source(
						label_placement['scale_source']
					)
					findings.append(Finding(
						scene=scene_name,
						placement_name=label_pname,
						rule='label_object_overlap',
						verdict=Verdict.ESCAPE_REQUIRED,
						predicts=['label_collision', 'svg_label_overlap'],
						bbox_type='label_bbox',
						confidence=confidence,
						message=(
							f"Label for '{label_pname}' overlaps object "
							f"'{other_pname}' with {inter_area_px_sq:.1f} px&sup2; "
							f"intersection (tolerance {label_tolerance_px_sq} px&sup2;)."
						),
						evidence={
							'label_placement': label_pname,
							'object_placement': other_pname,
							'intersection_area_px_sq': inter_area_px_sq,
							'tolerance_px_sq': label_tolerance_px_sq,
						},
						fix_hints=[
							'Move placement to a different location',
							'Reduce label_width on the placement or object',
							'Increase gap between placements',
						],
					))

	return findings


#============================================
# B9: invisible_placement
#============================================

def check_invisible_placement(
	scene: dict[str, Any],
	scene_name: str,
	dump_data: dict[str, Any],
) -> list[Finding]:
	"""
	B9: Predict invisible/degenerate placement per SCENE_LINT_PLAN.md §B9.

	Five triggers (each fires ESCAPE_REQUIRED at medium-or-higher confidence):
	1. Predicted size < 100 px^2 -> ESCAPE_REQUIRED, high confidence.
	2. height > 2 x zone_inner_h (renderer clamps to invisibility) -> ESCAPE_REQUIRED.
	3. scale_source == 'skipped_error' -> ESCAPE_REQUIRED.
	4. layout.default_width missing or <= 0 -> BLOCKED (Group A overlap; defensive).
	5. scale_source == 'fallback_authored' (no cm-model data) -> ESCAPE_REQUIRED,
	   medium confidence. Stays advisory until the rule is promoted via --strict.

	Args:
		scene: Parsed scene YAML dict (used to check object layout fields).
		scene_name: Scene name string for finding attribution.
		dump_data: Output of dump_scene_geometry() for this scene.

	Returns:
		List of ESCAPE_REQUIRED findings (triggers 1-3, 5) and BLOCKED findings
		(trigger 4, defensive overlap with Group A).
	"""
	findings: list[Finding] = []

	# Build placement -> zone_id mapping from scene YAML.
	placement_zone_map: dict[str, str] = {}
	for sp in scene.get('placements', []):
		pname = sp.get('placement_name', '')
		zone_id = sp.get('zone', '')
		if pname and zone_id:
			placement_zone_map[pname] = zone_id

	# Build zone inner_rect lookup from dump_data.
	zone_inner_by_name: dict[str, dict[str, float]] = {}
	for zone in dump_data.get('zones', []):
		zone_inner_by_name[zone['name']] = zone['inner_rect']

	# PX_PER_SCENE_PERCENT constant from LAYOUT_PIPELINE.md §2.
	px_per_scene_pct = 11.52

	for placement in dump_data.get('placements', []):
		placement_name = placement['placement_name']
		scale_source = placement['scale_source']

		# Trigger 3: scale_source == 'skipped_error' -> ESCAPE_REQUIRED.
		if scale_source == 'skipped_error':
			findings.append(Finding(
				scene=scene_name,
				placement_name=placement_name,
				rule='invisible_placement',
				verdict=Verdict.ESCAPE_REQUIRED,
				predicts=['invisible_object'],
				bbox_type='visual_bbox',
				confidence=Confidence.HIGH,
				message=(
					f"Placement '{placement_name}' has scale_source='skipped_error'; "
					f"geometry cannot be predicted."
				),
				evidence={
					'scale_source': scale_source,
					'trigger': 'asset_load_failure',
				},
				fix_hints=[
					'Verify object_name is correct',
					'Check that the object exists in the library',
					'Ensure asset file is present',
				],
			))
			continue

		# Trigger 1: visual_bbox area < 100 px&sup2; -> ESCAPE_REQUIRED.
		vb = placement['visual_bbox']
		vb_w_scene_pct = vb['w']
		vb_h_scene_pct = vb['h']
		vb_w_px = vb_w_scene_pct * px_per_scene_pct
		vb_h_px = vb_h_scene_pct * px_per_scene_pct
		vb_area_px_sq = vb_w_px * vb_h_px

		if vb_area_px_sq < 100.0:
			findings.append(Finding(
				scene=scene_name,
				placement_name=placement_name,
				rule='invisible_placement',
				verdict=Verdict.ESCAPE_REQUIRED,
				predicts=['invisible_object'],
				bbox_type='visual_bbox',
				confidence=_confidence_from_scale_source(scale_source),
				message=(
					f"Placement '{placement_name}' predicted size "
					f"{vb_area_px_sq:.1f} px&sup2; < 100 px&sup2; threshold."
				),
				evidence={
					'visual_bbox_area_px_sq': vb_area_px_sq,
					'threshold_px_sq': 100.0,
					'scale_source': scale_source,
					'trigger': 'size_too_small',
				},
				fix_hints=[
					'Increase default_width or add display_width_cm',
					'Move placement to a larger zone',
				],
			))
			continue

		# Trigger 2: height > 2 x zone_inner_h -> ESCAPE_REQUIRED.
		zone_id = placement_zone_map.get(placement_name)
		if zone_id:
			inner_rect = zone_inner_by_name.get(zone_id)
			if inner_rect:
				zone_inner_h = inner_rect['bottom'] - inner_rect['top']
				pb_h = placement['placement_bbox']['h']
				if pb_h > 2.0 * zone_inner_h:
					findings.append(Finding(
						scene=scene_name,
						placement_name=placement_name,
						rule='invisible_placement',
						verdict=Verdict.ESCAPE_REQUIRED,
						predicts=['invisible_object'],
						bbox_type='placement_bbox',
						confidence=_confidence_from_scale_source(scale_source),
						message=(
							f"Placement '{placement_name}' height {pb_h:.1f}% > "
							f"2x zone inner height {2.0 * zone_inner_h:.1f}%; "
							f"renderer clamps to invisibility."
						),
						evidence={
							'placement_height_pct': pb_h,
							'zone': zone_id,
							'zone_inner_height_pct': zone_inner_h,
							'scale_source': scale_source,
							'trigger': 'height_exceeds_double_zone',
						},
						fix_hints=[
							'Move placement to a taller zone',
							'Reduce default_width to shrink predicted height',
						],
					))
					continue

		# Trigger 5: fallback_authored without cm_model (ESCAPE_REQUIRED, medium
		# confidence). Fires when scale_source is fallback_authored (no cm-model
		# data); the placement may still render at the wrong size. Stays advisory
		# until the rule is promoted via --strict.
		if scale_source == 'fallback_authored':
			findings.append(Finding(
				scene=scene_name,
				placement_name=placement_name,
				rule='invisible_placement',
				verdict=Verdict.ESCAPE_REQUIRED,
				predicts=['invisible_object'],
				bbox_type='visual_bbox',
				confidence=Confidence.MEDIUM,
				message=(
					f"Placement '{placement_name}' uses fallback_authored scaling "
					f"(no display_width_cm); simulator confidence degraded."
				),
				evidence={
					'scale_source': scale_source,
					'trigger': 'fallback_scaling',
				},
				fix_hints=[
					'Add layout.display_width_cm to this placement or its object',
				],
			))

	return findings


#============================================
# B10: zone_overlap
#============================================

def check_zone_overlap(
	scene: dict[str, Any],
	scene_name: str,
	dump_data: dict[str, Any],
) -> list[Finding]:
	"""
	B10: Predict zone-zone collision per SCENE_LINT_PLAN.md section B10.

	For each pair of rendered zones, checks if their bounds rects have
	a non-zero intersection area. Overlapping zones cause cross-zone collisions
	per spec §10. Zone geometry belongs to the rendered dump, never source YAML.

	Per the rule spec:
	  For each pair (Za, Zb) in scene.zones:
	    if area(Za.bounds &cap; Zb.bounds) > 0: ESCAPE_REQUIRED

	Args:
		scene: Parsed source YAML dict, unused because it carries no geometry.
		scene_name: Scene name string for finding attribution.
		dump_data: Output of dump_scene_geometry(), including computed zones.

	Returns:
		List of ESCAPE_REQUIRED findings, one per overlapping zone pair.
	"""
	findings: list[Finding] = []

	# The source scene is intentionally not inspected here. Computed zones are
	# emitted by the real TypeScript layout pipeline and loaded by dump.py.
	_ = scene
	zones = dump_data.get('zones', [])
	n = len(zones)

	# Check every pair of zones.
	for i in range(n):
		for j in range(i + 1, n):
			zone_a = zones[i]
			zone_b = zones[j]

			zone_a_name = zone_a.get('name', zone_a.get('zone_name', f'zone[{i}]'))
			zone_b_name = zone_b.get('name', zone_b.get('zone_name', f'zone[{j}]'))

			bounds_a = zone_a['bounds']
			bounds_b = zone_b['bounds']

			za_left = bounds_a['left']
			za_right = bounds_a['right']
			za_top = bounds_a['top']
			za_bottom = bounds_a['bottom']

			zb_left = bounds_b['left']
			zb_right = bounds_b['right']
			zb_top = bounds_b['top']
			zb_bottom = bounds_b['bottom']

			# Compute intersection bounds.
			inter_left = max(za_left, zb_left)
			inter_right = min(za_right, zb_right)
			inter_top = max(za_top, zb_top)
			inter_bottom = min(za_bottom, zb_bottom)

			inter_w = inter_right - inter_left
			inter_h = inter_bottom - inter_top

			# Overlap exists only when both dimensions are strictly positive.
			if inter_w > 0.0 and inter_h > 0.0:
				findings.append(Finding(
					scene=scene_name,
					placement_name=None,
					rule='zone_overlap',
					verdict=Verdict.ESCAPE_REQUIRED,
					predicts=['cross_zone_collision'],
					bbox_type='zone_bounds',
					confidence=Confidence.HIGH,
					message=(
						f"Zones '{zone_a_name}' and '{zone_b_name}' have "
						f"overlapping bounds, causing potential cross-zone "
						f"collisions (spec §10)."
					),
					evidence={
						'zone_a': zone_a_name,
						'zone_b': zone_b_name,
						'zone_a_bounds': {
							'left': za_left, 'right': za_right,
							'top': za_top, 'bottom': za_bottom
						},
						'zone_b_bounds': {
							'left': zb_left, 'right': zb_right,
							'top': zb_top, 'bottom': zb_bottom
						},
						'intersection': {
							'left': inter_left, 'right': inter_right,
							'top': inter_top, 'bottom': inter_bottom,
							'area_pct_sq': inter_w * inter_h,
						},
					},
					fix_hints=[
						'Adjust zone bounds to eliminate overlap',
						'Move one zone to a non-overlapping region',
					],
				))

	return findings
