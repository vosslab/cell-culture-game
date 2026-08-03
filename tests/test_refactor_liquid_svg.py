"""Behavioral tests for the reviewed, developer-only liquid SVG refactorer."""

import hashlib
import json
import sys
from pathlib import Path

import lxml.etree
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

import refactor_liquid_svg
from validation.svg.layer_recipe_validator import validate_material_svg


SVG_NS = "http://www.w3.org/2000/svg"


def _donor(*, bounds_in_clip: bool = False, extra: str = "") -> str:
	"""Return a small donor with fixed art before and after a liquid band."""
	bounds = (
		'<rect id="anchor_liquid_bounds" x="1" y="2" width="8" height="9"/>'
		if bounds_in_clip
		else '<rect id="anchor_liquid_bounds" x="1" y="2" width="8" height="9" display="none"/>'
	)
	return f'''<svg xmlns="{SVG_NS}" viewBox="0 0 20 20">
<defs><clipPath id="anchor_liquid_clip">{bounds if bounds_in_clip else '<rect x="1" y="2" width="8" height="9"/>'}</clipPath></defs>
{'' if bounds_in_clip else bounds}
<path d="M0 0H10" fill="#111111"/>
<g><path d="M1 2H9V11Z" fill="#00aa00" stroke="#005500" style="stroke-width:1"/></g>
<path d="M2 3H3V4Z" fill="#ffffff"/>
<path d="M0 12H10" stroke="#222222"/>
{extra}</svg>'''


def _write_review(source: Path, runs: list[dict], *, source_hash: str | None = None, extra: dict | None = None) -> Path:
	"""Write one transient, exact-identity review input beside a temporary donor."""
	review = source.with_suffix(".review.json")
	payload = {
		"asset_path": str(source.resolve()),
		"source_sha256": source_hash or hashlib.sha256(source.read_bytes()).hexdigest(),
		"runs": runs,
	}
	if extra is not None:
		payload.update(extra)
	review.write_text(json.dumps(payload), encoding="utf-8")
	return review


def _runs() -> list[dict]:
	return [
		{"layer_name": "liquid_body", "paint_role": "base", "liquid_part": "body", "unit_indices": [3]},
		{"layer_name": "liquid_glint", "paint_role": "highlight", "liquid_part": "surface", "adjustment": "0.18", "unit_indices": [4]},
	]


def _legacy_runs() -> list[dict]:
	"""Return the shifted direct-root ordinals when bounds began inside defs."""
	return [
		{"layer_name": "liquid_body", "paint_role": "base", "liquid_part": "body", "unit_indices": [2]},
		{"layer_name": "liquid_glint", "paint_role": "highlight", "liquid_part": "surface", "adjustment": "0.18", "unit_indices": [3]},
	]


def test_refactor_groups_ordered_artwork_and_keeps_literal_donor_paint(tmp_path: Path):
	"""Reviewed runs become a contiguous material band without changing fallback paint."""
	source = tmp_path / "bottle.svg"
	output = tmp_path / "bottle.material.svg"
	source.write_text(_donor(), encoding="utf-8")
	result = refactor_liquid_svg.refactor_liquid_svg(source, _write_review(source, _runs()), output)
	root = lxml.etree.parse(str(output)).getroot()
	validate_material_svg(root)
	layers = [child for child in root if isinstance(child.tag, str) and child.get("data-vlab-layer-name")]
	assert [layer.get("data-vlab-layer-name") for layer in layers] == ["fixed_back", "liquid_body", "liquid_glint", "fixed_front"]
	assert '#00aa00' in output.read_text(encoding="utf-8") and '#005500' in output.read_text(encoding="utf-8")
	assert result.changed and result.material_unit_count == 2


