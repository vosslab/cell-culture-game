"""Behavioral tests for behavior-organized SVG picker destinations."""

from pathlib import Path

from tools.svg_picker.apply_decisions import run_preflight, target_path


def _decision(**overrides: object) -> dict:
	decision = {
		"asset_name": "new_device",
		"state": "assigned",
		"behavior_category": "binary_state",
		"candidate_id": "candidate-1",
		"source_repo": "OTHER_REPOS/example",
		"source_path": "candidate.svg",
		"license_tag": "CC0",
	}
	decision.update(overrides)
	return decision


def test_picker_target_path_includes_behavior_category(tmp_path: Path) -> None:
	assert target_path(tmp_path, _decision()).relative_to(tmp_path) == Path(
		"assets/equipment/binary_state/new_device.svg"
	)


def test_picker_preflight_rejects_missing_behavior_category(tmp_path: Path) -> None:
	(tmp_path / "assets").mkdir()
	(tmp_path / "candidate.svg").write_text(
		'<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8",
	)
	decision = _decision()
	del decision["behavior_category"]
	errors = run_preflight(
		[decision],
		{"candidate-1": {"rel_path": "candidate.svg"}},
		{"force": False, "rename_existing": False},
		tmp_path,
	)
	assert errors == [
		"Decision 0: state='assigned' requires key 'behavior_category'",
	]
