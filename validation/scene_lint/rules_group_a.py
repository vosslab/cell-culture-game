"""Group A rules: deterministic data blockers (BLOCKED verdict).

Group A rules detect authoring errors that prevent a scene from entering
the layout pipeline. They require no simulator. Never suppressible.
All findings carry verdict == BLOCKED.

Coordinate with validation/yaml/ structural validators to avoid duplication.
See coverage_matrix.md for the delegation of responsibility.
"""

from pathlib import Path
from typing import Any

from validation.scene_lint.findings import Finding, Verdict, Confidence
from validation.shared_toolkit.scene_loaders import (
	load_svg_viewbox,
	resolve_inheritance,
	InheritanceError,
	MultiLevelInheritanceError,
	InheritanceCycleError,
	LockedFieldMutationError,
	DanglingReferenceError,
)


#============================================
# A1: duplicate_scene_name
#============================================

def check_duplicate_scene_name(
	scenes: dict[str, dict[str, Any]]
) -> list[Finding]:
	"""
	Detect two or more scene YAMLs declaring the same scene_name.

	Args:
		scenes: Dict mapping scene file path -> loaded scene dict.

	Returns:
		List of findings, one per duplicate (empty if all unique).
	"""
	findings = []
	name_to_paths = {}

	for scene_path, scene in scenes.items():
		scene_name = scene.get('scene_name')
		if not scene_name:
			continue

		if scene_name not in name_to_paths:
			name_to_paths[scene_name] = []
		name_to_paths[scene_name].append(scene_path)

	for scene_name, paths in name_to_paths.items():
		if len(paths) > 1:
			for path in paths:
				findings.append(Finding(
					scene=scene_name,
					placement_name=None,
					rule='duplicate_scene_name',
					verdict=Verdict.BLOCKED,
					confidence=Confidence.HIGH,
					message=f"Scene name '{scene_name}' declared in multiple files: {sorted(paths)}",
					evidence={
						'duplicate_paths': sorted(paths),
					},
					fix_hints=[
						'Rename one of the scenes to have a unique scene_name',
					],
				))

	return findings


#============================================
# A2: duplicate_placement_name (post-inheritance)
#============================================

def check_duplicate_placement_name(
	scene: dict[str, Any],
	scene_name: str,
) -> list[Finding]:
	"""
	Detect placement_name duplicates within a scene after inheritance resolution.

	Args:
		scene: Resolved scene dict (inheritance already applied).
		scene_name: Scene identifier for reporting.

	Returns:
		List of findings (empty if all placement names unique).
	"""
	findings = []
	placements = scene.get('placements', [])
	if not isinstance(placements, list):
		return findings

	seen_names = {}
	for idx, placement in enumerate(placements):
		if not isinstance(placement, dict):
			continue

		pname = placement.get('placement_name')
		if not pname:
			continue

		if pname in seen_names:
			findings.append(Finding(
				scene=scene_name,
				placement_name=pname,
				rule='duplicate_placement_name',
				verdict=Verdict.BLOCKED,
				confidence=Confidence.HIGH,
				message=f"Placement name '{pname}' appears multiple times in scene '{scene_name}'",
				evidence={
					'first_occurrence': seen_names[pname],
					'second_occurrence': idx,
				},
				fix_hints=[
					'Rename one of the placements to have a unique placement_name',
				],
			))
		else:
			seen_names[pname] = idx

	return findings


#============================================
# A3: forbidden_source_geometry
#============================================

def check_forbidden_source_geometry(
	scene: dict[str, Any],
	scene_name: str,
) -> list[Finding]:
	"""Block source geometry while allowing semantic zones without bounds."""
	from pipeline.scene_inheritance import (
		SOURCE_FORBIDDEN_GEOMETRY_KEYS,
		SOURCE_LAYOUT_ALLOWED_KEYS,
		SOURCE_PLACEMENT_ALLOWED_KEYS,
		SOURCE_ZONE_ALLOWED_KEYS,
	)

	findings = []
	def add_geometry(path: str) -> None:
		findings.append(Finding(
			scene=scene_name,
			placement_name=None,
			rule='forbidden_source_geometry',
			verdict=Verdict.BLOCKED,
			confidence=Confidence.HIGH,
			message=(f"Authored geometry '{path}' is forbidden; the layout manager "
				"computes scene and zone bounds"),
			evidence={'path': path},
			fix_hints=['Keep zones semantic and remove numeric layout overrides'],
		))

	def add_unknown(path: str) -> None:
		findings.append(Finding(
			scene=scene_name,
			placement_name=None,
			rule='forbidden_source_geometry',
			verdict=Verdict.BLOCKED,
			confidence=Confidence.HIGH,
			message=f"Unknown source-scene key '{path}'",
			evidence={'path': path},
			fix_hints=['Use the closed semantic scene vocabulary'],
		))

	for key in scene:
		if key in SOURCE_FORBIDDEN_GEOMETRY_KEYS:
			add_geometry(key)
	background = scene.get('background')
	if isinstance(background, dict):
		for key in background:
			if key in SOURCE_FORBIDDEN_GEOMETRY_KEYS:
				add_geometry(f'background.{key}')
	for index, zone in enumerate(scene.get('zones', [])):
		if isinstance(zone, dict):
			for key in zone:
				if key in SOURCE_FORBIDDEN_GEOMETRY_KEYS:
					add_geometry(f'zones[{index}].{key}')
				elif key not in SOURCE_ZONE_ALLOWED_KEYS:
					add_unknown(f'zones[{index}].{key}')
	for index, placement in enumerate(scene.get('placements', [])):
		if not isinstance(placement, dict):
			continue
		for key in placement:
			if key in SOURCE_FORBIDDEN_GEOMETRY_KEYS:
				add_geometry(f'placements[{index}].{key}')
			elif key not in SOURCE_PLACEMENT_ALLOWED_KEYS:
				add_unknown(f'placements[{index}].{key}')
		layout = placement.get('layout')
		if isinstance(layout, dict):
			for key in layout:
				if key in SOURCE_FORBIDDEN_GEOMETRY_KEYS:
					add_geometry(f'placements[{index}].layout.{key}')
				elif key not in SOURCE_LAYOUT_ALLOWED_KEYS:
					add_unknown(f'placements[{index}].layout.{key}')
	return findings


