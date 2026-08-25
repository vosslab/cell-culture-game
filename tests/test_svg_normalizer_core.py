"""Tests for the focused SVG normalizer modules."""

import pathlib
import lxml.etree
import tools.svg_normalizer.model
import tools.svg_normalizer.transform_geometry
import tools.svg_normalizer.transform_tree
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
# Inline bbox tests: relative path commands and viewBox assertions
#============================================

def test_relative_hv_commands_bbox(tmp_path: pathlib.Path) -> None:
	"""Relative h/v commands produce the same bbox as the absolute equivalent.

	A path using relative h (horizontal) and v (vertical) commands describing
	a 20x30 rectangle must normalize to the correct bbox dimensions, confirming
	that parse_path_to_absolute handles the relative-to-absolute conversion.
	"""
	svg_in = tmp_path / "rel_hv.svg"
	svg_out = tmp_path / "rel_hv.out.svg"
	# Mixed absolute start + relative h/v: draws a 20-wide, 30-tall rect at (10,10).
	_write_svg(svg_in, '<path d="M 10 10 h 20 v 30 h -20 z" fill="#000"/>')
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	bb = result.bbox
	# The rect must be exactly 20 wide and 30 tall.
	assert abs(bb.max_x - bb.min_x - 20.0) < 0.01
	assert abs(bb.max_y - bb.min_y - 30.0) < 0.01


def test_relative_l_commands_bbox(tmp_path: pathlib.Path) -> None:
	"""Relative l (lineto) command produces the same bbox as absolute L.

	A path using 'm' + relative 'l' commands to draw a triangle must have a
	bbox matching the triangle vertices, confirming relative lineto conversion.
	"""
	svg_in = tmp_path / "rel_l.svg"
	svg_out = tmp_path / "rel_l.out.svg"
	# Triangle: start (10,10), relative l 40,0 (to 50,10), l -20,30 (to 30,40), z.
	_write_svg(svg_in, '<path d="M 10 10 l 40 0 l -20 30 z" fill="#000"/>')
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	bb = result.bbox
	# width = 40, height = 30.
	assert abs(bb.max_x - bb.min_x - 40.0) < 0.01
	assert abs(bb.max_y - bb.min_y - 30.0) < 0.01


def test_relative_arc_command_captures_bulge(tmp_path: pathlib.Path) -> None:
	"""Relative arc command 'a' produces the same bbox as absolute 'A'.

	A relative arc from (0,0) sweeping 100 units right (same geometry as the
	absolute semicircle test) must include the arc bulge near y=50 in the bbox.
	"""
	svg_in = tmp_path / "rel_arc.svg"
	svg_out = tmp_path / "rel_arc.out.svg"
	# Relative arc: same semicircle geometry as test_path_bbox_contains_arc_bulge
	# but using lowercase 'a' (relative endpoint).
	_write_svg(svg_in, '<path d="M 0 0 a 50 50 0 0 0 100 0" fill="#000"/>')
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	bb = result.bbox
	# The semicircle bulges to y~50; an endpoint-only bbox would give max_y=0.
	assert bb.max_y > 40.0


def test_viewbox_includes_padding(tmp_path: pathlib.Path) -> None:
	"""The output viewBox starts at '0 0' and dimensions include the padding on each side.

	A 10x10 rect normalized with padding=2 must produce viewBox '0 0 14 14':
	content is 10 user units wide and tall, plus 2 units of padding on each side.
	"""
	svg_in = tmp_path / "vb.svg"
	svg_out = tmp_path / "vb.out.svg"
	_write_svg(svg_in, '<rect x="0" y="0" width="10" height="10" fill="#000"/>')
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=2.0)
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


def test_viewbox_zero_padding_tight_to_geometry(tmp_path: pathlib.Path) -> None:
	"""With padding=0 the output viewBox dimensions match the geometry exactly.

	A 50x20 rect normalized with no padding must produce a viewBox whose width
	is 50 and height is 20 (no extra margin).
	"""
	svg_in = tmp_path / "vb_tight.svg"
	svg_out = tmp_path / "vb_tight.out.svg"
	_write_svg(svg_in, '<rect x="5" y="5" width="50" height="20" fill="#000"/>')
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
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

