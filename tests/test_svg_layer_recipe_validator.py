"""Behavioral checks for material SVG semantic validation and compilation."""

from pathlib import Path

import lxml.etree
import pytest

from pipeline import gen_liquid_regions
from pipeline import gen_svg_manifest
from tools import normalize_svg_v3
from validation.svg.layer_recipe_validator import (
	MaterialSvgValidationError,
	inject_normalizer_boundary_tokens,
	material_boundary_signature,
	remove_normalizer_boundary_tokens,
	validate_material_svg,
)
from validation.svg import layer_recipe_validator


def _svg(body: str) -> str:
	"""Wrap inline material content in the required structural anchors."""
	return f'''<svg xmlns="http://www.w3.org/2000/svg" data-vlab-rendering="material">
<defs><clipPath id="anchor_liquid_clip"><path d="M0 0H10V10H0Z"/></clipPath></defs>
<rect id="anchor_liquid_bounds" x="0" y="0" width="10" height="10" display="none"/>
{body}</svg>'''


def _valid_body() -> str:
	"""Return a valid recipe with repeated roles and nested ordinary artwork."""
	return '''<g data-vlab-layer-name="glass_back" data-vlab-layer-kind="fixed"><path d="M0 0H10" fill="#111111"/></g>
<g data-vlab-layer-name="liquid_body" data-vlab-layer-kind="material" data-vlab-paint-role="base" data-vlab-liquid-part="body"><g><path d="M0 0H10V10Z" fill="#00aa00"/></g></g>
<g data-vlab-layer-name="liquid_glint" data-vlab-layer-kind="material" data-vlab-paint-role="highlight" data-vlab-adjustment="0.2" data-vlab-liquid-part="surface"><path d="M1 1H2V2Z" fill="#ffffff"/></g>
<g data-vlab-layer-name="glass_front" data-vlab-layer-kind="fixed"><path d="M0 10H10" stroke="#222222"/></g>'''


def test_validator_accepts_repeated_roles_and_nested_artwork():
	"""Valid semantic groups preserve repeatable roles and ordinary nesting."""
	root = lxml.etree.fromstring(_svg(_valid_body().replace('</g></g>\n<g data-vlab-layer-name="liquid_glint"', '<path d="M2 2H3V3Z" fill="#00aa00"/></g></g>\n<g data-vlab-layer-name="liquid_glint"')).encode("utf-8"))
	signature = validate_material_svg(root)
	assert signature.layers[1][2] == "base"


@pytest.mark.parametrize("body", [
	'''<g data-vlab-layer-name="bad-name" data-vlab-layer-kind="material" data-vlab-paint-role="base"><path d="M0 0H1" fill="#000"/></g>''',
	'''<g data-vlab-layer-name="liquid" data-vlab-layer-kind="material" data-vlab-paint-role="highlight" data-vlab-adjustment="0"><path d="M0 0H1" fill="#000"/></g>''',
	'''<g data-vlab-layer-name="liquid" data-vlab-layer-kind="fixed" data-vlab-paint-role="base"><path d="M0 0H1" fill="#000"/></g>''',
	'''<g data-vlab-layer-name="a" data-vlab-layer-kind="material" data-vlab-paint-role="base"><path d="M0 0H1" fill="#000"/></g><g data-vlab-layer-name="fixed" data-vlab-layer-kind="fixed"><path d="M0 0H1" fill="#000"/></g><g data-vlab-layer-name="b" data-vlab-layer-kind="material" data-vlab-paint-role="base"><path d="M0 0H1" fill="#000"/></g>''',
])
def test_validator_rejects_invalid_recipe_categories(body: str):
	"""Malformed roles, names, and material bands do not enter compilation."""
	root = lxml.etree.fromstring(_svg(body).encode("utf-8"))
	with pytest.raises(MaterialSvgValidationError):
		validate_material_svg(root)


@pytest.mark.parametrize(
	("body", "message"),
	[
		(
			'''<g data-vlab-layer-name="liquid" data-vlab-layer-kind="material" data-vlab-paint-role="base"><path d="M0 0H1" fill="#000"/></g>''',
			"requires bottom, body, or surface",
		),
		(
			'''<g data-vlab-layer-name="liquid" data-vlab-layer-kind="material" data-vlab-paint-role="base" data-vlab-liquid-part="middle"><path d="M0 0H1" fill="#000"/></g>''',
			"requires bottom, body, or surface",
		),
		(
			'''<g data-vlab-layer-name="glass" data-vlab-layer-kind="fixed" data-vlab-liquid-part="bottom"><path d="M0 0H1" fill="#000"/></g>''',
			"fixed layer",
		),
	],
)
def test_validator_enforces_closed_gravity_part_ownership(body: str, message: str):
	"""Only material layers own one canonical gravity-part value."""
	root = lxml.etree.fromstring(_svg(body).encode("utf-8"))
	with pytest.raises(MaterialSvgValidationError, match=message):
		validate_material_svg(root)