#============================================
# A6: missing_svg_asset
#============================================

def check_missing_svg_asset(
	scene: dict[str, Any],
	scene_name: str,
	asset_base_dir: Path | None = None,
) -> list[Finding]:
	"""
	Verify that each placement's asset file resolves to a real SVG on disk.

	Args:
		scene: Scene dict to validate.
		scene_name: Scene identifier for reporting.
		asset_base_dir: Base directory for asset paths. If None, uses default.

	Returns:
		List of findings (empty if all assets exist).
	"""
	findings = []
	placements = scene.get('placements', [])

	if asset_base_dir is None:
		asset_base_dir = Path(__file__).parent.parent.parent / 'assets'

	if not isinstance(placements, list):
		return findings

	for idx, placement in enumerate(placements):
		if not isinstance(placement, dict):
			continue

		pname = placement.get('placement_name', f"placement[{idx}]")
		asset_path = placement.get('asset')

		if not asset_path:
			continue

		full_path = asset_base_dir / asset_path
		if not full_path.exists():
			findings.append(Finding(
				scene=scene_name,
				placement_name=pname,
				rule='missing_svg_asset',
				verdict=Verdict.BLOCKED,
				confidence=Confidence.HIGH,
				message=f"Asset '{asset_path}' not found for placement '{pname}'",
				evidence={
					'asset_path': asset_path,
					'resolved_path': str(full_path),
				},
				fix_hints=[
					'Verify asset path is correct',
					f'Create the asset file at {full_path}',
				],
			))

	return findings


#============================================
# A7: invalid_svg_viewbox
#============================================

def check_invalid_svg_viewbox(
	scene: dict[str, Any],
	scene_name: str,
	asset_base_dir: Path | None = None,
) -> list[Finding]:
	"""
	Verify each asset SVG has a valid viewBox with positive dimensions.

	Args:
		scene: Scene dict to validate.
		scene_name: Scene identifier for reporting.
		asset_base_dir: Base directory for asset paths. If None, uses default.

	Returns:
		List of findings (empty if all viewBoxes valid).
	"""
	findings = []
	placements = scene.get('placements', [])

	if asset_base_dir is None:
		asset_base_dir = Path(__file__).parent.parent.parent / 'assets'

	if not isinstance(placements, list):
		return findings

	for idx, placement in enumerate(placements):
		if not isinstance(placement, dict):
			continue

		pname = placement.get('placement_name', f"placement[{idx}]")
		asset_path = placement.get('asset')

		if not asset_path:
			continue

		full_path = asset_base_dir / asset_path
		if not full_path.exists():
			continue

		try:
			width, height = load_svg_viewbox(full_path)
			if width <= 0 or height <= 0:
				findings.append(Finding(
					scene=scene_name,
					placement_name=pname,
					rule='invalid_svg_viewbox',
					verdict=Verdict.BLOCKED,
					confidence=Confidence.HIGH,
					message=f"Asset '{asset_path}' viewBox dimensions are non-positive: {width} x {height}",
					evidence={
						'asset_path': asset_path,
						'viewbox_width': width,
						'viewbox_height': height,
					},
					fix_hints=[
						f"Fix the viewBox attribute in {asset_path}",
						"Ensure both width and height are positive",
					],
				))
		except (ValueError, FileNotFoundError) as e:
			findings.append(Finding(
				scene=scene_name,
				placement_name=pname,
				rule='invalid_svg_viewbox',
				verdict=Verdict.BLOCKED,
				confidence=Confidence.HIGH,
				message=f"Asset '{asset_path}' viewBox is invalid or missing: {e}",
				evidence={
					'asset_path': asset_path,
					'error': str(e),
				},
				fix_hints=[
					f"Add or fix the viewBox attribute in {asset_path}",
					"Format: viewBox='x y width height' (all positive numbers)",
				],
			))

	return findings


#============================================
# A8-A11: Inheritance errors (exception wrappers)
#============================================

