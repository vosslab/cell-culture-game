"""BaseSceneValidator: validates base scene YAML per SCENE_YAML_FORMAT.md."""

import math

from validation.yaml_schema.constants import (
	BASE_SCENE_REQUIRED_KEYS,
	BASE_SCENE_ALL_KEYS,
	LABEL_PLACEMENT_VALUES,
	ALIGN_STOP_VALUES,
)
from validation.yaml_schema.findings import Finding, Severity
import pipeline.scene_inheritance as scene_inheritance


# spec: docs/specs/SCENE_YAML_FORMAT.md "Layout rules"
# Scene layout hints are a closed authoring vocabulary.  They tune the manager;
# they never introduce per-scene coordinate or geometry controls.
LAYOUT_RULE_ALLOWED_KEYS = {
	'default_align_stop', 'label_font_size', 'label_line_height',
	'label_offset_y', 'label_placement', 'zone_gap',
}
LAYOUT_RULE_NUMERIC_KEYS = {
	'label_font_size', 'label_line_height', 'label_offset_y', 'zone_gap',
}
LAYOUT_RULE_POSITIVE_NUMERIC_KEYS = {'label_font_size', 'label_line_height'}


class BaseSceneValidator:
	"""Validates base scene YAML files per SCENE_YAML_FORMAT.md."""

	def __init__(self):
		"""Initialize validator."""
		self.all_objects: set = set()

	def set_object_names(self, names: set) -> None:
		"""Set known object names for cross-reference validation."""
		self.all_objects = names

	def validate(self, scene: dict, path: str) -> list:
		"""Validate a base scene definition."""
		findings = []

		if 'extends' in scene:
			findings.append(Finding(
				path=path,
				lineno=None,
				severity=Severity.ERROR,
				message="base scenes must not have 'extends' field",
			))

		for key in BASE_SCENE_REQUIRED_KEYS:
			if key not in scene:
				findings.append(Finding(
					path=path,
					lineno=None,
					severity=Severity.ERROR,
					message=f"missing required key '{key}'",
				))

		# Closure: unknown top-level keys are flagged (subsumes retired-key check).
		for key in scene:
			if key not in BASE_SCENE_ALL_KEYS:
				if key in scene_inheritance.SOURCE_FORBIDDEN_GEOMETRY_KEYS:
					findings.append(self._geometry_finding(path, key))
					continue
				findings.append(Finding(
					path=path,
					lineno=None,
					severity=Severity.ERROR,
					message=f"[CLOSURE] unknown top-level key '{key}' (allowed: {sorted(BASE_SCENE_ALL_KEYS)})",
				))

		findings.extend(self._validate_layout_rules(scene, path))

		if not findings:
			findings.extend(self._validate_source_geometry(scene, path))
			zone_findings, zone_ids = self._validate_zones(scene, path)
			findings.extend(zone_findings)
			findings.extend(self._validate_placements(scene, path, zone_ids))

		return findings

	def _validate_layout_rules(self, scene: dict, path: str) -> list:
		"""Validate the complete closed scene-wide layout-rules vocabulary."""
		findings = []
		if 'layout_rules' not in scene:
			return findings

		layout_rules = scene['layout_rules']
		if not isinstance(layout_rules, dict):
			findings.append(Finding(
				path=path,
				lineno=None,
				severity=Severity.ERROR,
				message='layout_rules must be a mapping',
			))
			return findings

		for key, value in layout_rules.items():
			if key not in LAYOUT_RULE_ALLOWED_KEYS:
				if key in scene_inheritance.SOURCE_FORBIDDEN_GEOMETRY_KEYS:
					findings.append(self._geometry_finding(path, f'layout_rules.{key}'))
				else:
					findings.append(self._unknown_key_finding(path, f'layout_rules.{key}'))
				continue

			if key == 'default_align_stop' and value not in ALIGN_STOP_VALUES:
				findings.append(Finding(
					path=path,
					lineno=None,
					severity=Severity.ERROR,
					message=(
						f"layout_rules.default_align_stop '{value}' is not valid "
						f"(allowed: {sorted(ALIGN_STOP_VALUES)})"
					),
				))
			elif key == 'label_placement' and value not in LABEL_PLACEMENT_VALUES:
				findings.append(Finding(
					path=path,
					lineno=None,
					severity=Severity.ERROR,
					message=(
						f"layout_rules.label_placement '{value}' is not valid "
						f"(allowed: {sorted(LABEL_PLACEMENT_VALUES)})"
					),
				))
			elif key in LAYOUT_RULE_NUMERIC_KEYS:
				findings.extend(self._validate_layout_rule_number(path, key, value))

		return findings

	def _validate_layout_rule_number(self, path: str, key: str, value: object) -> list:
		"""Validate one documented numeric scene-wide layout hint."""
		findings = []
		is_number = isinstance(value, (int, float)) and not isinstance(value, bool)
		if not is_number or not math.isfinite(value):
			findings.append(Finding(
				path=path,
				lineno=None,
				severity=Severity.ERROR,
				message=f'layout_rules.{key} must be a finite number',
			))
			return findings

		if key in LAYOUT_RULE_POSITIVE_NUMERIC_KEYS and value <= 0:
			findings.append(Finding(
				path=path,
				lineno=None,
				severity=Severity.ERROR,
				message=f'layout_rules.{key} must be positive',
			))
		return findings

	def _validate_source_geometry(self, scene: dict, path: str) -> list:
		"""Reject source geometry so only the layout manager allocates coordinates."""
		findings = []
		for key in scene:
			if key in scene_inheritance.SOURCE_FORBIDDEN_GEOMETRY_KEYS:
				findings.append(self._geometry_finding(path, key))

		background = scene.get('background')
		if isinstance(background, dict):
			for key in background:
				if key in scene_inheritance.SOURCE_FORBIDDEN_GEOMETRY_KEYS:
					findings.append(self._geometry_finding(path, f"background.{key}"))

		for idx, zone in enumerate(scene.get('zones', [])):
			if not isinstance(zone, dict):
				continue
			zone_path = f"{path}.zones[{idx}]"
			for key in zone:
				if key in scene_inheritance.SOURCE_FORBIDDEN_GEOMETRY_KEYS:
					findings.append(self._geometry_finding(zone_path, key))
				elif key not in scene_inheritance.SOURCE_ZONE_ALLOWED_KEYS:
					findings.append(self._unknown_key_finding(zone_path, key))

		for idx, placement in enumerate(scene.get('placements', [])):
			if not isinstance(placement, dict):
				continue
			placement_path = f"{path}.placements[{idx}]"
			align_stop = placement.get('align_stop')
			if align_stop is not None and align_stop not in ALIGN_STOP_VALUES:
				findings.append(Finding(
					path=placement_path,
					lineno=None,
					severity=Severity.ERROR,
					message=(
						f"placement.align_stop '{align_stop}' is not valid "
						f"(allowed: {sorted(ALIGN_STOP_VALUES)})"
					),
				))
			for key in placement:
				if key not in scene_inheritance.SOURCE_PLACEMENT_ALLOWED_KEYS:
					if key in scene_inheritance.SOURCE_FORBIDDEN_GEOMETRY_KEYS:
						findings.append(self._geometry_finding(placement_path, key))
					else:
						findings.append(self._unknown_key_finding(placement_path, key))
			layout = placement.get('layout')
			if isinstance(layout, dict):
				for key in layout:
					if key not in scene_inheritance.SOURCE_LAYOUT_ALLOWED_KEYS:
						if key in scene_inheritance.SOURCE_FORBIDDEN_GEOMETRY_KEYS:
							findings.append(self._geometry_finding(f"{placement_path}.layout", key))
						else:
							findings.append(self._unknown_key_finding(f"{placement_path}.layout", key))
		return findings

	def _geometry_finding(self, path: str, key: str) -> Finding:
		"""Create one path-aware source-geometry closure finding."""
		return Finding(
			path=path,
			lineno=None,
			severity=Severity.ERROR,
			message=(
				f"[CLOSURE] authored geometry '{key}' is forbidden; semantic zones "
				"are sized by the layout manager"
			),
		)

	def _unknown_key_finding(self, path: str, key: str) -> Finding:
		"""Create a closure finding that does not mislabel arbitrary keys."""
		return Finding(
			path=path,
			lineno=None,
			severity=Severity.ERROR,
			message=f"[CLOSURE] unknown source-scene key '{key}'",
		)

	def _validate_zones(self, scene: dict, path: str) -> tuple:
		"""Validate zones per SCENE_YAML_FORMAT.md."""
		findings = []
		zones = scene.get('zones', [])

		if not isinstance(zones, list):
			findings.append(Finding(
				path=path,
				lineno=None,
				severity=Severity.ERROR,
				message="zones must be a list",
			))
			return findings, set()

		zone_ids = set()
		for idx, zone in enumerate(zones):
			zone_path = f"{path}.zones[{idx}]"
			if not isinstance(zone, dict):
				findings.append(Finding(
					path=zone_path,
					lineno=None,
					severity=Severity.ERROR,
					message="zone entry must be a mapping",
				))
				continue

			if 'zone_name' not in zone:
				findings.append(Finding(
					path=zone_path,
					lineno=None,
					severity=Severity.ERROR,
					message="zone missing required 'zone_name'",
				))
			else:
				zone_name = zone['zone_name']
				if zone_name in zone_ids:
					findings.append(Finding(
						path=zone_path,
						lineno=None,
						severity=Severity.ERROR,
						message=f"duplicate zone_name '{zone_name}'",
					))
				else:
					zone_ids.add(zone_name)

		return findings, zone_ids

	def _validate_placements(self, scene: dict, path: str, zone_ids: set) -> list:
		"""Validate placements per SCENE_YAML_FORMAT.md."""
		findings = []
		placements = scene.get('placements', [])

		if not isinstance(placements, list):
			findings.append(Finding(
				path=path,
				lineno=None,
				severity=Severity.ERROR,
				message="placements must be a list",
			))
			return findings

		placement_names = set()
		for idx, placement in enumerate(placements):
			placement_path = f"{path}.placements[{idx}]"
			if not isinstance(placement, dict):
				findings.append(Finding(
					path=placement_path,
					lineno=None,
					severity=Severity.ERROR,
					message="placement entry must be a mapping",
				))
				continue

			if 'placement_name' not in placement:
				findings.append(Finding(
					path=placement_path,
					lineno=None,
					severity=Severity.ERROR,
					message="placement missing required 'placement_name'",
				))
			else:
				pname = placement['placement_name']
				if pname in placement_names:
					findings.append(Finding(
						path=placement_path,
						lineno=None,
						severity=Severity.ERROR,
						message=f"duplicate placement_name '{pname}'",
					))
				else:
					placement_names.add(pname)

			if 'object_name' not in placement:
				findings.append(Finding(
					path=placement_path,
					lineno=None,
					severity=Severity.ERROR,
					message="placement missing required 'object_name'",
				))
			elif self.all_objects and placement['object_name'] not in self.all_objects:
				findings.append(Finding(
					path=placement_path,
					lineno=None,
					severity=Severity.ERROR,
					message=f"object_name '{placement['object_name']}' not found",
				))

			if 'zone' not in placement:
				findings.append(Finding(
					path=placement_path,
					lineno=None,
					severity=Severity.ERROR,
					message="placement missing required 'zone'",
				))
			elif placement['zone'] not in zone_ids:
				findings.append(Finding(
					path=placement_path,
					lineno=None,
					severity=Severity.ERROR,
					message=f"placement zone '{placement['zone']}' not found",
				))

			# Validate placement.layout.label_placement if the block and field are present.
			# layout block is optional; absent block validates cleanly (default resolved by engine).
			placement_layout = placement.get('layout')
			if isinstance(placement_layout, dict) and 'label_placement' in placement_layout:
				lp_value = placement_layout['label_placement']
				if lp_value not in LABEL_PLACEMENT_VALUES:
					findings.append(Finding(
						path=placement_path,
						lineno=None,
						severity=Severity.ERROR,
						message=(
							f"placement.layout.label_placement '{lp_value}' is not valid "
							f"(allowed: {sorted(LABEL_PLACEMENT_VALUES)})"
						),
				))
		return findings