def test_compiler_emits_opaque_handles_and_literal_fallback(tmp_path: Path):
	"""Compiler produces deterministic private runtime data without color inference."""
	source = tmp_path / "sample.svg"
	output = tmp_path / "generated.svg"
	source.write_text(_svg(_valid_body()), encoding="utf-8")
	entry = gen_liquid_regions.compile_material_svg(source, output, "sample")
	compiled = output.read_text(encoding="utf-8")
	assert "liquid_body" not in compiled and "var(--lr_" in compiled
	assert "data-vlab-layer-name" not in compiled
	assert entry["region_handle"] in compiled
	assert entry["reveal_handle"] in compiled
	assert entry["paints"][0]["element_handle"] != entry["paints"][0]["paint_handle"]
	assert entry["paints"][0]["adjustment"] is None
	assert entry["paints"][0]["liquid_part"] == "body"
	assert entry["surface_reference_y"] == 0.0
	assert entry["body_join_y"] == 0.0
	assert entry["body_anchor_y"] == 10.0


def test_compiler_derives_separate_surface_and_body_join_datums(tmp_path: Path):
	"""A body joins the base surface at its authored tangent line, not its lower edge."""
	source = tmp_path / "surface_depth.svg"
	body = _valid_body().replace(
		'M0 0H10V10Z', 'M1 2H9V10H1Z',
	).replace(
		'<g data-vlab-layer-name="liquid_glint"',
		'<g data-vlab-layer-name="liquid_surface" data-vlab-layer-kind="material" data-vlab-paint-role="base" data-vlab-liquid-part="surface"><path d="M1 0H9V4H1Z" fill="#00aa00"/></g>\n<g data-vlab-layer-name="liquid_glint"',
	)
	source.write_text(_svg(body), encoding="utf-8")
	entry = gen_liquid_regions.compile_material_svg(source, tmp_path / "out.svg", "surface_depth")
	assert entry["surface_reference_y"] == 0.0
	assert entry["body_join_y"] == 2.0


def test_compiler_carries_the_optional_root_fill_ceiling(tmp_path: Path):
	"""A material form owns its closed fill ceiling through generated metadata."""
	source = tmp_path / "capped.svg"
	source.write_text(
		_svg(_valid_body()).replace(
			'data-vlab-rendering="material"',
			'data-vlab-rendering="material" data-vlab-max-fill-percent="70"',
		),
		encoding="utf-8",
	)
	entry = gen_liquid_regions.compile_material_svg(source, tmp_path / "out.svg", "capped")
	assert entry["max_fill_percent"] == 70
	assert "data-vlab-max-fill-percent" not in (tmp_path / "out.svg").read_text(encoding="utf-8")


def test_compiler_carries_optional_conical_body_start_calibration(tmp_path: Path):
	"""A material form carries its closed cone-to-body volume transition."""
	source = tmp_path / "conical.svg"
	source.write_text(
		_svg(_valid_body().replace("M0 0H10V10Z", "M0 0H10V8Z")).replace(
			'data-vlab-rendering="material"',
			'data-vlab-rendering="material" data-vlab-body-start-fill-percent="3.5"',
		),
		encoding="utf-8",
	)
	entry = gen_liquid_regions.compile_material_svg(source, tmp_path / "out.svg", "conical")
	assert entry["body_start_fill_percent"] == pytest.approx(3.5)
	assert "data-vlab-body-start-fill-percent" not in (tmp_path / "out.svg").read_text(
		encoding="utf-8",
	)


def test_compiler_carries_optional_normalized_fill_height_exponent(tmp_path: Path):
	"""A material form may own a normalized perceptual height calibration."""
	source = tmp_path / "exponent.svg"
	source.write_text(
		_svg(_valid_body()).replace(
			'data-vlab-rendering="material"',
			'data-vlab-rendering="material" data-vlab-fill-height-exponent="0.45"',
		),
		encoding="utf-8",
	)
	entry = gen_liquid_regions.compile_material_svg(source, tmp_path / "out.svg", "exponent")
	assert entry["fill_height_exponent"] == pytest.approx(0.45)
	assert "data-vlab-fill-height-exponent" not in (tmp_path / "out.svg").read_text(
		encoding="utf-8",
	)


