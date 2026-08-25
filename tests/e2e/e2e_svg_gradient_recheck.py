#!/usr/bin/env python3
"""
Targeted gradient-under-transform recheck harness.

Re-measures the Category-B (userSpaceOnUse gradient) worst offenders from the
prior visual regression run with the CURRENT (post-fix) normalizer, and produces
a before/after comparison report.

The prior phash distances are loaded from docs/active_plans/reports/svg_visual_regression.json.
The current normalizer is tools/normalize_svg_v3.py.

Output:
  docs/active_plans/reports/svg_visual_regression_gradient_recheck.md
  test-results/svg_gradient_recheck/  -- before/after PNGs (gitignored)

Run:
  source source_me.sh && python3 tests/e2e/e2e_svg_gradient_recheck.py
"""

# Standard Library
import json
import hashlib
import shutil
import tempfile
import subprocess
from pathlib import Path

# PIP3 modules
import PIL.Image
import imagehash

# Resolve repo root via git
_GIT = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True)
REPO_ROOT = Path(_GIT.stdout.strip())

import tools.svg_normalizer.workflow

# Paths
REPORTS_DIR = REPO_ROOT / "docs" / "active_plans" / "reports"
OLD_JSON = REPORTS_DIR / "svg_visual_regression.json"
OUT_MD = REPORTS_DIR / "svg_visual_regression_gradient_recheck.md"
GALLERY_DIR = REPO_ROOT / "test-results" / "svg_gradient_recheck"

# Batch renderer (same as the main harness)
BATCH_RENDERER_MJS = REPO_ROOT / "tests" / "playwright" / "svg_batch_render.mjs"

# Render settings (match the main harness)
RENDER_SIZE = 256
IDENTICAL_THRESHOLD = 2
MINOR_THRESHOLD = 6

# The top-20 worst offenders from the prior run (phash >= 30), which are
# the Category-B candidates plus other structural outliers.
# These are relative paths from REPO_ROOT.
TARGET_FILES = [
	"OTHER_REPOS/bioicons/static/icons/cc-0/Computer_hardware/Simon_Dürr/cpu.svg",
	"OTHER_REPOS/bioicons/static/icons/cc-by-4.0/Cell_membrane/Helicase_11/cell_membrane_arc.svg",
	"OTHER_REPOS/SVG/scour/unittests/straight-curve.svg",
	"OTHER_REPOS/bioicons/static/icons/cc-by-sa-4.0/Animals/Stefano-Vianello/Amphiprion_ocellaris_egg.svg",
	"OTHER_REPOS/SVG/scour/unittests/group-no-creation.svg",
	"OTHER_REPOS/bioicons/static/icons/cc-0/Chemistry/OpenClipart/round-bottomed-flask-1-500ml.svg",
	"OTHER_REPOS/bioicons/static/icons/cc-by-3.0/General_items/Servier/arrow-twosides-horizontal.svg",
	"OTHER_REPOS/bioicons/static/icons/cc-by-4.0/Chemistry/DBCLS/flask-3-empty.svg",
	"OTHER_REPOS/bioicons/static/icons/cc-by-4.0/Lab_apparatus/DBCLS/pipette-tip-box.svg",
	"OTHER_REPOS/bioicons/static/icons/mit/Human_physiology/Kathryn_Kananen/stanford_b_debakey_IIIa.svg",
	"OTHER_REPOS/SVG/scour/unittests/dont-convert-short-color-names.svg",
	"OTHER_REPOS/SVG/scour/unittests/group-creation.svg",
	"OTHER_REPOS/SVG/scour/unittests/path-quad-optimize.svg",
	"OTHER_REPOS/bioicons/static/icons/cc-0/Animals/EwaOz/Xenopus_new.svg",
	"OTHER_REPOS/bioicons/static/icons/cc-0/Intracellular_components/jaiganesh/ribosome.svg",
	"OTHER_REPOS/bioicons/static/icons/cc-0/Machine_Learning/Simon_Dürr/variational-autoencoder.svg",
	"OTHER_REPOS/bioicons/static/icons/cc-0/Nucleic_acids/Emmett_Leddin/nucleotide-a-ul.svg",
	"OTHER_REPOS/bioicons/static/icons/cc-by-4.0/Lab_apparatus/DBCLS/microtube-closed.svg",
	"OTHER_REPOS/bioicons/static/icons/mit/Human_physiology/Kathryn_Kananen/stanford_a_debakey_I.svg",
	"OTHER_REPOS/bioicons/static/icons/mit/Human_physiology/Kathryn_Kananen/stanford_a_debakey_II.svg",
]

