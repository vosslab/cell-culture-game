"""Flatten supported clip paths and reject unsupported clipping or style geometry."""

import lxml.etree
import shapely.geometry
import tinycss2

import tools.svg_normalizer.clip_geometry
import tools.svg_normalizer.geometry
import tools.svg_normalizer.model
import tools.svg_normalizer.sanitization
import tools.svg_normalizer.transform_geometry


def flatten_clip_paths(root: lxml.etree._Element) -> None:
	"""Flatten every simple clip-path reference into the target's path geometry (A6).

	Runs AFTER flatten_transforms + convert_shapes_to_paths so both target and
	clip geometry are absolute root-coordinate paths/shapes. For each visible
	element carrying clip-path="url(#cid)":
	  - resolve <clipPath id=cid>; enforce the simple-clip allowlist;
	  - compute target-geometry INTERSECT clip-geometry via shapely (curves
	    flattened to polylines within tools.svg_normalizer.clip_geometry._CLIP_FLATTEN_TOLERANCE);
	  - set the target's d to the clipped path data (empty d when the
	    intersection is empty), handling Polygon and MultiPolygon (holes emitted
	    as reverse-wound subpaths);
	  - remove the clip-path attribute.
	After all references are processed, remove every ordinary <clipPath> def that
	is no longer referenced anywhere.  The closed runtime material anchor remains
	available even though it is referenced only after DOM injection.

	Args:
		root: The parsed (transform-flattened, shape-converted) SVG root. Modified
			in place.

	Raises:
		tools.svg_normalizer.transform_geometry.ComplexClipError: When any clip-path usage is outside the simple allowlist.
	"""
	# Map clipPath id -> element, scanning the whole tree (clipPaths live in defs).
	clip_defs: dict[str, lxml.etree._Element] = {}
	for elem in root.iter():
		if isinstance(elem.tag, str) and tools.svg_normalizer.model.local_name(elem.tag) == "clipPath":
			cid = elem.get("id")
			if cid is not None:
				clip_defs[cid] = elem

	# Collect target elements first (do not mutate the tree while iterating).
	targets: list[tuple[lxml.etree._Element, str]] = []
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		if tools.svg_normalizer.model.local_name(elem.tag) == "clipPath":
			# Skip clip definitions themselves; only visible targets are processed.
			continue
		clip_ref = _resolved_property(elem, "clip-path")
		if clip_ref is None or clip_ref.strip().lower() in {"", "none"}:
			continue
		cid = _clip_ref_id(clip_ref)
		if cid is None:
			location = elem.getroottree().getpath(elem)
			raise tools.svg_normalizer.transform_geometry.ComplexClipError(location, f"unparseable clip-path {clip_ref!r}")
		targets.append((elem, cid))

	for elem, cid in targets:
		location = elem.getroottree().getpath(elem)
		clip_elem = clip_defs.get(cid)
		if clip_elem is None:
			# A clip-path pointing at a missing/non-clipPath id: the S1 gate would
			# otherwise reject; treat as complex (cannot flatten an absent clip).
			raise tools.svg_normalizer.transform_geometry.ComplexClipError(location, f"clip-path references unknown id #{cid}")
		_flatten_one_clip(elem, clip_elem, location)

	# Remove clipPath defs that are no longer referenced anywhere (S1-safe).
	_remove_unreferenced_clip_defs(root)


