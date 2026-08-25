"""
Pytest harness for tools/normalize_svg_v3.py.

Covers:
  - Inline bbox assertions: relative and absolute path commands, arc extrema,
    rect/circle/line elements, clip-path passthrough, rejection cases.
  - viewBox assertions after normalization (padding expands dimensions correctly).
  - Direct unit tests for arc_extrema and path_bbox_from_segments helpers.
  - UNSUPPORTED_UNIT rejection for required size attrs with non-user units.
  - Transform flattening: invariant checks and viewBox correctness.
  - Shape-to-path conversion: rect, circle, ellipse, line, polyline, polygon.
  - Full reject set: use/symbol, filter, mask, marker, image, clipPath, style,
    pattern; reference-integrity gate; editor-cruft removal.
  - Simple-clipPath flattening and floor-shadow removal.
"""

# Standard Library
import os
import pathlib
import re
import sys

import lxml.etree
import pytest

# Add tools/ to sys.path so normalize_svg_v3 can be imported directly.
_TOOLS_DIR = os.path.join(os.path.dirname(__file__), "..", "tools")
sys.path.insert(0, _TOOLS_DIR)

import normalize_svg_v3

SVG_NS = normalize_svg_v3.SVG_NS


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
# Inline bbox tests: relative path commands and viewBox assertions
#============================================

def test_relative_hv_commands_bbox(tmp_path) -> None:
	"""Relative h/v commands produce the same bbox as the absolute equivalent.

	A path using relative h (horizontal) and v (vertical) commands describing
	a 20x30 rectangle must normalize to the correct bbox dimensions, confirming
	that parse_path_to_absolute handles the relative-to-absolute conversion.
	"""
	svg_in = tmp_path / "rel_hv.svg"
	svg_out = tmp_path / "rel_hv.out.svg"
	# Mixed absolute start + relative h/v: draws a 20-wide, 30-tall rect at (10,10).
	_write_svg(svg_in, '<path d="M 10 10 h 20 v 30 h -20 z" fill="#000"/>')
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	bb = result.bbox
	# The rect must be exactly 20 wide and 30 tall.
	assert abs(bb.max_x - bb.min_x - 20.0) < 0.01
	assert abs(bb.max_y - bb.min_y - 30.0) < 0.01


def test_relative_l_commands_bbox(tmp_path) -> None:
	"""Relative l (lineto) command produces the same bbox as absolute L.

	A path using 'm' + relative 'l' commands to draw a triangle must have a
	bbox matching the triangle vertices, confirming relative lineto conversion.
	"""
	svg_in = tmp_path / "rel_l.svg"
	svg_out = tmp_path / "rel_l.out.svg"
	# Triangle: start (10,10), relative l 40,0 (to 50,10), l -20,30 (to 30,40), z.
	_write_svg(svg_in, '<path d="M 10 10 l 40 0 l -20 30 z" fill="#000"/>')
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	bb = result.bbox
	# width = 40, height = 30.
	assert abs(bb.max_x - bb.min_x - 40.0) < 0.01
	assert abs(bb.max_y - bb.min_y - 30.0) < 0.01


def test_relative_arc_command_captures_bulge(tmp_path) -> None:
	"""Relative arc command 'a' produces the same bbox as absolute 'A'.

	A relative arc from (0,0) sweeping 100 units right (same geometry as the
	absolute semicircle test) must include the arc bulge near y=50 in the bbox.
	"""
	svg_in = tmp_path / "rel_arc.svg"
	svg_out = tmp_path / "rel_arc.out.svg"
	# Relative arc: same semicircle geometry as test_path_bbox_contains_arc_bulge
	# but using lowercase 'a' (relative endpoint).
	_write_svg(svg_in, '<path d="M 0 0 a 50 50 0 0 0 100 0" fill="#000"/>')
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	bb = result.bbox
	# The semicircle bulges to y~50; an endpoint-only bbox would give max_y=0.
	assert bb.max_y > 40.0


def test_viewbox_includes_padding(tmp_path) -> None:
	"""The output viewBox starts at '0 0' and dimensions include the padding on each side.

	A 10x10 rect normalized with padding=2 must produce viewBox '0 0 14 14':
	content is 10 user units wide and tall, plus 2 units of padding on each side.
	"""
	svg_in = tmp_path / "vb.svg"
	svg_out = tmp_path / "vb.out.svg"
	_write_svg(svg_in, '<rect x="0" y="0" width="10" height="10" fill="#000"/>')
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	assert result.view_box is not None
	# viewBox must be normalized to origin: starts with "0 0 ".
	assert result.view_box.startswith("0 0 "), (
		f"expected viewBox starting '0 0 ', got {result.view_box!r}"
	)
	# Total width and height must each be 10 (content) + 2*2 (padding) = 14.
	parts = result.view_box.split()
	assert len(parts) == 4
	width = float(parts[2])
	height = float(parts[3])
	assert abs(width - 14.0) < 0.01, f"expected width 14.0, got {width}"
	assert abs(height - 14.0) < 0.01, f"expected height 14.0, got {height}"


def test_viewbox_zero_padding_tight_to_geometry(tmp_path) -> None:
	"""With padding=0 the output viewBox dimensions match the geometry exactly.

	A 50x20 rect normalized with no padding must produce a viewBox whose width
	is 50 and height is 20 (no extra margin).
	"""
	svg_in = tmp_path / "vb_tight.svg"
	svg_out = tmp_path / "vb_tight.out.svg"
	_write_svg(svg_in, '<rect x="5" y="5" width="50" height="20" fill="#000"/>')
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	assert result.view_box is not None
	parts = result.view_box.split()
	assert len(parts) == 4
	width = float(parts[2])
	height = float(parts[3])
	assert abs(width - 50.0) < 0.01, f"expected width 50.0, got {width}"
	assert abs(height - 20.0) < 0.01, f"expected height 20.0, got {height}"


#============================================
# UNSUPPORTED_UNIT rejection tests (fix a)
#============================================

def test_rect_percent_width_rejected(tmp_path) -> None:
	"""A rect with width='50%' must be rejected with UNSUPPORTED_UNIT.

	Percentage is not a user unit; silently stripping it would produce a phantom
	bbox (50.0 user units) instead of a reliable geometry measurement.
	"""
	svg_in = tmp_path / "rect_pct.svg"
	svg_out = tmp_path / "rect_pct.out.svg"
	_write_svg(svg_in, '<rect x="0" y="0" width="50%" height="40" fill="#000" />')
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert not result.normalized
	assert result.rejection.code == "UNSUPPORTED_UNIT"
	assert not svg_out.exists()


def test_rect_px_width_normalizes(tmp_path) -> None:
	"""A rect with width='50px' must normalize: px is a user-unit alias (1px == 1uu)."""
	svg_in = tmp_path / "rect_px.svg"
	svg_out = tmp_path / "rect_px.out.svg"
	_write_svg(svg_in, '<rect x="0" y="0" width="50px" height="40px" fill="#000" />')
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	assert result.bbox is not None
	# The drawn bbox should be 50 wide and 40 tall.
	assert abs(result.bbox.max_x - result.bbox.min_x - 50.0) < 0.1
	assert abs(result.bbox.max_y - result.bbox.min_y - 40.0) < 0.1


#============================================
# Direct arc_extrema unit tests
#============================================

def test_arc_extrema_semicircle_downward_bulge() -> None:
	"""Semicircle sweep=0 from (0,0) to (100,0) must capture y=50 bulge.

	This is the canonical arc-undershoot regression: endpoint-only code sees
	ys=[0,0] (height=0); fixed arc_extrema returns max_y near 50.
	"""
	xs, ys = normalize_svg_v3.arc_extrema(0.0, 0.0, 50.0, 50.0, 0.0, 0, 0, 100.0, 0.0)
	max_y = max(ys)
	# The bulge at y=50 must be in the returned candidates.
	assert max_y > 40.0
	assert abs(max_y - 50.0) < 1e-6


def test_arc_extrema_semicircle_upward_bulge() -> None:
	"""Semicircle sweep=1 (CW) from (0,0) to (100,0) bulges upward to y=-50."""
	xs, ys = normalize_svg_v3.arc_extrema(0.0, 0.0, 50.0, 50.0, 0.0, 0, 1, 100.0, 0.0)
	min_y = min(ys)
	# CW arc goes to y=-50 (upward in SVG coordinates).
	assert min_y < -40.0
	assert abs(min_y - (-50.0)) < 1e-6


def test_arc_extrema_degenerate_zero_radius() -> None:
	"""Zero radius arc returns only the two endpoint coordinates."""
	xs, ys = normalize_svg_v3.arc_extrema(10.0, 20.0, 0.0, 0.0, 0.0, 0, 1, 30.0, 40.0)
	# Degenerate: only the two endpoints; no extra extrema candidates.
	assert min(xs) >= 10.0
	assert max(xs) <= 30.0
	assert min(ys) >= 20.0
	assert max(ys) <= 40.0


def test_arc_extrema_rotated_bbox_wider_than_endpoints() -> None:
	"""Rotated arc (phi_deg=45) must capture extrema wider than endpoints alone.

	Arc from (0,0) to (0,100) with rx=ry=50 and phi_deg=45.  The rotation
	forces a bulge in the x direction that a pure-endpoint bbox would miss.
	"""
	xs, ys = normalize_svg_v3.arc_extrema(0.0, 0.0, 50.0, 50.0, 45.0, 0, 1, 0.0, 100.0)
	bbox_width = max(xs) - min(xs)
	# A rotated half-ellipse must be wider than its zero-width endpoint span.
	assert bbox_width > 30.0


#============================================
# path_bbox_from_segments round-trip
#============================================

def test_path_bbox_rectangle_absolute() -> None:
	"""Parse a simple absolute-command rectangle path and verify bbox round-trips."""
	d = "M 10 20 L 40 20 L 40 60 L 10 60 Z"
	segments = normalize_svg_v3.parse_path_to_absolute(d)
	bbox = normalize_svg_v3.path_bbox_from_segments(segments)
	assert bbox is not None
	assert abs(bbox.min_x - 10.0) < 1e-6
	assert abs(bbox.min_y - 20.0) < 1e-6
	assert abs(bbox.max_x - 40.0) < 1e-6
	assert abs(bbox.max_y - 60.0) < 1e-6


def test_path_bbox_contains_arc_bulge() -> None:
	"""path_bbox_from_segments for a path with an A command includes the arc bulge."""
	# Semicircle: arc goes from (0,0) to (100,0) sweeping downward to y=50.
	d = "M 0 0 A 50 50 0 0 0 100 0"
	segments = normalize_svg_v3.parse_path_to_absolute(d)
	bbox = normalize_svg_v3.path_bbox_from_segments(segments)
	assert bbox is not None
	# The bbox must extend to y=50, not stay at y=0 (the endpoint-only failure).
	assert bbox.max_y > 40.0


#============================================
# NormalizeResult contract
#============================================

def test_normalize_result_normalized_property(tmp_path) -> None:
	"""NormalizeResult.normalized is True when rejection is None."""
	svg_in = tmp_path / "simple.svg"
	svg_out = tmp_path / "simple.out.svg"
	_write_svg(svg_in, '<rect x="0" y="0" width="10" height="10" fill="#000" />')

	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert result.normalized
	assert result.rejection is None
	assert result.output_written


def test_rect_missing_width_yields_empty_geometry(tmp_path) -> None:
	"""A rect with no width attribute must not contribute a phantom zero-size bbox.

	When the only shape in an SVG is a rect missing its required width attribute,
	element_bbox must return None for it, so compute_bbox finds no drawable geometry
	and normalize_svg_file returns an EMPTY_GEOMETRY rejection.
	"""
	svg_in = tmp_path / "rect_no_width.svg"
	svg_out = tmp_path / "rect_no_width.out.svg"
	# rect missing width -- required attribute absent.
	_write_svg(svg_in, '<rect y="10" height="20" fill="#000" />')
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert not result.normalized
	assert result.rejection.code == "EMPTY_GEOMETRY"


