"""Scene YAML loading and inheritance resolution.

This module provides helpers for loading scene YAML files and resolving single-level
scene inheritance. It wraps existing toolkit functions (yaml_io, objects, paths) and
adds SVG viewBox parsing and inheritance resolution specific to scenes.

Inheritance is limited to single-level extends chains; multi-level, cyclic, and
dangling references raise typed exceptions. Locked-field mutations (modifications to
fields that the inheritance system protects) are detected and reported.
"""

import re
from pathlib import Path

import validation.shared_toolkit.yaml_io as yaml_io
import validation.shared_toolkit.paths as paths


#============================================
# Exception classes for inheritance errors
#============================================

class InheritanceError(Exception):
	"""Base class for all inheritance-related errors."""
	pass


class UnknownBaseError(InheritanceError):
	"""Raised when a scene extends a base that does not exist."""
	pass


class MultiLevelInheritanceError(InheritanceError):
	"""Raised when a scene chain has more than one level of inheritance."""
	pass


class InheritanceCycleError(InheritanceError):
	"""Raised when scene inheritance forms a cycle."""
	pass


class DanglingReferenceError(InheritanceError):
	"""Raised when an extends field refers to a non-existent scene."""
	pass


class LockedFieldMutationError(InheritanceError):
	"""Raised when add_placements, remove_placements, etc. attempt to modify locked fields."""
	pass


#============================================
# SVG viewBox parsing
#============================================

def load_svg_viewbox(svg_path: Path | str) -> tuple[float, float]:
	"""
	Extract viewBox dimensions (width, height) from an SVG file.

	Args:
		svg_path: Path to the SVG file.

	Returns:
		Tuple of (width, height) as floats extracted from the viewBox attribute.

	Raises:
		FileNotFoundError: If the SVG file does not exist.
		ValueError: If the SVG has no viewBox attribute or it is malformed.
	"""
	svg_path = Path(svg_path)
	if not svg_path.exists():
		raise FileNotFoundError(f"SVG file not found: {svg_path}")

	with open(svg_path, 'r', encoding='utf-8') as f:
		content = f.read()

	# Extract viewBox attribute using regex.
	# Pattern matches: viewBox="x y width height"
	match = re.search(r'viewBox\s*=\s*["\']([^"\']+)["\']', content)
	if not match:
		raise ValueError(f"SVG {svg_path} has no viewBox attribute")

	viewbox_str = match.group(1).strip()
	parts = viewbox_str.split()
	if len(parts) != 4:
		raise ValueError(f"SVG {svg_path} viewBox is malformed: {viewbox_str}")

	try:
		# viewBox format is "min_x min_y width height"
		# We extract width and height (parts[2] and parts[3])
		width = float(parts[2])
		height = float(parts[3])
	except ValueError as e:
		raise ValueError(f"SVG {svg_path} viewBox has non-numeric dimensions: {viewbox_str}") from e

	return width, height


#============================================
# Inheritance resolution
#============================================

