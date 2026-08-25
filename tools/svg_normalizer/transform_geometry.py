"""Flatten supported SVG geometry transforms without changing their meaning."""

import math
import re

import lxml.etree

import tools.svg_normalizer.model


class UnsupportedTransformError(Exception):
	"""Raised when a transform attribute names a function v3 cannot flatten.

	Carries the element location string for the rejection report so the caller
	can emit an UNSUPPORTED_TRANSFORM rejection rather than guessing geometry.
	"""
	def __init__(self, element_location: str, detail: str) -> None:
		super().__init__(f"Unsupported transform at {element_location}: {detail}")
		self.element_location = element_location
		self.detail = detail


#============================================
class NonScalingStrokeError(Exception):
	"""Raised when a non-scaling-stroke element cannot be safely flattened.

	Non-scaling stroke geometry under a transform is not resolved, so an
	element carrying vector-effect=non-scaling-stroke together with a transform
	that actually changes stroke width is refused (NONSCALING_STROKE_UNRESOLVED)
	rather than emitting wrong geometry.
	"""
	def __init__(self, element_location: str) -> None:
		super().__init__(f"Unresolvable non-scaling stroke at {element_location}")
		self.element_location = element_location


#============================================
class ComplexClipError(Exception):
	"""Raised when a clip-path usage falls outside the simple-clip allowlist (A6).

	The clip-flattening pass (flatten_clip_paths) raises this for any clip it
	cannot safely flatten with shapely. normalize_svg_file turns it into a
	CLIPPATH_UNSUPPORTED_COMPLEX rejection with no output. The detail string
	records which allowlist rule failed (for the rejection message); the location
	is the offending clipped element or clipPath.
	"""
	def __init__(self, element_location: str, detail: str) -> None:
		super().__init__(f"Complex clipPath at {element_location}: {detail}")
		self.element_location = element_location
		self.detail = detail


#============================================
def parse_transform_list(transform_str: str, element_location: str) -> list[tuple[str, tuple[float, ...]]]:
	"""Parse a transform attribute into an ordered list of (name, args).

	Ported from svgo transform2js. The transform list is applied left to right
	(outermost first), matching SVG semantics: transform="A B" means apply B to
	the local coordinates, then A.

	Args:
		transform_str: The raw transform attribute value.
		element_location: XPath-like location for error reporting.

	Returns:
		Ordered list of (function-name, numeric-args) tuples.

	Raises:
		UnsupportedTransformError: When the string contains a function v3 does
			not support, or args do not match the function arity.
	"""
	items: list[tuple[str, tuple[float, ...]]] = []
	# Reject any non-whitespace residue that the split regex did not consume; a
	# stray token means an unsupported function (e.g. a CSS transform) is present.
	consumed = tools.svg_normalizer.model._TRANSFORM_SPLIT_RE.sub(" ", transform_str)
	if consumed.strip() != "":
		raise UnsupportedTransformError(element_location, f"unparseable transform {transform_str!r}")
	for match in tools.svg_normalizer.model._TRANSFORM_SPLIT_RE.finditer(transform_str):
		name = match.group(1)
		args = tuple(float(n) for n in tools.svg_normalizer.model._TRANSFORM_NUM_RE.findall(match.group(2)))
		if name not in tools.svg_normalizer.model._TRANSFORM_NAMES:
			raise UnsupportedTransformError(element_location, f"unsupported function {name}")
		items.append((name, args))
	return items