def test_normalize_result_rejection_no_output(tmp_path) -> None:
	"""Rejected file leaves no output and output_written is False."""
	svg_in = tmp_path / "bad.svg"
	svg_out = tmp_path / "bad.out.svg"
	svg_in.write_text(
		'<svg xmlns="http://www.w3.org/2000/svg"><rect x="1"',
		encoding="utf-8",
	)

	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert not result.normalized
	assert not result.output_written
	assert not svg_out.exists()


#============================================
# Transform flattening unit tests
#============================================

def test_transform_arc_identity_preserves_radii() -> None:
	"""transformArc under the identity matrix leaves rx, ry, rotation, sweep unchanged."""
	rx, ry, rot, _large, sweep = normalize_svg_v3.transform_arc(
		0.0, 0.0, (50.0, 30.0, 0.0, 0.0, 1.0, 100.0, 0.0), normalize_svg_v3.IDENTITY_MATRIX
	)
	assert abs(rx - 50.0) < 1e-6
	assert abs(ry - 30.0) < 1e-6
	assert abs(rot) < 1e-6
	assert sweep == 1.0


def test_transform_arc_uniform_scale_doubles_radii() -> None:
	"""A uniform scale(2) doubles both arc radii."""
	rx, ry, _rot, _large, _sweep = normalize_svg_v3.transform_arc(
		0.0, 0.0, (50.0, 30.0, 0.0, 0.0, 1.0, 100.0, 0.0), (2.0, 0.0, 0.0, 2.0, 0.0, 0.0)
	)
	assert abs(rx - 100.0) < 1e-6
	assert abs(ry - 60.0) < 1e-6