# Engines to use
ENGINES = ["chromium", "firefox"]


#============================================
def load_prior_phash(old_json_path: Path) -> dict[str, dict]:
	"""Load prior phash distances per file per engine from the old JSON report.

	Args:
		old_json_path: Path to the prior svg_visual_regression.json.

	Returns:
		Dict mapping rel_path -> {engine: hamming_phash}.
	"""
	with open(old_json_path) as f:
		data = json.load(f)
	prior: dict[str, dict] = {}
	for record in data["results"]:
		rel = record["file"]
		prior[rel] = {}
		for engine, eng_data in record.get("engines", {}).items():
			if eng_data.get("error") is None:
				prior[rel][engine] = eng_data.get("hamming_phash")
	return prior


#============================================
def normalize_files(target_rels: list[str], tmp_dir: Path) -> dict[str, Path | None]:
	"""Normalize each target file with the current normalizer.

	Args:
		target_rels: Relative paths (from REPO_ROOT) of SVG files to normalize.
		tmp_dir: Directory to write normalized outputs.

	Returns:
		Dict mapping rel_path -> normalized Path (or None if rejected).
	"""
	norm_map: dict[str, Path | None] = {}
	for rel in target_rels:
		svg_path = REPO_ROOT / rel
		if not svg_path.exists():
			print(f"  MISSING: {rel}")
			norm_map[rel] = None
			continue
		# md5 here names a temp file stem, not a security control.
		stem = hashlib.md5(rel.encode(), usedforsecurity=False).hexdigest()[:10]
		out_path = tmp_dir / f"norm_{stem}.svg"
		result = tools.svg_normalizer.workflow.normalize_svg_file(svg_path, out_path)
		if result.normalized:
			norm_map[rel] = out_path
		else:
			reason = result.reject_reason or "unknown"
			print(f"  REJECTED ({reason}): {Path(rel).name}")
			norm_map[rel] = None
	return norm_map


#============================================
def build_engine_manifest(
	target_rels: list[str],
	norm_map: dict[str, Path | None],
	engine: str,
	tmp_dir: Path,
) -> list[dict]:
	"""Build per-engine manifest entries for the batch renderer.

	Args:
		target_rels: Relative paths (from REPO_ROOT) of all target SVGs.
		norm_map: rel -> normalized path or None.
		engine: Engine name (e.g. 'chromium').
		tmp_dir: Temp directory for output PNGs.

	Returns:
		List of {svg_path, output_png, rel_path, kind} dicts.
	"""
	entries = []
	for rel in target_rels:
		norm_path = norm_map.get(rel)
		if norm_path is None:
			continue
		svg_path = REPO_ROOT / rel
		# md5 here names a temp file stem, not a security control.
		stem = hashlib.md5(rel.encode(), usedforsecurity=False).hexdigest()[:10]
		# Original PNG (engine-specific path to avoid overwrite)
		orig_png = tmp_dir / f"png_{stem}_{engine}_orig.png"
		entries.append({
			"svg_path": str(svg_path),
			"output_png": str(orig_png),
			"rel_path": rel,
			"kind": "orig",
		})
		# Normalized PNG
		norm_png = tmp_dir / f"png_{stem}_{engine}_norm.png"
		entries.append({
			"svg_path": str(norm_path),
			"output_png": str(norm_png),
			"rel_path": rel,
			"kind": "norm",
		})
	return entries


#============================================
def run_batch_render(manifest_entries: list[dict], engine: str, tmp_dir: Path) -> dict[str, dict]:
	"""Run the Playwright batch renderer for one engine.

	Args:
		manifest_entries: {svg_path, output_png, ...} list.
		engine: 'chromium' or 'firefox'.
		tmp_dir: Temp directory for manifest JSON files.

	Returns:
		Dict mapping output_png -> {ok, error} from the renderer.
	"""
	manifest_path = tmp_dir / f"recheck_manifest_{engine}.json"
	renderer_manifest = [{"svg_path": e["svg_path"], "output_png": e["output_png"]} for e in manifest_entries]
	with open(manifest_path, "w") as f:
		json.dump(renderer_manifest, f)

	print(f"  Running batch renderer [{engine}] for {len(manifest_entries)} renders...")
	proc = subprocess.run(
		["node", str(BATCH_RENDERER_MJS), str(manifest_path), engine],
		cwd=str(REPO_ROOT),
		capture_output=False,
		text=True,
	)
	if proc.returncode != 0:
		raise RuntimeError(f"Batch renderer [{engine}] exited {proc.returncode}.")

	results_path = str(manifest_path) + ".results.json"
	if not Path(results_path).exists():
		raise RuntimeError(f"Batch renderer [{engine}] did not produce results JSON.")

	with open(results_path) as f:
		raw = json.load(f)
	if not isinstance(raw, list):
		raise RuntimeError(f"Batch renderer [{engine}] results JSON is not a list.")
	results = {r["output_png"]: r for r in raw}
	return results


