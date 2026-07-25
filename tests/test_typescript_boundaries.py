"""
Boundary lint for Solid.js import restrictions.

Solid import boundary (from plan refactored-drifting-narwhal.md, M1/WS-M1-B):

  Solid ALLOWED:    src/shell/, src/scene_runtime/renderer/,
                    src/scene_runtime/state/

  Solid FORBIDDEN:  src/scene_runtime/layout/, pipeline/, validation/,
                    generated/, src/scene_runtime/protocol/
                    (the stepper; type-only imports from state permitted).

The stepper (protocol/) calls store operations through a small runtime bridge,
never as a Solid component dependency. Type-only imports (import type ...) of
Solid types from the state layer into protocol/ are explicitly allowed.

Additional boundary rules:
  - No src/shell/ or src/launcher/ imported in scene_runtime/layout/ or
    scene_runtime/renderer/ (shell/adapter/types is the seam exception).

Approach: scan every .ts/.tsx file in the protected directories, extract
imports, and assert no violations. A negative test creates a known-bad fixture,
asserts it would be caught, then cleans up.
"""

import os
import re

# PIP3 modules
import pytest

# local repo modules
import file_utils


#============================================
def _resolve_repo_root() -> str:
	"""
	Resolve the repository root.

	Delegates to the propagated shared helper (tests/file_utils.py), the
	same resolver other tests use, instead of re-implementing the git rev-parse
	subprocess call here.

	Returns:
		str: Absolute path to repository root.
	"""
	return file_utils.get_repo_root()


#============================================
def _read_marker() -> str:
	"""
	Read REPO_TYPE marker from repository root.

	Returns:
		str: Marker token (e.g., "typescript"), or None if missing.
	"""
	repo_root = _resolve_repo_root()
	marker_path = os.path.join(repo_root, "REPO_TYPE")
	if not os.path.exists(marker_path):
		return None
	with open(marker_path, "r", encoding="utf-8") as handle:
		content = handle.read().strip()
	return content if content else None


#============================================
def _extract_imports(file_content: str) -> list[str]:
	"""
	Extract all import paths from TypeScript/TSX file content.

	Matches patterns like:
	  import { x } from "path"
	  import x from 'path'
	  import * as x from "path"
	  import type { T } from "path"

	Args:
		file_content: Raw TypeScript/TSX source code

	Returns:
		List of import paths (the string inside quotes)
	"""
	# Match import statements (including type-only) with any quote style
	pattern = r'import\s+(?:type\s+)?(?:\{[^}]*\}|[\w\s*,]+)\s+from\s+["\']([^"\']+)["\']'
	matches = re.findall(pattern, file_content)
	return matches


#============================================
def _extract_type_only_imports(file_content: str) -> list[str]:
	"""
	Extract only type-only import paths (import type ... from ...).

	Args:
		file_content: Raw TypeScript/TSX source code

	Returns:
		List of import paths that are type-only imports
	"""
	# Match only "import type { ... } from '...'" forms
	pattern = r'import\s+type\s+(?:\{[^}]*\}|[\w\s*,]+)\s+from\s+["\']([^"\']+)["\']'
	matches = re.findall(pattern, file_content)
	return matches


#============================================
def _is_solid_import(import_path: str) -> bool:
	"""
	Return True if import_path is a solid-js import.

	Args:
		import_path: The import string (e.g., "solid-js", "solid-js/store")

	Returns:
		True if this is a solid-js or solid-js/* import
	"""
	return import_path == "solid-js" or import_path.startswith("solid-js/")


#============================================
def _check_import_violation(import_path: str) -> str | None:
	"""
	Check if a single import violates the boundary rules for layout/ and renderer/.

	Rule 1: no 'solid-js' or 'solid-js/*'
	Rule 2: no absolute or relative paths resolving to src/shell/ or src/launcher/

	Args:
		import_path: The import string (e.g., "solid-js", "./../../shell/foo")

	Returns:
		Violation reason string if violated, None if OK.
	"""
	# Rule 1: Reject solid-js and solid-js subpaths
	if _is_solid_import(import_path):
		return f"forbidden solid-js import: {import_path}"

	# Rule 2: Reject relative/absolute paths pointing to shell/ or launcher/.
	# Exception: src/shell/adapter/types is the typed seam contract; the
	# protocol runtime imports it deliberately. Type-only imports stay
	# free of any runtime dependency.
	is_seam_types = (
		"shell/adapter/types" in import_path
		or import_path.endswith("/shell/adapter/types")
	)
	if not is_seam_types:
		if "/shell/" in import_path or import_path.endswith("/shell"):
			return f"forbidden shell import: {import_path}"
	if "/launcher/" in import_path or import_path.endswith("/launcher"):
		return f"forbidden launcher import: {import_path}"

	return None


