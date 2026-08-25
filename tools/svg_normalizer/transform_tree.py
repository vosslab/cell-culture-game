"""Transform user-space paint definitions and recurse through SVG geometry."""

import lxml.etree

import tools.svg_normalizer.geometry
import tools.svg_normalizer.model
import tools.svg_normalizer.sanitization
import tools.svg_normalizer.transform_geometry


def _element_paint_ref_ids(elem: lxml.etree._Element) -> list[str]:
	"""Return the url(#id) fragment ids referenced by an element's fill/stroke.

	Resolves fill and stroke through the inline-only cascade (inline style= wins
	over the presentation attribute of the same name), matching the v3 CSS scope.
	Only paint references (fill/stroke) are returned; clip/mask/filter refs are
	handled by their own passes and are paint-space exempt here.

	Args:
		elem: The drawable element being flattened.

	Returns:
		List of fragment ids (without the leading #) for each url(#id) paint ref.
	"""
	ids: list[str] = []
	for prop in ("fill", "stroke"):
		value = tools.svg_normalizer.geometry._resolved_property(elem, prop)
		if not value:
			continue
		match = tools.svg_normalizer.sanitization._URL_REF_RE.search(value)
		if match is not None:
			ids.append(match.group(1))
	return ids


#============================================
def _userspace_paint_defs(root: lxml.etree._Element) -> dict[str, lxml.etree._Element]:
	"""Map id -> paint element for every userSpaceOnUse gradient/pattern in the tree.

	A gradient defaults to gradientUnits=objectBoundingBox and a pattern defaults
	to patternUnits=objectBoundingBox; only an explicit userSpaceOnUse value puts
	the paint in absolute (geometry) coordinate space and therefore needs to move
	with flattened geometry. objectBoundingBox paints are bbox-relative and
	transform-invariant, so they are not collected.

	Args:
		root: The parsed SVG root element.

	Returns:
		Dict mapping fragment id to the paint element (userSpaceOnUse only).
	"""
	defs: dict[str, lxml.etree._Element] = {}
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		tag = tools.svg_normalizer.model.local_name(elem.tag)
		if tag not in tools.svg_normalizer.model._USERSPACE_PAINT_TAGS:
			continue
		paint_id = elem.get("id")
		if paint_id is None:
			continue
		# gradientUnits applies to gradients; patternUnits applies to patterns.
		units_attr = "patternUnits" if tag == "pattern" else "gradientUnits"
		units = elem.get(units_attr)
		if units is not None and units.strip() == "userSpaceOnUse":
			defs[paint_id] = elem
	return defs


#============================================
def _collect_paint_referrers(
	root: lxml.etree._Element,
) -> dict[str, list[tuple[lxml.etree._Element, tuple[float, ...]]]]:
	"""Build paint-id -> [(referring element, composed matrix), ...] before flattening.

	Walks the tree exactly as _flatten_recurse does (composing the ancestor
	transform chain plus each element's own transform), recording the matrix that
	would be baked into each drawable element. For every paint reference on that
	element it appends a (element, matrix) entry under the paint's id. Built BEFORE
	any geometry mutation so the recorded matrices are the true flatten matrices,
	and so shared-paint safety can be decided up front.

	Defs content (gradients/clips/patterns) is paint/clip space and is skipped, so
	a paint referenced from inside another def is not counted as a geometry
	referrer.

	Args:
		root: The parsed SVG root element.

	Returns:
		Dict mapping paint fragment id to a list of (element, composed-matrix)
		tuples for each geometry element that references it.
	"""
	referrers: dict[str, list[tuple[lxml.etree._Element, tuple[float, ...]]]] = {}
	_collect_referrers_recurse(root, tools.svg_normalizer.model.IDENTITY_MATRIX, False, referrers)
	return referrers


#============================================
def _collect_referrers_recurse(
	elem: lxml.etree._Element,
	parent_matrix: tuple[float, ...],
	in_defs: bool,
	referrers: dict[str, list[tuple[lxml.etree._Element, tuple[float, ...]]]],
) -> None:
	"""Recursive worker for _collect_paint_referrers (mirrors _flatten_recurse)."""
	if not isinstance(elem.tag, str):
		return
	tag = tools.svg_normalizer.model.local_name(elem.tag)
	entering_defs = in_defs or tag == "defs"
	own_matrix = parent_matrix
	own_transform = tools.svg_normalizer.transform_geometry._is_geometry_transform_attr(elem) if not entering_defs else None
	if own_transform is not None:
		location = elem.getroottree().getpath(elem)
		items = tools.svg_normalizer.transform_geometry.parse_transform_list(own_transform, location)
		this_matrix = tools.svg_normalizer.transform_geometry.transforms_multiply(items, location)
		own_matrix = tools.svg_normalizer.transform_geometry.multiply_matrices(parent_matrix, this_matrix)
	# Record paint references on drawable leaves with their composed matrix.
	if (not entering_defs) and tag in tools.svg_normalizer.model.SHAPE_TAGS:
		for paint_id in _element_paint_ref_ids(elem):
			referrers.setdefault(paint_id, []).append((elem, own_matrix))
		return
	for child in list(elem):
		_collect_referrers_recurse(child, own_matrix, entering_defs, referrers)


