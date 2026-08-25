"""Compute, shift, and convert the drawable geometry of SVG documents."""

import re

import lxml.etree

import tools.svg_normalizer.model
import tools.svg_normalizer.transform_geometry


def convert_shapes_to_paths(root: lxml.etree._Element) -> None:
	"""Convert every supported shape element in the tree to an absolute <path>.

	This is the general (transform-free) shape->path DOM rewrite (A2). It runs
	AFTER flatten_transforms so all geometry is already in root coordinates.
	Shapes that already went through _flatten_one (because they had a transform)
	were already rewritten to <path>; this pass covers the remaining shapes
	(no-transform rect/circle/ellipse/line/polyline/polygon elements).

	Elements inside <defs> are NOT converted: clipPath geometry and paint-only
	shapes in defs are handled separately; converting them here would change
	the structure those WPs expect.

	Each shape's presentation attributes (fill, stroke, id, class, clip-path,
	url(#) refs, etc.) are preserved on the new <path> via _COPY_THROUGH_ATTRS
	so reference integrity and ASCII-id rewriting remain correct.

	Args:
		root: The parsed SVG root element. Modified in place.

	Raises:
		tools.svg_normalizer.model.UnsupportedUnitError: When a required size attribute uses a non-user unit
			(%, mm, cm, ...). The caller should propagate this to a rejection.
	"""
	# Collect shape elements outside defs to avoid mutating the tree while
	# iterating. We need their location for tools.svg_normalizer.model.UnsupportedUnitError reporting.
	shapes_to_convert: list[lxml.etree._Element] = []
	_collect_shapes(root, in_defs=False, out=shapes_to_convert)
	for elem in shapes_to_convert:
		location = elem.getroottree().getpath(elem)
		segments = tools.svg_normalizer.transform_geometry.shape_to_segments(elem, location)
		if segments is None:
			# Missing required attributes -- leave element as-is (treated as no
			# drawable geometry by compute_bbox, consistent with element_bbox).
			continue
		# Rewrite the element in-place as a <path> with no transform.
		tools.svg_normalizer.transform_geometry._convert_shape_element_to_path(elem, segments)


#============================================
def _collect_shapes(
	elem: lxml.etree._Element,
	in_defs: bool,
	out: list[lxml.etree._Element],
) -> None:
	"""Recursively collect shape elements outside <defs> into out.

	Args:
		elem: Current element.
		in_defs: True when elem is inside a <defs> subtree.
		out: List to append matching elements to.
	"""
	if not isinstance(elem.tag, str):
		return
	tag = tools.svg_normalizer.model.local_name(elem.tag)
	entering_defs = in_defs or tag == "defs"
	# Shapes in defs are paint/clip space -- skip them.
	if (
		not entering_defs
		and tag in {"rect", "circle", "ellipse", "line", "polyline", "polygon"}
		and not (tag == "rect" and elem.get("id") == tools.svg_normalizer.model.RUNTIME_BOUNDS_RECT_ID)
	):
		out.append(elem)
		# Basic shapes have no element children to recurse into.
		return
	for child in elem:
		_collect_shapes(child, entering_defs, out)


#============================================
def format_points(points: list[tuple[float, float]], dx: float, dy: float) -> str:
	# Use tools.svg_normalizer.model.fmt_precise for emitted point coordinates (A4 precision).
	return " ".join(f"{tools.svg_normalizer.model.fmt_precise(x + dx)},{tools.svg_normalizer.model.fmt_precise(y + dy)}" for x, y in points)


# Default stroke-related SVG property values (SVG spec).
_DEFAULT_STROKE_WIDTH = 1.0
_DEFAULT_MITERLIMIT = 4.0

# Inline style property regex: matches "prop: value" pairs (separated by ;).
_STYLE_PROP_RE = re.compile(r"(?:^|;)\s*([\w-]+)\s*:\s*([^;]+?)(?=\s*(?:;|$))")


#============================================
def _parse_inline_style(style: str) -> dict[str, str]:
	"""Parse an SVG inline style= attribute into a {prop: value} dict.

	Only parses the flat key:value structure; does not apply cascade.

	Args:
		style: The raw style= attribute value.

	Returns:
		Dict of lowercase property name to stripped value string.
	"""
	props: dict[str, str] = {}
	for match in _STYLE_PROP_RE.finditer(style):
		props[match.group(1).lower().strip()] = match.group(2).strip()
	return props


def _resolved_property(elem: lxml.etree._Element, prop: str) -> str | None:
	"""Resolve one inline-style or presentation property on an element."""
	inline = _parse_inline_style(elem.get('style') or '')
	if prop in inline:
		return inline[prop]
	return elem.get(prop)


