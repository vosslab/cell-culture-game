"""Content tree discovery utilities."""

import subprocess
from pathlib import Path
from collections.abc import Iterator

import yaml

from validation.shared_toolkit.repo_root import REPO_ROOT


def _protocol_name_for_path(path: str | Path) -> str | None:
	"""
	Walk up from path and return the protocol directory name.

	Walks up from the given path until finding a directory containing
	protocol.yaml. Returns the basename of that directory (the protocol name),
	or None if no such ancestor exists.

	This helper makes discovery layout-agnostic: works whether protocols
	live at depth 2 (flat: content/protocols/<name>) or depth 3 (clustered:
	content/protocols/<cluster>/<name>).

	Args:
		path: File or directory path (absolute or relative).

	Returns:
		Protocol directory basename, or None if no protocol.yaml ancestor found.
	"""
	current = Path(path).resolve()

	# Walk up at most 10 levels to avoid infinite loops
	for _ in range(10):
		if not current.is_dir():
			current = current.parent

		if (current / "protocol.yaml").exists():
			return current.name

		parent = current.parent
		if parent == current:
			# Reached filesystem root
			break
		current = parent

	return None


def find_protocol_directory(protocols_root: Path, protocol_name: str) -> Path:
	"""
	Find the absolute path to a protocol directory.

	Searches under protocols_root for a protocol directory with the given name.
	Works with both flat layout (content/protocols/<name>) and clustered layout
	(content/protocols/<cluster>/<name>).

	Args:
		protocols_root: Path to content/protocols directory (absolute or relative).
		protocol_name: Name of the protocol (directory basename).

	Returns:
		Absolute Path to the protocol directory.

	Raises:
		RuntimeError: If protocol_name is not found under protocols_root.
	"""
	protocols_path = Path(protocols_root).resolve()
	if not protocols_path.exists():
		raise RuntimeError(f"Protocols root does not exist: {protocols_root}")

	# Search for protocol.yaml under a directory named protocol_name
	for protocol_yaml in protocols_path.rglob("protocol.yaml"):
		if protocol_yaml.parent.name == protocol_name:
			return protocol_yaml.parent

	# Protocol not found
	raise RuntimeError(f"Protocol '{protocol_name}' not found under {protocols_root}")


def construct_protocol_scene_path(protocols_root: Path, protocol_name: str, scene_name: str) -> str:
	"""
	Construct the relative path to a protocol-local scene.

	Searches under protocols_root for a protocol directory with the given name
	and computes the path to its scene YAML file. Works with both flat layout
	(content/protocols/<name>) and clustered layout (content/protocols/<cluster>/<name>).

	Args:
		protocols_root: Path to content/protocols directory (absolute or relative).
		protocol_name: Name of the protocol (directory basename).
		scene_name: Name of the scene (without .yaml extension).

	Returns:
		Relative path string (e.g., "content/protocols/<cluster>/<name>/scenes/<scene>.yaml").

	Raises:
		RuntimeError: If protocol_name is not found under protocols_root.
	"""
	protocol_dir = find_protocol_directory(protocols_root, protocol_name)
	scene_path = protocol_dir / "scenes" / f"{scene_name}.yaml"
	# Return relative to REPO_ROOT if protocol_dir is under REPO_ROOT
	try:
		return str(scene_path.relative_to(REPO_ROOT))
	except ValueError:
		# protocol_dir is absolute but not under REPO_ROOT; return as-is
		return str(scene_path)


def find_protocol_yaml_files(protocols_root: Path) -> list[Path]:
	"""
	Find every protocol.yaml under protocols_root, at any depth.

	Returns a sorted list of absolute paths. Works with both flat layout
	(content/protocols/<name>/protocol.yaml) and clustered layout
	(content/protocols/<cluster>/<name>/protocol.yaml).

	Args:
		protocols_root: Path to content/protocols directory.

	Returns:
		Sorted list of absolute paths to protocol.yaml files.
	"""
	if not protocols_root.exists():
		return []
	return sorted(protocols_root.rglob("protocol.yaml"))


def iter_protocols() -> Iterator[Path]:
	"""
	Yield each protocol.yaml file in the content tree.

	Each yielded path is an absolute Path to a file named protocol.yaml
	under content/protocols/ at any depth. Works with both flat layout
	(content/protocols/<name>/protocol.yaml) and clustered layout
	(content/protocols/<cluster>/<name>/protocol.yaml).
	"""
	protocols_dir = REPO_ROOT / "content" / "protocols"
	for protocol_yaml in find_protocol_yaml_files(protocols_dir):
		yield protocol_yaml