#============================================
def _composed_clip_matrix(
	clip_child: lxml.etree._Element, clip_elem: lxml.etree._Element, location: str,
) -> tuple[float, ...]:
	"""Compose the transform chain from the clipPath down to its geometry child.

	clipPath content lives in <defs>, which flatten_transforms intentionally
	skips, so a transform on the clip child (or on the clipPath element itself)
	is still live and must be applied to put the clip geometry in root
	coordinates. The chain is composed outermost-first: clipPath transform, then
	the child transform.

	Args:
		clip_child: The single geometry child of the clipPath.
		clip_elem: The <clipPath> element.
		location: XPath-like location for error reporting.

	Returns:
		The composed 6-tuple affine matrix (identity when no transforms present).

	Raises:
		tools.svg_normalizer.transform_geometry.ComplexClipError: When a transform on the clip chain cannot be parsed.
	"""
	# Build the ancestor chain from clipPath (outermost) down to the clip child.
	chain: list[lxml.etree._Element] = []
	node: lxml.etree._Element | None = clip_child
	while node is not None:
		chain.append(node)
		if node is clip_elem:
			break
		node = node.getparent()
	chain.reverse()
	matrix = tools.svg_normalizer.model.IDENTITY_MATRIX
	for elem in chain:
		transform_attr = tools.svg_normalizer.transform_geometry._is_geometry_transform_attr(elem)
		if transform_attr is None:
			continue
		try:
			items = tools.svg_normalizer.transform_geometry.parse_transform_list(transform_attr, location)
			this_matrix = tools.svg_normalizer.transform_geometry.transforms_multiply(items, location)
		except tools.svg_normalizer.transform_geometry.UnsupportedTransformError as exc:
			# A transform v3 cannot flatten inside a clip makes the clip complex.
			raise tools.svg_normalizer.transform_geometry.ComplexClipError(location, f"clip transform unsupported: {exc.detail}")
		matrix = tools.svg_normalizer.transform_geometry.multiply_matrices(matrix, this_matrix)
	return matrix


#============================================
def _clip_polygon_for_flatten(
	clip_elem: lxml.etree._Element, location: str,
) -> "shapely.geometry.base.BaseGeometry":
	"""Build the clip region polygon in root coordinates from a simple clipPath.

	Enforces the simple-clip-side allowlist via tools.svg_normalizer.clip_geometry._clip_child_geometry_node (which
	rejects multi-child, nested, forbidden-child, and objectBoundingBox clips),
	then composes any live transform on the clip chain and applies the clip-rule.
	This is the single source of the clip polygon shared by the no-op containment
	test and the fall-through intersection.

	Args:
		clip_elem: The resolved <clipPath> element.
		location: XPath-like location of the target (for errors).

	Returns:
		A shapely polygon for the clip region (possibly empty).

	Raises:
		tools.svg_normalizer.transform_geometry.ComplexClipError: When the clip side is outside the simple allowlist.
	"""
	clip_child = tools.svg_normalizer.clip_geometry._clip_child_geometry_node(clip_elem, location)
	clip_child_location = clip_child.getroottree().getpath(clip_child)
	clip_segments = tools.svg_normalizer.transform_geometry.shape_to_segments(clip_child, clip_child_location)
	if not clip_segments:
		raise tools.svg_normalizer.transform_geometry.ComplexClipError(location, "clipPath child has no usable geometry")
	# The clipPath lives in defs, so flatten_transforms never baked the clip
	# child's own transform (or transforms on ancestors up to the clipPath) into
	# its geometry. Compose that transform chain now and apply it so the clip
	# geometry is in root coordinates, matching the already-flattened target.
	clip_matrix = _composed_clip_matrix(clip_child, clip_elem, clip_child_location)
	if not tools.svg_normalizer.transform_geometry.matrix_is_identity(clip_matrix):
		clip_segments = tools.svg_normalizer.transform_geometry.apply_matrix_to_segments(clip_segments, clip_matrix)
	clip_rule = tools.svg_normalizer.clip_geometry._resolve_fill_rule(clip_child, "clip-rule")
	return tools.svg_normalizer.clip_geometry._polygon_from_segments(clip_segments, clip_rule, tools.svg_normalizer.clip_geometry._CLIP_FLATTEN_TOLERANCE)