#============================================
def _resolve_stroke_props(elem: lxml.etree._Element) -> dict[str, str]:
	"""Resolve stroke presentation properties for one element (inline cascade only).

	Per the v3 support contract (CSS scope: inline-only cascade), only inline
	style= and presentation attributes are checked. Presentation attributes are
	the fallback when the inline style does not set a property. No class/stylesheet
	resolution.

	Properties resolved: stroke, stroke-width, stroke-linecap, stroke-linejoin,
	stroke-miterlimit.

	Args:
		elem: The SVG element.

	Returns:
		Dict of resolved property values. Keys present only when found on this
		element. Values are raw strings.
	"""
	# Read inline style block first (higher specificity than presentation attrs).
	style_str = elem.get("style") or ""
	inline = _parse_inline_style(style_str)
	result: dict[str, str] = {}
	stroke_props = (
		"stroke", "stroke-width", "stroke-linecap",
		"stroke-linejoin", "stroke-miterlimit",
	)
	for prop in stroke_props:
		# Inline style wins over presentation attribute.
		if prop in inline:
			result[prop] = inline[prop]
		else:
			val = elem.get(prop)
			if val is not None:
				result[prop] = val
	return result


#============================================
def _path_is_open(segments: list[tools.svg_normalizer.model.PathSegment]) -> bool:
	"""Return True when a non-empty absolute path does not end with a Z segment.

	An open path has exposed endpoints that the round/square linecap extends.
	Butt linecap (SVG default) does not extend endpoints, so this only matters
	for round or square linecap values. An empty path is treated as closed
	(no endpoint extension).

	Args:
		segments: Absolute tools.svg_normalizer.model.PathSegment list.

	Returns:
		True when segments is non-empty and the last segment is not Z.
	"""
	return bool(segments) and segments[-1].cmd != "Z"


#============================================
def _stroke_padded_bbox(geom_bbox: tools.svg_normalizer.model.BBox, elem: lxml.etree._Element) -> tools.svg_normalizer.model.BBox:
	"""Expand a geometry bbox by the visible stroke envelope for one element.

	Implements the plan A3 stroke-pad rule:
	  pad = stroke_width / 2 * max(1, miterlimit)
	  round/square linecap: open path endpoints additionally extend by
	    stroke_width / 2 on each end (captured here by including the endpoint
	    pad in the uniform bbox expansion, which is conservative for non-trivial
	    paths but correct for the bbox contract).
	  butt linecap (default): no endpoint extension.
	  dashed strokes: treated as solid envelope (same pad).
	  markers: not padded (markers are rejected by the classifier).
	  vector-effect=non-scaling-stroke: stroke is already unscaled in root coords
	    (elements that cannot be resolved are rejected by flatten_transforms before
	    bbox is computed); pad uses stroke-width directly.

	Args:
		geom_bbox: The pure geometry bbox for this element.
		elem: The SVG element (already in root coordinates after flattening).

	Returns:
		Geometry bbox expanded by the visible stroke envelope. When the element
		has no visible stroke, returns geom_bbox unchanged.
	"""
	props = _resolve_stroke_props(elem)
	stroke = props.get("stroke")
	# No stroke or explicitly none/transparent -> no pad.
	if stroke is None or stroke.lower() in {"none", "transparent"}:
		return geom_bbox

	# Resolve stroke-width (default 1 when stroke is set but width is not).
	sw_raw = props.get("stroke-width")
	if sw_raw is None:
		stroke_width = _DEFAULT_STROKE_WIDTH
	else:
		stroke_width = tools.svg_normalizer.model.parse_float(sw_raw, _DEFAULT_STROKE_WIDTH)
	if stroke_width <= 0.0:
		return geom_bbox

	# Resolve miterlimit (default 4; only relevant for miter linejoin).
	linejoin = props.get("stroke-linejoin", "miter").lower()
	if linejoin == "miter":
		ml_raw = props.get("stroke-miterlimit")
		if ml_raw is None:
			miterlimit = _DEFAULT_MITERLIMIT
		else:
			miterlimit = tools.svg_normalizer.model.parse_float(ml_raw, _DEFAULT_MITERLIMIT)
	else:
		miterlimit = 1.0  # round/bevel: no miter extension beyond stroke_width/2

	# Core pad: half stroke width * max(1, miterlimit).
	pad = stroke_width / 2.0 * max(1.0, miterlimit)

	# Linecap extension for open paths: round and square extend endpoints
	# by stroke_width/2. Butt (default) does not.
	linecap = props.get("stroke-linecap", "butt").lower()
	if linecap in {"round", "square"}:
		# Parse the path d to determine if it is open (needs endpoint pad).
		# By the time bbox is computed, shapes have been converted to paths,
		# so elem should be a <path>. If not, fall through without endpoint pad.
		d_attr = elem.get("d")
		if d_attr:
			segments = tools.svg_normalizer.model.parse_path_to_absolute(d_attr)
			if _path_is_open(segments):
				# Round/square linecap extends each open endpoint by stroke_width/2
				# BEYOND the miter-join pad. This is additive (not max) so that an
				# open path with round/square always produces a strictly larger bbox
				# than the same path with butt linecap. Butt linecap keeps no
				# endpoint extension.
				endpoint_pad = stroke_width / 2.0
				pad += endpoint_pad

	# Expand the geometry bbox symmetrically in all four directions.
	padded = tools.svg_normalizer.model.BBox(
		geom_bbox.min_x - pad,
		geom_bbox.min_y - pad,
		geom_bbox.max_x + pad,
		geom_bbox.max_y + pad,
	)
	return padded


