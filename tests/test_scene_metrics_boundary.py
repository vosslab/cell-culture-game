# Standard Library
import ast
import pathlib

# PIP3 modules
import pytest
import yaml

# local repo modules
import file_utils
from validation.scene_calc.dump import MissingRenderEvidenceError
from validation.scene_calc.dump import dump_scene_geometry
from validation.shared_toolkit.yaml_io import load_yaml

REPORT_NAME = file_utils.report_name(__file__)

HEADER = "Scene metrics boundary report"

# Coordinate/bounds keys that only ever belong to rendered geometry (the
# dump), never to raw authored scene YAML. Authored YAML has no per-placement
# pixel coordinates; those are computed by the TS layout pipeline under
# src/scene_runtime/layout/ and surfaced only through
# validation.scene_calc.dump.dump_scene_geometry. Categorical YAML fields
# (zone, depth_tier, data-primary, object_name, etc.) are unaffected by this
# closed key set and stay readable directly off authored YAML.
COORDINATE_KEYS = frozenset({"x", "y", "w", "h", "bounds"})


#============================================
def _is_scene_design_or_calc(rel: str) -> bool:
	"""
	Keep only files under validation/scene_design/ or validation/scene_calc/.

	Args:
		rel: Repo-relative POSIX path.

	Returns:
		bool: True when the path is scoped to either package.
	"""
	return rel.startswith("validation/scene_design/") or rel.startswith("validation/scene_calc/")


FILES = file_utils.discover_files(
	extensions=(".py",),
	extra_filter=_is_scene_design_or_calc,
	test_key="scene_metrics_boundary",
)


#============================================
def _yaml_loaded_names(tree: ast.Module) -> set:
	"""
	Collect variable names assigned directly from a load_yaml(...) call.

	Only simple `name = load_yaml(...)` assignments are tracked (module or
	function scope, flattened via ast.walk). This is a narrow, file-local
	check: it does not follow the variable across function boundaries or
	track re-assignment, by design (see docs/PYTEST_STYLE.md "narrow AST
	guard").

	Args:
		tree: Parsed ast.Module for the file.

	Returns:
		set: Names assigned directly from a load_yaml(...) call.
	"""
	names = set()
	for node in ast.walk(tree):
		if not isinstance(node, ast.Assign):
			continue
		if not isinstance(node.value, ast.Call):
			continue
		func = node.value.func
		# Match either `load_yaml(...)` or `module.load_yaml(...)`.
		is_load_yaml = isinstance(func, ast.Name) and func.id == "load_yaml"
		is_load_yaml = is_load_yaml or (
			isinstance(func, ast.Attribute) and func.attr == "load_yaml"
		)
		if not is_load_yaml:
			continue
		for target in node.targets:
			if isinstance(target, ast.Name):
				names.add(target.id)
	return names


#============================================
def _coordinate_subscript_violations(rel: str, tree: ast.Module) -> list:
	"""
	Return violation lines for coordinate-key subscripts on YAML-loaded vars.

	Flags `<yaml_var>[<coordinate_key>]` where <yaml_var> was assigned
	directly from load_yaml(...) in the same file. This guards against
	scene_design/scene_calc re-deriving layout geometry from raw authored
	YAML instead of reading it from the rendered dump (see
	docs/archive/decisions/scene_calc_validator_follows_generator.md).

	Args:
		rel: Repo-relative POSIX path for error messages.
		tree: Parsed ast.Module for the file.

	Returns:
		list[str]: Violation lines (empty when the file is clean).
	"""
	yaml_names = _yaml_loaded_names(tree)
	issues = []
	for node in ast.walk(tree):
		if not isinstance(node, ast.Subscript):
			continue
		if not isinstance(node.value, ast.Name):
			continue
		if node.value.id not in yaml_names:
			continue
		key = node.slice
		if not (isinstance(key, ast.Constant) and isinstance(key.value, str)):
			continue
		if key.value not in COORDINATE_KEYS:
			continue
		line_no = getattr(node, "lineno", 0) or 0
		issues.append(
			f"{rel}:{line_no}: coordinate-key subscript '{key.value}' on YAML-loaded "
			f"var '{node.value.id}'; read geometry from dump_scene_geometry instead"
		)
	return sorted(set(issues))