def test_rect_percent_width_rejected(tmp_path: pathlib.Path) -> None:
	"""A rect with width='50%' must be rejected with UNSUPPORTED_UNIT.

	Percentage is not a user unit; silently stripping it would produce a phantom
	bbox (50.0 user units) instead of a reliable geometry measurement.
	"""
	svg_in = tmp_path / "rect_pct.svg"
	svg_out = tmp_path / "rect_pct.out.svg"
	_write_svg(svg_in, '<rect x="0" y="0" width="50%" height="40" fill="#000" />')
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert not result.normalized
	assert result.rejection.code == "UNSUPPORTED_UNIT"
	assert not svg_out.exists()


def test_rect_px_width_normalizes(tmp_path: pathlib.Path) -> None:
	"""A rect with width='50px' must normalize: px is a user-unit alias (1px == 1uu)."""
	svg_in = tmp_path / "rect_px.svg"
	svg_out = tmp_path / "rect_px.out.svg"
	_write_svg(svg_in, '<rect x="0" y="0" width="50px" height="40px" fill="#000" />')
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=2.0)
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
	xs, ys = tools.svg_normalizer.model.arc_extrema(0.0, 0.0, 50.0, 50.0, 0.0, 0, 0, 100.0, 0.0)
	max_y = max(ys)
	# The bulge at y=50 must be in the returned candidates.
	assert max_y > 40.0
	assert abs(max_y - 50.0) < 1e-6


def test_arc_extrema_semicircle_upward_bulge() -> None:
	"""Semicircle sweep=1 (CW) from (0,0) to (100,0) bulges upward to y=-50."""
	xs, ys = tools.svg_normalizer.model.arc_extrema(0.0, 0.0, 50.0, 50.0, 0.0, 0, 1, 100.0, 0.0)
	min_y = min(ys)
	# CW arc goes to y=-50 (upward in SVG coordinates).
	assert min_y < -40.0
	assert abs(min_y - (-50.0)) < 1e-6


def test_arc_extrema_degenerate_zero_radius() -> None:
	"""Zero radius arc returns only the two endpoint coordinates."""
	xs, ys = tools.svg_normalizer.model.arc_extrema(10.0, 20.0, 0.0, 0.0, 0.0, 0, 1, 30.0, 40.0)
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
	xs, ys = tools.svg_normalizer.model.arc_extrema(0.0, 0.0, 50.0, 50.0, 45.0, 0, 1, 0.0, 100.0)
	bbox_width = max(xs) - min(xs)
	# A rotated half-ellipse must be wider than its zero-width endpoint span.
	assert bbox_width > 30.0


#============================================
# path_bbox_from_segments round-trip
#============================================

def test_path_bbox_rectangle_absolute() -> None:
	"""Parse a simple absolute-command rectangle path and verify bbox round-trips."""
	d = "M 10 20 L 40 20 L 40 60 L 10 60 Z"
	segments = tools.svg_normalizer.model.parse_path_to_absolute(d)
	bbox = tools.svg_normalizer.model.path_bbox_from_segments(segments)
	assert bbox is not None
	assert abs(bbox.min_x - 10.0) < 1e-6
	assert abs(bbox.min_y - 20.0) < 1e-6
	assert abs(bbox.max_x - 40.0) < 1e-6
	assert abs(bbox.max_y - 60.0) < 1e-6


def test_path_bbox_contains_arc_bulge() -> None:
	"""path_bbox_from_segments for a path with an A command includes the arc bulge."""
	# Semicircle: arc goes from (0,0) to (100,0) sweeping downward to y=50.
	d = "M 0 0 A 50 50 0 0 0 100 0"
	segments = tools.svg_normalizer.model.parse_path_to_absolute(d)
	bbox = tools.svg_normalizer.model.path_bbox_from_segments(segments)
	assert bbox is not None
	# The bbox must extend to y=50, not stay at y=0 (the endpoint-only failure).
	assert bbox.max_y > 40.0


#============================================
# NormalizeResult contract
#============================================

