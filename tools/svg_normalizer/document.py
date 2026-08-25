"""Clean SVG document structure, validate references, and serialize canonically."""

import re
import pathlib

import lxml.etree

import tools.svg_normalizer.clips
import tools.svg_normalizer.geometry
import tools.svg_normalizer.model
import tools.svg_normalizer.sanitization


_EDITOR_CRUFT_NS = frozenset({
	"http://www.inkscape.org/namespaces/inkscape",
	"http://sodipodi.sourceforge.net/DTD/sodipodi-0.0.dtd",
	"http://ns.adobe.com/AdobeIllustrator/10.0/",
	"http://ns.adobe.com/AdobeSVGViewerExtensions/3.0/",
	"http://ns.adobe.com/Extensibility/1.0/",
	"http://ns.adobe.com/Flows/1.0/",
	"http://ns.adobe.com/GenericCustomNamespace/1.0/",
	"http://ns.adobe.com/ImageReplacement/1.0/",
	"http://ns.adobe.com/SaveForWeb/1.0/",
	"http://ns.adobe.com/Variables/1.0/",
	"http://ns.adobe.com/XPath/1.0/",
	"http://ns.adobe.com/pdf/1.3/",
})


def _namespace_uri_of(name: str) -> str | None:
	"""Return the namespace URI of a Clark-notation tag or attribute name."""
	if name.startswith("{"):
		return name[1:].split("}", 1)[0]
	return None


def remove_editor_cruft(root: lxml.etree._Element) -> None:
	"""Remove editor-namespace elements and attributes (B1 positive allowlist).

	Removes only elements whose tag is in a known editor-cruft namespace and only
	attributes whose name is in one of those
	namespaces. Preserves every SVG-namespace rendering attribute, every def,
	every id, and all dc/cc/rdf attribution and <title>/<desc>. Modifies root in
	place.

	Args:
		root: The parsed SVG root element.
	"""
	# Collect editor-cruft elements first (do not mutate while iterating).
	to_remove: list[lxml.etree._Element] = []
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		ns = _namespace_uri_of(elem.tag)
		if ns is not None and ns in _EDITOR_CRUFT_NS:
			to_remove.append(elem)
	for elem in to_remove:
		parent = elem.getparent()
		if parent is not None:
			parent.remove(elem)
	# Strip editor-cruft attributes from every remaining element.
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		cruft_attrs = [
			name for name in elem.attrib
			if _namespace_uri_of(name) in _EDITOR_CRUFT_NS
		]
		for name in cruft_attrs:
			del elem.attrib[name]


#============================================
def collect_internal_references(root: lxml.etree._Element) -> list[tuple[str, str]]:
	"""Collect every internal (#fragment) reference in the document (S1 input).

	Scans presentation attributes carrying url(#id), href/xlink:href fragments,
	and url(#id) references inside <style> block text. Each entry is a
	(fragment-id, element-location) pair.

	Args:
		root: The parsed SVG root element.

	Returns:
		List of (referenced_id, element_location) tuples for every internal ref.
	"""
	refs: list[tuple[str, str]] = []
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		location = elem.getroottree().getpath(elem)
		# href / xlink:href direct fragment references.
		href = tools.svg_normalizer.sanitization._href_value(elem)
		if href is not None and href.strip().startswith("#"):
			refs.append((href.strip()[1:], location))
		# url(#id) references in presentation attributes and inline style.
		for attr in tools.svg_normalizer.sanitization._URL_REF_ATTRS:
			val = tools.svg_normalizer.geometry._resolved_property(elem, attr)
			if not val:
				continue
			for match in tools.svg_normalizer.sanitization._URL_REF_RE.finditer(val):
				refs.append((match.group(1), location))
	# url(#id) references inside <style> block text.
	for style_elem in tools.svg_normalizer.sanitization._iter_style_blocks(root):
		css_text = style_elem.text or ""
		location = style_elem.getroottree().getpath(style_elem)
		for match in tools.svg_normalizer.sanitization._URL_REF_RE.finditer(css_text):
			refs.append((match.group(1), location))
	return refs


#============================================
def collect_defined_ids(root: lxml.etree._Element) -> set[str]:
	"""Return the set of all id values declared anywhere in the document (S1)."""
	ids: set[str] = set()
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		id_val = elem.get("id")
		if id_val is not None:
			ids.add(id_val)
	return ids