#============================================
def transform_to_matrix(name: str, args: tuple[float, ...], element_location: str) -> tuple[float, ...]:
	"""Convert a single transform function to a 6-tuple matrix [a,b,c,d,e,f].

	Ported from svgo transformToMatrix. Handles translate/scale/rotate (with
	optional cx,cy)/skewX/skewY/matrix.

	Args:
		name: Transform function name.
		args: Numeric arguments as authored.
		element_location: XPath-like location for error reporting.

	Returns:
		The 6-tuple affine matrix.

	Raises:
		UnsupportedTransformError: When argument count is invalid for the function.
	"""
	if name == "matrix":
		if len(args) != 6:
			raise UnsupportedTransformError(element_location, "matrix() needs 6 args")
		return tuple(args)
	if name == "translate":
		# translate(tx [ty]); ty defaults to 0.
		if len(args) not in (1, 2):
			raise UnsupportedTransformError(element_location, "translate() needs 1 or 2 args")
		tx = args[0]
		ty = args[1] if len(args) == 2 else 0.0
		return (1.0, 0.0, 0.0, 1.0, tx, ty)
	if name == "scale":
		# scale(sx [sy]); sy defaults to sx.
		if len(args) not in (1, 2):
			raise UnsupportedTransformError(element_location, "scale() needs 1 or 2 args")
		sx = args[0]
		sy = args[1] if len(args) == 2 else sx
		return (sx, 0.0, 0.0, sy, 0.0, 0.0)
	if name == "rotate":
		# rotate(angle [cx cy]); rotation about (cx,cy) defaults to origin.
		if len(args) not in (1, 3):
			raise UnsupportedTransformError(element_location, "rotate() needs 1 or 3 args")
		angle = math.radians(args[0])
		cos = math.cos(angle)
		sin = math.sin(angle)
		cx = args[1] if len(args) == 3 else 0.0
		cy = args[2] if len(args) == 3 else 0.0
		# rotate(a,cx,cy) == translate(cx,cy) rotate(a) translate(-cx,-cy).
		e = (1.0 - cos) * cx + sin * cy
		f = (1.0 - cos) * cy - sin * cx
		return (cos, sin, -sin, cos, e, f)
	if name == "skewX":
		if len(args) != 1:
			raise UnsupportedTransformError(element_location, "skewX() needs 1 arg")
		return (1.0, 0.0, math.tan(math.radians(args[0])), 1.0, 0.0, 0.0)
	if name == "skewY":
		if len(args) != 1:
			raise UnsupportedTransformError(element_location, "skewY() needs 1 arg")
		return (1.0, math.tan(math.radians(args[0])), 0.0, 1.0, 0.0, 0.0)
	raise UnsupportedTransformError(element_location, f"unsupported function {name}")


#============================================
def multiply_matrices(a: tuple[float, ...], b: tuple[float, ...]) -> tuple[float, ...]:
	"""Multiply two affine matrices (a then b applied as a*b on column vectors).

	Ported from svgo multiplyTransformMatrices. The result transforms a point by
	first b, then a (standard matrix product), so feeding a left-to-right
	transform list through reduce gives the correct composed transform.

	Args:
		a: Left 6-tuple matrix.
		b: Right 6-tuple matrix.

	Returns:
		The composed 6-tuple matrix.
	"""
	result = (
		a[0] * b[0] + a[2] * b[1],
		a[1] * b[0] + a[3] * b[1],
		a[0] * b[2] + a[2] * b[3],
		a[1] * b[2] + a[3] * b[3],
		a[0] * b[4] + a[2] * b[5] + a[4],
		a[1] * b[4] + a[3] * b[5] + a[5],
	)
	return result


#============================================
def transforms_multiply(items: list[tuple[str, tuple[float, ...]]], element_location: str) -> tuple[float, ...]:
	"""Compose an ordered transform list into a single matrix.

	Ported from svgo transformsMultiply. Each item is converted to a matrix and
	the matrices are multiplied left to right (outermost-to-element order), which
	is the order SVG applies a transform="A B C" list.

	Args:
		items: Ordered (name, args) list from parse_transform_list.
		element_location: XPath-like location for error reporting.

	Returns:
		The single composed 6-tuple matrix (identity when the list is empty).
	"""
	matrix = tools.svg_normalizer.model.IDENTITY_MATRIX
	for index, (name, args) in enumerate(items):
		m = transform_to_matrix(name, args, element_location)
		if index == 0:
			matrix = m
		else:
			matrix = multiply_matrices(matrix, m)
	return matrix


#============================================
def matrix_is_identity(matrix: tuple[float, ...], tol: float = 1e-12) -> bool:
	"""Return True when the matrix is (within tol) the identity transform."""
	return all(abs(matrix[i] - tools.svg_normalizer.model.IDENTITY_MATRIX[i]) <= tol for i in range(6))


#============================================
def transform_point(matrix: tuple[float, ...], x: float, y: float) -> tuple[float, float]:
	"""Apply an affine matrix to an absolute point. Ported from svgo transformAbsolutePoint."""
	nx = matrix[0] * x + matrix[2] * y + matrix[4]
	ny = matrix[1] * x + matrix[3] * y + matrix[5]
	return nx, ny


