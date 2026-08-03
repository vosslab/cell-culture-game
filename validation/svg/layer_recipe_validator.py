"""Validate the closed authored contract for material-rendered SVG forms.

The validator deliberately knows nothing about object YAML or protocol materials.
It protects the boundary between authored semantic groups and generated runtime
handles before and after the shared SVG normalizer runs.
"""

from __future__ import annotations

import re
import hashlib
import math
from dataclasses import dataclass

import lxml.etree

SVG_NS = "http://www.w3.org/2000/svg"
SEMANTIC_ATTRIBUTES = frozenset({
	"data-vlab-rendering",
	"data-vlab-max-fill-percent",
	"data-vlab-min-fill-percent",
	"data-vlab-body-start-fill-percent",
	"data-vlab-fill-height-exponent",
	"data-vlab-layer-name",
	"data-vlab-layer-kind",
	"data-vlab-paint-role",
	"data-vlab-adjustment",
	"data-vlab-liquid-part",
})
_NORMALIZER_BOUNDARY_TOKEN = "data-vlab-normalizer-boundary-token"
LAYER_NAME_RE = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*\Z")
ADJUSTMENT_RE = re.compile(r"-?[0-9]+(?:\.[0-9]+)?\Z")
MAX_FILL_PERCENT_RE = re.compile(r"(?:[1-9][0-9]?|100)\Z")
MIN_FILL_PERCENT_RE = re.compile(r"(?:[1-9]|[1-9][0-9])\Z")
BODY_START_FILL_PERCENT_RE = re.compile(r"[0-9]+(?:\.[0-9]+)?\Z")
FILL_HEIGHT_EXPONENT_RE = re.compile(r"[0-9]+(?:\.[0-9]+)?\Z")
GEOMETRY_TAGS = frozenset({"path", "rect", "circle", "ellipse", "line", "polyline", "polygon"})


class MaterialSvgValidationError(ValueError):
	"""Raised when a material SVG violates the authored semantic contract."""


@dataclass(frozen=True)
class MaterialBoundarySignature:
	"""The semantic layer order and boundaries the normalizer must preserve."""

	layers: tuple[tuple[str, str, str | None, str | None, tuple[str, ...], str | None], ...]
	anchors: tuple[str, ...]


def _local_name(element: lxml.etree._Element) -> str:
	return lxml.etree.QName(element).localname


def _semantic_attributes(element: lxml.etree._Element) -> set[str]:
	return {name for name in element.attrib if name.startswith("data-vlab-")}


def _fail(message: str) -> None:
	raise MaterialSvgValidationError(message)


def _inside(element: lxml.etree._Element, ancestor: lxml.etree._Element) -> bool:
	return any(parent is ancestor for parent in element.iterancestors())


def _inside_defs(element: lxml.etree._Element) -> bool:
	return any(_local_name(parent) == "defs" for parent in element.iterancestors())


def _style_value(element: lxml.etree._Element, name: str) -> str | None:
	"""Return the supported inline/presentation value with CSS declaration order.

	This intentionally implements only the bounded authoring surface accepted by
	the material contract: presentation attributes and inline declarations.
	Inline declarations override presentation attributes; the last declaration
	wins within one importance level and ``!important`` wins over ordinary
	declarations.
	"""
	selected: tuple[bool, str] | None = None
	for declaration in element.get("style", "").split(";"):
		key, separator, candidate = declaration.partition(":")
		if not separator or key.strip().lower() != name:
			continue
		candidate = candidate.strip()
		important = candidate.lower().endswith("!important")
		if important:
			candidate = candidate[: -len("!important")].rstrip()
		if selected is None or important or not selected[0]:
			selected = (important, candidate)
	if selected is not None:
		return selected[1]
	value = element.get(name)
	return value.strip() if value is not None else None


def _is_css_keyword(value: str | None, keyword: str) -> bool:
	"""Compare SVG/CSS keyword values without changing authored spelling."""
	return value is not None and value.casefold() == keyword


