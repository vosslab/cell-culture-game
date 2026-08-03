"""Validate the SVG asset taxonomy at its SVG and object-YAML boundary.

Selection is declared only by ``kind: svg`` object visual-state case maps.
This module deliberately does not infer a collection, state, or rendering mode
from a filename or a directory.  The SVG registry remains recursive but uses
the existing logical ``asset_name`` convention of a unique filename stem.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import lxml.etree
import yaml

from validation.svg.asset_registry import SvgAssetRegistryError, build_svg_asset_registry

_STATE_ONLY_STEMS = frozenset({"open", "closed", "on", "off"})
_BEHAVIOR_CATEGORIES = frozenset({
	"static",
	"binary_state",
	"multi_state",
	"variable_volume",
})


class AssetTaxonomyValidationError(ValueError):
	"""Raised when SVG registry or object-selected asset membership is invalid."""


@dataclass(frozen=True)
class SvgSelection:
	"""One object visual-state map and its YAML-declared selected SVG forms."""

	object_path: Path
	state_name: str
	asset_names: tuple[str, ...]
	variable_volume_context: bool = False


@dataclass(frozen=True)
class AssetTaxonomyResult:
	"""Validated recursive registry and authoritative object-YAML selections."""

	registry: tuple[tuple[str, Path], ...]
	selections: tuple[SvgSelection, ...]
	categories: tuple[tuple[str, str], ...]

	def asset_path(self, asset_name: str) -> Path:
		"""Return a uniquely registered SVG path by logical asset name."""
		for registered_name, registered_path in self.registry:
			if registered_name == asset_name:
				return registered_path
		raise KeyError(asset_name)

	def behavior_category(self, asset_name: str) -> str:
		"""Return the derived source-organization category for one logical asset."""
		for registered_name, category in self.categories:
			if registered_name == asset_name:
				return category
		raise KeyError(asset_name)


def _is_material_svg(svg_path: Path) -> bool:
	"""Read only the root rendering declaration needed for placement."""
	parser = lxml.etree.XMLParser(resolve_entities=False, no_network=True)
	try:
		root = lxml.etree.parse(str(svg_path), parser).getroot()
	except lxml.etree.XMLSyntaxError as exc:
		raise AssetTaxonomyValidationError(f"cannot classify malformed SVG: {svg_path}: {exc}") from exc
	return root.get("data-vlab-rendering") == "material"


def _derive_behavior_categories(
	registry: tuple[tuple[str, Path], ...], selections: list[SvgSelection],
) -> dict[str, str]:
	"""Project authoritative SVG/YAML behavior into source directories."""
	selection_sizes: dict[str, int] = {}
	for selection in selections:
		unique_names = set(selection.asset_names)
		for asset_name in unique_names:
			selection_sizes[asset_name] = max(selection_sizes.get(asset_name, 0), len(unique_names))
	categories: dict[str, str] = {}
	for asset_name, svg_path in registry:
		if _is_material_svg(svg_path):
			categories[asset_name] = "variable_volume"
			continue
		selection_size = selection_sizes.get(asset_name, 0)
		if selection_size <= 1:
			categories[asset_name] = "static"
		elif selection_size == 2:
			categories[asset_name] = "binary_state"
		else:
			categories[asset_name] = "multi_state"
	return categories


def _validate_behavior_placement(
	assets_dir: Path, registry: tuple[tuple[str, Path], ...], categories: dict[str, str],
) -> None:
	"""Reject equipment files outside their derived behavior directory."""
	for asset_name, svg_path in registry:
		relative = svg_path.relative_to(assets_dir.resolve())
		if not relative.parts or relative.parts[0] != "equipment":
			continue
		if len(relative.parts) != 3 or relative.parts[1] not in _BEHAVIOR_CATEGORIES:
			raise AssetTaxonomyValidationError(
				f"equipment SVG must live in a behavior directory: {svg_path}"
			)
		expected = categories[asset_name]
		if relative.parts[1] != expected:
			raise AssetTaxonomyValidationError(
				f"misplaced SVG '{asset_name}': expected equipment/{expected}, "
				f"found equipment/{relative.parts[1]}"
			)


def _svg_selection(
	yaml_path: Path, state_name: str, state: object, *, variable_volume_context: bool,
) -> SvgSelection:
	"""Read one bounded ``kind: svg`` declaration without schema duplication."""
	if not isinstance(state, dict):
		raise AssetTaxonomyValidationError(
			f"svg visual state must be a mapping: {yaml_path}:{state_name}"
		)
	cases = state.get("cases")
	if not isinstance(cases, list):
		raise AssetTaxonomyValidationError(
			f"svg visual state cases must be a list: {yaml_path}:{state_name}"
		)
	asset_names: list[str] = []
	for case_index, case in enumerate(cases):
		if not isinstance(case, dict):
			raise AssetTaxonomyValidationError(
				f"svg visual state case must be a mapping: {yaml_path}:{state_name}:{case_index}"
			)
		output = case.get("output")
		if not isinstance(output, dict):
			raise AssetTaxonomyValidationError(
				f"svg visual state output must be a mapping: {yaml_path}:{state_name}:{case_index}"
			)
		asset_name = output.get("asset_name")
		if not isinstance(asset_name, str) or not asset_name:
			raise AssetTaxonomyValidationError(
				f"svg visual state asset_name must be a nonempty string: {yaml_path}:{state_name}:{case_index}"
			)
		asset_names.append(asset_name)
	return SvgSelection(yaml_path, state_name, tuple(asset_names), variable_volume_context)


def _object_svg_selections(objects_dir: Path) -> list[SvgSelection]:
	"""Return only object YAML's authoritative complete-form svg selections."""
	if not objects_dir.exists():
		return []
	selections: list[SvgSelection] = []
	for yaml_path in sorted(objects_dir.rglob("*.yaml")):
		with yaml_path.open(encoding="utf-8") as source:
			object_data = yaml.safe_load(source)
		if not isinstance(object_data, dict):
			raise AssetTaxonomyValidationError(f"object YAML must be a mapping: {yaml_path}")
		visual_states = object_data.get("visual_states")
		if visual_states is None:
			continue
		if not isinstance(visual_states, dict):
			raise AssetTaxonomyValidationError(f"visual_states must be a mapping: {yaml_path}")
		variable_volume_context = any(
			isinstance(candidate_state, dict)
			and candidate_state.get("render_effect") == "fill_height"
			and candidate_state.get("applies_to") == "object"
			and candidate_state.get("target") == "anchor_liquid_bounds"
			for candidate_state in visual_states.values()
		)
		for state_name, state in visual_states.items():
			if not isinstance(state_name, str):
				raise AssetTaxonomyValidationError(f"visual-state name must be a string: {yaml_path}")
			if not isinstance(state, dict):
				raise AssetTaxonomyValidationError(
					f"visual state must be a mapping: {yaml_path}:{state_name}"
				)
			if state.get("kind") == "svg":
				selections.append(_svg_selection(
					yaml_path,
					state_name,
					state,
					variable_volume_context=variable_volume_context,
				))
	return selections