#============================================
def _clip_is_noop(
	clip_poly: "shapely.geometry.base.BaseGeometry",
	target_envelope: "shapely.geometry.base.BaseGeometry",
) -> bool:
	"""Return True when the clip region fully contains the target's painted envelope.

	The clip polygon is SHRUNK by _CLIP_NOOP_MARGIN before the containment
	test. A no-op fires only when the target fits inside the clip with this margin
	to spare. Shrinking makes the test CONSERVATIVE (harder to pass): a target
	that protrudes even a sub-pixel amount past the clip edge fails the test and
	the clip is kept. This guards against polyline-approximation slop on the clip
	boundary causing a genuine trim to be misread as a no-op.

	When the shrunk clip collapses to empty geometry (very thin clip polygon),
	the test conservatively returns False (not a no-op).

	An empty clip or empty envelope is never a no-op (an empty clip would
	clip everything away, not nothing).

	Args:
		clip_poly: The clip region polygon (root coordinates).
		target_envelope: The target's painted envelope (filled + stroke).

	Returns:
		True when the clip changes nothing visible (a dead page-bounds clip).
	"""
	if clip_poly.is_empty or target_envelope.is_empty:
		return False
	# Shrink the clip by the margin; if it collapses, keep the clip (conservative).
	shrunk = clip_poly.buffer(-(2.0 * tools.svg_normalizer.clip_geometry._CLIP_FLATTEN_TOLERANCE))
	if shrunk.is_empty:
		return False
	return bool(shrunk.contains(target_envelope))


#============================================
def _flatten_one_clip(
	elem: lxml.etree._Element, clip_elem: lxml.etree._Element, location: str,
) -> None:
	"""Flatten one target/clip pair: intersect, drop a no-op ref, or reject.

	The clip side must be a simple clip (else tools.svg_normalizer.transform_geometry.ComplexClipError). For the target:
	  - no-op clip (region already contains the painted target): drop the
	    clip-path reference and leave the target d UNCHANGED. This is render-
	    identical by construction (intersecting a shape with a region that
	    contains it returns the shape) and avoids any precision loss. Runs for
	    both filled and stroke-only targets.
	  - filled target, genuinely clipped: emit the target INTERSECT clip as the
	    new d (existing behavior).
	  - stroke-only target, genuinely clipped: tools.svg_normalizer.transform_geometry.ComplexClipError (a real stroke
	    trim needs stroke-to-path expansion, which is out of scope).

	Args:
		elem: The clipped target element (a <path> after shape conversion).
		clip_elem: The resolved <clipPath> element.
		location: XPath-like location of the target (for errors).

	Raises:
		tools.svg_normalizer.transform_geometry.ComplexClipError: When the allowlist fails or a genuine stroke trim is hit.
	"""
	# Target geometry (no fill check) and the simple-clip-side polygon. The clip
	# polygon build raises tools.svg_normalizer.transform_geometry.ComplexClipError for any complex clip side, so a
	# complex clip is rejected even when the target would otherwise be a no-op.
	target_segments = tools.svg_normalizer.clip_geometry._target_segments_for_clip(elem, location)
	clip_poly = _clip_polygon_for_flatten(clip_elem, location)

	# No-op short circuit: the painted target envelope is fully inside the clip.
	target_envelope = tools.svg_normalizer.clip_geometry._target_envelope_polygon(elem, target_segments)
	if _clip_is_noop(clip_poly, target_envelope):
		# Render-identical drop: keep the target d, just remove the dead clip ref.
		_remove_clip_path_reference(elem)
		return

	# Not a no-op. A stroke-only target would need a genuine stroke trim, which
	# v3 does not support; reject it as complex (matches the prior behavior).
	if tools.svg_normalizer.clip_geometry._target_is_stroke_only(elem):
		raise tools.svg_normalizer.transform_geometry.ComplexClipError(location, "clip target is stroke-only (fill:none)")

	# Filled target genuinely clipped: emit target INTERSECT clip as the new d.
	target_rule = tools.svg_normalizer.clip_geometry._resolve_fill_rule(elem, "fill-rule")
	target_poly = tools.svg_normalizer.clip_geometry._polygon_from_segments(target_segments, target_rule, tools.svg_normalizer.clip_geometry._CLIP_FLATTEN_TOLERANCE)
	if target_poly.is_empty or clip_poly.is_empty:
		# Degenerate input geometry: nothing fillable to clip.
		clipped = shapely.geometry.Polygon()
	else:
		clipped = shapely.make_valid(target_poly.intersection(clip_poly))

	# Emit the clipped geometry as absolute path data (empty string when empty).
	new_d = tools.svg_normalizer.clip_geometry._geometry_to_path_d(clipped)
	if new_d:
		elem.set("d", new_d)
	else:
		# Empty intersection: the element keeps no drawable geometry. Set an empty
		# d so the element contributes nothing to the bbox; compute_bbox treats a
		# path with no segments as no geometry (EMPTY_GEOMETRY applies only when
		# the whole document has none).
		elem.set("d", "")
	# Drop the now-applied clip reference (presentation attr and inline style).
	_remove_clip_path_reference(elem)