#============================================
def require_render_evidence(
	manifest_entries: list[dict],
	render_results: dict[str, dict],
	engine: str,
) -> None:
	"""Require one successful, nonempty render result for every manifest entry.

	Args:
		manifest_entries: Expected {output_png, ...} entries for one engine.
		render_results: Renderer results indexed by output PNG path.
		engine: Requested browser engine name.

	Raises:
		RuntimeError: The renderer did not produce complete browser evidence.
	"""
	if not manifest_entries:
		raise RuntimeError(f"No render manifest entries were built for requested engine [{engine}].")

	missing = []
	failed = []
	for entry in manifest_entries:
		output_png = entry["output_png"]
		result = render_results.get(output_png)
		if result is None:
			missing.append(output_png)
			continue
		if not result["ok"]:
			failed.append(f"{output_png}: {result['error']}")
			continue
		png_path = Path(output_png)
		if not png_path.is_file() or png_path.stat().st_size == 0:
			failed.append(f"{output_png}: missing or empty PNG evidence")

	if missing or failed:
		parts = []
		if missing:
			parts.append(f"missing results={len(missing)}")
		if failed:
			parts.append(f"failed renders={len(failed)}")
		message = ", ".join(parts)
		raise RuntimeError(f"Incomplete render evidence for [{engine}]: {message}.")


#============================================
def compute_hashes(png_path: Path) -> dict:
	"""Compute perceptual hashes for a PNG.

	Args:
		png_path: Path to the PNG file.

	Returns:
		Dict with 'phash' and 'dhash' as hex strings.
	"""
	img = PIL.Image.open(png_path).convert("RGB")
	ph = imagehash.phash(img)
	dh = imagehash.dhash(img)
	return {"phash": str(ph), "dhash": str(dh)}


#============================================
def hamming_between_hex(hex_a: str, hex_b: str) -> int:
	"""Compute hamming distance between two imagehash hex strings.

	Args:
		hex_a: First hash.
		hex_b: Second hash.

	Returns:
		Integer hamming distance.
	"""
	hash_a = imagehash.hex_to_hash(hex_a)
	hash_b = imagehash.hex_to_hash(hex_b)
	return int(hash_a - hash_b)


#============================================
def classify_distance(dist: int) -> str:
	"""Classify a hamming distance.

	Args:
		dist: Hamming distance.

	Returns:
		'identical', 'minor', or 'divergent'.
	"""
	if dist <= IDENTICAL_THRESHOLD:
		return "identical"
	if dist <= MINOR_THRESHOLD:
		return "minor"
	return "divergent"


#============================================
def hash_engine_results(
	manifest_entries: list[dict],
	render_results: dict[str, dict],
) -> dict[str, dict[str, dict]]:
	"""Hash rendered PNGs for all manifest entries.

	Args:
		manifest_entries: The manifest entries that were rendered.
		render_results: {output_png: {ok, error}} from the renderer.

	Returns:
		Dict mapping rel_path -> {kind: {phash, dhash}}.
	"""
	hashes: dict[str, dict[str, dict]] = {}
	for entry in manifest_entries:
		rel = entry["rel_path"]
		kind = entry["kind"]
		out_png = entry["output_png"]
		rr = render_results.get(out_png, {})
		if not rr.get("ok"):
			continue
		png_path = Path(out_png)
		if not png_path.exists():
			continue
		h = compute_hashes(png_path)
		if rel not in hashes:
			hashes[rel] = {}
		hashes[rel][kind] = h
	return hashes


