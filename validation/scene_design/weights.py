"""Per-class weight tables for scene design scoring.

Weight tables define the relative importance of each metric for each scene class.
These are extracted from SCENE_DESIGN_LINT_PLAN.md section "Per-class weight tables"
and are guaranteed to sum to 1.00 per class.

Classes:
	template - no placements
	composition - default/fallback classification
	instrument_heavy - primary placement is instrument/equipment kind
	zoom_detail - one placement
	dense_clutter - >=10 placements after inheritance resolution
"""


WEIGHTS: dict[str, dict[str, float]] = {
	'template': {
		'predicted_label_overlap': 0.40,
		'label_wrap_rate': 0.40,
		'largest_empty_band': 0.20,
	},
	# zone_footprint_balance removed (rewarded spreading objects across zones,
	# against the grouping design intent); see
	# docs/archive/decisions/scorecard_metric_spec_discrepancy.md. Its
	# 0.15 weight is redistributed proportionally across the remaining
	# metrics so the class still sums to 1.00.
	'composition': {
		'primary_area_ratio': 0.28,
		'support_distance': 0.24,
		'scene_density': 0.18,
		'predicted_label_overlap': 0.18,
		'label_wrap_rate': 0.06,
		'aspect_fidelity': 0.06,
	},
	'instrument_heavy': {
		'primary_area_ratio': 0.35,
		'support_distance': 0.20,
		'scene_density': 0.15,
		'predicted_label_overlap': 0.15,
		'label_wrap_rate': 0.05,
		'aspect_fidelity': 0.10,
	},
	# zone_footprint_balance removed (see comment on the composition table
	# above); its 0.10 weight is redistributed proportionally.
	'zoom_detail': {
		'primary_area_ratio': 0.56,
		'scene_density': 0.22,
		'predicted_label_overlap': 0.11,
		'label_wrap_rate': 0.11,
	},
	'dense_clutter': {
		'primary_area_ratio': 0.05,
		'support_distance': 0.20,
		'scene_density': 0.10,
		'predicted_label_overlap': 0.30,
		'label_wrap_rate': 0.25,
		'aspect_fidelity': 0.10,
	},
}