def test_refactor_clones_clip_bounds_and_moves_hidden_runtime_rect(tmp_path: Path):
	"""A legacy bounds rect inside the clip remains equivalent clip geometry."""
	source = tmp_path / "legacy.svg"
	output = tmp_path / "legacy.material.svg"
	source.write_text(_donor(bounds_in_clip=True), encoding="utf-8")
	refactor_liquid_svg.refactor_liquid_svg(source, _write_review(source, _legacy_runs()), output)
	root = lxml.etree.parse(str(output)).getroot()
	clip = next(element for element in root.iter() if element.get("id") == "anchor_liquid_clip")
	bounds = next(element for element in root.iter() if element.get("id") == "anchor_liquid_bounds")
	assert bounds.getparent() is root and bounds.get("display") == "none"
	assert any(lxml.etree.QName(child).localname == "rect" and child.get("id") is None for child in clip)


@pytest.mark.parametrize(
	"hidden_attribute",
	[
		'display="none"',
		'visibility="hidden"',
		'opacity="0"',
		'style="display:none"',
		'style="visibility:hidden"',
		'style="opacity:0"',
	],
)
def test_refactor_cleans_hidden_legacy_bounds_before_retaining_clip_geometry(tmp_path: Path, hidden_attribute: str):
	"""Legacy clip bounds retain geometry, never their non-rendering paint state."""
	source = tmp_path / "legacy.svg"
	output = tmp_path / "legacy.material.svg"
	legacy = _donor(bounds_in_clip=True).replace('height="9"', 'height="9" rx="1" ry="2"', 1)
	source.write_text(legacy.replace('/>', f' {hidden_attribute}/> ', 1), encoding="utf-8")
	refactor_liquid_svg.refactor_liquid_svg(source, _write_review(source, _legacy_runs()), output)
	root = lxml.etree.parse(str(output)).getroot()
	validate_material_svg(root)
	clip = next(element for element in root.iter() if element.get("id") == "anchor_liquid_clip")
	clone = next(child for child in clip if lxml.etree.QName(child).localname == "rect")
	assert clone.get("id") is None
	assert clone.get("style") is None
	assert all(clone.get(key) is None for key in ("display", "visibility", "opacity", "fill", "stroke", "class"))
	assert {key: clone.get(key) for key in ("x", "y", "width", "height")} == {
		"x": "1", "y": "2", "width": "8", "height": "9",
	}
	assert clone.get("rx") == "1" and clone.get("ry") == "2"


def test_refactor_second_run_is_a_byte_identical_no_write_before_review_read(tmp_path: Path):
	"""An exact valid material source succeeds without reading stale review input."""
	source = tmp_path / "source.svg"
	converted = tmp_path / "converted.svg"
	source.write_text(_donor(), encoding="utf-8")
	review = _write_review(source, _runs())
	refactor_liquid_svg.refactor_liquid_svg(source, review, converted)
	before = converted.read_bytes()
	missing_review = tmp_path / "does-not-exist.json"
	(converted.with_name("converted.material.svg")).write_text("must remain untouched", encoding="utf-8")
	different_output = tmp_path / "different-output.svg"
	result = refactor_liquid_svg.refactor_liquid_svg(converted, missing_review, different_output)
	assert not result.changed and result.output_path == converted.resolve() and converted.read_bytes() == before
	assert not different_output.exists()


@pytest.mark.parametrize(
	("runs", "message"),
	[
		([
			{"layer_name": "liquid_body", "paint_role": "base", "liquid_part": "body", "unit_indices": [3]},
			{"layer_name": "liquid_shadow", "paint_role": "shadow", "liquid_part": "body", "adjustment": "-0.2", "unit_indices": [5]},
		], "every artwork position"),
		([{"layer_name": "liquid_body", "paint_role": "highlight", "liquid_part": "surface", "adjustment": "0.2", "unit_indices": [3]}], "at least one base"),
		([{"layer_name": "bad-name", "paint_role": "base", "liquid_part": "body", "unit_indices": [3]}], "snake_case"),
	],
)
def test_refactor_rejects_invalid_reviewed_material_band_without_output(tmp_path: Path, runs: list[dict], message: str):
	"""Bad review semantics cannot produce a partial material source file."""
	source = tmp_path / "donor.svg"
	output = tmp_path / "out.svg"
	source.write_text(_donor(), encoding="utf-8")
	with pytest.raises(refactor_liquid_svg.LiquidSvgRefactorError, match=message):
		refactor_liquid_svg.refactor_liquid_svg(source, _write_review(source, runs), output)
	assert not output.exists()