#============================================
def save_gallery_pngs(
	target_rels: list[str],
	norm_map: dict[str, Path | None],
	per_engine_hashes: dict[str, dict],
	per_engine_manifests: dict[str, list[dict]],
) -> None:
	"""Save before/after PNGs to the gallery directory.

	Args:
		target_rels: All target relative paths.
		norm_map: rel -> normalized path or None.
		per_engine_hashes: {engine: {rel: {kind: hashes}}}.
		per_engine_manifests: {engine: [{svg_path, output_png, rel_path, kind}]}.
	"""
	GALLERY_DIR.mkdir(parents=True, exist_ok=True)

	# Build index: rel -> engine -> kind -> output_png
	png_index: dict[str, dict[str, dict[str, str]]] = {}
	for engine, entries in per_engine_manifests.items():
		for entry in entries:
			rel = entry["rel_path"]
			kind = entry["kind"]
			out_png = entry["output_png"]
			if rel not in png_index:
				png_index[rel] = {}
			if engine not in png_index[rel]:
				png_index[rel][engine] = {}
			png_index[rel][engine][kind] = out_png

	for idx, rel in enumerate(target_rels):
		if norm_map.get(rel) is None:
			continue
		safe_name = Path(rel).name.replace(".svg", "")[:40]
		for engine in ENGINES:
			eng_png = png_index.get(rel, {}).get(engine, {})
			orig_src = eng_png.get("orig")
			norm_src = eng_png.get("norm")
			if orig_src and Path(orig_src).exists():
				dest = GALLERY_DIR / f"{idx+1:02d}_{safe_name}_{engine}_orig.png"
				shutil.copy2(orig_src, dest)
			if norm_src and Path(norm_src).exists():
				dest = GALLERY_DIR / f"{idx+1:02d}_{safe_name}_{engine}_norm.png"
				shutil.copy2(norm_src, dest)

	print(f"Gallery PNGs saved to {GALLERY_DIR}")


#============================================
def write_markdown_report(
	target_rels: list[str],
	norm_map: dict[str, Path | None],
	prior_phash: dict[str, dict],
	per_engine_hashes: dict[str, dict],
	engines: list[str],
) -> None:
	"""Write the gradient recheck Markdown report.

	Args:
		target_rels: All target relative paths.
		norm_map: rel -> normalized path or None.
		prior_phash: Prior phash distances from old run.
		per_engine_hashes: {engine: {rel: {kind: hashes}}}.
		engines: Engines used.
	"""
	md = "# SVG gradient-under-transform recheck report\n\n"
	md += "**Scope:** top-20 phash offenders from the prior visual regression run\n"
	md += "**Fix audited:** gradient-under-transform (Category B) -- `tools/normalize_svg_v3.py`\n"
	md += "**Normalizer:** current (post-fix) `normalize_svg_v3.py`\n"
	md += f"**Engines:** {', '.join(engines)}\n"
	md += f"**Render size:** {RENDER_SIZE}x{RENDER_SIZE} px\n"
	md += "**Hash type:** phash (perceptual hash, 8x8 = 64-bit, hamming distance)\n\n"

	md += "## Before/after comparison table\n\n"
	md += "Legend: distance 0-2 = identical, 3-6 = minor, >6 = divergent\n\n"

	# One table per engine
	for engine in engines:
		md += f"### {engine.capitalize()} engine\n\n"
		md += "| File | Pre-fix phash | Post-fix phash | Verdict |\n"
		md += "| --- | --- | --- | --- |\n"

		for rel in target_rels:
			fname = Path(rel).name
			norm_path = norm_map.get(rel)

			if norm_path is None:
				# Was rejected by the normalizer
				prior_val = prior_phash.get(rel, {}).get(engine, "-")
				md += f"| `{fname}` | {prior_val} | rejected (UNSUPPORTED_TRANSFORM) | resolved |\n"
				continue

			if rel not in per_engine_hashes.get(engine, {}):
				# Render failed
				prior_val = prior_phash.get(rel, {}).get(engine, "-")
				md += f"| `{fname}` | {prior_val} | render-error | error |\n"
				continue

			file_hashes = per_engine_hashes[engine][rel]
			orig_h = file_hashes.get("orig")
			norm_h = file_hashes.get("norm")

			prior_val = prior_phash.get(rel, {}).get(engine)
			prior_str = str(prior_val) if prior_val is not None else "-"

			if orig_h is None or norm_h is None:
				md += f"| `{fname}` | {prior_str} | render-error | error |\n"
				continue

			new_dist = hamming_between_hex(orig_h["phash"], norm_h["phash"])
			new_cls = classify_distance(new_dist)

			# Verdict
			if prior_val is None:
				verdict = "no-prior"
			elif new_dist < prior_val - 2:
				verdict = "improved"
			elif new_dist > prior_val + 2:
				verdict = "regressed"
			else:
				verdict = "unchanged"

			md += f"| `{fname}` | {prior_str} | {new_dist} ({new_cls}) | {verdict} |\n"

		md += "\n"

	# Summary counts
	md += "## Summary\n\n"
	for engine in engines:
		improved = 0
		unchanged = 0
		regressed = 0
		resolved = 0
		errors = 0

		for rel in target_rels:
			norm_path = norm_map.get(rel)
			if norm_path is None:
				resolved += 1
				continue

			file_hashes = per_engine_hashes.get(engine, {}).get(rel)
			if file_hashes is None:
				errors += 1
				continue

			orig_h = file_hashes.get("orig")
			norm_h = file_hashes.get("norm")
			if orig_h is None or norm_h is None:
				errors += 1
				continue

			new_dist = hamming_between_hex(orig_h["phash"], norm_h["phash"])
			prior_val = prior_phash.get(rel, {}).get(engine)

			if prior_val is None:
				unchanged += 1
			elif new_dist < prior_val - 2:
				improved += 1
			elif new_dist > prior_val + 2:
				regressed += 1
			else:
				unchanged += 1

		md += f"**{engine.capitalize()}:** improved={improved}, unchanged={unchanged}, "
		md += f"regressed={regressed}, resolved-via-reject={resolved}, errors={errors}\n\n"

	md += "## Conclusion\n\n"
	md += "The gradient-under-transform fix (Category B from the prior report) "
	md += "bakes the accumulated element matrix into the `gradientTransform` of "
	md += "each referenced `userSpaceOnUse` gradient before flattening. "
	md += "The before/after phash distances above show whether the fix restored "
	md += "visual fidelity for the affected files (`cpu.svg` was the primary offender, "
	md += "phash=38 in both engines before the fix).\n\n"
	md += "Files in other categories (A: viewBox reframe, C: stacking/scale, D: test fixtures) "
	md += "are included in the table as context; their phash distances are expected to remain "
	md += "high (they are not gradient bugs).\n\n"
	md += "Gallery before/after PNGs are saved to `test-results/svg_gradient_recheck/` (gitignored).\n"

	REPORTS_DIR.mkdir(parents=True, exist_ok=True)
	clean_md = "\n".join(line.rstrip() for line in md.splitlines()).rstrip() + "\n"
	with open(OUT_MD, "w") as f:
		f.write(clean_md)
	print(f"Markdown report: {OUT_MD}")