def test_normalize_result_normalized_property(tmp_path: pathlib.Path) -> None:
	"""NormalizeResult.normalized is True when rejection is None."""
	svg_in = tmp_path / "simple.svg"
	svg_out = tmp_path / "simple.out.svg"
	_write_svg(svg_in, '<rect x="0" y="0" width="10" height="10" fill="#000" />')

	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert result.normalized
	assert result.rejection is None
	assert result.output_written


def test_rect_missing_width_yields_empty_geometry(tmp_path: pathlib.Path) -> None:
	"""A rect with no width attribute must not contribute a phantom zero-size bbox.

	When the only shape in an SVG is a rect missing its required width attribute,
	element_bbox must return None for it, so compute_bbox finds no drawable geometry
	and normalize_svg_file returns an EMPTY_GEOMETRY rejection.
	"""
	svg_in = tmp_path / "rect_no_width.svg"
	svg_out = tmp_path / "rect_no_width.out.svg"
	# rect missing width -- required attribute absent.
	_write_svg(svg_in, '<rect y="10" height="20" fill="#000" />')
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert not result.normalized
	assert result.rejection.code == "EMPTY_GEOMETRY"


def test_normalize_result_rejection_no_output(tmp_path: pathlib.Path) -> None:
	"""Rejected file leaves no output and output_written is False."""
	svg_in = tmp_path / "bad.svg"
	svg_out = tmp_path / "bad.out.svg"
	svg_in.write_text(
		'<svg xmlns="http://www.w3.org/2000/svg"><rect x="1"',
		encoding="utf-8",
	)

	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert not result.normalized
	assert not result.output_written
	assert not svg_out.exists()


#============================================
# Transform flattening unit tests
#============================================

def test_transform_arc_identity_preserves_radii() -> None:
	"""transformArc under the identity matrix leaves rx, ry, rotation, sweep unchanged."""
	rx, ry, rot, _large, sweep = tools.svg_normalizer.transform_geometry.transform_arc(
		0.0, 0.0, (50.0, 30.0, 0.0, 0.0, 1.0, 100.0, 0.0), tools.svg_normalizer.model.IDENTITY_MATRIX
	)
	assert abs(rx - 50.0) < 1e-6
	assert abs(ry - 30.0) < 1e-6
	assert abs(rot) < 1e-6
	assert sweep == 1.0


def test_transform_arc_uniform_scale_doubles_radii() -> None:
	"""A uniform scale(2) doubles both arc radii."""
	rx, ry, _rot, _large, _sweep = tools.svg_normalizer.transform_geometry.transform_arc(
		0.0, 0.0, (50.0, 30.0, 0.0, 0.0, 1.0, 100.0, 0.0), (2.0, 0.0, 0.0, 2.0, 0.0, 0.0)
	)
	assert abs(rx - 100.0) < 1e-6
	assert abs(ry - 60.0) < 1e-6


