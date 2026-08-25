"""
Content tree paths derived from this file's location.

The repo layout is: <repo>/validation/shared_toolkit/paths.py. Constants below
are the conventional locations every tool uses. For tests that load a
temporary content tree, use paths_from_root() instead of the constants.

REPO_ROOT is re-exported from validation.shared_toolkit.repo_root, which is the
canonical single source.
"""

import os
from validation.shared_toolkit.repo_root import REPO_ROOT


PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT_STR = str(REPO_ROOT)
CONTENT_ROOT = os.path.join(REPO_ROOT_STR, "content")
PROTOCOLS_DIR = os.path.join(CONTENT_ROOT, "protocols")
OBJECTS_DIR = os.path.join(CONTENT_ROOT, "objects")
BASE_SCENES_DIR = os.path.join(CONTENT_ROOT, "base_scenes")


def paths_from_root(root: object) -> object:
	"""
	Return a dict of content-tree paths anchored at an arbitrary root.

	Useful for tests that build a temporary content tree and want the
	same path names as the production layout without monkey-patching the
	module-level constants.
	"""
	root_str = str(root)
	content_root = os.path.join(root_str, "content")
	paths = {
		"repo_root": root_str,
		"content_root": content_root,
		"protocols_dir": os.path.join(content_root, "protocols"),
		"objects_dir": os.path.join(content_root, "objects"),
		"base_scenes_dir": os.path.join(content_root, "base_scenes"),
	}
	return paths