#============================================
def check_reference_integrity(root: lxml.etree._Element) -> tools.svg_normalizer.model.RejectionReason | None:
	"""S1 hard gate: confirm every internal reference resolves to a defined id.

	Runs AFTER all rewrites (ASCII rename, F8, transform flatten, shape->path)
	and BEFORE the final write. If any internal url(#id) / href="#id" reference
	names an id that does not exist in the output tree, the file is rejected with
	UNRESOLVED_REFERENCE (no output written). External refs are already rejected
	earlier; this gate protects predictable rendering of internal refs.

	Args:
		root: The (already normalized) SVG root element.

	Returns:
		tools.svg_normalizer.model.RejectionReason with code UNRESOLVED_REFERENCE for the first dangling ref,
		else None.
	"""
	defined = collect_defined_ids(root)
	for ref_id, location in collect_internal_references(root):
		if ref_id not in defined:
			reason = tools.svg_normalizer.model.RejectionReason(
				code="UNRESOLVED_REFERENCE",
				message=f"Internal reference '#{ref_id}' does not resolve to any id in the output.",
				fix="Define the referenced id, or remove the dangling reference, before ingestion.",
				element=location,
			)
			return reason
	return None


#============================================
def _detect_text_elements(root: lxml.etree._Element) -> tools.svg_normalizer.model.RejectionReason | None:
	"""Detect <text>, <tspan>, or <textPath> anywhere in the document (A5).

	Text elements cannot be normalized by v3 (glyph geometry is font-dependent
	and not computable from path math alone). Prose belongs in layout-manager DOM
	or object data; only approved intrinsic markings may be converted to paths
	before ingestion. Any file containing a text element is rejected with
	TEXT_UNSUPPORTED.

	The classifier calls this detector as part of its single-reason-return flow.

	Args:
		root: The parsed SVG root element.

	Returns:
		tools.svg_normalizer.model.RejectionReason with code TEXT_UNSUPPORTED when any text element is found,
		else None.
	"""
	text_local_names = {"text", "tspan", "textPath"}
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		tag = tools.svg_normalizer.model.local_name(elem.tag)
		if tag in text_local_names:
			# Build an XPath-like location for the offending element.
			element_location = elem.getroottree().getpath(elem)
			reason = tools.svg_normalizer.model.RejectionReason(
				code="TEXT_UNSUPPORTED",
				message="Text elements are not normalized by v3.",
				fix=(
					"Remove prose text and move it to layout-manager DOM or object data; "
					"convert only approved intrinsic markings to paths before ingestion."
				),
				element=element_location,
			)
			return reason
	return None


#============================================
def _detect_runtime_bounds_anchor(root: lxml.etree._Element) -> tools.svg_normalizer.model.RejectionReason | None:
	"""Reject an ambiguous or runtime-incompatible material bounds anchor.

	The bounds anchor is optional for generic SVGs. When present, the material
	runtime needs exactly one bare, outside-``defs`` ``<rect>`` to read after
	injection. A duplicate id cannot resolve to one target, and a non-rect or
	definition-space element cannot supply direct rectangle geometry.

	Args:
		root: Parsed SVG root before normalization mutates geometry.

	Returns:
		A UNRESOLVED_REFERENCE reason for an invalid bounds-anchor declaration, or
		None when the optional anchor is absent or valid.
	"""
	anchors = [
		elem
		for elem in root.iter()
		if isinstance(elem.tag, str) and elem.get("id") == tools.svg_normalizer.model.RUNTIME_BOUNDS_RECT_ID
	]
	if not anchors:
		return None
	if len(anchors) != 1:
		return tools.svg_normalizer.model.RejectionReason(
			code="UNRESOLVED_REFERENCE",
			message=(
				"Material anchor 'anchor_liquid_bounds' must resolve to exactly one "
				"outside-defs rect."
			),
			fix=(
				"Keep one bare id='anchor_liquid_bounds' on the hidden bounds rect; "
				"remove that id from clip geometry and all other elements."
			),
			element=anchors[0].getroottree().getpath(anchors[0]),
		)
	anchor = anchors[0]
	if tools.svg_normalizer.model.local_name(anchor.tag) != "rect":
		return tools.svg_normalizer.model.RejectionReason(
			code="UNRESOLVED_REFERENCE",
			message="Material anchor 'anchor_liquid_bounds' must resolve to an outside-defs rect.",
			fix="Move the bare id='anchor_liquid_bounds' to one hidden outside-defs rect.",
			element=anchor.getroottree().getpath(anchor),
		)
	parent = anchor.getparent()
	while parent is not None:
		if isinstance(parent.tag, str) and tools.svg_normalizer.model.local_name(parent.tag) == "defs":
			return tools.svg_normalizer.model.RejectionReason(
				code="UNRESOLVED_REFERENCE",
				message="Material anchor 'anchor_liquid_bounds' must resolve outside <defs>.",
				fix="Move the hidden bounds rect outside <defs>; keep clip geometry under anchor_liquid_clip.",
				element=anchor.getroottree().getpath(anchor),
			)
		parent = parent.getparent()
	return None


