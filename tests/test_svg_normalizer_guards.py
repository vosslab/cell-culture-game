"""Tests for the focused SVG normalizer modules."""

import pathlib
import lxml.etree
import pytest
import tools.svg_normalizer.model
import tools.svg_normalizer.workflow

SVG_NS = tools.svg_normalizer.model.SVG_NS


#============================================
def _write_svg(path: pathlib.Path, body: str) -> None:
	"""Write a minimal SVG wrapper around body to path."""
	path.write_text(
		f'<svg xmlns="{SVG_NS}" viewBox="0 0 100 100">\n{body}\n</svg>\n',
		encoding="utf-8",
	)


#============================================
def _write_raw_svg(path: pathlib.Path, raw: str) -> None:
	"""Write raw SVG text (no wrapper) to path."""
	path.write_text(raw, encoding="utf-8")



#============================================
# Always-reject detector tests: script/handler, animation, DOCTYPE/entity, foreignObject
#============================================

def test_reject_script_element(tmp_path: pathlib.Path) -> None:
	"""A file containing a <script> element is rejected with SCRIPT_OR_HANDLER."""
	svg_in = tmp_path / "script.svg"
	svg_out = tmp_path / "script.out.svg"
	_write_svg(svg_in, '<rect x="10" y="10" width="80" height="80" fill="#000"/>'
		'<script>alert(1)</script>')
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert not result.normalized
	assert result.rejection.code == "SCRIPT_OR_HANDLER"
	assert not result.output_written
	assert not svg_out.exists()


def test_reject_onclick_handler(tmp_path: pathlib.Path) -> None:
	"""A file with an on* event handler attribute is rejected with SCRIPT_OR_HANDLER."""
	svg_in = tmp_path / "onclick.svg"
	svg_out = tmp_path / "onclick.out.svg"
	_write_svg(svg_in, '<rect x="10" y="10" width="80" height="80" fill="#000" onclick="evil()"/>')
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert not result.normalized
	assert result.rejection.code == "SCRIPT_OR_HANDLER"
	assert not result.output_written


def test_reject_animation_animate(tmp_path: pathlib.Path) -> None:
	"""A file containing an <animate> element is rejected with ANIMATION_UNSUPPORTED."""
	svg_in = tmp_path / "animate.svg"
	svg_out = tmp_path / "animate.out.svg"
	_write_svg(svg_in, '<rect x="10" y="10" width="80" height="80" fill="#000">'
		'<animate attributeName="x" from="10" to="50" dur="1s"/>'
		'</rect>')
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert not result.normalized
	assert result.rejection.code == "ANIMATION_UNSUPPORTED"
	assert not result.output_written


def test_reject_animation_animate_transform(tmp_path: pathlib.Path) -> None:
	"""A file containing an <animateTransform> element is rejected with ANIMATION_UNSUPPORTED."""
	svg_in = tmp_path / "animateTransform.svg"
	svg_out = tmp_path / "animateTransform.out.svg"
	_write_svg(svg_in, '<rect x="10" y="10" width="80" height="80" fill="#000">'
		'<animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="1s"/>'
		'</rect>')
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert not result.normalized
	assert result.rejection.code == "ANIMATION_UNSUPPORTED"


def test_reject_doctype_declaration(tmp_path: pathlib.Path) -> None:
	"""A file with a DOCTYPE declaration is rejected with DOCTYPE_OR_ENTITY."""
	svg_in = tmp_path / "doctype.svg"
	svg_out = tmp_path / "doctype.out.svg"
	# Write raw SVG with a DOCTYPE declaration; _write_raw_svg bypasses the wrapper.
	_write_raw_svg(svg_in,
		'<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" '
		'"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">'
		'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
		'<rect x="10" y="10" width="80" height="80" fill="#000"/>'
		'</svg>')
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert not result.normalized
	assert result.rejection.code == "DOCTYPE_OR_ENTITY"
	assert not result.output_written
	assert not svg_out.exists()


