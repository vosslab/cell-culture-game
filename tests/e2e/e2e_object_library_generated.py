#!/usr/bin/env python3
"""End-to-end check for the generated object_library.ts artifact.

Lives in tests/e2e/ because it reads a GENERATED build artifact
(generated/object_library.ts) rather than walking source YAML. Reading a
generated file in the pytest fast lane is a stale-file risk: the assertion can
pass or fail based on whether the generator was last run, not on current source.
Per docs/E2E_TESTS.md and docs/PYTEST_STYLE.md, artifact round-trip checks belong
here, not in `pytest tests/`. The fast YAML-walk behavioral tests stay in
tests/test_object_library_visual_states.py.

This verifies the generator -> generated module round trip: the emitted
aspirating_pipette must carry the declarative held-material volume contract and
its paired material identity state.

Usage:
	python3 tests/e2e/e2e_object_library_generated.py
Exits 0 on success, nonzero on first failure.
"""

import json
import os
import subprocess
import sys

# tests/file_utils.py is the shared repo-root helper. This e2e script runs
# standalone (not under pytest), so add tests/ to the path before importing it.
_TESTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _TESTS_DIR not in sys.path:
	sys.path.insert(0, _TESTS_DIR)

import file_utils


#============================================

def load_generated_aspirating_pipette(repo_root: str) -> dict:
	"""Load the generated module through the same TypeScript loader as runtime checks."""
	generated_path = os.path.join(repo_root, "generated", "object_library.ts")
	loader_script = (
		"import { pathToFileURL } from 'node:url'; "
		"const module = await import(pathToFileURL(process.argv[1]).href); "
		"console.log(JSON.stringify(module.OBJECT_LIBRARY.aspirating_pipette));"
	)
	result = subprocess.run(
		["node", "--import", "tsx", "--input-type=module", "-e", loader_script, generated_path],
		check=True,
		capture_output=True,
		cwd=repo_root,
		text=True,
	)
	return json.loads(result.stdout)


#============================================

def check_generated_visual_states(repo_root: str) -> None:
	"""Assert the generated pipette preserves the held-material render contract."""
	pipette = load_generated_aspirating_pipette(repo_root)
	volume_state = pipette["visual_states"]["held_material_volume"]
	identity_state = pipette["visual_states"]["held_material_name"]
	expected_volume_state = {
		"applies_to": "object",
		"render_effect": "fill_height",
		"target": "anchor_liquid_bounds",
		"clip": "anchor_liquid_clip",
		"capacity_ml": pipette["state_schema"]["held_material_volume"]["max"],
	}

	assert volume_state == expected_volume_state
	assert identity_state["kind"] == "svg" and identity_state["cases"]


#============================================

def main() -> None:
	repo_root = file_utils.get_repo_root()
	check_generated_visual_states(repo_root)
	print("PASS: generated/object_library.ts carries aspirating_pipette visual_states")


if __name__ == "__main__":
	main()
