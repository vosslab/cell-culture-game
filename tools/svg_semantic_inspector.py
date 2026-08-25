#!/usr/bin/env python3
"""Inspect semantic geometry or compare paint across normalized SVG variants.

The semantic report covers one material SVG. Variant comparison geometry-matches
an asset family and proposes material candidates whose paint changes between
variants. Both modes report conservative painted bounds in SVG user units. They
deliberately do not infer volume, capacity, or physical units from artwork. The
shared SVG normalizer remains the geometry parser; browser/librsvg rendering
remains the visual oracle.
"""

from __future__ import annotations

# Standard Library
import argparse
import copy
import hashlib
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Sequence

# PIP3 modules
import lxml.etree

# Local application
import tools.svg_normalizer.geometry
import tools.svg_normalizer.model
from validation.svg.layer_recipe_validator import (
	GEOMETRY_TAGS,
	is_visible_renderable,
	validate_material_svg,
)
from validation.svg.semantic_geometry import SemanticGeometryError, measure_material_geometry


class SvgSemanticInspectionError(ValueError):
	"""Raised when semantic geometry cannot be measured without guessing."""


GEOMETRY_ATTRIBUTES = frozenset({
	"cx", "cy", "d", "height", "points", "r", "rx", "ry", "width",
	"x", "x1", "x2", "y", "y1", "y2",
})
PAINT_ATTRIBUTES = (
	"fill", "fill-opacity", "opacity", "stroke", "stroke-opacity", "stroke-width",
)


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


def _clean_number(value: float) -> float:
	"""Return stable JSON evidence without floating-point display noise."""
	cleaned = round(value, 9)
	return 0.0 if cleaned == 0.0 else cleaned


def _bounds_payload(bounds: Bounds) -> dict[str, float]:
	"""Serialize one measured rectangle with explicit edge and size fields."""
	return {
		"min_x": _clean_number(bounds.min_x),
		"min_y": _clean_number(bounds.min_y),
		"max_x": _clean_number(bounds.max_x),
		"max_y": _clean_number(bounds.max_y),
		"width": _clean_number(bounds.width),
		"height": _clean_number(bounds.height),
	}


def _local_name(element: lxml.etree._Element) -> str:
	"""Return one element's namespace-free local name."""
	return lxml.etree.QName(element).localname


def _inside_defs(element: lxml.etree._Element) -> bool:
	"""Return whether an element belongs to a resource definition."""
	return any(_local_name(parent) == "defs" for parent in element.iterancestors())


def _find_required(root: lxml.etree._Element, element_id: str) -> lxml.etree._Element:
	"""Return exactly one required authored anchor."""
	matches = [element for element in root.iter() if element.get("id") == element_id]
	if len(matches) != 1:
		raise SvgSemanticInspectionError(f"expected exactly one {element_id}")
	return matches[0]


def _required_number(element: lxml.etree._Element, name: str, label: str) -> float:
	"""Read one finite user-unit coordinate without accepting CSS units."""
	raw = element.get(name)
	if raw is None:
		raise SvgSemanticInspectionError(f"{label} is missing {name}")
	try:
		value = float(raw)
	except ValueError as error:
		raise SvgSemanticInspectionError(f"{label}.{name} must be a plain user-unit number") from error
	if not math.isfinite(value):
		raise SvgSemanticInspectionError(f"{label}.{name} must be finite")
	return value


def _rect_bounds(element: lxml.etree._Element, label: str) -> Bounds:
	"""Measure a required positive rectangle in user units."""
	if _local_name(element) != "rect":
		raise SvgSemanticInspectionError(f"{label} must be a rect")
	x = _required_number(element, "x", label)
	y = _required_number(element, "y", label)
	width = _required_number(element, "width", label)
	height = _required_number(element, "height", label)
	if width <= 0.0 or height <= 0.0:
		raise SvgSemanticInspectionError(f"{label} width and height must be positive")
	return Bounds(x, y, x + width, y + height)