#============================================
def transform_arc(
	cur_x: float, cur_y: float, arc: tuple[float, ...], matrix: tuple[float, ...],
) -> tuple[float, float, float, float, float]:
	"""Recompute an elliptical-arc's (rx, ry, x-axis-rotation, large, sweep) under a matrix.

	Ported BY HAND from svgo plugins/_transforms.js transformArc. Represents the
	ellipse as a matrix, multiplies by the transform, and uses an SVD to recover
	the new rx, ry, and rotation. Flips the sweep flag when the transform mirrors
	the coordinate system (determinant sign change: matrix[0]<0 XOR matrix[3]<0).
	The arc endpoint is transformed separately by the caller.

	Args:
		cur_x, cur_y: Absolute arc start point (previous pen position).
		arc: The seven absolute arc params (rx, ry, rot_deg, large, sweep, x, y).
		matrix: The composed 6-tuple affine matrix.

	Returns:
		Tuple (new_rx, new_ry, new_rot_deg, large_flag, sweep_flag).
	"""
	# Displacement from arc start to arc end (svgo works in this local frame).
	x = arc[5] - cur_x
	y = arc[6] - cur_y
	a = arc[0]
	b = arc[1]
	rot = math.radians(arc[2])
	cos = math.cos(rot)
	sin = math.sin(rot)
	large = arc[3]
	sweep = arc[4]
	# Correct out-of-range radii exactly as svgo does (skip when radius is 0).
	if a > 0.0 and b > 0.0:
		h = (
			math.pow(x * cos + y * sin, 2) / (4.0 * a * a)
			+ math.pow(y * cos - x * sin, 2) / (4.0 * b * b)
		)
		if h > 1.0:
			h = math.sqrt(h)
			a *= h
			b *= h
	# Ellipse-as-matrix, then composed with the transform.
	ellipse = (a * cos, a * sin, -b * sin, b * cos, 0.0, 0.0)
	m = multiply_matrices(matrix, ellipse)
	# SVD of the 2x2 part to recover major/minor axes and rotation.
	last_col = m[2] * m[2] + m[3] * m[3]
	square_sum = m[0] * m[0] + m[1] * m[1] + last_col
	root = math.hypot(m[0] - m[3], m[1] + m[2]) * math.hypot(m[0] + m[3], m[1] - m[2])
	if root == 0.0:
		# Degenerates to a circle.
		new_rx = math.sqrt(square_sum / 2.0)
		new_ry = new_rx
		new_rot_deg = 0.0
	else:
		major_axis_sqr = (square_sum + root) / 2.0
		minor_axis_sqr = (square_sum - root) / 2.0
		major = abs(major_axis_sqr - last_col) > 1e-6
		sub = (major_axis_sqr if major else minor_axis_sqr) - last_col
		rows_sum = m[0] * m[2] + m[1] * m[3]
		term1 = m[0] * sub + m[2] * rows_sum
		term2 = m[1] * sub + m[3] * rows_sum
		new_rx = math.sqrt(major_axis_sqr)
		new_ry = math.sqrt(minor_axis_sqr)
		# Sign selection mirrors svgo's conditional exactly.
		sign = -1.0 if (term2 < 0.0 if major else term1 > 0.0) else 1.0
		numer = term1 if major else term2
		hyp = math.hypot(term1, term2)
		if hyp == 0.0:
			# Degenerate case: both terms are zero -> no well-defined rotation angle.
			# Emit 0 degrees (safe fallback; the arc is already degenerate).
			new_rot_deg = 0.0
		else:
			new_rot_deg = sign * math.degrees(math.acos(numer / hyp))
	# Flip the sweep flag on a single-axis mirror (determinant sign change).
	if (matrix[0] < 0.0) != (matrix[3] < 0.0):
		sweep = 1.0 - sweep
	return new_rx, new_ry, new_rot_deg, large, sweep


