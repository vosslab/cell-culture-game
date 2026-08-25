#!/usr/bin/env python3
"""
Build candidate manifest for SVG picker.

Walks assets/equipment/, OTHER_REPOS/bioicons/, OTHER_REPOS/scienceicons/
and emits tools/svg_picker/candidates.json with one record per SVG:
{id, source_repo, rel_path, filename, search_tokens, license_tag,
 license_url, license_confidence, attribution_required}
"""

import sys
import json
import argparse
import subprocess
import hashlib
from pathlib import Path


# License-folder names sit directly above the author folder in bioicons:
# OTHER_REPOS/bioicons/static/icons/<license>/<Author>/<file>.svg
LICENSE_FOLDERS = {
	"cc-0", "cc-by-3.0", "cc-by-4.0", "cc-by-sa-3.0", "cc-by-sa-4.0", "mit", "bsd",
}


def extract_bioicons_category(rel_path: str) -> str:
	"""Pull the category folder from a bioicons rel_path, or empty string.

	bioicons convention: .../static/icons/<license>/<Category>/<file>.svg
	(e.g. Human_physiology, Lab_apparatus, Chemistry). Returns the category
	segment when the parent of the file's folder matches a known license
	token; otherwise empty.
	"""
	parts = Path(rel_path).parts
	for i, part in enumerate(parts):
		if part in LICENSE_FOLDERS and i + 1 < len(parts) - 1:
			return parts[i + 1]
	return ""


def get_repo_root() -> object:
	"""Get repository root via git."""
	result = subprocess.run(
		["git", "rev-parse", "--show-toplevel"],
		capture_output=True,
		text=True,
		check=True
	)
	return result.stdout.strip()


def get_bioicons_license_for_path(repo_root: object, rel_path: object) -> object:
	"""
	Determine license for a bioicons SVG by checking its parent folder.

	bioicons/static/icons/ has subfolders: cc-0/, cc-by-3.0/, cc-by-4.0/,
	cc-by-sa-3.0/, cc-by-sa-4.0/, mit/, bsd/

	Returns: (license_tag, license_url, license_confidence, attribution_required)
	"""
	bioicons_base = Path(repo_root) / "OTHER_REPOS" / "bioicons"
	full_path = bioicons_base / rel_path

	# Walk up from SVG location to find a folder that matches a known license folder
	parent = full_path.parent
	while parent >= bioicons_base:
		folder_name = parent.name

		if folder_name == "cc-0":
			return ("CC0", "", "exact", False)
		elif folder_name == "cc-by-3.0":
			return ("CC-BY-3.0", "https://creativecommons.org/licenses/by/3.0/", "exact", True)
		elif folder_name == "cc-by-4.0":
			return ("CC-BY-4.0", "https://creativecommons.org/licenses/by/4.0/", "exact", True)
		elif folder_name == "cc-by-sa-3.0":
			return ("CC-BY-SA-3.0", "https://creativecommons.org/licenses/by-sa/3.0/", "exact", True)
		elif folder_name == "cc-by-sa-4.0":
			return ("CC-BY-SA-4.0", "https://creativecommons.org/licenses/by-sa/4.0/", "exact", True)
		elif folder_name == "mit":
			return ("MIT", "", "exact", False)
		elif folder_name == "bsd":
			return ("BSD", "", "exact", False)

		parent = parent.parent

	# Fallback: conservative default for unclear licenses
	return ("CC-BY", "https://creativecommons.org/licenses/by/4.0/", "inferred", True)


def extract_search_tokens(filename: object, parent_folder: object) -> object:
	"""
	Extract search tokens from filename and parent folder.

	Filename tokens: split on underscores, remove extension.
	Parent tokens: folder name split on underscores.
	Returns: deduplicated, lowercased list.
	"""
	tokens = set()

	# Filename tokens (without extension)
	name_part = filename.rsplit(".", 1)[0] if "." in filename else filename
	for token in name_part.split("_"):
		if token:
			tokens.add(token.lower())

	# Parent folder tokens
	folder_part = parent_folder.rsplit(".", 1)[0] if "." in parent_folder else parent_folder
	for token in folder_part.split("_"):
		if token:
			tokens.add(token.lower())

	return sorted(list(tokens))