def derive_requested_asset_behavior_categories(objects_dir: Path) -> dict[str, str]:
	"""Project object intent for assets that may not have source files yet.

	This is the picker-side projection. Existing SVG placement remains governed
	by the SVG root rendering declaration plus YAML selection cardinality.
	"""
	categories: dict[str, str] = {}
	for selection in _object_svg_selections(objects_dir):
		unique_names = set(selection.asset_names)
		if selection.variable_volume_context:
			category = "variable_volume"
		elif len(unique_names) <= 1:
			category = "static"
		elif len(unique_names) == 2:
			category = "binary_state"
		else:
			category = "multi_state"
		for asset_name in unique_names:
			previous = categories.get(asset_name)
			if previous == "variable_volume" or category == previous:
				continue
			if category == "variable_volume":
				categories[asset_name] = category
				continue
			if previous is None:
				categories[asset_name] = category
				continue
			previous_size = {"static": 1, "binary_state": 2, "multi_state": 3}[previous]
			category_size = {"static": 1, "binary_state": 2, "multi_state": 3}[category]
			if category_size > previous_size:
				categories[asset_name] = category
	return categories


def derive_asset_behavior_categories(assets_dir: Path, objects_dir: Path) -> dict[str, str]:
	"""Return the behavior projection without requiring sources to be moved yet."""
	try:
		svg_registry = build_svg_asset_registry(assets_dir)
	except SvgAssetRegistryError as exc:
		raise AssetTaxonomyValidationError(str(exc)) from exc
	registry = tuple((entry.asset_name, entry.source_path) for entry in svg_registry.entries)
	return _derive_behavior_categories(registry, _object_svg_selections(objects_dir))


def validate_asset_taxonomy(assets_dir: Path, objects_dir: Path) -> AssetTaxonomyResult:
	"""Validate registry uniqueness and object-YAML selected SVG membership.

	The result deliberately exposes selections rather than a synthetic collection
	manifest.  A caller can inspect the exact object state map that selected each
	form, including a mixed static/material collection, without filename logic.
	"""
	try:
		svg_registry = build_svg_asset_registry(assets_dir)
	except SvgAssetRegistryError as exc:
		raise AssetTaxonomyValidationError(str(exc)) from exc
	registry = tuple((entry.asset_name, entry.source_path) for entry in svg_registry.entries)
	for asset_name, svg_path in registry:
		if asset_name in _STATE_ONLY_STEMS:
			raise AssetTaxonomyValidationError(
				f"bare state-only SVG filename is invalid: {svg_path}"
			)
	selections = _object_svg_selections(objects_dir)
	for selection in selections:
		for asset_name in selection.asset_names:
			if asset_name not in svg_registry.asset_names:
				raise AssetTaxonomyValidationError(
					f"object SVG selection references missing asset '{asset_name}': "
					f"{selection.object_path}:{selection.state_name}"
				)
	categories = _derive_behavior_categories(registry, selections)
	for selection in selections:
		if not selection.variable_volume_context:
			continue
		for asset_name in selection.asset_names:
			if categories[asset_name] != "variable_volume":
				raise AssetTaxonomyValidationError(
					f"object-level fill_height must select a material-rendered SVG: "
					f"{selection.object_path}:{selection.state_name} -> '{asset_name}'"
				)
	_validate_behavior_placement(assets_dir, registry, categories)
	result = AssetTaxonomyResult(
		registry=registry,
		selections=tuple(selections),
		categories=tuple(sorted(categories.items())),
	)
	return result
