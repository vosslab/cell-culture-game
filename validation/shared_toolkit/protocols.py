"""Protocol discovery and name-or-path resolution shared across tools."""

import os
from pathlib import Path

import validation.shared_toolkit.paths as paths
from validation.shared_toolkit.discovery import find_protocol_yaml_files


def list_protocols(protocols_dir: object=None) -> object:
	"""
	List protocol package names under content/protocols/.

	A protocol package is a directory containing protocol.yaml. Returns a
	sorted list of names. Works with both flat layout (content/protocols/<name>)
	and clustered layout (content/protocols/<cluster>/<name>) by using
	marker-based discovery.
	"""
	root = protocols_dir if protocols_dir is not None else paths.PROTOCOLS_DIR
	root_path = Path(root)
	if not root_path.exists():
		return []

	# Use marker-based discovery to find all protocol.yaml files at any depth
	protocol_yamls = find_protocol_yaml_files(root_path)
	names = []
	for protocol_yaml in protocol_yamls:
		# Protocol directory is the parent of protocol.yaml
		protocol_dir = protocol_yaml.parent
		names.append(protocol_dir.name)

	return sorted(names)


def resolve_protocol_path(name_or_path: object, repo_root: object=None) -> object:
	"""
	Resolve a protocol identifier to an absolute protocol.yaml Path.

	If name_or_path contains '/' or ends in '.yaml', treat as a file
	path (absolute or repo-relative). Otherwise treat as a protocol
	directory name (protocol_name) and search for it under content/protocols/
	at any depth via marker-based discovery.

	Returns Path on success, None if no protocol file was found.
	"""
	root = repo_root if repo_root is not None else paths.REPO_ROOT
	test_path = Path(name_or_path)
	if "/" in name_or_path or name_or_path.endswith(".yaml"):
		if test_path.is_absolute():
			full_path = test_path
		else:
			full_path = Path(root) / name_or_path
		if full_path.exists() and full_path.is_file():
			return full_path
		return None

	# Search for protocol by name at any depth using marker-based discovery
	protocols_dir = Path(root) / "content" / "protocols"
	protocol_yamls = find_protocol_yaml_files(protocols_dir)
	for protocol_yaml in protocol_yamls:
		if protocol_yaml.parent.name == name_or_path:
			return protocol_yaml

	return None


def classify_protocol(protocol_dict: object) -> object:
	"""
	Return the declared protocol_type, defaulting to mini_protocol.

	Reads the protocol_type field from a parsed protocol.yaml. The default
	mirrors the runtime: an unset protocol_type is treated as mini.
	"""
	if not isinstance(protocol_dict, dict):
		return "mini_protocol"
	return protocol_dict.get("protocol_type", "mini_protocol")


def protocol_name_from_path(protocol_path: object) -> object:
	"""
	Derive the protocol directory name from a path to its protocol.yaml.

	The protocol directory is the parent of protocol.yaml; its basename is
	the canonical protocol name.
	"""
	return os.path.basename(os.path.dirname(str(protocol_path)))