def test_reject_foreignobject(tmp_path: pathlib.Path) -> None:
	"""A file containing a <foreignObject> element is rejected with FOREIGNOBJECT_UNSUPPORTED."""
	svg_in = tmp_path / "foreignobj.svg"
	svg_out = tmp_path / "foreignobj.out.svg"
	_write_svg(svg_in, '<rect x="10" y="10" width="80" height="80" fill="#000"/>'
		'<foreignObject x="0" y="0" width="100" height="100">'
		'<div xmlns="http://www.w3.org/1999/xhtml">hello</div>'
		'</foreignObject>')
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert not result.normalized
	assert result.rejection.code == "FOREIGNOBJECT_UNSUPPORTED"
	assert not result.output_written


#============================================
# Full reject set: use/symbol, filter, mask, marker, image,
# external href, clipPath, geometry-<style>, unparseable-<style>, pattern
#============================================

# Each parametrized case: (fixture-id, svg-body, expected-reason-code).
# Behavioral: feed the body through the gate, assert it rejects with the code
# and writes no output.
_REJECT_CASES = [
	(
		"use_element",
		'<defs><rect id="r" x="0" y="0" width="10" height="10"/></defs>'
		'<use href="#r" x="20" y="20"/>',
		"USE_OR_SYMBOL_UNSUPPORTED",
	),
	(
		"symbol_element",
		'<symbol id="s"><rect x="0" y="0" width="10" height="10"/></symbol>'
		'<rect x="0" y="0" width="10" height="10" fill="#000"/>',
		"USE_OR_SYMBOL_UNSUPPORTED",
	),
	(
		"filter_element",
		'<defs><filter id="f"><feGaussianBlur stdDeviation="2"/></filter></defs>'
		'<rect x="0" y="0" width="10" height="10" fill="#000"/>',
		"FILTER_UNSUPPORTED",
	),
	(
		"filter_reference",
		'<rect x="0" y="0" width="10" height="10" fill="#000" filter="url(#f)"/>',
		"FILTER_UNSUPPORTED",
	),
	(
		"mask_element",
		'<defs><mask id="m"><rect x="0" y="0" width="10" height="10" fill="#fff"/></mask></defs>'
		'<rect x="0" y="0" width="10" height="10" fill="#000"/>',
		"MASK_UNSUPPORTED",
	),
	(
		"marker_element",
		'<defs><marker id="mk"><path d="M 0 0 L 5 5 z"/></marker></defs>'
		'<path d="M 0 0 L 10 0" stroke="#000" marker-end="url(#mk)"/>',
		"MARKER_UNSUPPORTED",
	),
	(
		"embedded_raster_image",
		'<image x="0" y="0" width="10" height="10" '
		'href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUg=="/>',
		"EMBEDDED_RASTER_UNSUPPORTED",
	),
	(
		"external_href_image",
		'<image x="0" y="0" width="10" height="10" href="https://example.com/x.png"/>',
		"EXTERNAL_RESOURCE_UNSUPPORTED",
	),
	(
		"clippath_complex_multi_child",
		'<defs><clipPath id="c"><rect x="0" y="0" width="10" height="10"/>'
		'<rect x="20" y="20" width="10" height="10"/></clipPath></defs>'
		'<rect x="0" y="0" width="40" height="40" fill="#000" clip-path="url(#c)"/>',
		"CLIPPATH_UNSUPPORTED_COMPLEX",
	),
	(
		"style_geometry_rule",
		'<style>rect { fill: red; stroke-width: 4px; }</style>'
		'<rect x="0" y="0" width="10" height="10"/>',
		"STYLE_GEOMETRY_UNSUPPORTED",
	),
	(
		"style_unparseable",
		'<style>}}}</style>'
		'<rect x="0" y="0" width="10" height="10" fill="#000"/>',
		"STYLE_UNPARSEABLE",
	),
	(
		"pattern_with_child_geometry",
		'<defs><pattern id="p" width="4" height="4">'
		'<rect x="0" y="0" width="2" height="2"/></pattern></defs>'
		'<rect x="0" y="0" width="10" height="10" fill="#000"/>',
		"PATTERN_UNSUPPORTED",
	),
]


