"""Load content tree and expose protocols, objects, materials, and scenes."""

from pathlib import Path

from validation.yaml_schema.database import ContentDatabase
from validation.shared_toolkit.yaml_io import load_yaml


class ProtocolNotFoundError(Exception):
	"""Raised when a protocol is not found in the content tree."""


class LoadedContentTree:
	"""Stepper-side view of loaded content, exposing protocols, objects, materials, and scenes."""

	def __init__(self, database: ContentDatabase, root_path: Path | None = None) -> None:
		"""Initialize with a populated ContentDatabase."""
		self.database = database
		self.objects = database.objects
		self.base_scenes = database.base_scenes
		self.protocols = database.protocols
		self.materials_by_protocol = database.materials_by_protocol
		self.protocol_local_scenes: dict = {}
		self.root_path = root_path

		# Load protocol-local scenes if root_path is provided
		if root_path:
			self._load_protocol_local_scenes()

	def get_protocol(self, protocol_name: str) -> dict:
		"""Fetch a protocol by name. Raises ProtocolNotFoundError if not found."""
		if protocol_name not in self.protocols:
			raise ProtocolNotFoundError(
				f"Protocol '{protocol_name}' not found in loaded content tree."
			)
		return self.protocols[protocol_name]

	def get_object(self, object_name: str) -> dict | None:
		"""Resolve an object by name."""
		return self.database.resolve_object(object_name)

	def get_target(self, target: str) -> tuple | None:
		"""
		Resolve a target (bare or dotted form).
		Returns (object_data, subpart_name) or None.
		Examples:
		  - "well_plate" -> (well_plate_object, None)
		  - "well_plate.A1" -> (well_plate_object, "A1")
		"""
		return self.database.resolve_target(target)

	def get_state_field(
		self,
		object_name: str,
		field_name: str,
		subpart_targeted: bool = False,
	) -> dict | None:
		"""
		Resolve a state field declaration for an object.

		Pass subpart_targeted=True to select the applies_to: subpart decl for a
		structured object; the default selects the object-level decl.
		"""
		return self.database.resolve_state_field(object_name, field_name, subpart_targeted)

	def get_material(self, protocol_name: str, material_name: str) -> dict | None:
		"""Resolve a material by protocol and name."""
		return self.database.resolve_material(protocol_name, material_name)

	def get_protocol_materials(self, protocol_name: str) -> dict:
		"""Fetch all materials declared for a protocol."""
		return self.materials_by_protocol.get(protocol_name, {})

	def _load_protocol_local_scenes(self) -> None:
		"""
		Load protocol-local scenes from content/protocols/<...>/scenes/ at any depth.

		Walks the entire protocols tree recursively and finds every scenes/
		directory that is a sibling of a protocol.yaml file. Populates
		self.protocol_local_scenes dict keyed by protocol_name.
		"""
		if not self.root_path:
			return

		protocols_dir = self.root_path / "content" / "protocols"
		if not protocols_dir.exists():
			return

		# Recursively find all protocol directories by locating protocol.yaml
		# at any depth
		for protocol_yaml in sorted(protocols_dir.rglob("protocol.yaml")):
			protocol_dir = protocol_yaml.parent
			protocol_name = protocol_dir.name
			scenes_dir = protocol_dir / "scenes"
			if not scenes_dir.exists():
				continue

			protocol_scenes = {}
			for scene_file in sorted(scenes_dir.glob("*.yaml")):
				# load_yaml raises RuntimeError on malformed YAML; let it propagate
				# so authors see the failure instead of silently dropping scenes.
				scene_data = load_yaml(scene_file)
				scene_name = scene_data.get("scene_name")
				if scene_name:
					protocol_scenes[scene_name] = scene_data

			if protocol_scenes:
				self.protocol_local_scenes[protocol_name] = protocol_scenes


def load_content_tree(root: Path | str) -> LoadedContentTree:
	"""
	Load content tree and return a LoadedContentTree.

	Args:
		root: Path to repo root or content directory.

	Returns:
		LoadedContentTree exposing protocols, objects, materials, base scenes,
		and protocol-local scenes for any protocol name.

	Raises:
		ProtocolNotFoundError: If a requested protocol is not found.
	"""
	root_path = Path(root)
	db = ContentDatabase()
	db.load_from_tree(root_path)
	return LoadedContentTree(db, root_path)