#============================================
def _element_geometry_bbox(elem: lxml.etree._Element) -> "tools.svg_normalizer.model.BBox | str | None":
	"""Compute the pure geometry bbox of a single SVG shape element (no stroke pad).

	Returns:
		tools.svg_normalizer.model.BBox for a fully resolvable shape.
		tools.svg_normalizer.model._UNIT_SENTINEL (str) when a REQUIRED size attribute carries a non-user-unit
		  (%, mm, cm, in, pt, pc, em, ex).
		None for non-shape tags, hidden elements, and shapes with absent/bad
		  required attributes.
	"""
	tag = tools.svg_normalizer.model.local_name(elem.tag)
	if tag not in tools.svg_normalizer.model.SHAPE_TAGS:
		return None
	# Visibility checks resolve through the inline-only cascade (style= wins over
	# the presentation attribute) so style="display:none" and
	# style="fill:none;stroke:none" exclude the element from the bbox, matching
	# the bare-attribute semantics. fill:none alone with a visible stroke still
	# contributes geometry; both none -> excluded.
	if _resolved_property(elem, "display") == "none":
		return None
	if _resolved_property(elem, "fill") == "none" and _resolved_property(elem, "stroke") == "none":
		return None

	if tag == "path":
		d_attr = elem.get("d")
		if not d_attr:
			return None
		return tools.svg_normalizer.model.path_bbox_from_segments(tools.svg_normalizer.model.parse_path_to_absolute(d_attr))

	if tag == "rect":
		# x/y default to 0 per SVG spec; width/height are required.
		# A % or other non-user unit is an UNSUPPORTED_UNIT rejection (not phantom 0).
		x = tools.svg_normalizer.model.parse_float(elem.get("x"))
		y = tools.svg_normalizer.model.parse_float(elem.get("y"))
		w = tools.svg_normalizer.model.parse_float_required(elem.get("width"))
		h = tools.svg_normalizer.model.parse_float_required(elem.get("height"))
		if w is tools.svg_normalizer.model._UNIT_SENTINEL or h is tools.svg_normalizer.model._UNIT_SENTINEL:
			# Return the sentinel so the caller can build the rejection.
			return tools.svg_normalizer.model._UNIT_SENTINEL
		if w is None or h is None:
			return None
		# w and h are floats at this point.
		return tools.svg_normalizer.model.BBox(x, y, x + float(w), y + float(h))

	if tag == "circle":
		# cx/cy default to 0 per SVG spec; r is required.
		cx = tools.svg_normalizer.model.parse_float(elem.get("cx"))
		cy = tools.svg_normalizer.model.parse_float(elem.get("cy"))
		r = tools.svg_normalizer.model.parse_float_required(elem.get("r"))
		if r is tools.svg_normalizer.model._UNIT_SENTINEL:
			return tools.svg_normalizer.model._UNIT_SENTINEL
		if r is None:
			return None
		r_f = float(r)
		return tools.svg_normalizer.model.BBox(cx - r_f, cy - r_f, cx + r_f, cy + r_f)

	if tag == "ellipse":
		# cx/cy default to 0 per SVG spec; rx/ry are required.
		cx = tools.svg_normalizer.model.parse_float(elem.get("cx"))
		cy = tools.svg_normalizer.model.parse_float(elem.get("cy"))
		rx = tools.svg_normalizer.model.parse_float_required(elem.get("rx"))
		ry = tools.svg_normalizer.model.parse_float_required(elem.get("ry"))
		if rx is tools.svg_normalizer.model._UNIT_SENTINEL or ry is tools.svg_normalizer.model._UNIT_SENTINEL:
			return tools.svg_normalizer.model._UNIT_SENTINEL
		if rx is None or ry is None:
			return None
		rx_f = float(rx)
		ry_f = float(ry)
		return tools.svg_normalizer.model.BBox(cx - rx_f, cy - ry_f, cx + rx_f, cy + ry_f)

	if tag == "line":
		# If NONE of the four endpoint attrs are authored, the line contributes
		# no geometry (consistent with rect/circle required-attr handling).
		# Per SVG spec x1/y1/x2/y2 all default to 0 when absent, so if at least
		# one is authored we use that spec default for the missing ones.
		has_any = any(elem.get(a) is not None for a in ("x1", "y1", "x2", "y2"))
		if not has_any:
			return None
		x1 = tools.svg_normalizer.model.parse_float(elem.get("x1"))
		y1 = tools.svg_normalizer.model.parse_float(elem.get("y1"))
		x2 = tools.svg_normalizer.model.parse_float(elem.get("x2"))
		y2 = tools.svg_normalizer.model.parse_float(elem.get("y2"))
		return tools.svg_normalizer.model.BBox(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))

	if tag in {"polyline", "polygon"}:
		points = tools.svg_normalizer.model.parse_points(elem.get("points", ""))
		if not points:
			return None
		xs = [p[0] for p in points]
		ys = [p[1] for p in points]
		return tools.svg_normalizer.model.BBox(min(xs), min(ys), max(xs), max(ys))

	if tag == "text":
		# Text elements are rejected by classify() (A5 TEXT_UNSUPPORTED) before
		# bbox is ever computed. Return None here so that if a text element somehow
		# reaches bbox computation it is silently skipped rather than contributing
		# a phantom zero-size point (previously v2 returned a zero-size bbox).
		return None

	return None