#============================================
def _clip_ref_id(clip_ref: str) -> str | None:
	"""Extract the fragment id from a clip-path value, or None.

	Accepts url(#id), url('#id'), url("#id"). A bare #id is not valid clip-path
	syntax and returns None.
	"""
	match = tools.svg_normalizer.sanitization._URL_REF_RE.search(clip_ref)
	if match:
		return match.group(1)
	return None


#============================================
def _remove_clip_path_reference(elem: lxml.etree._Element) -> None:
	"""Remove the clip-path reference from an element (attribute and inline style)."""
	if elem.get("clip-path") is not None:
		del elem.attrib["clip-path"]
	style_str = elem.get("style")
	if style_str:
		props = tools.svg_normalizer.geometry._parse_inline_style(style_str)
		if "clip-path" in props:
			del props["clip-path"]
			# Rebuild the style string without the clip-path declaration.
			if props:
				elem.set("style", "; ".join(f"{k}: {v}" for k, v in props.items()))
			else:
				del elem.attrib["style"]


#============================================
def _remove_unreferenced_clip_defs(root: lxml.etree._Element) -> None:
	"""Remove <clipPath> defs no longer referenced by any clip-path in the tree.

	S1-safe: a clipPath whose id still appears in some clip-path reference is
	kept; only fully-unreferenced ordinary clipPath defs are detached.  The closed
	runtime material anchor is also kept because the renderer references it only
	after DOM injection.  Removing other dead defs keeps the document free of
	dead resources without creating a dangling reference.

	Args:
		root: The parsed SVG root element. Modified in place.
	"""
	# Collect every clip-path id still referenced anywhere.
	referenced: set[str] = set()
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		clip_ref = _resolved_property(elem, "clip-path")
		if clip_ref is None:
			continue
		cid = _clip_ref_id(clip_ref)
		if cid is not None:
			referenced.add(cid)
	# Detach clipPath defs whose id is neither locally referenced nor a closed
	# runtime material anchor.
	to_remove: list[lxml.etree._Element] = []
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		if tools.svg_normalizer.model.local_name(elem.tag) != "clipPath":
			continue
		cid = elem.get("id")
		if cid is None or (cid not in referenced and cid not in tools.svg_normalizer.model.RUNTIME_EXTERNAL_CLIP_IDS):
			to_remove.append(elem)
	for elem in to_remove:
		parent = elem.getparent()
		if parent is not None:
			parent.remove(elem)


#============================================
def _detect_clippath(root: lxml.etree._Element) -> tools.svg_normalizer.model.RejectionReason | None:
	"""Detect only COMPLEX clip-path usage; simple clips are flattened, not rejected.

	The simple-clip allowlist permits the supported cases while the classifier rejects
	actual flattening (and the complex-clip rejection) is performed by
	flatten_clip_paths inside normalize_svg_file, which raises tools.svg_normalizer.transform_geometry.ComplexClipError ->
	CLIPPATH_UNSUPPORTED_COMPLEX for anything outside the allowlist. Because the
	flattening step is the authority on simple-vs-complex, this classifier no
	longer rejects clip-path on its own: doing so would wrongly refuse the simple
	unsupported clips.

	The function is kept in classify()'s detector list (signature unchanged) so
	the composition contract is preserved; it simply always returns None now. The
	real verdict comes from flatten_clip_paths.

	Args:
		root: The parsed SVG root element.

	Returns:
		Always None (clip handling moved to flatten_clip_paths).
	"""
	return None


