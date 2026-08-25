"""Sanitize SVG identifiers and reject unsupported or unsafe SVG constructs."""

import re
import unicodedata

import lxml.etree

import tools.svg_normalizer.geometry
import tools.svg_normalizer.model


def _ascii_id(value: str, seen_ids: dict[str, str]) -> str:
	"""Return an ASCII replacement for a non-ASCII id or data-name attribute value.

	Checks seen_ids to avoid collisions within a single file. The mapping is
	recorded in seen_ids so in-file references can be updated consistently.

	Args:
		value: The original attribute value (may contain non-ASCII).
		seen_ids: Mutable dict mapping original value -> replacement (in-file state).

	Returns:
		An ASCII replacement string.
	"""
	if value in seen_ids:
		return seen_ids[value]
	# Strip or transliterate each character to its ASCII equivalent.
	# For layer-style ids with CJK characters we drop non-ASCII bytes;
	# for unknown scripts we fall back to removing non-ASCII entirely
	# and then deduplicate against already-seen names.
	ascii_chars: list[str] = []
	for ch in value:
		if ord(ch) < 128:
			# Already ASCII -- keep as-is.
			ascii_chars.append(ch)
		else:
			# Try NFKD decomposition first (e.g. accented Latin).
			decomposed = unicodedata.normalize("NFKD", ch)
			ascii_part = decomposed.encode("ascii", "ignore").decode("ascii")
			if ascii_part:
				ascii_chars.append(ascii_part)
			else:
				# Non-decomposable (e.g. CJK). Drop the character.
				pass
	candidate = "".join(ascii_chars).strip("_").strip()
	# If the entire value was non-ASCII and everything was dropped, use a
	# generic fallback name.
	if not candidate:
		candidate = "layer"
	# Deduplicate: if candidate already taken by a *different* original, append counter.
	reverse = {v: k for k, v in seen_ids.items()}
	base = candidate
	counter = 2
	while candidate in reverse and reverse[candidate] != value:
		candidate = f"{base}_{counter}"
		counter += 1
	seen_ids[value] = candidate
	return candidate


#============================================
def make_ascii_clean(root: lxml.etree._Element) -> None:
	"""Replace non-ASCII id and data-name attribute VALUES with ASCII equivalents.

	Also updates any in-file references (href="#...", xlink:href="#...",
	url(#...) in fill/stroke/clip-path/mask attributes) to match renamed ids.
	Other non-ASCII text content (comments, text nodes) is not touched here.

	The function modifies *root* in place.

	Args:
		root: The parsed SVG root element.
	"""
	# First pass: collect all non-ASCII ids and build the rename map.
	# seen_ids maps original_value -> ascii_replacement (shared state for uniqueness).
	seen_ids: dict[str, str] = {}
	id_renames: dict[str, str] = {}
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		for attr in ("id", "data-name"):
			val = elem.get(attr)
			if val is None:
				continue
			if any(ord(ch) >= 128 for ch in val):
				new_val = _ascii_id(val, seen_ids)
				id_renames[val] = new_val
				elem.set(attr, new_val)
	if not id_renames:
		# Nothing to fix; return early.
		return
	# Second pass: update references to renamed ids.
	# References appear in href="#id", xlink:href="#id",
	# and as url(#id) inside fill, stroke, clip-path, mask, filter attributes.
	ref_attrs = {"fill", "stroke", "clip-path", "mask", "filter", "marker-start",
		"marker-mid", "marker-end", "color-profile", "cursor", "href"}
	xlink_href = "{http://www.w3.org/1999/xlink}href"
	# Use the shared quote-tolerant url() regex so quoted attribute references
	# (url('#id'), url("#id")) are rewritten too, matching the F8 <style> rewrite
	# and the S1 reference scan (fix (a): unify on _URL_REF_RE).
	url_pat = _URL_REF_RE

	# Defined once per call (not per-iteration) so there is no repeated closure
	# redefinition inside the loops below (fix (d): hoist replace_url_ref).
	def replace_url_ref(m: re.Match) -> str:
		frag = m.group(1)
		return "url(#" + id_renames.get(frag, frag) + ")"

	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		# Handle xlink:href and href as direct fragment references.
		for attr_name in (xlink_href, "href"):
			val = elem.get(attr_name)
			if val and val.startswith("#"):
				frag = val[1:]
				if frag in id_renames:
					elem.set(attr_name, "#" + id_renames[frag])
		# Handle url(#id) in presentation attributes.
		for attr_name in ref_attrs:
			val = elem.get(attr_name)
			if not val:
				continue
			new_val = url_pat.sub(replace_url_ref, val)
			if new_val != val:
				elem.set(attr_name, new_val)

	# F8: rewrite url(#oldid) references inside <style> block text so CSS refs
	# to a renamed id stay valid. Uses the shared url() regex (tolerant of quotes)
	# rather than the attribute-only url_pat above.
	for style_elem in _iter_style_blocks(root):
		css_text = style_elem.text
		if not css_text:
			continue
		new_css = _rewrite_style_url_refs(css_text, id_renames)
		if new_css != css_text:
			style_elem.text = new_css


