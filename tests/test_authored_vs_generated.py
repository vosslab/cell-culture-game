"""
Test that generated TS files are under generated/ and authored files are under src/.

WP-1.2.1: Verify the authored/generated boundary:
- No file under src/ carries an AUTO-GENERATED header.
- Every .ts file under generated/ carries an AUTO-GENERATED or "Generated file" header.
- The test bootstraps generators if generated/ files are missing, or skips that half gracefully.
"""

import os
import re

import pytest

import file_utils


#============================================
def is_ts_file(path: str) -> bool:
	"""Check if a file is a TypeScript source file (.ts or .mjs)."""
	return path.endswith(".ts") or path.endswith(".mjs")


#============================================
def get_first_comment_line(file_path: str) -> str:
	"""
	Extract the first line of the file that looks like a comment.
	For TypeScript, that's typically a // comment on line 1.
	Returns the full line (with leading //) or empty string if no comment found.
	"""
	with open(file_path, "r", encoding="utf-8") as f:
		for line in f:
			line = line.rstrip()
			# Skip blank lines
			if not line.strip():
				continue
			# Return the first non-blank line that is a comment
			if line.strip().startswith("//") or line.strip().startswith("/*"):
				return line.strip()
			# Stop at first non-comment, non-blank line
			break
	return ""


#============================================
def has_generated_marker(first_comment: str) -> bool:
	"""Check if a comment line contains AUTO-GENERATED or Generated file marker."""
	if not first_comment:
		return False
	# Case-insensitive search for the markers
	return bool(
		re.search(r"AUTO-GENERATED", first_comment, re.IGNORECASE)
		or re.search(r"Generated file", first_comment, re.IGNORECASE)
	)


#============================================
def walk_ts_files_in_dir(dir_path: str) -> list[str]:
	"""Walk a directory and return all .ts files (relative to repo root)."""
	repo_root = file_utils.get_repo_root()
	ts_files = []
	if not os.path.isdir(dir_path):
		return ts_files
	for root, dirs, files in os.walk(dir_path):
		for f in files:
			if is_ts_file(f):
				full_path = os.path.join(root, f)
				rel_path = os.path.relpath(full_path, repo_root)
				ts_files.append(rel_path)
	return ts_files


#============================================
def test_src_has_no_generated_markers() -> None:
	"""WP-1.2.1a: Assert no file under src/ carries an AUTO-GENERATED header."""
	repo_root = file_utils.get_repo_root()
	src_dir = os.path.join(repo_root, "src")

	offending_files = []
	for ts_file in walk_ts_files_in_dir(src_dir):
		full_path = os.path.join(repo_root, ts_file)
		first_comment = get_first_comment_line(full_path)
		if has_generated_marker(first_comment):
			offending_files.append((ts_file, first_comment))

	assert not offending_files, (
		"The following files under src/ carry AUTO-GENERATED headers"
		" but should not be in src/:\n"
		+ "\n".join(
			f"  {f}: {comment}"
			for f, comment in offending_files
		)
	)


#============================================
def test_generated_ts_all_have_markers() -> None:
	"""
	WP-1.2.1b: Assert every .ts file under generated/ carries an AUTO-GENERATED marker.

	conftest.pytest_sessionstart() bootstraps generated/ if any required file is missing.
	If generated/ is still absent after bootstrap, skip with a clear message.
	"""
	repo_root = file_utils.get_repo_root()
	generated_dir = os.path.join(repo_root, "generated")

	# Check if generated/ exists and has .ts files
	if not os.path.isdir(generated_dir):
		pytest.skip(
			"generated/ not found after conftest bootstrap; "
			"run: npm run prebuild"
		)

	# Now check all .ts files in generated/
	ts_files = walk_ts_files_in_dir(generated_dir)

	if not ts_files:
		# No .ts files in generated/, which is OK on a clean checkout.
		# Just skip with a message.
		pytest.skip(
			"No .ts files found in generated/; "
			"run: npm run prebuild"
		)

	# Check that each .ts file has a generated marker
	offending_files = []
	for ts_file in ts_files:
		full_path = os.path.join(repo_root, ts_file)
		first_comment = get_first_comment_line(full_path)
		if not has_generated_marker(first_comment):
			offending_files.append((ts_file, first_comment or "(no comment)"))

	assert not offending_files, (
		"The following files under generated/ do not carry AUTO-GENERATED headers"
		" but should:\n"
		+ "\n".join(
			f"  {f}: {comment}"
			for f, comment in offending_files
		)
	)