def test_transform_arc_single_axis_flip_inverts_sweep() -> None:
	"""A horizontal flip (det sign change) toggles the arc sweep flag."""
	_rx, _ry, _rot, _large, sweep = tools.svg_normalizer.transform_geometry.transform_arc(
		0.0, 0.0, (50.0, 30.0, 0.0, 0.0, 1.0, 100.0, 0.0), (-1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
	)
	# Sweep started at 1; a single-axis mirror flips it to 0.
	assert sweep == 0.0


def test_transform_arc_rotate_keeps_circle_circular() -> None:
	"""A circular arc stays circular (rx == ry) under a pure rotation."""
	rx, ry, _rot, _large, _sweep = tools.svg_normalizer.transform_geometry.transform_arc(
		0.0, 0.0, (50.0, 50.0, 0.0, 0.0, 1.0, 100.0, 0.0), (0.0, 1.0, -1.0, 0.0, 0.0, 0.0)
	)
	assert abs(rx - ry) < 1e-6
	assert abs(rx - 50.0) < 1e-6


def test_compose_translate_then_scale_point() -> None:
	"""Composing translate(10,10) then scale(2) maps a point through both, in order.

	transform="translate(10,10) scale(2)" applies scale to local coords first,
	then translate, so (5,5) -> (2*5+10, 2*5+10) = (20,20).
	"""
	items = tools.svg_normalizer.transform_geometry.parse_transform_list("translate(10,10) scale(2)", "/svg")
	matrix = tools.svg_normalizer.transform_geometry.transforms_multiply(items, "/svg")
	nx, ny = tools.svg_normalizer.transform_geometry.transform_point(matrix, 5.0, 5.0)
	assert abs(nx - 20.0) < 1e-6
	assert abs(ny - 20.0) < 1e-6


def test_apply_matrix_rotate90_to_path_segments() -> None:
	"""rotate(90) maps a path point (x,y) to (-y,x) after flattening."""
	segments = tools.svg_normalizer.model.parse_path_to_absolute("M 0 0 L 10 0")
	items = tools.svg_normalizer.transform_geometry.parse_transform_list("rotate(90)", "/svg")
	matrix = tools.svg_normalizer.transform_geometry.transforms_multiply(items, "/svg")
	flat = tools.svg_normalizer.transform_geometry.apply_matrix_to_segments(segments, matrix)
	bbox = tools.svg_normalizer.model.path_bbox_from_segments(flat)
	# (10,0) rotates to (0,10); (0,0) stays at origin.
	assert abs(bbox.min_x - 0.0) < 1e-6
	assert abs(bbox.max_x - 0.0) < 1e-6
	assert abs(bbox.max_y - 10.0) < 1e-6


def test_invariant_holds_after_flatten(tmp_path: pathlib.Path) -> None:
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
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	root = lxml.etree.parse(str(svg_out)).getroot()
	assert tools.svg_normalizer.transform_tree.find_geometry_transform_violation(root) is None


def test_gradient_transform_exempt_from_invariant(tmp_path: pathlib.Path) -> None:
	"""gradientTransform in defs is paint-space and must not trip the invariant."""
	svg_in = tmp_path / "grad.svg"
	svg_out = tmp_path / "grad.out.svg"
	_write_svg(
		svg_in,
		'<defs><linearGradient id="g" gradientTransform="rotate(45)">'
		'<stop offset="0" stop-color="#000"/></linearGradient></defs>'
		'<rect x="0" y="0" width="10" height="10" fill="url(#g)"/>',
	)
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	root = lxml.etree.parse(str(svg_out)).getroot()
	# gradientTransform must survive and not be flagged as a violation.
	assert tools.svg_normalizer.transform_tree.find_geometry_transform_violation(root) is None


def test_stroked_nonuniform_scale_rejected(tmp_path: pathlib.Path) -> None:
	"""A visible stroke under non-uniform scale is refused (UNSUPPORTED_TRANSFORM)."""
	svg_in = tmp_path / "stroked.svg"
	svg_out = tmp_path / "stroked.out.svg"
	_write_svg(
		svg_in,
		'<path d="M 0 0 L 10 0" transform="scale(2,3)" stroke="#000" stroke-width="1" fill="none"/>',
	)
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert not result.normalized
	assert result.rejection.code == "UNSUPPORTED_TRANSFORM"
	assert not svg_out.exists()


def test_stroked_uniform_scale_rotate_allowed(tmp_path: pathlib.Path) -> None:
	"""A visible stroke under uniform scale plus rotation flattens without distortion."""
	svg_in = tmp_path / "stroked_ok.svg"
	svg_out = tmp_path / "stroked_ok.out.svg"
	_write_svg(
		svg_in,
		'<path d="M 0 0 L 10 0" transform="rotate(45) scale(2)" stroke="#000" stroke-width="1" fill="none"/>',
	)
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"


def test_non_scaling_stroke_under_scale_rejected(tmp_path: pathlib.Path) -> None:
	"""vector-effect=non-scaling-stroke under a scaling transform is unresolved -> reject."""
	svg_in = tmp_path / "nss.svg"
	svg_out = tmp_path / "nss.out.svg"
	_write_svg(
		svg_in,
		'<path d="M 0 0 L 10 0" transform="scale(2)" stroke="#000" '
		'vector-effect="non-scaling-stroke"/>',
	)
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=2.0)
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
	root = lxml.etree.parse(str(svg_out_path)).getroot()
	shape_tags = {"rect", "circle", "ellipse", "line", "polyline", "polygon"}
	for elem in root.iter():
		if isinstance(elem.tag, str):
			tag = tools.svg_normalizer.model.local_name(elem.tag)
			if tag in shape_tags:
				return False
	return True