def test_transform_arc_single_axis_flip_inverts_sweep() -> None:
	"""A horizontal flip (det sign change) toggles the arc sweep flag."""
	_rx, _ry, _rot, _large, sweep = normalize_svg_v3.transform_arc(
		0.0, 0.0, (50.0, 30.0, 0.0, 0.0, 1.0, 100.0, 0.0), (-1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
	)
	# Sweep started at 1; a single-axis mirror flips it to 0.
	assert sweep == 0.0


def test_transform_arc_rotate_keeps_circle_circular() -> None:
	"""A circular arc stays circular (rx == ry) under a pure rotation."""
	rx, ry, _rot, _large, _sweep = normalize_svg_v3.transform_arc(
		0.0, 0.0, (50.0, 50.0, 0.0, 0.0, 1.0, 100.0, 0.0), (0.0, 1.0, -1.0, 0.0, 0.0, 0.0)
	)
	assert abs(rx - ry) < 1e-6
	assert abs(rx - 50.0) < 1e-6


def test_compose_translate_then_scale_point() -> None:
	"""Composing translate(10,10) then scale(2) maps a point through both, in order.

	transform="translate(10,10) scale(2)" applies scale to local coords first,
	then translate, so (5,5) -> (2*5+10, 2*5+10) = (20,20).
	"""
	items = normalize_svg_v3.parse_transform_list("translate(10,10) scale(2)", "/svg")
	matrix = normalize_svg_v3.transforms_multiply(items, "/svg")
	nx, ny = normalize_svg_v3.transform_point(matrix, 5.0, 5.0)
	assert abs(nx - 20.0) < 1e-6
	assert abs(ny - 20.0) < 1e-6


def test_apply_matrix_rotate90_to_path_segments() -> None:
	"""rotate(90) maps a path point (x,y) to (-y,x) after flattening."""
	segments = normalize_svg_v3.parse_path_to_absolute("M 0 0 L 10 0")
	items = normalize_svg_v3.parse_transform_list("rotate(90)", "/svg")
	matrix = normalize_svg_v3.transforms_multiply(items, "/svg")
	flat = normalize_svg_v3.apply_matrix_to_segments(segments, matrix)
	bbox = normalize_svg_v3.path_bbox_from_segments(flat)
	# (10,0) rotates to (0,10); (0,0) stays at origin.
	assert abs(bbox.min_x - 0.0) < 1e-6
	assert abs(bbox.max_x - 0.0) < 1e-6
	assert abs(bbox.max_y - 10.0) < 1e-6


def test_invariant_holds_after_flatten(tmp_path) -> None:
	"""After normalization, no geometry-affecting transform remains on output.

	The canonical-invariant checker (find_geometry_transform_violation) must
	return None for a normalized file whose input carried element + group
	transforms.
	"""
	svg_in = tmp_path / "xform.svg"
	svg_out = tmp_path / "xform.out.svg"
	_write_svg(
		svg_in,
		'<g transform="translate(5,7)">'
		'<rect x="10" y="10" width="20" height="20" transform="scale(2)" fill="#000"/>'
		'</g>',
	)
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	root = normalize_svg_v3.lxml.etree.parse(str(svg_out)).getroot()
	assert normalize_svg_v3.find_geometry_transform_violation(root) is None


def test_gradient_transform_exempt_from_invariant(tmp_path) -> None:
	"""gradientTransform in defs is paint-space and must not trip the invariant."""
	svg_in = tmp_path / "grad.svg"
	svg_out = tmp_path / "grad.out.svg"
	_write_svg(
		svg_in,
		'<defs><linearGradient id="g" gradientTransform="rotate(45)">'
		'<stop offset="0" stop-color="#000"/></linearGradient></defs>'
		'<rect x="0" y="0" width="10" height="10" fill="url(#g)"/>',
	)
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	root = normalize_svg_v3.lxml.etree.parse(str(svg_out)).getroot()
	# gradientTransform must survive and not be flagged as a violation.
	assert normalize_svg_v3.find_geometry_transform_violation(root) is None


def test_stroked_nonuniform_scale_rejected(tmp_path) -> None:
	"""A visible stroke under non-uniform scale is refused (UNSUPPORTED_TRANSFORM)."""
	svg_in = tmp_path / "stroked.svg"
	svg_out = tmp_path / "stroked.out.svg"
	_write_svg(
		svg_in,
		'<path d="M 0 0 L 10 0" transform="scale(2,3)" stroke="#000" stroke-width="1" fill="none"/>',
	)
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert not result.normalized
	assert result.rejection.code == "UNSUPPORTED_TRANSFORM"
	assert not svg_out.exists()


def test_stroked_uniform_scale_rotate_allowed(tmp_path) -> None:
	"""A visible stroke under uniform scale plus rotation flattens without distortion."""
	svg_in = tmp_path / "stroked_ok.svg"
	svg_out = tmp_path / "stroked_ok.out.svg"
	_write_svg(
		svg_in,
		'<path d="M 0 0 L 10 0" transform="rotate(45) scale(2)" stroke="#000" stroke-width="1" fill="none"/>',
	)
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"


def test_non_scaling_stroke_under_scale_rejected(tmp_path) -> None:
	"""vector-effect=non-scaling-stroke under a scaling transform is unresolved -> reject."""
	svg_in = tmp_path / "nss.svg"
	svg_out = tmp_path / "nss.out.svg"
	_write_svg(
		svg_in,
		'<path d="M 0 0 L 10 0" transform="scale(2)" stroke="#000" '
		'vector-effect="non-scaling-stroke"/>',
	)
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert not result.normalized
	assert result.rejection.code == "NONSCALING_STROKE_UNRESOLVED"


#============================================
# Shape->path conversion tests
#
# Primary assertion: each shape normalizes with a bbox that matches the
# declared geometry within tolerance (round-trip correctness).
# Secondary assertion: the output SVG contains only <path> elements for
# shape content (no residual rect/circle/ellipse/line/polyline/polygon).
#============================================

def _output_has_no_raw_shapes(svg_out_path: pathlib.Path) -> bool:
	"""Return True when the output SVG has no unconverted shape elements.

	Checks that rect/circle/ellipse/line/polyline/polygon do not appear in
	the output after normalization (they must all be converted to path).
	"""
	root = normalize_svg_v3.lxml.etree.parse(str(svg_out_path)).getroot()
	shape_tags = {"rect", "circle", "ellipse", "line", "polyline", "polygon"}
	for elem in root.iter():
		if isinstance(elem.tag, str):
			tag = normalize_svg_v3.local_name(elem.tag)
			if tag in shape_tags:
				return False
	return True


def test_shape_to_path_sharp_rect_bbox(tmp_path) -> None:
	"""Sharp rect converts to path; bbox matches declared x/y/width/height."""
	svg_in = tmp_path / "sharp_rect.svg"
	svg_out = tmp_path / "sharp_rect.out.svg"
	_write_svg(svg_in, '<rect x="10" y="20" width="60" height="40" fill="#000"/>')
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	# bbox must match the declared geometry of the rect
	bb = result.bbox
	assert abs(bb.max_x - bb.min_x - 60.0) < 0.01
	assert abs(bb.max_y - bb.min_y - 40.0) < 0.01


def test_shape_to_path_sharp_rect_tag(tmp_path) -> None:
	"""Sharp rect is rewritten as <path> in the normalized output."""
	svg_in = tmp_path / "sharp_rect_tag.svg"
	svg_out = tmp_path / "sharp_rect_tag.out.svg"
	_write_svg(svg_in, '<rect x="10" y="20" width="60" height="40" fill="#000"/>')
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized
	assert _output_has_no_raw_shapes(svg_out)


def test_shape_to_path_rounded_rect_rx_only_bbox(tmp_path) -> None:
	"""Rounded rect (rx only) converts to path; bbox equals outer rectangle.

	rx is specified but ry is absent; per SVG spec ry defaults to rx.
	The arc corners stay within the outer bbox so the path bbox == (x,y,x+w,y+h).
	"""
	svg_in = tmp_path / "rrect_rx.svg"
	svg_out = tmp_path / "rrect_rx.out.svg"
	_write_svg(svg_in, '<rect x="0" y="0" width="60" height="40" rx="10" fill="#000"/>')
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	bb = result.bbox
	assert abs(bb.max_x - bb.min_x - 60.0) < 0.01
	assert abs(bb.max_y - bb.min_y - 40.0) < 0.01


def test_shape_to_path_rounded_rect_rx_and_ry_bbox(tmp_path) -> None:
	"""Rounded rect (rx=8 ry=5) converts to path; bbox equals outer rectangle."""
	svg_in = tmp_path / "rrect_rxry.svg"
	svg_out = tmp_path / "rrect_rxry.out.svg"
	_write_svg(svg_in, '<rect x="10" y="5" width="40" height="30" rx="8" ry="5" fill="#000"/>')
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	bb = result.bbox
	assert abs(bb.max_x - bb.min_x - 40.0) < 0.01
	assert abs(bb.max_y - bb.min_y - 30.0) < 0.01


def test_shape_to_path_rounded_rect_tag(tmp_path) -> None:
	"""Rounded rect is rewritten as <path> with no residual rect element."""
	svg_in = tmp_path / "rrect_tag.svg"
	svg_out = tmp_path / "rrect_tag.out.svg"
	_write_svg(svg_in, '<rect x="0" y="0" width="60" height="40" rx="10" fill="#000"/>')
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized
	assert _output_has_no_raw_shapes(svg_out)


def test_shape_to_path_circle_bbox(tmp_path) -> None:
	"""Circle converts to two-arc path; bbox matches (cx-r, cy-r, cx+r, cy+r)."""
	svg_in = tmp_path / "circle.svg"
	svg_out = tmp_path / "circle.out.svg"
	_write_svg(svg_in, '<circle cx="50" cy="50" r="30" fill="#333"/>')
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	bb = result.bbox
	# circle bbox width and height must both equal 2*r = 60
	assert abs(bb.max_x - bb.min_x - 60.0) < 0.01
	assert abs(bb.max_y - bb.min_y - 60.0) < 0.01


def test_shape_to_path_circle_tag(tmp_path) -> None:
	"""Circle is rewritten as <path> in the normalized output."""
	svg_in = tmp_path / "circle_tag.svg"
	svg_out = tmp_path / "circle_tag.out.svg"
	_write_svg(svg_in, '<circle cx="50" cy="50" r="30" fill="#333"/>')
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized
	assert _output_has_no_raw_shapes(svg_out)


def test_shape_to_path_ellipse_bbox(tmp_path) -> None:
	"""Ellipse converts to two-arc path; bbox matches (cx-rx, cy-ry, cx+rx, cy+ry)."""
	svg_in = tmp_path / "ellipse.svg"
	svg_out = tmp_path / "ellipse.out.svg"
	_write_svg(svg_in, '<ellipse cx="30" cy="40" rx="20" ry="10" fill="#555"/>')
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	bb = result.bbox
	# ellipse bbox: width = 2*rx = 40, height = 2*ry = 20
	assert abs(bb.max_x - bb.min_x - 40.0) < 0.01
	assert abs(bb.max_y - bb.min_y - 20.0) < 0.01


def test_shape_to_path_ellipse_tag(tmp_path) -> None:
	"""Ellipse is rewritten as <path> in the normalized output."""
	svg_in = tmp_path / "ellipse_tag.svg"
	svg_out = tmp_path / "ellipse_tag.out.svg"
	_write_svg(svg_in, '<ellipse cx="30" cy="40" rx="20" ry="10" fill="#555"/>')
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized
	assert _output_has_no_raw_shapes(svg_out)


def test_shape_to_path_line_bbox(tmp_path) -> None:
	"""Line converts to M/L path; bbox includes stroke pad (A3: stroke-width=1 -> pad=2).

	With stroke-width=1 and default miterlimit=4: pad = 1/2 * 4 = 2.
	Geometry spans 75 wide and 50 tall; stroke-padded spans 79 wide and 54 tall.
	"""
	svg_in = tmp_path / "line.svg"
	svg_out = tmp_path / "line.out.svg"
	_write_svg(svg_in, '<line x1="5" y1="10" x2="80" y2="60" stroke="#000" stroke-width="1"/>')
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	bb = result.bbox
	# Geometry width 75 + 2*pad(2) = 79; geometry height 50 + 2*pad(2) = 54.
	assert abs(bb.max_x - bb.min_x - 79.0) < 0.01
	assert abs(bb.max_y - bb.min_y - 54.0) < 0.01


def test_shape_to_path_line_tag(tmp_path) -> None:
	"""Line is rewritten as <path> in the normalized output."""
	svg_in = tmp_path / "line_tag.svg"
	svg_out = tmp_path / "line_tag.out.svg"
	_write_svg(svg_in, '<line x1="5" y1="10" x2="80" y2="60" stroke="#000" stroke-width="1"/>')
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized
	assert _output_has_no_raw_shapes(svg_out)


def test_shape_to_path_polyline_bbox(tmp_path) -> None:
	"""Polyline converts to M/L/L path; bbox includes stroke pad (A3).

	stroke="#000" with no stroke-width -> default stroke-width=1; pad = 1/2*4 = 2.
	Geometry spans 100 wide and 20 tall; stroke-padded spans 104 wide and 24 tall.
	"""
	svg_in = tmp_path / "polyline.svg"
	svg_out = tmp_path / "polyline.out.svg"
	_write_svg(svg_in, '<polyline points="0,0 50,20 100,0" fill="none" stroke="#000"/>')
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	bb = result.bbox
	# Geometry width 100 + 2*pad(2) = 104; geometry height 20 + 2*pad(2) = 24.
	assert abs(bb.max_x - bb.min_x - 104.0) < 0.01
	assert abs(bb.max_y - bb.min_y - 24.0) < 0.01


def test_shape_to_path_polyline_tag(tmp_path) -> None:
	"""Polyline is rewritten as <path> in the normalized output."""
	svg_in = tmp_path / "polyline_tag.svg"
	svg_out = tmp_path / "polyline_tag.out.svg"
	_write_svg(svg_in, '<polyline points="0,0 50,20 100,0" fill="none" stroke="#000"/>')
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized
	assert _output_has_no_raw_shapes(svg_out)


def test_shape_to_path_polygon_bbox(tmp_path) -> None:
	"""Polygon converts to M/L/L/Z path; bbox spans all vertices."""
	svg_in = tmp_path / "polygon.svg"
	svg_out = tmp_path / "polygon.out.svg"
	_write_svg(svg_in, '<polygon points="10,10 90,10 50,80" fill="#222"/>')
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	bb = result.bbox
	# width = 80, height = 70
	assert abs(bb.max_x - bb.min_x - 80.0) < 0.01
	assert abs(bb.max_y - bb.min_y - 70.0) < 0.01


def test_shape_to_path_polygon_tag(tmp_path) -> None:
	"""Polygon is rewritten as <path> in the normalized output."""
	svg_in = tmp_path / "polygon_tag.svg"
	svg_out = tmp_path / "polygon_tag.out.svg"
	_write_svg(svg_in, '<polygon points="10,10 90,10 50,80" fill="#222"/>')
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized
	assert _output_has_no_raw_shapes(svg_out)


def test_shape_to_path_preserves_id_and_paint_ref(tmp_path) -> None:
	"""Shape->path preserves id and a fill url(#) reference on the new <path>.

	The converted <path> must carry the same id and fill paint reference so
	reference integrity (S1) and url(#) rewrite (F8) remain correct. A gradient
	is used (rather than a clip) because a simple clip would be flattened away by
	the url(#)-preservation property is what this test checks.
	"""
	svg_in = tmp_path / "refs.svg"
	svg_out = tmp_path / "refs.out.svg"
	_write_svg(
		svg_in,
		'<defs><linearGradient id="g1"><stop offset="0" stop-color="#000"/></linearGradient></defs>'
		'<circle id="mycirc" cx="50" cy="50" r="30" fill="url(#g1)"/>',
	)
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	root = normalize_svg_v3.lxml.etree.parse(str(svg_out)).getroot()
	# Find the converted path (by id); it must carry the fill paint reference.
	found = root.find(f".//{{{SVG_NS}}}path[@id='mycirc']")
	assert found is not None, "converted path missing id='mycirc'"
	assert found.get("fill") == "url(#g1)", "fill ref not preserved on converted path"


def test_shape_to_path_invariant_still_holds(tmp_path) -> None:
	"""After shape->path the canonical invariant still holds: no geometry transform remains."""
	svg_in = tmp_path / "inv.svg"
	svg_out = tmp_path / "inv.out.svg"
	_write_svg(
		svg_in,
		'<g transform="translate(5,5)">'
		'<circle cx="20" cy="20" r="10" fill="#000"/>'
		'</g>',
	)
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	root = normalize_svg_v3.lxml.etree.parse(str(svg_out)).getroot()
	assert normalize_svg_v3.find_geometry_transform_violation(root) is None


def test_rounded_rect_radii_clamped_to_half_side(tmp_path) -> None:
	"""Rounded rect with rx > width/2 must clamp rx to width/2 (SVG spec).

	A 20x20 rect with rx=20 would produce rx=10 after clamping.  The path bbox
	must still equal (x, y, x+w, y+h); a wrong bbox would indicate the radii
	were not clamped.
	"""
	svg_in = tmp_path / "clamp.svg"
	svg_out = tmp_path / "clamp.out.svg"
	# rx=20 > width/2=10 so rx is clamped to 10; ry defaults to clamped rx=10,
	# then clamped to height/2=10 as well -- effectively a stadium shape.
	_write_svg(svg_in, '<rect x="0" y="0" width="20" height="20" rx="20" fill="#000"/>')
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	bb = result.bbox
	assert abs(bb.max_x - bb.min_x - 20.0) < 0.01
	assert abs(bb.max_y - bb.min_y - 20.0) < 0.01


#============================================
# Stroke pad, text reject, and precision round-trip tests
#============================================

def test_stroke_pad_thick_path_bbox_larger_than_geometry(tmp_path) -> None:
	"""Thick-stroke path: padded bbox must contain the stroke envelope.

	A horizontal path M 10 10 L 90 10 with stroke-width=10 has geometry height 0
	but must produce a padded bbox that contains the stroke envelope
	(stroke_width/2 * max(1,miterlimit) = 5*4 = 20 pad on each side).
	The padded bbox height must be > 0 and significantly larger than the geometry.
	"""
	svg_in = tmp_path / "thick_stroke.svg"
	svg_out = tmp_path / "thick_stroke.out.svg"
	_write_svg(
		svg_in,
		'<path d="M 10 10 L 90 10" stroke="#000" stroke-width="10" fill="none"/>',
	)
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	bb = result.bbox
	geom_height = 0.0  # horizontal line: no geometry height
	# Padded height must be larger than bare geometry by at least stroke_width/2.
	padded_height = bb.max_y - bb.min_y
	assert padded_height > geom_height + 1.0


def test_stroke_pad_miter_join_uses_miterlimit(tmp_path) -> None:
	"""Miter join pad = stroke_width/2 * max(1, miterlimit).

	With stroke-width=4 and stroke-miterlimit=6, pad = 4/2*6 = 12.
	The path geometry M 20 20 L 80 20 (height=0) gets padded by 12 on each side.
	Padded height must be >= 2*12 = 24.
	"""
	svg_in = tmp_path / "miter.svg"
	svg_out = tmp_path / "miter.out.svg"
	_write_svg(
		svg_in,
		'<path d="M 20 20 L 80 20" stroke="#000" stroke-width="4" '
		'stroke-linejoin="miter" stroke-miterlimit="6" fill="none"/>',
	)
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	padded_height = result.bbox.max_y - result.bbox.min_y
	# pad = 4/2*max(1,6) = 12 on each side -> total height >= 24.
	assert padded_height >= 23.9


def test_stroke_pad_round_linecap_open_path(tmp_path) -> None:
	"""Round linecap open path: bbox extends by stroke_width/2 BEYOND the miter pad.

	Path M 30 30 L 70 30 is open (no Z). With stroke-width=8 and round linecap,
	the endpoint extension (stroke_width/2 = 4) is additive on top of the miter
	pad (8/2*max(1,4) = 16), giving pad_final = 20 per side, total height 40.
	"""
	svg_in = tmp_path / "roundcap.svg"
	svg_out = tmp_path / "roundcap.out.svg"
	_write_svg(
		svg_in,
		'<path d="M 30 30 L 70 30" stroke="#000" stroke-width="8" '
		'stroke-linecap="round" fill="none"/>',
	)
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	round_height = result.bbox.max_y - result.bbox.min_y
	# pad = 8/2*max(1,4) + 8/2 = 16 + 4 = 20 per side -> total height = 40.
	assert round_height >= 39.9


def test_stroke_pad_butt_linecap_no_endpoint_extra(tmp_path) -> None:
	"""Butt linecap open path: no endpoint extension beyond the miter pad.

	Path M 30 30 L 70 30 with stroke-width=8 and butt linecap (default):
	pad = 8/2 * max(1, 4) = 16 per side, total height = 32.
	Round/square linecap produces a strictly larger bbox (~stroke_width taller).
	"""
	svg_in = tmp_path / "buttcap.svg"
	svg_out = tmp_path / "buttcap.out.svg"
	_write_svg(
		svg_in,
		'<path d="M 30 30 L 70 30" stroke="#000" stroke-width="8" '
		'stroke-linecap="butt" fill="none"/>',
	)
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	butt_height = result.bbox.max_y - result.bbox.min_y
	# pad = 8/2*max(1,4) = 16 per side -> total height = 32 (no endpoint add).
	assert butt_height >= 31.9
	# Butt must be strictly narrower than round/square by ~stroke_width (8).
	# We assert round_height - butt_height >= stroke_width - epsilon.
	round_svg_in = tmp_path / "roundcap2.svg"
	round_svg_out = tmp_path / "roundcap2.out.svg"
	_write_svg(
		round_svg_in,
		'<path d="M 30 30 L 70 30" stroke="#000" stroke-width="8" '
		'stroke-linecap="round" fill="none"/>',
	)
	round_result = normalize_svg_v3.normalize_svg_file(round_svg_in, round_svg_out, padding=0.0)
	assert round_result.normalized
	round_height = round_result.bbox.max_y - round_result.bbox.min_y
	# round/square adds stroke_width (8) to total height vs butt.
	assert round_height >= butt_height + 8 - 0.1


def test_stroke_none_no_pad(tmp_path) -> None:
	"""stroke=none element must not be padded; bbox equals geometry bbox."""
	svg_in = tmp_path / "nostroke.svg"
	svg_out = tmp_path / "nostroke.out.svg"
	_write_svg(
		svg_in,
		'<rect x="10" y="10" width="80" height="60" fill="#333" stroke="none"/>',
	)
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	bb = result.bbox
	# Geometry only: no stroke pad applied.
	assert abs(bb.max_x - bb.min_x - 80.0) < 0.01
	assert abs(bb.max_y - bb.min_y - 60.0) < 0.01


#============================================
# Text reject tests
#============================================

def test_text_element_rejected(tmp_path) -> None:
	"""An SVG containing a <text> element is rejected with TEXT_UNSUPPORTED.

	v3 cannot compute text glyph geometry. Prose belongs in layout-manager DOM or
	object data; only approved intrinsic markings may be outlined before ingestion.
	"""
	svg_in = tmp_path / "text.svg"
	svg_out = tmp_path / "text.out.svg"
	_write_svg(svg_in, '<rect x="0" y="0" width="100" height="100" fill="#000"/>'
		'<text x="10" y="50">Hello</text>')
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert not result.normalized
	assert result.rejection.code == "TEXT_UNSUPPORTED"
	assert not svg_out.exists()


def test_tspan_element_rejected(tmp_path) -> None:
	"""An SVG with a <tspan> inside <text> is rejected with TEXT_UNSUPPORTED."""
	svg_in = tmp_path / "tspan.svg"
	svg_out = tmp_path / "tspan.out.svg"
	_write_svg(
		svg_in,
		'<text x="10" y="50"><tspan>Hi</tspan></text>',
	)
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert not result.normalized
	assert result.rejection.code == "TEXT_UNSUPPORTED"
	assert not svg_out.exists()


def test_text_rejection_element_location(tmp_path) -> None:
	"""TEXT_UNSUPPORTED rejection includes an XPath-like element location."""
	svg_in = tmp_path / "textloc.svg"
	svg_out = tmp_path / "textloc.out.svg"
	_write_svg(svg_in, '<text x="5" y="20">Label</text>')
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert not result.normalized
	assert result.rejection.code == "TEXT_UNSUPPORTED"
	# The element field should be non-empty for a locatable element.
	assert result.rejection.element != ""


#============================================
# Precision and round-trip determinism tests
#============================================

def test_precision_fmt_precise_leading_zero_strip() -> None:
	"""fmt_precise strips the leading zero from 0.5 -> .5 and -0.5 -> -.5."""
	assert normalize_svg_v3.fmt_precise(0.5) == ".5"
	assert normalize_svg_v3.fmt_precise(-0.5) == "-.5"


def test_precision_fmt_precise_integer_strips_trailing_zeros() -> None:
	"""fmt_precise emits integers without decimal point: 10.0 -> '10'."""
	result = normalize_svg_v3.fmt_precise(10.0)
	assert "." not in result
	assert result == "10"


def test_precision_fmt_precise_zero() -> None:
	"""fmt_precise returns '0' for values very close to zero."""
	result = normalize_svg_v3.fmt_precise(0.0)
	assert result == "0"
	result2 = normalize_svg_v3.fmt_precise(1e-12)
	assert result2 == "0"


def test_precision_normalize_twice_identical(tmp_path) -> None:
	"""Normalizing a file twice produces byte-identical output (determinism).

	This is the A4 round-trip determinism check: the precision formatter must
	not introduce drift on repeated application.
	"""
	svg_in = tmp_path / "det.svg"
	svg_out1 = tmp_path / "det.out1.svg"
	svg_out2 = tmp_path / "det.out2.svg"
	_write_svg(
		svg_in,
		'<path d="M 3.14159265 2.71828182 L 100.123456789 50.987654321" '
		'fill="#000"/>',
	)
	result1 = normalize_svg_v3.normalize_svg_file(svg_in, svg_out1, padding=2.0)
	assert result1.normalized, f"unexpected rejection: {result1.rejection}"
	# Second normalization: input is the already-normalized output.
	result2 = normalize_svg_v3.normalize_svg_file(svg_out1, svg_out2, padding=2.0)
	assert result2.normalized, f"second-pass rejection: {result2.rejection}"
	content1 = svg_out1.read_text(encoding="utf-8")
	content2 = svg_out2.read_text(encoding="utf-8")
	# The path d attribute content must be identical across passes.
	# (viewBox may shift on second pass due to padding; we only require
	# the coordinate content to be stable.)
	assert content1 == content2, "second normalization produced different output"


#============================================
# Always-reject detector tests: script/handler, animation, DOCTYPE/entity, foreignObject
#============================================

def test_reject_script_element(tmp_path) -> None:
	"""A file containing a <script> element is rejected with SCRIPT_OR_HANDLER."""
	svg_in = tmp_path / "script.svg"
	svg_out = tmp_path / "script.out.svg"
	_write_svg(svg_in, '<rect x="10" y="10" width="80" height="80" fill="#000"/>'
		'<script>alert(1)</script>')
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert not result.normalized
	assert result.rejection.code == "SCRIPT_OR_HANDLER"
	assert not result.output_written
	assert not svg_out.exists()


def test_reject_onclick_handler(tmp_path) -> None:
	"""A file with an on* event handler attribute is rejected with SCRIPT_OR_HANDLER."""
	svg_in = tmp_path / "onclick.svg"
	svg_out = tmp_path / "onclick.out.svg"
	_write_svg(svg_in, '<rect x="10" y="10" width="80" height="80" fill="#000" onclick="evil()"/>')
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert not result.normalized
	assert result.rejection.code == "SCRIPT_OR_HANDLER"
	assert not result.output_written


def test_reject_animation_animate(tmp_path) -> None:
	"""A file containing an <animate> element is rejected with ANIMATION_UNSUPPORTED."""
	svg_in = tmp_path / "animate.svg"
	svg_out = tmp_path / "animate.out.svg"
	_write_svg(svg_in, '<rect x="10" y="10" width="80" height="80" fill="#000">'
		'<animate attributeName="x" from="10" to="50" dur="1s"/>'
		'</rect>')
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert not result.normalized
	assert result.rejection.code == "ANIMATION_UNSUPPORTED"
	assert not result.output_written


def test_reject_animation_animate_transform(tmp_path) -> None:
	"""A file containing an <animateTransform> element is rejected with ANIMATION_UNSUPPORTED."""
	svg_in = tmp_path / "animateTransform.svg"
	svg_out = tmp_path / "animateTransform.out.svg"
	_write_svg(svg_in, '<rect x="10" y="10" width="80" height="80" fill="#000">'
		'<animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="1s"/>'
		'</rect>')
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert not result.normalized
	assert result.rejection.code == "ANIMATION_UNSUPPORTED"


def test_reject_doctype_declaration(tmp_path) -> None:
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
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert not result.normalized
	assert result.rejection.code == "DOCTYPE_OR_ENTITY"
	assert not result.output_written
	assert not svg_out.exists()


def test_reject_foreignobject(tmp_path) -> None:
	"""A file containing a <foreignObject> element is rejected with FOREIGNOBJECT_UNSUPPORTED."""
	svg_in = tmp_path / "foreignobj.svg"
	svg_out = tmp_path / "foreignobj.out.svg"
	_write_svg(svg_in, '<rect x="10" y="10" width="80" height="80" fill="#000"/>'
		'<foreignObject x="0" y="0" width="100" height="100">'
		'<div xmlns="http://www.w3.org/1999/xhtml">hello</div>'
		'</foreignObject>')
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=2.0)
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
def test_reject_set(tmp_path, fixture_id, svg_body, expected_code) -> None:
	"""Each unsupported feature rejects with its declared reason code.

	Behavioral: the gate refuses the file with the right code and writes no
	output (the rejection contract: no output, input untouched).
	"""
	svg_in = tmp_path / f"{fixture_id}.svg"
	svg_out = tmp_path / f"{fixture_id}.out.svg"
	_write_svg(svg_in, svg_body)
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert not result.normalized, f"{fixture_id}: expected rejection, got normalized"
	assert result.rejection.code == expected_code, (
		f"{fixture_id}: expected {expected_code}, got {result.rejection.code}"
	)
	assert not svg_out.exists(), f"{fixture_id}: output written despite rejection"


