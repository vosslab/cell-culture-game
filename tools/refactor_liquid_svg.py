#!/usr/bin/env python3
"""Create one reviewed self-describing material SVG from a donor SVG.

This is a development-only conversion helper, not a recipe format or a
classifier.  It accepts a transient JSON review file with this closed shape:

```
{
  "asset_path": "/absolute/path/to/donor.svg",
  "source_sha256": "<lowercase SHA-256 of the donor bytes>",
  "runs": [
    {
      "layer_name": "liquid_body",
      "paint_role": "base",
      "liquid_part": "body",
      "unit_indices": [2, 3]
    },
    {
      "layer_name": "liquid_glint",
      "paint_role": "highlight",
      "liquid_part": "surface",
      "adjustment": "0.18",
      "unit_indices": [4]
    }
  ]
}
```

``unit_indices`` are zero-based ordinals among direct *element* children of
the source SVG (including ``defs`` and other structural children).  A selected
direct-root ``g`` is atomic: this tool never selects, moves, or labels a child
of that group independently.  Runs are ordered and together must form one
unbroken band of visible/renderable artwork units.  Unselected artwork before
and after that band becomes the optional fixed-back and fixed-front groups.

The review file is deliberately hash-guarded conversion input.  It is never
copied beside assets, emitted to generated output, or used by the runtime.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import lxml.etree

from validation.svg.layer_recipe_validator import (
	ADJUSTMENT_RE,
	GEOMETRY_TAGS,
	LAYER_NAME_RE,
	MaterialSvgValidationError,
	is_visible_renderable,
	validate_material_svg,
	validate_reserved_attributes,
)

SVG_NS = "http://www.w3.org/2000/svg"
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_ROOT_NON_ART_TAGS = frozenset({"defs", "desc", "metadata", "title"})
_FIXED_LAYER_NAMES = frozenset({"fixed_back", "fixed_front"})


class LiquidSvgRefactorError(ValueError):
	"""Raised for an author-facing refusal to transform one donor SVG."""


@dataclass(frozen=True)
class ReviewedRun:
	"""One ordered, reviewed material semantic group."""

	layer_name: str
	paint_role: str
	liquid_part: str
	adjustment: str | None
	unit_indices: tuple[int, ...]


@dataclass(frozen=True)
class ReviewPlan:
	"""The complete closed review input for one exact donor source."""

	asset_path: Path
	source_sha256: str
	runs: tuple[ReviewedRun, ...]


@dataclass(frozen=True)
class RefactorResult:
	"""Result of a conversion attempt; no-write success is explicit."""

	output_path: Path
	changed: bool
	material_unit_count: int


def _local_name(element: lxml.etree._Element) -> str:
	return lxml.etree.QName(element).localname


def _inside_defs(element: lxml.etree._Element) -> bool:
	return any(_local_name(parent) == "defs" for parent in element.iterancestors())


def _is_hidden(element: lxml.etree._Element) -> bool:
	"""Return whether a source anchor is already non-rendering artwork."""
	return not is_visible_renderable(element)


def _json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
	"""Decode JSON objects while refusing duplicate keys."""
	result: dict[str, object] = {}
	for key, value in pairs:
		if key in result:
			raise LiquidSvgRefactorError(f"review JSON has duplicate key {key!r}")
		result[key] = value
	return result


def _require_mapping(value: object, label: str) -> dict[str, object]:
	if not isinstance(value, dict):
		raise LiquidSvgRefactorError(f"{label} must be a JSON object")
	return value


def _require_exact_keys(mapping: dict[str, object], allowed: frozenset[str], label: str) -> None:
	unknown = set(mapping) - allowed
	if unknown:
		raise LiquidSvgRefactorError(f"{label} has unknown key(s): {', '.join(sorted(unknown))}")


def _require_string(mapping: dict[str, object], key: str, label: str) -> str:
	value = mapping.get(key)
	if not isinstance(value, str) or not value:
		raise LiquidSvgRefactorError(f"{label}.{key} must be a nonempty string")
	return value


def load_review_plan(review_path: Path) -> ReviewPlan:
	"""Parse and validate one closed, transient conversion-review input."""
	try:
		decoded = json.loads(review_path.read_text(encoding="utf-8"), object_pairs_hook=_json_object)
	except (OSError, json.JSONDecodeError) as exc:
		raise LiquidSvgRefactorError(f"cannot read review JSON {review_path}: {exc}") from exc
	mapping = _require_mapping(decoded, "review")
	_require_exact_keys(mapping, frozenset({"asset_path", "source_sha256", "runs"}), "review")
	asset_path = Path(_require_string(mapping, "asset_path", "review")).resolve()
	source_sha256 = _require_string(mapping, "source_sha256", "review")
	if _SHA256_RE.fullmatch(source_sha256) is None:
		raise LiquidSvgRefactorError("review.source_sha256 must be a lowercase SHA-256")
	raw_runs = mapping.get("runs")
	if not isinstance(raw_runs, list) or not raw_runs:
		raise LiquidSvgRefactorError("review.runs must be a nonempty JSON array")
	runs: list[ReviewedRun] = []
	names: set[str] = set()
	for ordinal, raw_run in enumerate(raw_runs):
		label = f"review.runs[{ordinal}]"
		run = _require_mapping(raw_run, label)
		_require_exact_keys(
			run,
			frozenset({"layer_name", "paint_role", "liquid_part", "adjustment", "unit_indices"}),
			label,
		)
		name = _require_string(run, "layer_name", label)
		if LAYER_NAME_RE.fullmatch(name) is None or name in names or name in _FIXED_LAYER_NAMES:
			raise LiquidSvgRefactorError(f"{label}.layer_name must be a unique snake_case material name")
		names.add(name)
		role = _require_string(run, "paint_role", label)
		if role not in {"base", "highlight", "shadow"}:
			raise LiquidSvgRefactorError(f"{label}.paint_role must be base, highlight, or shadow")
		liquid_part = _require_string(run, "liquid_part", label)
		if liquid_part not in {"bottom", "body", "surface"}:
			raise LiquidSvgRefactorError(f"{label}.liquid_part must be bottom, body, or surface")
		adjustment_value = run.get("adjustment")
		if role == "base":
			if "adjustment" in run:
				raise LiquidSvgRefactorError(f"{label}.adjustment is forbidden for base")
			adjustment: str | None = None
		else:
			if not isinstance(adjustment_value, str) or ADJUSTMENT_RE.fullmatch(adjustment_value) is None:
				raise LiquidSvgRefactorError(f"{label}.adjustment must be a strict decimal string")
			adjustment = adjustment_value
			value = float(adjustment)
			if role == "highlight" and not 0.0 < value <= 0.5:
				raise LiquidSvgRefactorError(f"{label}.adjustment must be in (0, 0.5] for highlight")
			if role == "shadow" and not -0.5 <= value < 0.0:
				raise LiquidSvgRefactorError(f"{label}.adjustment must be in [-0.5, 0) for shadow")
		indices = run.get("unit_indices")
		if not isinstance(indices, list) or not indices or any(isinstance(item, bool) or not isinstance(item, int) for item in indices):
			raise LiquidSvgRefactorError(f"{label}.unit_indices must be a nonempty integer array")
		if indices != sorted(indices) or len(indices) != len(set(indices)):
			raise LiquidSvgRefactorError(f"{label}.unit_indices must be sorted and unique")
		runs.append(ReviewedRun(name, role, liquid_part, adjustment, tuple(indices)))
	return ReviewPlan(asset_path, source_sha256, tuple(runs))


def _element_children(root: lxml.etree._Element) -> dict[int, lxml.etree._Element]:
	"""Return zero-based direct element-child ordinals, ignoring comments."""
	children: dict[int, lxml.etree._Element] = {}
	ordinal = 0
	for child in root:
		if isinstance(child.tag, str):
			children[ordinal] = child
			ordinal += 1
	return children


def _find_one_anchor(root: lxml.etree._Element, anchor_id: str) -> lxml.etree._Element:
	matches = [element for element in root.iter() if isinstance(element.tag, str) and element.get("id") == anchor_id]
	if len(matches) != 1:
		raise LiquidSvgRefactorError(f"expected exactly one {anchor_id}")
	return matches[0]


def _validate_rect_geometry(bounds: lxml.etree._Element) -> None:
	if _local_name(bounds) != "rect":
		raise LiquidSvgRefactorError("anchor_liquid_bounds must be a rect")
	if bounds.get("transform") is not None:
		raise LiquidSvgRefactorError("anchor_liquid_bounds cannot carry an unresolved transform")
	values: dict[str, float] = {}
	for key in ("x", "y", "width", "height"):
		raw = bounds.get(key)
		if raw is None:
			raise LiquidSvgRefactorError(f"anchor_liquid_bounds requires numeric {key}")
		try:
			value = float(raw)
		except ValueError as exc:
			raise LiquidSvgRefactorError(f"anchor_liquid_bounds {key} must be finite numeric") from exc
		if not math.isfinite(value):
			raise LiquidSvgRefactorError(f"anchor_liquid_bounds {key} must be finite numeric")
		values[key] = value
	if values["width"] <= 0.0 or values["height"] <= 0.0:
		raise LiquidSvgRefactorError("anchor_liquid_bounds width and height must be positive")
	for key in ("rx", "ry"):
		raw = bounds.get(key)
		if raw is None:
			continue
		try:
			value = float(raw)
		except ValueError as exc:
			raise LiquidSvgRefactorError(f"anchor_liquid_bounds {key} must be finite numeric") from exc
		if not math.isfinite(value) or value < 0.0:
			raise LiquidSvgRefactorError(f"anchor_liquid_bounds {key} must be finite nonnegative numeric")


def _clean_clip_bounds_geometry(bounds: lxml.etree._Element) -> lxml.etree._Element:
	"""Copy only supported rect geometry into a functional clip child.

	The ID-bearing bounds anchor is compiler-only and must become hidden root
	geometry. A legacy anchor embedded in its clip can carry non-rendering
	presentation state, which would otherwise make the retained clip empty.
	"""
	clone = lxml.etree.Element(bounds.tag)
	for key in ("x", "y", "width", "height", "rx", "ry"):
		value = bounds.get(key)
		if value is not None:
			clone.set(key, value)
	return clone


def _canonicalize_anchors(root: lxml.etree._Element) -> None:
	"""Keep one clip anchor and make the bounds anchor hidden root geometry."""
	clip = _find_one_anchor(root, "anchor_liquid_clip")
	bounds = _find_one_anchor(root, "anchor_liquid_bounds")
	if _local_name(clip) != "clipPath" or not _inside_defs(clip):
		raise LiquidSvgRefactorError("anchor_liquid_clip must be one clipPath inside defs")
	_validate_rect_geometry(bounds)
	if _inside_defs(bounds):
		if bounds.getparent() is not clip:
			raise LiquidSvgRefactorError("bounds inside defs must be a direct anchor_liquid_clip geometry child")
		clone = _clean_clip_bounds_geometry(bounds)
		clip.insert(clip.index(bounds), clone)
		clip.remove(bounds)
		root.append(bounds)
	elif not _is_hidden(bounds):
		raise LiquidSvgRefactorError("outside-defs anchor_liquid_bounds must already be hidden")
	bounds.set("display", "none")


def _contains_visible_geometry(element: lxml.etree._Element) -> bool:
	for descendant in element.iter():
		if (
			isinstance(descendant.tag, str)
			and _local_name(descendant) in GEOMETRY_TAGS
			and is_visible_renderable(descendant)
		):
			return True
	return False


def _visible_artwork_units(
	root: lxml.etree._Element,
	children: dict[int, lxml.etree._Element],
	bounds: lxml.etree._Element,
) -> dict[int, lxml.etree._Element]:
	"""Find direct-root, atomic visible artwork while rejecting opaque renderers."""
	units: dict[int, lxml.etree._Element] = {}
	for index, child in children.items():
		tag = _local_name(child)
		if child is bounds or tag in _ROOT_NON_ART_TAGS:
			continue
		if tag == "style":
			raise LiquidSvgRefactorError("style blocks and selector-driven behavior are unsupported for refactoring")
		if _contains_visible_geometry(child):
			units[index] = child
			continue
		if tag in {"image", "text", "textPath", "tspan", "use", "symbol", "foreignObject"}:
			raise LiquidSvgRefactorError(f"unsupported root artwork element <{tag}>")
	return units


def _validate_review_selection(plan: ReviewPlan, units: dict[int, lxml.etree._Element]) -> list[int]:
	selected = [index for run in plan.runs for index in run.unit_indices]
	if len(selected) != len(set(selected)):
		raise LiquidSvgRefactorError("review material runs may not select one artwork unit twice")
	if selected != sorted(selected):
		raise LiquidSvgRefactorError("review material runs must be in document order")
	unknown = [index for index in selected if index not in units]
	if unknown:
		raise LiquidSvgRefactorError(f"review selected non-artwork root-child index {unknown[0]}")
	ordered_units = sorted(units)
	positions_by_index = {index: position for position, index in enumerate(ordered_units)}
	previous_position = -1
	for run in plan.runs:
		run_positions = [positions_by_index[index] for index in run.unit_indices]
		if run_positions != list(range(run_positions[0], run_positions[-1] + 1)):
			raise LiquidSvgRefactorError("each material run must occupy consecutive artwork positions")
		if run_positions[0] <= previous_position:
			raise LiquidSvgRefactorError("review material runs must be in document order")
		previous_position = run_positions[-1]
	positions = [positions_by_index[index] for index in selected]
	if positions != list(range(positions[0], positions[-1] + 1)):
		raise LiquidSvgRefactorError("material units must occupy every artwork position from first through last")
	return selected


def _semantic_group(run: ReviewedRun | None, kind: str) -> lxml.etree._Element:
	group = lxml.etree.Element(f"{{{SVG_NS}}}g")
	if run is None:
		name = "fixed_back" if kind == "fixed_back" else "fixed_front"
		group.set("data-vlab-layer-name", name)
		group.set("data-vlab-layer-kind", "fixed")
		return group
	group.set("data-vlab-layer-name", run.layer_name)
	group.set("data-vlab-layer-kind", "material")
	group.set("data-vlab-paint-role", run.paint_role)
	group.set("data-vlab-liquid-part", run.liquid_part)
	if run.adjustment is not None:
		group.set("data-vlab-adjustment", run.adjustment)
	return group


def _replace_units_with_groups(
	root: lxml.etree._Element,
	units: dict[int, lxml.etree._Element],
	plan: ReviewPlan,
	selected: list[int],
) -> int:
	"""Replace atomic artwork units with fixed/material groups without reordering art."""
	ordered_units = sorted(units)
	first_selected = selected[0]
	last_selected = selected[-1]
	back_indices = [index for index in ordered_units if index < first_selected]
	front_indices = [index for index in ordered_units if index > last_selected]
	group_items: list[tuple[int, lxml.etree._Element, tuple[int, ...]]] = []
	if back_indices:
		group_items.append((back_indices[0], _semantic_group(None, "fixed_back"), tuple(back_indices)))
	for run in plan.runs:
		group_items.append((run.unit_indices[0], _semantic_group(run, "material"), run.unit_indices))
	if front_indices:
		group_items.append((front_indices[0], _semantic_group(None, "fixed_front"), tuple(front_indices)))
	original_children = list(root)
	element_ordinals = {id(child): ordinal for ordinal, child in _element_children(root).items()}
	for child in original_children:
		root.remove(child)
	for _, group, indices in group_items:
		for index in indices:
			group.append(units[index])
	groups_by_first = {first: group for first, group, _ in group_items}
	assigned = {index for _, _, indices in group_items for index in indices}
	for child in original_children:
		if not isinstance(child.tag, str):
			root.append(child)
			continue
		ordinal = element_ordinals[id(child)]
		if ordinal in groups_by_first:
			root.append(groups_by_first[ordinal])
		elif ordinal not in assigned:
			root.append(child)
	return len(selected)


def _serialize(root: lxml.etree._Element) -> bytes:
	return lxml.etree.tostring(root, encoding="utf-8", xml_declaration=True, pretty_print=True) + b"\n"


def _atomic_write(output_path: Path, contents: bytes) -> None:
	if not output_path.parent.is_dir():
		raise LiquidSvgRefactorError(f"output parent does not exist: {output_path.parent}")
	with tempfile.NamedTemporaryFile(prefix=f".{output_path.name}.", dir=output_path.parent, delete=False) as staged:
		staged.write(contents)
		staged_path = Path(staged.name)
	try:
		os.replace(staged_path, output_path)
	except OSError:
		staged_path.unlink(missing_ok=True)
		raise


def refactor_liquid_svg(
	input_path: Path,
	review_path: Path,
	output_path: Path | None = None,
	*,
	in_place: bool = False,
) -> RefactorResult:
	"""Transform a reviewed donor SVG or report exact-material no-write success."""
	input_path = input_path.resolve()
	if not input_path.is_file():
		raise LiquidSvgRefactorError(f"input SVG does not exist: {input_path}")
	if in_place:
		if output_path is not None and output_path.resolve() != input_path:
			raise LiquidSvgRefactorError("--in-place cannot be combined with a different output path")
		destination = input_path
	else:
		destination = (output_path or input_path.with_name(f"{input_path.stem}.material.svg")).resolve()
		if destination == input_path:
			raise LiquidSvgRefactorError("default conversion output must not overwrite the donor; use --in-place")
	source_bytes = input_path.read_bytes()
	try:
		root = lxml.etree.fromstring(source_bytes, lxml.etree.XMLParser(resolve_entities=False, no_network=True))
	except lxml.etree.XMLSyntaxError as exc:
		raise LiquidSvgRefactorError(f"cannot parse input SVG: {exc}") from exc
	if _local_name(root) != "svg":
		raise LiquidSvgRefactorError("input document root must be svg")
	if root.get("data-vlab-rendering") == "material":
		try:
			validate_material_svg(root)
		except MaterialSvgValidationError as exc:
			raise LiquidSvgRefactorError(f"existing material SVG is invalid: {exc}") from exc
		return RefactorResult(input_path, False, 0)
	if destination.exists():
		raise LiquidSvgRefactorError(f"output already exists: {destination}")
	try:
		validate_reserved_attributes(root)
	except MaterialSvgValidationError as exc:
		raise LiquidSvgRefactorError(f"donor uses an invalid reserved SVG contract: {exc}") from exc
	plan = load_review_plan(review_path)
	if plan.asset_path != input_path:
		raise LiquidSvgRefactorError("review.asset_path does not identify this exact donor path")
	if hashlib.sha256(source_bytes).hexdigest() != plan.source_sha256:
		raise LiquidSvgRefactorError("review.source_sha256 does not match donor source bytes")
	if any(isinstance(element.tag, str) and _local_name(element) == "style" for element in root.iter()):
		raise LiquidSvgRefactorError("style blocks and selector-driven behavior are unsupported for refactoring")
	_canonicalize_anchors(root)
	bounds = _find_one_anchor(root, "anchor_liquid_bounds")
	children = _element_children(root)
	units = _visible_artwork_units(root, children, bounds)
	if not units:
		raise LiquidSvgRefactorError("donor has no visible/renderable direct-root artwork units")
	selected = _validate_review_selection(plan, units)
	root.set("data-vlab-rendering", "material")
	count = _replace_units_with_groups(root, units, plan, selected)
	try:
		validate_material_svg(root)
	except MaterialSvgValidationError as exc:
		raise LiquidSvgRefactorError(f"transformed SVG violates the material contract: {exc}") from exc
	_atomic_write(destination, _serialize(root))
	return RefactorResult(destination, True, count)


def _parse_args(argv: list[str]) -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Refactor one reviewed donor SVG into semantic material groups.")
	parser.add_argument("--input", "-i", type=Path, required=True, help="Donor SVG source path.")
	parser.add_argument("--review", "-r", type=Path, required=True, help="Transient hash-guarded JSON review input.")
	parser.add_argument("--output", "-o", type=Path, help="New material SVG path; must not already exist.")
	parser.add_argument("--in-place", action="store_true", help="Replace the donor atomically after successful validation.")
	return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
	"""Run the development helper and print one concise author-facing result."""
	arguments = _parse_args(sys.argv[1:] if argv is None else argv)
	try:
		result = refactor_liquid_svg(arguments.input, arguments.review, arguments.output, in_place=arguments.in_place)
	except LiquidSvgRefactorError as exc:
		print(f"refactor_liquid_svg: {exc}", file=sys.stderr)
		return 2
	if result.changed:
		print(f"wrote {result.output_path} ({result.material_unit_count} material artwork units)")
	else:
		print(f"already valid material SVG; no write: {arguments.input.resolve()}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
