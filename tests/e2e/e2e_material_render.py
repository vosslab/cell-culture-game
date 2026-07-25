#!/usr/bin/env python3
"""Capture and guard current protocol-host material rendering.

The authoritative material registry belongs to the protocol host. This E2E
therefore captures each emitted protocol's initial authored scene through its
own host page, not through ``scene_viewer.html`` (which intentionally has no
active registry). The companion browser script records generic anchor, legacy
bbox, and structured-subpart surfaces without naming an object or material.

For each visibly painted surface it stores a before/after screenshot pair with
only that one surface hidden. Pixel diff measures painted footprint within the
surface's rendered geometry. It is evidence for initial authored states; real
walkers remain the evidence for protocol-driven post-interaction transitions.

Run:
  source source_me.sh && python3 tests/e2e/e2e_material_render.py --write-baseline
  source source_me.sh && python3 tests/e2e/e2e_material_render.py
"""

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy
import PIL.Image

from tests import file_utils

REPO_ROOT = Path(file_utils.get_repo_root())
CAPTURE_MJS = REPO_ROOT / "tests" / "playwright" / "material_render_capture.mjs"
CAPTURE_OUT_DIR = REPO_ROOT / "test-results" / "material_render"
REPORTS_DIR = REPO_ROOT / "docs" / "active_plans" / "reports"
JSON_BASELINE = REPORTS_DIR / "material_render.json"
MD_REPORT = REPORTS_DIR / "material_render.md"
CAPTURE_SCHEMA = "protocol-host-material-surfaces-v2"
BASELINE_SCHEMA = "protocol-host-material-baseline-v2"
DIFF_THRESHOLD = 15
REGRESSION_THRESHOLD_PP = 5.0
GEOMETRY_TOLERANCE_PP = 1.0


#============================================
def parse_args() -> argparse.Namespace:
	"""Parse command-line arguments."""
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument(
		"-w",
		"--write-baseline",
		dest="write_baseline",
		action="store_true",
		help="Write a fresh protocol-host material baseline.",
	)
	args = parser.parse_args()
	return args


#============================================
def run_capture(out_dir: Path) -> dict:
	"""Run browser capture and return its structured payload.

	Args:
		out_dir: Directory that receives screenshots and capture.json.

	Returns:
		Capture payload written by material_render_capture.mjs.
	"""
	out_dir.mkdir(parents=True, exist_ok=True)
	command = ["node", "--import", "tsx", str(CAPTURE_MJS), str(out_dir)]
	result = subprocess.run(command, cwd=str(REPO_ROOT), check=False)
	if result.returncode != 0:
		raise RuntimeError(
			"material_render_capture.mjs failed; rebuild dist first with "
			"bash build_github_pages.sh and inspect the browser output above."
		)
	capture_path = out_dir / "capture.json"
	if not capture_path.exists():
		raise RuntimeError(f"Capture did not produce {capture_path}")
	with open(capture_path, encoding="utf-8") as handle:
		payload = json.load(handle)
	if payload.get("schema_version") != CAPTURE_SCHEMA:
		raise RuntimeError("Material capture schema does not match the protocol-host analyzer")
	return payload


#============================================
def geometry_key(record: dict) -> str:
	"""Return a stable identity key for one declarative material surface."""
	parts = [
		record["protocol_name"],
		record["initial_scene"],
		record["placement_name"],
		record["kind"],
		record["driving_field"],
		record["subpart_name"],
	]
	key = "::".join(parts)
	return key


#============================================
def measure_surface_percent(before_img: PIL.Image.Image, after_img: PIL.Image.Image, geometry: dict) -> float:
	"""Measure painted percentage inside one surface's own rendered geometry."""
	x0 = max(0, int(geometry["x"]))
	y0 = max(0, int(geometry["y"]))
	x1 = min(before_img.width, int(geometry["x"] + geometry["w"]))
	y1 = min(before_img.height, int(geometry["y"] + geometry["h"]))
	if x1 <= x0 or y1 <= y0:
		return 0.0
	before_crop = numpy.asarray(before_img.crop((x0, y0, x1, y1)), dtype=numpy.int16)
	after_crop = numpy.asarray(after_img.crop((x0, y0, x1, y1)), dtype=numpy.int16)
	pixel_count = before_crop.shape[0] * before_crop.shape[1]
	if pixel_count == 0:
		return 0.0
	channel_diff = numpy.abs(before_crop - after_crop).max(axis=-1)
	changed_count = int((channel_diff > DIFF_THRESHOLD).sum())
	percent = 100.0 * changed_count / pixel_count
	return percent


