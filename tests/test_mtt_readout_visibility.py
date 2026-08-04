"""Behavior checks for the visible representative MTT result display."""

from pathlib import Path

import yaml
import lxml.etree


REPO_ROOT = Path(__file__).resolve().parents[1]
READOUT_DIR = REPO_ROOT / "content" / "protocols" / "cell_culture" / "mtt_solubilization_readout"
PLATE_READER = REPO_ROOT / "content" / "objects" / "equipment" / "plate_reader.yaml"
ASSET_DIR = REPO_ROOT / "assets" / "equipment" / "static"


def load_yaml(path: Path) -> dict:
	"""Load one authored YAML file for the MTT readout behavior checks."""
	with path.open(encoding="utf-8") as handle:
		contents = yaml.safe_load(handle)
	return contents


def svg_words(asset_name: str) -> str:
	"""Return the visible SVG text for a result panel, normalized for matching."""
	tree = lxml.etree.parse(str(ASSET_DIR / asset_name))
	words = " ".join(text.strip() for text in tree.getroot().itertext() if text.strip())
	return words


def test_mtt_readout_exposes_the_interpretation_evidence() -> None:
	"""The completed reading shows blank, control, dose series, and combination data."""
	protocol = load_yaml(READOUT_DIR / "protocol.yaml")
	reader = load_yaml(PLATE_READER)
	read_step = next(step for step in protocol["steps"] if step["step_name"] == "read_absorbance")
	complete_read = read_step["sequence"][-1]
	reader_write = next(
		op["state"]
		for op in complete_read["response"]["scene_operations"]
		if op["type"] == "ObjectStateChange" and op["target"] == "plate_reader"
	)

	assert read_step["sequence"][1]["validator"]["value"]["wavelength_nm"] == 560
	assert reader_write["result_state"] == "results_ready"
	assert reader_write["mean_absorbance"] == 0.20
	assert reader_write["normalized_viability_percent"] == 22
	assert "Representative simulated" in complete_read["response"]["feedback"]["correct"]
	assert complete_read["response"]["scene_operations"][-1] == {
		"type": "SceneChange",
		"to_scene": "mtt_solubilization_readout_result_review",
	}

	result_panels = reader["visual_states"]["result_state"]["cases"]
	result_assets = {
		component["asset_name"]
		for case in result_panels
		for component in case["output"].get("composite", [])
	}
	assert "plate_reader_absorbance_result_panel" in result_assets
	assert "plate_reader_normalized_viability_panel" in result_assets

	monitor_words = svg_words("mtt_reader_results_display.svg")
	for required_word in (
		"Blank/background",
		"Untreated control",
		"Carboplatin (uM)",
		"Viability (%)",
		"10 uM carboplatin",
		"metformin",
	):
		assert required_word in monitor_words