#============================================
def apply_matrix_to_segments(
	segments: list[tools.svg_normalizer.model.PathSegment], matrix: tuple[float, ...],
) -> list[tools.svg_normalizer.model.PathSegment]:
	"""Apply an affine matrix to a list of ABSOLUTE path segments.

	The segments must already be absolute (tools.svg_normalizer.model.parse_path_to_absolute output: only
	M/L/C/Q/A/Z, with H/V already folded into L). Each endpoint and control point
	is transformed; arcs go through transform_arc for new radii/rotation/sweep.

	Args:
		segments: Absolute tools.svg_normalizer.model.PathSegment list.
		matrix: The composed 6-tuple affine matrix.

	Returns:
		A new list of transformed PathSegments (input is not mutated; tools.svg_normalizer.model.PathSegment
		is frozen).
	"""
	out: list[tools.svg_normalizer.model.PathSegment] = []
	cur_x = 0.0
	cur_y = 0.0
	start_x = 0.0
	start_y = 0.0
	for seg in segments:
		cmd = seg.cmd
		nums = seg.nums
		if cmd == "M":
			nx, ny = transform_point(matrix, nums[0], nums[1])
			out.append(tools.svg_normalizer.model.PathSegment("M", (nx, ny)))
			cur_x, cur_y = nums[0], nums[1]
			start_x, start_y = nums[0], nums[1]
		elif cmd == "L":
			nx, ny = transform_point(matrix, nums[0], nums[1])
			out.append(tools.svg_normalizer.model.PathSegment("L", (nx, ny)))
			cur_x, cur_y = nums[0], nums[1]
		elif cmd == "C":
			x1, y1 = transform_point(matrix, nums[0], nums[1])
			x2, y2 = transform_point(matrix, nums[2], nums[3])
			ex, ey = transform_point(matrix, nums[4], nums[5])
			out.append(tools.svg_normalizer.model.PathSegment("C", (x1, y1, x2, y2, ex, ey)))
			cur_x, cur_y = nums[4], nums[5]
		elif cmd == "Q":
			x1, y1 = transform_point(matrix, nums[0], nums[1])
			ex, ey = transform_point(matrix, nums[2], nums[3])
			out.append(tools.svg_normalizer.model.PathSegment("Q", (x1, y1, ex, ey)))
			cur_x, cur_y = nums[2], nums[3]
		elif cmd == "A":
			rx, ry, rot_deg, large, sweep = transform_arc(cur_x, cur_y, nums, matrix)
			ex, ey = transform_point(matrix, nums[5], nums[6])
			out.append(tools.svg_normalizer.model.PathSegment("A", (rx, ry, rot_deg, large, sweep, ex, ey)))
			cur_x, cur_y = nums[5], nums[6]
		elif cmd == "Z":
			out.append(tools.svg_normalizer.model.PathSegment("Z", ()))
			cur_x, cur_y = start_x, start_y
	return out