def _to_bounds(measured: tools.svg_normalizer.model.BBox | str | None, label: str) -> Bounds:
	"""Convert the normalizer's bounded geometry result or fail explicitly."""
	if measured is None or isinstance(measured, str):
		raise SvgSemanticInspectionError(f"cannot measure {label} with the normalized SVG geometry model")
	return Bounds(measured.min_x, measured.min_y, measured.max_x, measured.max_y)


def _union(bounds: Sequence[Bounds], label: str) -> Bounds:
	"""Return the enclosing rectangle for a nonempty set of measurements."""
	if not bounds:
		raise SvgSemanticInspectionError(f"{label} has no measurable geometry")
	return Bounds(
		min(item.min_x for item in bounds),
		min(item.min_y for item in bounds),
		max(item.max_x for item in bounds),
		max(item.max_y for item in bounds),
	)


def _intersection(left: Bounds, right: Bounds) -> Bounds | None:
	"""Return the shared rectangle of two bounding boxes."""
	result = Bounds(
		max(left.min_x, right.min_x),
		max(left.min_y, right.min_y),
		min(left.max_x, right.max_x),
		min(left.max_y, right.max_y),
	)
	return result if result.width > 0.0 and result.height > 0.0 else None


def _clip_child_bounds(element: lxml.etree._Element, label: str) -> Bounds:
	"""Measure clip geometry independently of its non-painting resource style."""
	copy_element = copy.deepcopy(element)
	for name in ("display", "visibility", "opacity", "fill", "fill-opacity", "stroke", "stroke-opacity", "style"):
		copy_element.attrib.pop(name, None)
	copy_element.set("fill", "#000000")
	copy_element.set("stroke", "none")
	return _to_bounds(tools.svg_normalizer.geometry.element_bbox(copy_element), label)


def _clip_bounds(root: lxml.etree._Element) -> Bounds:
	"""Measure the conservative envelope of the authored liquid clip."""
	clip = _find_required(root, "anchor_liquid_clip")
	if _local_name(clip) != "clipPath":
		raise SvgSemanticInspectionError("anchor_liquid_clip must be a clipPath")
	if clip.get("clipPathUnits", "userSpaceOnUse") != "userSpaceOnUse":
		raise SvgSemanticInspectionError("anchor_liquid_clip must use userSpaceOnUse")
	children = [
		_clip_child_bounds(element, f"anchor_liquid_clip {index}")
		for index, element in enumerate(clip.iterdescendants(), start=1)
		if isinstance(element.tag, str) and _local_name(element) in GEOMETRY_TAGS
	]
	return _union(children, "anchor_liquid_clip")


def _reject_transforms(root: lxml.etree._Element) -> None:
	"""Refuse geometry whose coordinate frame the normalizer has not flattened."""
	transformed = [
		_local_name(element)
		for element in root.iter()
		if isinstance(element.tag, str) and element.get("transform") is not None
	]
	if transformed:
		tags = ", ".join(transformed[:5])
		raise SvgSemanticInspectionError(
			f"unflattened transform geometry ({tags}); normalize the SVG before inspection"
		)


def _parse_svg(svg_path: Path) -> lxml.etree._Element:
	"""Parse one local SVG without resolving entities or using the network."""
	parser = lxml.etree.XMLParser(resolve_entities=False, no_network=True)
	try:
		return lxml.etree.parse(str(svg_path), parser).getroot()
	except (OSError, lxml.etree.XMLSyntaxError) as error:
		raise SvgSemanticInspectionError(f"cannot parse {svg_path.as_posix()}: {error}") from error


def _geometry_signature(element: lxml.etree._Element) -> tuple[str, tuple[tuple[str, str], ...]]:
	"""Return paint-independent normalized geometry used to align variants."""
	attributes = tuple(sorted(
		(name, value)
		for name, value in element.attrib.items()
		if lxml.etree.QName(name).localname in GEOMETRY_ATTRIBUTES
	))
	return _local_name(element), attributes