@pytest.mark.parametrize(
	"fixture_id,svg_body,expected_code",
	_REJECT_CASES,
	ids=[c[0] for c in _REJECT_CASES],
)
def test_reject_set(
	tmp_path: pathlib.Path,
	fixture_id: str,
	svg_body: str,
	expected_code: str,
) -> None:
	"""Each unsupported feature rejects with its declared reason code.

	Behavioral: the gate refuses the file with the right code and writes no
	output (the rejection contract: no output, input untouched).
	"""
	svg_in = tmp_path / f"{fixture_id}.svg"
	svg_out = tmp_path / f"{fixture_id}.out.svg"
	_write_svg(svg_in, svg_body)
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert not result.normalized, f"{fixture_id}: expected rejection, got normalized"
	assert result.rejection.code == expected_code, (
		f"{fixture_id}: expected {expected_code}, got {result.rejection.code}"
	)
	assert not svg_out.exists(), f"{fixture_id}: output written despite rejection"


def test_style_paint_only_preserved(tmp_path: pathlib.Path) -> None:
	"""A <style> block with paint-only rules (no geometry props) normalizes.

	Per the contract, paint/color rules in <style> may remain; only geometry-
	affecting rules trigger STYLE_GEOMETRY_UNSUPPORTED. The block must survive
	in the output.
	"""
	svg_in = tmp_path / "paint_style.svg"
	svg_out = tmp_path / "paint_style.out.svg"
	_write_svg(
		svg_in,
		'<style>.a { color: red; }</style>'
		'<rect x="0" y="0" width="10" height="10" fill="#000"/>',
	)
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	content = svg_out.read_text(encoding="utf-8")
	assert "<style" in content, "paint-only <style> block was dropped"


def test_paint_only_pattern_preserved(tmp_path: pathlib.Path) -> None:
	"""A paint-only pattern (no child geometry, no transform) normalizes and survives.

	The visible geometry references the pattern by url(#); the pattern itself has
	no drawable child, so it is preserved (not rejected).
	"""
	svg_in = tmp_path / "paint_pattern.svg"
	svg_out = tmp_path / "paint_pattern.out.svg"
	_write_svg(
		svg_in,
		'<defs><pattern id="p" width="4" height="4"/></defs>'
		'<rect x="0" y="0" width="10" height="10" fill="url(#p)"/>',
	)
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"


#============================================
# F8 -- rewrite url(#id) inside <style> on ASCII id rename
#============================================

def test_f8_style_url_ref_rewritten_on_rename(tmp_path: pathlib.Path) -> None:
	"""A non-ASCII id referenced via url(#) inside <style> is renamed consistently.

	The gradient id contains a non-ASCII character; make_ascii_clean renames it
	and F8 must rewrite the url(#oldid) inside the <style> text to the new id so
	the reference still resolves (S1 would otherwise reject the file).
	"""
	# Use a non-ASCII id (accented e, U+00E9) for the gradient and reference it
	# from <style>. Built via chr() so this source file stays pure ASCII.
	bad_id = "gr" + chr(0x00E9) + "f"
	svg_in = tmp_path / "f8.svg"
	svg_out = tmp_path / "f8.out.svg"
	_write_raw_svg(
		svg_in,
		f'<svg xmlns="{SVG_NS}" viewBox="0 0 100 100">'
		f'<style>.dot {{ color: blue; }} /* ref: url(#{bad_id}) */</style>'
		f'<defs><linearGradient id="{bad_id}">'
		f'<stop offset="0" stop-color="#000"/></linearGradient></defs>'
		f'<path fill="url(#{bad_id})" d="M 5 5 h 10 v 10 z"/>'
		f'</svg>',
	)
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=2.0)
	# The file must normalize: the rename keeps both the attribute ref and the
	# <style> ref pointing at the renamed gradient id (no dangling ref).
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	content = svg_out.read_text(encoding="utf-8")
	# The non-ASCII id must be gone from the output entirely.
	assert bad_id not in content, "non-ASCII id survived in output"
	# The <style> url(#) and the renamed gradient id must agree: find the new id
	# from the gradient element and confirm the style references it.
	root = lxml.etree.parse(str(svg_out)).getroot()
	grad = root.find(f".//{{{SVG_NS}}}linearGradient")
	assert grad is not None
	new_id = grad.get("id")
	style_elem = root.find(f".//{{{SVG_NS}}}style")
	assert style_elem is not None
	assert f"url(#{new_id})" in (style_elem.text or ""), (
		"F8 did not rewrite the url(#) reference inside <style>"
	)


