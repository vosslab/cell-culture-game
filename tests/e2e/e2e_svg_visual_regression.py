#!/usr/bin/env python3
"""
Visual-regression harness for SVG v3 normalization.

For each SVG in OTHER_REPOS/ that v3 normalizes (rejected files are skipped),
renders both the original and normalized SVG to PNG using Playwright in both
chromium and firefox, computes perceptual hashes (imagehash.phash + dhash),
and reports the hamming distance between original and normalized per engine.
Also records chromium-vs-firefox divergence on the normalized output.

Large hamming distance = potential visual regression (cropping / distortion /
dropped content) = a contract item 3 violation (PRIMARY_CONTRACT.md item 3:
"never crop or aspect-distort scientific assets").

Outputs:
  docs/active_plans/reports/svg_visual_regression.json
  docs/active_plans/reports/svg_visual_regression.md
  test-results/svg_visual_regression/   -- worst-offender PNGs (before + after)

Run:
  source source_me.sh && python3 tests/e2e/e2e_svg_visual_regression.py
  source source_me.sh && python3 tests/e2e/e2e_svg_visual_regression.py --full

Exit code:
  0: every requested engine produced complete browser render evidence
  1: normalization or browser rendering could not produce complete evidence

NOTE: v3 flattens simple clipPaths (allowlist) into path geometry and rejects
complex clipPaths (CLIPPATH_UNSUPPORTED_COMPLEX).  Only the small simple-clip
subset is normalized; most clip-bearing files in the corpus are rejected.

PERFORMANCE: Uses batch rendering (svg_batch_render.mjs) -- one browser session per
engine, not one node launch per file. ~300-file run takes ~5-10 min vs hours.
"""

# Standard Library
import json
import shutil
import random
import hashlib
import tempfile
import argparse
import subprocess
from pathlib import Path

# PIP3 modules
import PIL.Image
import imagehash

# Resolve repo root via git so this script works from any cwd.
_GIT_RESULT = subprocess.run(
	["git", "rev-parse", "--show-toplevel"],
	capture_output=True,
	text=True,
	check=True,
)
REPO_ROOT = Path(_GIT_RESULT.stdout.strip())

import tools.svg_normalizer.workflow

# Paths
OTHER_REPOS = REPO_ROOT / "OTHER_REPOS"
REPORTS_DIR = REPO_ROOT / "docs" / "active_plans" / "reports"
GALLERY_DIR = REPO_ROOT / "test-results" / "svg_visual_regression"
JSON_REPORT = REPORTS_DIR / "svg_visual_regression.json"
MD_REPORT = REPORTS_DIR / "svg_visual_regression.md"

# Playwright batch renderer (keeps browser open across renders -- much faster).
BATCH_RENDERER_MJS = REPO_ROOT / "tests" / "playwright" / "svg_batch_render.mjs"

# Fixed render resolution.
RENDER_SIZE = 256

# Hamming-distance thresholds (phash on 8x8 = 64 bits max).
IDENTICAL_THRESHOLD = 2      # distance 0-2: perceptually identical
MINOR_THRESHOLD = 6          # distance 3-6: minor difference
# distance >6: divergent / potential regression

# Number of worst offenders to show in the gallery.
GALLERY_TOP_N = 25

# Target number of valid comparisons for the default sample.
SAMPLE_SIZE = 300

# Maximum SVGs to pre-screen in default mode.
# At ~23% current pass rate, 1500 pre-screen -> ~350 candidates -> 300 sample.
PRESCREEN_CAP = 1500

# Random seed for reproducible sampling.
SAMPLE_SEED = 42


#============================================
def parse_args() -> argparse.Namespace:
	"""Parse command-line arguments."""
	parser = argparse.ArgumentParser(
		description="Visual-regression harness for SVG v3 normalization."
	)
	parser.add_argument(
		"--full",
		dest="full",
		action="store_true",
		help="Run on all currently-normalizable SVGs (no sample cap). Default is ~300 sample.",
	)
	parser.add_argument(
		"--engines",
		dest="engines",
		default="chromium,firefox",
		help="Comma-separated engines. Default: chromium,firefox.",
	)
	args = parser.parse_args()
	return args


