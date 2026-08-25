#!/usr/bin/env python3
"""Compile material SVG forms and emit one opaque liquid-region manifest."""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import tempfile
from pathlib import Path

import lxml.etree

import tools.svg_normalizer.workflow
from validation.svg.layer_recipe_validator import validate_material_svg, validate_reserved_attributes
from validation.svg.asset_taxonomy_validator import validate_asset_taxonomy
from validation.svg.semantic_geometry import measure_material_geometry

SVG_NS = "http://www.w3.org/2000/svg"
_PAINT_CHANNELS = ("fill", "stroke")


def _tag(name: str) -> str:
	return f"{{{SVG_NS}}}{name}"


def _opaque_handle(asset_name: str, purpose: str, ordinal: int) -> str:
	"""Return a deterministic opaque id, never an authored recipe name."""
	digest = hashlib.sha256(f"{asset_name}:{purpose}:{ordinal}".encode("utf-8")).hexdigest()[:16]
	return f"lr_{digest}"


def _local_name(element: lxml.etree._Element) -> str:
	return lxml.etree.QName(element).localname


def _style_value(element: lxml.etree._Element, name: str) -> str | None:
	"""Resolve the bounded inline/presentation cascade used by material SVGs."""
	selected: tuple[bool, str] | None = None
	for declaration in element.get("style", "").split(";"):
		key, separator, value = declaration.partition(":")
		if not separator or key.strip().lower() != name:
			continue
		value = value.strip()
		important = value.lower().endswith("!important")
		if important:
			value = value[: -len("!important")].rstrip()
		if selected is None or important or not selected[0]:
			selected = (important, value)
	if selected is not None:
		return selected[1]
	value = element.get(name)
	return value.strip() if value is not None else None


def _is_css_keyword(value: str | None, keyword: str) -> bool:
	"""Compare SVG/CSS keyword values without changing authored spelling."""
	return value is not None and value.casefold() == keyword


def _set_paint(element: lxml.etree._Element, channel: str, value: str) -> None:
	"""Set a presentation value, replacing inline style when it owns the channel."""
	style = element.get("style")
	if style is not None:
		declarations = [
			declaration for declaration in style.split(";")
			if not (declaration.partition(":")[1] and declaration.partition(":")[0].strip().lower() == channel)
		]
		declarations.append(f"{channel}:{value}")
		element.set("style", ";".join(declarations))
		element.attrib.pop(channel, None)
		return
	element.set(channel, value)


def _resolved_paint(element: lxml.etree._Element, channel: str) -> str:
	"""Resolve the supported inherited fallback through the SVG root."""
	current: lxml.etree._Element | None = element
	while current is not None:
		value = _style_value(current, channel)
		if value is not None and not _is_css_keyword(value, "inherit"):
			return value
		current = current.getparent()
	return "black" if channel == "fill" else "none"


def _paint_owner(element: lxml.etree._Element, layer: lxml.etree._Element, channel: str) -> lxml.etree._Element:
	"""Return the nearest explicit owner inside this semantic layer only."""
	current: lxml.etree._Element | None = element
	while current is not None:
		if _style_value(current, channel) is not None:
			return current
		if current is layer:
			break
		current = current.getparent()
	return layer


def _material_layers(root: lxml.etree._Element) -> list[lxml.etree._Element]:
	return [
		child for child in root
		if isinstance(child.tag, str)
		and _local_name(child) == "g"
		and child.get("data-vlab-layer-kind") == "material"
	]


def _bounds(root: lxml.etree._Element) -> dict[str, float]:
	bounds = next(element for element in root.iter() if element.get("id") == "anchor_liquid_bounds")
	values: dict[str, float] = {}
	for key in ("x", "y", "width", "height"):
		raw = bounds.get(key)
		if raw is None:
			raise ValueError(f"anchor_liquid_bounds requires numeric {key}")
		try:
			value = float(raw)
		except ValueError as exc:
			raise ValueError(f"anchor_liquid_bounds {key} must be finite numeric") from exc
		if not math.isfinite(value):
			raise ValueError(f"anchor_liquid_bounds {key} must be finite numeric")
		values[key] = value
	if values["width"] <= 0.0 or values["height"] <= 0.0:
		raise ValueError("anchor_liquid_bounds width and height must be positive")
	return values