# Geometry-affecting CSS properties. A <style> rule that sets any of these
# triggers STYLE_GEOMETRY_UNSUPPORTED (v3 resolves geometry from inline style
# only; a stylesheet rule would need a selector/specificity engine v3 does not
# have). Note: fill and fill-opacity ARE in this set and ARE rejected in a
# <style> rule -- they affect whether geometry is drawn (fill:none) and the
# floor-shadow signal, so v3 cannot leave them to an unresolved cascade. Only
# properties absent from this set (e.g. color, stop-color, paint-order) may
# remain in a preserved <style> block.
_STYLE_GEOMETRY_PROPS = frozenset({
	"display", "visibility", "opacity", "fill", "fill-opacity",
	"stroke", "stroke-width", "stroke-opacity", "vector-effect",
	"filter", "clip-path", "mask",
	"marker", "marker-start", "marker-mid", "marker-end",
})


#============================================
def _detect_style_geometry(root: lxml.etree._Element) -> tools.svg_normalizer.model.RejectionReason | None:
	"""Classify <style> blocks: reject geometry-affecting or unparseable CSS.

	Per the support contract, <style> blocks are preserved (paint/color rules
	stay) and only their url(#id) refs are rewritten on rename (F8). But a rule
	that sets a geometry-affecting property would change rendering in a way the
	inline-only cascade cannot resolve, so it is rejected
	(STYLE_GEOMETRY_UNSUPPORTED). A <style> block tinycss2 cannot parse is
	rejected (STYLE_UNPARSEABLE).

	Args:
		root: The parsed SVG root element.

	Returns:
		tools.svg_normalizer.model.RejectionReason (STYLE_UNPARSEABLE or STYLE_GEOMETRY_UNSUPPORTED) when a
		style block is unparseable or sets a geometry property, else None.
	"""
	for style_elem in tools.svg_normalizer.sanitization._iter_style_blocks(root):
		css_text = style_elem.text or ""
		location = style_elem.getroottree().getpath(style_elem)
		# tinycss2 is error-tolerant: it returns ParseError nodes rather than
		# raising. Treat any ParseError as STYLE_UNPARSEABLE.
		rules = tinycss2.parse_stylesheet(
			css_text, skip_comments=True, skip_whitespace=True
		)
		for node in rules:
			if node.type == "error":
				reason = tools.svg_normalizer.model.RejectionReason(
					code="STYLE_UNPARSEABLE",
					message="A <style> block could not be parsed as CSS.",
					fix="Repair or remove the malformed <style> block before ingestion.",
					element=location,
				)
				return reason
			# Only qualified rules (selector { declarations }) carry properties we
			# care about. At-rules (e.g. @font-face) are not geometry-affecting here.
			if node.type != "qualified-rule":
				continue
			geometry_reason = _style_rule_geometry_reason(node, location)
			if geometry_reason is not None:
				return geometry_reason
	return None


