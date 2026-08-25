"""Shared geometry measurements for normalized semantic material SVGs.

Measurements use the normalizer's conservative painted axis-aligned bounds in
SVG user units. They describe geometry only; they never infer physical volume.
"""

from __future__ import annotations

# Standard Library
import copy
import math
from dataclasses import dataclass

# PIP3 modules
import lxml.etree

# Local application
import tools.svg_normalizer.geometry
import tools.svg_normalizer.model
from validation.svg.layer_recipe_validator import GEOMETRY_TAGS, is_visible_renderable


class SemanticGeometryError(ValueError):
	"""Raised when semantic SVG geometry cannot be measured without guessing."""


@dataclass(frozen=True)
class Bounds:
	"""An axis-aligned rectangle in normalized SVG user units."""

	min_x: float
	min_y: float
	max_x: float
	max_y: float

	@property
	def width(self) -> float:
		return self.max_x - self.min_x

	@property
	def height(self) -> float:
		return self.max_y - self.min_y


@dataclass(frozen=True)
class MaterialGeometry:
	"""Structural envelopes and gravity-part calibration for one material SVG."""

	level_frame: Bounds
	clip_envelope: Bounds
	material: Bounds
	parts: tuple[tuple[str, Bounds], ...]
	surface_base: Bounds | None

	def part(self, name: str) -> Bounds | None:
		"""Return the measured envelope for one optional liquid part."""
		return dict(self.parts).get(name)

	@property
	def surface_reference_y(self) -> float | None:
		"""Top of the base meniscus used as the volume-reading datum."""
		if self.surface_base is not None:
			return self.surface_base.min_y
		body = self.part("body")
		if body is not None:
			return body.min_y
		surface = self.part("surface")
		return surface.min_y if surface is not None else None

	@property
	def body_join_y(self) -> float | None:
		"""Top of the authored stretchable body, its join with the surface."""
		body = self.part("body")
		return body.min_y if body is not None else None

	@property
	def body_anchor_y(self) -> float | None:
		"""Fixed lower Y datum around which the middle body scales."""
		body = self.part("body")
		return body.max_y if body is not None else None


def local_name(element: lxml.etree._Element) -> str:
	"""Return one element's namespace-free local name."""
	return lxml.etree.QName(element).localname


def inside_defs(element: lxml.etree._Element) -> bool:
	"""Return whether an element belongs to a resource definition."""
	return any(local_name(parent) == "defs" for parent in element.iterancestors())


def find_required(root: lxml.etree._Element, element_id: str) -> lxml.etree._Element:
	"""Return exactly one required authored anchor."""
	matches = [element for element in root.iter() if element.get("id") == element_id]
	if len(matches) != 1:
		raise SemanticGeometryError(f"expected exactly one {element_id}")
	return matches[0]


def required_number(element: lxml.etree._Element, name: str, label: str) -> float:
	"""Read one finite user-unit coordinate without accepting CSS units."""
	raw = element.get(name)
	if raw is None:
		raise SemanticGeometryError(f"{label} is missing {name}")
	try:
		value = float(raw)
	except ValueError as error:
		raise SemanticGeometryError(f"{label}.{name} must be a plain user-unit number") from error
	if not math.isfinite(value):
		raise SemanticGeometryError(f"{label}.{name} must be finite")
	return value


def rect_bounds(element: lxml.etree._Element, label: str) -> Bounds:
	"""Measure a required positive rectangle in user units."""
	if local_name(element) != "rect":
		raise SemanticGeometryError(f"{label} must be a rect")
	x = required_number(element, "x", label)
	y = required_number(element, "y", label)
	width = required_number(element, "width", label)
	height = required_number(element, "height", label)
	if width <= 0.0 or height <= 0.0:
		raise SemanticGeometryError(f"{label} width and height must be positive")
	return Bounds(x, y, x + width, y + height)


def to_bounds(measured: tools.svg_normalizer.model.BBox | str | None, label: str) -> Bounds:
	"""Convert the normalizer's bounded geometry result or fail explicitly."""
	if measured is None or isinstance(measured, str):
		raise SemanticGeometryError(
			f"cannot measure {label} with the normalized SVG geometry model"
		)
	return Bounds(measured.min_x, measured.min_y, measured.max_x, measured.max_y)


def union(bounds: list[Bounds], label: str) -> Bounds:
	"""Return the enclosing rectangle for a nonempty set of measurements."""
	if not bounds:
		raise SemanticGeometryError(f"{label} has no measurable geometry")
	return Bounds(
		min(item.min_x for item in bounds),
		min(item.min_y for item in bounds),
		max(item.max_x for item in bounds),
		max(item.max_y for item in bounds),
	)