#============================================
def _check_solid_violation_strict(import_path: str) -> str | None:
	"""
	Check if an import is a forbidden solid-js import (strict: no exceptions).

	Used for pipeline/, validation/, generated/, and layout/ directories
	where solid-js is never allowed.

	Args:
		import_path: The import string

	Returns:
		Violation reason string if violated, None if OK.
	"""
	if _is_solid_import(import_path):
		return f"forbidden solid-js import: {import_path}"
	return None


#============================================
def _check_solid_violation_protocol(
	import_path: str,
	is_type_only: bool,
) -> str | None:
	"""
	Check if an import violates the solid-js rule for the protocol/ stepper.

	The stepper (protocol/) must not depend on solid-js as a runtime import.
	Type-only imports of Solid types (import type ...) from the state layer
	are explicitly permitted so the stepper can reference state types.

	Args:
		import_path: The import string
		is_type_only: True if this import is an 'import type' statement

	Returns:
		Violation reason string if violated, None if OK.
	"""
	if not _is_solid_import(import_path):
		return None
	# Type-only imports are allowed in protocol/ (for state type references)
	if is_type_only:
		return None
	return f"forbidden runtime solid-js import in protocol/: {import_path}"


#============================================
def _scan_directory_for_violations(
	directory: str,
	repo_root: str,
) -> list[tuple[str, str]]:
	"""
	Scan a directory for .ts/.tsx files and check for import violations.

	Applies the layout/renderer boundary rules (both solid-js and shell/launcher).

	Args:
		directory: Path to scan (e.g., src/scene_runtime/layout/)
		repo_root: Repository root for absolute path handling

	Returns:
		List of (filepath, violation_reason) tuples for files with violations
	"""
	violations: list[tuple[str, str]] = []

	# Walk all .ts and .tsx files in the directory
	for root, _dirs, files in os.walk(directory):
		for filename in files:
			if not (filename.endswith(".ts") or filename.endswith(".tsx")):
				continue

			filepath = os.path.join(root, filename)
			rel_path = os.path.relpath(filepath, repo_root)

			try:
				with open(filepath, "r", encoding="utf-8") as handle:
					content = handle.read()
			except OSError as err:
				violations.append((rel_path, f"read error: {err}"))
				continue

			imports = _extract_imports(content)
			for imp in imports:
				violation = _check_import_violation(imp)
				if violation:
					violations.append((rel_path, violation))

	return violations


#============================================
def _scan_directory_for_solid_violations_strict(
	directory: str,
	repo_root: str,
) -> list[tuple[str, str]]:
	"""
	Scan a directory for solid-js imports (strict: no type-only exception).

	Used for pipeline/, validation/, generated/ where solid-js is never allowed
	regardless of import form.

	Args:
		directory: Path to scan
		repo_root: Repository root

	Returns:
		List of (filepath, violation_reason) tuples
	"""
	violations: list[tuple[str, str]] = []

	for root, _dirs, files in os.walk(directory):
		for filename in files:
			if not (filename.endswith(".ts") or filename.endswith(".tsx")):
				continue

			filepath = os.path.join(root, filename)
			rel_path = os.path.relpath(filepath, repo_root)

			try:
				with open(filepath, "r", encoding="utf-8") as handle:
					content = handle.read()
			except OSError as err:
				violations.append((rel_path, f"read error: {err}"))
				continue

			imports = _extract_imports(content)
			for imp in imports:
				violation = _check_solid_violation_strict(imp)
				if violation:
					violations.append((rel_path, violation))

	return violations