#============================================
def classify(root: lxml.etree._Element) -> tools.svg_normalizer.model.RejectionReason | None:
	"""Classify the parsed SVG for unsupported features (S2 seam).

	This is the shared classifier seam. It checks text, structural, effect,
	resource, clip, and style features without changing this signature.

	Each detector is a function that takes root and returns a tools.svg_normalizer.model.RejectionReason or
	None. They are called in priority order; the first non-None reason is returned
	as the primary rejection reason.

	Args:
		root: The parsed SVG root element.

	Returns:
		A tools.svg_normalizer.model.RejectionReason when an unsupported feature is found, else None.
	"""
	# Reject text, tspan, and textPath elements.
	reason = _detect_text_elements(root)
	if reason is not None:
		return reason
	reason = _detect_runtime_bounds_anchor(root)
	if reason is not None:
		return reason

	# Always reject scripts, event handlers, animation, and foreignObject.
	reason = tools.svg_normalizer.sanitization._detect_script_or_handler(root)
	if reason is not None:
		return reason
	reason = tools.svg_normalizer.sanitization._detect_animation_elements(root)
	if reason is not None:
		return reason
	reason = tools.svg_normalizer.sanitization._detect_foreignobject(root)
	if reason is not None:
		return reason

	# Remaining feature rejects use the same single-reason contract.
	# Order: structural rejects (use/symbol), effect rejects (filter/mask/marker),
	# resource rejects (image embedded/external, external href), clip, style, then
	# pattern. The first non-None reason wins as the primary rejection.
	for detector in (
		tools.svg_normalizer.sanitization._detect_use_or_symbol,
		tools.svg_normalizer.sanitization._detect_filter,
		tools.svg_normalizer.sanitization._detect_mask,
		tools.svg_normalizer.sanitization._detect_marker,
		tools.svg_normalizer.sanitization._detect_image,
		tools.svg_normalizer.sanitization._detect_external_href,
		tools.svg_normalizer.clips._detect_clippath,
		tools.svg_normalizer.clips._detect_style_geometry,
		tools.svg_normalizer.clips._detect_pattern,
	):
		reason = detector(root)
		if reason is not None:
			return reason
	return None


#============================================
def parse_svg(input_path: pathlib.Path) -> lxml.etree._ElementTree:
	"""Parse an SVG once with lxml, WITHOUT recovery.

	The v3 gate parses exactly once and never normalizes recovered XML. A parse
	failure is the caller's signal to reject the file with PARSER_ERROR; the
	feature classification may separately re-parse with recover only to classify
	the likely feature, but the normalizer here does not.

	Args:
		input_path: pathlib.Path to the source SVG.

	Returns:
		The parsed lxml ElementTree.

	Raises:
		lxml.etree.XMLSyntaxError: When the document is not well-formed.
	"""
	# recover=False: malformed input is a hard parse failure, not silently fixed.
	# resolve_entities=False / no_network=True: do not expand entities or fetch
	# external resources during parse (defense in depth; DOCTYPE/entity files are
	# rejected by the classifier in a later WP).
	parser = lxml.etree.XMLParser(
		recover=False,
		resolve_entities=False,
		no_network=True,
		huge_tree=False,
	)
	tree = lxml.etree.parse(str(input_path), parser=parser)
	return tree


#============================================
def _build_canonical_nsmap(root: lxml.etree._Element) -> dict[str | None, str]:
	"""Build a serialization nsmap that pins canonical prefixes.

	Starts from the parsed root's own nsmap (so the default SVG namespace and any
	author-declared prefixes are kept) and adds the canonical attribution/editor
	prefixes for any namespace the document actually uses, so lxml never emits
	ns0:/ns1:. This is the core of the S4 "no ns0:" guarantee.

	Args:
		root: The parsed SVG root element.

	Returns:
		A prefix -> uri mapping suitable for an lxml nsmap.
	"""
	# Collect every namespace URI actually used by elements or attributes so we
	# only pin prefixes the document needs (avoids declaring unused namespaces).
	used_uris: set[str] = set()
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		if elem.tag.startswith("{"):
			used_uris.add(elem.tag[1:].split("}", 1)[0])
		for attr_name in elem.attrib:
			if isinstance(attr_name, str) and attr_name.startswith("{"):
				used_uris.add(attr_name[1:].split("}", 1)[0])

	# Start from the root's declared nsmap (default SVG ns + author prefixes).
	nsmap: dict[str | None, str] = dict(root.nsmap)
	# Ensure the default namespace is SVG when present.
	if None not in nsmap:
		nsmap[None] = tools.svg_normalizer.model.SVG_NS

	# Invert to find which URIs already have a prefix, so we do not double-map.
	mapped_uris = set(nsmap.values())
	for prefix, uri in tools.svg_normalizer.model.CANONICAL_NS_PREFIXES.items():
		if uri in used_uris and uri not in mapped_uris:
			nsmap[prefix] = uri
			mapped_uris.add(uri)
	return nsmap


