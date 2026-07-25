"""Behavioral validation of authored label placement vocabulary."""

# PIP3 modules
import pytest

# local repo modules
import validation.shared_toolkit.findings as shared_findings
import validation.yaml_schema.scene_base_validator as scene_base_validator


#============================================

def _scene_with_label_placement(location: str, value: str | None) -> dict:
	"""Build one valid semantic scene with an optional label-placement value."""
	placement = {
		"placement_name": "instrument",
		"object_name": "some_object",
		"zone": "bench",
	}
	scene = {
		"scene_name": "test_scene",
		"workspace": "equipment_bench",
		"capabilities": ["item_workspace"],
		"zones": [{"zone_name": "bench"}],
		"placements": [placement],
	}
	if value is not None:
		if location == "scene":
			scene["layout_rules"] = {"label_placement": value}
		else:
			placement["layout"] = {"label_placement": value}
	return scene


def _has_error(scene: dict) -> bool:
	"""Return whether validation rejects the authored scene."""
	validator = scene_base_validator.BaseSceneValidator()
	validator.set_object_names({"some_object"})
	findings = validator.validate(scene, "inline_scene.yaml")
	has_error = any(
		finding.severity == shared_findings.Severity.ERROR
		for finding in findings
	)
	return has_error


def _scene_with_layout_rules(layout_rules: object) -> dict:
	"""Build a valid scene with one complete scene-wide layout-rules value."""
	scene = _scene_with_label_placement("scene", None)
	scene["layout_rules"] = layout_rules
	return scene


#============================================

@pytest.mark.parametrize("location", ("scene", "placement"))
@pytest.mark.parametrize("value", ("top", "bottom"))
def test_label_placement_accepts_the_closed_authoring_vocabulary(
	location: str,
	value: str,
) -> None:
	"""Both supported source locations accept the same closed vocabulary."""
	assert not _has_error(_scene_with_label_placement(location, value))


@pytest.mark.parametrize("location", ("scene", "placement"))
def test_label_placement_rejects_an_unknown_author_value(location: str) -> None:
	"""A made-up placement label cannot silently enter scene YAML."""
	assert _has_error(_scene_with_label_placement(location, "middle"))


@pytest.mark.parametrize("location", ("scene", "placement"))
def test_label_placement_remains_optional_at_each_source_location(location: str) -> None:
	"""Omitting the field leaves default resolution to the layout engine."""
	assert not _has_error(_scene_with_label_placement(location, None))


def test_layout_rules_accepts_every_documented_scene_wide_hint() -> None:
	"""All documented scene-wide hints compose without becoming an open map."""
	layout_rules = {
		"default_align_stop": "center",
		"label_font_size": 12,
		"label_line_height": 1.2,
		"label_offset_y": 5,
		"label_placement": "top",
		"zone_gap": 3,
	}
	assert not _has_error(_scene_with_layout_rules(layout_rules))


@pytest.mark.parametrize("layout_rules", (
	{"invented_rule": "new meaning"},
	{"x": 42},
	{"bounds": {"left": 0}},
))
def test_layout_rules_rejects_unknown_and_geometry_escape_hatches(
	layout_rules: dict,
) -> None:
	"""Scene-wide hints cannot introduce new vocabulary or authored coordinates."""
	assert _has_error(_scene_with_layout_rules(layout_rules))


@pytest.mark.parametrize("layout_rules", (
	{"default_align_stop": "justify"},
	{"label_font_size": 0},
	{"label_line_height": "1.1"},
	{"zone_gap": True},
	[],
))
def test_layout_rules_rejects_invalid_documented_value_shapes(layout_rules: object) -> None:
	"""Each supported hint keeps its documented enum or numeric shape."""
	assert _has_error(_scene_with_layout_rules(layout_rules))