#============================================
def _scan_protocol_directory_for_solid_violations(
	directory: str,
	repo_root: str,
) -> list[tuple[str, str]]:
	"""
	Scan the protocol/ directory for forbidden solid-js imports.

	Type-only imports of solid-js types are permitted (for state type references).
	Runtime solid-js imports are forbidden.

	Args:
		directory: Path to the protocol/ directory
		repo_root: Repository root

	Returns:
		List of (filepath, violation_reason) tuples
	"""
	violations: list[tuple[str, str]] = []

	for root, _dirs, files in os.walk(directory):
		for filename in files:
			if not (filename.endswith(".ts") or filename.endswith(".tsx")):
				continue

			filepath = os.path.join(root, filename)
			rel_path = os.path.relpath(filepath, repo_root)

			try:
				with open(filepath, "r", encoding="utf-8") as handle:
					content = handle.read()
			except OSError as err:
				violations.append((rel_path, f"read error: {err}"))
				continue

			# Gather type-only imports separately so we can exempt them
			type_only_imports = set(_extract_type_only_imports(content))
			all_imports = _extract_imports(content)

			for imp in all_imports:
				is_type_only = imp in type_only_imports
				violation = _check_solid_violation_protocol(imp, is_type_only)
				if violation:
					violations.append((rel_path, violation))

	return violations


#============================================
def test_no_solid_js_in_layout() -> None:
	"""
	Solid.js is FORBIDDEN in src/scene_runtime/layout/.

	The layout engine is a pure pipeline that must not depend on the
	reactive framework. Solid owns rendering; the layout engine owns geometry.
	"""
	import pytest

	marker = _read_marker()
	repo_root = _resolve_repo_root()

	if marker != "typescript":
		pytest.skip("repo is not typescript-typed")

	layout_dir = os.path.join(repo_root, "src", "scene_runtime", "layout")

	violations: list[tuple[str, str]] = []

	# Only check if the directory exists; absence is not a failure
	if os.path.isdir(layout_dir):
		violations.extend(
			_scan_directory_for_solid_violations_strict(layout_dir, repo_root)
		)

	if violations:
		msg_lines = ["Solid.js boundary lint violations in layout/:"]
		for filepath, reason in violations:
			msg_lines.append(f"  {filepath}: {reason}")
		raise AssertionError("\n".join(msg_lines))


#============================================
def test_no_solid_js_in_pipeline() -> None:
	"""
	Solid.js is FORBIDDEN in pipeline/.

	The build pipeline emits generated data; it must never depend on the
	reactive framework.
	"""
	import pytest

	marker = _read_marker()
	repo_root = _resolve_repo_root()

	if marker != "typescript":
		pytest.skip("repo is not typescript-typed")

	pipeline_dir = os.path.join(repo_root, "pipeline")

	violations: list[tuple[str, str]] = []

	# Only check if the directory exists; absence is not a failure
	if os.path.isdir(pipeline_dir):
		violations.extend(
			_scan_directory_for_solid_violations_strict(pipeline_dir, repo_root)
		)

	if violations:
		msg_lines = ["Solid.js boundary lint violations in pipeline/:"]
		for filepath, reason in violations:
			msg_lines.append(f"  {filepath}: {reason}")
		raise AssertionError("\n".join(msg_lines))


#============================================
def test_no_solid_js_in_validation() -> None:
	"""
	Solid.js is FORBIDDEN in validation/.

	YAML validators and protocol stepper simulation are pure Python/TS;
	they must not depend on the reactive framework.
	"""
	import pytest

	marker = _read_marker()
	repo_root = _resolve_repo_root()

	if marker != "typescript":
		pytest.skip("repo is not typescript-typed")

	validation_dir = os.path.join(repo_root, "validation")

	violations: list[tuple[str, str]] = []

	# Only check if the directory exists; absence is not a failure
	if os.path.isdir(validation_dir):
		violations.extend(
			_scan_directory_for_solid_violations_strict(validation_dir, repo_root)
		)

	if violations:
		msg_lines = ["Solid.js boundary lint violations in validation/:"]
		for filepath, reason in violations:
			msg_lines.append(f"  {filepath}: {reason}")
		raise AssertionError("\n".join(msg_lines))