#============================================
def _matrix_to_transform_str(matrix: tuple[float, ...]) -> str:
	"""Serialize a 6-tuple affine matrix as an SVG matrix(...) transform string."""
	parts = [tools.svg_normalizer.model.fmt_precise(component) for component in matrix]
	result = "matrix(" + ",".join(parts) + ")"
	return result


#============================================
def transform_userspace_paints(root: lxml.etree._Element) -> None:
	"""Move userSpaceOnUse gradients/patterns in sync with flattened geometry (Fix B).

	When transform flattening bakes a non-identity matrix M into an element that
	paints with a userSpaceOnUse gradient or pattern, the paint's absolute
	coordinates must move by the same M or the paint resolves out of bounds and
	collapses to its nearest stop color. The correct, paint-space-preserving fix
	is to prepend M to the paint's gradientTransform/patternTransform
	(new = M * existing); the paint's own coordinates and stops are left untouched.

	Shared-paint safety: a paint referenced by more than one geometry element, or
	by elements whose composed matrices differ, cannot have a single matrix baked
	into the shared def. Such a file is rejected upstream as UNSUPPORTED_TRANSFORM.

	Must run BEFORE the geometry recursion of flatten_transforms so the recorded
	matrices match the matrices the recursion will bake into geometry.

	Args:
		root: The parsed SVG root element. Modified in place.

	Raises:
		tools.svg_normalizer.transform_geometry.UnsupportedTransformError: When a userSpaceOnUse paint is shared by
			geometry under differing transforms (cannot bake one matrix safely).
	"""
	paint_defs = _userspace_paint_defs(root)
	if not paint_defs:
		return
	referrers = _collect_paint_referrers(root)
	for paint_id, paint_elem in paint_defs.items():
		uses = referrers.get(paint_id, [])
		# Only the non-identity referrers actually move the paint.
		moving = [(elem, m) for (elem, m) in uses if not tools.svg_normalizer.transform_geometry.matrix_is_identity(m)]
		if not moving:
			# Paint is unreferenced or only referenced by untransformed geometry;
			# its coordinates already align with the (unmoved) geometry.
			continue
		first_matrix = moving[0][1]
		# Shared-paint safety: more than one referrer always rejects regardless of
		# matrix values (one bake cannot satisfy two different element positions).
		# The divergence loop below only runs for the single-referrer case (len==1),
		# where it is a tautology and never fires; it is kept for defensive clarity.
		shared_unsafe = len(uses) > 1
		if not shared_unsafe:
			for _elem, matrix in uses:
				if not _matrices_equal(matrix, first_matrix):
					shared_unsafe = True
					break
		if shared_unsafe:
			location = paint_elem.getroottree().getpath(paint_elem)
			raise tools.svg_normalizer.transform_geometry.UnsupportedTransformError(
				location,
				"a userSpaceOnUse paint is shared by elements under differing "
				"transforms; pre-flatten the transform or give each element its "
				"own paint",
			)
		# Single-use paint: prepend M to its existing paint transform.
		transform_attr = "patternTransform" if tools.svg_normalizer.model.local_name(paint_elem.tag) == "pattern" else "gradientTransform"
		existing = paint_elem.get(transform_attr)
		composed = first_matrix
		if existing is not None and existing.strip() != "":
			location = paint_elem.getroottree().getpath(paint_elem)
			items = tools.svg_normalizer.transform_geometry.parse_transform_list(existing, location)
			existing_matrix = tools.svg_normalizer.transform_geometry.transforms_multiply(items, location)
			composed = tools.svg_normalizer.transform_geometry.multiply_matrices(first_matrix, existing_matrix)
		paint_elem.set(transform_attr, _matrix_to_transform_str(composed))


#============================================
def _matrices_equal(a: tuple[float, ...], b: tuple[float, ...], tol: float = 1e-9) -> bool:
	"""Return True when two 6-tuple affine matrices are equal within tol."""
	return all(abs(a[i] - b[i]) <= tol for i in range(6))


#============================================
def flatten_transforms(root: lxml.etree._Element) -> None:
	"""Flatten every geometry transform into absolute root-coordinate geometry.

	Walks the tree from the root, composing each element's transform with its
	ancestor-group chain (outermost-to-element order). Drawable leaf elements
	(paths and basic shapes) get the composed matrix baked into their geometry
	and their transform attribute removed; container groups have their transform
	attribute removed after their children are flattened. Content inside <defs>
	(gradients, clipPaths, patterns) is NOT flattened here: it is paint/clip
	space, handled by other WPs, and gradientTransform/patternTransform are
	invariant-exempt.

	After this call the canonical invariant holds for visible geometry: no
	geometry-affecting transform remains on any normalized visible element.

	Args:
		root: The parsed SVG root element. Modified in place.

	Raises:
		tools.svg_normalizer.transform_geometry.UnsupportedTransformError / NonScalingStrokeError / UnsupportedUnitError:
			propagated from tools.svg_normalizer.transform_geometry._flatten_one for the caller to turn into a rejection.
	"""
	# Depth-first recursion carrying the composed ancestor matrix. The root <svg>
	# element's own transform attribute (non-standard in SVG) IS flattened: it is
	# treated as the starting matrix for the root's children, and after all
	# children are flattened the root-level transform attribute is removed.
	# _flatten_recurse handles this transparently because the root is passed in
	# as `elem` with parent_matrix=IDENTITY; its own transform is composed in and
	# then stripped after its children are processed.
	#
	# Fix B: before mutating any geometry, move every userSpaceOnUse gradient /
	# pattern in sync with the transforms about to be baked into the geometry that
	# references it. This must precede the recursion so the matrices it reads match
	# the matrices the recursion will apply. It may raise UnsupportedTransformError
	# for a shared paint under differing transforms, in which case no geometry has
	# been touched yet and the caller rejects the file with no output.
	transform_userspace_paints(root)
	_flatten_recurse(root, tools.svg_normalizer.model.IDENTITY_MATRIX, in_defs=False)