#============================================
def shape_to_segments(elem: lxml.etree._Element, element_location: str) -> list[tools.svg_normalizer.model.PathSegment] | None:
	"""Convert a basic shape element to an equivalent absolute tools.svg_normalizer.model.PathSegment list.

	This flattens a transform onto a non-path shape (so the
	transform can be removed and the invariant holds). It covers rect (sharp and
	rounded), circle, ellipse, line, polyline, and polygon. The path converter owns the
	general transform-free shape->path DOM rewrite and may reuse this helper.

	A circle/ellipse is emitted as two arc halves; a rounded rect uses arc
	corners. These are the same primitives the bbox math already solves exactly.

	Args:
		elem: The shape element.
		element_location: XPath-like location for error reporting.

	Returns:
		Absolute tools.svg_normalizer.model.PathSegment list, or None when the shape has no usable geometry
		(absent required attributes / non-user unit handled by element_bbox).
	"""
	tag = tools.svg_normalizer.model.local_name(elem.tag)
	if tag == "path":
		d_attr = elem.get("d")
		if not d_attr:
			return None
		return tools.svg_normalizer.model.parse_path_to_absolute(d_attr)
	if tag == "rect":
		x = tools.svg_normalizer.model.parse_float(elem.get("x"))
		y = tools.svg_normalizer.model.parse_float(elem.get("y"))
		w = tools.svg_normalizer.model.parse_float_required(elem.get("width"))
		h = tools.svg_normalizer.model.parse_float_required(elem.get("height"))
		if w is tools.svg_normalizer.model._UNIT_SENTINEL or h is tools.svg_normalizer.model._UNIT_SENTINEL:
			raise tools.svg_normalizer.model.UnsupportedUnitError(element_location)
		if w is None or h is None:
			return None
		w_f = float(w)
		h_f = float(h)
		# Resolve corner radii (rx/ry); per spec each defaults to the other.
		rx_raw = tools.svg_normalizer.model.parse_float_required(elem.get("rx"))
		ry_raw = tools.svg_normalizer.model.parse_float_required(elem.get("ry"))
		if rx_raw is tools.svg_normalizer.model._UNIT_SENTINEL or ry_raw is tools.svg_normalizer.model._UNIT_SENTINEL:
			raise tools.svg_normalizer.model.UnsupportedUnitError(element_location)
		rx = float(rx_raw) if isinstance(rx_raw, float) else None
		ry = float(ry_raw) if isinstance(ry_raw, float) else None
		if rx is None and ry is not None:
			rx = ry
		if ry is None and rx is not None:
			ry = rx
		if rx is None:
			rx = 0.0
		if ry is None:
			ry = 0.0
		# Clamp radii to half the side length (SVG spec).
		rx = min(rx, w_f / 2.0)
		ry = min(ry, h_f / 2.0)
		return _rect_segments(x, y, w_f, h_f, rx, ry)
	if tag == "circle":
		cx = tools.svg_normalizer.model.parse_float(elem.get("cx"))
		cy = tools.svg_normalizer.model.parse_float(elem.get("cy"))
		r = tools.svg_normalizer.model.parse_float_required(elem.get("r"))
		if r is tools.svg_normalizer.model._UNIT_SENTINEL:
			raise tools.svg_normalizer.model.UnsupportedUnitError(element_location)
		if r is None:
			return None
		r_f = float(r)
		return _ellipse_segments(cx, cy, r_f, r_f)
	if tag == "ellipse":
		cx = tools.svg_normalizer.model.parse_float(elem.get("cx"))
		cy = tools.svg_normalizer.model.parse_float(elem.get("cy"))
		rx_raw = tools.svg_normalizer.model.parse_float_required(elem.get("rx"))
		ry_raw = tools.svg_normalizer.model.parse_float_required(elem.get("ry"))
		if rx_raw is tools.svg_normalizer.model._UNIT_SENTINEL or ry_raw is tools.svg_normalizer.model._UNIT_SENTINEL:
			raise tools.svg_normalizer.model.UnsupportedUnitError(element_location)
		if rx_raw is None or ry_raw is None:
			return None
		return _ellipse_segments(cx, cy, float(rx_raw), float(ry_raw))
	if tag == "line":
		has_any = any(elem.get(a) is not None for a in ("x1", "y1", "x2", "y2"))
		if not has_any:
			return None
		x1 = tools.svg_normalizer.model.parse_float(elem.get("x1"))
		y1 = tools.svg_normalizer.model.parse_float(elem.get("y1"))
		x2 = tools.svg_normalizer.model.parse_float(elem.get("x2"))
		y2 = tools.svg_normalizer.model.parse_float(elem.get("y2"))
		return [tools.svg_normalizer.model.PathSegment("M", (x1, y1)), tools.svg_normalizer.model.PathSegment("L", (x2, y2))]
	if tag in {"polyline", "polygon"}:
		points = tools.svg_normalizer.model.parse_points(elem.get("points", ""))
		if not points:
			return None
		segs: list[tools.svg_normalizer.model.PathSegment] = [tools.svg_normalizer.model.PathSegment("M", (points[0][0], points[0][1]))]
		for px, py in points[1:]:
			segs.append(tools.svg_normalizer.model.PathSegment("L", (px, py)))
		if tag == "polygon":
			segs.append(tools.svg_normalizer.model.PathSegment("Z", ()))
		return segs
	return None