# Matches a url(#id) reference, capturing the fragment id. Tolerates optional
# quotes around the fragment: url(#a), url('#a'), url("#a"). Used by F8 (style
# rewrite) and S1 (reference integrity).
_URL_REF_RE = re.compile(r"""url\(\s*['"]?\s*#([^)'"\s]+)\s*['"]?\s*\)""")

# Presentation attributes that may carry a url(#id) paint/clip/effect reference.
# Used by the reference-integrity gate to collect every internal reference.
_URL_REF_ATTRS = frozenset({
	"fill", "stroke", "clip-path", "mask", "filter", "marker-start",
	"marker-mid", "marker-end", "marker", "color-profile", "cursor",
})

# Attributes that may carry a direct fragment (href="#id") reference.
_HREF_ATTRS = ("{http://www.w3.org/1999/xlink}href", "href")


#============================================
def _iter_style_blocks(root: lxml.etree._Element) -> "list[lxml.etree._Element]":
	"""Return every <style> element in the document tree, in document order.

	Args:
		root: The parsed SVG root element.

	Returns:
		List of <style> elements (may be empty).
	"""
	blocks: list[lxml.etree._Element] = []
	for elem in root.iter():
		if isinstance(elem.tag, str) and tools.svg_normalizer.model.local_name(elem.tag) == "style":
			blocks.append(elem)
	return blocks


#============================================
def _rewrite_style_url_refs(css_text: str, id_renames: dict[str, str]) -> str:
	"""Rewrite url(#oldid) references inside CSS text using an id-rename map (F8).

	Used after make_ascii_clean renames a non-ASCII id so that references to it
	inside a <style> block stay valid. The rewrite is a targeted substitution on
	the url(#...) token only; the rest of the CSS text is untouched.

	Args:
		css_text: The raw CSS text from a <style> block.
		id_renames: Mapping of original id -> ASCII replacement.

	Returns:
		The CSS text with renamed url(#id) references updated.
	"""
	def replace(match: re.Match) -> str:
		frag = match.group(1)
		new_frag = id_renames.get(frag, frag)
		return "url(#" + new_frag + ")"
	return _URL_REF_RE.sub(replace, css_text)


#============================================
def _detect_script_or_handler(root: lxml.etree._Element) -> tools.svg_normalizer.model.RejectionReason | None:
	"""Detect <script> elements or on* event-handler attributes anywhere in the SVG.

	Security + non-determinism: scripts and event handlers are never supported by
	the normalizer gate. Any file containing them is rejected with SCRIPT_OR_HANDLER.

	Reject script elements and inline event handlers.

	Args:
		root: The parsed SVG root element.

	Returns:
		tools.svg_normalizer.model.RejectionReason with code SCRIPT_OR_HANDLER when found, else None.
	"""
	# _ON_HANDLER_RE is a module-level constant reused across elements.
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		tag = tools.svg_normalizer.model.local_name(elem.tag)
		if tag == "script":
			element_location = elem.getroottree().getpath(elem)
			reason = tools.svg_normalizer.model.RejectionReason(
				code="SCRIPT_OR_HANDLER",
				message="Script elements are not supported and rejected for security.",
				fix="Remove all <script> elements and on* event handler attributes before ingestion.",
				element=element_location,
			)
			return reason
		# Check for on* event handler attributes on any element.
		for attr_name in elem.attrib:
			local_attr = tools.svg_normalizer.model.local_name(attr_name) if isinstance(attr_name, str) else attr_name
			if isinstance(local_attr, str) and tools.svg_normalizer.model._ON_HANDLER_RE.match(local_attr):
				element_location = elem.getroottree().getpath(elem)
				reason = tools.svg_normalizer.model.RejectionReason(
					code="SCRIPT_OR_HANDLER",
					message=f"Event handler attribute '{local_attr}' is not supported.",
					fix="Remove all <script> elements and on* event handler attributes before ingestion.",
					element=element_location,
				)
				return reason
	return None