def check_inheritance_errors(
	scene: dict[str, Any],
	scene_name: str,
	scene_path: Path | str,
) -> list[Finding]:
	"""
	Attempt to resolve scene inheritance and wrap typed exceptions as findings.

	Covers:
	- A8: inheritance_unknown_base (DanglingReferenceError)
	- A9: inheritance_multi_level (MultiLevelInheritanceError)
	- A10: inheritance_cycle (InheritanceCycleError)
	- A11: inheritance_locked_field_mutation (LockedFieldMutationError)

	Args:
		scene: Scene dict loaded from YAML (may have 'extends' field).
		scene_name: Scene identifier for reporting.
		scene_path: Path to scene YAML file (for error location context).

	Returns:
		List of findings (empty if inheritance resolves cleanly).
	"""
	findings = []

	try:
		_ = resolve_inheritance(scene)
	except DanglingReferenceError as e:
		findings.append(Finding(
			scene=scene_name,
			placement_name=None,
			rule='inheritance_unknown_base',
			verdict=Verdict.BLOCKED,
			confidence=Confidence.HIGH,
			message=str(e),
			evidence={'scene_path': str(scene_path)},
			fix_hints=[
				"Verify the 'extends' field references an existing base scene",
				"Check for typos in the base scene name",
			],
		))
	except MultiLevelInheritanceError as e:
		findings.append(Finding(
			scene=scene_name,
			placement_name=None,
			rule='inheritance_multi_level',
			verdict=Verdict.BLOCKED,
			confidence=Confidence.HIGH,
			message=str(e),
			evidence={'scene_path': str(scene_path)},
			fix_hints=[
				"Inline the base scene's 'extends' into this scene",
				"Only single-level inheritance is supported",
			],
		))
	except InheritanceCycleError as e:
		findings.append(Finding(
			scene=scene_name,
			placement_name=None,
			rule='inheritance_cycle',
			verdict=Verdict.BLOCKED,
			confidence=Confidence.HIGH,
			message=str(e),
			evidence={'scene_path': str(scene_path)},
			fix_hints=[
				"Remove the circular extends reference",
				"A scene cannot extend itself or form a cycle",
			],
		))
	except LockedFieldMutationError as e:
		findings.append(Finding(
			scene=scene_name,
			placement_name=None,
			rule='inheritance_locked_field_mutation',
			verdict=Verdict.BLOCKED,
			confidence=Confidence.HIGH,
			message=str(e),
			evidence={'scene_path': str(scene_path)},
			fix_hints=[
				"Reposition operations can only modify: zone, data-primary",
				"For other fields, use add_placements / remove_placements",
			],
		))
	except InheritanceError as e:
		findings.append(Finding(
			scene=scene_name,
			placement_name=None,
			rule='inheritance_error',
			verdict=Verdict.BLOCKED,
			confidence=Confidence.HIGH,
			message=f"Inheritance resolution failed: {e}",
			evidence={'scene_path': str(scene_path)},
			fix_hints=[
				"Check the 'extends' chain and operation fields",
			],
		))

	return findings


#============================================
# A12: inheritance_dangling_ref
#============================================

def check_inheritance_dangling_ref(
	scene: dict[str, Any],
	scene_name: str,
) -> list[Finding]:
	"""
	Detect when deactivate_placements or reposition_placements targets
	a placement that was removed by remove_placements.

	Checks the order of operations within the inheritance mutation block.

	Args:
		scene: Original scene dict (before inheritance resolution).
		scene_name: Scene identifier for reporting.

	Returns:
		List of findings (empty if no dangling references).
	"""
	findings = []

	removed_names = set(scene.get('remove_placements', []))
	deactivated_names = set(scene.get('deactivate_placements', []))
	repositioned_ops = scene.get('reposition_placements', [])

	if not isinstance(repositioned_ops, list):
		repositioned_ops = []

	repositioned_names = {op.get('placement_name') for op in repositioned_ops if isinstance(op, dict)}

	for pname in deactivated_names:
		if pname in removed_names:
			findings.append(Finding(
				scene=scene_name,
				placement_name=pname,
				rule='inheritance_dangling_ref',
				verdict=Verdict.BLOCKED,
				confidence=Confidence.HIGH,
				message=f"Placement '{pname}' is targeted by 'deactivate_placements' but was removed by 'remove_placements'",
				evidence={
					'target_name': pname,
					'operation': 'deactivate_placements',
				},
				fix_hints=[
					f"Remove '{pname}' from deactivate_placements (it is already removed)",
				],
			))

	for pname in repositioned_names:
		if pname in removed_names:
			findings.append(Finding(
				scene=scene_name,
				placement_name=pname,
				rule='inheritance_dangling_ref',
				verdict=Verdict.BLOCKED,
				confidence=Confidence.HIGH,
				message=f"Placement '{pname}' is targeted by 'reposition_placements' but was removed by 'remove_placements'",
				evidence={
					'target_name': pname,
					'operation': 'reposition_placements',
				},
				fix_hints=[
					f"Remove '{pname}' from reposition_placements (it is already removed)",
				],
			))

	return findings