#============================================
def _rect_segments(x: float, y: float, w: float, h: float, rx: float, ry: float) -> list[tools.svg_normalizer.model.PathSegment]:
	"""Build absolute path segments for a rect, sharp or rounded.

	Sharp rect (rx==0 or ry==0) is four lines. Rounded rect uses four quarter
	arcs (sweep=1, large=0) at the corners, matching svgo convertShapeToPath.
	"""
	if rx <= 0.0 or ry <= 0.0:
		return [
			tools.svg_normalizer.model.PathSegment("M", (x, y)),
			tools.svg_normalizer.model.PathSegment("L", (x + w, y)),
			tools.svg_normalizer.model.PathSegment("L", (x + w, y + h)),
			tools.svg_normalizer.model.PathSegment("L", (x, y + h)),
			tools.svg_normalizer.model.PathSegment("Z", ()),
		]
	# Rounded rectangle: start after the top-left horizontal radius, then walk
	# clockwise placing a quarter-arc at each corner.
	segs = [
		tools.svg_normalizer.model.PathSegment("M", (x + rx, y)),
		tools.svg_normalizer.model.PathSegment("L", (x + w - rx, y)),
		tools.svg_normalizer.model.PathSegment("A", (rx, ry, 0.0, 0.0, 1.0, x + w, y + ry)),
		tools.svg_normalizer.model.PathSegment("L", (x + w, y + h - ry)),
		tools.svg_normalizer.model.PathSegment("A", (rx, ry, 0.0, 0.0, 1.0, x + w - rx, y + h)),
		tools.svg_normalizer.model.PathSegment("L", (x + rx, y + h)),
		tools.svg_normalizer.model.PathSegment("A", (rx, ry, 0.0, 0.0, 1.0, x, y + h - ry)),
		tools.svg_normalizer.model.PathSegment("L", (x, y + ry)),
		tools.svg_normalizer.model.PathSegment("A", (rx, ry, 0.0, 0.0, 1.0, x + rx, y)),
		tools.svg_normalizer.model.PathSegment("Z", ()),
	]
	return segs


#============================================
def _ellipse_segments(cx: float, cy: float, rx: float, ry: float) -> list[tools.svg_normalizer.model.PathSegment]:
	"""Build absolute path segments for a circle/ellipse using two half arcs."""
	segs = [
		tools.svg_normalizer.model.PathSegment("M", (cx - rx, cy)),
		tools.svg_normalizer.model.PathSegment("A", (rx, ry, 0.0, 1.0, 0.0, cx + rx, cy)),
		tools.svg_normalizer.model.PathSegment("A", (rx, ry, 0.0, 1.0, 0.0, cx - rx, cy)),
		tools.svg_normalizer.model.PathSegment("Z", ()),
	]
	return segs


# Presentation attributes that carry url(#id) paint/clip references. These are
# copied verbatim when a shape is rewritten to a <path>; their referenced
# geometry (gradients/clips) lives in defs and is paint-space exempt.
# Note: "transform" is intentionally ABSENT -- _convert_shape_element_to_path
# always strips the transform (geometry is baked into the path d), so copying
# it would re-introduce the very attribute the flattening pass just removed.
_COPY_THROUGH_ATTRS = frozenset({
	"fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin",
	"stroke-miterlimit", "stroke-dasharray", "stroke-dashoffset", "stroke-opacity",
	"fill-opacity", "fill-rule", "opacity", "clip-path", "clip-rule", "mask",
	"filter", "vector-effect", "style", "class", "id", "data-name", "display",
	"visibility", "color", "data-vlab-normalizer-boundary-token",
})


#============================================
def _stroke_distortion_unsafe(elem: lxml.etree._Element, matrix: tuple[float, ...]) -> bool:
	"""Return True when applying matrix to a stroked element would distort the stroke.

	Ported from svgo applyTransforms: a stroke can only be applied when the matrix
	is a uniform scale plus rotation, optionally with a single-axis flip. That is
	exactly when (a==d and b==-c) OR (a==-d and b==c). A non-uniform scale or skew
	would turn a round stroke into an ellipse, which v3 must never emit. A visible
	stroke under such a matrix is refused upstream as UNSUPPORTED_TRANSFORM.

	Args:
		elem: The element being flattened.
		matrix: The composed 6-tuple affine matrix.

	Returns:
		True when the element has a visible stroke and the matrix is non-uniform
		or skewed (so flattening would distort the stroke); False otherwise.
	"""
	stroke = elem.get("stroke")
	# An inline style may also set stroke; check it minimally (inline-only cascade).
	if stroke is None:
		style = elem.get("style") or ""
		stroke_match = re.search(r"(?:^|;)\s*stroke\s*:\s*([^;]+)", style)
		if stroke_match:
			stroke = stroke_match.group(1).strip()
	if stroke is None or stroke == "none":
		return False
	a, b, c, d = matrix[0], matrix[1], matrix[2], matrix[3]
	uniform = (abs(a - d) < 1e-9 and abs(b + c) < 1e-9)
	flipped = (abs(a + d) < 1e-9 and abs(b - c) < 1e-9)
	return not (uniform or flipped)