#============================================
def _detect_animation_elements(root: lxml.etree._Element) -> tools.svg_normalizer.model.RejectionReason | None:
	"""Detect SVG animation elements: <animate>, <animateTransform>, <animateMotion>, <set>.

	Animation introduces non-determinism and is never supported. Any file containing
	animation elements is rejected with ANIMATION_UNSUPPORTED.

	Reject animation elements.

	Args:
		root: The parsed SVG root element.

	Returns:
		tools.svg_normalizer.model.RejectionReason with code ANIMATION_UNSUPPORTED when found, else None.
	"""
	_ANIMATION_TAGS = {"animate", "animateTransform", "animateMotion", "set"}
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		tag = tools.svg_normalizer.model.local_name(elem.tag)
		if tag in _ANIMATION_TAGS:
			element_location = elem.getroottree().getpath(elem)
			reason = tools.svg_normalizer.model.RejectionReason(
				code="ANIMATION_UNSUPPORTED",
				message=f"Animation element <{tag}> is not supported by the v3 normalizer.",
				fix="Remove all animation elements before ingestion.",
				element=element_location,
			)
			return reason
	return None


#============================================
def _detect_foreignobject(root: lxml.etree._Element) -> tools.svg_normalizer.model.RejectionReason | None:
	"""Detect <foreignObject> elements anywhere in the SVG.

	foreignObject embeds HTML and renders inconsistently across renderers. Any file
	containing it is rejected with FOREIGNOBJECT_UNSUPPORTED.

	Reject foreignObject elements.

	Args:
		root: The parsed SVG root element.

	Returns:
		tools.svg_normalizer.model.RejectionReason with code FOREIGNOBJECT_UNSUPPORTED when found, else None.
	"""
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		tag = tools.svg_normalizer.model.local_name(elem.tag)
		if tag == "foreignObject":
			element_location = elem.getroottree().getpath(elem)
			reason = tools.svg_normalizer.model.RejectionReason(
				code="FOREIGNOBJECT_UNSUPPORTED",
				message="<foreignObject> embeds HTML and renders inconsistently.",
				fix="Remove all <foreignObject> elements before ingestion.",
				element=element_location,
			)
			return reason
	return None


#============================================
def detect_doctype_or_entity(source_text: str) -> tools.svg_normalizer.model.RejectionReason | None:
	"""Detect DOCTYPE declarations or ENTITY definitions in raw SVG text.

	parse_svg uses resolve_entities=False so a DOCTYPE may parse without error, but
	DOCTYPE and ENTITY declarations introduce parser/security complexity that v3 does
	not handle. This check is done on raw text BEFORE (or after) parsing to catch
	files that slipped through the lxml recovery guard.

	The check is cheap: scan the first 4096 bytes for "<!DOCTYPE" or "<!ENTITY".
	Case-insensitive to catch unusual capitalizations.

	Reject unsafe document declarations before XML parsing.

	Args:
		source_text: Raw text content of the SVG file.

	Returns:
		tools.svg_normalizer.model.RejectionReason with code DOCTYPE_OR_ENTITY when found, else None.
	"""
	# Only scan the document preamble (first 4096 chars) for efficiency; DOCTYPE /
	# ENTITY declarations must appear before the root element.
	head = source_text[:4096].upper()
	if "<!DOCTYPE" in head or "<!ENTITY" in head:
		reason = tools.svg_normalizer.model.RejectionReason(
			code="DOCTYPE_OR_ENTITY",
			message="DOCTYPE or ENTITY declarations are not supported.",
			fix="Remove the DOCTYPE declaration and all ENTITY definitions before ingestion.",
			element="",
		)
		return reason
	return None


#============================================
# Feature reject detectors and reference-integrity helpers.
#
# Each detector takes root and returns a
# tools.svg_normalizer.model.RejectionReason or None, matching the classify() composition contract. They
# are composed into classify() in priority order (see classify()).
#============================================