def iter_scenes() -> Iterator[Path]:
	"""
	Yield each scene YAML file in the content tree.

	Yields scene YAML files from:
	- content/protocols/<protocol_name>/scenes/*.yaml (any depth)
	- content/base_scenes/*.yaml
	"""
	# Scenes under individual protocols (at any depth)
	protocols_dir = REPO_ROOT / "content" / "protocols"
	if protocols_dir.exists():
		for scene_yaml in protocols_dir.rglob("scenes/*.yaml"):
			yield scene_yaml

	# Base scenes directory
	base_scenes_dir = REPO_ROOT / "content" / "base_scenes"
	if base_scenes_dir.exists():
		for scene_yaml in base_scenes_dir.glob("*.yaml"):
			yield scene_yaml


def iter_objects() -> Iterator[Path]:
	"""
	Yield each object YAML file in the content tree.

	Each yielded path is an absolute Path to a file under
	content/objects/<kind>/*.yaml, enumerated recursively.
	"""
	objects_dir = REPO_ROOT / "content" / "objects"
	if objects_dir.exists():
		for object_yaml in objects_dir.rglob("*.yaml"):
			yield object_yaml


def iter_focus() -> dict:
	"""
	Discover changed content and compute scope for focused validation.

	Runs git diff to identify touched files and maps them to validation
	entities (protocols, objects, scenes). Computes transitive dependents:
	if a protocol references a changed object/scene, the protocol is included
	in transitive_protocols.

	Returns:
		dict with keys:
		  - protocols: set[str] of directly changed protocol names
		  - objects: set[str] of directly changed object names
		  - scenes: set[str] of directly changed scene names
		  - transitive_protocols: set[str] of protocols that reference changed entities

	If git is unavailable or we are not in a git repo, returns empty sets.
	"""
	changed_paths = set()

	try:
		# Collect changed paths from git diff (HEAD vs working tree)
		result = subprocess.run(
			['git', 'diff', '--name-only', 'HEAD'],
			cwd=str(REPO_ROOT),
			capture_output=True,
			text=True,
			timeout=10,
		)
		if result.returncode == 0:
			for line in result.stdout.strip().split('\n'):
				if line:
					changed_paths.add(line)

		# Collect staged changes
		result = subprocess.run(
			['git', 'diff', '--name-only', '--cached'],
			cwd=str(REPO_ROOT),
			capture_output=True,
			text=True,
			timeout=10,
		)
		if result.returncode == 0:
			for line in result.stdout.strip().split('\n'):
				if line:
					changed_paths.add(line)

		# Collect untracked modified files
		result = subprocess.run(
			['git', 'ls-files', '--others', '--exclude-standard', '--modified'],
			cwd=str(REPO_ROOT),
			capture_output=True,
			text=True,
			timeout=10,
		)
		if result.returncode == 0:
			for line in result.stdout.strip().split('\n'):
				if line:
					changed_paths.add(line)
	except (subprocess.TimeoutExpired, FileNotFoundError):
		# If git is unavailable or fails, return empty scope
		return {
			'protocols': set(),
			'objects': set(),
			'scenes': set(),
			'transitive_protocols': set(),
		}

	# Map changed paths to entities
	protocols_direct = set()
	objects_direct = set()
	scenes_direct = set()

	for path in changed_paths:
		# content/protocols/<...>/... -> protocol name (via marker walk)
		if path.startswith('content/protocols/'):
			protocol_name = _protocol_name_for_path(path)
			if protocol_name:
				protocols_direct.add(protocol_name)
				# If it's under scenes/, also add the scene
				if '/scenes/' in path:
					scene_name = path.split('/')[-1].replace('.yaml', '')
					scenes_direct.add(scene_name)

		# content/objects/<kind>/<name>.yaml -> object <name>
		elif path.startswith('content/objects/'):
			parts = path.split('/')
			if len(parts) >= 3 and path.endswith('.yaml'):
				obj_name = parts[-1].replace('.yaml', '')
				objects_direct.add(obj_name)

		# content/base_scenes/<name>.yaml -> scene <name>
		elif path.startswith('content/base_scenes/') and path.endswith('.yaml'):
			parts = path.split('/')
			if len(parts) >= 2:
				scene_name = parts[-1].replace('.yaml', '')
				scenes_direct.add(scene_name)

	# Compute transitive protocols: scan every protocol.yaml and check if it
	# references any changed object or scene by name
	transitive_protocols = set()

	for protocol_path in iter_protocols():
		with open(protocol_path, 'r', encoding='utf-8') as f:
			protocol_data = yaml.safe_load(f)
		if not protocol_data:
			continue

		# Get protocol name from directory name
		protocol_name = protocol_path.parent.name

		# Check if protocol references any changed object or scene
		protocol_yaml_str = str(protocol_data)
		references_changed = False

		for obj_name in objects_direct:
			if obj_name in protocol_yaml_str:
				references_changed = True
				break

		if not references_changed:
			for scene_name in scenes_direct:
				if scene_name in protocol_yaml_str:
					references_changed = True
					break

		if references_changed:
			transitive_protocols.add(protocol_name)

	return {
		'protocols': protocols_direct,
		'objects': objects_direct,
		'scenes': scenes_direct,
		'transitive_protocols': transitive_protocols,
	}