@pytest.mark.parametrize("value", ("0", "70.5", "101", "-1", " 70"))
def test_validator_rejects_invalid_root_fill_ceiling(value: str):
	"""The root ceiling is a bounded integer semantic term, never free-form SVG data."""
	root = lxml.etree.fromstring(
		_svg(_valid_body()).replace(
			'data-vlab-rendering="material"',
			f'data-vlab-rendering="material" data-vlab-max-fill-percent="{value}"',
		).encode("utf-8"),
	)
	with pytest.raises(MaterialSvgValidationError, match="max-fill-percent"):
		validate_material_svg(root)


@pytest.mark.parametrize("value", ("0", "100", "-1", "+1", "NaN", "1e1", " 3.5"))
def test_validator_rejects_invalid_conical_body_start_calibration(value: str):
	"""The cone-to-body transition is a finite bounded decimal, not free-form data."""
	root = lxml.etree.fromstring(
		_svg(_valid_body()).replace(
			'data-vlab-rendering="material"',
			f'data-vlab-rendering="material" data-vlab-body-start-fill-percent="{value}"',
		).encode("utf-8"),
	)
	with pytest.raises(MaterialSvgValidationError, match="body-start-fill-percent"):
		validate_material_svg(root)


@pytest.mark.parametrize("value", ("0", "10.1", "-1", "+1", "NaN", "1e1", " 0.45"))
def test_validator_rejects_invalid_fill_height_exponent(value: str):
	"""The perceptual curve is a bounded decimal, never arbitrary SVG data."""
	root = lxml.etree.fromstring(
		_svg(_valid_body()).replace(
			'data-vlab-rendering="material"',
			f'data-vlab-rendering="material" data-vlab-fill-height-exponent="{value}"',
		).encode("utf-8"),
	)
	with pytest.raises(MaterialSvgValidationError, match="fill-height-exponent"):
		validate_material_svg(root)


def test_validator_rejects_combining_conical_and_exponent_calibrations():
	"""The two height mappings have incompatible geometric interpretations."""
	root = lxml.etree.fromstring(
		_svg(_valid_body()).replace(
			'data-vlab-rendering="material"',
			'data-vlab-rendering="material" data-vlab-body-start-fill-percent="3.5" '
			'data-vlab-fill-height-exponent="0.45"',
		).encode("utf-8"),
	)
	with pytest.raises(MaterialSvgValidationError, match="mutually exclusive"):
		validate_material_svg(root)


def test_compiler_derives_gravity_part_calibration_without_bottom_overscan(tmp_path: Path):
	"""Body calibration comes from its authored top and fixed lower anchor."""
	body = _valid_body().replace(
		"M0 0H10V10Z", "M0 4H10V24H0Z",
	).replace("M1 1H2V2Z", "M1 4H2V5Z")
	source = tmp_path / "partial.svg"
	output = tmp_path / "partial_out.svg"
	source.write_text(_svg(body), encoding="utf-8")
	entry = gen_liquid_regions.compile_material_svg(source, output, "partial")
	assert entry["surface_reference_y"] == 4.0
	assert entry["body_join_y"] == 4.0
	assert entry["body_anchor_y"] == 24.0

	insufficient = tmp_path / "insufficient.svg"
	insufficient.write_text(_svg(body.replace("V24", "V10")), encoding="utf-8")
	insufficient_entry = gen_liquid_regions.compile_material_svg(
		insufficient, tmp_path / "insufficient_out.svg", "insufficient"
	)
	assert insufficient_entry["body_anchor_y"] == 10.0


def test_publication_requires_compiled_material_artifact(tmp_path: Path):
	"""Publication dispatch never falls back from material source to source copy."""
	assets = tmp_path / "assets"
	source = assets / "equipment" / "variable_volume" / "sample.svg"
	source.parent.mkdir(parents=True)
	source.write_text(_svg(_valid_body()), encoding="utf-8")
	with pytest.raises(FileNotFoundError):
		gen_svg_manifest.plan_svg_publication(source, assets, tmp_path / "generated")


def test_publication_tree_selects_compiled_material_and_ordinary_source(tmp_path: Path):
	"""The built URL tree never exposes an authored material SVG form."""
	assets = tmp_path / "assets"
	generated = tmp_path / "generated"
	material_source = assets / "equipment" / "variable_volume" / "material.svg"
	ordinary_source = assets / "equipment" / "static" / "ordinary.svg"
	material_source.parent.mkdir(parents=True)
	ordinary_source.parent.mkdir(parents=True)
	material_source.write_text(_svg(_valid_body()), encoding="utf-8")
	ordinary_source.write_text(
		'<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0H1"/></svg>',
		encoding="utf-8",
	)
	compiled = generated / "material_svg" / "equipment" / "variable_volume" / "material.svg"
	compiled.parent.mkdir(parents=True)
	compiled.write_text('<svg xmlns="http://www.w3.org/2000/svg" id="compiled"/>', encoding="utf-8")
	out = tmp_path / "dist" / "assets" / "svg"
	gen_svg_manifest.publish_svg_tree(assets, generated, out)
	assert (out / "equipment" / "material.svg").read_bytes() == compiled.read_bytes()
	assert (out / "equipment" / "ordinary.svg").read_bytes() == ordinary_source.read_bytes()