def build_id(source_repo_short: object, rel_path: object) -> object:
	"""
	Build stable ID from source_repo and rel_path.
	Format: <source_repo_short>:<sha1(rel_path)[:12]>
	"""
	# usedforsecurity=False: SHA1 here builds a stable path-derived ID, not a
	# security digest.
	sha1 = hashlib.sha1(rel_path.encode(), usedforsecurity=False).hexdigest()[:12]
	return f"{source_repo_short}:{sha1}"


def walk_svg_directory(repo_root: object, source_path: object, source_repo: object, source_repo_short: object, verbose: object=False) -> None:
	"""
	Walk a directory of SVGs and yield candidate records.

	Args:
		repo_root: absolute repo root
		source_path: relative path within repo (e.g., "assets/equipment")
		source_repo: human name (e.g., "assets/equipment")
		source_repo_short: short code (e.g., "eq")
		verbose: print progress

	Yields: dict records
	"""
	full_path = Path(repo_root) / source_path

	if not full_path.exists():
		if verbose:
			print(f"Warning: {full_path} does not exist, skipping.", file=sys.stderr)
		return

	count = 0
	for svg_file in sorted(full_path.rglob("*.svg")):
		count += 1

		# rel_path is relative to repo root
		rel_path = str(svg_file.relative_to(repo_root))
		filename = svg_file.name
		parent_folder = svg_file.parent.name

		# License handling per source
		if source_repo_short == "eq":
			# assets/equipment/
			license_tag = "repo"
			license_url = ""
			license_confidence = "exact"
			attribution_required = False
		elif source_repo_short == "bio":
			# OTHER_REPOS/bioicons/
			license_tag, license_url, license_confidence, attribution_required = \
				get_bioicons_license_for_path(repo_root, rel_path)
		elif source_repo_short == "sci":
			# OTHER_REPOS/scienceicons/ - MIT per license file
			license_tag = "MIT"
			license_url = ""
			license_confidence = "exact"
			attribution_required = False
		else:
			# Unknown source
			license_tag = "unknown"
			license_url = ""
			license_confidence = "unknown"
			attribution_required = False

		category = extract_bioicons_category(rel_path) if source_repo_short == "bio" else ""

		record = {
			"id": build_id(source_repo_short, rel_path),
			"source_repo": source_repo,
			"rel_path": rel_path,
			"filename": filename,
			"category": category,
			"search_tokens": extract_search_tokens(filename, parent_folder),
			"license_tag": license_tag,
			"license_url": license_url,
			"license_confidence": license_confidence,
			"attribution_required": attribution_required
		}

		yield record

	if verbose:
		print(f"Indexed {count} SVGs from {source_repo}", file=sys.stderr)


def main() -> None:
	"""Main entry point."""
	parser = argparse.ArgumentParser(
		description="Build SVG candidate manifest from assets and external repos"
	)
	parser.add_argument(
		"-o", "--output",
		dest="output_path",
		default="tools/svg_picker/candidates.json",
		help="Output JSON file (default: tools/svg_picker/candidates.json)"
	)
	parser.add_argument(
		"-v", "--verbose",
		action="store_true",
		help="Print progress output"
	)

	args = parser.parse_args()

	# Get repo root
	try:
		repo_root = get_repo_root()
	except subprocess.CalledProcessError as e:
		print(f"Error: Could not determine repo root: {e}", file=sys.stderr)
		sys.exit(1)

	if args.verbose:
		print(f"Repo root: {repo_root}", file=sys.stderr)

	# Collect all candidates
	candidates = []

	# Walk assets/equipment/
	for record in walk_svg_directory(
		repo_root, "assets/equipment", "assets/equipment", "eq", args.verbose
	):
		candidates.append(record)

	# Walk OTHER_REPOS/bioicons/static/icons/
	for record in walk_svg_directory(
		repo_root, "OTHER_REPOS/bioicons/static/icons", "OTHER_REPOS/bioicons", "bio", args.verbose
	):
		candidates.append(record)

	# Walk OTHER_REPOS/scienceicons/icons/ or /
	for record in walk_svg_directory(
		repo_root, "OTHER_REPOS/scienceicons", "OTHER_REPOS/scienceicons", "sci", args.verbose
	):
		candidates.append(record)

	# Write output
	output_path = Path(repo_root) / args.output_path
	output_path.parent.mkdir(parents=True, exist_ok=True)

	with open(output_path, "w") as f:
		json.dump(candidates, f, indent=2)

	if args.verbose:
		print(f"Indexed {len(candidates)} candidates", file=sys.stderr)

	print(f"Indexed {len(candidates)} candidates")


if __name__ == "__main__":
	main()