def test_style_paint_only_preserved(tmp_path) -> None:
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
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	content = svg_out.read_text(encoding="utf-8")
	assert "<style" in content, "paint-only <style> block was dropped"


def test_paint_only_pattern_preserved(tmp_path) -> None:
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
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"


#============================================
# F8 -- rewrite url(#id) inside <style> on ASCII id rename
#============================================

def test_f8_style_url_ref_rewritten_on_rename(tmp_path) -> None:
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
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=2.0)
	# The file must normalize: the rename keeps both the attribute ref and the
	# <style> ref pointing at the renamed gradient id (no dangling ref).
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	content = svg_out.read_text(encoding="utf-8")
	# The non-ASCII id must be gone from the output entirely.
	assert bad_id not in content, "non-ASCII id survived in output"
	# The <style> url(#) and the renamed gradient id must agree: find the new id
	# from the gradient element and confirm the style references it.
	root = normalize_svg_v3.lxml.etree.parse(str(svg_out)).getroot()
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

def test_s1_dangling_url_ref_rejected(tmp_path) -> None:
	"""A url(#id) paint reference with no matching id rejects with UNRESOLVED_REFERENCE."""
	svg_in = tmp_path / "dangling.svg"
	svg_out = tmp_path / "dangling.out.svg"
	# fill references #nope which is never defined.
	_write_svg(svg_in, '<rect x="0" y="0" width="10" height="10" fill="url(#nope)"/>')
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert not result.normalized
	assert result.rejection.code == "UNRESOLVED_REFERENCE"
	assert not svg_out.exists()


def test_s1_resolved_ref_normalizes(tmp_path) -> None:
	"""A url(#id) reference to a defined gradient passes the S1 gate."""
	svg_in = tmp_path / "resolved.svg"
	svg_out = tmp_path / "resolved.out.svg"
	_write_svg(
		svg_in,
		'<defs><linearGradient id="ok"><stop offset="0" stop-color="#000"/></linearGradient></defs>'
		'<rect x="0" y="0" width="10" height="10" fill="url(#ok)"/>',
	)
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"


#============================================
# B1 -- editor-cruft removal (positive allowlist)
#============================================

def test_b1_cruft_removed_attribution_preserved(tmp_path) -> None:
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
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=2.0)
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


def test_b1_preserves_render_attrs_and_ids(tmp_path) -> None:
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
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	root = normalize_svg_v3.lxml.etree.parse(str(svg_out)).getroot()
	kept = root.find(f".//{{{SVG_NS}}}path[@id='keepme']")
	assert kept is not None, "id and converted geometry must survive cruft removal"
	assert kept.get("fill") == "#abc", "render attribute fill must survive"


#============================================
# Floor-shadow removal (D1)
#
# Test fixtures use a synthetic asset pattern: a tall object path (the "real"
# object) plus a wide-flat low-opacity grey ellipse in the bottom band.
# The real object occupies the upper region; the shadow sits in the lowest ~20%
# and is visually much wider than it is tall.
#
# Detection function: detect_floor_shadow_candidates (pure, testable).
# Wiring: normalize_svg_file with remove_floor_shadow=True deletes before the
# single bbox pass; flag False (default) is a no-op.
# Dry-run: _shadow_dry_run_report reports without deleting (tested via the
# detection function directly, since _shadow_dry_run_report is a CLI helper).
#============================================


def _make_shadow_svg(real_body: str, shadow_body: str) -> str:
	"""Compose a minimal SVG with a real-object path and a shadow path.

	Both bodies are raw element strings (already <path> elements).
	The SVG viewBox is large enough to contain both.

	Args:
		real_body: The <path ...> string for the real object.
		shadow_body: The <path ...> string for the floor shadow.

	Returns:
		Complete SVG text string.
	"""
	svg_text = (
		f'<svg xmlns="{SVG_NS}" viewBox="0 0 200 200">'
		f'{real_body}'
		f'{shadow_body}'
		f'</svg>'
	)
	return svg_text


# A tall rect representing the "real" object (upper region, 20x80).
_REAL_OBJECT_PATH = (
	'<path d="M 80 10 L 100 10 L 100 90 L 80 90 Z" fill="#333"/>'
)

