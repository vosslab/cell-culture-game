"""Turn supported SVG clip geometry into explicit polygon operations."""

import math

import lxml.etree
import shapely.geometry

import tools.svg_normalizer.model
import tools.svg_normalizer.transform_geometry
import tools.svg_normalizer.geometry


_CLIP_FLATTEN_TOLERANCE = 0.1
_STROKE_ENVELOPE_MIN_HALF = _CLIP_FLATTEN_TOLERANCE
_CLIP_GEOMETRY_TAGS = frozenset({'path', 'rect', 'circle', 'ellipse', 'polygon', 'polyline'})
_CLIP_FORBIDDEN_CHILD_TAGS = frozenset({'use', 'text', 'image', 'g', 'svg'})


def _cubic_points(
	p0: tuple[float, float], p1: tuple[float, float],
	p2: tuple[float, float], p3: tuple[float, float], tol: float,
) -> list[tuple[float, float]]:
	"""Adaptively flatten a cubic bezier to a polyline within chord tolerance tol.

	Recursively subdivides until the control points lie within tol of the chord.
	Returns the interior and end points (the start point p0 is added by caller).

	Args:
		p0, p1, p2, p3: Cubic bezier control points (absolute).
		tol: Maximum allowed chord deviation in user units.

	Returns:
		List of points approximating the curve, excluding p0, including p3.
	"""
	# Flatness test: distance of control points p1, p2 from the chord p0-p3.
	dx = p3[0] - p0[0]
	dy = p3[1] - p0[1]
	# Use the unnormalized cross-product distance; guard the degenerate chord.
	chord_len = math.hypot(dx, dy)
	if chord_len < 1e-12:
		d1 = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
		d2 = math.hypot(p2[0] - p0[0], p2[1] - p0[1])
		flat = max(d1, d2) <= tol
	else:
		d1 = abs((p1[0] - p0[0]) * dy - (p1[1] - p0[1]) * dx) / chord_len
		d2 = abs((p2[0] - p0[0]) * dy - (p2[1] - p0[1]) * dx) / chord_len
		flat = max(d1, d2) <= tol
	if flat:
		return [p3]
	# Subdivide at t=0.5 using de Casteljau.
	p01 = ((p0[0] + p1[0]) / 2.0, (p0[1] + p1[1]) / 2.0)
	p12 = ((p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0)
	p23 = ((p2[0] + p3[0]) / 2.0, (p2[1] + p3[1]) / 2.0)
	p012 = ((p01[0] + p12[0]) / 2.0, (p01[1] + p12[1]) / 2.0)
	p123 = ((p12[0] + p23[0]) / 2.0, (p12[1] + p23[1]) / 2.0)
	mid = ((p012[0] + p123[0]) / 2.0, (p012[1] + p123[1]) / 2.0)
	left = _cubic_points(p0, p01, p012, mid, tol)
	right = _cubic_points(mid, p123, p23, p3, tol)
	return left + right


#============================================
def _quadratic_points(
	p0: tuple[float, float], p1: tuple[float, float], p2: tuple[float, float], tol: float,
) -> list[tuple[float, float]]:
	"""Flatten a quadratic bezier by elevating it to a cubic, then flattening that.

	A quadratic with control point p1 is the cubic with control points
	c1 = p0 + 2/3 (p1 - p0) and c2 = p2 + 2/3 (p1 - p2).

	Args:
		p0, p1, p2: Quadratic bezier control points (absolute).
		tol: Maximum allowed chord deviation in user units.

	Returns:
		List of points approximating the curve, excluding p0, including p2.
	"""
	c1 = (p0[0] + 2.0 / 3.0 * (p1[0] - p0[0]), p0[1] + 2.0 / 3.0 * (p1[1] - p0[1]))
	c2 = (p2[0] + 2.0 / 3.0 * (p1[0] - p2[0]), p2[1] + 2.0 / 3.0 * (p1[1] - p2[1]))
	return _cubic_points(p0, c1, c2, p2, tol)


#============================================
def _arc_points(
	x0: float, y0: float, arc: tuple[float, ...], tol: float,
) -> list[tuple[float, float]]:
	"""Flatten an elliptical arc to a polyline within chord tolerance tol.

	Uses the center parameterization (_arc_center_params) and samples the arc at
	a step fine enough that the chord deviation stays under tol. A degenerate arc
	(zero radius / coincident endpoints) reduces to a single line to the endpoint.

	Args:
		x0, y0: Arc start point (absolute).
		arc: The seven absolute arc params (rx, ry, rot_deg, large, sweep, x, y).
		tol: Maximum allowed chord deviation in user units.

	Returns:
		List of points approximating the arc, excluding (x0,y0), including the end.
	"""
	rx, ry, rot_deg, large, sweep, x1, y1 = arc
	params = tools.svg_normalizer.model._arc_center_params(x0, y0, rx, ry, rot_deg, large, sweep, x1, y1)
	if params is None:
		# Degenerate arc: straight line to the endpoint.
		return [(x1, y1)]
	cx, cy, theta1, delta = params
	rx = abs(rx)
	ry = abs(ry)
	phi = math.radians(rot_deg % 360.0)
	cos_phi = math.cos(phi)
	sin_phi = math.sin(phi)
	# Re-apply the radius correction so sampling matches the solved center.
	dx2 = (x0 - x1) / 2.0
	dy2 = (y0 - y1) / 2.0
	x1p = cos_phi * dx2 + sin_phi * dy2
	y1p = -sin_phi * dx2 + cos_phi * dy2
	radii_check = (x1p * x1p) / (rx * rx) + (y1p * y1p) / (ry * ry)
	if radii_check > 1.0:
		scale = math.sqrt(radii_check)
		rx *= scale
		ry *= scale
	# Choose a step count so the chord deviation of a circle of radius max(rx,ry)
	# stays under tol: deviation ~= r (1 - cos(step/2)). Solve for step.
	r_max = max(rx, ry)
	if r_max <= tol:
		# The whole arc is smaller than the tolerance: one segment suffices.
		return [(x1, y1)]
	# 1 - cos(a) <= tol/r  ->  a <= 2 * acos(1 - tol/r_max).
	ratio = 1.0 - tol / r_max
	ratio = max(-1.0, min(1.0, ratio))
	max_step = 2.0 * math.acos(ratio)
	if max_step <= 1e-9:
		max_step = abs(delta)
	steps = max(1, int(math.ceil(abs(delta) / max_step)))
	points: list[tuple[float, float]] = []
	for i in range(1, steps + 1):
		t = theta1 + delta * (i / steps)
		px, py = tools.svg_normalizer.model._arc_point(cx, cy, rx, ry, cos_phi, sin_phi, t)
		points.append((px, py))
	return points


#============================================
def segments_to_rings(
	segments: list[tools.svg_normalizer.model.PathSegment], tol: float,
) -> list[list[tuple[float, float]]]:
	"""Flatten absolute path segments into a list of closed point rings.

	Each subpath (M..Z or M.. up to the next M) becomes one ring. Curves are
	flattened to polylines within tol. Open subpaths are implicitly closed (clip
	regions are filled areas, so each subpath bounds a region). Rings with fewer
	than 3 distinct points are dropped (no area).

	Args:
		segments: Absolute tools.svg_normalizer.model.PathSegment list (M/L/C/Q/A/Z only).
		tol: Curve-flattening chord tolerance in user units.

	Returns:
		List of rings; each ring is a list of (x, y) points.
	"""
	rings: list[list[tuple[float, float]]] = []
	current: list[tuple[float, float]] = []
	cur_x = 0.0
	cur_y = 0.0
	start_x = 0.0
	start_y = 0.0
	for seg in segments:
		cmd = seg.cmd
		nums = seg.nums
		if cmd == "M":
			# Starting a new subpath: flush the previous ring.
			if len(current) >= 3:
				rings.append(current)
			current = [(nums[0], nums[1])]
			cur_x, cur_y = nums[0], nums[1]
			start_x, start_y = nums[0], nums[1]
		elif cmd == "L":
			current.append((nums[0], nums[1]))
			cur_x, cur_y = nums[0], nums[1]
		elif cmd == "C":
			pts = _cubic_points(
				(cur_x, cur_y), (nums[0], nums[1]),
				(nums[2], nums[3]), (nums[4], nums[5]), tol,
			)
			current.extend(pts)
			cur_x, cur_y = nums[4], nums[5]
		elif cmd == "Q":
			pts = _quadratic_points(
				(cur_x, cur_y), (nums[0], nums[1]), (nums[2], nums[3]), tol,
			)
			current.extend(pts)
			cur_x, cur_y = nums[2], nums[3]
		elif cmd == "A":
			pts = _arc_points(cur_x, cur_y, nums, tol)
			current.extend(pts)
			cur_x, cur_y = nums[5], nums[6]
		elif cmd == "Z":
			# Close back to the subpath start; flush.
			if current and (cur_x, cur_y) != (start_x, start_y):
				current.append((start_x, start_y))
			if len(current) >= 3:
				rings.append(current)
			current = []
			cur_x, cur_y = start_x, start_y
	# Flush a trailing open subpath (implicitly closed).
	if len(current) >= 3:
		rings.append(current)
	return rings


#============================================
def _polygon_from_segments(
	segments: list[tools.svg_normalizer.model.PathSegment], fill_rule: str, tol: float,
) -> "shapely.geometry.base.BaseGeometry":
	"""Build a (possibly multi) shapely polygon from absolute path segments.

	Each subpath ring becomes a shapely polygon; the rings are combined with the
	requested fill rule. nonzero (the SVG default) and evenodd both map cleanly
	to shapely's set operations after make_valid normalizes self-intersections:
	  - evenodd: symmetric_difference of all rings (overlaps cancel).
	  - nonzero: union of all rings (overlaps accumulate as filled).
	make_valid handles self-touching / bowtie rings so the result is a valid
	(Multi)Polygon. An empty ring set yields an empty geometry.

	Args:
		segments: Absolute tools.svg_normalizer.model.PathSegment list.
		fill_rule: "evenodd" or "nonzero".
		tol: Curve-flattening chord tolerance in user units.

	Returns:
		A shapely Polygon / MultiPolygon (possibly empty).
	"""
	rings = segments_to_rings(segments, tol)
	if not rings:
		return shapely.geometry.Polygon()
	polys = [shapely.make_valid(shapely.geometry.Polygon(ring)) for ring in rings]
	combined = polys[0]
	for poly in polys[1:]:
		if fill_rule == "evenodd":
			combined = combined.symmetric_difference(poly)
		else:
			combined = combined.union(poly)
	# Normalize the result so downstream emission sees clean (Multi)Polygon parts.
	return shapely.make_valid(combined)


#============================================
def _resolve_fill_rule(elem: lxml.etree._Element, prop: str) -> str:
	"""Return 'evenodd' or 'nonzero' (default) for a fill-rule / clip-rule property.

	Reads inline style then presentation attribute (inline-only cascade).

	Args:
		elem: The element.
		prop: "fill-rule" (target) or "clip-rule" (clip child).

	Returns:
		"evenodd" when the property is set to evenodd, else "nonzero".
	"""
	val = tools.svg_normalizer.geometry._resolved_property(elem, prop)
	if val is not None and val.strip().lower() == "evenodd":
		return "evenodd"
	return "nonzero"


#============================================
def _geometry_to_path_d(geometry: "shapely.geometry.base.BaseGeometry") -> str:
	"""Serialize a shapely Polygon / MultiPolygon to absolute SVG path data.

	Each polygon emits its exterior ring as a clockwise-wound subpath and each
	interior hole as a reverse-wound subpath, so the SVG nonzero winding rule
	renders the holes as cut-outs. Coordinates use tools.svg_normalizer.model.fmt_precise (A4 precision).
	An empty geometry returns "".

	Args:
		geometry: A shapely Polygon or MultiPolygon (already make_valid).

	Returns:
		Absolute SVG path data string (M/L/Z subpaths), or "" when empty.
	"""
	if geometry.is_empty:
		return ""
	# Normalize to a flat list of Polygon parts.
	if geometry.geom_type == "Polygon":
		polygons = [geometry]
	elif geometry.geom_type == "MultiPolygon":
		polygons = list(geometry.geoms)
	elif geometry.geom_type == "GeometryCollection":
		# Keep only polygonal parts (lines/points from degenerate clips are dropped).
		polygons = [g for g in geometry.geoms if g.geom_type == "Polygon"]
	else:
		# Lower-dimensional result (LineString/Point): no fillable area.
		return ""
	parts: list[str] = []
	for poly in polygons:
		if poly.is_empty:
			continue
		# Exterior ring clockwise; holes counter-clockwise (opposite winding) so
		# the SVG nonzero rule subtracts them.
		exterior = _ring_coords(poly.exterior, clockwise=True)
		if exterior:
			parts.append(_ring_to_subpath(exterior))
		for interior in poly.interiors:
			hole = _ring_coords(interior, clockwise=False)
			if hole:
				parts.append(_ring_to_subpath(hole))
	return " ".join(parts)


#============================================
def _ring_coords(ring: "shapely.geometry.base.BaseGeometry", clockwise: bool) -> list[tuple[float, float]]:
	"""Return a ring's coordinates wound in the requested direction (no closing dup).

	Shapely rings repeat the first point as the last; that duplicate is dropped
	(the Z command closes the subpath). The winding is enforced via is_ccw.

	Args:
		ring: A shapely LinearRing.
		clockwise: True to return clockwise points, False for counter-clockwise.

	Returns:
		List of (x, y) points without the closing duplicate.
	"""
	coords = list(ring.coords)
	if len(coords) > 1 and coords[0] == coords[-1]:
		coords = coords[:-1]
	# ring.is_ccw is True when the stored ring is counter-clockwise.
	is_ccw = ring.is_ccw
	want_ccw = not clockwise
	if is_ccw != want_ccw:
		coords = list(reversed(coords))
	return [(float(x), float(y)) for x, y in coords]


#============================================
def _ring_to_subpath(points: list[tuple[float, float]]) -> str:
	"""Emit one closed subpath (M + L* + Z) from a ring's points using tools.svg_normalizer.model.fmt_precise."""
	first = points[0]
	parts = [f"M {tools.svg_normalizer.model.fmt_precise(first[0])} {tools.svg_normalizer.model.fmt_precise(first[1])}"]
	for x, y in points[1:]:
		parts.append(f"L {tools.svg_normalizer.model.fmt_precise(x)} {tools.svg_normalizer.model.fmt_precise(y)}")
	parts.append("Z")
	return " ".join(parts)


#============================================
def _clip_child_geometry_node(clip_elem: lxml.etree._Element, location: str) -> lxml.etree._Element:
	"""Return the single geometry child of a clipPath, enforcing the allowlist.

	Raises tools.svg_normalizer.transform_geometry.ComplexClipError when the clipPath does not hold exactly one geometry
	child, contains a forbidden child (mask/filter/text/image/use/nested clip),
	or uses clipPathUnits=objectBoundingBox.

	Args:
		clip_elem: The <clipPath> element.
		location: XPath-like location of the clipped target (for the error).

	Returns:
		The single geometry child element.

	Raises:
		tools.svg_normalizer.transform_geometry.ComplexClipError: When the clipPath is outside the simple allowlist.
	"""
	clip_location = clip_elem.getroottree().getpath(clip_elem)
	# clipPathUnits default is userSpaceOnUse; objectBoundingBox is rejected.
	units = clip_elem.get("clipPathUnits")
	if units is not None and units.strip() != "userSpaceOnUse":
		raise tools.svg_normalizer.transform_geometry.ComplexClipError(clip_location, f"clipPathUnits={units!r} is not supported")
	geometry_children: list[lxml.etree._Element] = []
	for child in clip_elem:
		if not isinstance(child.tag, str):
			continue
		child_tag = tools.svg_normalizer.model.local_name(child.tag)
		if child_tag in _CLIP_FORBIDDEN_CHILD_TAGS:
			raise tools.svg_normalizer.transform_geometry.ComplexClipError(
				clip_location, f"clipPath contains forbidden <{child_tag}>"
			)
		if child_tag in _CLIP_GEOMETRY_TAGS:
			geometry_children.append(child)
		# Any other element type (e.g. a group) makes the clip non-simple.
		elif child_tag not in {"title", "desc", "metadata"}:
			raise tools.svg_normalizer.transform_geometry.ComplexClipError(
				clip_location, f"clipPath contains unsupported <{child_tag}>"
			)
	if len(geometry_children) != 1:
		raise tools.svg_normalizer.transform_geometry.ComplexClipError(
			clip_location,
			f"clipPath must hold exactly one path/shape, found {len(geometry_children)}",
		)
	return geometry_children[0]


#============================================
def _target_is_stroke_only(elem: lxml.etree._Element) -> bool:
	"""Return True when the clip target is stroke-only (fill resolves to none).

	A stroke-only target carries no filled area, so clipping it is a stroke trim
	rather than a filled-area intersection. The no-op short circuit handles the
	common page-bounds case; a genuine stroke trim stays rejected.

	Args:
		elem: The clipped target element.

	Returns:
		True when fill is explicitly "none", else False.
	"""
	fill = tools.svg_normalizer.geometry._resolved_property(elem, "fill")
	return fill is not None and fill.strip().lower() == "none"


#============================================
def _target_segments_for_clip(elem: lxml.etree._Element, location: str) -> list[tools.svg_normalizer.model.PathSegment]:
	"""Return the absolute segments of a clip TARGET path.

	After flatten_transforms + convert_shapes_to_paths a supported target is a
	<path>. This returns the target geometry without enforcing the fill rule;
	callers decide how to treat a stroke-only target (no-op drop vs reject).

	Args:
		elem: The clipped target element.
		location: XPath-like location (for the error).

	Returns:
		Absolute tools.svg_normalizer.model.PathSegment list of the target geometry.

	Raises:
		tools.svg_normalizer.transform_geometry.ComplexClipError: When the target is not path geometry or has no path data.
	"""
	tag = tools.svg_normalizer.model.local_name(elem.tag)
	if tag != "path":
		raise tools.svg_normalizer.transform_geometry.ComplexClipError(location, f"clip target <{tag}> is not path geometry")
	d_attr = elem.get("d")
	if not d_attr:
		raise tools.svg_normalizer.transform_geometry.ComplexClipError(location, "clip target has no path data")
	return tools.svg_normalizer.model.parse_path_to_absolute(d_attr)


#============================================
def _resolved_stroke_width(elem: lxml.etree._Element) -> float:
	"""Return the element's stroke-width in user units (SVG default 1.0 when absent).

	After flatten_transforms a uniform scale is baked into the geometry and the
	stroke-width is rewritten to match, so the value read here is already in root
	coordinates. A trailing "px" unit is tolerated; any other unit or an
	unparseable value falls back to the SVG default rather than guessing.

	Args:
		elem: The clipped target element.

	Returns:
		The stroke-width as a float, defaulting to 1.0.
	"""
	raw = tools.svg_normalizer.geometry._resolved_property(elem, "stroke-width")
	if raw is None:
		return tools.svg_normalizer.geometry._DEFAULT_STROKE_WIDTH
	text = raw.strip().lower()
	if text.endswith("px"):
		text = text[:-2].strip()
	# A bare number (optionally with a px unit) is the only supported form; any
	# other unit or junk falls back to the default so the envelope stays sane.
	if not tools.svg_normalizer.model._TRANSFORM_NUM_RE.fullmatch(text):
		return tools.svg_normalizer.geometry._DEFAULT_STROKE_WIDTH
	return float(text)


#============================================
def _target_envelope_polygon(
	elem: lxml.etree._Element, target_segments: list[tools.svg_normalizer.model.PathSegment],
) -> "shapely.geometry.base.BaseGeometry":
	"""Build the target's rendered envelope: filled area unioned with stroke envelope.

	The envelope is the region the target actually paints, used by the no-op
	containment test. It is the union of:
	  - the filled polygon (empty for a stroke-only fill:none target);
	  - the stroke envelope: each ring buffered by half the stroke-width (with a
	    small floor so a hairline stroke still has area).
	A pure-stroke target yields the stroke buffer alone; a filled target with no
	stroke still yields its filled polygon.

	Args:
		elem: The clipped target element (for fill-rule and stroke-width).
		target_segments: The target's absolute path segments.

	Returns:
		A shapely geometry covering the target's painted area (possibly empty).
	"""
	target_rule = _resolve_fill_rule(elem, "fill-rule")
	filled = _polygon_from_segments(target_segments, target_rule, _CLIP_FLATTEN_TOLERANCE)
	# Stroke envelope: buffer every flattened ring by half the stroke-width.
	half = max(_resolved_stroke_width(elem) / 2.0, _STROKE_ENVELOPE_MIN_HALF)
	stroke_parts: list["shapely.geometry.base.BaseGeometry"] = []
	for ring in segments_to_rings(target_segments, _CLIP_FLATTEN_TOLERANCE):
		if len(ring) >= 2:
			stroke_parts.append(shapely.geometry.LineString(ring).buffer(half))
	if stroke_parts:
		stroke_env = shapely.union_all(stroke_parts)
	else:
		stroke_env = shapely.geometry.Polygon()
	# Union the filled area with the stroke envelope; either part may be empty.
	if filled.is_empty:
		envelope = stroke_env
	elif stroke_env.is_empty:
		envelope = filled
	else:
		envelope = filled.union(stroke_env)
	return shapely.make_valid(envelope)


#============================================