def _inherited_value(element: lxml.etree._Element, name: str, default: str | None) -> str | None:
	current: lxml.etree._Element | None = element
	while current is not None:
		value = _style_value(current, name)
		if value is not None:
			if not _is_css_keyword(value, "inherit"):
				return value
		current = current.getparent()
	return default


_SELECTOR_DRIVEN_PAINT_RE = re.compile(
	r"(?:^|[;{\s])(display|visibility|opacity|fill|fill-opacity|stroke|stroke-opacity)\s*:",
	re.IGNORECASE,
)


def _has_unsupported_css(element: lxml.etree._Element) -> bool:
	"""Reject only selector-driven paint that needs an unavailable CSS cascade."""
	root = element.getroottree().getroot()
	for candidate in root.iter():
		if isinstance(candidate.tag, str) and _local_name(candidate) == "style":
			if _SELECTOR_DRIVEN_PAINT_RE.search(candidate.text or "") is not None:
				return True
	return False


def _opacity(value: str | None, label: str) -> float:
	try:
		parsed = float(value) if value is not None else 1.0
	except ValueError as exc:
		_fail(f"{label} must be a finite numeric value in material SVG artwork")
		raise AssertionError from exc
	if not math.isfinite(parsed):
		_fail(f"{label} must be a finite numeric value in material SVG artwork")
	return parsed


def _computed_opacity(element: lxml.etree._Element) -> float:
	"""Return one element's opacity after its explicit ``inherit`` is resolved.

	Opacity does not inherit by default.  Its one relevant keyword here is
	``inherit``, which copies the parent computed opacity and is then still
	composited at this element's position in the tree.	That distinction matters
	for nested groups: a parent at 0.5 and a child at ``inherit`` paint at 0.25.
	"""
	value = _style_value(element, "opacity")
	if _is_css_keyword(value, "inherit"):
		parent = element.getparent()
		return _computed_opacity(parent) if parent is not None else 1.0
	return _opacity(value, "opacity")


def _channel_opacity(element: lxml.etree._Element, channel: str) -> float:
	"""Compose group opacity but inherit one nearest channel-opacity value."""
	group_opacity = 1.0
	ancestors = [*element.iterancestors()][::-1] + [element]
	for candidate in ancestors:
		group_opacity *= _computed_opacity(candidate)
	channel_opacity = _opacity(
		_inherited_value(element, f"{channel}-opacity", None),
		f"{channel}-opacity",
	)
	return group_opacity * channel_opacity


def is_visible_renderable(element: lxml.etree._Element) -> bool:
	"""Return whether geometry can paint under inherited SVG presentation state."""
	if _has_unsupported_css(element):
		_fail("class and stylesheet paint are unsupported in material SVG layers; use presentation attributes or inline style")
	ancestors = [*element.iterancestors()][::-1] + [element]
	if any(_is_css_keyword(_style_value(candidate, "display"), "none") for candidate in ancestors):
		return False
	visibility = _inherited_value(element, "visibility", "visible")
	if _is_css_keyword(visibility, "hidden") or _is_css_keyword(visibility, "collapse"):
		return False
	fill = _inherited_value(element, "fill", "black")
	stroke = _inherited_value(element, "stroke", "none")
	return (not _is_css_keyword(fill, "none") and _channel_opacity(element, "fill") > 0.0) or (
		not _is_css_keyword(stroke, "none") and _channel_opacity(element, "stroke") > 0.0
	)


def _is_visible_renderable(element: lxml.etree._Element) -> bool:
	"""Compatibility alias; new callers must use :func:`is_visible_renderable`."""
	return is_visible_renderable(element)


def is_material_root(root: lxml.etree._Element) -> bool:
	return _local_name(root) == "svg" and root.get("data-vlab-rendering") == "material"