def _max_fill_percent(root: lxml.etree._Element) -> int | None:
	"""Return the already-validated optional authored fill ceiling."""
	raw = root.get("data-vlab-max-fill-percent")
	return int(raw) if raw is not None else None


def _min_fill_percent(root: lxml.etree._Element) -> int | None:
	"""Return the validated optional nonzero authored fill floor."""
	raw = root.get("data-vlab-min-fill-percent")
	return int(raw) if raw is not None else None


def _body_start_fill_percent(root: lxml.etree._Element) -> float | None:
	"""Return the validated volume fraction where a conical vessel reaches its body."""
	raw = root.get("data-vlab-body-start-fill-percent")
	return float(raw) if raw is not None else None


def _fill_height_exponent(root: lxml.etree._Element) -> float | None:
	"""Return the validated optional normalized perceptual height exponent."""
	raw = root.get("data-vlab-fill-height-exponent")
	return float(raw) if raw is not None else None


def _rewrite_paint(layer: lxml.etree._Element, paint_handle: str) -> None:
	"""Rewrite every painted material channel while retaining literal fallback paint."""
	rewritten: set[tuple[int, str]] = set()
	for element in layer.iter():
		if not isinstance(element.tag, str):
			continue
		if _local_name(element) not in {"path", "rect", "circle", "ellipse", "line", "polyline", "polygon"}:
			continue
		for channel in _PAINT_CHANNELS:
			owner = _paint_owner(element, layer, channel)
			fallback = _resolved_paint(element, channel)
			key = (id(owner), channel)
			if key in rewritten or _is_css_keyword(fallback, "none"):
				continue
			if fallback.casefold().startswith("var("):
				raise ValueError("material source cannot contain generated paint variables")
			_set_paint(owner, channel, f"var(--{paint_handle}, {fallback})")
			rewritten.add(key)


def _strip_authored_semantics(root: lxml.etree._Element) -> None:
	for element in root.iter():
		if isinstance(element.tag, str):
			for attribute in list(element.attrib):
				if attribute.startswith("data-vlab-"):
					del element.attrib[attribute]


def _remove_bounds_anchor(root: lxml.etree._Element) -> None:
	bounds = next(element for element in root.iter() if element.get("id") == "anchor_liquid_bounds")
	bounds.getparent().remove(bounds)


def _assert_generated_id_space(root: lxml.etree._Element, handles: list[str]) -> None:
	"""Reserve generated element IDs against every existing SVG ID before mutation."""
	existing = {element.get("id") for element in root.iter() if isinstance(element.tag, str) and element.get("id") is not None}
	if len(handles) != len(set(handles)) or any(handle in existing for handle in handles):
		raise ValueError("opaque liquid-region handle collision with SVG id")