# A wide-flat low-opacity grey ellipse in the bottom band (y=160..175, w=160, h=15).
# width/height = 160/15 ~ 10.7 >> 3.0, center_y=167.5 > 200*0.8=160 -> bottom band.
# fill-opacity=0.3 < 0.5 -> shadow signal.
_SHADOW_PATH_OPACITY = (
	'<path d="M 20 160 A 80 7.5 0 1 0 180 160 A 80 7.5 0 1 0 20 160 Z"'
	' fill="#888" fill-opacity="0.3"/>'
)

# A wide-flat grey fill path (no explicit fill-opacity, uses grey colour signal).
# fill=#808080 -> R=128,G=128,B=128: max=128 <= 180, max-min=0 <= 30 -> grey.
_SHADOW_PATH_GREY = (
	'<path d="M 20 160 A 80 7.5 0 1 0 180 160 A 80 7.5 0 1 0 20 160 Z"'
	' fill="#808080"/>'
)

# A wide-flat path with id containing "shadow".
_SHADOW_PATH_ID = (
	'<path d="M 20 160 A 80 7.5 0 1 0 180 160 A 80 7.5 0 1 0 20 160 Z"'
	' id="floor_shadow_ellipse" fill="#ccc"/>'
)

# A wide-flat bottom path that is NOT a shadow: full-opacity saturated red.
_NOT_SHADOW_PATH = (
	'<path d="M 20 160 A 80 7.5 0 1 0 180 160 A 80 7.5 0 1 0 20 160 Z"'
	' fill="#ff0000"/>'
)


def _parse_svg_root(svg_text: str) -> "normalize_svg_v3.lxml.etree._Element":
	"""Parse SVG text and return the root element."""
	return normalize_svg_v3.lxml.etree.fromstring(svg_text.encode("utf-8"))


#============================================
# Detection-function unit tests (pure, no file I/O)
#============================================

@pytest.mark.parametrize("shadow_path,expected_signal", [
	(_SHADOW_PATH_OPACITY, "fill_opacity"),
	(_SHADOW_PATH_GREY, "grey_fill"),
	(_SHADOW_PATH_ID, "id_class"),
])
def test_d1_detect_shadow_candidate_found(shadow_path: str, expected_signal: str) -> None:
	"""detect_floor_shadow_candidates finds the wide-flat bottom shadow element.

	Three synthetic shadow signals are tested: fill-opacity, grey fill, id_class.
	Each must produce exactly one candidate with the expected signal name.
	"""
	svg_text = _make_shadow_svg(_REAL_OBJECT_PATH, shadow_path)
	root = _parse_svg_root(svg_text)
	# Compute overall bbox from the two paths.
	overall_bbox = normalize_svg_v3.compute_bbox(root)
	candidates = normalize_svg_v3.detect_floor_shadow_candidates(root, overall_bbox)
	assert len(candidates) == 1, f"expected 1 candidate for signal={expected_signal}, got {len(candidates)}"
	assert candidates[0].signal == expected_signal


def test_d1_detect_no_false_positive_saturated_color() -> None:
	"""detect_floor_shadow_candidates must NOT flag a saturated-color bottom path.

	A wide-flat bottom element with full-opacity saturated red fill and no
	shadow id/class is not a shadow -- no false positive.
	"""
	svg_text = _make_shadow_svg(_REAL_OBJECT_PATH, _NOT_SHADOW_PATH)
	root = _parse_svg_root(svg_text)
	overall_bbox = normalize_svg_v3.compute_bbox(root)
	candidates = normalize_svg_v3.detect_floor_shadow_candidates(root, overall_bbox)
	assert len(candidates) == 0, f"false positive: got {len(candidates)} candidate(s)"


def test_d1_detect_no_candidate_when_not_bottom_band() -> None:
	"""An element in the top half is not a floor-shadow candidate even if wide-flat.

	The shadow shape is moved to y=10..25 (top region): its center_y is well
	above the bottom-band threshold.
	"""
	# Wide-flat low-opacity path at the TOP (y=10..25, center_y=17.5).
	top_shadow = (
		'<path d="M 20 10 A 80 7.5 0 1 0 180 10 A 80 7.5 0 1 0 20 10 Z"'
		' fill="#888" fill-opacity="0.3"/>'
	)
	svg_text = _make_shadow_svg(_REAL_OBJECT_PATH, top_shadow)
	root = _parse_svg_root(svg_text)
	overall_bbox = normalize_svg_v3.compute_bbox(root)
	candidates = normalize_svg_v3.detect_floor_shadow_candidates(root, overall_bbox)
	assert len(candidates) == 0, "wide-flat top element should not be a shadow candidate"


def test_d1_detect_no_candidate_when_not_wide_flat() -> None:
	"""A squarish bottom element is not a floor-shadow candidate even with low opacity.

	A square-ish path (aspect ~1.0) in the bottom band with fill-opacity=0.2
	should not be detected (fails the wide-flat criterion).
	"""
	# A square-ish low-opacity path at the bottom (w=20, h=15, aspect=1.3 < 3).
	squarish_bottom = (
		'<path d="M 85 160 L 105 160 L 105 175 L 85 175 Z"'
		' fill="#888" fill-opacity="0.2"/>'
	)
	svg_text = _make_shadow_svg(_REAL_OBJECT_PATH, squarish_bottom)
	root = _parse_svg_root(svg_text)
	overall_bbox = normalize_svg_v3.compute_bbox(root)
	candidates = normalize_svg_v3.detect_floor_shadow_candidates(root, overall_bbox)
	assert len(candidates) == 0, "non-wide-flat bottom element should not be a shadow candidate"


#============================================
# Style-class no-guess test: shadow signal via <style> class only -> no candidate
#============================================

def test_d1_no_guess_on_style_class_only_signal() -> None:
	"""A shadow signal living ONLY in a <style> class rule is not used (no guessing).

	A wide-flat bottom path whose fill-opacity:0.2 is set only by a <style> class
	rule (no inline style, no presentation attribute) and whose id/class do NOT
	contain "shadow" and whose fill is saturated (not grey) must produce NO
	candidate: v3 reads only the inline cascade and never resolves a class rule.

	The file would be rejected by _detect_style_geometry (fill-opacity in
	<style>), so the detection function is exercised directly on a prepared root.
	"""
	svg_text = (
		f'<svg xmlns="{SVG_NS}" viewBox="0 0 200 200">'
		'<style>.band { fill-opacity: 0.2; }</style>'
		+ _REAL_OBJECT_PATH
		+ '<path d="M 20 160 A 80 7.5 0 1 0 180 160 A 80 7.5 0 1 0 20 160 Z"'
		' class="band" id="floorband" fill="#0044ff"/>'
		'</svg>'
	)
	root = _parse_svg_root(svg_text)
	overall_bbox = normalize_svg_v3.compute_bbox(root)
	candidates = normalize_svg_v3.detect_floor_shadow_candidates(root, overall_bbox)
	# fill-opacity is only in <style> (ignored); fill #0044ff is not grey; neither
	# id nor class contains "shadow" -> the no-guess rule yields zero candidates.
	assert len(candidates) == 0


def test_d1_no_fill_opacity_signal_from_style_class() -> None:
	"""fill-opacity from a <style> class rule is NOT used as a shadow signal.

	A wide-flat bottom path with its fill-opacity set only via a <style> block
	(the element itself has no inline fill-opacity and no presentation attribute)
	must NOT trigger the fill_opacity sub-criterion.  The id and class are neutral
	(no 'shadow' substring).  The fill colour is saturated blue (#0000ff) so
	grey_fill is also absent.  Result: no candidate.
	"""
	# This SVG would normally be REJECTED by _detect_style_geometry (fill-opacity
	# in a <style> block is in _STYLE_GEOMETRY_PROPS).  We test the detection
	# function directly with a pre-prepared root (bypassing the classifier).
	svg_text = (
		f'<svg xmlns="{SVG_NS}" viewBox="0 0 200 200">'
		'<style>.accent { fill-opacity: 0.1; }</style>'
		+ _REAL_OBJECT_PATH
		+ '<path d="M 20 160 A 80 7.5 0 1 0 180 160 A 80 7.5 0 1 0 20 160 Z"'
		' class="accent" id="bottomband" fill="#0000ff"/>'
		'</svg>'
	)
	root = _parse_svg_root(svg_text)
	overall_bbox = normalize_svg_v3.compute_bbox(root)
	candidates = normalize_svg_v3.detect_floor_shadow_candidates(root, overall_bbox)
	# fill="#0000ff": max channel 255 > _SHADOW_GREY_MAX_VALUE -> not grey.
	# fill-opacity is only in <style> -> no fill_opacity signal.
	# id="bottomband", class="accent": neither contains "shadow" -> no id_class.
	assert len(candidates) == 0, (
		f"no shadow signal should fire on a saturated fill with "
		f"fill-opacity only in <style>; got {len(candidates)} candidate(s)"
	)


#============================================
# normalize_svg_file integration tests (flag-off vs flag-on)
#============================================

def test_d1_flag_off_shadow_retained(tmp_path) -> None:
	"""With remove_floor_shadow=False (default), the shadow element is NOT removed.

	The viewBox must include the shadow's geometry (bbox includes the bottom band).
	"""
	svg_text = _make_shadow_svg(_REAL_OBJECT_PATH, _SHADOW_PATH_OPACITY)
	svg_in = tmp_path / "shadow_off.svg"
	svg_out = tmp_path / "shadow_off.out.svg"
	svg_in.write_text(svg_text, encoding="utf-8")

	# Default: remove_floor_shadow=False.
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	# With shadow retained, the bbox must include the shadow region (min_y ~ 152.5
	# because the arc bottom extends past y=160).  The real object ends at y=90.
	# So bbox height must be significantly larger than 80 (the real object height).
	bb = result.bbox
	assert bb is not None
	assert (bb.max_y - bb.min_y) > 100.0, (
		"flag-off: shadow retained so bbox height should exceed 100"
	)


def test_d1_flag_on_shadow_removed_viewbox_tightens(tmp_path) -> None:
	"""With remove_floor_shadow=True, the shadow is removed and the viewBox tightens.

	After removal the bbox must NOT extend into the shadow's y-range; the tightened
	viewBox height must be smaller than when the shadow is retained.
	"""
	svg_text = _make_shadow_svg(_REAL_OBJECT_PATH, _SHADOW_PATH_OPACITY)
	svg_in = tmp_path / "shadow_on.svg"
	svg_out_off = tmp_path / "shadow_on_off.out.svg"
	svg_out_on = tmp_path / "shadow_on_on.out.svg"
	svg_in.write_text(svg_text, encoding="utf-8")

	result_off = normalize_svg_v3.normalize_svg_file(svg_in, svg_out_off, padding=0.0)
	result_on = normalize_svg_v3.normalize_svg_file(
		svg_in, svg_out_on, padding=0.0, remove_floor_shadow=True
	)
	assert result_off.normalized, f"flag-off unexpected rejection: {result_off.rejection}"
	assert result_on.normalized, f"flag-on unexpected rejection: {result_on.rejection}"

	height_off = result_off.bbox.max_y - result_off.bbox.min_y
	height_on = result_on.bbox.max_y - result_on.bbox.min_y
	# After shadow removal the bbox must be strictly smaller.
	assert height_on < height_off, (
		f"flag-on bbox height {height_on:.2f} should be less than flag-off {height_off:.2f}"
	)
	# The real object occupies y=10..90 (height=80); after shadow removal the
	# tightened bbox height should be close to 80 (within a small tolerance).
	assert abs(height_on - 80.0) < 5.0, (
		f"tightened bbox height {height_on:.2f} should be ~80 (real object only)"
	)


def test_d1_dry_run_reports_numeric_geometry_without_mutating_input(
	tmp_path, capsys,
) -> None:
	"""The dry-run report formats numeric bounds and preserves source bytes."""
	svg_in = tmp_path / "dry_run_shadow.svg"
	svg_text = _make_shadow_svg(_REAL_OBJECT_PATH, _SHADOW_PATH_OPACITY)
	svg_in.write_text(svg_text, encoding="utf-8")
	original_bytes = svg_in.read_bytes()

	normalize_svg_v3._shadow_dry_run_report(svg_in)

	report = capsys.readouterr().out
	assert re.search(
		r"SHADOW-CANDIDATE: .*bbox=\([^)]*\).*"
		r"crop_delta=\(w_shrink_up_to=\d+(?:\.\d+)? "
		r"h_shrink_up_to=\d+(?:\.\d+)?\)",
		report,
	)
	assert svg_in.read_bytes() == original_bytes