def _paint_payload(element: lxml.etree._Element) -> dict[str, str | None]:
	"""Return presentation values whose differences provide material evidence."""
	return {name: element.get(name) for name in PAINT_ATTRIBUTES}


def _visible_geometry(root: lxml.etree._Element) -> list[lxml.etree._Element]:
	"""Return visible painted geometry in document order, excluding resources."""
	return [
		element
		for element in root.iter()
		if (
			isinstance(element.tag, str)
			and _local_name(element) in GEOMETRY_TAGS
			and not _inside_defs(element)
			and is_visible_renderable(element)
		)
	]


def _keyed_geometry(
	root: lxml.etree._Element,
) -> dict[tuple[tuple[str, tuple[tuple[str, str], ...]], int], tuple[int, lxml.etree._Element]]:
	"""Key repeated geometry by signature plus its occurrence within one SVG."""
	counts: dict[tuple[str, tuple[tuple[str, str], ...]], int] = {}
	keyed = {}
	for ordinal, element in enumerate(_visible_geometry(root), start=1):
		signature = _geometry_signature(element)
		occurrence = counts.get(signature, 0) + 1
		counts[signature] = occurrence
		keyed[(signature, occurrence)] = (ordinal, element)
	return keyed


def _signature_id(
	key: tuple[tuple[str, tuple[tuple[str, str], ...]], int],
) -> str:
	"""Return a short stable identifier for human and machine review."""
	payload = json.dumps(key, separators=(",", ":"), ensure_ascii=True)
	return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def _paint_is_white_or_translucent(paint: dict[str, str | None]) -> bool:
	"""Flag shared paint that color-difference evidence cannot classify safely."""
	colors = [paint["fill"], paint["stroke"]]
	whiteish = {"#fff", "#ffffff", "white", "#f5f5f5", "#f6fafb", "#f7f4f4", "#f8f8f8"}
	if any(color is not None and color.lower() in whiteish for color in colors):
		return True
	for name in ("fill-opacity", "stroke-opacity", "opacity"):
		raw = paint[name]
		if raw is None:
			continue
		try:
			if float(raw) < 1.0:
				return True
		except ValueError:
			return True
	return False


def _variant_element_payload(
	geometry_id: str,
	ordinal: int,
	element: lxml.etree._Element,
	paints: dict[str, dict[str, str | None]],
	match_deltas: dict[str, float],
) -> dict[str, object]:
	"""Describe one geometry-matched variant candidate."""
	measured = _to_bounds(
		tools.svg_normalizer.geometry.element_bbox(element),
		f"variant geometry {ordinal}",
	)
	return {
		"geometry_id": geometry_id,
		"ordinal": ordinal,
		"tag": _local_name(element),
		"bounds": _bounds_payload(measured),
		"paint_by_asset": paints,
		"normalized_match_max_edge_delta_by_asset": match_deltas,
	}


def _view_box(root: lxml.etree._Element) -> Bounds:
	"""Read the normalized root frame used for cross-variant comparison."""
	raw = root.get("viewBox")
	if raw is None:
		raise SvgSemanticInspectionError("variant comparison requires a viewBox")
	try:
		x, y, width, height = (float(part) for part in raw.replace(",", " ").split())
	except (TypeError, ValueError) as error:
		raise SvgSemanticInspectionError("variant comparison requires a numeric viewBox") from error
	if width <= 0.0 or height <= 0.0:
		raise SvgSemanticInspectionError("variant comparison requires a positive viewBox")
	return Bounds(x, y, x + width, y + height)


def _normalize_bounds(bounds: Bounds, view_box: Bounds) -> Bounds:
	"""Map artwork bounds into a zero-to-one frame for near-variant matching."""
	return Bounds(
		(bounds.min_x - view_box.min_x) / view_box.width,
		(bounds.min_y - view_box.min_y) / view_box.height,
		(bounds.max_x - view_box.min_x) / view_box.width,
		(bounds.max_y - view_box.min_y) / view_box.height,
	)


