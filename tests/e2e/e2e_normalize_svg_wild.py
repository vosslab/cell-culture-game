#!/usr/bin/env python3
"""
E2E wild-corpus runner for normalize_svg_v3.py (WP-1c).

Walks every *.svg file under OTHER_REPOS/ (~3000+ files), runs v3 on each in a
temporary output directory, and records a verdict per file:
  - normalized: the file was accepted and written
  - rejected:<CODE>: the file was refused with a RejectionReason

Writes two output artifacts:
  docs/active_plans/reports/normalize_svg_v3_wild_verdicts.json
  docs/active_plans/reports/normalize_svg_v3_wild_verdicts.md

Exit code:
  0: all files produced a clean verdict (normalized or clean rejection)
  1: one or more files produced an UNCLASSIFIED crash (neither normalized nor
     a clean RejectionReason) -- this is a gate failure

Run with:
  source source_me.sh && python3 tests/e2e/e2e_normalize_svg_wild.py
"""

# Standard Library
import os
import sys
import json
import time
import tempfile
import traceback
import subprocess
from pathlib import Path

# Resolve repo root via git so this script works from any working directory.
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
JSON_REPORT = REPORTS_DIR / "normalize_svg_v3_wild_verdicts.json"
MD_REPORT = REPORTS_DIR / "normalize_svg_v3_wild_verdicts.md"


#============================================
def collect_svg_paths(root_dir: Path) -> list[Path]:
	"""Collect all *.svg files under root_dir, sorted for reproducibility.

	Args:
		root_dir: Root directory to walk.

	Returns:
		Sorted list of absolute paths to .svg files.
	"""
	paths: list[Path] = []
	for dirpath, _dirnames, filenames in os.walk(root_dir):
		for filename in filenames:
			if filename.lower().endswith(".svg"):
				paths.append(Path(dirpath) / filename)
	paths.sort()
	return paths


#============================================
def run_one(svg_path: Path, out_dir: Path) -> dict:
	"""Run v3 on one SVG file and return a per-file result record.

	The normalizer writes output to out_dir / svg_path.name. If two files happen
	to share a basename (unlikely across repos but possible), the output simply
	overwrites -- we only care about the NormalizeResult, not the output file.

	On any unhandled exception (crash) the verdict is set to "unclassified_crash"
	so the runner can count them and exit non-zero.

	Args:
		svg_path: Absolute path to the source SVG.
		out_dir: Temporary directory for normalized output.

	Returns:
		Dict matching the plan's per-file report schema.
	"""
	# Construct a unique output path under out_dir using a flat name derived from
	# the last two path components to reduce collision risk.
	safe_name = svg_path.parent.name + "__" + svg_path.name
	out_path = out_dir / safe_name

	verdict = "unclassified_crash"
	primary_reason_code = None
	message = None
	fix = None
	element = None
	secondary_reason_codes: list[str] = []
	output_written = False
	crash_traceback = None

	try:
		result = tools.svg_normalizer.workflow.normalize_svg_file(svg_path, out_path, padding=2.0)
		output_written = result.output_written
		secondary_reason_codes = list(result.secondary_reason_codes)
		if result.normalized:
			verdict = "normalized"
		else:
			rejection = result.rejection
			verdict = f"rejected:{rejection.code}"
			primary_reason_code = rejection.code
			message = rejection.message
			fix = rejection.fix
			element = rejection.element
	except Exception:
		# Any unhandled exception is an UNCLASSIFIED crash -- a gate failure.
		crash_traceback = traceback.format_exc()
		verdict = "unclassified_crash"
		output_written = False

	record: dict = {
		"file": str(svg_path.relative_to(REPO_ROOT)),
		"verdict": verdict,
		"primary_reason_code": primary_reason_code,
		"message": message,
		"fix": fix,
		"element": element,
		"secondary_reason_codes": secondary_reason_codes,
		"features_seen": [],
		"refs_checked": False,
		"output_written": output_written,
	}
	# Include crash info for diagnosis when present.
	if crash_traceback is not None:
		record["crash_traceback"] = crash_traceback
	return record