@pytest.mark.parametrize(
	"hex_fill",
	[
		"#808080",  # classic mid-grey
		"#404040",  # dark grey
		"#888",     # 3-hex grey -> #888888 (max=136 <= 180, delta=0 <= 30)
	],
	ids=["mid_grey", "dark_grey", "short_hex_grey"],
)
def test_d1_grey_fill_signal_true(hex_fill) -> None:
	"""_fill_is_desaturated_grey accepts desaturated mid/low grey hex fills."""
	assert normalize_svg_v3._fill_is_desaturated_grey(hex_fill)


@pytest.mark.parametrize(
	"hex_fill",
	[
		"#f0f0f0",  # near-white: max channel 240 > 180
		"#ff0000",  # saturated red: per-channel delta 255 >> 30
		"grey",     # named colour, not a parseable hex value
	],
	ids=["near_white", "saturated_red", "named_colour"],
)
def test_d1_grey_fill_signal_false(hex_fill) -> None:
	"""_fill_is_desaturated_grey rejects near-white, saturated, and non-hex fills."""
	assert not normalize_svg_v3._fill_is_desaturated_grey(hex_fill)


def test_d1_output_passes_reference_integrity(tmp_path) -> None:
	"""After shadow removal the output still passes S1 reference integrity.

	A shadow path that has no url(#) references; removing it must leave all
	other references intact.
	"""
	svg_text = _make_shadow_svg(_REAL_OBJECT_PATH, _SHADOW_PATH_OPACITY)
	svg_in = tmp_path / "ref_int.svg"
	svg_out = tmp_path / "ref_int.out.svg"
	svg_in.write_text(svg_text, encoding="utf-8")
	result = normalize_svg_v3.normalize_svg_file(
		svg_in, svg_out, padding=0.0, remove_floor_shadow=True
	)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	# Re-parse output and confirm reference integrity passes.
	out_root = normalize_svg_v3.lxml.etree.parse(str(svg_out)).getroot()
	ref_rejection = normalize_svg_v3.check_reference_integrity(out_root)
	assert ref_rejection is None, f"S1 reference integrity failed after shadow removal: {ref_rejection}"


#============================================
# Simple-clipPath flattening behavior tests
#============================================

def _normalize_clip(tmp_path, body, padding=0.0):
	"""Helper: wrap body in an <svg>, normalize, and return (result, output text)."""
	svg_in = tmp_path / "clip_in.svg"
	svg_out = tmp_path / "clip_out.svg"
	_write_svg(svg_in, body)
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=padding)
	text = svg_out.read_text(encoding="utf-8") if svg_out.exists() else ""
	return result, text


#============================================
def _element_with_id(
	root: lxml.etree._Element,
	element_id: str,
) -> lxml.etree._Element | None:
	"""Return the output element with element_id, or None when it is absent."""
	for elem in root.iter():
		if isinstance(elem.tag, str) and elem.get("id") == element_id:
			return elem
	return None


#============================================
def _rect_or_path_geometry_bbox(elem: lxml.etree._Element) -> normalize_svg_v3.BBox:
	"""Return geometry bbox for a retained clip child in either supported form."""
	tag = normalize_svg_v3.local_name(elem.tag)
	if tag == "path":
		d_attr = elem.get("d")
		assert d_attr is not None
		bbox = normalize_svg_v3.path_bbox_from_segments(
			normalize_svg_v3.parse_path_to_absolute(d_attr)
		)
		assert bbox is not None
		return bbox
	assert tag == "rect"
	x_attr = elem.get("x")
	y_attr = elem.get("y")
	width_attr = elem.get("width")
	height_attr = elem.get("height")
	assert x_attr is not None and y_attr is not None
	assert width_attr is not None and height_attr is not None
	x = float(x_attr)
	y = float(y_attr)
	return normalize_svg_v3.BBox(x, y, x + float(width_attr), y + float(height_attr))


def test_clip_flatten_drops_clip_ref_and_def(tmp_path) -> None:
	"""A flattened simple clip leaves no clip-path attribute and no clipPath def.

	After flattening, the output must contain neither a clip-path reference nor
	the now-unused <clipPath> definition, and must pass S1 reference integrity.
	"""
	body = (
		'<defs><clipPath id="c"><rect x="5" y="5" width="40" height="40"/></clipPath></defs>'
		'<rect x="20" y="20" width="60" height="60" fill="#000" clip-path="url(#c)"/>'
	)
	result, text = _normalize_clip(tmp_path, body)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	assert "clip-path" not in text and "clipPath" not in text


def test_clip_flatten_simple_not_rejected_by_classify(tmp_path) -> None:
	"""classify() must not reject a simple clip; flattening handles it.

	A single filled rect clipped by a single rect clipPath normalizes (the gate
	does not refuse it as CLIPPATH_UNSUPPORTED_COMPLEX).
	"""
	body = (
		'<defs><clipPath id="c"><circle cx="50" cy="50" r="30"/></clipPath></defs>'
		'<rect x="0" y="0" width="100" height="100" fill="#000" clip-path="url(#c)"/>'
	)
	result, _ = _normalize_clip(tmp_path, body)
	assert result.normalized, f"simple clip wrongly rejected: {result.rejection}"


def test_clip_flatten_multipolygon_with_hole(tmp_path) -> None:
	"""A clip producing a hole emits exterior + reverse-wound interior subpaths.

	A ring-shaped target (outer square with an inner square hole, even-odd fill)
	clipped by a containing rect must keep its hole: the flattened path data has
	more than one subpath (M ... appears at least twice).
	"""
	body = (
		'<defs><clipPath id="c"><rect x="-10" y="-10" width="200" height="200"/></clipPath></defs>'
		'<path fill-rule="evenodd" fill="#000" clip-path="url(#c)" '
		'd="M 0 0 H 100 V 100 H 0 Z M 30 30 H 70 V 70 H 30 Z"/>'
	)
	result, text = _normalize_clip(tmp_path, body)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	assert text.count("M ") >= 2


def test_clip_flatten_complex_nested_rejected(tmp_path) -> None:
	"""A clipPath containing a forbidden child (text) rejects as complex."""
	body = (
		'<defs><clipPath id="c"><text x="0" y="0">x</text></clipPath></defs>'
		'<rect x="0" y="0" width="40" height="40" fill="#000" clip-path="url(#c)"/>'
	)
	result, _ = _normalize_clip(tmp_path, body)
	# The <text> is caught by the text classifier before clip flattening, but the
	# verdict is still a rejection (the file is not normalized).
	assert not result.normalized


#============================================
# Runtime material clip preservation
#============================================

def test_normalize_keeps_runtime_material_clip_without_expanding_visible_crop(
	tmp_path: pathlib.Path,
) -> None:
	"""An external material clip survives while a generic unused clip is pruned.

	Runtime resolves anchor_liquid_clip after SVG injection, so it has no local
	clip-path user.  Its far-away geometry must survive normalization without
	changing the cropped dimensions of the visible instrument.
	"""
	svg_in = tmp_path / "material_anchor.svg"
	svg_out = tmp_path / "material_anchor.out.svg"
	_write_svg(
		svg_in,
		'<defs>'
		'<clipPath id="anchor_liquid_clip"><rect x="900" y="1200" width="20" height="10"/></clipPath>'
		'<clipPath id="unused_clip"><rect x="700" y="800" width="20" height="10"/></clipPath>'
		'</defs>'
		'<rect id="anchor_liquid_bounds" x="100" y="200" width="30" height="20" '
		'fill="none" stroke="none" display="none"/>'
		'<rect x="100" y="200" width="30" height="20" fill="#000"/>',
	)
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	assert result.bbox is not None
	assert abs(result.bbox.width - 30.0) < 1e-9
	assert abs(result.bbox.height - 20.0) < 1e-9
	assert result.view_box is not None
	view_box_parts = result.view_box.split()
	assert abs(float(view_box_parts[2]) - 30.0) < 1e-9
	assert abs(float(view_box_parts[3]) - 20.0) < 1e-9

	root = normalize_svg_v3.lxml.etree.parse(str(svg_out)).getroot()
	clip = _element_with_id(root, "anchor_liquid_clip")
	assert clip is not None
	assert _element_with_id(root, "unused_clip") is None
	clip_child = next(
		child
		for child in clip
		if normalize_svg_v3.local_name(child.tag) in {"path", "rect"}
	)
	clip_bbox = _rect_or_path_geometry_bbox(clip_child)
	assert abs(clip_bbox.min_x - 800.0) < 1e-9
	assert abs(clip_bbox.min_y - 1000.0) < 1e-9


def test_normalize_preserves_runtime_material_bounds_rect_geometry(
	tmp_path: pathlib.Path,
) -> None:
	"""The hidden material bounds anchor remains a rect with shifted geometry."""
	svg_in = tmp_path / "material_bounds.svg"
	svg_out = tmp_path / "material_bounds.out.svg"
	_write_svg(
		svg_in,
		'<rect id="anchor_liquid_bounds" x="100" y="200" width="30" height="20" '
		'fill="none" stroke="none" display="none"/>'
		'<rect x="100" y="200" width="30" height="20" fill="#000"/>',
	)
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	root = normalize_svg_v3.lxml.etree.parse(str(svg_out)).getroot()
	anchor = _element_with_id(root, "anchor_liquid_bounds")
	assert anchor is not None and normalize_svg_v3.local_name(anchor.tag) == "rect"
	assert (
		float(anchor.get("x", "nan")),
		float(anchor.get("y", "nan")),
		float(anchor.get("width", "nan")),
		float(anchor.get("height", "nan")),
	) == (0.0, 0.0, 30.0, 20.0)


def test_runtime_material_clip_path_shifts_with_anchor_bounds(
	tmp_path: pathlib.Path,
) -> None:
	"""Crop-to-origin shifts an external path clip and its material bounds together."""
	svg_in = tmp_path / "material_path.svg"
	svg_out = tmp_path / "material_path.out.svg"
	_write_svg(
		svg_in,
		'<defs><clipPath id="anchor_liquid_clip">'
		'<path d="M 110 215 H 125 V 222 H 110 Z"/>'
		'</clipPath></defs>'
		'<rect id="anchor_liquid_bounds" x="100" y="200" width="30" height="20" '
		'fill="none" stroke="none" display="none"/>'
		'<rect x="100" y="200" width="30" height="20" fill="#000"/>',
	)
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"

	root = normalize_svg_v3.lxml.etree.parse(str(svg_out)).getroot()
	clip = _element_with_id(root, "anchor_liquid_clip")
	assert clip is not None
	clip_child = next(
		child
		for child in clip
		if normalize_svg_v3.local_name(child.tag) in {"path", "rect"}
	)
	clip_bbox = _rect_or_path_geometry_bbox(clip_child)
	anchor_bounds = _element_with_id(root, "anchor_liquid_bounds")
	assert anchor_bounds is not None
	assert normalize_svg_v3.local_name(anchor_bounds.tag) == "rect"
	anchor_x = float(anchor_bounds.get("x", "nan"))
	anchor_y = float(anchor_bounds.get("y", "nan"))
	assert abs(clip_bbox.min_x - (anchor_x + 10.0)) < 1e-9
	assert abs(clip_bbox.min_y - (anchor_y + 15.0)) < 1e-9


def test_transformed_runtime_material_bounds_rect_rejects_without_output(
	tmp_path: pathlib.Path,
) -> None:
	"""A material bounds rect must stay in root coordinates for direct DOM reads."""
	svg_in = tmp_path / "material_bounds_transform.svg"
	svg_out = tmp_path / "material_bounds_transform.out.svg"
	_write_svg(
		svg_in,
		'<rect id="anchor_liquid_bounds" x="10" y="20" width="30" height="20" '
		'transform="translate(5 0)" fill="none" stroke="none" display="none"/>'
		'<rect x="10" y="20" width="30" height="20" fill="#000"/>',
	)
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert not result.normalized
	assert result.rejection is not None
	assert result.rejection.code == "UNSUPPORTED_TRANSFORM"
	assert not svg_out.exists()