def _compile_normalized_root(root: lxml.etree._Element, output_path: Path, asset_name: str) -> dict:
	"""Compile a verified normalized tree to one derived SVG artifact."""
	validate_material_svg(root)
	bounds = _bounds(root)
	max_fill_percent = _max_fill_percent(root)
	min_fill_percent = _min_fill_percent(root)
	body_start_fill_percent = _body_start_fill_percent(root)
	fill_height_exponent = _fill_height_exponent(root)
	geometry = measure_material_geometry(root)
	if body_start_fill_percent is not None:
		body_anchor_y = geometry.body_anchor_y
		if body_anchor_y is None or geometry.surface_reference_y is None:
			raise ValueError("body-start fill calibration requires body and surface geometry")
		bounds_bottom = bounds["y"] + bounds["height"]
		if not bounds["y"] < body_anchor_y < bounds_bottom:
			raise ValueError("body-start fill calibration requires body anchor inside liquid bounds")
	layers = _material_layers(root)
	region_handle = _opaque_handle(asset_name, "region", 0)
	reveal_clip_handle = _opaque_handle(asset_name, "reveal_clip", 0)
	reveal_handle = _opaque_handle(asset_name, "reveal", 0)
	element_handles = [_opaque_handle(asset_name, "element", ordinal) for ordinal in range(len(layers))]
	paint_handles = [_opaque_handle(asset_name, "paint", ordinal) for ordinal in range(len(layers))]
	_assert_generated_id_space(root, [
		region_handle, reveal_clip_handle, reveal_handle, *element_handles, *paint_handles,
	])
	defs = next((child for child in root if isinstance(child.tag, str) and _local_name(child) == "defs"), None)
	if defs is None:
		defs = lxml.etree.Element(_tag("defs"))
		root.insert(0, defs)
	reveal_clip = lxml.etree.SubElement(defs, _tag("clipPath"), id=reveal_clip_handle)
	reveal_rect = lxml.etree.SubElement(reveal_clip, _tag("rect"), id=reveal_handle)
	for key in ("x", "y", "width", "height"):
		reveal_rect.set(key, f"{bounds[key]:.12g}")
	region_group = lxml.etree.Element(_tag("g"), id=region_handle)
	region_group.set("clip-path", "url(#anchor_liquid_clip)")
	first_index = root.index(layers[0])
	for layer in layers:
		root.remove(layer)
		if layer.get("data-vlab-liquid-part") in {"bottom", "body"}:
			stationary_reveal = lxml.etree.SubElement(region_group, _tag("g"))
			stationary_reveal.set("clip-path", f"url(#{reveal_clip_handle})")
			stationary_reveal.append(layer)
		else:
			region_group.append(layer)
	root.insert(first_index, region_group)

	paint_entries: list[dict] = []
	for ordinal, layer in enumerate(layers):
		element_handle = element_handles[ordinal]
		paint_handle = paint_handles[ordinal]
		layer.set("id", element_handle)
		_rewrite_paint(layer, paint_handle)
		adjustment = layer.get("data-vlab-adjustment")
		paint_entries.append({
			"element_handle": element_handle,
			"paint_handle": paint_handle,
			"paint_role": layer.get("data-vlab-paint-role"),
			"liquid_part": layer.get("data-vlab-liquid-part"),
			"adjustment": float(adjustment) if adjustment is not None else None,
		})
	_remove_bounds_anchor(root)
	_strip_authored_semantics(root)
	output_path.parent.mkdir(parents=True, exist_ok=True)
	output_path.write_bytes(lxml.etree.tostring(root, encoding="utf-8", xml_declaration=False) + b"\n")
	return {
		"region_handle": region_handle,
		"reveal_handle": reveal_handle,
		"paints": paint_entries,
		"bounds": bounds,
		"surface_reference_y": geometry.surface_reference_y,
		"body_join_y": geometry.body_join_y,
		"body_anchor_y": geometry.body_anchor_y,
		"max_fill_percent": max_fill_percent,
		"min_fill_percent": min_fill_percent,
		"body_start_fill_percent": body_start_fill_percent,
		"fill_height_exponent": fill_height_exponent,
	}


def compile_material_svg(source_path: Path, output_path: Path, asset_name: str) -> dict:
	"""Normalize, post-validate, then compile one source form without partial output."""
	with tempfile.TemporaryDirectory(prefix="liquid_svg_") as temp_dir:
		normalized = Path(temp_dir) / "normalized.svg"
		result = tools.svg_normalizer.workflow.normalize_svg_file(source_path, normalized, padding=2.0)
		if not result.normalized:
			raise ValueError(f"material normalization failed: {result.rejection.code}: {result.rejection.message}")
		root = lxml.etree.parse(str(normalized), lxml.etree.XMLParser(resolve_entities=False, no_network=True)).getroot()
		validate_material_svg(root)
		staged_output = Path(temp_dir) / "compiled.svg"
		entry = _compile_normalized_root(root, staged_output, asset_name)
		output_path.parent.mkdir(parents=True, exist_ok=True)
		shutil.copyfile(staged_output, output_path)
		return entry


