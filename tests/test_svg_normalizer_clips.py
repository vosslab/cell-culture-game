"""Tests for the focused SVG normalizer modules."""

import pathlib
import lxml.etree
import pytest
import re
import tools.svg_normalizer.cli
import tools.svg_normalizer.clips
import tools.svg_normalizer.geometry
import tools.svg_normalizer.model
import tools.svg_normalizer.transform_geometry
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


def _parse_svg_root(svg_text: str) -> lxml.etree._Element:
	"""Parse SVG text into a root element for direct clip transforms."""
	return lxml.etree.fromstring(svg_text.encode("utf-8"))


# Simple-clipPath flattening behavior tests
#============================================

def _normalize_clip(
	tmp_path: pathlib.Path,
	body: str,
	padding: float = 0.0,
) -> tuple[tools.svg_normalizer.model.NormalizeResult, str]:
	"""Helper: wrap body in an <svg>, normalize, and return (result, output text)."""
	svg_in = tmp_path / "clip_in.svg"
	svg_out = tmp_path / "clip_out.svg"
	_write_svg(svg_in, body)
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=padding)
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
def _rect_or_path_geometry_bbox(elem: lxml.etree._Element) -> tools.svg_normalizer.model.BBox:
	"""Return geometry bbox for a retained clip child in either supported form."""
	tag = tools.svg_normalizer.model.local_name(elem.tag)
	if tag == "path":
		d_attr = elem.get("d")
		assert d_attr is not None
		bbox = tools.svg_normalizer.model.path_bbox_from_segments(
			tools.svg_normalizer.model.parse_path_to_absolute(d_attr)
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
	return tools.svg_normalizer.model.BBox(x, y, x + float(width_attr), y + float(height_attr))


def test_clip_flatten_drops_clip_ref_and_def(tmp_path: pathlib.Path) -> None:
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


def test_clip_flatten_simple_not_rejected_by_classify(tmp_path: pathlib.Path) -> None:
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


def test_clip_flatten_multipolygon_with_hole(tmp_path: pathlib.Path) -> None:
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


def test_clip_flatten_complex_nested_rejected(tmp_path: pathlib.Path) -> None:
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
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	assert result.bbox is not None
	assert abs(result.bbox.width - 30.0) < 1e-9
	assert abs(result.bbox.height - 20.0) < 1e-9
	assert result.view_box is not None
	view_box_parts = result.view_box.split()
	assert abs(float(view_box_parts[2]) - 30.0) < 1e-9
	assert abs(float(view_box_parts[3]) - 20.0) < 1e-9

	root = lxml.etree.parse(str(svg_out)).getroot()
	clip = _element_with_id(root, "anchor_liquid_clip")
	assert clip is not None
	assert _element_with_id(root, "unused_clip") is None
	clip_child = next(
		child
		for child in clip
		if tools.svg_normalizer.model.local_name(child.tag) in {"path", "rect"}
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
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	root = lxml.etree.parse(str(svg_out)).getroot()
	anchor = _element_with_id(root, "anchor_liquid_bounds")
	assert anchor is not None and tools.svg_normalizer.model.local_name(anchor.tag) == "rect"
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
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"

	root = lxml.etree.parse(str(svg_out)).getroot()
	clip = _element_with_id(root, "anchor_liquid_clip")
	assert clip is not None
	clip_child = next(
		child
		for child in clip
		if tools.svg_normalizer.model.local_name(child.tag) in {"path", "rect"}
	)
	clip_bbox = _rect_or_path_geometry_bbox(clip_child)
	anchor_bounds = _element_with_id(root, "anchor_liquid_bounds")
	assert anchor_bounds is not None
	assert tools.svg_normalizer.model.local_name(anchor_bounds.tag) == "rect"
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
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
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
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
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
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
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
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
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
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.rejection is not None and result.rejection.code == "UNRESOLVED_REFERENCE"
	assert not svg_out.exists()


#============================================
# Rank 1 no-op clip elimination behavior tests
#============================================

def _clip_target_path(root: lxml.etree._Element) -> lxml.etree._Element:
	"""Return the single drawable <path> target (the one element with id 't')."""
	for elem in root.iter():
		if isinstance(elem.tag, str) and tools.svg_normalizer.model.local_name(elem.tag) == "path":
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
	tools.svg_normalizer.clips.flatten_clip_paths(root)
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
	with pytest.raises(tools.svg_normalizer.transform_geometry.ComplexClipError):
		tools.svg_normalizer.clips.flatten_clip_paths(root)


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
	tools.svg_normalizer.clips.flatten_clip_paths(root)
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
	tools.svg_normalizer.clips.flatten_clip_paths(root)
	target = _clip_target_path(root)
	assert target.get("clip-path") is None
	new_d = target.get("d")
	assert new_d != original_d, "a genuine clip must re-emit the intersected geometry"
	# The intersection is bounded by the clip at x<=45.
	bbox = tools.svg_normalizer.model.path_bbox_from_segments(
		tools.svg_normalizer.model.parse_path_to_absolute(new_d)
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
	tools.svg_normalizer.clips.flatten_clip_paths(root)
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
	with pytest.raises(tools.svg_normalizer.transform_geometry.ComplexClipError):
		tools.svg_normalizer.clips.flatten_clip_paths(root)


#============================================
# Fix B: userSpaceOnUse paint moves in sync with flattened geometry
#============================================

def _gradient_transform_of(svg_out: pathlib.Path, grad_id: str) -> str | None:
	"""Return the gradientTransform attr of the named gradient in output, or None."""
	root = lxml.etree.parse(str(svg_out)).getroot()
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		if tools.svg_normalizer.model.local_name(elem.tag) != "linearGradient":
			continue
		if elem.get("id") == grad_id:
			return elem.get("gradientTransform")
	return None


def _linear_gradient_effective_endpoints(
	svg_out: pathlib.Path,
	grad_id: str,
) -> tuple[tuple[float, float], tuple[float, float]]:
	"""Return the two effective endpoints of a userSpaceOnUse linearGradient.

	The browser resolves a userSpaceOnUse gradient's (x1,y1)/(x2,y2) THROUGH its
	gradientTransform in the painted element's current user space. After flattening
	the painted element has no transform, so its user space is the root space and
	the effective endpoints are gradientTransform * (x1,y1) and * (x2,y2). These are
	the render-meaningful coordinates that must land on the painted geometry.
	"""
	root = lxml.etree.parse(str(svg_out)).getroot()
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
		matrix = tools.svg_normalizer.transform_geometry.transforms_multiply(
			tools.svg_normalizer.transform_geometry.parse_transform_list(gt, "/test"), "/test"
		)
	else:
		matrix = tools.svg_normalizer.model.IDENTITY_MATRIX
	p1 = tools.svg_normalizer.transform_geometry.transform_point(matrix, x1, y1)
	p2 = tools.svg_normalizer.transform_geometry.transform_point(matrix, x2, y2)
	return p1, p2


def _first_path_bbox(svg_out: pathlib.Path) -> tools.svg_normalizer.model.BBox:
	"""Return the BBox of the first <path> in the output (the flattened geometry)."""
	root = lxml.etree.parse(str(svg_out)).getroot()
	for elem in root.iter():
		if isinstance(elem.tag, str) and tools.svg_normalizer.model.local_name(elem.tag) == "path":
			segs = tools.svg_normalizer.model.parse_path_to_absolute(elem.get("d"))
			bbox = tools.svg_normalizer.model.path_bbox_from_segments(segs)
			assert bbox is not None
			return bbox
	raise AssertionError("no path found in output")


def test_userspace_gradient_single_use_lands_on_flattened_geometry(tmp_path: pathlib.Path) -> None:
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
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	p1, p2 = _linear_gradient_effective_endpoints(svg_out, "g")
	bbox = _first_path_bbox(svg_out)
	# Gradient start coincides with the path bbox min corner, end with the max corner.
	assert abs(p1[0] - bbox.min_x) < 1e-6 and abs(p1[1] - bbox.min_y) < 1e-6
	assert abs(p2[0] - bbox.max_x) < 1e-6 and abs(p2[1] - bbox.max_y) < 1e-6


def test_userspace_gradient_shared_diff_transform_rejected(tmp_path: pathlib.Path) -> None:
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
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert not result.normalized
	assert result.rejection.code == "UNSUPPORTED_TRANSFORM"
	assert not svg_out.exists()


def test_objectboundingbox_gradient_under_transform_unchanged(tmp_path: pathlib.Path) -> None:
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
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=2.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	# Default gradientUnits is objectBoundingBox; the gradient must not gain a
	# gradientTransform from the geometry flatten.
	assert _gradient_transform_of(svg_out, "g") is None
	# objectBoundingBox coords are 0..1 fractions and crop-invariant; the crop shift
	# must NOT be added to them (the earlier shift_element bug shifted every cx/x1).
	root = lxml.etree.parse(str(svg_out)).getroot()
	grad = next(e for e in root.iter() if e.get("id") == "g")
	assert grad.get("x1") == "0" and grad.get("x2") == "1"


def test_userspace_gradient_crop_shift_tracks_geometry(tmp_path: pathlib.Path) -> None:
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
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	p1, p2 = _linear_gradient_effective_endpoints(svg_out, "g")
	bbox = _first_path_bbox(svg_out)
	# After crop-to-origin the square sits at (0,0)-(10,10); the gradient spanned it
	# corner-to-corner and must still do so.
	assert abs(p1[0] - bbox.min_x) < 1e-6 and abs(p1[1] - bbox.min_y) < 1e-6
	assert abs(p2[0] - bbox.max_x) < 1e-6 and abs(p2[1] - bbox.max_y) < 1e-6
	assert abs(bbox.min_x) < 1e-6 and abs(bbox.min_y) < 1e-6


def test_userspace_gradient_existing_transform_stays_aligned(tmp_path: pathlib.Path) -> None:
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
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	p1, p2 = _linear_gradient_effective_endpoints(svg_out, "g")
	# Original on-screen effective endpoints: M * E * coords, with M=scale(2),
	# E=translate(10,20). The geometry bbox is (0,0)-(20,20) so crop shift is zero
	# at padding=0; the effective endpoints must therefore be preserved exactly.
	m_e = tools.svg_normalizer.transform_geometry.multiply_matrices(
		(2.0, 0.0, 0.0, 2.0, 0.0, 0.0),
		tools.svg_normalizer.transform_geometry.transforms_multiply(
			tools.svg_normalizer.transform_geometry.parse_transform_list("translate(10,20)", "/test"), "/test"
		),
	)
	exp1 = tools.svg_normalizer.transform_geometry.transform_point(m_e, 0.0, 0.0)
	exp2 = tools.svg_normalizer.transform_geometry.transform_point(m_e, 10.0, 10.0)
	assert abs(p1[0] - exp1[0]) < 1e-6 and abs(p1[1] - exp1[1]) < 1e-6
	assert abs(p2[0] - exp2[0]) < 1e-6 and abs(p2[1] - exp2[1]) < 1e-6


#============================================
# Stroke-width scaling under transform flatten
#============================================

def _stroke_width_of_first_path(svg_out: pathlib.Path) -> float | None:
	"""Return the effective stroke-width of the first path (attr or inline style)."""
	root = lxml.etree.parse(str(svg_out)).getroot()
	for elem in root.iter():
		if not (isinstance(elem.tag, str) and tools.svg_normalizer.model.local_name(elem.tag) == "path"):
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


def test_stroke_width_scaled_by_uniform_flatten_attr(tmp_path: pathlib.Path) -> None:
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
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	sw = _stroke_width_of_first_path(svg_out)
	assert sw is not None and abs(sw - 2.0) < 1e-6


def test_stroke_width_scaled_by_uniform_flatten_style(tmp_path: pathlib.Path) -> None:
	"""An inline-style stroke-width is scaled by the baked uniform-scale matrix."""
	svg_in = tmp_path / "sws.svg"
	svg_out = tmp_path / "sws.out.svg"
	_write_svg(
		svg_in,
		'<rect x="0" y="0" width="20" height="20" transform="scale(2)" '
		'style="fill:#fff;stroke:#000;stroke-width:1.5"/>',
	)
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
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
	elem = lxml.etree.fromstring(
		f'<svg xmlns="{SVG_NS}">{body}</svg>'
	)[0]
	assert tools.svg_normalizer.geometry._element_geometry_bbox(elem) is None


def test_style_fill_none_stroke_none_excluded_from_bbox() -> None:
	"""style="fill:none;stroke:none" excludes an element from the bbox."""
	body = '<rect style="fill:none;stroke:none" x="0" y="0" width="50" height="50"/>'
	elem = lxml.etree.fromstring(
		f'<svg xmlns="{SVG_NS}">{body}</svg>'
	)[0]
	assert tools.svg_normalizer.geometry._element_geometry_bbox(elem) is None


def test_style_fill_none_with_stroke_contributes_bbox() -> None:
	"""style="fill:none" with a visible stroke still contributes geometry."""
	body = '<rect style="fill:none;stroke:#000" x="0" y="0" width="50" height="50"/>'
	elem = lxml.etree.fromstring(
		f'<svg xmlns="{SVG_NS}">{body}</svg>'
	)[0]
	bbox = tools.svg_normalizer.geometry._element_geometry_bbox(elem)
	assert bbox is not None and bbox is not tools.svg_normalizer.model._UNIT_SENTINEL