#============================================
def collect_all_svg_paths() -> list[Path]:
	"""Collect all *.svg paths under OTHER_REPOS/, sorted for reproducibility.

	Returns:
		Sorted list of absolute SVG paths.
	"""
	paths = sorted(OTHER_REPOS.rglob("*.svg"))
	return paths


#============================================
def prescreen_normalizable(
	svg_paths: list[Path],
	tmp_dir: Path,
	cap: int | None,
	seed: int,
) -> dict[Path, Path]:
	"""Pre-screen SVG paths and return those the current normalizer accepts.

	Runs the normalizer on each candidate. This handles the case where wild
	verdicts JSON is stale (normalizer has gained new rejection rules since
	verdicts were generated). The normalized output for each passing file is
	kept on disk at a unique path, so a later normalize-once pass can reuse
	it instead of re-normalizing the same file.

	Args:
		svg_paths: All candidate SVG paths.
		tmp_dir: Temp directory for normalized output.
		cap: Max files to screen (None = all). Shuffles before capping for diversity.
		seed: Random seed for shuffle.

	Returns:
		Dict mapping each passing absolute svg_path to its normalized Path.
	"""
	rng = random.Random(seed)
	shuffled = list(svg_paths)
	rng.shuffle(shuffled)

	screened = shuffled[:cap] if cap is not None else shuffled
	print(f"Pre-screening {len(screened)} SVGs for normalizability...")

	passing: dict[Path, Path] = {}

	for idx, svg_path in enumerate(screened):
		if idx % 200 == 0:
			pct = 100.0 * (idx + 1) / len(screened)
			print(f"  prescreen [{idx+1}/{len(screened)}] {pct:.0f}%  passing={len(passing)}")
		# Unique output filename so passing outputs can be kept and reused.
		# md5 here names a temp file stem, not a security control.
		stem = hashlib.md5(str(svg_path).encode(), usedforsecurity=False).hexdigest()[:10]
		out_path = tmp_dir / f"norm_{stem}.svg"
		result = tools.svg_normalizer.workflow.normalize_svg_file(svg_path, out_path)
		if result.normalized:
			passing[svg_path] = out_path
		elif out_path.exists():
			# Remove failed-normalize output; nothing to reuse.
			out_path.unlink()

	print(f"Pre-screen done: {len(passing)} of {len(screened)} passed.")
	return passing


#============================================
def select_sample(all_paths: list[Path], sample_size: int, seed: int) -> list[Path]:
	"""Select a reproducible random sample from all_paths.

	Args:
		all_paths: All normalizable SVG paths.
		sample_size: Target count.
		seed: Random seed.

	Returns:
		Sampled and sorted list.
	"""
	rng = random.Random(seed)
	if len(all_paths) <= sample_size:
		return list(all_paths)
	sampled = rng.sample(all_paths, sample_size)
	sampled.sort()
	return sampled


#============================================
def build_norm_map_for_corpus(
	corpus: list[Path],
	passing_map: dict[Path, Path],
) -> dict[str, Path | None]:
	"""Build rel_path -> normalized Path map for corpus, reusing prescreen output.

	Every corpus path is guaranteed present in passing_map, since corpus is
	always drawn from the prescreen's passing set. This avoids a second
	normalize pass over the same files.

	Args:
		corpus: Selected SVG paths (subset of passing_map keys).
		passing_map: Map from svg_path -> already-normalized Path (from prescreen).

	Returns:
		Dict mapping relative path string -> normalized Path.
	"""
	norm_map: dict[str, Path | None] = {}
	for svg_path in corpus:
		rel = str(svg_path.relative_to(REPO_ROOT))
		norm_map[rel] = passing_map[svg_path]

	print(f"Reusing {len(norm_map)} pre-normalized corpus files (normalize-once).")
	return norm_map