def emit_liquid_regions(entries: dict[str, dict], output_path: Path) -> None:
	"""Write exactly one sorted aggregate manifest, rejecting handle collisions."""
	handles: set[str] = set()
	for entry in entries.values():
		for handle in [entry["region_handle"], entry["reveal_handle"], *(
			handle for paint in entry["paints"]
			for handle in (paint["element_handle"], paint["paint_handle"])
		)]:
			if handle in handles:
				raise ValueError("opaque liquid-region handle collision")
			handles.add(handle)
	output_path.parent.mkdir(parents=True, exist_ok=True)
	ordered = {key: entries[key] for key in sorted(entries)}
	output_path.write_text(json.dumps(ordered, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _assert_tree_reserved_contract(assets_dir: Path, objects_dir: Path) -> list[Path]:
	"""Validate reserved attributes on every SVG before any tree compilation."""
	taxonomy = validate_asset_taxonomy(assets_dir, objects_dir)
	material_paths: list[Path] = []
	parser = lxml.etree.XMLParser(resolve_entities=False, no_network=True)
	for _asset_name, source_path in taxonomy.registry:
		root = lxml.etree.parse(str(source_path), parser).getroot()
		if validate_reserved_attributes(root):
			validate_material_svg(root)
			material_paths.append(source_path)
	return material_paths


def compile_material_tree(
	assets_dir: Path, generated_dir: Path, objects_dir: Path | None = None,
) -> dict[str, dict]:
	"""Compile every declared material form using a staging tree before publication."""
	if objects_dir is None:
		objects_dir = assets_dir.parent / "content" / "objects"
	material_paths = _assert_tree_reserved_contract(assets_dir, objects_dir)
	entries: dict[str, dict] = {}
	with tempfile.TemporaryDirectory(prefix="liquid_regions_", dir=generated_dir.parent) as temp_dir:
		stage_root = Path(temp_dir)
		for source_path in material_paths:
			asset_name = source_path.stem
			if asset_name in entries:
				raise ValueError(f"duplicate logical material asset name: {asset_name}")
			relative = source_path.relative_to(assets_dir)
			entries[asset_name] = compile_material_svg(
				source_path, stage_root / "material_svg" / relative, asset_name,
			)
		emit_liquid_regions(entries, stage_root / "liquid_regions.json")
		generated_dir.mkdir(parents=True, exist_ok=True)
		_publish_complete_tree(stage_root, generated_dir)
	return entries


def _publish_complete_tree(stage_root: Path, generated_dir: Path) -> None:
	"""Replace only material outputs after the complete staged tree is valid."""
	staged_material = stage_root / "material_svg"
	if not staged_material.exists():
		staged_material.mkdir()
	target_material = generated_dir / "material_svg"
	target_manifest = generated_dir / "liquid_regions.json"
	previous_material = stage_root / "previous_material_svg"
	previous_manifest = stage_root / "previous_liquid_regions.json"
	material_backed_up = False
	manifest_backed_up = False
	material_published = False
	manifest_published = False
	try:
		if target_material.exists():
			os.replace(target_material, previous_material)
			material_backed_up = True
		if target_manifest.exists():
			os.replace(target_manifest, previous_manifest)
			manifest_backed_up = True
		os.replace(staged_material, target_material)
		material_published = True
		os.replace(stage_root / "liquid_regions.json", target_manifest)
		manifest_published = True
	except OSError:
		# Remove only outputs known to have been published by this attempt.  A
		# backup-phase failure leaves untouched originals at their target paths.
		if material_published and target_material.exists():
			shutil.rmtree(target_material)
		if manifest_published and target_manifest.exists():
			target_manifest.unlink()
		if material_backed_up and previous_material.exists():
			os.replace(previous_material, target_material)
		if manifest_backed_up and previous_manifest.exists():
			os.replace(previous_manifest, target_manifest)
		raise


def main() -> None:
	repo_root = Path(__file__).resolve().parents[1]
	compile_material_tree(repo_root / "assets", repo_root / "generated", repo_root / "content" / "objects")


if __name__ == "__main__":
	main()