def test_sanitizer_preserves_valid_semantics_but_removes_untrusted_attributes():
	"""Manifest sanitation deliberately retains only the approved material carrier."""
	body = _valid_body().replace(
		'<g><path d="M0 0H10V10Z" fill="#00aa00"/></g>',
		'<g><path d="M0 0H10V10Z" fill="#00aa00"/><path d="M2 2H3V3Z" fill="#00aa00"/></g>',
	)
	root = lxml.etree.fromstring(_svg(body).encode("utf-8"))
	root.set("data-vlab-fill-height-exponent", "0.45")
	root.set("onclick", "bad()")
	gen_svg_manifest._strip_unsafe_attrs(root, preserve_material_semantics=True)
	assert root.get("data-vlab-rendering") == "material"
	assert root.get("data-vlab-fill-height-exponent") == "0.45"
	assert root.get("onclick") is None
	assert root[2].get("data-vlab-layer-name") == "glass_back"
	validate_material_svg(root)


def test_normalizer_preserves_material_boundaries_and_is_idempotent(tmp_path: Path):
	"""Material policy retains semantic order while ordinary geometry normalizes."""
	source = tmp_path / "source.svg"
	first = tmp_path / "first.svg"
	second = tmp_path / "second.svg"
	source.write_text(_svg(_valid_body()), encoding="utf-8")
	result = normalize_svg_v3.normalize_svg_file(source, first, padding=0.0)
	assert result.normalized, result.rejection
	root = lxml.etree.parse(str(first)).getroot()
	signature = validate_material_svg(root)
	assert [layer[0] for layer in signature.layers] == [
		"glass_back", "liquid_body", "liquid_glint", "glass_front",
	]
	second_result = normalize_svg_v3.normalize_svg_file(first, second, padding=0.0)
	assert second_result.normalized, second_result.rejection
	assert first.read_bytes() == second.read_bytes()


def test_normalizer_preserves_material_authored_frame_and_anchor_coordinates(tmp_path: Path):
	"""Material normalization keeps the authored viewport and structural coordinates."""
	source = tmp_path / "source.svg"
	first = tmp_path / "first.svg"
	second = tmp_path / "second.svg"
	source.write_text(
		'''<svg xmlns="http://www.w3.org/2000/svg" width="300" height="600" viewBox="10 20 100 200" data-vlab-rendering="material">
<defs><clipPath id="anchor_liquid_clip"><path d="M25 60H75V180H25Z"/></clipPath></defs>
<rect id="anchor_liquid_bounds" x="25" y="60" width="50" height="120" display="none"/>
<g data-vlab-layer-name="glass_back" data-vlab-layer-kind="fixed"><path d="M15 25H105V215H15Z" fill="#111111"/></g>
<g data-vlab-layer-name="liquid_body" data-vlab-layer-kind="material" data-vlab-paint-role="base" data-vlab-liquid-part="body"><path d="M25 60H75V180H25Z" fill="#00aa00"/></g>
<g data-vlab-layer-name="glass_front" data-vlab-layer-kind="fixed"><path d="M20 30H100V210H20Z" fill="#222222"/></g>
</svg>''',
		encoding="utf-8",
	)
	result = normalize_svg_v3.normalize_svg_file(source, first, padding=37.0)
	assert result.normalized, result.rejection
	assert result.view_box == "10 20 100 200"
	root = lxml.etree.parse(str(first)).getroot()
	assert root.get("viewBox") == "10 20 100 200"
	assert root.get("width") == "300"
	assert root.get("height") == "600"
	bounds = root.xpath('.//*[local-name()="rect" and @id="anchor_liquid_bounds"]')[0]
	assert {name: bounds.get(name) for name in ("x", "y", "width", "height")} == {
		"x": "25", "y": "60", "width": "50", "height": "120",
	}
	clip_path = root.xpath('.//*[local-name()="clipPath" and @id="anchor_liquid_clip"]/*[local-name()="path"]')[0]
	assert clip_path.get("d") == "M25 60H75V180H25Z"
	liquid_path = root.xpath('.//*[local-name()="g" and @data-vlab-layer-name="liquid_body"]//*[local-name()="path"]')[0]
	assert liquid_path.get("d") == "M25 60H75V180H25Z"
	second_result = normalize_svg_v3.normalize_svg_file(first, second, padding=0.0)
	assert second_result.normalized, second_result.rejection
	assert first.read_bytes() == second.read_bytes()