def intersection(left: Bounds, right: Bounds) -> Bounds | None:
	"""Return the shared rectangle of two bounding boxes."""
	result = Bounds(
		max(left.min_x, right.min_x),
		max(left.min_y, right.min_y),
		min(left.max_x, right.max_x),
		min(left.max_y, right.max_y),
	)
	return result if result.width > 0.0 and result.height > 0.0 else None


def _clip_child_bounds(element: lxml.etree._Element, label: str) -> Bounds:
	"""Measure clip geometry independently of resource-only paint style."""
	copy_element = copy.deepcopy(element)
	for name in (
		"display", "visibility", "opacity", "fill", "fill-opacity", "stroke",
		"stroke-opacity", "style",
	):
		copy_element.attrib.pop(name, None)
	copy_element.set("fill", "#000000")
	copy_element.set("stroke", "none")
	return to_bounds(tools.svg_normalizer.geometry.element_bbox(copy_element), label)


def clip_bounds(root: lxml.etree._Element) -> Bounds:
	"""Measure the conservative envelope of the authored liquid clip."""
	clip = find_required(root, "anchor_liquid_clip")
	if local_name(clip) != "clipPath":
		raise SemanticGeometryError("anchor_liquid_clip must be a clipPath")
	if clip.get("clipPathUnits", "userSpaceOnUse") != "userSpaceOnUse":
		raise SemanticGeometryError("anchor_liquid_clip must use userSpaceOnUse")
	children = [
		_clip_child_bounds(element, f"anchor_liquid_clip {index}")
		for index, element in enumerate(clip.iterdescendants(), start=1)
		if isinstance(element.tag, str) and local_name(element) in GEOMETRY_TAGS
	]
	return union(children, "anchor_liquid_clip")


def reject_transforms(root: lxml.etree._Element) -> None:
	"""Refuse geometry whose coordinate frame has not been flattened."""
	transformed = [
		local_name(element)
		for element in root.iter()
		if isinstance(element.tag, str) and element.get("transform") is not None
	]
	if transformed:
		tags = ", ".join(transformed[:5])
		raise SemanticGeometryError(
			f"unflattened transform geometry ({tags}); normalize the SVG before measurement"
		)


def _material_bounds(
	root: lxml.etree._Element,
	part: str | None = None,
	paint_role: str | None = None,
) -> Bounds:
	"""Measure visible material geometry, optionally for one gravity part."""
	measured: list[Bounds] = []
	for layer in root:
		if not isinstance(layer.tag, str) or layer.get("data-vlab-layer-kind") != "material":
			continue
		if part is not None and layer.get("data-vlab-liquid-part") != part:
			continue
		if paint_role is not None and layer.get("data-vlab-paint-role") != paint_role:
			continue
		for element in layer.iterdescendants():
			if (
				not isinstance(element.tag, str)
				or local_name(element) not in GEOMETRY_TAGS
				or inside_defs(element)
				or not is_visible_renderable(element)
			):
				continue
			bbox = tools.svg_normalizer.geometry.element_bbox(element)
			if bbox is not None:
				measured.append(to_bounds(bbox, "material geometry"))
	return union(measured, f"material {part or 'all'} layers")


def material_bounds(root: lxml.etree._Element) -> Bounds:
	"""Measure all visible painted geometry in direct material-layer groups."""
	return _material_bounds(root)


def measure_material_geometry(root: lxml.etree._Element) -> MaterialGeometry:
	"""Measure one validated, normalized material SVG in a single frame."""
	reject_transforms(root)
	parts = tuple(
		(part, _material_bounds(root, part))
		for part in ("bottom", "body", "surface")
		if any(
			isinstance(layer.tag, str)
			and layer.get("data-vlab-layer-kind") == "material"
			and layer.get("data-vlab-liquid-part") == part
			for layer in root
		)
	)
	return MaterialGeometry(
		level_frame=rect_bounds(
			find_required(root, "anchor_liquid_bounds"), "anchor_liquid_bounds"
		),
		clip_envelope=clip_bounds(root),
		material=material_bounds(root),
		parts=parts,
		surface_base=(
			_material_bounds(root, "surface", "base")
			if any(
				isinstance(layer.tag, str)
				and layer.get("data-vlab-layer-kind") == "material"
				and layer.get("data-vlab-liquid-part") == "surface"
				and layer.get("data-vlab-paint-role") == "base"
				for layer in root
			)
			else None
		),
	)