def test_shape_to_path_sharp_rect_bbox(tmp_path: pathlib.Path) -> None:
	"""Sharp rect converts to path; bbox matches declared x/y/width/height."""
	svg_in = tmp_path / "sharp_rect.svg"
	svg_out = tmp_path / "sharp_rect.out.svg"
	_write_svg(svg_in, '<rect x="10" y="20" width="60" height="40" fill="#000"/>')
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	# bbox must match the declared geometry of the rect
	bb = result.bbox
	assert abs(bb.max_x - bb.min_x - 60.0) < 0.01
	assert abs(bb.max_y - bb.min_y - 40.0) < 0.01


def test_shape_to_path_sharp_rect_tag(tmp_path: pathlib.Path) -> None:
	"""Sharp rect is rewritten as <path> in the normalized output."""
	svg_in = tmp_path / "sharp_rect_tag.svg"
	svg_out = tmp_path / "sharp_rect_tag.out.svg"
	_write_svg(svg_in, '<rect x="10" y="20" width="60" height="40" fill="#000"/>')
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized
	assert _output_has_no_raw_shapes(svg_out)


def test_shape_to_path_rounded_rect_rx_only_bbox(tmp_path: pathlib.Path) -> None:
	"""Rounded rect (rx only) converts to path; bbox equals outer rectangle.

	rx is specified but ry is absent; per SVG spec ry defaults to rx.
	The arc corners stay within the outer bbox so the path bbox == (x,y,x+w,y+h).
	"""
	svg_in = tmp_path / "rrect_rx.svg"
	svg_out = tmp_path / "rrect_rx.out.svg"
	_write_svg(svg_in, '<rect x="0" y="0" width="60" height="40" rx="10" fill="#000"/>')
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	bb = result.bbox
	assert abs(bb.max_x - bb.min_x - 60.0) < 0.01
	assert abs(bb.max_y - bb.min_y - 40.0) < 0.01


def test_shape_to_path_rounded_rect_rx_and_ry_bbox(tmp_path: pathlib.Path) -> None:
	"""Rounded rect (rx=8 ry=5) converts to path; bbox equals outer rectangle."""
	svg_in = tmp_path / "rrect_rxry.svg"
	svg_out = tmp_path / "rrect_rxry.out.svg"
	_write_svg(svg_in, '<rect x="10" y="5" width="40" height="30" rx="8" ry="5" fill="#000"/>')
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	bb = result.bbox
	assert abs(bb.max_x - bb.min_x - 40.0) < 0.01
	assert abs(bb.max_y - bb.min_y - 30.0) < 0.01


def test_shape_to_path_rounded_rect_tag(tmp_path: pathlib.Path) -> None:
	"""Rounded rect is rewritten as <path> with no residual rect element."""
	svg_in = tmp_path / "rrect_tag.svg"
	svg_out = tmp_path / "rrect_tag.out.svg"
	_write_svg(svg_in, '<rect x="0" y="0" width="60" height="40" rx="10" fill="#000"/>')
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized
	assert _output_has_no_raw_shapes(svg_out)


def test_shape_to_path_circle_bbox(tmp_path: pathlib.Path) -> None:
	"""Circle converts to two-arc path; bbox matches (cx-r, cy-r, cx+r, cy+r)."""
	svg_in = tmp_path / "circle.svg"
	svg_out = tmp_path / "circle.out.svg"
	_write_svg(svg_in, '<circle cx="50" cy="50" r="30" fill="#333"/>')
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	bb = result.bbox
	# circle bbox width and height must both equal 2*r = 60
	assert abs(bb.max_x - bb.min_x - 60.0) < 0.01
	assert abs(bb.max_y - bb.min_y - 60.0) < 0.01