def _variant_entries(root: lxml.etree._Element) -> list[dict[str, object]]:
	"""Measure visible geometry once for deterministic family correspondence."""
	view_box = _view_box(root)
	entries = []
	for ordinal, element in enumerate(_visible_geometry(root), start=1):
		bounds = _to_bounds(tools.svg_normalizer.geometry.element_bbox(element), f"variant geometry {ordinal}")
		entries.append({
			"ordinal": ordinal,
			"element": element,
			"bounds": bounds,
			"normalized_bounds": _normalize_bounds(bounds, view_box),
		})
	return entries


def _max_edge_delta(left: Bounds, right: Bounds) -> float:
	"""Return the largest normalized bounding-edge disagreement."""
	return max(
		abs(left.min_x - right.min_x),
		abs(left.min_y - right.min_y),
		abs(left.max_x - right.max_x),
		abs(left.max_y - right.max_y),
	)


def _match_variant_entries(
	reference: Sequence[dict[str, object]],
	candidate: Sequence[dict[str, object]],
	*,
	maximum_edge_delta: float = 0.02,
) -> tuple[dict[int, tuple[int, float]], list[int], list[int]]:
	"""Greedily align near-identical artwork by tag and normalized painted bounds."""
	possible = []
	for reference_index, reference_entry in enumerate(reference):
		for candidate_index, candidate_entry in enumerate(candidate):
			if _local_name(reference_entry["element"]) != _local_name(candidate_entry["element"]):
				continue
			delta = _max_edge_delta(
				reference_entry["normalized_bounds"],
				candidate_entry["normalized_bounds"],
			)
			if delta <= maximum_edge_delta:
				ordinal_delta = abs(reference_entry["ordinal"] - candidate_entry["ordinal"])
				possible.append((delta, ordinal_delta, reference_index, candidate_index))
	possible.sort()
	matches = {}
	used_candidates = set()
	for delta, _ordinal_delta, reference_index, candidate_index in possible:
		if reference_index in matches or candidate_index in used_candidates:
			continue
		matches[reference_index] = (candidate_index, delta)
		used_candidates.add(candidate_index)
	missing_reference = [index for index in range(len(reference)) if index not in matches]
	unmatched_candidate = [index for index in range(len(candidate)) if index not in used_candidates]
	return matches, missing_reference, unmatched_candidate


def compare_svg_variants(svg_paths: Sequence[Path]) -> dict[str, object]:
	"""Propose material geometry from paint differences in an SVG family.

	Paint variation is evidence, not a final semantic decision. Shared white or
	translucent geometry is emitted separately for the required physical review.
	"""
	if len(svg_paths) < 2:
		raise SvgSemanticInspectionError("variant comparison requires at least two SVG files")
	roots = [_parse_svg(path) for path in svg_paths]
	for root in roots:
		_reject_transforms(root)
	entries_by_asset = [_variant_entries(root) for root in roots]
	reference_entries = entries_by_asset[0]
	matches_by_asset = [{index: (index, 0.0) for index in range(len(reference_entries))}]
	unmatched = []
	for path, entries in zip(svg_paths[1:], entries_by_asset[1:], strict=True):
		matches, missing_reference, unmatched_asset = _match_variant_entries(reference_entries, entries)
		matches_by_asset.append(matches)
		if missing_reference or unmatched_asset:
			unmatched.append({
				"asset": path.as_posix(),
				"reference_ordinals_without_match": [
					reference_entries[index]["ordinal"] for index in missing_reference
				],
				"asset_ordinals_without_match": [entries[index]["ordinal"] for index in unmatched_asset],
			})
	changed = []
	shared_review = []
	for reference_index, reference_entry in enumerate(reference_entries):
		if any(reference_index not in matches for matches in matches_by_asset):
			continue
		ordinal = reference_entry["ordinal"]
		element = reference_entry["element"]
		geometry_id = hashlib.sha256(
			f"{svg_paths[0].as_posix()}:{ordinal}:{_geometry_signature(element)}".encode("utf-8")
		).hexdigest()[:12]
		paints = {}
		match_deltas = {}
		for path, entries, matches in zip(svg_paths, entries_by_asset, matches_by_asset, strict=True):
			candidate_index, delta = matches[reference_index]
			paints[path.as_posix()] = _paint_payload(entries[candidate_index]["element"])
			match_deltas[path.as_posix()] = _clean_number(delta)
		paint_values = list(paints.values())
		payload = _variant_element_payload(
			geometry_id, ordinal, element, paints, match_deltas,
		)
		if any(paint != paint_values[0] for paint in paint_values[1:]):
			payload["evidence"] = "paint varies across geometry-matched variants"
			changed.append(payload)
		elif _paint_is_white_or_translucent(paint_values[0]):
			payload["evidence"] = "shared white or translucent paint requires physical review"
			shared_review.append(payload)
	return {
		"schema_version": 2,
		"mode": "variant_paint_comparison",
		"assets": [path.as_posix() for path in svg_paths],
		"view_box_by_asset": {
			path.as_posix(): root.get("viewBox")
			for path, root in zip(svg_paths, roots, strict=True)
		},
		"correspondence_model": {
			"frame": "normalized viewBox coordinates",
			"maximum_painted_edge_delta": 0.02,
			"matching": "same element tag, then smallest edge and document-order difference",
		},
		"interpretation": {
			"changed_paint": "strong material candidate; confirm by physical behavior",
			"shared_white_or_translucent": "manual review required near donor liquid geometry",
			"unmatched_geometry": "manual correspondence review required",
		},
		"changed_paint": changed,
		"shared_white_or_translucent": shared_review,
		"unmatched_geometry": unmatched,
	}