def test_validator_requires_semantic_ownership_only_for_visible_external_geometry():
	"""Hidden external geometry is inert; visible external geometry is not."""
	hidden = lxml.etree.fromstring(_svg(_valid_body() + '<g display="none"><path d="M0 0H1"/></g>').encode("utf-8"))
	validate_material_svg(hidden)
	visible = lxml.etree.fromstring(_svg(_valid_body() + '<path d="M0 0H1" fill="#000"/>').encode("utf-8"))
	with pytest.raises(MaterialSvgValidationError, match="geometry must belong"):
		validate_material_svg(visible)


def test_visible_geometry_uses_inline_precedence_and_channel_specific_opacity():
	"""Classification follows SVG precedence without hiding a painted stroke."""
	body = _valid_body() + '''<g display="none"><path d="M0 0H1" fill="#000" style="display:inline"/></g>
<path d="M0 0H1" fill="none" stroke="#000" fill-opacity="0" stroke-opacity="1"/>
<path d="M0 0H1" fill="#000" style="fill:none;stroke:none"/>'''
	root = lxml.etree.fromstring(_svg(body).encode("utf-8"))
	with pytest.raises(MaterialSvgValidationError, match="geometry must belong"):
		validate_material_svg(root)


def test_visibility_inherit_under_hidden_ancestor_is_not_renderable():
	"""Inherited visibility cannot revive a hidden ancestor."""
	root = lxml.etree.fromstring(
		'<svg xmlns="http://www.w3.org/2000/svg"><g visibility="hidden"><path visibility="inherit" d="M0 0H1" fill="#000"/></g></svg>'.encode("utf-8"),
	)
	path = next(root.iter("{%s}path" % "http://www.w3.org/2000/svg"))
	assert not layer_recipe_validator.is_visible_renderable(path)


def test_svg_keyword_comparisons_are_case_insensitive():
	"""SVG visibility, display, paint, and inherit keywords ignore case."""
	root = lxml.etree.fromstring(
		'''<svg xmlns="http://www.w3.org/2000/svg" fill="NoNe">
<g display="NONE"><path d="M0 0H1" fill="#000"/></g>
<g visibility="HIDDEN"><path d="M0 0H1" fill="#000"/></g>
<path d="M0 0H1" fill="InHeRiT"/>
<path d="M0 0H1" fill="NONE"/>
</svg>'''.encode("utf-8"),
	)
	paths = list(root.iter("{%s}path" % "http://www.w3.org/2000/svg"))
	assert all(not layer_recipe_validator.is_visible_renderable(path) for path in paths)


def test_fill_inherit_under_none_and_duplicate_inline_values_are_resolved():
	"""The supported cascade has explicit inherit and last-declaration behavior."""
	root = lxml.etree.fromstring(
		'<svg xmlns="http://www.w3.org/2000/svg" fill="none"><path d="M0 0H1" fill="inherit"/><path d="M1 0H2" style="fill:#111; fill:none"/></svg>'.encode("utf-8"),
	)
	paths = list(root.iter("{%s}path" % "http://www.w3.org/2000/svg"))
	assert not layer_recipe_validator._is_visible_renderable(paths[0])
	assert layer_recipe_validator._style_value(paths[1], "fill") == "none"
	paths[1].set("style", "fill:#111; fill:none; fill:#222 !important")
	assert layer_recipe_validator._style_value(paths[1], "fill") == "#222"


def test_opacity_inherit_composites_parent_value_with_mixed_case_inline_important():
	"""Explicit opacity inherit resolves before each nested SVG group composites."""
	root = lxml.etree.fromstring(
		'''<svg xmlns="http://www.w3.org/2000/svg" opacity="0.5">
<g style="opacity: InHeRiT !IMPORTANT"><path opacity="iNhErIt" d="M0 0H1" fill="#000"/></g>
</svg>'''.encode("utf-8"),
	)
	path = next(root.iter("{%s}path" % "http://www.w3.org/2000/svg"))
	assert layer_recipe_validator._channel_opacity(path, "fill") == 0.125


def test_material_validation_accepts_inert_classes_rejects_selector_paint_and_runtime_namespace():
	"""Classes remain styling, but unresolved selector-driven paint fails loudly."""
	class_root = lxml.etree.fromstring(_svg(_valid_body().replace('fill="#00aa00"', 'class="liquid"')).encode("utf-8"))
	validate_material_svg(class_root)
	selector_root = lxml.etree.fromstring(_svg('<style>.liquid { fill: #00aa00; }</style>' + _valid_body().replace('fill="#00aa00"', 'class="liquid"')).encode("utf-8"))
	with pytest.raises(MaterialSvgValidationError, match="class and stylesheet"):
		validate_material_svg(selector_root)
	runtime_id = lxml.etree.fromstring(_svg(_valid_body().replace('fill="#00aa00"', 'id="lr_not_runtime" fill="#00aa00"')).encode("utf-8"))
	with pytest.raises(MaterialSvgValidationError, match="runtime handles"):
		validate_material_svg(runtime_id)


