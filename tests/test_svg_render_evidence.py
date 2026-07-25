"""Regression tests for SVG visual E2E browser-evidence gates."""

# Standard Library
import sys
import types
import importlib.util
from pathlib import Path

# PIP3 modules
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
E2E_SCRIPTS = [
	REPO_ROOT / "tests" / "e2e" / "e2e_svg_gradient_recheck.py",
	REPO_ROOT / "tests" / "e2e" / "e2e_svg_visual_regression.py",
]


#============================================
def load_e2e_script(script_path: Path) -> types.ModuleType:
	"""Load one executable E2E script without invoking its main entry point.

	Args:
		script_path: Absolute path to the E2E script.

	Returns:
		Loaded module exposing the browser-evidence gate.
	"""
	module_name = f"svg_evidence_{script_path.stem}"
	spec = importlib.util.spec_from_file_location(module_name, script_path)
	if spec is None or spec.loader is None:
		raise RuntimeError(f"Could not load E2E script: {script_path}")
	module = importlib.util.module_from_spec(spec)
	sys.modules[module_name] = module
	spec.loader.exec_module(module)
	return module


#============================================
@pytest.mark.parametrize("script_path", E2E_SCRIPTS)
def test_svg_e2e_rejects_missing_browser_evidence(script_path: Path, tmp_path: Path) -> None:
	"""A zero-result browser run cannot be reported as a successful E2E."""
	module = load_e2e_script(script_path)
	manifest = [{"output_png": str(tmp_path / "missing.png")}]
	with pytest.raises(RuntimeError, match="Incomplete render evidence"):
		module.require_render_evidence(manifest, {}, "chromium")