def _element_payload(element: lxml.etree._Element, ordinal: int, layer_name: str) -> dict[str, object] | None:
	"""Describe one visible semantic shape using the normalizer's geometry model."""
	if _inside_defs(element) or not is_visible_renderable(element):
		return None
	measured = tools.svg_normalizer.geometry.element_bbox(element)
	if measured is None:
		return None
	bounds = _to_bounds(measured, f"{layer_name} geometry {ordinal}")
	return {
		"ordinal": ordinal,
		"tag": _local_name(element),
		"fill": element.get("fill"),
		"stroke": element.get("stroke"),
		"bounds": _bounds_payload(bounds),
	}


def _semantic_layer_payloads(root: lxml.etree._Element) -> list[dict[str, object]]:
	"""Report every semantic layer and its individual painted elements."""
	layers = []
	for layer in root:
		if not isinstance(layer.tag, str) or layer.get("data-vlab-layer-name") is None:
			continue
		name = layer.get("data-vlab-layer-name")
		kind = layer.get("data-vlab-layer-kind")
		assert name is not None and kind is not None
		elements = []
		for ordinal, element in enumerate(layer.iterdescendants(), start=1):
			if not isinstance(element.tag, str) or _local_name(element) not in GEOMETRY_TAGS:
				continue
			payload = _element_payload(element, ordinal, name)
			if payload is not None:
				elements.append(payload)
		bounds = _union(
			[
				Bounds(
					item["bounds"]["min_x"], item["bounds"]["min_y"],
					item["bounds"]["max_x"], item["bounds"]["max_y"],
				)
				for item in elements
			],
			f"semantic layer {name}",
		)
		layers.append({
			"name": name,
			"kind": kind,
			"paint_role": layer.get("data-vlab-paint-role"),
			"liquid_part": layer.get("data-vlab-liquid-part"),
			"adjustment": layer.get("data-vlab-adjustment"),
			"bounds": _bounds_payload(bounds),
			"elements": elements,
		})
	return layers