#============================================
def build_current_measurements(capture_data: dict, out_dir: Path) -> dict[str, dict]:
	"""Build initial-state material records, including visible surface diffs."""
	current: dict[str, dict] = {}
	for protocol_record in capture_data["protocols"]:
		before_name = protocol_record["png_before"]
		before_img = None
		if before_name is not None:
			with PIL.Image.open(out_dir / before_name) as source_img:
				before_img = source_img.convert("RGB")
		for surface in protocol_record["surfaces"]:
			record = {
				"protocol_name": protocol_record["protocol_name"],
				"initial_scene": protocol_record["initial_scene"],
				"placement_name": surface["placement_name"],
				"object_name": surface["object_name"],
				"kind": surface["kind"],
				"driving_field": surface["driving_field"],
				"subpart_name": surface["subpart_name"],
				"material_name": surface["material_name"],
				"computed_fill": surface["computed_fill"],
				"visible": surface["visible"],
				"geometry": surface["geometry"],
				"owner_geometry": surface["owner_geometry"],
				"measured_percent": None,
			}
			if surface["visible"]:
				if before_img is None or "png_after" not in surface:
					raise RuntimeError("Visible material surface has no isolated screenshot pair")
				with PIL.Image.open(out_dir / surface["png_after"]) as source_img:
					after_img = source_img.convert("RGB")
				percent = measure_surface_percent(before_img, after_img, surface["geometry"])
				if percent <= 0:
					raise RuntimeError(
						"Visible material surface produced no isolated pixel difference: "
						f"{protocol_record['protocol_name']}::{surface['placement_name']}"
					)
				record["measured_percent"] = round(percent, 2)
			key = geometry_key(record)
			if key in current:
				raise RuntimeError(f"Duplicate material surface identity: {key}")
			current[key] = record
	return current


#============================================
def load_baseline() -> dict | None:
	"""Load a v2 baseline; legacy full-bbox evidence is intentionally ignored."""
	if not JSON_BASELINE.exists():
		return None
	with open(JSON_BASELINE, encoding="utf-8") as handle:
		baseline = json.load(handle)
	if baseline.get("schema_version") != BASELINE_SCHEMA:
		return None
	return baseline


#============================================
def write_baseline(current: dict[str, dict]) -> dict:
	"""Write a current protocol-host baseline from observed capture evidence."""
	payload = {
		"schema_version": BASELINE_SCHEMA,
		"scope": "initial authored protocol-host scenes with their active material registries",
		"transition_evidence": "Protocol walkers provide post-interaction material evidence.",
		"meta": {
			"generated_at": datetime.now(timezone.utc).isoformat(),
			"diff_threshold": DIFF_THRESHOLD,
			"regression_threshold_pp": REGRESSION_THRESHOLD_PP,
			"geometry_tolerance_pp": GEOMETRY_TOLERANCE_PP,
			"entry_count": len(current),
		},
		"entries": current,
	}
	REPORTS_DIR.mkdir(parents=True, exist_ok=True)
	with open(JSON_BASELINE, "w", encoding="utf-8") as handle:
		json.dump(payload, handle, indent=2, sort_keys=True)
	return payload


#============================================
def relative_geometry(record: dict) -> dict[str, float] | None:
	"""Return surface bounds as percentages of the owning object's bounds."""
	geometry = record["geometry"]
	owner = record["owner_geometry"]
	if owner["w"] <= 0 or owner["h"] <= 0:
		return None
	relative = {
		"x": 100.0 * (geometry["x"] - owner["x"]) / owner["w"],
		"y": 100.0 * (geometry["y"] - owner["y"]) / owner["h"],
		"w": 100.0 * geometry["w"] / owner["w"],
		"h": 100.0 * geometry["h"] / owner["h"],
	}
	return relative


#============================================
def geometry_changed(current: dict[str, float] | None, previous: dict[str, float] | None) -> bool:
	"""Return whether normalized material bounds drift beyond the evidence tolerance."""
	if current is None or previous is None:
		return current != previous
	for dimension in ("x", "y", "w", "h"):
		if abs(current[dimension] - previous[dimension]) > GEOMETRY_TOLERANCE_PP:
			return True
	return False


#============================================
def compare_against_baseline(current: dict[str, dict], baseline: dict) -> dict:
	"""Compare material identity, visibility, footprint, and coverage."""
	baseline_entries = baseline["entries"]
	regressed = []
	new_keys = []
	unchanged_count = 0
	for key, record in current.items():
		if key not in baseline_entries:
			new_keys.append(key)
			continue
		previous = baseline_entries[key]
		if record["object_name"] != previous["object_name"]:
			regressed.append({"key": key, "reason": "object identity changed"})
			continue
		if record["computed_fill"] != previous["computed_fill"]:
			regressed.append({"key": key, "reason": "computed fill changed"})
			continue
		if record["material_name"] != previous["material_name"]:
			regressed.append({"key": key, "reason": "material identity changed"})
			continue
		if record["visible"] != previous["visible"]:
			regressed.append({"key": key, "reason": "surface visibility changed"})
			continue
		if record["visible"] and previous["visible"]:
			current_relative = relative_geometry(record)
			previous_relative = relative_geometry(previous)
			if geometry_changed(current_relative, previous_relative):
				regressed.append({"key": key, "reason": "surface geometry changed"})
				continue
			delta = record["measured_percent"] - previous["measured_percent"]
			if abs(delta) > REGRESSION_THRESHOLD_PP:
				direction = "grew" if delta > 0 else "shrank"
				regressed.append({
					"key": key,
					"reason": f"footprint {direction} by {abs(delta):.2f}pp",
				})
				continue
		unchanged_count += 1
	missing_keys = [key for key in baseline_entries if key not in current]
	comparison = {
		"regressed": regressed,
		"new_keys": new_keys,
		"missing_keys": missing_keys,
		"unchanged_count": unchanged_count,
	}
	return comparison