def test_inherited_transform_on_runtime_material_bounds_rect_rejects_without_output(
	tmp_path: pathlib.Path,
) -> None:
	"""A parent geometry transform cannot be baked into the runtime bounds rect."""
	svg_in = tmp_path / "material_bounds_inherited_transform.svg"
	svg_out = tmp_path / "material_bounds_inherited_transform.out.svg"
	_write_svg(
		svg_in,
		'<g transform="translate(5 0)">'
		'<rect id="anchor_liquid_bounds" x="10" y="20" width="30" height="20" '
		'fill="none" stroke="none" display="none"/>'
		'</g><rect x="10" y="20" width="30" height="20" fill="#000"/>',
	)
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert not result.normalized
	assert result.rejection is not None
	assert result.rejection.code == "UNSUPPORTED_TRANSFORM"
	assert not svg_out.exists()


def test_duplicate_runtime_material_bounds_rects_reject_without_output(
	tmp_path: pathlib.Path,
) -> None:
	"""Two divergent bounds rects cannot resolve one material target."""
	svg_in = tmp_path / "duplicate_material_bounds.svg"
	svg_out = tmp_path / "duplicate_material_bounds.out.svg"
	_write_svg(
		svg_in,
		'<rect id="anchor_liquid_bounds" x="10" y="20" width="30" height="20" '
		'fill="none" stroke="none" display="none"/>'
		'<rect id="anchor_liquid_bounds" x="40" y="50" width="60" height="70" '
		'fill="none" stroke="none" display="none"/>'
		'<rect x="10" y="20" width="30" height="20" fill="#000"/>',
	)
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.rejection is not None and result.rejection.code == "UNRESOLVED_REFERENCE"
	assert not svg_out.exists()


def test_nonrect_runtime_material_bounds_anchor_rejects_without_output(
	tmp_path: pathlib.Path,
) -> None:
	"""The material runtime requires a bounds rect, not arbitrary path geometry."""
	svg_in = tmp_path / "path_material_bounds.svg"
	svg_out = tmp_path / "path_material_bounds.out.svg"
	_write_svg(
		svg_in,
		'<path id="anchor_liquid_bounds" d="M 10 20 H 40 V 40 H 10 Z" '
		'fill="none" stroke="none" display="none"/>'
		'<rect x="10" y="20" width="30" height="20" fill="#000"/>',
	)
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.rejection is not None and result.rejection.code == "UNRESOLVED_REFERENCE"
	assert not svg_out.exists()


def test_runtime_material_bounds_rect_inside_defs_rejects_without_output(
	tmp_path: pathlib.Path,
) -> None:
	"""A definition-space bounds rect is not the material renderer's target."""
	svg_in = tmp_path / "defs_material_bounds.svg"
	svg_out = tmp_path / "defs_material_bounds.out.svg"
	_write_svg(
		svg_in,
		'<defs><rect id="anchor_liquid_bounds" x="10" y="20" width="30" height="20"/></defs>'
		'<rect x="10" y="20" width="30" height="20" fill="#000"/>',
	)
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.rejection is not None and result.rejection.code == "UNRESOLVED_REFERENCE"
	assert not svg_out.exists()


#============================================
# Rank 1 no-op clip elimination behavior tests
#============================================

def _clip_target_path(root):
	"""Return the single drawable <path> target (the one element with id 't')."""
	for elem in root.iter():
		if isinstance(elem.tag, str) and normalize_svg_v3.local_name(elem.tag) == "path":
			if elem.get("id") == "t":
				return elem
	raise AssertionError("target path id='t' not found")


def test_noop_stroke_only_contained_drops_ref_keeps_d() -> None:
	"""A stroke-only target inside its clip: ref removed, target d untouched.

	flatten_clip_paths is called directly (no origin shift) so the d can be
	compared byte-for-byte: the no-op short circuit must not rewrite geometry.
	"""
	original_d = "M 30 30 L 60 30 L 60 60 Z"
	svg_text = (
		f'<svg xmlns="{SVG_NS}" viewBox="0 0 100 100">'
		'<defs><clipPath id="c"><path d="M 10 10 H 90 V 90 H 10 Z"/></clipPath></defs>'
		f'<path id="t" clip-path="url(#c)" d="{original_d}" fill="none" '
		'stroke="#000" stroke-width="1"/>'
		"</svg>"
	)
	root = _parse_svg_root(svg_text)
	normalize_svg_v3.flatten_clip_paths(root)
	target = _clip_target_path(root)
	assert target.get("clip-path") is None, "clip-path attribute should be dropped"
	assert target.get("d") == original_d, "no-op drop must leave the target d unchanged"


def test_noop_stroke_only_trim_stays_rejected() -> None:
	"""A stroke-only target genuinely cut by its clip stays a complex rejection."""
	svg_text = (
		f'<svg xmlns="{SVG_NS}" viewBox="0 0 100 100">'
		'<defs><clipPath id="c"><path d="M 0 0 H 45 V 100 H 0 Z"/></clipPath></defs>'
		'<path id="t" clip-path="url(#c)" d="M 30 30 L 60 30 L 60 60 Z" fill="none" '
		'stroke="#000" stroke-width="1"/>'
		"</svg>"
	)
	root = _parse_svg_root(svg_text)
	with pytest.raises(normalize_svg_v3.ComplexClipError):
		normalize_svg_v3.flatten_clip_paths(root)


def test_noop_filled_contained_keeps_original_d() -> None:
	"""A filled target inside its clip keeps the original d (no polygonized re-emit).

	The intersection of a shape with a region that contains it is the shape, so the
	short circuit must preserve the exact input d rather than re-emitting a
	tolerance-flattened polygon (which would mangle precision).
	"""
	original_d = "M 30 30 L 60 30 L 60 60 Z"
	svg_text = (
		f'<svg xmlns="{SVG_NS}" viewBox="0 0 100 100">'
		'<defs><clipPath id="c"><path d="M 10 10 H 90 V 90 H 10 Z"/></clipPath></defs>'
		f'<path id="t" clip-path="url(#c)" d="{original_d}" fill="#000"/>'
		"</svg>"
	)
	root = _parse_svg_root(svg_text)
	normalize_svg_v3.flatten_clip_paths(root)
	target = _clip_target_path(root)
	assert target.get("clip-path") is None
	assert target.get("d") == original_d, "filled no-op must not re-emit a polygonized d"


def test_filled_partial_clip_intersects_and_changes_d() -> None:
	"""A filled target poking outside its clip is genuinely intersected (d changes)."""
	original_d = "M 20 20 L 80 20 L 80 80 L 20 80 Z"
	svg_text = (
		f'<svg xmlns="{SVG_NS}" viewBox="0 0 100 100">'
		'<defs><clipPath id="c"><path d="M 0 0 H 45 V 100 H 0 Z"/></clipPath></defs>'
		f'<path id="t" clip-path="url(#c)" d="{original_d}" fill="#000"/>'
		"</svg>"
	)
	root = _parse_svg_root(svg_text)
	normalize_svg_v3.flatten_clip_paths(root)
	target = _clip_target_path(root)
	assert target.get("clip-path") is None
	new_d = target.get("d")
	assert new_d != original_d, "a genuine clip must re-emit the intersected geometry"
	# The intersection is bounded by the clip at x<=45.
	bbox = normalize_svg_v3.path_bbox_from_segments(
		normalize_svg_v3.parse_path_to_absolute(new_d)
	)
	assert abs(bbox.max_x - 45.0) <= 0.2, f"clipped max_x should be ~45, got {bbox.max_x}"


def test_filled_sub_pixel_protrusion_is_not_noop() -> None:
	"""A filled target that pokes past the clip edge by a sub-pixel amount is NOT a no-op.

	The old (wrong) direction grew the clip, making the no-op fire too easily.
	The fixed code shrinks the clip, so a target that protrudes even slightly
	past the clip edge must be intersected, not dropped.

	The target square (M 30 30 L 60 30 L 60 60 L 30 60 Z) extends to x=60.
	The clip right edge is at x=59.9, so the target protrudes by 0.1 user units
	(well under the old 2*_CLIP_FLATTEN_TOLERANCE grow that would have swallowed
	it as a no-op). The corrected conservative test must NOT drop the clip.
	"""
	original_d = "M 30 30 L 60 30 L 60 60 L 30 60 Z"
	# Clip right edge at 59.9 -- target protrudes 0.1 user units past it.
	svg_text = (
		f'<svg xmlns="{SVG_NS}" viewBox="0 0 100 100">'
		'<defs><clipPath id="c"><path d="M 10 10 H 59.9 V 90 H 10 Z"/></clipPath></defs>'
		f'<path id="t" clip-path="url(#c)" d="{original_d}" fill="#000"/>'
		"</svg>"
	)
	root = _parse_svg_root(svg_text)
	normalize_svg_v3.flatten_clip_paths(root)
	target = _clip_target_path(root)
	# The clip must be honored: the output d must differ from the input.
	assert target.get("d") != original_d, (
		"sub-pixel protrusion must NOT be treated as a no-op; clip must be applied"
	)


def test_complex_clip_side_with_contained_target_rejected() -> None:
	"""A two-child clip over a contained target rejects (clip-side complexity wins)."""
	svg_text = (
		f'<svg xmlns="{SVG_NS}" viewBox="0 0 100 100">'
		'<defs><clipPath id="c">'
		'<rect x="0" y="0" width="100" height="100"/>'
		'<rect x="10" y="10" width="5" height="5"/>'
		'</clipPath></defs>'
		'<path id="t" clip-path="url(#c)" d="M 30 30 L 60 30 L 60 60 Z" fill="#000"/>'
		"</svg>"
	)
	root = _parse_svg_root(svg_text)
	with pytest.raises(normalize_svg_v3.ComplexClipError):
		normalize_svg_v3.flatten_clip_paths(root)


#============================================
# Fix B: userSpaceOnUse paint moves in sync with flattened geometry
#============================================

def _gradient_transform_of(svg_out, grad_id: str) -> "str | None":
	"""Return the gradientTransform attr of the named gradient in output, or None."""
	root = normalize_svg_v3.lxml.etree.parse(str(svg_out)).getroot()
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		if normalize_svg_v3.local_name(elem.tag) != "linearGradient":
			continue
		if elem.get("id") == grad_id:
			return elem.get("gradientTransform")
	return None


def _linear_gradient_effective_endpoints(svg_out, grad_id: str):
	"""Return the two effective endpoints of a userSpaceOnUse linearGradient.

	The browser resolves a userSpaceOnUse gradient's (x1,y1)/(x2,y2) THROUGH its
	gradientTransform in the painted element's current user space. After flattening
	the painted element has no transform, so its user space is the root space and
	the effective endpoints are gradientTransform * (x1,y1) and * (x2,y2). These are
	the render-meaningful coordinates that must land on the painted geometry.
	"""
	root = normalize_svg_v3.lxml.etree.parse(str(svg_out)).getroot()
	grad = None
	for elem in root.iter():
		if isinstance(elem.tag, str) and elem.get("id") == grad_id:
			grad = elem
			break
	assert grad is not None, f"gradient {grad_id} missing from output"
	x1 = float(grad.get("x1"))
	y1 = float(grad.get("y1"))
	x2 = float(grad.get("x2"))
	y2 = float(grad.get("y2"))
	gt = grad.get("gradientTransform")
	if gt:
		matrix = normalize_svg_v3.transforms_multiply(
			normalize_svg_v3.parse_transform_list(gt, "/test"), "/test"
		)
	else:
		matrix = normalize_svg_v3.IDENTITY_MATRIX
	p1 = normalize_svg_v3.transform_point(matrix, x1, y1)
	p2 = normalize_svg_v3.transform_point(matrix, x2, y2)
	return p1, p2