def inspect_material_svg(svg_path: Path) -> dict[str, object]:
	"""Return a deterministic semantic-geometry report for one normalized SVG."""
	root = _parse_svg(svg_path)
	validate_material_svg(root)
	try:
		geometry = measure_material_geometry(root)
	except SemanticGeometryError as error:
		raise SvgSemanticInspectionError(str(error)) from error
	level_bounds = geometry.level_frame
	clip_bounds = geometry.clip_envelope
	layers = _semantic_layer_payloads(root)
	material_layers = [layer for layer in layers if layer["kind"] == "material"]
	material_bounds = _union(
		[
			Bounds(
				layer["bounds"]["min_x"], layer["bounds"]["min_y"],
				layer["bounds"]["max_x"], layer["bounds"]["max_y"],
			)
			for layer in material_layers
		],
		"material layers",
	)
	visible_material_bounds = _intersection(material_bounds, clip_bounds)
	top_gap = material_bounds.min_y - clip_bounds.min_y
	level_top_gap = material_bounds.min_y - level_bounds.min_y
	part_bounds = {name: bounds for name, bounds in geometry.parts}
	warnings = []
	if top_gap > 0.0:
		warnings.append("material geometry begins below the liquid clip top")
	if level_top_gap > 0.0:
		warnings.append("material geometry begins below the authored level-frame top")
	if material_bounds.max_y < clip_bounds.max_y:
		warnings.append("material geometry ends above the liquid clip bottom")
	body = part_bounds.get("body")
	bottom = part_bounds.get("bottom")
	surface = part_bounds.get("surface")
	if body is not None and bottom is not None and body.max_y < bottom.min_y:
		warnings.append("body and bottom geometry have a vertical gap")
	if body is not None and surface is not None and not surface.min_y <= body.min_y <= surface.max_y:
		warnings.append("surface geometry does not meet the authored body top")
	return {
		"schema_version": 2,
		"asset": svg_path.as_posix(),
		"sha256": hashlib.sha256(svg_path.read_bytes()).hexdigest(),
		"coordinate_system": {
			"dimension": "2d",
			"units": "svg_user_units",
			"x_axis": "right",
			"y_axis": "down",
			"bounds_model": "conservative_painted_aabb",
			"volume_inference": "none",
		},
		"view_box": root.get("viewBox"),
		"anchors": {
			"level_frame": _bounds_payload(level_bounds),
			"clip_envelope": _bounds_payload(clip_bounds),
		},
		"material": {
			"bounds": _bounds_payload(material_bounds),
			"clip_bbox_intersection": (
				_bounds_payload(visible_material_bounds) if visible_material_bounds is not None else None
			),
			"top_gap_to_clip": _clean_number(top_gap),
			"top_gap_to_level_frame": _clean_number(level_top_gap),
			"parts": {name: _bounds_payload(bounds) for name, bounds in geometry.parts},
			"surface_reference_y": (
				_clean_number(geometry.surface_reference_y)
				if geometry.surface_reference_y is not None else None
			),
			"body_join_y": (
				_clean_number(geometry.body_join_y)
				if geometry.body_join_y is not None else None
			),
			"body_anchor_y": (
				_clean_number(geometry.body_anchor_y)
				if geometry.body_anchor_y is not None else None
			),
		},
		"layers": layers,
		"warnings": warnings,
	}


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
	"""Parse the intentionally small read-only CLI."""
	parser = argparse.ArgumentParser(
		description="Inspect semantic geometry or compare paint across normalized SVG variants."
	)
	parser.add_argument("svg", nargs="+", type=Path, help="normalized material SVG to inspect")
	parser.add_argument(
		"--compare-variants",
		action="store_true",
		help="geometry-match an SVG family and report paint-change candidates",
	)
	return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
	"""Print deterministic JSON reports; never modify an SVG."""
	args = parse_args(argv)
	try:
		if args.compare_variants:
			payload: dict[str, object] | list[dict[str, object]] = compare_svg_variants(args.svg)
		else:
			reports = [inspect_material_svg(path) for path in args.svg]
			payload = reports[0] if len(reports) == 1 else reports
	except (SvgSemanticInspectionError, ValueError) as error:
		print(f"ERROR: {error}", file=sys.stderr)
		return 2
	print(json.dumps(payload, indent=2, sort_keys=True))
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
