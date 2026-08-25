"""
Shared SVG validator module.

Validates SVG files for safety and structural sanity.
Exposes validate() function that returns ValidationReport or raises on errors.
"""

import os
from dataclasses import dataclass

import lxml.etree


@dataclass
class ValidationReport:
	"""Result of SVG validation."""
	ok: bool
	file_path: str
	error_message: str = ""


def validate(svg_path: str) -> ValidationReport:
	"""
	Validate an SVG file for safety and structure.

	Args:
		svg_path: absolute path to SVG file

	Returns:
		ValidationReport with ok=True if valid, ok=False with error_message if invalid

	Raises:
		FileNotFoundError: if file not found
		ValueError: on validation failure (file outside assets, remote refs, etc.)
	"""
	abs_path = os.path.abspath(svg_path)

	# Check file exists
	if not os.path.isfile(abs_path):
		raise FileNotFoundError(f"SVG file not found: {abs_path}")

	# Check path is under assets/**/
	repo_root = _get_repo_root()
	assets_dir = os.path.join(repo_root, "assets")
	try:
		rel_path = os.path.relpath(abs_path, assets_dir)
		if rel_path.startswith(".."):
			raise ValueError(f"SVG file outside assets/: {abs_path}")
	except ValueError:
		raise ValueError(f"SVG file outside assets/: {abs_path}")

	# Check for symlinks pointing outside assets
	if os.path.islink(abs_path):
		target = os.readlink(abs_path)
		if not os.path.isabs(target):
			target = os.path.normpath(os.path.join(os.path.dirname(abs_path), target))
		try:
			rel_target = os.path.relpath(target, assets_dir)
			if rel_target.startswith(".."):
				raise ValueError(f"SVG symlink target outside assets/: {abs_path} -> {target}")
		except ValueError:
			raise ValueError(f"SVG symlink target outside assets/: {abs_path} -> {target}")

	# Parse XML. Hardened lxml parser: resolve_entities=False blocks XXE entity
	# expansion, no_network=True blocks external DTD/entity network fetches.
	# remove_comments=True and remove_pis=True match stdlib ElementTree's
	# default behavior (comments and processing instructions are dropped from
	# the tree), so root.iter() below never yields a Comment/PI node whose
	# .tag is the lxml factory function instead of a string.
	# First-party repo asset, but the parser stays hardened regardless of source trust.
	try:
		parser = lxml.etree.XMLParser(
			resolve_entities=False, no_network=True, remove_comments=True, remove_pis=True
		)
		tree = lxml.etree.parse(abs_path, parser)
		root = tree.getroot()
	except lxml.etree.XMLSyntaxError as e:
		raise ValueError(f"Malformed XML: {abs_path}: {e}")

	# Check root is <svg>
	if not root.tag.endswith("}svg") and root.tag != "svg":
		raise ValueError(f"Root element is not <svg>: {abs_path}")

	# Check for viewBox
	if "viewBox" not in root.attrib:
		raise ValueError(f"Missing viewBox attribute: {abs_path}")

	viewbox_val = root.attrib["viewBox"].strip()
	if not viewbox_val:
		raise ValueError(f"Empty viewBox attribute: {abs_path}")

	# Check for <script> elements
	for elem in root.iter():
		if elem.tag.endswith("}script") or elem.tag == "script":
			raise ValueError(f"Found <script> element: {abs_path}")

	# Check for inline event handlers (on*)
	_check_no_event_handlers(root, abs_path)

	# Check SVG body is not empty (has at least one child)
	if len(root) == 0:
		raise ValueError(f"Empty <svg> body (no child elements): {abs_path}")

	return ValidationReport(ok=True, file_path=abs_path)


def _check_no_event_handlers(elem: object, svg_path: str) -> None:
	"""Recursively check element and children for on* attributes."""
	for key in elem.attrib.keys():
		if key.startswith("on"):
			raise ValueError(
				f"Found inline event handler '{key}' on <{elem.tag}>: {svg_path}"
			)

	for child in elem:
		_check_no_event_handlers(child, svg_path)


def _get_repo_root() -> str:
	"""Get repository root via git."""
	import subprocess

	try:
		result = subprocess.run(
			["git", "rev-parse", "--show-toplevel"],
			cwd=os.path.dirname(__file__),
			capture_output=True,
			text=True,
			timeout=5,
		)
		if result.returncode == 0:
			return result.stdout.strip()
	except Exception:
		pass

	raise RuntimeError("Could not determine repo root via git")