#============================================
def _is_geometry_transform_attr(elem: lxml.etree._Element) -> str | None:
	"""Return the geometry-affecting transform attribute value, or None.

	gradientTransform and patternTransform are paint-space and are NOT returned
	(they are exempt from the canonical invariant). Only the plain `transform`
	attribute on a drawable element / group affects geometry.
	"""
	val = elem.get("transform")
	if val is not None and val.strip() != "":
		return val
	return None


#============================================
# Matches a stroke-width declaration inside an inline style attribute, capturing
# the numeric value (user units; svgo only scales unitless / px stroke widths).
_STYLE_STROKE_WIDTH_RE = re.compile(
	r"(stroke-width\s*:\s*)([-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?)(\s*(?:px)?\s*)(;|$)",
	re.IGNORECASE,
)


#============================================
def _scale_stroke_width(elem: lxml.etree._Element, scale: float) -> None:
	"""Multiply an element's stroke-width by a uniform scale factor.

	Handles both the presentation attribute (stroke-width="...") and an inline
	style declaration (style="...;stroke-width:...;..."). Only user-unit values
	(unitless or px) are scaled; a non-user unit is left untouched (such files are
	rejected elsewhere for unsupported units). When no stroke-width is declared the
	SVG default is 1 user unit; that case is left implicit and unscaled because the
	stroke-distortion guard already refuses visibly-stroked non-uniform transforms,
	and a default-width hairline change is below the visual-integrity threshold.

	Args:
		elem: The drawable element whose geometry is being baked.
		scale: The uniform scale factor (matrix major-axis length).
	"""
	# Identity scale changes nothing; skip to avoid reformatting attributes.
	if abs(scale - 1.0) < 1e-12:
		return
	# Presentation attribute form.
	attr_val = elem.get("stroke-width")
	if attr_val is not None:
		parsed = tools.svg_normalizer.model.parse_float_required(attr_val)
		if isinstance(parsed, float):
			elem.set("stroke-width", tools.svg_normalizer.model.fmt_precise(parsed * scale))
	# Inline style form. Rewrite the first stroke-width:NUM occurrence in place.
	style = elem.get("style")
	if style is not None and "stroke-width" in style:
		def _repl(match: "re.Match[str]") -> str:
			scaled = float(match.group(2)) * scale
			return match.group(1) + tools.svg_normalizer.model.fmt_precise(scaled) + match.group(3) + match.group(4)
		new_style = _STYLE_STROKE_WIDTH_RE.sub(_repl, style, count=1)
		elem.set("style", new_style)


