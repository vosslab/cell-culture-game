"""Post-cutover anti-return gate for semantic in-SVG liquid rendering.

This is intentionally a small repository lint rather than a second renderer
validator.  The SVG validator owns semantic structure; the taxonomy validator
owns the object-to-form binding.  This module composes those existing
authoritative checks and adds the one source-boundary check that neither can
express: runtime material code must consume generated handles, never recreate
the retired object-level rectangle overlay.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import lxml.etree

from validation.svg.asset_registry import build_svg_asset_registry
from validation.svg.asset_taxonomy_validator import AssetTaxonomyValidationError, validate_asset_taxonomy
from validation.svg.layer_recipe_validator import (
	MaterialSvgValidationError,
	validate_material_svg,
	validate_reserved_attributes,
)


class MaterialAntiReturnLintError(ValueError):
	"""Raised when retired material-overlay behavior is found."""


_TYPE_SCRIPT_SUFFIXES = frozenset({".ts", ".tsx"})
_DIRECT_SEMANTIC_ACCESS = re.compile(r"data-vlab-[A-Za-z0-9_-]+")
_AUTHORED_SEMANTIC_ID = re.compile(r"['\"](?:liquid_[a-z0-9_]+|fixed_(?:back|front))['\"]")
_SEMANTIC_QUERY = re.compile(
	r"(?:querySelector(?:All)?|getElementById|getAttribute)\s*\([^\n;]*(?:data-vlab-|liquid_(?:bottom|body|surface)|anchor_liquid_)",
)
_RECT_CREATION = re.compile(
	r"(?:createElement|createElementNS)\s*\([^\n;]*['\"]rect['\"]",
)
_JSX_RECT = re.compile(r"<rect\b")
_STRUCTURED_RECT_ALLOWLIST = frozenset({
	"scene_runtime/renderer/subpart_hit_surface.tsx",
	"scene_runtime/renderer/subpart_visual_state_renderer.tsx",
})


def _display_path(path: Path, repo_root: Path) -> str:
	try:
		return path.relative_to(repo_root).as_posix()
	except ValueError:
		return path.as_posix()


def _lint_svg_contracts(repo_root: Path, assets_dir: Path, objects_dir: Path) -> list[str]:
	"""Apply source semantic and object-binding gates with rule-labelled errors."""
	violations: list[str] = []
	parser = lxml.etree.XMLParser(resolve_entities=False, no_network=True)
	try:
		registry = build_svg_asset_registry(assets_dir)
	except Exception as exc:  # Registry error text already gives both offending paths.
		return [f"M7-REGISTRY: {_display_path(assets_dir, repo_root)}: {exc}"]

	for entry in registry.entries:
		path = entry.source_path
		try:
			root = lxml.etree.parse(str(path), parser).getroot()
			is_material = validate_reserved_attributes(root)
			if is_material:
				validate_material_svg(root)
		except (lxml.etree.XMLSyntaxError, MaterialSvgValidationError) as exc:
			violations.append(f"M7-SVG-SEMANTICS: {_display_path(path, repo_root)}: {exc}")

	try:
		validate_asset_taxonomy(assets_dir, objects_dir)
	except AssetTaxonomyValidationError as exc:
		violations.append(f"M7-OBJECT-BINDING: {_display_path(objects_dir, repo_root)}: {exc}")
	return violations


def _lint_source_tree(repo_root: Path, source_dir: Path) -> list[str]:
	"""Reject overlay recreation and authored-semantic DOM access anywhere in ``src/``."""
	violations: list[str] = []
	legacy_renderer = source_dir / "scene_runtime" / "renderer" / "anchor_material_renderer.ts"
	if legacy_renderer.exists():
		violations.append(
			f"M7-RETIRED-OVERLAY: {_display_path(legacy_renderer, repo_root)}: "
			"retired anchor_material_renderer.ts must not return"
		)

	for path in sorted(source_dir.rglob("*")):
		if path.suffix not in _TYPE_SCRIPT_SUFFIXES:
			continue
		text = path.read_text(encoding="utf-8")
		shown = _display_path(path, repo_root)
		if "anchor_material_renderer" in text:
			violations.append(
				f"M7-RETIRED-OVERLAY: {shown}: retired anchor_material_renderer import or token"
			)
		if _DIRECT_SEMANTIC_ACCESS.search(text) is not None:
			violations.append(
				f"M7-GENERATED-HANDLES: {shown}: source reads authored data-vlab-* semantics"
			)
		if _AUTHORED_SEMANTIC_ID.search(text) is not None:
			violations.append(
				f"M7-GENERATED-HANDLES: {shown}: source constructs an authored semantic id"
			)
		if _SEMANTIC_QUERY.search(text) is not None:
			violations.append(
				f"M7-GENERATED-HANDLES: {shown}: source queries an authored semantic id or selector"
			)
		relative_to_source = path.relative_to(source_dir).as_posix()
		if (
			relative_to_source not in _STRUCTURED_RECT_ALLOWLIST
			and (_RECT_CREATION.search(text) is not None or _JSX_RECT.search(text) is not None)
		):
			violations.append(
				f"M7-RETIRED-OVERLAY: {shown}: source creates an unapproved SVG rect overlay"
			)
	return violations


def lint_material_anti_return(
	repo_root: Path,
	*,
	assets_dir: Path | None = None,
	objects_dir: Path | None = None,
	source_dir: Path | None = None,
) -> None:
	"""Fail closed if semantic liquid rendering regresses after the cutover.

	The optional paths make deliberate reintroduction tests fully isolated in a
	``tmp_path`` tree.  Production callers pass only the repository root.
	"""
	repo_root = repo_root.resolve()
	assets_dir = (assets_dir or repo_root / "assets").resolve()
	objects_dir = (objects_dir or repo_root / "content" / "objects").resolve()
	source_dir = (source_dir or repo_root / "src").resolve()
	violations = _lint_svg_contracts(repo_root, assets_dir, objects_dir)
	violations.extend(_lint_source_tree(repo_root, source_dir))
	if violations:
		raise MaterialAntiReturnLintError("\n".join(violations))


def main(argv: list[str] | None = None) -> int:
	"""Run the post-cutover gate as the build's narrow validation front door."""
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument(
		"--repo-root",
		type=Path,
		default=Path.cwd(),
		help="repository root to validate (default: current directory)",
	)
	args = parser.parse_args(argv)
	try:
		lint_material_anti_return(args.repo_root)
	except MaterialAntiReturnLintError as exc:
		print(exc, file=sys.stderr)
		return 1
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