#============================================
# S1 -- reference-integrity hard gate
#============================================

def test_s1_dangling_url_ref_rejected(tmp_path: pathlib.Path) -> None:
	"""A url(#id) paint reference with no matching id rejects with UNRESOLVED_REFERENCE."""
	svg_in = tmp_path / "dangling.svg"
	svg_out = tmp_path / "dangling.out.svg"
	# fill references #nope which is never defined.
	_write_svg(svg_in, '<rect x="0" y="0" width="10" height="10" fill="url(#nope)"/>')
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert not result.normalized
	assert result.rejection.code == "UNRESOLVED_REFERENCE"
	assert not svg_out.exists()


def test_s1_resolved_ref_normalizes(tmp_path: pathlib.Path) -> None:
	"""A url(#id) reference to a defined gradient passes the S1 gate."""
	svg_in = tmp_path / "resolved.svg"
	svg_out = tmp_path / "resolved.out.svg"
	_write_svg(
		svg_in,
		'<defs><linearGradient id="ok"><stop offset="0" stop-color="#000"/></linearGradient></defs>'
		'<rect x="0" y="0" width="10" height="10" fill="url(#ok)"/>',
	)
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"


#============================================
# B1 -- editor-cruft removal (positive allowlist)
#============================================

def test_b1_cruft_removed_attribution_preserved(tmp_path: pathlib.Path) -> None:
	"""B1 removes editor cruft while dc/cc/rdf attribution survives.

	A fixture where editor cruft and attribution coexist proves both halves of
	the B1 allowlist: cruft gone AND attribution intact.
	"""
	svg_in = tmp_path / "cruft.svg"
	svg_out = tmp_path / "cruft.out.svg"
	_write_raw_svg(
		svg_in,
		'<svg xmlns="http://www.w3.org/2000/svg"'
		' xmlns:dc="http://purl.org/dc/elements/1.1/"'
		' xmlns:cc="http://creativecommons.org/ns#"'
		' xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"'
		' xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.0.dtd"'
		' xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"'
		' viewBox="0 0 100 100">'
		'<sodipodi:namedview id="nv" inkscape:zoom="2"/>'
		'<metadata><rdf:RDF><cc:Work rdf:about="">'
		'<dc:creator><cc:Agent><dc:title>Test Author</dc:title></cc:Agent></dc:creator>'
		'</cc:Work></rdf:RDF></metadata>'
		'<rect x="10" y="10" width="80" height="80" fill="#000" inkscape:label="bg"/>'
		'</svg>',
	)
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	content = svg_out.read_text(encoding="utf-8")
	# Editor cruft gone: no named-view element or editor-prefixed attribute.
	assert "namedview" not in content, "sodipodi:namedview cruft survived"
	assert "inkscape:zoom" not in content, "editor zoom attribute survived"
	assert "inkscape:label" not in content, "editor label attribute survived"
	# Attribution intact: dc/cc/rdf metadata preserved.
	assert "dc:creator" in content, "dc:creator attribution lost"
	assert "cc:Work" in content, "cc:Work attribution lost"
	assert "Test Author" in content, "attribution text lost"


def test_b1_preserves_render_attrs_and_ids(tmp_path: pathlib.Path) -> None:
	"""B1 must not touch SVG render attributes or ids while removing cruft."""
	svg_in = tmp_path / "preserve.svg"
	svg_out = tmp_path / "preserve.out.svg"
	_write_raw_svg(
		svg_in,
		'<svg xmlns="http://www.w3.org/2000/svg"'
		' xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"'
		' viewBox="0 0 100 100">'
		'<rect id="keepme" x="10" y="10" width="80" height="80" fill="#abc"'
		' inkscape:label="drop"/>'
		'</svg>',
	)
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	root = lxml.etree.parse(str(svg_out)).getroot()
	kept = root.find(f".//{{{SVG_NS}}}path[@id='keepme']")
	assert kept is not None, "id and converted geometry must survive cruft removal"
	assert kept.get("fill") == "#abc", "render attribute fill must survive"


