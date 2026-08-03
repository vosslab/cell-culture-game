#!/usr/bin/env python3
"""End-to-end check for the generated object_library.ts artifact.

Lives in tests/e2e/ because it reads a GENERATED build artifact
(generated/object_library.ts) rather than walking source YAML. Reading a
generated file in the pytest fast lane is a stale-file risk: the assertion can
pass or fail based on whether the generator was last run, not on current source.
Per docs/E2E_TESTS.md and docs/PYTEST_STYLE.md, artifact round-trip checks belong
here, not in `pytest tests/`. The fast YAML-walk behavioral tests stay in
tests/test_object_library_visual_states.py.

This verifies the generator -> generated module round trip across both sides of
the material cutover. A static pipette keeps its held-volume state but declares
that amount explicitly nonvisual, while the variable-volume serological pipette
keeps the compiled fill-height binding.

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

def load_generated_objects(repo_root: str) -> dict:
	"""Load representative generated objects through the runtime TypeScript loader."""
	generated_path = os.path.join(repo_root, "generated", "object_library.ts")
	loader_script = (
		"import { pathToFileURL } from 'node:url'; "
		"const module = await import(pathToFileURL(process.argv[1]).href); "
		"const objects = module.OBJECT_LIBRARY; "
		"console.log(JSON.stringify({ "
		"aspirating_pipette: objects.aspirating_pipette, "
		"serological_pipette: objects.serological_pipette }));"
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

def check_static_amount_state_is_nonvisual(objects: dict) -> None:
	"""Assert a static form keeps amount state without receiving a liquid renderer."""
	pipette = objects["aspirating_pipette"]
	volume_state = pipette["visual_states"]["held_material_volume"]
	assert "held_material_volume" in pipette["state_schema"]
	assert volume_state["kind"] == "composite" and "render_effect" not in volume_state


#============================================

def check_variable_amount_state_uses_compiled_fill(objects: dict) -> None:
	"""Assert a material form retains the generated variable-volume binding."""
	pipette = objects["serological_pipette"]
	volume_state = pipette["visual_states"]["held_material_volume"]
	assert (
		volume_state["render_effect"],
		volume_state["target"],
		volume_state["clip"],
	) == ("fill_height", "anchor_liquid_bounds", "anchor_liquid_clip")
	assert volume_state["capacity_ml"] == pipette["state_schema"]["held_material_volume"]["max"]


#============================================

def main() -> None:
	repo_root = file_utils.get_repo_root()
	objects = load_generated_objects(repo_root)
	check_static_amount_state_is_nonvisual(objects)
	check_variable_amount_state_uses_compiled_fill(objects)
	print("PASS: generated/object_library.ts preserves static and variable material contracts")


if __name__ == "__main__":
	main()