#============================================
def build_render_manifest(
	corpus: list[Path],
	norm_map: dict[str, Path | None],
	tmp_dir: Path,
) -> list[dict]:
	"""Build the list of (svg_path, output_png) pairs for the batch renderer.

	Each corpus file that normalized gets two entries: original and normalized.

	Args:
		corpus: All corpus SVG paths.
		norm_map: Map from rel_path -> normalized Path (or None).
		tmp_dir: Directory for PNG outputs.

	Returns:
		List of dicts with svg_path, output_png, rel_path, kind ('orig' or 'norm').
	"""
	entries = []
	for svg_path in corpus:
		rel = str(svg_path.relative_to(REPO_ROOT))
		norm_path = norm_map.get(rel)
		if norm_path is None:
			continue
		# md5 here names a temp file stem, not a security control.
		stem = hashlib.md5(rel.encode(), usedforsecurity=False).hexdigest()[:10]
		# Original PNG.
		orig_png = tmp_dir / f"png_{stem}_orig.png"
		entries.append({
			"svg_path": str(svg_path),
			"output_png": str(orig_png),
			"rel_path": rel,
			"kind": "orig",
		})
		# Normalized PNG.
		norm_png = tmp_dir / f"png_{stem}_norm.png"
		entries.append({
			"svg_path": str(norm_path),
			"output_png": str(norm_png),
			"rel_path": rel,
			"kind": "norm",
		})
	return entries