#============================================
def element_bbox(elem: lxml.etree._Element) -> "tools.svg_normalizer.model.BBox | str | None":
	"""Compute the stroke-padded bounding box of a single SVG shape element.

	Returns the geometry bbox expanded by the visible stroke envelope (A3).
	When the element has no visible stroke the geometry bbox is returned unchanged.

	Returns:
		tools.svg_normalizer.model.BBox (possibly stroke-padded) for a fully resolvable shape.
		tools.svg_normalizer.model._UNIT_SENTINEL (str) when a REQUIRED size attribute carries a non-user-unit.
		None for non-shape tags, hidden elements, and shapes with absent/bad
		  required attributes.
	"""
	geom = _element_geometry_bbox(elem)
	# Propagate sentinel and None unchanged; only pad real tools.svg_normalizer.model.BBox instances.
	if geom is None or geom is tools.svg_normalizer.model._UNIT_SENTINEL:
		return geom
	return _stroke_padded_bbox(geom, elem)


#============================================
def compute_bbox(root: lxml.etree._Element) -> tools.svg_normalizer.model.BBox:
	"""Compute the drawn bounding box of every visible shape under root.

	Backend note: this iterates lxml elements but delegates all geometry math to
	the backend-agnostic helpers (element_bbox -> tools.svg_normalizer.model.path_bbox_from_segments ->
	arc_extrema). Later WPs that flatten transforms feed already-flattened
	coordinates through these same helpers.

	Args:
		root: The parsed SVG root element.

	Returns:
		The union tools.svg_normalizer.model.BBox of all drawable elements.

	Raises:
		ValueError: When no drawable SVG elements are found.
	"""
	bbox: tools.svg_normalizer.model.BBox | None = None
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			# Skip comments and processing instructions (lxml yields these).
			continue
		# Definitions are paint, clip, and runtime-anchor resources, not rendered
		# artwork.  Their geometry must not influence the visible crop.
		if _is_definition_content(elem):
			continue
		eb = element_bbox(elem)
		if eb is None:
			continue
		if eb is tools.svg_normalizer.model._UNIT_SENTINEL:
			# A required size attribute carries a non-user unit (%, mm, cm, ...).
			# Build an XPath-like location string for the rejection report.
			location = elem.getroottree().getpath(elem)
			raise tools.svg_normalizer.model.UnsupportedUnitError(location)
		bbox = eb if bbox is None else bbox.union(eb)
	if bbox is None:
		raise ValueError("No drawable SVG elements found")
	return bbox


#============================================
def _is_definition_content(elem: lxml.etree._Element) -> bool:
	"""Return True when elem is nested in a SVG <defs> resource subtree."""
	node: lxml.etree._Element | None = elem
	while node is not None:
		if isinstance(node.tag, str) and tools.svg_normalizer.model.local_name(node.tag) == "defs":
			return True
		node = node.getparent()
	return False