#============================================
def _reroot_with_nsmap(root: lxml.etree._Element) -> lxml.etree._Element:
	"""Return root rebuilt under a canonical nsmap if new prefixes are needed.

	lxml fixes an element's nsmap at creation time; you cannot add a namespace
	prefix to an existing element. To guarantee canonical prefixes (no ns0:),
	build a fresh root element with the full canonical nsmap and move the
	original children, attributes, text, and tail onto it.

	Args:
		root: The parsed SVG root element.

	Returns:
		Either the original root (when no new prefixes were needed) or a new root
		carrying the canonical nsmap with identical content.
	"""
	desired = _build_canonical_nsmap(root)
	# If the root already declares every desired prefix->uri, no reroot needed.
	current = dict(root.nsmap)
	if all(current.get(p) == u for p, u in desired.items()):
		return root
	# Build a replacement root with the desired nsmap and copy everything over.
	new_root = lxml.etree.Element(root.tag, nsmap=desired)
	for name, value in root.attrib.items():
		new_root.set(name, value)
	new_root.text = root.text
	new_root.tail = root.tail
	for child in list(root):
		new_root.append(child)
	return new_root


#============================================
def serialize_canonical(tree_or_root: lxml.etree._Element) -> bytes:
	"""Serialize an SVG element to canonical S4 bytes.

	S4 guarantees: UTF-8 encoding, a single trailing newline, and stable
	namespace prefixes (no ns0:/ns1: renaming). The XML declaration is omitted
	(v2 wrote none); any pre-root comments are re-injected by the caller.

	Args:
		tree_or_root: The SVG root element to serialize.

	Returns:
		UTF-8 bytes ending in exactly one newline.
	"""
	# pretty_print=False keeps author whitespace; we only guarantee a final
	# newline. xml_declaration=False matches v2 (caller may add a preamble).
	data = lxml.etree.tostring(
		tree_or_root,
		encoding="utf-8",
		xml_declaration=False,
		pretty_print=False,
	)
	# Guarantee exactly one trailing newline.
	text = data.decode("utf-8").rstrip("\n") + "\n"
	return text.encode("utf-8")


#============================================
def extract_pre_root_comments(source_text: str) -> list[str]:
	"""Return XML comments that appear before the <svg> root element.

	Comments between <?xml ...?> and <svg ...> are otherwise dropped on
	round-trip, stripping attribution credit lines. lxml keeps comments inside
	the root via the tree, but pre-root siblings are re-injected by the caller.

	Args:
		source_text: Full raw text of an SVG file.

	Returns:
		Each captured comment as its full <!-- ... --> form, in source order.
	"""
	pre_root_match = re.search(r"^(.*?)<svg\b", source_text, re.DOTALL)
	if not pre_root_match:
		return []
	return re.findall(r"<!--.*?-->", pre_root_match.group(1), re.DOTALL)


#============================================
def _reject(
	input_path: pathlib.Path, output_path: pathlib.Path, code: str, message: str, fix: str, element: str = "",
) -> tools.svg_normalizer.model.NormalizeResult:
	"""Build a REJECTED tools.svg_normalizer.model.NormalizeResult (no output written, input untouched).

	Args:
		input_path: The source SVG path.
		output_path: Where output would have been written.
		code: A stable token from REASON_CODES.
		message: Why the file was rejected.
		fix: Suggested author fix.
		element: XPath-like location when available.

	Returns:
		A tools.svg_normalizer.model.NormalizeResult carrying the rejection; output_written is False.
	"""
	reason = tools.svg_normalizer.model.RejectionReason(code=code, message=message, fix=fix, element=element)
	result = tools.svg_normalizer.model.NormalizeResult(
		input_path=input_path,
		output_path=output_path,
		rejection=reason,
		output_written=False,
	)
	return result


#============================================