@pytest.mark.parametrize("bounds", [
	'<rect id="anchor_liquid_bounds" x="0" y="0" width="-1" height="10" display="none"/>',
	'<rect id="anchor_liquid_bounds" x="0" y="0" width="NaN" height="10" display="none"/>',
	'<rect id="anchor_liquid_bounds" x="0" y="0" width="10" display="none"/>',
])
def test_compiler_rejects_invalid_finite_bounds(bounds: str, tmp_path: Path):
	"""Runtime manifest bounds are always finite and positive."""
	source = tmp_path / "invalid_bounds.svg"
	source.write_text(_svg(_valid_body()).replace('<rect id="anchor_liquid_bounds" x="0" y="0" width="10" height="10" display="none"/>', bounds), encoding="utf-8")
	with pytest.raises((ValueError, MaterialSvgValidationError)):
		gen_liquid_regions.compile_material_svg(source, tmp_path / "out.svg", "invalid_bounds")


def test_compiler_keeps_clip_definition_removes_bounds_and_preserves_none_channel(tmp_path: Path):
	"""Compiled output owns the level clip but not the compiler-only bounds anchor."""
	body = _valid_body().replace('fill="#00aa00"', 'fill="none" stroke="#00aa00"')
	source = tmp_path / "sample.svg"
	output = tmp_path / "out.svg"
	source.write_text(_svg(body), encoding="utf-8")
	gen_liquid_regions.compile_material_svg(source, output, "painted_stroke")
	compiled = output.read_text(encoding="utf-8")
	assert 'id="anchor_liquid_bounds"' not in compiled
	assert 'id="anchor_liquid_clip"' in compiled and 'clip-path="url(#anchor_liquid_clip)"' in compiled
	assert 'fill="none"' in compiled and 'var(--lr_' in compiled


def test_material_layer_with_only_case_insensitive_none_is_rejected():
	"""A material role with no painted channel cannot satisfy the SVG contract."""
	body = _valid_body().replace('fill="#00aa00"', 'fill="NONE" stroke="NoNe"', 1)
	root = lxml.etree.fromstring(_svg(body).encode("utf-8"))
	with pytest.raises(MaterialSvgValidationError, match="visible renderable geometry"):
		validate_material_svg(root)


def test_compiler_keeps_case_insensitive_none_channel_unmodified(tmp_path: Path):
	"""A NONE channel stays literal and never receives a generated paint variable."""
	body = _valid_body().replace('fill="#00aa00"', 'fill="NONE" stroke="#00aa00"', 1)
	source = tmp_path / "sample.svg"
	output = tmp_path / "out.svg"
	source.write_text(_svg(body), encoding="utf-8")
	entry = gen_liquid_regions.compile_material_svg(source, output, "case_none")
	compiled = output.read_text(encoding="utf-8")
	paint = entry["paints"][0]["paint_handle"]
	assert 'fill="NONE"' in compiled
	assert f"var(--{paint}, NONE)" not in compiled
	assert f"var(--{paint}, #00aa00)" in compiled


def test_tree_contract_scans_ordinary_svg_reserved_attributes_before_compilation(tmp_path: Path):
	"""A malformed ordinary form cannot bypass the semantic compiler gate."""
	assets = tmp_path / "assets"
	material = assets / "equipment" / "variable_volume" / "material.svg"
	ordinary = assets / "equipment" / "static" / "ordinary.svg"
	material.parent.mkdir(parents=True)
	ordinary.parent.mkdir(parents=True)
	material.write_text(_svg(_valid_body()), encoding="utf-8")
	ordinary.write_text('<svg xmlns="http://www.w3.org/2000/svg"><path data-vlab-layer-name="bad"/></svg>', encoding="utf-8")
	with pytest.raises(MaterialSvgValidationError):
		gen_liquid_regions.compile_material_tree(assets, tmp_path / "generated")
	assert not (tmp_path / "generated" / "liquid_regions.json").exists()


def test_compile_failure_leaves_no_partial_material_artifact(tmp_path: Path):
	"""The normalize-to-compile seam publishes nothing when source validation fails."""
	source = tmp_path / "bad.svg"
	output = tmp_path / "generated.svg"
	source.write_text(_svg(_valid_body().replace('data-vlab-layer-kind="material"', 'data-vlab-layer-kind="material" clip-path="url(#anchor_liquid_clip)"', 1)), encoding="utf-8")
	with pytest.raises(ValueError, match="material normalization failed"):
		gen_liquid_regions.compile_material_svg(source, output, "bad")
	assert not output.exists()