#============================================
def _flatten_one(elem: lxml.etree._Element, matrix: tuple[float, ...]) -> None:
	"""Bake an already-composed matrix into one drawable element's geometry.

	The element's own transform attribute (if any) must already be folded into
	matrix by the caller. After this call the element carries no geometry
	transform.

	Args:
		elem: A drawable shape/path element (not a container).
		matrix: The composed 6-tuple matrix from root down to this element.

	Raises:
		UnsupportedTransformError: When a visible stroke would be distorted.
		NonScalingStrokeError: When a non-scaling stroke cannot be resolved.
		tools.svg_normalizer.model.UnsupportedUnitError: When a required size attr carries a non-user unit.
	"""
	location = elem.getroottree().getpath(elem)
	# A material bounds anchor is a hidden runtime resource, not visible artwork.
	# The renderer deliberately reads SVGRectElement geometry instead of getBBox()
	# because getBBox() on display:none content is browser-dependent.  Preserve a
	# valid authored rect in root coordinates; a non-identity own or inherited
	# transform would require path conversion, so reject it through the normal
	# transform path instead of emitting a runtime-incompatible anchor.
	if (
		tools.svg_normalizer.model.local_name(elem.tag) == "rect"
		and elem.get("id") == tools.svg_normalizer.model.RUNTIME_BOUNDS_RECT_ID
	):
		if not matrix_is_identity(matrix):
			raise UnsupportedTransformError(
				location,
				"anchor_liquid_bounds must be an untransformed root-coordinate rect",
			)
		if elem.get("transform") is not None:
			del elem.attrib["transform"]
		return
	# If the composed matrix is identity, only strip the (now-redundant) attr.
	if matrix_is_identity(matrix):
		if elem.get("transform") is not None:
			del elem.attrib["transform"]
		return
	# Non-scaling stroke under a transform that changes scale is unresolved here.
	if elem.get("vector-effect") == "non-scaling-stroke":
		scale = math.hypot(matrix[0], matrix[1])
		if abs(scale - 1.0) > 1e-9:
			raise NonScalingStrokeError(location)
	# A visible stroke under a non-uniform / skew matrix would be distorted.
	if _stroke_distortion_unsafe(elem, matrix):
		raise UnsupportedTransformError(
			location, "non-uniform/skew transform on a stroked element"
		)
	# Scale stroke-width by the matrix's uniform scale factor. Baking the matrix
	# into geometry shrinks/grows the shape, so a fixed stroke-width would render at
	# the wrong thickness (the cpu.svg mesh-greyout bug: a stroke authored under a
	# 0.415 scale stayed at full width after flatten and filled the holes). The
	# distortion guard above guarantees the matrix is a uniform scale + rotation
	# (optionally flipped) whenever a visible stroke is present, so a single scalar
	# scale is exact. Non-scaling-stroke elements were handled (and rejected when
	# scale != 1) above, so they never reach here with a scaling matrix.
	_scale_stroke_width(elem, math.hypot(matrix[0], matrix[1]))
	segments = shape_to_segments(elem, location)
	if segments is None:
		# No drawable geometry (e.g. shape missing required attrs). Just drop the
		# transform attribute so the invariant holds; bbox treats it as empty.
		if elem.get("transform") is not None:
			del elem.attrib["transform"]
		return
	flattened = apply_matrix_to_segments(segments, matrix)
	tag = tools.svg_normalizer.model.local_name(elem.tag)
	if tag == "path":
		# Rewrite path d in place; keep all other attributes.
		elem.set("d", tools.svg_normalizer.model.path_segments_to_d(flattened))
		if elem.get("transform") is not None:
			del elem.attrib["transform"]
		return
	# Convert a basic shape element into a <path>, preserving paint/ref attributes.
	_convert_shape_element_to_path(elem, flattened)


#============================================
def _convert_shape_element_to_path(elem: lxml.etree._Element, segments: list[tools.svg_normalizer.model.PathSegment]) -> None:
	"""Rewrite a basic-shape element in place as a <path> with flattened geometry.

	Preserves id/data-name, paint attributes, and url(#) references so reference
	integrity is unaffected. Shape-specific geometry attributes (x/width/cx/r/...)
	are dropped because they are now encoded in the path d. The transform
	attribute is removed (geometry is baked in).

	Args:
		elem: The shape element to convert.
		segments: The already-flattened absolute path segments.
	"""
	# Capture attributes to carry forward (paint, refs, identity), drop geometry.
	carried: list[tuple[str, str]] = []
	for name, value in elem.attrib.items():
		local = tools.svg_normalizer.model.local_name(name) if isinstance(name, str) else name
		if local == "transform":
			continue
		if local in _COPY_THROUGH_ATTRS:
			carried.append((name, value))
	# Retag the element as a path in the SVG namespace and reset its attributes.
	elem.tag = f"{{{tools.svg_normalizer.model.SVG_NS}}}path"
	for name in list(elem.attrib):
		del elem.attrib[name]
	for name, value in carried:
		elem.set(name, value)
	elem.set("d", tools.svg_normalizer.model.path_segments_to_d(segments))


# Paint elements whose userSpaceOnUse coordinates live in the same coordinate
# space as the referencing geometry. When that geometry is moved by transform
# flattening, the paint must be moved with it or the paint resolves out of
# bounds and collapses to its nearest stop color (the cpu.svg grey-out bug).
_USERSPACE_PAINT_TAGS = frozenset({"linearGradient", "radialGradient", "pattern"})


#============================================