#============================================
def _detect_use_or_symbol(root: lxml.etree._Element) -> tools.svg_normalizer.model.RejectionReason | None:
	"""Reject any file containing a <use> or <symbol> element.

	Symbol expansion is not implemented in v3; refusing the whole file is simpler
	and safe for the gate (per the support contract). A later WP may add symbol
	expansion and carve this back.

	Args:
		root: The parsed SVG root element.

	Returns:
		tools.svg_normalizer.model.RejectionReason with code USE_OR_SYMBOL_UNSUPPORTED when found, else None.
	"""
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		tag = tools.svg_normalizer.model.local_name(elem.tag)
		if tag in {"use", "symbol"}:
			location = elem.getroottree().getpath(elem)
			reason = tools.svg_normalizer.model.RejectionReason(
				code="USE_OR_SYMBOL_UNSUPPORTED",
				message=f"<{tag}> is not supported (symbol expansion is not implemented in v3).",
				fix="Expand <use>/<symbol> into concrete geometry in your editor before ingestion.",
				element=location,
			)
			return reason
	return None


#============================================
def _detect_filter(root: lxml.etree._Element) -> tools.svg_normalizer.model.RejectionReason | None:
	"""Reject any file using a filter (a <filter> element or a filter= reference).

	Filters (including feGaussianBlur) can extend or alter visible pixels beyond
	the geometry bbox, which would violate contract item 3 (bbox must bound the
	visible art). Any <filter> definition, any filter primitive, or any element
	carrying a non-none filter= reference is rejected.

	Args:
		root: The parsed SVG root element.

	Returns:
		tools.svg_normalizer.model.RejectionReason with code FILTER_UNSUPPORTED when found, else None.
	"""
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		tag = tools.svg_normalizer.model.local_name(elem.tag)
		# A <filter> definition or any fe* filter primitive (feGaussianBlur, etc.).
		if tag == "filter" or tag.startswith("fe"):
			location = elem.getroottree().getpath(elem)
			reason = tools.svg_normalizer.model.RejectionReason(
				code="FILTER_UNSUPPORTED",
				message=f"<{tag}> filters can alter visible pixels beyond the geometry bbox.",
				fix="Remove filters (rasterize or bake the effect) before ingestion.",
				element=location,
			)
			return reason
		# A filter= reference (presentation attribute or inline style) on any element.
		filter_ref = tools.svg_normalizer.geometry._resolved_property(elem, "filter")
		if filter_ref is not None and filter_ref.strip().lower() not in {"", "none"}:
			location = elem.getroottree().getpath(elem)
			reason = tools.svg_normalizer.model.RejectionReason(
				code="FILTER_UNSUPPORTED",
				message="A filter reference can alter visible pixels beyond the geometry bbox.",
				fix="Remove the filter reference (rasterize or bake the effect) before ingestion.",
				element=location,
			)
			return reason
	return None


#============================================
def _detect_mask(root: lxml.etree._Element) -> tools.svg_normalizer.model.RejectionReason | None:
	"""Reject any file using a mask (a <mask> element or a mask= reference).

	Masks change which pixels are visible in ways not computable from geometry
	alone, so the bbox guarantee cannot hold. Any <mask> definition or any
	element carrying a non-none mask= reference is rejected.

	Args:
		root: The parsed SVG root element.

	Returns:
		tools.svg_normalizer.model.RejectionReason with code MASK_UNSUPPORTED when found, else None.
	"""
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		tag = tools.svg_normalizer.model.local_name(elem.tag)
		if tag == "mask":
			location = elem.getroottree().getpath(elem)
			reason = tools.svg_normalizer.model.RejectionReason(
				code="MASK_UNSUPPORTED",
				message="<mask> changes visible pixels in ways not computable from geometry.",
				fix="Bake or remove the mask before ingestion.",
				element=location,
			)
			return reason
		mask_ref = tools.svg_normalizer.geometry._resolved_property(elem, "mask")
		if mask_ref is not None and mask_ref.strip().lower() not in {"", "none"}:
			location = elem.getroottree().getpath(elem)
			reason = tools.svg_normalizer.model.RejectionReason(
				code="MASK_UNSUPPORTED",
				message="A mask reference changes visible pixels in ways not computable from geometry.",
				fix="Bake or remove the mask before ingestion.",
				element=location,
			)
			return reason
	return None