def test_normalizer_private_ownership_markers_detect_moved_geometry_and_are_not_serialized(tmp_path: Path):
	"""Same-count path moves fail the material-boundary proof before output."""
	source = tmp_path / "source.svg"
	output = tmp_path / "out.svg"
	source.write_text(_svg(_valid_body()), encoding="utf-8")
	result = normalize_svg_v3.normalize_svg_file(source, output, padding=0.0)
	assert result.normalized, result.rejection
	assert "normalizer-boundary-token" not in output.read_text(encoding="utf-8")
	body = _valid_body().replace(
		'<g><path d="M0 0H10V10Z" fill="#00aa00"/></g>',
		'<g><path d="M0 0H10V10Z" fill="#00aa00"/><path d="M2 2H3V3Z" fill="#00aa00"/></g>',
	)
	root = lxml.etree.fromstring(_svg(body).encode("utf-8"))
	inject_normalizer_boundary_tokens(root)
	before = material_boundary_signature(root, allow_normalizer_tokens=True)
	layers = [child for child in root if child.get("data-vlab-layer-kind") is not None]
	moved = next(layers[1].iter("{%s}path" % "http://www.w3.org/2000/svg"))
	moved.getparent().remove(moved)
	layers[2].append(moved)
	after = material_boundary_signature(root, allow_normalizer_tokens=True)
	assert before != after
	remove_normalizer_boundary_tokens(root)
	assert "normalizer-boundary-token" not in lxml.etree.tostring(root, encoding="unicode")


def test_aggregate_manifest_is_sorted_and_does_not_leak_authored_recipe_names(tmp_path: Path):
	"""Aggregate runtime data is deterministic and exposes only generated handles."""
	assets = tmp_path / "assets"
	for name in ("zeta", "alpha"):
		path = assets / "equipment" / "variable_volume" / f"{name}.svg"
		path.parent.mkdir(parents=True, exist_ok=True)
		path.write_text(_svg(_valid_body()), encoding="utf-8")
	generated = tmp_path / "generated"
	gen_liquid_regions.compile_material_tree(assets, generated)
	manifest = (generated / "liquid_regions.json").read_text(encoding="utf-8")
	assert manifest.index('"alpha"') < manifest.index('"zeta"')
	assert "liquid_body" not in manifest and "#00aa00" not in manifest


def test_normalizer_preserves_private_boundary_tokens_across_shape_conversion_and_transform(tmp_path: Path):
	"""Material shapes retain boundary proof while conversion bakes transforms."""
	body = _valid_body().replace(
		'<g><path d="M0 0H10V10Z" fill="#00aa00"/></g>',
		'<g transform="translate(1 0)"><rect x="0" y="0" width="8" height="8" fill="#00aa00"/></g>',
	)
	source = tmp_path / "shapes.svg"
	first = tmp_path / "first.svg"
	second = tmp_path / "second.svg"
	source.write_text(_svg(body), encoding="utf-8")
	result = normalize_svg_v3.normalize_svg_file(source, first, padding=0.0)
	assert result.normalized, result.rejection
	root = lxml.etree.parse(str(first)).getroot()
	assert [element.get("id") for element in root.iter("{%s}rect" % "http://www.w3.org/2000/svg")] == ["anchor_liquid_bounds"]
	assert "normalizer-boundary-token" not in first.read_text(encoding="utf-8")
	second_result = normalize_svg_v3.normalize_svg_file(first, second, padding=0.0)
	assert second_result.normalized, second_result.rejection
	assert first.read_bytes() == second.read_bytes()


def test_compiler_resolves_inherited_paint_without_recoloring_fixed_layers(tmp_path: Path):
	"""Generated paint lives inside material layers even when source paint is inherited."""
	body = _valid_body().replace('fill="#00aa00"', '').replace(
		'<g><path d="M0 0H10V10Z" /></g>',
		'<g fill="#123456"><path d="M0 0H10V10Z" style="fill:#654321"/></g>',
	)
	source = tmp_path / "inherited.svg"
	output = tmp_path / "out.svg"
	source.write_text(_svg(body).replace('data-vlab-rendering="material"', 'data-vlab-rendering="material" fill="#abcdef"'), encoding="utf-8")
	entry = gen_liquid_regions.compile_material_svg(source, output, "inherited")
	compiled = output.read_text(encoding="utf-8")
	paint = entry["paints"][0]["paint_handle"]
	assert f"var(--{paint}, #654321)" in compiled
	assert 'fill="#abcdef"' in compiled and 'fill="#111111"' in compiled