def test_shape_to_path_circle_tag(tmp_path: pathlib.Path) -> None:
	"""Circle is rewritten as <path> in the normalized output."""
	svg_in = tmp_path / "circle_tag.svg"
	svg_out = tmp_path / "circle_tag.out.svg"
	_write_svg(svg_in, '<circle cx="50" cy="50" r="30" fill="#333"/>')
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized
	assert _output_has_no_raw_shapes(svg_out)


def test_shape_to_path_ellipse_bbox(tmp_path: pathlib.Path) -> None:
	"""Ellipse converts to two-arc path; bbox matches (cx-rx, cy-ry, cx+rx, cy+ry)."""
	svg_in = tmp_path / "ellipse.svg"
	svg_out = tmp_path / "ellipse.out.svg"
	_write_svg(svg_in, '<ellipse cx="30" cy="40" rx="20" ry="10" fill="#555"/>')
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	bb = result.bbox
	# ellipse bbox: width = 2*rx = 40, height = 2*ry = 20
	assert abs(bb.max_x - bb.min_x - 40.0) < 0.01
	assert abs(bb.max_y - bb.min_y - 20.0) < 0.01


def test_shape_to_path_ellipse_tag(tmp_path: pathlib.Path) -> None:
	"""Ellipse is rewritten as <path> in the normalized output."""
	svg_in = tmp_path / "ellipse_tag.svg"
	svg_out = tmp_path / "ellipse_tag.out.svg"
	_write_svg(svg_in, '<ellipse cx="30" cy="40" rx="20" ry="10" fill="#555"/>')
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized
	assert _output_has_no_raw_shapes(svg_out)


def test_shape_to_path_line_bbox(tmp_path: pathlib.Path) -> None:
	"""Line converts to M/L path; bbox includes stroke pad (A3: stroke-width=1 -> pad=2).

	With stroke-width=1 and default miterlimit=4: pad = 1/2 * 4 = 2.
	Geometry spans 75 wide and 50 tall; stroke-padded spans 79 wide and 54 tall.
	"""
	svg_in = tmp_path / "line.svg"
	svg_out = tmp_path / "line.out.svg"
	_write_svg(svg_in, '<line x1="5" y1="10" x2="80" y2="60" stroke="#000" stroke-width="1"/>')
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	bb = result.bbox
	# Geometry width 75 + 2*pad(2) = 79; geometry height 50 + 2*pad(2) = 54.
	assert abs(bb.max_x - bb.min_x - 79.0) < 0.01
	assert abs(bb.max_y - bb.min_y - 54.0) < 0.01


def test_shape_to_path_line_tag(tmp_path: pathlib.Path) -> None:
	"""Line is rewritten as <path> in the normalized output."""
	svg_in = tmp_path / "line_tag.svg"
	svg_out = tmp_path / "line_tag.out.svg"
	_write_svg(svg_in, '<line x1="5" y1="10" x2="80" y2="60" stroke="#000" stroke-width="1"/>')
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized
	assert _output_has_no_raw_shapes(svg_out)


def test_shape_to_path_polyline_bbox(tmp_path: pathlib.Path) -> None:
	"""Polyline converts to M/L/L path; bbox includes stroke pad (A3).

	stroke="#000" with no stroke-width -> default stroke-width=1; pad = 1/2*4 = 2.
	Geometry spans 100 wide and 20 tall; stroke-padded spans 104 wide and 24 tall.
	"""
	svg_in = tmp_path / "polyline.svg"
	svg_out = tmp_path / "polyline.out.svg"
	_write_svg(svg_in, '<polyline points="0,0 50,20 100,0" fill="none" stroke="#000"/>')
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	bb = result.bbox
	# Geometry width 100 + 2*pad(2) = 104; geometry height 20 + 2*pad(2) = 24.
	assert abs(bb.max_x - bb.min_x - 104.0) < 0.01
	assert abs(bb.max_y - bb.min_y - 24.0) < 0.01


def test_shape_to_path_polyline_tag(tmp_path: pathlib.Path) -> None:
	"""Polyline is rewritten as <path> in the normalized output."""
	svg_in = tmp_path / "polyline_tag.svg"
	svg_out = tmp_path / "polyline_tag.out.svg"
	_write_svg(svg_in, '<polyline points="0,0 50,20 100,0" fill="none" stroke="#000"/>')
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized
	assert _output_has_no_raw_shapes(svg_out)


