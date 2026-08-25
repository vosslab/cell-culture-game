#!/usr/bin/env python3
"""End-to-end test: scene_design CLI dump_data wiring + graceful degradation.

Whole-CLI invocation via subprocess; coupled to real content/base_scenes/*.yaml
fixtures and to the dump pipeline's filesystem layout. Belongs in tests/e2e/
per docs/E2E_TESTS.md (excluded from `pytest tests/`).

Run directly:
	bash -c 'source source_me.sh && python3 tests/e2e/e2e_scene_design_cli.py'
"""

import json
import subprocess
import sys
from pathlib import Path


def test_scene_design_cli_populates_metrics_with_dump() -> None:
	"""scene_design CLI populates metrics with non-None values on successful dump."""
	scene_path = Path('content/base_scenes/bench_basic.yaml')
	if not scene_path.exists():
		raise FileNotFoundError(f'{scene_path} not found; run from repo root')

	result = subprocess.run(
		[sys.executable, '-m', 'validation.scene_design.cli', '-S', str(scene_path), '--json'],
		capture_output=True,
		text=True,
	)

	assert result.returncode == 0, f'CLI failed: {result.stderr}'
	assert result.stdout, 'CLI produced no output'

	# --json emits a single {"cards":[...]} document, not JSONL.
	document = json.loads(result.stdout)
	card = document['cards'][0]
	metrics = card['metrics']

	# depth_tier_usage is YAML-only and should always populate.
	assert metrics['depth_tier_usage'] is not None

	# At least one dump-consuming metric should also populate.
	dump_consuming = [
		'predicted_label_overlap', 'label_to_object_distance', 'label_wrap_rate',
		'scene_density', 'tab_stops_symmetry', 'aspect_fidelity',
	]
	assert any(metrics.get(m) is not None for m in dump_consuming)


if __name__ == '__main__':
	test_scene_design_cli_populates_metrics_with_dump()
	print('All tests passed.')
