"""ProtocolSceneValidator: validates protocol-scene (inherited) YAML per SCENE_INHERITANCE.md."""

from validation.yaml_schema.constants import (
	PROTOCOL_SCENE_ALLOWED_KEYS,
	PLACEMENT_LOCKED_FIELDS,
	REPOSITION_ALLOWED_FIELDS,
	ALIGN_STOP_VALUES,
)
from validation.yaml_schema.findings import Finding, Severity


class ProtocolSceneValidator:
	"""Validates protocol-scene (inherited) YAML files per SCENE_INHERITANCE.md."""

	def __init__(self):
		"""Initialize validator."""
		self.base_scenes: dict = {}

	def set_base_scenes(self, scenes: dict) -> None:
		"""Set known base scenes for inheritance validation."""
		self.base_scenes = scenes

	def validate(self, scene: dict, path: str) -> list:
		"""Validate a protocol-scene definition."""
		findings = []

		for key in scene:
			if key not in PROTOCOL_SCENE_ALLOWED_KEYS:
				findings.append(Finding(
					path=path,
					lineno=None,
					severity=Severity.ERROR,
					message=f"unknown top-level key '{key}' (protocol-scene keys are closed)",
				))

		if 'extends' not in scene:
			findings.append(Finding(
				path=path,
				lineno=None,
				severity=Severity.ERROR,
				message="protocol-scene missing required 'extends' field",
			))
		else:
			extends = scene['extends']
			# Scene self-extension: scene_name must not equal extends
			if 'scene_name' in scene:
				scene_name = scene['scene_name']
				if scene_name == extends:
					findings.append(Finding(
						path=path,
						lineno=None,
						severity=Severity.ERROR,
						message=f"scene '{scene_name}' extends itself (self-extension not allowed)",
						tag="scene_self_extends",
					))
			if extends not in self.base_scenes:
				findings.append(Finding(
					path=path,
					lineno=None,
					severity=Severity.ERROR,
					message=f"extends '{extends}' does not name a known base scene",
					tag="SCENE_EXTENDS",
				))

		if not findings and 'extends' in scene:
			findings.extend(self._validate_operations(scene, path))

		return findings

	def _validate_operations(self, scene: dict, path: str) -> list:
		"""Validate add/remove/reposition/deactivate operations."""
		findings = []

		base_name = scene['extends']
		base_scene = self.base_scenes.get(base_name, {})
		base_placements = base_scene.get('placements', [])
		base_placement_names = {p.get('placement_name') for p in base_placements if isinstance(p, dict)}

		new_placement_names = set(base_placement_names)

		# remove_placements and deactivate_placements are LISTS OF STRINGS
		# (bare placement_name values). The builder iterates these names
		# directly and filters by name; see pipeline/scene_inheritance.py
		# apply_remove_placements / apply_deactivate_placements. The canonical
		# authored form is a list of strings, not a list of mappings.
		for op in ['remove_placements', 'deactivate_placements']:
			ops = scene.get(op, [])
			if not isinstance(ops, list):
				findings.append(Finding(
					path=path,
					lineno=None,
					severity=Severity.ERROR,
					message=f"{op} must be a list",
				))
				continue

			for idx, entry in enumerate(ops):
				entry_path = f"{path}.{op}[{idx}]"
				# Each entry must be a non-empty placement-name string.
				if not isinstance(entry, str) or not entry:
					findings.append(Finding(
						path=entry_path,
						lineno=None,
						severity=Severity.ERROR,
						message="entry must be a non-empty placement_name string",
					))
					continue

				if entry not in new_placement_names:
					findings.append(Finding(
						path=entry_path,
						lineno=None,
						severity=Severity.ERROR,
						message=f"{op} references unknown placement_name '{entry}'",
					))

		# add_placements and reposition_placements are LISTS OF MAPPINGS,
		# each carrying a 'placement_name' key plus operation fields.
		for op in ['reposition_placements', 'add_placements']:
			ops = scene.get(op, [])
			if not isinstance(ops, list):
				findings.append(Finding(
					path=path,
					lineno=None,
					severity=Severity.ERROR,
					message=f"{op} must be a list",
				))
				continue

			for idx, entry in enumerate(ops):
				entry_path = f"{path}.{op}[{idx}]"
				if not isinstance(entry, dict):
					findings.append(Finding(
						path=entry_path,
						lineno=None,
						severity=Severity.ERROR,
						message="entry must be a mapping",
					))
					continue

				if 'placement_name' not in entry:
					findings.append(Finding(
						path=entry_path,
						lineno=None,
						severity=Severity.ERROR,
						message="entry missing required 'placement_name'",
					))
					continue

				pname = entry['placement_name']
				align_stop = entry.get('align_stop')
				if align_stop is not None and align_stop not in ALIGN_STOP_VALUES:
					findings.append(Finding(
						path=entry_path,
						lineno=None,
						severity=Severity.ERROR,
						message=(
							f"{op} align_stop '{align_stop}' is not valid "
							f"(allowed: {sorted(ALIGN_STOP_VALUES)})"
						),
					))

				if op == 'add_placements':
					if pname in base_placement_names:
						findings.append(Finding(
							path=entry_path,
							lineno=None,
							severity=Severity.ERROR,
							message=f"add_placements placement_name '{pname}' collides with base",
						))
					else:
						new_placement_names.add(pname)
				else:
					if pname not in new_placement_names:
						findings.append(Finding(
							path=entry_path,
							lineno=None,
							severity=Severity.ERROR,
							message=f"{op} references unknown placement_name '{pname}'",
						))

				if op == 'reposition_placements':
					for key in entry:
						if key not in REPOSITION_ALLOWED_FIELDS:
							findings.append(Finding(
								path=entry_path,
								lineno=None,
								severity=Severity.ERROR,
								message=f"reposition_placements may only change {REPOSITION_ALLOWED_FIELDS}, not '{key}'",
							))

				if op == 'add_placements':
					for key in entry:
						if key in PLACEMENT_LOCKED_FIELDS:
							findings.append(Finding(
								path=entry_path,
								lineno=None,
								severity=Severity.ERROR,
								message=f"add_placements may not set object-owned field '{key}'",
							))

		return findings