def test_shape_to_path_polygon_bbox(tmp_path: pathlib.Path) -> None:
	"""Polygon converts to M/L/L/Z path; bbox spans all vertices."""
	svg_in = tmp_path / "polygon.svg"
	svg_out = tmp_path / "polygon.out.svg"
	_write_svg(svg_in, '<polygon points="10,10 90,10 50,80" fill="#222"/>')
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	bb = result.bbox
	# width = 80, height = 70
	assert abs(bb.max_x - bb.min_x - 80.0) < 0.01
	assert abs(bb.max_y - bb.min_y - 70.0) < 0.01


def test_shape_to_path_polygon_tag(tmp_path: pathlib.Path) -> None:
	"""Polygon is rewritten as <path> in the normalized output."""
	svg_in = tmp_path / "polygon_tag.svg"
	svg_out = tmp_path / "polygon_tag.out.svg"
	_write_svg(svg_in, '<polygon points="10,10 90,10 50,80" fill="#222"/>')
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized
	assert _output_has_no_raw_shapes(svg_out)


def test_shape_to_path_preserves_id_and_paint_ref(tmp_path: pathlib.Path) -> None:
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
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	root = lxml.etree.parse(str(svg_out)).getroot()
	# Find the converted path (by id); it must carry the fill paint reference.
	found = root.find(f".//{{{SVG_NS}}}path[@id='mycirc']")
	assert found is not None, "converted path missing id='mycirc'"
	assert found.get("fill") == "url(#g1)", "fill ref not preserved on converted path"


def test_shape_to_path_invariant_still_holds(tmp_path: pathlib.Path) -> None:
	"""After shape->path the canonical invariant still holds: no geometry transform remains."""
	svg_in = tmp_path / "inv.svg"
	svg_out = tmp_path / "inv.out.svg"
	_write_svg(
		svg_in,
		'<g transform="translate(5,5)">'
		'<circle cx="20" cy="20" r="10" fill="#000"/>'
		'</g>',
	)
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	root = lxml.etree.parse(str(svg_out)).getroot()
	assert tools.svg_normalizer.transform_tree.find_geometry_transform_violation(root) is None


def test_rounded_rect_radii_clamped_to_half_side(tmp_path: pathlib.Path) -> None:
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
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	bb = result.bbox
	assert abs(bb.max_x - bb.min_x - 20.0) < 0.01
	assert abs(bb.max_y - bb.min_y - 20.0) < 0.01


#============================================
# Stroke pad, text reject, and precision round-trip tests
#============================================

def test_stroke_pad_thick_path_bbox_larger_than_geometry(tmp_path: pathlib.Path) -> None:
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
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	bb = result.bbox
	geom_height = 0.0  # horizontal line: no geometry height
	# Padded height must be larger than bare geometry by at least stroke_width/2.
	padded_height = bb.max_y - bb.min_y
	assert padded_height > geom_height + 1.0


def test_stroke_pad_miter_join_uses_miterlimit(tmp_path: pathlib.Path) -> None:
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
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	padded_height = result.bbox.max_y - result.bbox.min_y
	# pad = 4/2*max(1,6) = 12 on each side -> total height >= 24.
	assert padded_height >= 23.9


def test_stroke_pad_round_linecap_open_path(tmp_path: pathlib.Path) -> None:
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
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	round_height = result.bbox.max_y - result.bbox.min_y
	# pad = 8/2*max(1,4) + 8/2 = 16 + 4 = 20 per side -> total height = 40.
	assert round_height >= 39.9


def test_stroke_pad_butt_linecap_no_endpoint_extra(tmp_path: pathlib.Path) -> None:
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
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
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
	round_result = tools.svg_normalizer.workflow.normalize_svg_file(round_svg_in, round_svg_out, padding=0.0)
	assert round_result.normalized
	round_height = round_result.bbox.max_y - round_result.bbox.min_y
	# round/square adds stroke_width (8) to total height vs butt.
	assert round_height >= butt_height + 8 - 0.1