def validate_reserved_attributes(root: lxml.etree._Element, *, allow_normalizer_tokens: bool = False) -> bool:
	"""Validate root dispatch and reject every misplaced/unknown reserved key."""
	is_material = is_material_root(root)
	root_value = root.get("data-vlab-rendering")
	if root_value is not None and not is_material:
		_fail("data-vlab-rendering must have the exact value material on the root svg")
	for element in root.iter():
		if not isinstance(element.tag, str):
			continue
		reserved = _semantic_attributes(element)
		if allow_normalizer_tokens:
			reserved.discard(_NORMALIZER_BOUNDARY_TOKEN)
		elif element.get(_NORMALIZER_BOUNDARY_TOKEN) is not None:
			_fail("normalizer boundary tokens are internal and cannot be authored")
		if not reserved:
			continue
		if not is_material:
			_fail("data-vlab-* requires root data-vlab-rendering=material")
		if element is root:
			if not reserved <= {
				"data-vlab-rendering",
				"data-vlab-max-fill-percent",
				"data-vlab-min-fill-percent",
				"data-vlab-body-start-fill-percent",
				"data-vlab-fill-height-exponent",
			}:
				_fail("the root permits only material rendering and closed fill calibration attributes")
			max_fill_percent = root.get("data-vlab-max-fill-percent")
			if max_fill_percent is not None and MAX_FILL_PERCENT_RE.fullmatch(max_fill_percent) is None:
				_fail("data-vlab-max-fill-percent must be an integer in [1, 100]")
			min_fill_percent = root.get("data-vlab-min-fill-percent")
			if min_fill_percent is not None and MIN_FILL_PERCENT_RE.fullmatch(min_fill_percent) is None:
				_fail("data-vlab-min-fill-percent must be an integer in [1, 99]")
			if (
				min_fill_percent is not None
				and max_fill_percent is not None
				and int(min_fill_percent) > int(max_fill_percent)
			):
				_fail("data-vlab-min-fill-percent must not exceed data-vlab-max-fill-percent")
			body_start_fill_percent = root.get("data-vlab-body-start-fill-percent")
			if body_start_fill_percent is not None:
				if BODY_START_FILL_PERCENT_RE.fullmatch(body_start_fill_percent) is None:
					_fail("data-vlab-body-start-fill-percent must be a finite decimal in (0, 100)")
				value = float(body_start_fill_percent)
				if not 0.0 < value < 100.0:
					_fail("data-vlab-body-start-fill-percent must be a finite decimal in (0, 100)")
			fill_height_exponent = root.get("data-vlab-fill-height-exponent")
			if fill_height_exponent is not None:
				if FILL_HEIGHT_EXPONENT_RE.fullmatch(fill_height_exponent) is None:
					_fail("data-vlab-fill-height-exponent must be a finite decimal in (0, 10]")
				value = float(fill_height_exponent)
				if not 0.0 < value <= 10.0:
					_fail("data-vlab-fill-height-exponent must be a finite decimal in (0, 10]")
			if body_start_fill_percent is not None and fill_height_exponent is not None:
				_fail("data-vlab-body-start-fill-percent and data-vlab-fill-height-exponent are mutually exclusive")
			continue
		if "data-vlab-rendering" in reserved:
			_fail("data-vlab-rendering is allowed only on the root svg")
		if not reserved <= SEMANTIC_ATTRIBUTES - {
			"data-vlab-rendering",
			"data-vlab-max-fill-percent",
			"data-vlab-min-fill-percent",
			"data-vlab-body-start-fill-percent",
			"data-vlab-fill-height-exponent",
		}:
			_fail("unknown data-vlab-* attribute")
		if element.getparent() is not root or _local_name(element) != "g":
			_fail("semantic attributes are allowed only on direct root-child g groups")
	return is_material


def _find_anchor(root: lxml.etree._Element, anchor_id: str, in_defs: bool) -> lxml.etree._Element:
	matches = [element for element in root.iter() if element.get("id") == anchor_id]
	if len(matches) != 1:
		_fail(f"expected exactly one {anchor_id}")
	anchor = matches[0]
	if _inside_defs(anchor) != in_defs:
		location = "inside defs" if in_defs else "outside defs"
		_fail(f"{anchor_id} must live {location}")
	return anchor