#============================================
def _detect_marker(root: lxml.etree._Element) -> tools.svg_normalizer.model.RejectionReason | None:
	"""Reject any file using a marker (a <marker> element or marker-* reference).

	Markers draw extra geometry at path vertices that is not part of the path's
	own bbox, so the geometry bbox would undershoot. Any <marker> definition or
	any element carrying a non-none marker / marker-start / marker-mid /
	marker-end reference is rejected.

	Args:
		root: The parsed SVG root element.

	Returns:
		tools.svg_normalizer.model.RejectionReason with code MARKER_UNSUPPORTED when found, else None.
	"""
	marker_props = ("marker", "marker-start", "marker-mid", "marker-end")
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		tag = tools.svg_normalizer.model.local_name(elem.tag)
		if tag == "marker":
			location = elem.getroottree().getpath(elem)
			reason = tools.svg_normalizer.model.RejectionReason(
				code="MARKER_UNSUPPORTED",
				message="<marker> draws extra geometry the bbox cannot account for.",
				fix="Remove markers (convert them to explicit path geometry) before ingestion.",
				element=location,
			)
			return reason
		for prop in marker_props:
			ref = tools.svg_normalizer.geometry._resolved_property(elem, prop)
			if ref is not None and ref.strip().lower() not in {"", "none"}:
				location = elem.getroottree().getpath(elem)
				reason = tools.svg_normalizer.model.RejectionReason(
					code="MARKER_UNSUPPORTED",
					message=f"A {prop} reference draws extra geometry the bbox cannot account for.",
					fix="Remove markers (convert them to explicit path geometry) before ingestion.",
					element=location,
				)
				return reason
	return None


# A data: URI (embedded resource, e.g. base64 raster). Matches the scheme prefix.
_DATA_URI_RE = re.compile(r"^\s*data:", re.IGNORECASE)
# An external resource scheme (http, https, file, ftp) or a protocol-relative URL.
_EXTERNAL_SCHEME_RE = re.compile(r"^\s*(?:[a-zA-Z][a-zA-Z0-9+.-]*:|//)")


#============================================
def _href_value(elem: lxml.etree._Element) -> str | None:
	"""Return the href / xlink:href value of an element, or None when absent."""
	for attr in _HREF_ATTRS:
		val = elem.get(attr)
		if val is not None:
			return val
	return None


#============================================
def _detect_image(root: lxml.etree._Element) -> tools.svg_normalizer.model.RejectionReason | None:
	"""Reject <image> elements: embedded raster (data:) or external href.

	An <image> with a data: URI embeds a raster (EMBEDDED_RASTER_UNSUPPORTED);
	an <image> with any other href references an external resource
	(EXTERNAL_RESOURCE_UNSUPPORTED). A bare in-document fragment (#id) on an image
	is still rejected as external, since v3 does not resolve image content.

	Args:
		root: The parsed SVG root element.

	Returns:
		tools.svg_normalizer.model.RejectionReason with the appropriate code when an <image> is found, else None.
	"""
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		if tools.svg_normalizer.model.local_name(elem.tag) != "image":
			continue
		location = elem.getroottree().getpath(elem)
		href = _href_value(elem)
		if href is not None and _DATA_URI_RE.match(href):
			reason = tools.svg_normalizer.model.RejectionReason(
				code="EMBEDDED_RASTER_UNSUPPORTED",
				message="<image> embeds a raster (data: URI); v3 normalizes vector geometry only.",
				fix="Recreate the artwork as vector paths before ingestion.",
				element=location,
			)
			return reason
		# Any other <image> (external href, relative path, or no href) is external.
		reason = tools.svg_normalizer.model.RejectionReason(
			code="EXTERNAL_RESOURCE_UNSUPPORTED",
			message="<image> references an external resource; v3 normalizes self-contained vector SVGs only.",
			fix="Inline the artwork as vector paths before ingestion.",
			element=location,
		)
		return reason
	return None