#============================================
def main() -> None:
	"""Main entry point."""
	print(f"Gradient recheck: {len(TARGET_FILES)} target files, engines={ENGINES}")

	# Load prior phash distances
	print(f"Loading prior phash from {OLD_JSON}")
	prior_phash = load_prior_phash(OLD_JSON)

	GALLERY_DIR.mkdir(parents=True, exist_ok=True)

	with tempfile.TemporaryDirectory() as tmp_dir:
		tmp_path = Path(tmp_dir)

		# Normalize all target files with the current (fixed) normalizer
		print("Normalizing target files...")
		norm_map = normalize_files(TARGET_FILES, tmp_path)
		n_pass = sum(1 for v in norm_map.values() if v is not None)
		n_reject = sum(1 for v in norm_map.values() if v is None)
		print(f"  Normalized: {n_pass} pass, {n_reject} rejected")

		# Build per-engine manifests and run batch renderer
		per_engine_manifests: dict[str, list[dict]] = {}
		per_engine_hashes: dict[str, dict] = {}

		for engine in ENGINES:
			manifest = build_engine_manifest(TARGET_FILES, norm_map, engine, tmp_path)
			per_engine_manifests[engine] = manifest
			render_results = run_batch_render(manifest, engine, tmp_path)
			require_render_evidence(manifest, render_results, engine)
			hashes = hash_engine_results(manifest, render_results)
			per_engine_hashes[engine] = hashes
			print(f"  Engine {engine}: hashed {len(hashes)} files")

		# Save gallery PNGs before tmp_dir is cleaned up
		save_gallery_pngs(TARGET_FILES, norm_map, per_engine_hashes, per_engine_manifests)

	# Write report
	write_markdown_report(TARGET_FILES, norm_map, prior_phash, per_engine_hashes, ENGINES)

	# Print headline
	print("\n=== Headline ===")
	for engine in ENGINES:
		improved = 0
		unchanged = 0
		regressed = 0

		for rel in TARGET_FILES:
			norm_path = norm_map.get(rel)
			if norm_path is None:
				continue
			file_hashes = per_engine_hashes.get(engine, {}).get(rel)
			if not file_hashes:
				continue
			orig_h = file_hashes.get("orig")
			norm_h = file_hashes.get("norm")
			if orig_h is None or norm_h is None:
				continue
			new_dist = hamming_between_hex(orig_h["phash"], norm_h["phash"])
			prior_val = prior_phash.get(rel, {}).get(engine)
			if prior_val is None:
				continue
			if new_dist < prior_val - 2:
				improved += 1
			elif new_dist > prior_val + 2:
				regressed += 1
			else:
				unchanged += 1

		print(f"{engine}: improved={improved}, unchanged={unchanged}, regressed={regressed}")


if __name__ == "__main__":
	main()