#============================================
def _shift_userspace_paint(elem: lxml.etree._Element, dx: float, dy: float) -> None:
	"""Shift a userSpaceOnUse gradient/pattern by (dx, dy) in ROOT space.

	A userSpaceOnUse paint resolves its coordinate attributes (cx/cy/r/fx/fy or
	x1/y1/x2/y2; pattern x/y/width/height) THROUGH its gradientTransform /
	patternTransform. After transform flattening (transform_userspace_paints)
	that transform already holds the baked element matrix M, so the paint paints
	at M * coords. The crop-to-origin pass then shifts all geometry by (dx, dy)
	in root space; to keep the paint aligned, the SAME root-space shift must be
	applied to the paint OUTPUT, i.e. translate(dx, dy) is prepended to the paint
	transform (new = T(dx,dy) * existing).

	Adding (dx, dy) to the raw coordinate attributes instead is WRONG: those
	attributes are pre-transform, so the shift would be re-scaled (and re-skewed)
	by the paint transform and the paint would land off the geometry, collapsing
	to a single stop color (the cpu.svg grey-out bug). This function is the
	coordinate-preserving correction.

	Args:
		elem: The userSpaceOnUse gradient or pattern element. Modified in place.
		dx, dy: The root-space crop-to-origin shift.
	"""
	transform_attr = "patternTransform" if tools.svg_normalizer.model.local_name(elem.tag) == "pattern" else "gradientTransform"
	translate = (1.0, 0.0, 0.0, 1.0, dx, dy)
	existing = elem.get(transform_attr)
	composed = translate
	if existing is not None and existing.strip() != "":
		location = elem.getroottree().getpath(elem)
		items = tools.svg_normalizer.transform_geometry.parse_transform_list(existing, location)
		existing_matrix = tools.svg_normalizer.transform_geometry.transforms_multiply(items, location)
		composed = tools.svg_normalizer.transform_geometry.multiply_matrices(translate, existing_matrix)
		elem.set(transform_attr, tools.svg_normalizer.model.matrix_to_transform_str(composed))


#============================================
def _is_userspace_paint_element(elem: lxml.etree._Element) -> bool:
	"""Return True for a gradient/pattern explicitly in userSpaceOnUse units."""
	tag = tools.svg_normalizer.model.local_name(elem.tag)
	if tag not in tools.svg_normalizer.model._USERSPACE_PAINT_TAGS:
		return False
	units_attr = "patternUnits" if tag == "pattern" else "gradientUnits"
	units = elem.get(units_attr)
	return units is not None and units.strip() == "userSpaceOnUse"


#============================================
def shift_element(elem: lxml.etree._Element, dx: float, dy: float) -> None:
	tag = tools.svg_normalizer.model.local_name(elem.tag)
	# Gradient/pattern paint elements are never shifted by adding (dx,dy) to their
	# coordinate attributes. userSpaceOnUse paints resolve THROUGH their paint
	# transform, so the crop shift is prepended to that transform instead.
	# objectBoundingBox paints (the default) use bbox-relative 0..1 fractions and
	# are crop-invariant, so they are left untouched entirely. Shifting either
	# coordinate set directly mis-places the paint (the cpu.svg grey-out bug).
	if tools.svg_normalizer.model.local_name(elem.tag) in tools.svg_normalizer.model._USERSPACE_PAINT_TAGS:
		if _is_userspace_paint_element(elem):
			_shift_userspace_paint(elem, dx, dy)
		return
	if tag == "path" and elem.get("d"):
		segments = tools.svg_normalizer.model.parse_path_to_absolute(elem.get("d"))
		elem.set("d", tools.svg_normalizer.model.path_segments_to_d(segments, dx, dy))
		return
	if tag in {"polyline", "polygon"} and elem.get("points"):
		elem.set("points", format_points(tools.svg_normalizer.model.parse_points(elem.get("points")), dx, dy))
		return
	for attr in tools.svg_normalizer.model.COORD_ATTRS_X:
		val = elem.get(attr)
		if val is not None:
			# Use tools.svg_normalizer.model.fmt_precise for emitted geometry coordinates (A4 precision).
			elem.set(attr, tools.svg_normalizer.model.fmt_precise(tools.svg_normalizer.model.parse_float(val) + dx))
	for attr in tools.svg_normalizer.model.COORD_ATTRS_Y:
		val = elem.get(attr)
		if val is not None:
			elem.set(attr, tools.svg_normalizer.model.fmt_precise(tools.svg_normalizer.model.parse_float(val) + dy))