#============================================
def _detect_external_href(root: lxml.etree._Element) -> tools.svg_normalizer.model.RejectionReason | None:
	"""Reject any href / xlink:href that points outside the document.

	An internal fragment reference (href="#id") is allowed (resolved by S1).
	A data: URI or any scheme/relative/protocol-relative href is an external
	resource and rejected with EXTERNAL_RESOURCE_UNSUPPORTED. <image> is handled
	earlier by _detect_image; this catches external hrefs on any other element
	(e.g. a <use>-like ref that slipped past, or a feImage, or a pattern child).

	Args:
		root: The parsed SVG root element.

	Returns:
		tools.svg_normalizer.model.RejectionReason with code EXTERNAL_RESOURCE_UNSUPPORTED when found, else None.
	"""
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		href = _href_value(elem)
		if href is None:
			continue
		stripped = href.strip()
		if stripped == "" or stripped.startswith("#"):
			# Internal fragment ref (or empty): handled by S1, not external.
			continue
		location = elem.getroottree().getpath(elem)
		reason = tools.svg_normalizer.model.RejectionReason(
			code="EXTERNAL_RESOURCE_UNSUPPORTED",
			message=f"href {href!r} references a resource outside this document.",
			fix="Inline the referenced content (or remove the reference) before ingestion.",
			element=location,
		)
		return reason
	return None


#============================================
# Simple clipPath flattening.
#
# Flattens a SIMPLE clipPath into the clipped target's path geometry using
# shapely, then drops the clip reference and the now-unused clipPath def. Curves
# (cubic/quadratic bezier and elliptical arcs) are flattened to polylines within
# a fixed tolerance before intersection. Anything outside the simple-clip
# allowlist is refused with ComplexClipError -> CLIPPATH_UNSUPPORTED_COMPLEX.
#
# Clip-side allowlist (all must hold, else ComplexClipError):
#   - the clipPath holds exactly one child path/shape (one geometry node);
#   - no nested clipPaths;
#   - no mask/filter/text/image/use inside the clipPath;
#   - clipPathUnits is userSpaceOnUse (objectBoundingBox is rejected);
#   - the clip geometry converts to a path in root coordinates.
#
# Target-side handling (after the clip side passes):
#   - no-op clip (the clip region already contains the painted target envelope,
#     the common editor page-bounds case): drop the clip ref, keep the target d
#     UNCHANGED. Runs for both filled and stroke-only (fill:none) targets and is
#     render-identical by construction with no precision loss.
#   - filled target, genuinely clipped: emit target INTERSECT clip as the new d
#     (must be expressible as absolute path data).
#   - stroke-only target, genuinely clipped: rejected (a real stroke trim needs
#     stroke-to-path expansion, which is out of scope).
#
# Curve-flattening tolerance: _CLIP_FLATTEN_TOLERANCE user units (~0.1). This is
# the maximum chord deviation used when subdividing a bezier/arc into line
# segments before building shapely polygons. Documented like the A4 precision
# constant; not CLI-tunable.
#============================================

# Maximum chord deviation (user units) when flattening curves to polylines for
# the shapely intersection. Smaller -> more segments -> tighter clip boundary.
# 0.1 user units is well below the A4 coordinate precision and is invisible at
# asset scale.
_CLIP_FLATTEN_TOLERANCE = 0.1

# Margin (user units) by which a clip polygon is SHRUNK before the no-op
# containment test. A clip is a no-op only when the SHRUNK clip still fully
# contains the target envelope, meaning the target clears the real clip edge
# by at least this margin. Shrinking makes the test CONSERVATIVE (harder to
# pass): a target that protrudes even slightly outside the clip fails the test
# and the clip is kept. The margin equals a small multiple of the
# curve-flattening tolerance so polyline-approximation slop on the clip
# boundary never causes a genuine trim to be misread as a no-op.
_CLIP_NOOP_MARGIN = 2.0 * _CLIP_FLATTEN_TOLERANCE

# Minimum half-width (user units) for a stroke envelope buffer. A stroke-only
# target with a zero or hairline stroke-width still has a nonzero rendered
# footprint; this floor keeps its envelope from collapsing to a zero-area line
# (which shapely.contains would treat inconsistently). Kept at the flattening
# tolerance so it is invisible at asset scale.
_STROKE_ENVELOPE_MIN_HALF = _CLIP_FLATTEN_TOLERANCE

# Geometry tags allowed as the single child of a simple clipPath (after the
# shape->path pass, a clip child may still be a basic shape because defs content
# is not converted by convert_shapes_to_paths).
_CLIP_GEOMETRY_TAGS = frozenset({
	"path", "rect", "circle", "ellipse", "polygon", "polyline", "line",
})

# Tags that, if present inside a clipPath, make the clip complex (not flattened).
_CLIP_FORBIDDEN_CHILD_TAGS = frozenset({
	"mask", "filter", "text", "tspan", "textPath", "image", "use", "clipPath",
})


#============================================