#============================================
def test_no_solid_js_in_generated() -> None:
	"""
	Solid.js is FORBIDDEN in generated/.

	Generated data files carry YAML-compiled runtime data; they must not
	import Solid.js. If a generated file starts importing Solid, a pipeline
	generator has violated the layer boundary.
	"""
	import pytest

	marker = _read_marker()
	repo_root = _resolve_repo_root()

	if marker != "typescript":
		pytest.skip("repo is not typescript-typed")

	generated_dir = os.path.join(repo_root, "generated")

	violations: list[tuple[str, str]] = []

	# Only check if the directory exists; absence is not a failure
	if os.path.isdir(generated_dir):
		violations.extend(
			_scan_directory_for_solid_violations_strict(generated_dir, repo_root)
		)

	if violations:
		msg_lines = ["Solid.js boundary lint violations in generated/:"]
		for filepath, reason in violations:
			msg_lines.append(f"  {filepath}: {reason}")
		raise AssertionError("\n".join(msg_lines))


#============================================
def test_no_solid_js_runtime_import_in_protocol() -> None:
	"""
	Runtime solid-js imports are FORBIDDEN in src/scene_runtime/protocol/.

	The stepper (protocol/) calls store operations through a small runtime
	bridge, never as a Solid component dependency. Type-only imports of
	Solid types (import type ...) from the state layer are permitted so the
	stepper can reference state types without a runtime dependency.
	"""
	import pytest

	marker = _read_marker()
	repo_root = _resolve_repo_root()

	if marker != "typescript":
		pytest.skip("repo is not typescript-typed")

	protocol_dir = os.path.join(repo_root, "src", "scene_runtime", "protocol")

	violations: list[tuple[str, str]] = []

	# Only check if the directory exists; absence is not a failure
	if os.path.isdir(protocol_dir):
		violations.extend(
			_scan_protocol_directory_for_solid_violations(protocol_dir, repo_root)
		)

	if violations:
		msg_lines = [
			"Solid.js runtime boundary lint violations in src/scene_runtime/protocol/:",
			"(type-only imports are permitted; runtime imports are forbidden)",
		]
		for filepath, reason in violations:
			msg_lines.append(f"  {filepath}: {reason}")
		raise AssertionError("\n".join(msg_lines))


#============================================
def test_no_shell_launcher_in_scene_runtime() -> None:
	"""
	No src/shell/ or src/launcher/ import in scene_runtime/layout/.

	The layout engine must not depend on the shell or launcher layers.
	shell/adapter/types is the one permitted seam exception (typed contract).
	"""
	import pytest

	marker = _read_marker()
	repo_root = _resolve_repo_root()

	if marker != "typescript":
		pytest.skip("repo is not typescript-typed")

	layout_dir = os.path.join(repo_root, "src", "scene_runtime", "layout")

	violations: list[tuple[str, str]] = []

	if os.path.isdir(layout_dir):
		violations.extend(_scan_directory_for_violations(layout_dir, repo_root))

	if violations:
		msg_lines = ["Boundary lint violations found:"]
		for filepath, reason in violations:
			msg_lines.append(f"  {filepath}: {reason}")
		raise AssertionError("\n".join(msg_lines))


#============================================
def test_solid_boundary_distinguishes_runtime_and_type_imports() -> None:
	"""
	Verify runtime Solid imports fail while type-only protocol imports remain valid.
	"""
	marker = _read_marker()

	if marker != "typescript":
		pytest.skip("repo is not typescript-typed")

	runtime_violation = _check_solid_violation_protocol("solid-js", is_type_only=False)
	type_violation = _check_solid_violation_protocol("solid-js", is_type_only=True)
	assert (runtime_violation is not None, type_violation) == (True, None)


@pytest.mark.parametrize(
	("module_parts", "expected_violation"),
	[
		(("src", "shell", "hud", "protocol_hud"), True),
		(("src", "shell", "adapter", "types"), False),
		(("src", "launcher", "launcher"), True),
	],
)
def test_import_boundary_classifies_repo_modules(
	module_parts: tuple[str, ...],
	expected_violation: bool,
) -> None:
	"""
	Classify protected modules from paths anchored at the repository root.
	"""
	module_path = os.path.join(file_utils.get_repo_root(), *module_parts)
	actual_violation = _check_import_violation(module_path) is not None
	assert actual_violation is expected_violation