def _first_path_bbox(svg_out):
	"""Return the BBox of the first <path> in the output (the flattened geometry)."""
	root = normalize_svg_v3.lxml.etree.parse(str(svg_out)).getroot()
	for elem in root.iter():
		if isinstance(elem.tag, str) and normalize_svg_v3.local_name(elem.tag) == "path":
			segs = normalize_svg_v3.parse_path_to_absolute(elem.get("d"))
			return normalize_svg_v3.path_bbox_from_segments(segs)
	raise AssertionError("no path found in output")


def test_userspace_gradient_single_use_lands_on_flattened_geometry(tmp_path) -> None:
	"""A single-use userSpaceOnUse gradient stays aligned with the geometry it paints.

	The path carries transform="scale(2)" over local geometry (0,0)-(10,10), so on
	screen it spans (0,0)-(20,20). The gradient runs x1y1=(0,0) to x2y2=(10,10) in
	the path's local user space, i.e. corner-to-corner of the painted square. After
	flattening + crop-to-origin, the gradient's EFFECTIVE endpoints (gradientTransform
	applied to its coords) must still land on the flattened path's bbox corners; this
	is the render-meaningful invariant. Asserting only the gradientTransform matrix
	value would re-encode the earlier incomplete fix, which baked the element matrix
	but ignored the crop shift and rendered a collapsed single-stop color.
	"""
	svg_in = tmp_path / "uspace.svg"
	svg_out = tmp_path / "uspace.out.svg"
	_write_svg(
		svg_in,
		'<defs><linearGradient id="g" gradientUnits="userSpaceOnUse" '
		'x1="0" y1="0" x2="10" y2="10">'
		'<stop offset="0" stop-color="#f00"/><stop offset="1" stop-color="#00f"/>'
		'</linearGradient></defs>'
		'<path d="M 0 0 h 10 v 10 z" transform="scale(2)" fill="url(#g)"/>',
	)
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	p1, p2 = _linear_gradient_effective_endpoints(svg_out, "g")
	bbox = _first_path_bbox(svg_out)
	# Gradient start coincides with the path bbox min corner, end with the max corner.
	assert abs(p1[0] - bbox.min_x) < 1e-6 and abs(p1[1] - bbox.min_y) < 1e-6
	assert abs(p2[0] - bbox.max_x) < 1e-6 and abs(p2[1] - bbox.max_y) < 1e-6


def test_userspace_gradient_shared_diff_transform_rejected(tmp_path) -> None:
	"""A userSpaceOnUse gradient shared by two elements under different transforms rejects."""
	svg_in = tmp_path / "shared.svg"
	svg_out = tmp_path / "shared.out.svg"
	_write_svg(
		svg_in,
		'<defs><linearGradient id="g" gradientUnits="userSpaceOnUse" '
		'x1="0" y1="0" x2="10" y2="0">'
		'<stop offset="0" stop-color="#f00"/><stop offset="1" stop-color="#00f"/>'
		'</linearGradient></defs>'
		'<path d="M 0 0 h 10 v 10 z" transform="scale(2)" fill="url(#g)"/>'
		'<path d="M 0 0 h 10 v 10 z" transform="translate(50,0)" fill="url(#g)"/>',
	)
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert not result.normalized
	assert result.rejection.code == "UNSUPPORTED_TRANSFORM"
	assert not svg_out.exists()


def test_objectboundingbox_gradient_under_transform_unchanged(tmp_path) -> None:
	"""An objectBoundingBox gradient is transform-invariant: no spurious gradientTransform."""
	svg_in = tmp_path / "obb.svg"
	svg_out = tmp_path / "obb.out.svg"
	_write_svg(
		svg_in,
		'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="0">'
		'<stop offset="0" stop-color="#f00"/><stop offset="1" stop-color="#00f"/>'
		'</linearGradient></defs>'
		'<path d="M 0 0 h 10 v 10 z" transform="scale(2)" fill="url(#g)"/>',
	)
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	# Default gradientUnits is objectBoundingBox; the gradient must not gain a
	# gradientTransform from the geometry flatten.
	assert _gradient_transform_of(svg_out, "g") is None
	# objectBoundingBox coords are 0..1 fractions and crop-invariant; the crop shift
	# must NOT be added to them (the earlier shift_element bug shifted every cx/x1).
	root = normalize_svg_v3.lxml.etree.parse(str(svg_out)).getroot()
	grad = next(e for e in root.iter() if e.get("id") == "g")
	assert grad.get("x1") == "0" and grad.get("x2") == "1"


def test_userspace_gradient_crop_shift_tracks_geometry(tmp_path) -> None:
	"""A userSpaceOnUse gradient tracks the crop-to-origin shift, not just the matrix.

	The painted square sits far from the origin (translate(100,100)) so the
	crop-to-origin shift is large and non-zero. The gradient must remain aligned to
	the flattened path bbox; this is the exact case the earlier fix missed (it baked
	the element matrix but ignored the crop shift, leaving the gradient stranded).
	"""
	svg_in = tmp_path / "shift.svg"
	svg_out = tmp_path / "shift.out.svg"
	_write_svg(
		svg_in,
		'<defs><linearGradient id="g" gradientUnits="userSpaceOnUse" '
		'x1="0" y1="0" x2="10" y2="10">'
		'<stop offset="0" stop-color="#f00"/><stop offset="1" stop-color="#00f"/>'
		'</linearGradient></defs>'
		'<path d="M 0 0 h 10 v 10 z" transform="translate(100,100)" fill="url(#g)"/>',
	)
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	p1, p2 = _linear_gradient_effective_endpoints(svg_out, "g")
	bbox = _first_path_bbox(svg_out)
	# After crop-to-origin the square sits at (0,0)-(10,10); the gradient spanned it
	# corner-to-corner and must still do so.
	assert abs(p1[0] - bbox.min_x) < 1e-6 and abs(p1[1] - bbox.min_y) < 1e-6
	assert abs(p2[0] - bbox.max_x) < 1e-6 and abs(p2[1] - bbox.max_y) < 1e-6
	assert abs(bbox.min_x) < 1e-6 and abs(bbox.min_y) < 1e-6


def test_userspace_gradient_existing_transform_stays_aligned(tmp_path) -> None:
	"""A userSpaceOnUse gradient with an existing gradientTransform stays aligned.

	The path carries transform="scale(2)" (element flatten matrix M). The gradient
	already carries gradientTransform="translate(10,20)" (existing E) and runs from
	(0,0) to (10,10) in pre-E space. In the original its effective endpoints are
	M * E * coords; after flattening + crop the same effective endpoints (recomputed
	through the new gradientTransform, since the path no longer has a transform) must
	match the original up to the crop translation -- i.e. they must land on the
	flattened path bbox shifted consistently. With padding=0 the flattened path bbox
	is the crop of the on-screen square, and the gradient endpoints must coincide with
	its corners. This asserts the render-meaningful alignment, not a raw matrix value.
	"""
	svg_in = tmp_path / "compose.svg"
	svg_out = tmp_path / "compose.out.svg"
	_write_svg(
		svg_in,
		'<defs><linearGradient id="g" gradientUnits="userSpaceOnUse" '
		'gradientTransform="translate(10,20)" x1="0" y1="0" x2="10" y2="10">'
		'<stop offset="0" stop-color="#f00"/><stop offset="1" stop-color="#00f"/>'
		'</linearGradient></defs>'
		'<path d="M 0 0 h 10 v 10 z" transform="scale(2)" fill="url(#g)"/>',
	)
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	p1, p2 = _linear_gradient_effective_endpoints(svg_out, "g")
	# Original on-screen effective endpoints: M * E * coords, with M=scale(2),
	# E=translate(10,20). The geometry bbox is (0,0)-(20,20) so crop shift is zero
	# at padding=0; the effective endpoints must therefore be preserved exactly.
	m_e = normalize_svg_v3.multiply_matrices(
		(2.0, 0.0, 0.0, 2.0, 0.0, 0.0),
		normalize_svg_v3.transforms_multiply(
			normalize_svg_v3.parse_transform_list("translate(10,20)", "/test"), "/test"
		),
	)
	exp1 = normalize_svg_v3.transform_point(m_e, 0.0, 0.0)
	exp2 = normalize_svg_v3.transform_point(m_e, 10.0, 10.0)
	assert abs(p1[0] - exp1[0]) < 1e-6 and abs(p1[1] - exp1[1]) < 1e-6
	assert abs(p2[0] - exp2[0]) < 1e-6 and abs(p2[1] - exp2[1]) < 1e-6


#============================================
# Stroke-width scaling under transform flatten
#============================================

def _stroke_width_of_first_path(svg_out) -> "float | None":
	"""Return the effective stroke-width of the first path (attr or inline style)."""
	root = normalize_svg_v3.lxml.etree.parse(str(svg_out)).getroot()
	for elem in root.iter():
		if not (isinstance(elem.tag, str) and normalize_svg_v3.local_name(elem.tag) == "path"):
			continue
		attr = elem.get("stroke-width")
		if attr is not None:
			return float(attr)
		style = elem.get("style") or ""
		match = re.search(r"stroke-width\s*:\s*([-+]?[0-9.eE]+)", style)
		if match:
			return float(match.group(1))
		return None
	return None


def test_stroke_width_scaled_by_uniform_flatten_attr(tmp_path) -> None:
	"""A presentation stroke-width is scaled by the baked uniform-scale matrix.

	The element renders at scale 0.5 (transform="scale(0.5)") with stroke-width=4.
	On screen the stroke is 2 user units. After flattening the geometry to half size
	the stored stroke-width must become 2, or the hairline renders twice too thick
	(the cpu.svg mesh greyout: an over-thick stroke filled the holes).
	"""
	svg_in = tmp_path / "sw.svg"
	svg_out = tmp_path / "sw.out.svg"
	_write_svg(
		svg_in,
		'<rect x="0" y="0" width="20" height="20" transform="scale(0.5)" '
		'fill="#fff" stroke="#000" stroke-width="4"/>',
	)
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	sw = _stroke_width_of_first_path(svg_out)
	assert sw is not None and abs(sw - 2.0) < 1e-6


def test_stroke_width_scaled_by_uniform_flatten_style(tmp_path) -> None:
	"""An inline-style stroke-width is scaled by the baked uniform-scale matrix."""
	svg_in = tmp_path / "sws.svg"
	svg_out = tmp_path / "sws.out.svg"
	_write_svg(
		svg_in,
		'<rect x="0" y="0" width="20" height="20" transform="scale(2)" '
		'style="fill:#fff;stroke:#000;stroke-width:1.5"/>',
	)
	result = normalize_svg_v3.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	sw = _stroke_width_of_first_path(svg_out)
	# scale(2) doubles the stroke: 1.5 -> 3.0.
	assert sw is not None and abs(sw - 3.0) < 1e-6


#============================================
# Inline-style visibility excludes elements from the bbox
#============================================

def test_style_display_none_excluded_from_bbox() -> None:
	"""style="display:none" excludes an element from the geometry bbox."""
	body = '<rect style="display:none" x="200" y="200" width="50" height="50" fill="#000"/>'
	elem = normalize_svg_v3.lxml.etree.fromstring(
		f'<svg xmlns="{SVG_NS}">{body}</svg>'
	)[0]
	assert normalize_svg_v3._element_geometry_bbox(elem) is None


def test_style_fill_none_stroke_none_excluded_from_bbox() -> None:
	"""style="fill:none;stroke:none" excludes an element from the bbox."""
	body = '<rect style="fill:none;stroke:none" x="0" y="0" width="50" height="50"/>'
	elem = normalize_svg_v3.lxml.etree.fromstring(
		f'<svg xmlns="{SVG_NS}">{body}</svg>'
	)[0]
	assert normalize_svg_v3._element_geometry_bbox(elem) is None


def test_style_fill_none_with_stroke_contributes_bbox() -> None:
	"""style="fill:none" with a visible stroke still contributes geometry."""
	body = '<rect style="fill:none;stroke:#000" x="0" y="0" width="50" height="50"/>'
	elem = normalize_svg_v3.lxml.etree.fromstring(
		f'<svg xmlns="{SVG_NS}">{body}</svg>'
	)[0]
	bbox = normalize_svg_v3._element_geometry_bbox(elem)
	assert bbox is not None and bbox is not normalize_svg_v3._UNIT_SENTINEL