#============================================
def run_batch_render(manifest_entries: list[dict], engine: str, tmp_dir: Path) -> dict[str, dict]:
	"""Run the batch renderer for one engine on the given manifest entries.

	Writes a JSON manifest file, invokes svg_batch_render.mjs, reads results.

	Args:
		manifest_entries: List of {svg_path, output_png, ...} dicts.
		engine: 'chromium' or 'firefox'.
		tmp_dir: Temp directory for manifest files.

	Returns:
		Dict mapping output_png -> {ok, error} from the renderer.
	"""
	# Write manifest JSON for the node renderer.
	manifest_path = tmp_dir / f"manifest_{engine}.json"
	# Renderer only needs svg_path and output_png.
	renderer_manifest = [{"svg_path": e["svg_path"], "output_png": e["output_png"]} for e in manifest_entries]
	with open(manifest_path, "w") as f:
		json.dump(renderer_manifest, f)

	print(f"Running batch renderer [{engine}] for {len(manifest_entries)} renders...")
	result = subprocess.run(
		["node", str(BATCH_RENDERER_MJS), str(manifest_path), engine],
		cwd=str(REPO_ROOT),
		capture_output=False,
		text=True,
	)
	if result.returncode != 0:
		raise RuntimeError(f"Batch renderer [{engine}] exited {result.returncode}.")

	# Read results JSON.
	results_path = str(manifest_path) + ".results.json"
	if not Path(results_path).exists():
		raise RuntimeError(f"Batch renderer [{engine}] did not produce results JSON.")

	with open(results_path) as f:
		results_raw = json.load(f)

	if not isinstance(results_raw, list):
		raise RuntimeError(f"Batch renderer [{engine}] results JSON is not a list.")
	# Index by output_png.
	results = {r["output_png"]: r for r in results_raw}
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
	"""Compute perceptual hashes for a PNG file.

	Args:
		png_path: Path to the PNG image.

	Returns:
		Dict with keys 'phash' and 'dhash' as hex strings.
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
def assemble_results(
	corpus: list[Path],
	norm_map: dict[str, Path | None],
	per_engine_hashes: dict[str, dict[str, dict[str, dict]]],
	engines: list[str],
) -> list[dict]:
	"""Assemble per-file result records from pre-computed per-engine hashes.

	Args:
		corpus: All corpus SVG paths.
		norm_map: rel_path -> normalized path or None.
		per_engine_hashes: {engine: {rel_path: {orig: {phash, dhash}, norm: {phash, dhash}}}}.
		engines: Engine names used.

	Returns:
		List of per-file result dicts.
	"""
	results = []

	for svg_path in corpus:
		rel = str(svg_path.relative_to(REPO_ROOT))
		norm_path = norm_map.get(rel)
		if norm_path is None:
			results.append({
				"file": rel,
				"normalized": False,
				"error": "rejected_at_normalize_phase",
				"engines": {},
				"chromium_vs_firefox_hamming": None,
				"chromium_vs_firefox_classification": "unavailable",
			})
			continue

		record: dict = {
			"file": rel,
			"normalized": True,
			"error": None,
			"engines": {},
			"chromium_vs_firefox_hamming": None,
			"chromium_vs_firefox_classification": "unavailable",
		}

		for engine in engines:
			eng_hashes = per_engine_hashes.get(engine, {}).get(rel)
			if eng_hashes is None:
				record["engines"][engine] = {"error": "render_failed"}
				continue

			orig_h = eng_hashes.get("orig")
			norm_h = eng_hashes.get("norm")
			if orig_h is None or norm_h is None:
				record["engines"][engine] = {"error": "render_failed"}
				continue

			hamming_phash = hamming_between_hex(orig_h["phash"], norm_h["phash"])
			hamming_dhash = hamming_between_hex(orig_h["dhash"], norm_h["dhash"])
			classification = classify_distance(hamming_phash)

			record["engines"][engine] = {
				"error": None,
				"phash_orig": orig_h["phash"],
				"phash_norm": norm_h["phash"],
				"dhash_orig": orig_h["dhash"],
				"dhash_norm": norm_h["dhash"],
				"hamming_phash": hamming_phash,
				"hamming_dhash": hamming_dhash,
				"classification": classification,
				"orig_png_saved": None,
				"norm_png_saved": None,
			}

		# Chromium vs firefox divergence on normalized output.
		if "chromium" in engines and "firefox" in engines:
			ce = record["engines"].get("chromium")
			fe = record["engines"].get("firefox")
			if ce and fe and ce.get("error") is None and fe.get("error") is None:
				cf_hamming = hamming_between_hex(ce["phash_norm"], fe["phash_norm"])
				record["chromium_vs_firefox_hamming"] = cf_hamming
				record["chromium_vs_firefox_classification"] = classify_distance(cf_hamming)

		results.append(record)

	return results


#============================================
def save_worst_offender_pngs(
	results: list[dict],
	engines: list[str],
	top_n: int,
	png_store: dict[str, dict[str, dict[str, str]]],
) -> None:
	"""Copy PNGs for the top worst offenders into GALLERY_DIR.

	Args:
		results: Per-file result records.
		engines: Engines used.
		top_n: Count of worst offenders to save.
		png_store: {rel_path: {engine: {orig: png_path, norm: png_path}}}.
	"""
	GALLERY_DIR.mkdir(parents=True, exist_ok=True)

	def get_score(rec: dict) -> int:
		# Max phash distance across engines.
		best = 0
		for eng_data in rec.get("engines", {}).values():
			if eng_data.get("error") is None:
				h = eng_data.get("hamming_phash", 0)
				if h > best:
					best = h
		return best

	valid = [r for r in results if r.get("normalized") and r.get("error") is None]
	valid.sort(key=get_score, reverse=True)
	worst = valid[:top_n]

	for idx, rec in enumerate(worst):
		rel = rec["file"]
		safe_name = Path(rel).name.replace(".svg", "")[:40]
		store = png_store.get(rel, {})

		for engine in engines:
			eng_store = store.get(engine, {})
			eng_data = rec["engines"].get(engine, {})
			if eng_data.get("error") is not None:
				continue

			orig_src = eng_store.get("orig")
			norm_src = eng_store.get("norm")

			if orig_src and Path(orig_src).exists():
				dest = GALLERY_DIR / f"{idx+1:03d}_{safe_name}_{engine}_orig.png"
				shutil.copy2(orig_src, dest)
				eng_data["orig_png_saved"] = str(dest.relative_to(REPO_ROOT))

			if norm_src and Path(norm_src).exists():
				dest = GALLERY_DIR / f"{idx+1:03d}_{safe_name}_{engine}_norm.png"
				shutil.copy2(norm_src, dest)
				eng_data["norm_png_saved"] = str(dest.relative_to(REPO_ROOT))

	print(f"Saved worst-offender PNGs to {GALLERY_DIR} ({len(worst)} entries).")


#============================================
def build_stats(results: list[dict], engines: list[str]) -> dict:
	"""Compute aggregate statistics from result records.

	Args:
		results: List of per-file result dicts.
		engines: Engines used.

	Returns:
		Dict of aggregate stats.
	"""
	stats: dict = {
		"total_files_processed": len(results),
		"normalized_count": sum(1 for r in results if r.get("normalized")),
		"skipped_or_error": sum(1 for r in results if not r.get("normalized") or r.get("error")),
		"engines": {},
		"chromium_vs_firefox": {
			"identical": 0,
			"minor": 0,
			"divergent": 0,
			"unavailable": 0,
		},
	}

	for engine in engines:
		engine_stats: dict = {
			"identical": 0,
			"minor": 0,
			"divergent": 0,
			"render_errors": 0,
			"worst_phash_distance": 0,
		}
		for rec in results:
			eng_data = rec.get("engines", {}).get(engine)
			if eng_data is None:
				continue
			if eng_data.get("error") is not None:
				engine_stats["render_errors"] += 1
				continue
			cls = eng_data.get("classification", "divergent")
			engine_stats[cls] = engine_stats.get(cls, 0) + 1
			h = eng_data.get("hamming_phash", 0)
			if h > engine_stats["worst_phash_distance"]:
				engine_stats["worst_phash_distance"] = h
		stats["engines"][engine] = engine_stats

	# Cross-engine stats.
	for rec in results:
		cls = rec.get("chromium_vs_firefox_classification", "unavailable")
		key = cls if cls in stats["chromium_vs_firefox"] else "unavailable"
		stats["chromium_vs_firefox"][key] = stats["chromium_vs_firefox"].get(key, 0) + 1

	return stats


#============================================
def build_worst_offenders_table(results: list[dict], engines: list[str], top_n: int) -> list[dict]:
	"""Build a sorted list of worst offenders for the Markdown report.

	Args:
		results: All result records.
		engines: Engines used.
		top_n: Count to include.

	Returns:
		List of worst-offender row dicts.
	"""
	valid = [r for r in results if r.get("normalized") and r.get("error") is None]

	def get_max_phash(rec: dict) -> int:
		best = 0
		for eng_data in rec.get("engines", {}).values():
			if eng_data.get("error") is None:
				h = eng_data.get("hamming_phash", 0)
				if h > best:
					best = h
		return best

	valid.sort(key=get_max_phash, reverse=True)
	top = valid[:top_n]

	rows = []
	for rec in top:
		row: dict = {
			"file": rec["file"],
			"max_phash": get_max_phash(rec),
			"cf_hamming": rec.get("chromium_vs_firefox_hamming"),
		}
		for engine in engines:
			eng_data = rec.get("engines", {}).get(engine, {})
			row[f"{engine}_phash"] = eng_data.get("hamming_phash")
			row[f"{engine}_dhash"] = eng_data.get("hamming_dhash")
			row[f"{engine}_classification"] = eng_data.get("classification")
		rows.append(row)
	return rows


#============================================
def write_json_report(results: list[dict], stats: dict, meta: dict) -> None:
	"""Write the JSON report artifact.

	Args:
		results: All result records.
		stats: Aggregate statistics.
		meta: Metadata.
	"""
	payload = {"meta": meta, "stats": stats, "results": results}
	REPORTS_DIR.mkdir(parents=True, exist_ok=True)
	with open(JSON_REPORT, "w") as f:
		json.dump(payload, f, indent=2)
	print(f"JSON report: {JSON_REPORT}")


#============================================
def write_markdown_report(
	stats: dict,
	worst_offenders: list[dict],
	meta: dict,
	engines: list[str],
) -> None:
	"""Write the Markdown summary report.

	Args:
		stats: Aggregate statistics.
		worst_offenders: Top-N worst offender rows.
		meta: Metadata.
		engines: Engines used.
	"""
	md = ""
	md += "# SVG v3 visual regression report\n\n"
	md += f"**Sample mode:** {meta['sample_mode']}  \n"
	md += f"**Files processed:** {stats['total_files_processed']}  \n"
	md += f"**Engines:** {', '.join(meta['engines'])}  \n"
	md += f"**Render size:** {meta['render_size']}x{meta['render_size']} px  \n"
	md += "**Hash type:** phash (primary), dhash (secondary)  \n\n"
	md += "> NOTE: v3 flattens simple clipPaths (allowlist) and rejects complex ones.\n"
	md += "> Only the small simple-clip subset is normalized; most clip-bearing files\n"
	md += "> are rejected (CLIPPATH_UNSUPPORTED_COMPLEX).\n\n"
	md += "> NOTE: The wild verdicts JSON was stale at time of run. This harness\n"
	md += "> pre-screens by running the normalizer fresh on all candidates.\n\n"

	# Per-engine stats.
	for engine in engines:
		es = stats["engines"].get(engine, {})
		md += f"## {engine.capitalize()} engine\n\n"
		md += "| Classification | Count |\n"
		md += "| --- | --- |\n"
		md += f"| identical (distance 0-{IDENTICAL_THRESHOLD}) | {es.get('identical', 0)} |\n"
		md += f"| minor (distance {IDENTICAL_THRESHOLD+1}-{MINOR_THRESHOLD}) | {es.get('minor', 0)} |\n"
		md += f"| divergent (distance >{MINOR_THRESHOLD}) | {es.get('divergent', 0)} |\n"
		md += f"| render errors | {es.get('render_errors', 0)} |\n"
		md += f"| worst phash distance | {es.get('worst_phash_distance', 0)} |\n\n"

	# Cross-engine divergence.
	cf = stats.get("chromium_vs_firefox", {})
	md += "## Chromium vs Firefox divergence (normalized SVGs)\n\n"
	md += "| Classification | Count |\n"
	md += "| --- | --- |\n"
	md += f"| identical | {cf.get('identical', 0)} |\n"
	md += f"| minor | {cf.get('minor', 0)} |\n"
	md += f"| divergent | {cf.get('divergent', 0)} |\n"
	md += f"| unavailable | {cf.get('unavailable', 0)} |\n\n"

	# Worst offenders table.
	md += f"## Top {len(worst_offenders)} worst offenders\n\n"
	if not worst_offenders:
		md += "_No worst offenders to show._\n\n"
	else:
		header_parts = ["| File | Max phash |"]
		for engine in engines:
			header_parts.append(f" {engine} phash | {engine} class |")
		header_parts.append(" CF hamming |")
		md += "".join(header_parts) + "\n"

		sep_parts = ["| --- | --- |"]
		for engine in engines:
			sep_parts.append(" --- | --- |")
		sep_parts.append(" --- |")
		md += "".join(sep_parts) + "\n"

		for row in worst_offenders:
			fname = Path(row["file"]).name
			line = f"| `{fname}` | {row['max_phash']} |"
			for engine in engines:
				ph = row.get(f"{engine}_phash", "-")
				cls = row.get(f"{engine}_classification", "-")
				line += f" {ph} | {cls} |"
			cf_h = row.get("cf_hamming", "-")
			line += f" {cf_h} |"
			md += line + "\n"
		md += "\n"

	# Gallery reference.
	md += "## Worst-offender gallery\n\n"
	md += "Before/after PNG pairs saved under "
	md += "`test-results/svg_visual_regression/` (gitignored).  \n"
	md += "Files are named `NNN_<stem>_<engine>_orig.png` and `NNN_<stem>_<engine>_norm.png`.\n\n"

	# Visual fidelity summary.
	md += "## Visual fidelity assessment\n\n"
	for engine in engines:
		es = stats["engines"].get(engine, {})
		total_e = es.get("identical", 0) + es.get("minor", 0) + es.get("divergent", 0)
		if total_e > 0:
			pct_identical = 100.0 * es["identical"] / total_e
			pct_minor = 100.0 * es.get("minor", 0) / total_e
			pct_divergent = 100.0 * es.get("divergent", 0) / total_e
			md += f"**{engine.capitalize()}:** {pct_identical:.1f}% identical, "
			md += f"{pct_minor:.1f}% minor, {pct_divergent:.1f}% divergent  \n"
	md += "\n"

	REPORTS_DIR.mkdir(parents=True, exist_ok=True)
	clean_md = "\n".join(line.rstrip() for line in md.splitlines()).rstrip() + "\n"
	with open(MD_REPORT, "w") as f:
		f.write(clean_md)
	print(f"Markdown report: {MD_REPORT}")


#============================================
def main() -> None:
	"""Main orchestration entry point."""
	args = parse_args()
	engines = [e.strip() for e in args.engines.split(",") if e.strip()]
	print(f"Engines: {engines}")

	# Collect all SVG paths under OTHER_REPOS/.
	all_svgs = collect_all_svg_paths()
	print(f"Total SVG files in OTHER_REPOS: {len(all_svgs)}")

	GALLERY_DIR.mkdir(parents=True, exist_ok=True)

	with tempfile.TemporaryDirectory() as tmp_dir:
		tmp_path = Path(tmp_dir)

		# Pre-screen to find which SVGs the current normalizer accepts. The
		# passing map already holds each file's normalized output on disk, so
		# no separate normalize pass is needed later (normalize-once).
		if args.full:
			passing_map = prescreen_normalizable(all_svgs, tmp_path, None, SAMPLE_SEED)
			corpus = sorted(passing_map.keys())
			sample_mode = f"full ({len(corpus)} currently-normalizable files)"
		else:
			passing_map = prescreen_normalizable(all_svgs, tmp_path, PRESCREEN_CAP, SAMPLE_SEED)
			candidates = sorted(passing_map.keys())
			corpus = select_sample(candidates, SAMPLE_SIZE, SAMPLE_SEED)
			sample_mode = (
				f"sample ({len(corpus)} of {len(candidates)} passing files, "
				f"screened from {min(PRESCREEN_CAP, len(all_svgs))} candidates, "
				f"seed={SAMPLE_SEED})"
			)

		print(f"Processing: {sample_mode}")

		# Reuse the pre-normalized outputs for the selected corpus.
		norm_map = build_norm_map_for_corpus(corpus, passing_map)

		# Build render manifest (engine-specific output paths).
		# We need separate PNGs per engine for cross-engine comparison.
		# Build the manifest once; the batch renderer is called once per engine
		# with engine-specific output_png paths derived from the engine name.

		# Build per-engine manifest: same SVG paths but different output PNGs.
		per_engine_manifests: dict[str, list[dict]] = {}
		for engine in engines:
			entries = []
			for svg_path in corpus:
				rel = str(svg_path.relative_to(REPO_ROOT))
				norm_path = norm_map.get(rel)
				if norm_path is None:
					continue
				# md5 here names a temp file stem, not a security control.
				stem = hashlib.md5(rel.encode(), usedforsecurity=False).hexdigest()[:10]
				# Engine-specific output paths.
				orig_png = tmp_path / f"png_{stem}_{engine}_orig.png"
				norm_png = tmp_path / f"png_{stem}_{engine}_norm.png"
				entries.append({
					"svg_path": str(svg_path),
					"output_png": str(orig_png),
					"rel_path": rel,
					"kind": "orig",
				})
				entries.append({
					"svg_path": str(norm_path),
					"output_png": str(norm_png),
					"rel_path": rel,
					"kind": "norm",
				})
			per_engine_manifests[engine] = entries

		# Run batch renderer for each engine and compute hashes immediately.
		# per_engine_hashes: {engine: {rel_path: {orig: {phash, dhash}, norm: {phash, dhash}}}}.
		per_engine_hashes: dict[str, dict[str, dict[str, dict]]] = {}
		# png_store: {rel_path: {engine: {orig: png_path_str, norm: png_path_str}}}.
		png_store: dict[str, dict[str, dict[str, str]]] = {}

		for engine in engines:
			manifest_entries = per_engine_manifests[engine]
			render_results = run_batch_render(manifest_entries, engine, tmp_path)
			require_render_evidence(manifest_entries, render_results, engine)

			engine_hashes: dict[str, dict[str, dict]] = {}
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

				hashes = compute_hashes(png_path)

				if rel not in engine_hashes:
					engine_hashes[rel] = {}
				engine_hashes[rel][kind] = hashes

				# Store PNG path for worst-offender gallery.
				if rel not in png_store:
					png_store[rel] = {}
				if engine not in png_store[rel]:
					png_store[rel][engine] = {}
				png_store[rel][engine][kind] = out_png

			per_engine_hashes[engine] = engine_hashes
			print(f"Engine {engine}: hashed {len(engine_hashes)} files.")

		# Assemble final per-file results.
		results = assemble_results(corpus, norm_map, per_engine_hashes, engines)

		# Save worst-offender PNGs BEFORE tmp_dir is cleaned.
		save_worst_offender_pngs(results, engines, GALLERY_TOP_N, png_store)

	# Compute stats and build reports.
	meta: dict = {
		"sample_mode": sample_mode,
		"sample_size": len(corpus),
		"total_svgs_in_corpus": len(all_svgs),
		"engines": engines,
		"render_size": RENDER_SIZE,
		"identical_threshold": IDENTICAL_THRESHOLD,
		"minor_threshold": MINOR_THRESHOLD,
		"gallery_top_n": GALLERY_TOP_N,
		"clip_flatten_note": (
			"v3 flattens simple clipPaths (allowlist) and rejects complex clipPaths "
			"(CLIPPATH_UNSUPPORTED_COMPLEX). Only the small simple-clip subset is normalized."
		),
		"verdicts_json_note": (
			"Wild verdicts JSON was stale (normalizer gained new rejection rules). "
			"This harness pre-screens by running the normalizer fresh on all candidates."
		),
	}

	stats = build_stats(results, engines)
	worst_offenders = build_worst_offenders_table(results, engines, GALLERY_TOP_N)

	write_json_report(results, stats, meta)
	write_markdown_report(stats, worst_offenders, meta, engines)

	# Print headline stats.
	print("\n=== Headline stats ===")
	print(f"Files processed: {stats['total_files_processed']}")
	print(f"Errors/skipped: {stats['skipped_or_error']}")
	for engine in engines:
		es = stats["engines"].get(engine, {})
		print(
			f"{engine}: identical={es.get('identical',0)}, "
			f"minor={es.get('minor',0)}, "
			f"divergent={es.get('divergent',0)}, "
			f"render_errors={es.get('render_errors',0)}, "
			f"worst_phash={es.get('worst_phash_distance',0)}"
		)
	cf = stats.get("chromium_vs_firefox", {})
	print(
		f"chromium_vs_firefox: identical={cf.get('identical',0)}, "
		f"minor={cf.get('minor',0)}, "
		f"divergent={cf.get('divergent',0)}"
	)
	print(f"Reports: {JSON_REPORT} | {MD_REPORT}")
	print(f"Gallery: {GALLERY_DIR}")


if __name__ == "__main__":
	main()