#============================================
def _style_rule_geometry_reason(
	rule: "tinycss2.ast.QualifiedRule", location: str,
) -> tools.svg_normalizer.model.RejectionReason | None:
	"""Return a STYLE_GEOMETRY_UNSUPPORTED reason if a CSS rule sets a geometry prop.

	Parses the rule's declaration block and checks each declared property name
	against _STYLE_GEOMETRY_PROPS.

	Args:
		rule: A tinycss2 qualified-rule node.
		location: XPath-like location of the owning <style> element.

	Returns:
		tools.svg_normalizer.model.RejectionReason when a geometry-affecting property is declared, else None.
	"""
	declarations = tinycss2.parse_declaration_list(
		rule.content, skip_comments=True, skip_whitespace=True
	)
	for decl in declarations:
		if decl.type == "error":
			# A malformed declaration inside an otherwise-parseable rule -> unparseable.
			reason = tools.svg_normalizer.model.RejectionReason(
				code="STYLE_UNPARSEABLE",
				message="A <style> declaration could not be parsed as CSS.",
				fix="Repair or remove the malformed <style> block before ingestion.",
				element=location,
			)
			return reason
		if decl.type != "declaration":
			continue
		prop_name = decl.lower_name
		if prop_name in _STYLE_GEOMETRY_PROPS:
			reason = tools.svg_normalizer.model.RejectionReason(
				code="STYLE_GEOMETRY_UNSUPPORTED",
				message=(
					f"A <style> rule sets the geometry-affecting property '{prop_name}'. "
					"v3 resolves geometry from inline style only."
				),
				fix=(
					"Move geometry-affecting properties to inline style= attributes "
					"(or bake them into the geometry) before ingestion."
				),
				element=location,
			)
			return reason
	return None


#============================================
def _detect_pattern(root: lxml.etree._Element) -> tools.svg_normalizer.model.RejectionReason | None:
	"""Classify <pattern> elements: preserve paint-only, reject anything with content.

	Per the support contract, a pattern is preserved only when it is paint-only:
	it has no child GEOMETRY, no images, no external refs, no transform, and no
	unresolved refs. Any pattern with child geometry (shapes/paths), an <image>,
	an external href, a patternTransform, or a transform is rejected with
	PATTERN_UNSUPPORTED (avoids a hidden pattern renderer). The image/external/
	transform cases are already caught by earlier detectors when they appear
	anywhere; this detector specifically catches a pattern whose CHILD content is
	drawable geometry (the case earlier detectors do not reject on their own).

	Args:
		root: The parsed SVG root element.

	Returns:
		tools.svg_normalizer.model.RejectionReason with code PATTERN_UNSUPPORTED when an unsupported pattern
		is found, else None.
	"""
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		if tools.svg_normalizer.model.local_name(elem.tag) != "pattern":
			continue
		location = elem.getroottree().getpath(elem)
		# A patternTransform makes the pattern non-paint-only for v3's purposes.
		if elem.get("patternTransform") is not None or elem.get("transform") is not None:
			reason = tools.svg_normalizer.model.RejectionReason(
				code="PATTERN_UNSUPPORTED",
				message="A <pattern> with a transform is not supported.",
				fix="Bake the pattern into explicit geometry before ingestion.",
				element=location,
			)
			return reason
		# Any drawable child geometry makes this a content pattern (would need a
		# pattern renderer to bbox correctly).
		for child in elem.iter():
			if child is elem or not isinstance(child.tag, str):
				continue
			child_tag = tools.svg_normalizer.model.local_name(child.tag)
			if child_tag in tools.svg_normalizer.model.SHAPE_TAGS or child_tag in {"image", "use"}:
				reason = tools.svg_normalizer.model.RejectionReason(
					code="PATTERN_UNSUPPORTED",
					message="A <pattern> with child geometry is not supported (no pattern renderer).",
					fix="Bake the pattern into explicit geometry before ingestion.",
					element=location,
				)
				return reason
	return None


#============================================
def _resolved_property(elem: lxml.etree._Element, prop: str) -> str | None:
	"""Return the value of a property from inline style= or presentation attribute.

	Inline-only cascade (per the v3 CSS scope): the inline style= block wins over
	the presentation attribute of the same name. No class/stylesheet resolution.

	Args:
		elem: The SVG element.
		prop: The property/attribute name (e.g. "filter", "clip-path").

	Returns:
		The resolved value string, or None when the property is set nowhere on
		this element.
	"""
	style_str = elem.get("style") or ""
	if style_str:
		inline = tools.svg_normalizer.geometry._parse_inline_style(style_str)
		if prop in inline:
			return inline[prop]
	return elem.get(prop)

#============================================