#============================================
def write_markdown_report(mode: str, current: dict[str, dict], comparison: dict | None) -> None:
	"""Write an evidence report that distinguishes initial and transition scope."""
	lines = [
		"# Material rendering evidence",
		"",
		"This report measures the initial authored scene of each emitted protocol host, where the active protocol material registry is present. It does not use `scene_viewer.html` for material-color claims because that viewer deliberately runs without a registry.",
		"",
		"The browser capture discovers generic SVG-anchor, temporary legacy-bbox, and structured-subpart material surfaces. For each visible surface it records owner placement, driving field or subpart, material identity, computed fill, geometry, and a visible-versus-hidden pixel diff within that surface's own rendered bounds.",
		"",
		"Post-interaction material transitions are not synthesized here. They remain evidenced by visible protocol walkers, which execute the authored student path.",
		"",
		f"- **Mode:** {mode}",
		f"- **Material surfaces observed:** {len(current)}",
		f"- **Diff threshold:** {DIFF_THRESHOLD} per-channel max-abs difference",
		f"- **Footprint drift threshold:** {REGRESSION_THRESHOLD_PP} percentage points",
		f"- **Relative geometry tolerance:** {GEOMETRY_TOLERANCE_PP} percentage points",
		"",
	]
	if comparison is not None:
		lines.extend([
			"## Verification summary",
			"",
			f"- unchanged: {comparison['unchanged_count']}",
			f"- regressed: {len(comparison['regressed'])}",
			f"- new: {len(comparison['new_keys'])}",
			f"- missing: {len(comparison['missing_keys'])}",
			"",
		])
		if comparison["regressed"]:
			lines.extend(["## Regressions", ""])
			for row in comparison["regressed"]:
				lines.append(f"- `{row['key']}`: {row['reason']}")
			lines.append("")
		if comparison["new_keys"]:
			lines.extend(["## New surfaces requiring baseline review", ""])
			for key in comparison["new_keys"]:
				lines.append(f"- `{key}`")
			lines.append("")
		if comparison["missing_keys"]:
			lines.extend(["## Missing baseline surfaces", ""])
			for key in comparison["missing_keys"]:
				lines.append(f"- `{key}`")
			lines.append("")
	lines.extend([
		"## Current initial-state corpus",
		"",
		"| Surface | Owner | Kind | Field or subpart | Material | Computed fill | Visible | Footprint % |",
		"| --- | --- | --- | --- | --- | --- | --- | --- |",
	])
	for key in sorted(current):
		record = current[key]
		field = record["driving_field"]
		if record["subpart_name"]:
			field += f" / {record['subpart_name']}"
		percent = "" if record["measured_percent"] is None else f"{record['measured_percent']:.2f}"
		lines.append(
			f"| `{key}` | `{record['placement_name']}` | `{record['kind']}` | `{field}` | "
			f"`{record['material_name']}` | `{record['computed_fill']}` | {record['visible']} | {percent} |"
		)
	lines.append("")
	REPORTS_DIR.mkdir(parents=True, exist_ok=True)
	content = "\n".join(lines)
	with open(MD_REPORT, "w", encoding="utf-8") as handle:
		handle.write(content)


#============================================
def main() -> None:
	"""Capture, baseline, or verify protocol-host material evidence."""
	args = parse_args()
	capture_data = run_capture(CAPTURE_OUT_DIR)
	current = build_current_measurements(capture_data, CAPTURE_OUT_DIR)
	if not current:
		raise RuntimeError("Material capture found no declarative material surfaces")
	baseline = load_baseline()
	if args.write_baseline:
		write_baseline(current)
		write_markdown_report("baseline", current, None)
		return
	if baseline is None:
		write_markdown_report("capture only; baseline refresh required", current, None)
		raise RuntimeError(
			"No current protocol-host material baseline exists. Run again with --write-baseline; "
			"the prior standalone-viewer baseline is intentionally not comparable."
		)
	comparison = compare_against_baseline(current, baseline)
	write_markdown_report("verify", current, comparison)
	messages = [f"{row['key']}: {row['reason']}" for row in comparison["regressed"]]
	messages.extend(f"{key}: new surface requires baseline review" for key in comparison["new_keys"])
	messages.extend(f"{key}: baseline surface is missing" for key in comparison["missing_keys"])
	if messages:
		raise RuntimeError("Material rendering baseline drift:\n" + "\n".join(messages))


if __name__ == "__main__":
	main()