#============================================
def build_markdown_summary(records: list[dict], elapsed: float) -> str:
	"""Build a grouped Markdown summary of the wild-corpus run.

	Groups rejected files by reason code with counts. Normalized count is a single
	summary line. Unclassified crashes (gate failures) are listed individually for
	diagnosis.

	Args:
		records: Per-file result dicts from run_one().
		elapsed: Total wall-clock seconds for the run.

	Returns:
		Markdown text as a string.
	"""
	total = len(records)
	normalized_count = sum(1 for r in records if r["verdict"] == "normalized")
	crash_count = sum(1 for r in records if r["verdict"] == "unclassified_crash")
	rejected_count = total - normalized_count - crash_count

	# Count rejections by reason code.
	code_counts: dict[str, int] = {}
	for rec in records:
		if rec["verdict"].startswith("rejected:"):
			code = rec["primary_reason_code"] or "UNKNOWN"
			code_counts[code] = code_counts.get(code, 0) + 1

	lines: list[str] = []
	lines.append("# SVG Normalizer v3 wild-corpus verdicts")
	lines.append("")
	lines.append("Generated by `tests/e2e/e2e_normalize_svg_wild.py` (WP-1c).")
	lines.append("")
	lines.append("## Summary")
	lines.append("")
	lines.append(f"- Total files: {total}")
	lines.append(f"- Normalized: {normalized_count}")
	lines.append(f"- Rejected: {rejected_count}")
	lines.append(f"- Unclassified crashes: {crash_count}")
	lines.append(f"- Elapsed: {elapsed:.1f}s")
	lines.append("")

	if code_counts:
		lines.append("## Rejections by reason code")
		lines.append("")
		lines.append("| Reason code | Count |")
		lines.append("| --- | --- |")
		# Sort by count descending for easy review.
		for code, count in sorted(code_counts.items(), key=lambda kv: -kv[1]):
			lines.append(f"| `{code}` | {count} |")
		lines.append("")

	if crash_count > 0:
		lines.append("## Unclassified crashes (gate failures)")
		lines.append("")
		lines.append("These files produced an unhandled exception -- each is a bug in v3.")
		lines.append("")
		for rec in records:
			if rec["verdict"] == "unclassified_crash":
				lines.append(f"- `{rec['file']}`")
				tb = rec.get("crash_traceback", "")
				if tb:
					# Indent traceback for readability.
					lines.append("")
					lines.append("  ```")
					for tb_line in tb.strip().splitlines():
						lines.append(f"  {tb_line}")
					lines.append("  ```")
					lines.append("")
		lines.append("")

	lines.append("## Next steps")
	lines.append("")
	lines.append(
		"The rejection counts above identify which feature classes to invest in next. "
		"A rejection class graduates from reject to normalize only when a tested "
		"implementation is added to v3. The gate is never loosened to pass ambiguous files."
	)
	lines.append("")

	return "\n".join(lines)


#============================================
def main() -> int:
	"""Walk OTHER_REPOS, run v3 on every SVG, write reports, exit 0 or 1.

	Returns:
		0 if all files ended as normalized or clean rejections (zero crashes).
		1 if any file produced an unclassified crash.
	"""
	if not OTHER_REPOS.exists():
		print(f"ERROR: OTHER_REPOS not found at {OTHER_REPOS}", file=sys.stderr)
		return 1

	svg_paths = collect_svg_paths(OTHER_REPOS)
	if not svg_paths:
		print(f"ERROR: no .svg files found under {OTHER_REPOS}", file=sys.stderr)
		return 1

	print(f"Wild runner: {len(svg_paths)} SVG files under {OTHER_REPOS}")

	start_time = time.time()

	records: list[dict] = []
	crash_count = 0

	# Use a single shared temp dir for all output so we only create one tmpdir and
	# clean it up at the end.
	with tempfile.TemporaryDirectory(prefix="normalize-svg-v3-wild-") as tmp_str:
		out_dir = Path(tmp_str)
		for idx, svg_path in enumerate(svg_paths):
			# Progress dot every 100 files so long runs are not silent.
			if idx > 0 and idx % 100 == 0:
				elapsed_so_far = time.time() - start_time
				print(f"  [{idx}/{len(svg_paths)}] {elapsed_so_far:.1f}s elapsed ...")
			record = run_one(svg_path, out_dir)
			records.append(record)
			if record["verdict"] == "unclassified_crash":
				crash_count += 1
				# Print crash info immediately so it is visible even if the run is slow.
				print(f"CRASH: {record['file']}", file=sys.stderr)
				tb = record.get("crash_traceback", "")
				if tb:
					print(tb, file=sys.stderr)

	elapsed = time.time() - start_time

	# Write reports.
	REPORTS_DIR.mkdir(parents=True, exist_ok=True)

	json_text = json.dumps(records, indent=2)
	JSON_REPORT.write_text(json_text, encoding="utf-8")

	md_text = build_markdown_summary(records, elapsed)
	MD_REPORT.write_text(md_text, encoding="utf-8")

	# Print headline counts to stdout.
	total = len(records)
	normalized = sum(1 for r in records if r["verdict"] == "normalized")
	rejected = total - normalized - crash_count
	print(f"\nWild run complete: {total} files in {elapsed:.1f}s")
	print(f"  normalized:         {normalized}")
	print(f"  rejected:           {rejected}")
	print(f"  unclassified_crash: {crash_count}")

	# Count rejections by code for headline display.
	code_counts: dict[str, int] = {}
	for rec in records:
		if rec["verdict"].startswith("rejected:"):
			code = rec["primary_reason_code"] or "UNKNOWN"
			code_counts[code] = code_counts.get(code, 0) + 1
	if code_counts:
		print("  rejection breakdown:")
		for code, count in sorted(code_counts.items(), key=lambda kv: -kv[1]):
			print(f"    {code}: {count}")

	print("\nReports written to:")
	print(f"  {JSON_REPORT}")
	print(f"  {MD_REPORT}")

	if crash_count > 0:
		print(f"\nGATE FAILURE: {crash_count} unclassified crash(es). See report.", file=sys.stderr)
		return 1
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