def test_compiler_uses_root_inherited_fallback_and_keeps_none_channels(tmp_path: Path):
	"""The root fallback is copied to the semantic layer and stroke none remains none."""
	body = _valid_body().replace('fill="#00aa00"', '')
	source = tmp_path / "root_inherited.svg"
	output = tmp_path / "out.svg"
	source.write_text(_svg(body).replace('data-vlab-rendering="material"', 'data-vlab-rendering="material" fill="#abcdef"'), encoding="utf-8")
	entry = gen_liquid_regions.compile_material_svg(source, output, "root_inherited")
	compiled = output.read_text(encoding="utf-8")
	paint = entry["paints"][0]["paint_handle"]
	assert f"var(--{paint}, #abcdef)" in compiled
	assert 'stroke="none"' not in compiled


def test_compiler_rejects_generated_id_collision_before_mutating_source_tree(tmp_path: Path, monkeypatch):
	"""Opaque output IDs are checked against every source ID, not only reserved prefixes."""
	source = tmp_path / "sample.svg"
	source.write_text(_svg(_valid_body()), encoding="utf-8")
	monkeypatch.setattr(gen_liquid_regions, "_opaque_handle", lambda *_args: "anchor_liquid_clip")
	with pytest.raises(ValueError, match="handle collision with SVG id"):
		gen_liquid_regions.compile_material_svg(source, tmp_path / "out.svg", "sample")


def test_compiler_rejects_paint_handle_collision_before_writing(tmp_path: Path, monkeypatch):
	"""Paint identifiers share one namespace with level and element identifiers."""
	source = tmp_path / "sample.svg"
	output = tmp_path / "out.svg"
	source.write_text(_svg(_valid_body()), encoding="utf-8")
	def colliding_handle(_asset: str, purpose: str, ordinal: int) -> str:
		return "shared" if purpose == "paint" else f"{purpose}_{ordinal}"
	monkeypatch.setattr(gen_liquid_regions, "_opaque_handle", colliding_handle)
	with pytest.raises(ValueError, match="handle collision"):
		gen_liquid_regions.compile_material_svg(source, output, "sample")
	assert not output.exists()


def test_tree_publication_removes_stale_material_outputs_and_preserves_previous_tree_on_failure(tmp_path: Path):
	"""Staged publication is exact and a failed replacement leaves prior artifacts intact."""
	assets = tmp_path / "assets"
	source = assets / "equipment" / "variable_volume" / "sample.svg"
	source.parent.mkdir(parents=True)
	source.write_text(_svg(_valid_body()), encoding="utf-8")
	generated = tmp_path / "generated"
	gen_liquid_regions.compile_material_tree(assets, generated)
	stale = generated / "material_svg" / "equipment" / "variable_volume" / "stale.svg"
	stale.parent.mkdir(parents=True, exist_ok=True)
	stale.write_text("stale", encoding="utf-8")
	gen_liquid_regions.compile_material_tree(assets, generated)
	assert not stale.exists()
	previous_svg = (
		generated / "material_svg" / "equipment" / "variable_volume" / "sample.svg"
	).read_bytes()
	previous_manifest = (generated / "liquid_regions.json").read_bytes()
	source.write_text(_svg(_valid_body().replace('data-vlab-layer-kind="material"', 'data-vlab-layer-kind="material" clip-path="url(#anchor_liquid_clip)"', 1)), encoding="utf-8")
	with pytest.raises(MaterialSvgValidationError):
		gen_liquid_regions.compile_material_tree(assets, generated)
	assert (
		generated / "material_svg" / "equipment" / "variable_volume" / "sample.svg"
	).read_bytes() == previous_svg
	assert (generated / "liquid_regions.json").read_bytes() == previous_manifest


def test_normalizer_rejects_selector_driven_paint_but_accepts_inert_class(tmp_path: Path):
	"""Classes alone remain valid; stylesheet paint reaches the normalizer loudly."""
	inert = tmp_path / "inert.svg"
	inert.write_text(_svg(_valid_body().replace('fill="#00aa00"', 'class="liquid"')), encoding="utf-8")
	inert_result = normalize_svg_v3.normalize_svg_file(inert, tmp_path / "inert_out.svg", padding=0.0)
	assert inert_result.normalized, inert_result.rejection
	styled = tmp_path / "styled.svg"
	styled.write_text(_svg('<style>.liquid { display: none; }</style>' + _valid_body().replace('fill="#00aa00"', 'class="liquid"')), encoding="utf-8")
	styled_result = normalize_svg_v3.normalize_svg_file(styled, tmp_path / "styled_out.svg", padding=0.0)
	assert not styled_result.normalized and styled_result.rejection.code == "MATERIAL_SEMANTIC_INVALID"