def _semantic_layers(root: lxml.etree._Element) -> list[lxml.etree._Element]:
	layers: list[lxml.etree._Element] = []
	for child in root:
		if not isinstance(child.tag, str):
			continue
		reserved = _semantic_attributes(child)
		if reserved:
			if _local_name(child) != "g":
				_fail("semantic attributes require a g group")
			layers.append(child)
	return layers


def _layer_geometry_tokens(layer: lxml.etree._Element, *, allow_normalizer_tokens: bool) -> tuple[str, ...]:
	tokens: list[str] = []
	for ordinal, element in enumerate(layer.iter()):
		if not (
			isinstance(element.tag, str)
			and _local_name(element) in GEOMETRY_TAGS
			and not _inside_defs(element)
		):
			continue
		token = element.get(_NORMALIZER_BOUNDARY_TOKEN)
		if token is not None:
			if not allow_normalizer_tokens:
				_fail("normalizer boundary tokens are internal and cannot be authored")
			tokens.append(token)
			continue
		payload = "|".join((str(ordinal), _local_name(element), element.get("d", ""), element.get("points", "")))
		tokens.append(hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16])
	return tuple(tokens)


def _reject_generated_runtime_tokens(root: lxml.etree._Element) -> None:
	for element in root.iter():
		if not isinstance(element.tag, str):
			continue
		if element.get("data-vlab-runtime-handle") is not None or (element.get("id") or "").startswith("lr_"):
			_fail("authored SVG cannot contain generated runtime handles")
		for value in element.attrib.values():
			if re.search(r"--lr_[A-Za-z0-9_-]+", value) is not None:
				_fail("authored SVG cannot contain generated paint handles")


