"""
Test that no Python file and directory share the same name in the repo.

This guards against Python import resolution silently preferring the package
over the module, which can hide bugs.
"""

import os
import file_utils


#============================================
def test_no_file_folder_name_collision() -> None:
	"""
	Assert that no directory contains both a file named <X>.py and a subdirectory named <X>.
	"""
	REPO_ROOT = file_utils.get_repo_root()

	# Directories to exclude from the walk
	EXCLUDE_DIRS = {
		'.git', 'node_modules', 'build', 'dist', 'dist-single', 'generated',
		'output_manuals', '.claude', '__pycache__', 'archive'
	}

	collisions = []

	for root, dirs, files in os.walk(REPO_ROOT):
		# Remove excluded directories from dirs to prevent walking into them
		dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith('.')]

		# Get the set of .py files in this directory (without extension)
		py_files = {f[:-3] for f in files if f.endswith('.py')}

		# Get the set of directories in this directory
		dir_names = set(dirs)

		# Find collisions
		collision_names = py_files & dir_names
		if collision_names:
			for name in sorted(collision_names):
				rel_root = os.path.relpath(root, REPO_ROOT)
				collisions.append({
					'dir': rel_root,
					'name': name,
					'file': os.path.join(rel_root, f'{name}.py'),
					'folder': os.path.join(rel_root, name),
				})

	# Build detailed error message if collisions were found
	if collisions:
		error_lines = ["Python file/folder name collisions found:"]
		for c in collisions:
			error_lines.append(f"  {c['file']} and {c['folder']}/")
		error_message = "\n".join(error_lines)
		assert False, error_message
