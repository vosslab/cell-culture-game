"""Detect and remove optional editorial floor shadows from normalized SVGs."""

import dataclasses
import re

import lxml.etree

import tools.svg_normalizer.geometry
import tools.svg_normalizer.model


_SHADOW_ASPECT_THRESHOLD = 3.0
_SHADOW_BAND_FRAC = 0.20
_SHADOW_OPACITY_THRESHOLD = 0.5
_SHADOW_GREY_TOLERANCE = 30
_SHADOW_GREY_MAX_VALUE = 180
_HEX_RGB_FULL = re.compile(r'^#([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})$')
_HEX_RGB_SHORT = re.compile(r'^#([0-9a-fA-F])([0-9a-fA-F])([0-9a-fA-F])$')


def _fill_is_desaturated_grey(fill_value: str) -> bool:
	"""Return True when a hex fill colour is a desaturated near-grey at mid/low value.

	Matches both 6-hex (#rrggbb) and 3-hex (#rgb) formats.  The grey test is:
	  - Max channel minus min channel <= _SHADOW_GREY_TOLERANCE (approx equal RGB).
	  - Max channel value <= _SHADOW_GREY_MAX_VALUE (mid/low, not near-white).

	Only hex colours are tested; named colours ("grey", "silver", etc.) are NOT
	parsed here to keep the inline-only-cascade contract (no guessing).

	Args:
		fill_value: The raw fill attribute value string.

	Returns:
		True when the colour is a desaturated mid-to-low grey.
	"""
	fill_value = fill_value.strip()
	m6 = _HEX_RGB_FULL.match(fill_value)
	if m6:
		r = int(m6.group(1), 16)
		g = int(m6.group(2), 16)
		b = int(m6.group(3), 16)
	else:
		m3 = _HEX_RGB_SHORT.match(fill_value)
		if not m3:
			# Not a parseable hex colour; no signal.
			return False
		# Expand 3-hex to 6-hex: #rgb -> #rrggbb.
		r = int(m3.group(1) * 2, 16)
		g = int(m3.group(2) * 2, 16)
		b = int(m3.group(3) * 2, 16)
	channels = [r, g, b]
	max_ch = max(channels)
	min_ch = min(channels)
	# Both criteria must hold: near-equal channels AND mid/low luminance.
	return (max_ch - min_ch) <= _SHADOW_GREY_TOLERANCE and max_ch <= _SHADOW_GREY_MAX_VALUE


#============================================
@dataclasses.dataclass(frozen=True)
class ShadowCandidate:
	"""One floor-shadow candidate element detected by detect_floor_shadow_candidates.

	Attributes:
		element: The lxml element node.
		element_location: XPath-like location string (for dry-run reporting).
		tools.svg_normalizer.geometry.element_bbox: The pure geometry bbox of the element.
		signal: A short string naming which shadow signal matched ("fill_opacity",
			"grey_fill", or "id_class").
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

	This is the D1 pure detection function.  It reads only inline style and
	presentation attributes (inline-only cascade); if a needed signal would require
	a <style> class rule, that sub-criterion is treated as no signal.  Blur filter
	alone is never a signal (filters are already rejected by the classifier).

	By this stage all shapes are <path>, so element geometry is
	available from _element_geometry_bbox.

	A candidate satisfies ALL three criteria:
	  1. Wide-flat: tools.svg_normalizer.geometry.element_bbox.width / tools.svg_normalizer.geometry.element_bbox.height > _SHADOW_ASPECT_THRESHOLD.
	  2. Bottom-band: tools.svg_normalizer.geometry.element_bbox center_y > overall_bbox.min_y +
	     (1 - _SHADOW_BAND_FRAC) * overall_bbox.height.
	  3. Shadow signal (at least one of):
	     a. Resolved fill-opacity < _SHADOW_OPACITY_THRESHOLD.
	     b. Resolved fill is a desaturated near-grey hex colour.
	     c. id= or class= contains the substring "shadow" (case-insensitive).

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
		# Criterion 3: shadow signal (inline-only cascade; no class/stylesheet guessing).
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

	Checks in this order: fill-opacity sub-criterion (a), then grey fill (b),
	then id/class substring (c).  Returns the FIRST matching signal name so
	the caller can report which signal caused the match.

	Only inline style and presentation attributes are read (no class/stylesheet).

	Args:
		elem: The SVG path element to test.

	Returns:
		"fill_opacity", "grey_fill", "id_class", or None.
	"""
	# Sub-criterion (a): resolved fill-opacity < threshold.
	fill_opacity_str = tools.svg_normalizer.geometry._resolved_property(elem, "fill-opacity")
	if fill_opacity_str is not None:
		fill_opacity = tools.svg_normalizer.model.parse_float(fill_opacity_str, default=1.0)
		if fill_opacity < _SHADOW_OPACITY_THRESHOLD:
			return "fill_opacity"

	# Sub-criterion (b): desaturated near-grey hex fill.
	fill_str = tools.svg_normalizer.geometry._resolved_property(elem, "fill")
	if fill_str is not None and _fill_is_desaturated_grey(fill_str):
		return "grey_fill"

	# Sub-criterion (c): id or class contains "shadow" (case-insensitive).
	id_val = elem.get("id") or ""
	class_val = elem.get("class") or ""
	if "shadow" in id_val.lower() or "shadow" in class_val.lower():
		return "id_class"

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
