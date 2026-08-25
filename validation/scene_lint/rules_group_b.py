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


from validation.scene_lint.findings import Finding, Verdict, Confidence
import validation.scene_lint.rules_group_b_common


# Threshold constants from SCENE_LINT_PLAN.md "Tolerance defaults".
ASPECT_DISTORTION_THRESHOLD_PCT = 5.0
# MIN_SCALE from LAYOUT_PIPELINE.md §2; mirrors bboxes.MIN_SCALE.
MIN_SCALE = 0.55
# B5 tolerance: 4 px allowed overflow past zone bounds before firing.
# Converts px to scene-percent using PX_PER_SCENE_PERCENT = 11.52 (LAYOUT_PIPELINE.md §2).
_PX_PER_SCENE_PERCENT = 11.52
ZONE_OVERFLOW_TOLERANCE_PCT = 4.0 / _PX_PER_SCENE_PERCENT  # ~0.347 scene-%


#============================================
# B1: aspect_distorted_predicted
#============================================

def check_aspect_distorted_predicted(
	scene: dict[str, object],
	scene_name: str,
	dump_data: dict[str, object],
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
			confidence = validation.scene_lint.rules_group_b_common.confidence_from_scale_source(scale_source)
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
	scene: dict[str, object],
	scene_name: str,
	dump_data: dict[str, object],
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
	zone_by_name: dict[str, dict[str, object]] = {}
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
			confidence = validation.scene_lint.rules_group_b_common.confidence_from_scale_source(scale_source)
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
	scene: dict[str, object],
	scene_name: str,
	dump_data: dict[str, object],
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
	row_groups: dict[tuple[str, object], list[dict[str, object]]] = {}
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
	scene: dict[str, object],
	scene_name: str,
	dump_data: dict[str, object],
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
			confidence = validation.scene_lint.rules_group_b_common.confidence_from_scale_source(scale_source)
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
	scene: dict[str, object],
	scene_name: str,
	dump_data: dict[str, object],
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
			confidence = validation.scene_lint.rules_group_b_common.confidence_from_scale_source(scale_source)
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