def validate_material_svg(root: lxml.etree._Element, *, allow_normalizer_tokens: bool = False) -> MaterialBoundarySignature:
	"""Validate a material SVG and return the invariant boundary signature."""
	if not validate_reserved_attributes(root, allow_normalizer_tokens=allow_normalizer_tokens):
		_fail("material validator requires root data-vlab-rendering=material")
	clip = _find_anchor(root, "anchor_liquid_clip", True)
	bounds = _find_anchor(root, "anchor_liquid_bounds", False)
	if _local_name(clip) != "clipPath" or _local_name(bounds) != "rect":
		_fail("liquid anchors have invalid element kinds")
	_reject_generated_runtime_tokens(root)
	layers = _semantic_layers(root)
	if not layers:
		_fail("material SVG needs semantic layer groups")

	names: set[str] = set()
	material_positions: list[int] = []
	base_count = 0
	signature_layers: list[tuple[str, str, str | None, str | None, tuple[str, ...], str | None]] = []
	for index, layer in enumerate(layers):
		reserved = _semantic_attributes(layer)
		reserved.discard(_NORMALIZER_BOUNDARY_TOKEN)
		required = {"data-vlab-layer-name", "data-vlab-layer-kind"}
		if not required <= reserved:
			_fail("semantic layer missing name or kind")
		name = layer.get("data-vlab-layer-name")
		kind = layer.get("data-vlab-layer-kind")
		role = layer.get("data-vlab-paint-role")
		adjustment = layer.get("data-vlab-adjustment")
		liquid_part = layer.get("data-vlab-liquid-part")
		if name is None or LAYER_NAME_RE.fullmatch(name) is None or name in names:
			_fail("layer names must be unique lowercase snake_case")
		names.add(name)
		if kind not in {"fixed", "material"}:
			_fail("layer kind must be fixed or material")
		if layer.get("clip-path") is not None or _style_value(layer, "clip-path") is not None:
			_fail("semantic layer groups may not carry clip-path")
		if layer.get("id") is not None:
			_fail("semantic layers cannot carry authored runtime ids")
		for descendant in layer.iterdescendants():
			descendant_reserved = _semantic_attributes(descendant)
			descendant_reserved.discard(_NORMALIZER_BOUNDARY_TOKEN)
			if descendant_reserved:
				_fail("semantic groups may not nest and artwork has no data-vlab-* attributes")
			if descendant.get("id") is not None:
				_fail("semantic artwork cannot carry authored runtime ids")
		if kind == "fixed":
			if role is not None or adjustment is not None or liquid_part is not None or reserved != required:
				_fail("fixed layers cannot carry paint role, adjustment, liquid part, or extra semantics")
		else:
			material_positions.append(index)
			expected = required | {"data-vlab-paint-role", "data-vlab-liquid-part"}
			if role not in {"base", "highlight", "shadow"}:
				_fail("material layer requires base, highlight, or shadow role")
			if liquid_part not in {"bottom", "body", "surface"}:
				_fail("material layer requires bottom, body, or surface liquid part")
			if role == "base":
				base_count += 1
				if adjustment is not None:
					_fail("base layers cannot carry adjustment")
			else:
				expected.add("data-vlab-adjustment")
				if adjustment is None or ADJUSTMENT_RE.fullmatch(adjustment) is None:
					_fail("highlight and shadow require strict decimal adjustment")
				value = float(adjustment)
				if role == "highlight" and not 0.0 < value <= 0.5:
					_fail("highlight adjustment must be in (0, 0.5]")
				if role == "shadow" and not -0.5 <= value < 0.0:
					_fail("shadow adjustment must be in [-0.5, 0)")
			if reserved != expected:
				_fail("material layer has role-incompatible semantic attributes")
		geometry_tokens = _layer_geometry_tokens(layer, allow_normalizer_tokens=allow_normalizer_tokens)
		visible_geometry = any(
			isinstance(element.tag, str)
			and _local_name(element) in GEOMETRY_TAGS
			and not _inside_defs(element)
			and is_visible_renderable(element)
			for element in layer.iter()
		)
		if kind == "material" and not visible_geometry:
			_fail("material layers must contain visible renderable geometry")
		signature_layers.append((name, kind, role, adjustment, geometry_tokens, liquid_part))

	if not material_positions or base_count == 0:
		_fail("material band needs at least one base layer")
	if material_positions != list(range(min(material_positions), max(material_positions) + 1)):
		_fail("material layers must form one contiguous band")

	for element in root.iter():
		if not isinstance(element.tag, str) or _local_name(element) not in GEOMETRY_TAGS:
			continue
		if element is bounds or _inside_defs(element):
			continue
		if is_visible_renderable(element) and not any(_inside(element, layer) for layer in layers):
			_fail("geometry must belong to exactly one semantic layer")
	return MaterialBoundarySignature(tuple(signature_layers), ("anchor_liquid_clip", "anchor_liquid_bounds"))


def inject_normalizer_boundary_tokens(root: lxml.etree._Element) -> None:
	"""Mark material geometry in-memory so normalization can prove ownership."""
	validate_material_svg(root)
	for layer in _semantic_layers(root):
		for ordinal, element in enumerate(layer.iter()):
			if (
				isinstance(element.tag, str)
				and _local_name(element) in GEOMETRY_TAGS
				and not _inside_defs(element)
			):
				payload = f"{layer.get('data-vlab-layer-name')}:{ordinal}:{_local_name(element)}:{element.get('d', '')}:{element.get('points', '')}"
				element.set(_NORMALIZER_BOUNDARY_TOKEN, hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16])


def remove_normalizer_boundary_tokens(root: lxml.etree._Element) -> None:
	"""Remove compiler-private in-memory proof markers before serialization."""
	for element in root.iter():
		if isinstance(element.tag, str):
			element.attrib.pop(_NORMALIZER_BOUNDARY_TOKEN, None)


def material_boundary_signature(root: lxml.etree._Element, *, allow_normalizer_tokens: bool = False) -> MaterialBoundarySignature:
	"""Alias that makes the normalizer's preservation use explicit."""
	return validate_material_svg(root, allow_normalizer_tokens=allow_normalizer_tokens)
