"""Behavior tests for scene-design focus classification."""

# local repo modules
import validation.scene_design.class_detect
import validation.scene_design.metrics.labels


#============================================
def test_single_placement_scene_is_zoom_detail() -> None:
	"""A one-object teaching surface is scored as a focused detail scene."""
	scene = {
		"scene_name": "focused_plate",
		"placements": [{"placement_name": "plate"}],
	}

	scene_class = validation.scene_design.class_detect.detect(scene)

	assert scene_class == "zoom_detail"


#============================================
def test_single_valid_label_has_no_cross_placement_overlap() -> None:
	"""One label cannot overlap another placement because none exists."""
	scene = {"scene_name": "focused_plate", "placements": [{}]}
	dump_data = {
		"placements": [
			{
				"label_bbox": {"x": 10.0, "y": 5.0, "w": 20.0, "h": 4.0},
				"footprint_bbox": {"x": 5.0, "y": 10.0, "w": 60.0, "h": 40.0},
			}
		]
	}

	score = validation.scene_design.metrics.labels.predicted_label_overlap(
		scene,
		dump_data,
	)

	assert score == 100.0