def test_stroke_none_no_pad(tmp_path: pathlib.Path) -> None:
	"""stroke=none element must not be padded; bbox equals geometry bbox."""
	svg_in = tmp_path / "nostroke.svg"
	svg_out = tmp_path / "nostroke.out.svg"
	_write_svg(
		svg_in,
		'<rect x="10" y="10" width="80" height="60" fill="#333" stroke="none"/>',
	)
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	bb = result.bbox
	# Geometry only: no stroke pad applied.
	assert abs(bb.max_x - bb.min_x - 80.0) < 0.01
	assert abs(bb.max_y - bb.min_y - 60.0) < 0.01


#============================================
# Text reject tests
#============================================

def test_text_element_rejected(tmp_path: pathlib.Path) -> None:
	"""An SVG containing a <text> element is rejected with TEXT_UNSUPPORTED.

	v3 cannot compute text glyph geometry. Prose belongs in layout-manager DOM or
	object data; only approved intrinsic markings may be outlined before ingestion.
	"""
	svg_in = tmp_path / "text.svg"
	svg_out = tmp_path / "text.out.svg"
	_write_svg(svg_in, '<rect x="0" y="0" width="100" height="100" fill="#000"/>'
		'<text x="10" y="50">Hello</text>')
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert not result.normalized
	assert result.rejection.code == "TEXT_UNSUPPORTED"
	assert not svg_out.exists()


def test_tspan_element_rejected(tmp_path: pathlib.Path) -> None:
	"""An SVG with a <tspan> inside <text> is rejected with TEXT_UNSUPPORTED."""
	svg_in = tmp_path / "tspan.svg"
	svg_out = tmp_path / "tspan.out.svg"
	_write_svg(
		svg_in,
		'<text x="10" y="50"><tspan>Hi</tspan></text>',
	)
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert not result.normalized
	assert result.rejection.code == "TEXT_UNSUPPORTED"
	assert not svg_out.exists()


def test_text_rejection_element_location(tmp_path: pathlib.Path) -> None:
	"""TEXT_UNSUPPORTED rejection includes an XPath-like element location."""
	svg_in = tmp_path / "textloc.svg"
	svg_out = tmp_path / "textloc.out.svg"
	_write_svg(svg_in, '<text x="5" y="20">Label</text>')
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert not result.normalized
	assert result.rejection.code == "TEXT_UNSUPPORTED"
	# The element field should be non-empty for a locatable element.
	assert result.rejection.element != ""


#============================================
# Precision and round-trip determinism tests
#============================================

def test_precision_fmt_precise_leading_zero_strip() -> None:
	"""fmt_precise strips the leading zero from 0.5 -> .5 and -0.5 -> -.5."""
	assert tools.svg_normalizer.model.fmt_precise(0.5) == ".5"
	assert tools.svg_normalizer.model.fmt_precise(-0.5) == "-.5"


def test_precision_fmt_precise_integer_strips_trailing_zeros() -> None:
	"""fmt_precise emits integers without decimal point: 10.0 -> '10'."""
	result = tools.svg_normalizer.model.fmt_precise(10.0)
	assert "." not in result
	assert result == "10"


def test_precision_fmt_precise_zero() -> None:
	"""fmt_precise returns '0' for values very close to zero."""
	result = tools.svg_normalizer.model.fmt_precise(0.0)
	assert result == "0"
	result2 = tools.svg_normalizer.model.fmt_precise(1e-12)
	assert result2 == "0"


def test_precision_normalize_twice_identical(tmp_path: pathlib.Path) -> None:
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
	result1 = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out1, padding=2.0)
	assert result1.normalized, f"unexpected rejection: {result1.rejection}"
	# Second normalization: input is the already-normalized output.
	result2 = tools.svg_normalizer.workflow.normalize_svg_file(svg_out1, svg_out2, padding=2.0)
	assert result2.normalized, f"second-pass rejection: {result2.rejection}"
	content1 = svg_out1.read_text(encoding="utf-8")
	content2 = svg_out2.read_text(encoding="utf-8")
	# The path d attribute content must be identical across passes.
	# (viewBox may shift on second pass due to padding; we only require
	# the coordinate content to be stable.)
	assert content1 == content2, "second normalization produced different output"

