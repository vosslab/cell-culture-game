"""Scene discovery and target resolution behavior for StateMap."""

import validation.stepper.findings
import validation.stepper.loader


class SceneResolutionMixin:
	def _reachable_base_scenes(self) -> set:
		"""
		Compute base scenes actually reachable by this protocol.

		Reachable = referenced via `extends` from a protocol-local scene, OR named by a
		SceneChange.to_scene op anywhere in the protocol's steps. Without this filter,
		every base scene under content/base_scenes/ (including unrelated SDS-PAGE benches)
		leaks into the registry and creates spurious ambiguous_target_in_scene errors
		when two unrelated protocols both place the same object kind.
		"""
		reachable: set = set()

		# Base scenes extended by any protocol-local scene
		for scene_protocol_name in self.scene_protocol_names:
			protocol_local_scenes = self.tree.protocol_local_scenes.get(scene_protocol_name, {})
			for scene_data in protocol_local_scenes.values():
				extends = scene_data.get("extends") if isinstance(scene_data, dict) else None
				if extends and extends in self.tree.base_scenes:
					reachable.add(extends)

		# Base scenes named by SceneChange ops in this protocol's steps
		for scene_protocol_name in self.scene_protocol_names:
			try:
				protocol = self.tree.get_protocol(scene_protocol_name)
			except validation.stepper.loader.ProtocolNotFoundError:
				protocol = None
			if not isinstance(protocol, dict):
				continue
			for step in protocol.get("steps", []) or []:
				if not isinstance(step, dict):
					continue
				for interaction in step.get("sequence", []) or []:
					if not isinstance(interaction, dict):
						continue
					response = interaction.get("response", {}) or {}
					for op in response.get("scene_operations", []) or []:
						if not isinstance(op, dict):
							continue
						if op.get("type") == "SceneChange":
							to_scene = op.get("to_scene")
							if to_scene and to_scene in self.tree.base_scenes:
								reachable.add(to_scene)

		return reachable

	def _build_scenes_registry(self) -> None:
		"""
		Build a per-protocol registry of all resolvable placements across all scenes.

		The registry maps object_name -> [(placement_name, scene_name), ...]
		This allows target resolution to fall back to cross-scene lookup when
		active-scene lookup fails, per SCENE_VOCABULARY.md "Scene-adapter resolution".

		Deactivated placements are excluded per spec.

		Needed because a target may be named in a step whose active scene differs from
		the scene where the target's placement was declared; registry lets resolution succeed
		across sibling scenes in the same protocol without forcing authors to insert SceneChange
		ops back to the prior scene.

		Scope is restricted to scenes reachable by this protocol (protocol-local scenes plus
		base scenes referenced via `extends` or SceneChange). Unrelated base scenes from
		other protocols must not pollute this registry.
		"""
		# Collect reachable scene data (protocol-local + referenced base) with their names
		all_scenes = {}

		# Add only base scenes actually referenced by this protocol
		reachable_base = self._reachable_base_scenes()
		protocol_local_scenes = {}
		for scene_protocol_name in self.scene_protocol_names:
			protocol_local_scenes.update(self.tree.protocol_local_scenes.get(scene_protocol_name, {}))
		if not reachable_base and not protocol_local_scenes:
			# No protocol-local scenes and no SceneChange ops to constrain the set; fall back to
			# every base scene so target resolution still works for trivial single-base-scene protocols.
			reachable_base = set(self.tree.base_scenes.keys())
		for scene_name in reachable_base:
			scene_data = self.tree.base_scenes.get(scene_name)
			if scene_data is not None:
				all_scenes[scene_name] = (scene_data, 'base')

		# Add protocol-local scenes
		for scene_name, scene_data in protocol_local_scenes.items():
			all_scenes[scene_name] = (scene_data, 'protocol')

		# Track unique registrations by (placement_name, object_name) to avoid duplicates
		# from base scenes appearing both in their own iteration and in extended scene inheritance
		seen = set()

		# For each scene, extract effective placements and register them
		for scene_name, (scene_data, _) in all_scenes.items():
			effective_placements = self._get_effective_placements(scene_data)

			for placement in effective_placements:
				if not isinstance(placement, dict):
					continue

				placement_name = placement.get('placement_name')
				object_name = placement.get('object_name')

				if not placement_name or not object_name:
					continue

				# Deduplicate by (placement_name, object_name) pair to prevent registering
				# the same placement twice when it appears in both base and extended scenes
				entry_key = (placement_name, object_name)
				if entry_key in seen:
					continue
				seen.add(entry_key)

				# Register this placement under its object_name
				if object_name not in self._scenes_registry:
					self._scenes_registry[object_name] = []

				self._scenes_registry[object_name].append((placement_name, scene_name))

	#============================================

	def resolve_target(
		self,
		target_str: str,
		step_name: str | None = None,
		interaction_index: int | None = None,
	) -> tuple[str | None, str | None]:
		"""
		Resolve a semantic target string to a placement_name in the active scene.

		A target_str is a semantic name like "micropipette" or "well_plate_96.A1".
		This method:
		  1. Splits the target on first "." to separate object_name_part and subpart_name.
		  2. Scans placements in the active scene for matching object_name.
		  3. If exactly one match: returns (placement_name, subpart_name_or_None).
		  4. If multiple matches: emits ERROR [ambiguous_target_in_scene] and returns first match for graceful continuation.
		  5. If zero matches: emits ERROR [unknown_target_active_scene] and returns (None, subpart_name_or_None).
		  6. If subpart_name is present, validates it against the object's subparts (soft check).

		Args:
			target_str: The semantic target string (e.g. "micropipette" or "well_plate_96.A1").
			step_name: Optional step name for error context.
			interaction_index: Optional interaction index for error context.

		Returns:
			(placement_name, subpart_name) tuple, or (None, subpart_name) if resolution failed.
		"""
		if not target_str:
			return None, None

		# Split on first "." to separate object_name_part and subpart_name
		if "." in target_str:
			object_name_part, subpart_name = target_str.split(".", 1)
		else:
			object_name_part = target_str
			subpart_name = None

		if subpart_name is not None:
			object_data = self.tree.get_object(object_name_part)
			if not object_data or not self.tree.database.subpart_matches(object_data, subpart_name):
				self.emitter.emit_finding(validation.stepper.findings.Finding(
					level=validation.stepper.findings.Level.ERROR,
					protocol_name=self.protocol_name,
					step_name=step_name,
					interaction_index=interaction_index,
					target=target_str,
					file_path="unknown",
					code="unknown_authored_subpart",
					message=f"target '{target_str}' names no declared subpart",
					spec_cite="docs/PRIMARY_SPEC.md Targets and the scene boundary",
				))
				return None, subpart_name

		# If no active scene, emit error
		if not self._active_scene:
			self.emitter.emit_finding(validation.stepper.findings.Finding(
				level=validation.stepper.findings.Level.ERROR,
				protocol_name=self.protocol_name,
				step_name=step_name,
				interaction_index=interaction_index,
				target=target_str,
				file_path="unknown",
				code="no_active_scene_at_resolution",
				message=f"Cannot resolve target '{target_str}': no active scene set before target resolution",
				spec_cite="docs/PRIMARY_SPEC.md Targets and the scene boundary",
			))
			return None, subpart_name

		# Get placements from the active scene
		active_scene_data = self._get_active_scene_data()
		if not active_scene_data:
			self.emitter.emit_finding(validation.stepper.findings.Finding(
				level=validation.stepper.findings.Level.ERROR,
				protocol_name=self.protocol_name,
				step_name=step_name,
				interaction_index=interaction_index,
				target=target_str,
				file_path="unknown",
				code="unknown_active_scene",
				message=f"Active scene '{self._active_scene}' not found in base scenes or protocol-local scenes",
				spec_cite="docs/PRIMARY_SPEC.md Targets and the scene boundary",
			))
			return None, subpart_name

		# Get effective placements (base + inherited + add_placements - remove_placements)
		effective_placements = self._get_effective_placements(active_scene_data)

		# Find placements by semantic object name or explicit placement identity.
		matching_placements = []
		for placement in effective_placements:
			if isinstance(placement, dict):
				if placement.get("object_name") == object_name_part or placement.get("placement_name") == object_name_part:
					placement_name = placement.get("placement_name")
					if placement_name:
						matching_placements.append((placement_name, placement))

		# Scene adapters resolve semantic objects only in the active scene.  A
		# cross-scene match is state identity, not a clickable target here.
		if len(matching_placements) == 0:
			self.emitter.emit_finding(validation.stepper.findings.Finding(
				level=validation.stepper.findings.Level.ERROR,
				protocol_name=self.protocol_name,
				step_name=step_name,
				interaction_index=interaction_index,
				target=target_str,
				file_path="unknown",
				code="unknown_target_active_scene",
				message=f"target '{target_str}' (object_name '{object_name_part}') is not present in active scene '{self._active_scene}'",
				spec_cite="docs/specs/SCENE_VOCABULARY.md Scene-adapter resolution",
			))
			return None, subpart_name

		if len(matching_placements) > 1:
			self.emitter.emit_finding(validation.stepper.findings.Finding(
				level=validation.stepper.findings.Level.ERROR,
				protocol_name=self.protocol_name,
				step_name=step_name,
				interaction_index=interaction_index,
				target=target_str,
				file_path="unknown",
				code="ambiguous_target_in_scene",
				message=f"target '{target_str}' (object_name '{object_name_part}') matches multiple placements in scene '{self._active_scene}': {', '.join(p[0] for p in matching_placements)}",
				spec_cite="docs/PRIMARY_SPEC.md Targets and the scene boundary",
			))
			# Continue gracefully with first match
			return matching_placements[0][0], subpart_name

		# Exactly one match in active scene
		placement_name = matching_placements[0][0]
		if subpart_name is not None:
			placement_data = self._state.get(placement_name)
			object_name = placement_data["object_name"] if placement_data else object_name_part
			object_data = self.tree.get_object(object_name)
			if not object_data or not self.tree.database.subpart_matches(object_data, subpart_name):
				self.emitter.emit_finding(validation.stepper.findings.Finding(
					level=validation.stepper.findings.Level.ERROR,
					protocol_name=self.protocol_name,
					step_name=step_name,
					interaction_index=interaction_index,
					target=target_str,
					file_path="unknown",
					code="unknown_authored_subpart",
					message=f"target '{target_str}' names no declared subpart on '{object_name}'",
					spec_cite="docs/PRIMARY_SPEC.md Targets and the scene boundary",
				))
				return None, subpart_name

		object_name = matching_placements[0][1]["object_name"]
		return self._object_state_keys[object_name], subpart_name

	def _get_active_scene_data(self) -> dict | None:
		"""
		Retrieve the YAML data for the active scene.

		Returns:
			Scene data dict, or None if not found.
		"""
		if not self._active_scene:
			return None

		# Check base scenes first
		if self._active_scene in self.tree.base_scenes:
			return self.tree.base_scenes[self._active_scene]

		# Check protocol-local scenes
		for scene_protocol_name in self.scene_protocol_names:
			protocol_local_scenes = self.tree.protocol_local_scenes.get(scene_protocol_name, {})
			if self._active_scene in protocol_local_scenes:
				return protocol_local_scenes[self._active_scene]

		return None

	def _get_effective_placements(self, scene_data: dict) -> list:
		"""
		Compute effective placements for a scene, accounting for inheritance.

		For a scene that extends a base scene, resolve the inheritance.
		Apply add_placements and remove_placements.

		Args:
			scene_data: The scene YAML dict.

		Returns:
			List of placement dicts.
		"""
		# Start with placements from the scene
		placements = scene_data.get("placements", [])
		if not isinstance(placements, list):
			placements = []

		# If this scene extends a base scene, start with base placements
		extends = scene_data.get("extends")
		if extends and extends in self.tree.base_scenes:
			base_scene = self.tree.base_scenes[extends]
			base_placements = base_scene.get("placements", [])
			placements = list(base_placements) if isinstance(base_placements, list) else []

		# Apply remove_placements (by name)
		# Apply removals to inherited placements before additions, the same order
		# used by the runtime scene resolver. A derived same-name addition is a
		# replacement, not a second thing to remove.
		remove_placements = scene_data.get("remove_placements", [])
		if isinstance(remove_placements, list):
			# Handle string entries (the YAML format) as well as legacy dict entries
			removed_names: set[str] = set()
			for p in remove_placements:
				if isinstance(p, str):
					removed_names.add(p)
				elif isinstance(p, dict):
					name = p.get("placement_name")
					if name:
						removed_names.add(name)
			placements = [p for p in placements if not (isinstance(p, dict) and p.get("placement_name") in removed_names)]

		# Apply local additions after inherited removals.
		add_placements = scene_data.get("add_placements", [])
		if isinstance(add_placements, list):
			placements.extend(add_placements)

		return placements

	#============================================