#============================================
def _flatten_recurse(
	elem: lxml.etree._Element, parent_matrix: tuple[float, ...], in_defs: bool,
) -> None:
	"""Recursive worker for flatten_transforms.

	Args:
		elem: Current element.
		parent_matrix: Composed matrix of all ancestors above elem.
		in_defs: True when elem lives inside a <defs> subtree (paint/clip space,
			not flattened).
	"""
	if not isinstance(elem.tag, str):
		# Comment / PI: nothing to flatten, but descend is unnecessary.
		return
	tag = tools.svg_normalizer.model.local_name(elem.tag)
	entering_defs = in_defs or tag == "defs"
	# Compose this element's own transform with the inherited matrix.
	own_matrix = parent_matrix
	own_transform = tools.svg_normalizer.transform_geometry._is_geometry_transform_attr(elem) if not entering_defs else None
	if own_transform is not None:
		location = elem.getroottree().getpath(elem)
		items = tools.svg_normalizer.transform_geometry.parse_transform_list(own_transform, location)
		this_matrix = tools.svg_normalizer.transform_geometry.transforms_multiply(items, location)
		own_matrix = tools.svg_normalizer.transform_geometry.multiply_matrices(parent_matrix, this_matrix)

	# Drawable leaves carry the composed matrix into their geometry.
	# text is not in tools.svg_normalizer.model.SHAPE_TAGS (rejected by classifier before this runs).
	if (not entering_defs) and tag in tools.svg_normalizer.model.SHAPE_TAGS:
		tools.svg_normalizer.transform_geometry._flatten_one(elem, own_matrix)
		# A leaf shape has no element children to recurse into.
		return

	# Recurse into children with the composed matrix. Copy the child list first
	# because tools.svg_normalizer.transform_geometry._flatten_one may retag shape children (changing the live list).
	for child in list(elem):
		_flatten_recurse(child, own_matrix, entering_defs)

	# After children are flattened, the container's transform is fully baked in;
	# remove it so no geometry transform remains (groups outside defs only).
	if (not entering_defs) and own_transform is not None:
		if elem.get("transform") is not None:
			del elem.attrib["transform"]


#============================================
def find_geometry_transform_violation(root: lxml.etree._Element) -> str | None:
	"""Canonical-invariant checker: locate any remaining geometry transform.

	After flatten_transforms + shape conversion, all visible geometry must be
	absolute path data in root coordinates with no geometry-affecting transform
	remaining. gradientTransform / patternTransform (paint-space) and anything
	inside <defs> are exempt.

	Args:
		root: The parsed (and normalized) SVG root element.

	Returns:
		The XPath-like location of the first violating element, or None when the
		invariant holds.
	"""
	def visit(elem: lxml.etree._Element, in_defs: bool) -> str | None:
		if not isinstance(elem.tag, str):
			return None
		tag = tools.svg_normalizer.model.local_name(elem.tag)
		entering_defs = in_defs or tag == "defs"
		if not entering_defs:
			if tools.svg_normalizer.transform_geometry._is_geometry_transform_attr(elem) is not None:
				return elem.getroottree().getpath(elem)
		for child in elem:
			found = visit(child, entering_defs)
			if found is not None:
				return found
		return None

	return visit(root, False)


#============================================
# Shape-to-path conversion.
#
# Math ported BY HAND from svgo (MIT) plugins/convertShapeToPath.js:
#   - rect (sharp): M/H/V/H/z template.
#   - line:         M/L template.
#   - polyline:     M + repeated L.
#   - polygon:      M + repeated L + z.
#   - circle/ellipse: two-arc trick (ported from svgo convertShapeToPath.js
#       with convertArcs=true path); v3 uses a left-right split (M cx-rx cy /
#       A cx+rx cy / A cx-rx cy / Z) from _ellipse_segments, which is
#       geometrically equivalent to svgo's top-bottom split.
#   - rounded-rect: svgo omits this case; authored here as four quarter-arcs
#       (sweep=1, large-arc=0) with straight edges between them, matching the
#       _rect_segments implementation.
# No svgo file is copied into this repo.
#============================================


#============================================
