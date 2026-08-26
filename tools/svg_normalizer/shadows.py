"""Detect and remove optional editorial floor shadows from normalized SVGs."""

import dataclasses

import lxml.etree

import tools.svg_normalizer.geometry
import tools.svg_normalizer.model


_SHADOW_ASPECT_THRESHOLD = 3.0
_SHADOW_BAND_FRAC = 0.20
_EDITORIAL_FLOOR_SHADOW_ATTRIBUTE = "data-editorial-floor-shadow"
_EDITORIAL_FLOOR_SHADOW_VALUE = "true"


#============================================
@dataclasses.dataclass(frozen=True)
class ShadowCandidate:
	"""One floor-shadow candidate element detected by detect_floor_shadow_candidates.

	Attributes:
		element: The lxml element node.
		element_location: XPath-like location string (for dry-run reporting).
		tools.svg_normalizer.geometry.element_bbox: The pure geometry bbox of the element.
		signal: The explicit semantic signal that authorized detection.
	"""
	element: lxml.etree._Element
	element_location: str
	element_bbox: tools.svg_normalizer.model.BBox
	signal: str


#============================================
def detect_floor_shadow_candidates(
	root: lxml.etree._Element,
	overall_bbox: tools.svg_normalizer.model.BBox,
) -> list[ShadowCandidate]:
	"""Detect floor-shadow candidates from the element set given the overall bbox.

	This is the pure floor-shadow detection function. An editorial floor shadow must opt in
	with ``data-editorial-floor-shadow="true"``. Colour, opacity, id, and class
	are visual or generic metadata, not semantics: none authorizes removal.

	By this stage all shapes are <path>, so element geometry is
	available from _element_geometry_bbox.

	A candidate satisfies ALL three criteria:
	  1. Wide-flat: element bbox width divided by height exceeds
	     _SHADOW_ASPECT_THRESHOLD.
	  2. Bottom-band: tools.svg_normalizer.geometry.element_bbox center_y > overall_bbox.min_y +
	     (1 - _SHADOW_BAND_FRAC) * overall_bbox.height.
	  3. Explicit editorial marker: ``data-editorial-floor-shadow="true"``.

	Args:
		root: The parsed SVG root element (after classify, flatten, and shape->path).
		overall_bbox: The overall drawing bbox (computed BEFORE any removal).

	Returns:
		Ordered list of ShadowCandidate records (document order); empty when none.
	"""
	candidates: list[ShadowCandidate] = []
	# The overall drawing height must be positive for the band calculation.
	overall_height = overall_bbox.height
	if overall_height <= 0.0:
		return candidates
	# Bottom-band threshold: center_y must exceed this y value.
	band_threshold_y = overall_bbox.min_y + (1.0 - _SHADOW_BAND_FRAC) * overall_height

	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		tag = tools.svg_normalizer.model.local_name(elem.tag)
		if tag != "path":
			# All geometry is <path> at this stage; skip non-path nodes.
			continue
		# Criterion 1: compute element geometry bbox (no stroke pad).
		elem_geom = tools.svg_normalizer.geometry._element_geometry_bbox(elem)
		if elem_geom is None or isinstance(elem_geom, str):
			# No bbox or UNIT_SENTINEL -> skip.
			continue
		elem_h = elem_geom.height
		if elem_h <= 0.0:
			# Zero-height element: cannot compute a meaningful aspect ratio.
			continue
		# Criterion 1: wide-flat check.
		aspect = elem_geom.width / elem_h
		if aspect <= _SHADOW_ASPECT_THRESHOLD:
			continue
		# Criterion 2: bottom-band check.
		center_y = (elem_geom.min_y + elem_geom.max_y) / 2.0
		if center_y <= band_threshold_y:
			continue
		# ASVS 2.2.1: only the exact positive marker authorizes destructive removal.
		location = elem.getroottree().getpath(elem)
		signal = _shadow_signal(elem)
		if signal is None:
			continue
		candidates.append(ShadowCandidate(
			element=elem,
			element_location=location,
			element_bbox=elem_geom,
			signal=signal,
		))
	return candidates


#============================================
def _shadow_signal(elem: lxml.etree._Element) -> str | None:
	"""Return the matched shadow signal name for an element, or None.

	Only the canonical exact marker is accepted. This makes deletion depend on
	a positive semantic declaration rather than presentation values that real
	base geometry commonly shares.

	Args:
		elem: The SVG path element to test.

	Returns:
		"explicit_marker", or None.
	"""
	# ASVS 15.3.5: use an exact string comparison; truthy/coerced values cannot delete art.
	if elem.get(_EDITORIAL_FLOOR_SHADOW_ATTRIBUTE) == _EDITORIAL_FLOOR_SHADOW_VALUE:
		return "explicit_marker"

	return None


#============================================
def remove_floor_shadow_elements(
	root: lxml.etree._Element,
	candidates: list[ShadowCandidate],
) -> int:
	"""Remove the detected floor-shadow candidate elements from the tree.

	Modifies root in place by detaching each candidate element.  Returns the
	number of elements actually removed.  If a candidate's parent is None
	(already detached), it is silently skipped.

	Args:
		root: The parsed SVG root element.
		candidates: List of ShadowCandidate records from detect_floor_shadow_candidates.

	Returns:
		Number of elements removed.
	"""
	removed = 0
	for candidate in candidates:
		parent = candidate.element.getparent()
		if parent is not None:
			parent.remove(candidate.element)
			removed += 1
	return removed


#============================================