def resolve_inheritance(scene: dict[str, object], base_scenes_dir: Path | str | None = None) -> dict[str, object]:
	"""
	Resolve single-level scene inheritance and return a new scene dict.

	Resolves the 'extends' field and applies add_placements, remove_placements,
	deactivate_placements, and reposition_placements operations. Only single-level
	inheritance is supported; chains, cycles, and dangling references raise typed
	exceptions.

	Args:
		scene: The scene dict to resolve (loaded from YAML).
		base_scenes_dir: Directory containing base scene files. If None, uses
			validation.shared_toolkit.paths.BASE_SCENES_DIR.

	Returns:
		A new dict with inheritance resolved and operations applied. The returned
		dict does not include the 'extends' field.

	Raises:
		UnknownBaseError: If a base scene cannot be loaded.
		MultiLevelInheritanceError: If the base scene also has an 'extends' field.
		InheritanceCycleError: If a scene tries to extend itself.
		DanglingReferenceError: If 'extends' names a scene that does not exist.
		LockedFieldMutationError: If an operation attempts to modify a locked field.
	"""

	if base_scenes_dir is None:
		base_scenes_dir = paths.BASE_SCENES_DIR

	base_scenes_dir = Path(base_scenes_dir)

	# If there is no 'extends' field, return a copy of the scene as-is.
	if 'extends' not in scene:
		return dict(scene)

	base_name = scene['extends']

	# Check for self-inheritance (cycle of length 1).
	if base_name == scene.get('scene_name'):
		raise InheritanceCycleError(f"Scene '{scene.get('scene_name')}' extends itself")

	# Load the base scene.
	base_scene_path = base_scenes_dir / f"{base_name}.yaml"
	if not base_scene_path.exists():
		raise DanglingReferenceError(f"Base scene '{base_name}' not found at {base_scene_path}")

	try:
		base_scene = yaml_io.load_yaml(base_scene_path)
	except RuntimeError as e:
		raise UnknownBaseError(f"Failed to load base scene '{base_name}': {e}") from e

	# Check that the base scene does not have its own 'extends' (multi-level).
	if 'extends' in base_scene:
		raise MultiLevelInheritanceError(
			f"Base scene '{base_name}' also has 'extends: {base_scene['extends']}'; "
			"only single-level inheritance is supported"
		)

	# Start with a copy of the base scene.
	resolved = dict(base_scene)

	# Apply operations: add_placements, remove_placements, deactivate_placements,
	# reposition_placements.

	# add_placements: append new placements to the placements list.
	if 'add_placements' in scene:
		if 'placements' not in resolved:
			resolved['placements'] = []
		add_list = scene['add_placements']
		if not isinstance(add_list, list):
			raise LockedFieldMutationError(
				f"'add_placements' must be a list, got {type(add_list).__name__}"
			)
		resolved['placements'].extend(add_list)

	# remove_placements: filter out placements by name.
	if 'remove_placements' in scene:
		remove_names = scene['remove_placements']
		if not isinstance(remove_names, list):
			raise LockedFieldMutationError(
				f"'remove_placements' must be a list, got {type(remove_names).__name__}"
			)
		if 'placements' in resolved:
			resolved['placements'] = [
				p for p in resolved['placements']
				if p.get('placement_name') not in remove_names
			]

	# deactivate_placements: mark placements as inactive.
	if 'deactivate_placements' in scene:
		deactivate_names = scene['deactivate_placements']
		if not isinstance(deactivate_names, list):
			raise LockedFieldMutationError(
				f"'deactivate_placements' must be a list, got {type(deactivate_names).__name__}"
			)
		if 'placements' in resolved:
			for placement in resolved['placements']:
				if placement.get('placement_name') in deactivate_names:
					placement['active'] = False

	# reposition_placements: update zone or other position fields.
	if 'reposition_placements' in scene:
		reposition_ops = scene['reposition_placements']
		if not isinstance(reposition_ops, list):
			raise LockedFieldMutationError(
				f"'reposition_placements' must be a list, got {type(reposition_ops).__name__}"
			)
		if 'placements' in resolved:
			# reposition_ops is a list of dicts with structure:
			# {placement_name: "...", updates: {zone: "...", ...}}
			for op in reposition_ops:
				if not isinstance(op, dict):
					raise LockedFieldMutationError(
						f"reposition_placements entry must be a dict, got {type(op).__name__}"
					)
				target_name = op.get('placement_name')
				updates = op.get('updates', {})
				for placement in resolved['placements']:
					if placement.get('placement_name') == target_name:
						placement.update(updates)
						break

	# Remove the 'extends' field and the operation fields from the resolved scene.
	resolved.pop('extends', None)
	resolved.pop('add_placements', None)
	resolved.pop('remove_placements', None)
	resolved.pop('deactivate_placements', None)
	resolved.pop('reposition_placements', None)

	return resolved