def test_refactor_rejects_unknown_review_keys_without_output(tmp_path: Path):
	"""The transient review format is closed rather than a recipe escape hatch."""
	source = tmp_path / "donor.svg"
	output = tmp_path / "out.svg"
	source.write_text(_donor(), encoding="utf-8")
	review = _write_review(source, _runs(), source_hash="0" * 64, extra={"extra": "no"})
	with pytest.raises(refactor_liquid_svg.LiquidSvgRefactorError, match="unknown key"):
		refactor_liquid_svg.refactor_liquid_svg(source, review, output)
	assert not output.exists()


def test_refactor_rejects_hash_drift_without_writing_a_partial_output(tmp_path: Path):
	"""A reviewed classification is tied to the exact donor bytes it inspected."""
	source = tmp_path / "donor.svg"
	output = tmp_path / "out.svg"
	source.write_text(_donor(), encoding="utf-8")
	review = _write_review(source, _runs(), source_hash="0" * 64)
	with pytest.raises(refactor_liquid_svg.LiquidSvgRefactorError, match="does not match"):
		refactor_liquid_svg.refactor_liquid_svg(source, review, output)
	assert not output.exists()


def test_refactor_rejects_selector_style_and_atomic_nested_group_selection(tmp_path: Path):
	"""Selector behavior and descendant selection do not become grouping special cases."""
	source = tmp_path / "styled.svg"
	output = tmp_path / "out.svg"
	source.write_text(_donor(extra='<style>.x { fill: red; }</style>'), encoding="utf-8")
	with pytest.raises(refactor_liquid_svg.LiquidSvgRefactorError, match="style blocks"):
		refactor_liquid_svg.refactor_liquid_svg(source, _write_review(source, _runs()), output)
	assert not output.exists()


def test_refactor_rejects_a_descendant_as_though_it_were_a_root_artwork_unit(tmp_path: Path):
	"""Nested donor artwork remains atomic under its direct-root group unit."""
	source = tmp_path / "nested.svg"
	output = tmp_path / "out.svg"
	source.write_text(_donor(), encoding="utf-8")
	runs = [{"layer_name": "liquid_body", "paint_role": "base", "liquid_part": "body", "unit_indices": [6]}]
	with pytest.raises(refactor_liquid_svg.LiquidSvgRefactorError, match="non-artwork root-child index"):
		refactor_liquid_svg.refactor_liquid_svg(source, _write_review(source, runs), output)
	assert not output.exists()


def test_refactor_rejects_existing_output_and_reports_cli_failure(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
	"""The default never overwrites a donor or an existing output artifact."""
	source = tmp_path / "donor.svg"
	output = tmp_path / "out.svg"
	source.write_text(_donor(), encoding="utf-8")
	output.write_text("keep", encoding="utf-8")
	review = _write_review(source, _runs())
	assert refactor_liquid_svg.main(["--input", str(source), "--review", str(review), "--output", str(output)]) == 2
	assert "output already exists" in capsys.readouterr().err and output.read_text(encoding="utf-8") == "keep"


@pytest.mark.parametrize(
	"replacement",
	[
		'<rect id="anchor_liquid_bounds" x="1" y="2" width="8" height="9" display="none"/><rect id="anchor_liquid_bounds" x="1" y="2" width="8" height="9" display="none"/>',
		'<rect id="anchor_liquid_bounds" x="1" y="2" width="-8" height="9" display="none"/>',
	],
)
def test_refactor_rejects_invalid_anchor_contract_without_output(tmp_path: Path, replacement: str):
	"""Ambiguous or non-positive anchors require author repair, never a guess."""
	source = tmp_path / "bad_anchor.svg"
	output = tmp_path / "out.svg"
	source.write_text(_donor().replace('<rect id="anchor_liquid_bounds" x="1" y="2" width="8" height="9" display="none"/>', replacement), encoding="utf-8")
	with pytest.raises(refactor_liquid_svg.LiquidSvgRefactorError):
		refactor_liquid_svg.refactor_liquid_svg(source, _write_review(source, _runs()), output)
	assert not output.exists()
