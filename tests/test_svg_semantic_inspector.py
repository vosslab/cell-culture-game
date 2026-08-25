"""Behavioral checks for the normalized SVG semantic geometry inspector."""

# Standard Library
import json
from pathlib import Path

# PIP3 modules
import pytest

# Local application
from tools import svg_semantic_inspector


def _material_svg(*, transform: str = "") -> str:
	"""Return a material SVG with a deliberate five-unit top geometry gap."""
	transform_attribute = f' transform="{transform}"' if transform else ""
	return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 20" data-vlab-rendering="material">
<defs><clipPath id="anchor_liquid_clip"><rect x="0" y="0" width="10" height="20"/></clipPath></defs>
<g data-vlab-layer-name="fixed_back" data-vlab-layer-kind="fixed"><path d="M0 0H10V20H0Z" fill="#eeeeee"/></g>
<g data-vlab-layer-name="liquid_body" data-vlab-layer-kind="material" data-vlab-paint-role="base" data-vlab-liquid-part="body"{transform_attribute}><path d="M1 5H9V20H1Z" fill="#cc0066"/></g>
<g data-vlab-layer-name="liquid_surface" data-vlab-layer-kind="material" data-vlab-paint-role="highlight" data-vlab-adjustment="0.2" data-vlab-liquid-part="surface"><path d="M1 5C3 4 7 4 9 5V6H1Z" fill="#ff99cc"/></g>
<g data-vlab-layer-name="fixed_front" data-vlab-layer-kind="fixed"><path d="M0 0H10" stroke="#222222"/></g>
<rect id="anchor_liquid_bounds" x="0" y="0" width="10" height="20" display="none"/>
</svg>'''


def _variant_svg(*, liquid_fill: str, transform: str = "") -> str:
	"""Return one normalized donor variant with colored and shared-white art."""
	transform_attribute = f' transform="{transform}"' if transform else ""
	return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 20">
<path d="M0 0H10V20H0Z" fill="#eeeeee"/>
<path d="M1 5H9V20H1Z" fill="{liquid_fill}"{transform_attribute}/>
<path d="M1 5C3 4 7 4 9 5" fill="none" stroke="#fff"/>
</svg>'''


def test_inspector_reports_coordinate_model_layers_and_top_gap(tmp_path: Path) -> None:
	"""The report distinguishes geometric user units from physical volume."""
	source = tmp_path / "sample.svg"
	source.write_text(_material_svg(), encoding="utf-8")
	report = svg_semantic_inspector.inspect_material_svg(source)
	assert report["coordinate_system"] == {
		"dimension": "2d",
		"units": "svg_user_units",
		"x_axis": "right",
		"y_axis": "down",
		"bounds_model": "conservative_painted_aabb",
		"volume_inference": "none",
	}
	assert report["material"]["bounds"]["min_y"] == 4.0
	assert report["material"]["top_gap_to_clip"] == 4.0
	assert report["material"]["top_gap_to_level_frame"] == 4.0
	assert report["material"]["parts"]["body"]["min_y"] == 5.0
	assert report["material"]["parts"]["surface"]["min_y"] == 4.0
	assert report["material"]["surface_reference_y"] == 5.0
	assert report["material"]["body_join_y"] == 5.0
	assert report["material"]["body_anchor_y"] == 20.0
	assert report["warnings"] == [
		"material geometry begins below the liquid clip top",
		"material geometry begins below the authored level-frame top",
	]
	material_names = [layer["name"] for layer in report["layers"] if layer["kind"] == "material"]
	assert material_names == ["liquid_body", "liquid_surface"]


def test_inspector_reports_individual_element_paint_and_bounds(tmp_path: Path) -> None:
	"""Human review can trace a layer envelope back to its concrete artwork."""
	source = tmp_path / "sample.svg"
	source.write_text(_material_svg(), encoding="utf-8")
	report = svg_semantic_inspector.inspect_material_svg(source)
	body = next(layer for layer in report["layers"] if layer["name"] == "liquid_body")
	assert body["bounds"]["min_y"] == 5.0
	assert body["elements"] == [{
		"ordinal": 1,
		"tag": "path",
		"fill": "#cc0066",
		"stroke": None,
		"bounds": {
			"min_x": 1.0, "min_y": 5.0, "max_x": 9.0, "max_y": 20.0,
			"width": 8.0, "height": 15.0,
		},
	}]


def test_inspector_rejects_unflattened_transforms(tmp_path: Path) -> None:
	"""The inspector refuses to approximate a coordinate frame normalization owns."""
	source = tmp_path / "transformed.svg"
	source.write_text(_material_svg(transform="translate(0 2)"), encoding="utf-8")
	with pytest.raises(svg_semantic_inspector.SvgSemanticInspectionError, match="normalize"):
		svg_semantic_inspector.inspect_material_svg(source)


def test_cli_emits_one_json_object_without_modifying_source(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
	"""The read-only CLI emits stable machine-readable evidence for one asset."""
	source = tmp_path / "sample.svg"
	source.write_text(_material_svg(), encoding="utf-8")
	before = source.read_bytes()
	assert svg_semantic_inspector.main([str(source)]) == 0
	report = json.loads(capsys.readouterr().out)
	assert report["asset"] == source.as_posix()
	assert report["schema_version"] == 2
	assert source.read_bytes() == before


def test_variant_comparison_proposes_changed_paint_and_flags_shared_white(tmp_path: Path) -> None:
	"""Variant paint is evidence while shared white artwork remains reviewable."""
	pink = tmp_path / "pink.svg"
	green = tmp_path / "green.svg"
	pink.write_text(_variant_svg(liquid_fill="#cc0066"), encoding="utf-8")
	green.write_text(_variant_svg(liquid_fill="#339966"), encoding="utf-8")
	report = svg_semantic_inspector.compare_svg_variants([pink, green])
	assert report["mode"] == "variant_paint_comparison"
	assert len(report["changed_paint"]) == 1
	assert report["changed_paint"][0]["bounds"] == {
		"min_x": 1.0, "min_y": 5.0, "max_x": 9.0, "max_y": 20.0,
		"width": 8.0, "height": 15.0,
	}
	assert len(report["shared_white_or_translucent"]) == 1
	assert report["shared_white_or_translucent"][0]["tag"] == "path"
	assert report["unmatched_geometry"] == []


def test_variant_comparison_rejects_unflattened_geometry(tmp_path: Path) -> None:
	"""Variant correspondence is not guessed across unnormalized transforms."""
	pink = tmp_path / "pink.svg"
	green = tmp_path / "green.svg"
	pink.write_text(_variant_svg(liquid_fill="#cc0066"), encoding="utf-8")
	green.write_text(
		_variant_svg(liquid_fill="#339966", transform="translate(0 1)"),
		encoding="utf-8",
	)
	with pytest.raises(svg_semantic_inspector.SvgSemanticInspectionError, match="normalize"):
		svg_semantic_inspector.compare_svg_variants([pink, green])


def test_variant_comparison_cli_emits_one_report(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
	"""The CLI exposes the reusable read-only donor-family comparison."""
	pink = tmp_path / "pink.svg"
	green = tmp_path / "green.svg"
	pink.write_text(_variant_svg(liquid_fill="#cc0066"), encoding="utf-8")
	green.write_text(_variant_svg(liquid_fill="#339966"), encoding="utf-8")
	assert svg_semantic_inspector.main([
		"--compare-variants", str(pink), str(green),
	]) == 0
	report = json.loads(capsys.readouterr().out)
	assert report["assets"] == [pink.as_posix(), green.as_posix()]
	assert len(report["changed_paint"]) == 1
