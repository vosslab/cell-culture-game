"""Behavior tests for material-anchor readiness validation."""

# Standard Library
import pathlib

# PIP3 modules
import pytest

# local repo modules
import validation.shared_toolkit.repo_root
from validation.yaml_schema.object_validator import ObjectValidator


#============================================
def _write_svg(repo_root: pathlib.Path, asset_name: str, content: str) -> None:
	"""Write one inline SVG source under a temporary repository root."""
	asset_dir = repo_root / "assets" / "equipment"
	asset_dir.mkdir(parents=True, exist_ok=True)
	svg_path = asset_dir / f"{asset_name}.svg"
	svg_path.write_text(content, encoding="utf-8")


#============================================
def _pipette_object(asset_names: tuple[str, ...]) -> dict:
	"""Build a minimal pipette using the current fill-height declaration."""
	cases = [
		{"when": material_name, "output": {"asset_name": asset_name}}
		for material_name, asset_name in zip(("empty", "sample"), asset_names, strict=True)
	]
	obj = {
		"object_name": "test_pipette",
		"kind": "pipette",
		"label": "Test pipette",
		"state_fields": [
			{
				"field_name": "held_material_name",
				"type": "enum",
				"allowed": ["empty", "sample"],
				"default": "empty",
				"description": "Material held in the tip.",
			},
			{
				"field_name": "held_material_volume",
				"type": "float",
				"unit": "ul",
				"min": 0,
				"max": 200,
				"default": 0,
				"description": "Volume held in the tip.",
			},
		],
		"visual_states": {
			"held_material_name": {"kind": "svg", "cases": cases},
			"held_material_volume": {
				"applies_to": "object",
				"render_effect": "fill_height",
				"target": "anchor_liquid_bounds",
				"clip": "anchor_liquid_clip",
				"capacity_ul": 200,
			},
		},
		"capabilities": ["clickable", "material_container", "cursor_attachable"],
		"layout": {"default_width": 3, "label_width": 5},
	}
	return obj


#============================================
def test_current_fill_height_shape_reports_missing_anchors(
	tmp_path: pathlib.Path,
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""The current render-effect shape participates in SVG readiness checks."""
	_write_svg(tmp_path, "plain_pipette", "<svg xmlns='http://www.w3.org/2000/svg'/>")
	monkeypatch.setattr(validation.shared_toolkit.repo_root, "REPO_ROOT", tmp_path)
	obj = _pipette_object(("plain_pipette", "plain_pipette"))

	findings = ObjectValidator().validate(
		obj,
		"content/objects/pipette/test_pipette.yaml",
	)

	assert any(
		finding.code == "non-normalized" and "plain_pipette" in finding.message
		for finding in findings
	)


#============================================
def test_variant_fan_out_does_not_hide_asset_readiness(
	tmp_path: pathlib.Path,
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	"""Each variant is inspected even when the single-base rule also fires."""
	anchored_svg = """
<svg xmlns="http://www.w3.org/2000/svg">
	<clipPath id="anchor_liquid_clip"/>
	<rect id="anchor_liquid_bounds"/>
</svg>
""".strip()
	_write_svg(tmp_path, "anchored_pipette", anchored_svg)
	_write_svg(tmp_path, "plain_pipette", "<svg xmlns='http://www.w3.org/2000/svg'/>")
	monkeypatch.setattr(validation.shared_toolkit.repo_root, "REPO_ROOT", tmp_path)
	obj = _pipette_object(("anchored_pipette", "plain_pipette"))

	findings = ObjectValidator().validate(
		obj,
		"content/objects/pipette/test_pipette.yaml",
	)

	assert any(
		finding.code == "non-normalized" and "plain_pipette" in finding.message
		for finding in findings
	)


#============================================
def test_subpart_fill_height_does_not_require_base_svg_anchors() -> None:
	"""Generated subpart geometry is independent of base-SVG liquid anchors."""
	obj = _pipette_object(("unresolved_asset", "unresolved_asset"))
	obj["visual_states"]["held_material_volume"] = {
		"kind": "composite",
		"applies_to": "subpart",
		"formula": "fill_height(state(held_material_volume), capacity_ul=200)",
	}

	findings = ObjectValidator().validate(
		obj,
		"content/objects/pipette/test_pipette.yaml",
	)

	assert not any(finding.code in {"missing", "non-normalized"} for finding in findings)