#============================================
def _layout_import_violations(rel: str, tree: ast.Module) -> list:
	"""
	Return violation lines for any import naming a layout-engine module.

	Flags an import whose module path contains "layout" (case-insensitive).
	This is the Python-side proxy for the src/scene_runtime/layout/ boundary:
	scene_design/scene_calc must consume rendered geometry only through
	validation.scene_calc.dump; importing a layout-computing module (whether a
	shim over src/scene_runtime/layout/ or a new Python re-implementation)
	would reintroduce the retired shadow layout model.

	Args:
		rel: Repo-relative POSIX path for error messages.
		tree: Parsed ast.Module for the file.

	Returns:
		list[str]: Violation lines (empty when the file is clean).
	"""
	issues = []
	for node in file_utils.iter_imports(tree):
		if isinstance(node, ast.Import):
			module_names = [alias.name for alias in node.names]
		else:
			module_names = [node.module or ""]
		for module_name in module_names:
			if "layout" in module_name.lower():
				line_no = getattr(node, "lineno", 0) or 0
				issues.append(f"{rel}:{line_no}: layout-engine import '{module_name}'")
	return sorted(set(issues))


#============================================
def check_file(rel: str, tree: ast.Module) -> list:
	"""
	Combine the two narrow boundary checks for one file.

	Args:
		rel: Repo-relative POSIX path.
		tree: Parsed ast.Module for the file.

	Returns:
		list[str]: Combined violation lines (empty when the file is clean).
	"""
	return _layout_import_violations(rel, tree) + _coordinate_subscript_violations(rel, tree)


# Module-level dict of repo-relative POSIX key -> list of violation lines.
# Populated by the autouse collect_report fixture before any test runs.
VIOLATIONS_BY_FILE: dict[str, list[str]] = {}


#============================================
@pytest.fixture(scope="module", autouse=True)
def collect_report() -> None:
	"""Clear stale reports, populate VIOLATIONS_BY_FILE, write report on failure."""
	file_utils.clear_stale_reports()
	VIOLATIONS_BY_FILE.clear()
	VIOLATIONS_BY_FILE.update(file_utils.collect_python_violations(FILES, check_file))
	lines = file_utils.format_violation_report(HEADER, VIOLATIONS_BY_FILE)
	if lines:
		file_utils.write_report_lines(REPORT_NAME, lines)


#============================================
@pytest.mark.parametrize("path", FILES, ids=file_utils.rel_id)
def test_no_layout_import_or_yaml_coordinate_subscript(path: str) -> None:
	"""Enforce no layout-engine import and no coordinate subscript on raw YAML."""
	rel = file_utils.rel_to_root(path)
	assert rel not in VIOLATIONS_BY_FILE, file_utils.format_violation_assert_message(
		rel, VIOLATIONS_BY_FILE.get(rel, []), REPORT_NAME
	)


#============================================
def test_dump_scene_geometry_raises_on_missing_render(tmp_path) -> None:
	"""
	dump_scene_geometry is the only geometry source and fails loudly when a
	scene has never been rendered (no stats.json under
	generated/scene_render_stats/), rather than synthesizing geometry.

	Loads a REAL base scene's authored YAML (content/base_scenes/
	electrophoresis_bench.yaml) so the scene structure under test is genuine
	authored content, then replays that exact dict into an isolated fake repo
	root under tmp_path. tmp_path has no generated/scene_render_stats/ entry
	for this scene, so the loader must hit the missing-stats branch. This
	keeps the test self-contained (no fixture files, per NO_FIXTURE_POLICY)
	while never touching the real repo's generated/ tree.
	"""
	repo_root = pathlib.Path(file_utils.get_repo_root())
	real_scene_path = repo_root / "content" / "base_scenes" / "electrophoresis_bench.yaml"
	real_scene = load_yaml(real_scene_path)

	# Fake a minimal repo root so _find_repo_root resolves inside tmp_path,
	# keeping this test isolated from the real repo's generated/ tree.
	(tmp_path / "AGENTS.md").write_text("# fake repo root for boundary test\n")
	scene_path = tmp_path / "electrophoresis_bench.yaml"
	scene_path.write_text(yaml.safe_dump(real_scene))

	with pytest.raises(MissingRenderEvidenceError):
		dump_scene_geometry(scene_path)
