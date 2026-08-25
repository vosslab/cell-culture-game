"""Object discovery and name resolution shared across tools."""

from pathlib import Path

import validation.shared_toolkit.paths as paths


def list_objects(objects_dir: object=None) -> object:
	"""
	List object YAML file basenames (without .yaml) under content/objects/.

	Returns a sorted list of object names (file stems).
	"""
	root = objects_dir if objects_dir is not None else paths.OBJECTS_DIR
	root_path = Path(root)
	if not root_path.exists():
		return []
	names = []
	for item in sorted(root_path.glob("**/*.yaml")):
		if item.is_file():
			names.append(item.stem)
	return names
