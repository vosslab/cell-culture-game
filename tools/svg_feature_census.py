#!/usr/bin/env python3
"""
Feature census for the wild SVG corpus under OTHER_REPOS/.

Answers "how many SVGs had clipping and other normalization requirements"
independent of the accept/reject verdict. A file can carry a clipPath and
still be rejected for an unrelated reason (text, filter), so the primary
rejection reason alone undercounts feature prevalence. This census walks
every element of every SVG and records, per file, whether each
normalization-relevant feature is present. It then cross-tabulates feature
presence against the current v3 verdict.

Read-only: parses inputs, writes only the two report artifacts. It never
writes normalized SVGs and never mutates the corpus.

Outputs:
  docs/active_plans/reports/svg_feature_census.json
  docs/active_plans/reports/svg_feature_census.md

Run:
  source source_me.sh && python3 tools/svg_feature_census.py
"""

# Standard Library
import json
import subprocess
from pathlib import Path

# PIP3 modules
import lxml.etree

# Resolve repo root via git so this script works from any cwd.
_GIT_RESULT = subprocess.run(
	["git", "rev-parse", "--show-toplevel"],
	capture_output=True,
	text=True,
	check=True,
)
REPO_ROOT = Path(_GIT_RESULT.stdout.strip())

import tools.svg_normalizer.clips
import tools.svg_normalizer.document
import tools.svg_normalizer.model
import tools.svg_normalizer.sanitization
import tools.svg_normalizer.workflow

OTHER_REPOS = REPO_ROOT / "OTHER_REPOS"
REPORTS_DIR = REPO_ROOT / "docs" / "active_plans" / "reports"
JSON_REPORT = REPORTS_DIR / "svg_feature_census.json"
MD_REPORT = REPORTS_DIR / "svg_feature_census.md"

# Geometry-affecting CSS properties used to flag <style>/inline style geometry.
GEOMETRY_CSS_PROPS = frozenset({
	"transform", "d", "x", "y", "cx", "cy", "r", "rx", "ry",
	"width", "height", "clip-path", "x1", "y1", "x2", "y2", "points",
})


#============================================
def local_tag(elem: lxml.etree._Element) -> str:
	"""Return the namespace-stripped lowercase tag name for an element.

	Comment/PI nodes have a callable tag; those return an empty string.

	Args:
		elem: An lxml element.

	Returns:
		Lowercase local tag name, or empty string for non-element nodes.
	"""
	tag = elem.tag
	if not isinstance(tag, str):
		return ""
	return tools.svg_normalizer.model.local_name(tag).lower()


#============================================
def empty_feature_record() -> dict:
	"""Return a fresh per-file feature record with all flags off.

	Returns:
		Dict of feature-name -> False, plus integer counters at 0.
	"""
	record = {
		"clip_path": False,
		"transform_attr": False,
		"nested_groups": False,
		"text": False,
		"shape_rect": False,
		"shape_circle": False,
		"shape_ellipse": False,
		"shape_line": False,
		"shape_polyline": False,
		"shape_polygon": False,
		"gradient": False,
		"pattern": False,
		"filter": False,
		"mask": False,
		"marker": False,
		"use_or_symbol": False,
		"image": False,
		"foreign_object": False,
		"script_or_handler": False,
		"animation": False,
		"style_block": False,
		"inline_style": False,
		"non_ascii_id": False,
		"attribution": False,
		"parse_error": False,
	}
	return record


#============================================
def scan_svg_features(svg_path: Path) -> dict:
	"""Parse one SVG and record which normalization-relevant features it uses.

	Args:
		svg_path: Absolute path to the SVG file.

	Returns:
		A per-file feature record (see empty_feature_record).
	"""
	record = empty_feature_record()

	# Parse without recovery; a parse failure is itself a recorded feature.
	parser = lxml.etree.XMLParser(recover=False)
	tree = _try_parse(svg_path, parser)
	if tree is None:
		record["parse_error"] = True
		return record

	root = tree.getroot()
	group_depth_seen = _max_group_depth(root)
	if group_depth_seen >= 2:
		record["nested_groups"] = True

	for elem in root.iter():
		tag = local_tag(elem)
		if tag == "":
			continue
		_flag_tag(record, tag)
		_flag_attributes(record, elem)

	return record


#============================================
def _try_parse(svg_path: Path, parser: lxml.etree.XMLParser) -> object:
	"""Parse an SVG file, returning the tree or None on failure.

	Two-line try/except is permitted here: a malformed wild SVG is expected
	input for a census and its failure is a recorded data point.

	Args:
		svg_path: Path to the SVG.
		parser: Configured lxml parser.

	Returns:
		The parsed ElementTree, or None if parsing failed.
	"""
	try:
		return lxml.etree.parse(str(svg_path), parser)
	except (lxml.etree.XMLSyntaxError, OSError, ValueError):
		return None


#============================================
def _max_group_depth(root: lxml.etree._Element) -> int:
	"""Return the maximum nesting depth of <g> elements under root.

	Args:
		root: The SVG root element.

	Returns:
		Deepest chain length of nested <g> elements (0 if none).
	"""
	best = 0

	def walk(elem: lxml.etree._Element, depth: int) -> None:
		nonlocal best
		for child in elem:
			child_depth = depth
			if local_tag(child) == "g":
				child_depth = depth + 1
				if child_depth > best:
					best = child_depth
			walk(child, child_depth)

	walk(root, 0)
	return best


#============================================
def _flag_tag(record: dict, tag: str) -> None:
	"""Set feature flags implied by an element's tag name.

	Args:
		record: The per-file feature record to mutate.
		tag: Lowercase local tag name.
	"""
	tag_to_flag = {
		"clippath": "clip_path",
		"text": "text",
		"tspan": "text",
		"textpath": "text",
		"rect": "shape_rect",
		"circle": "shape_circle",
		"ellipse": "shape_ellipse",
		"line": "shape_line",
		"polyline": "shape_polyline",
		"polygon": "shape_polygon",
		"lineargradient": "gradient",
		"radialgradient": "gradient",
		"pattern": "pattern",
		"filter": "filter",
		"mask": "mask",
		"marker": "marker",
		"use": "use_or_symbol",
		"symbol": "use_or_symbol",
		"image": "image",
		"foreignobject": "foreign_object",
		"script": "script_or_handler",
		"style": "style_block",
	}
	if tag in tag_to_flag:
		record[tag_to_flag[tag]] = True
	if tag in ("animate", "animatetransform", "animatemotion", "set"):
		record["animation"] = True


#============================================
def _flag_attributes(record: dict, elem: lxml.etree._Element) -> None:
	"""Set feature flags implied by an element's attributes.

	Args:
		record: The per-file feature record to mutate.
		elem: The element whose attributes are inspected.
	"""
	for attr_name, attr_value in elem.attrib.items():
		local = tools.svg_normalizer.model.local_name(attr_name).lower()
		if local == "transform":
			record["transform_attr"] = True
		elif local == "style":
			record["inline_style"] = True
		elif local == "id":
			if not _is_ascii(attr_value):
				record["non_ascii_id"] = True
		elif local.startswith("on"):
			record["script_or_handler"] = True
	# Attribution lives in the dc/cc/rdf namespaces.
	ns_uri = lxml.etree.QName(elem).namespace if elem.tag and isinstance(elem.tag, str) else None
	if ns_uri and ("dc/elements" in ns_uri or "creativecommons" in ns_uri or "rdf-syntax" in ns_uri):
		record["attribution"] = True


#============================================
def _is_ascii(value: str) -> bool:
	"""Return True if every character in value is ASCII.

	Args:
		value: String to test.

	Returns:
		True if pure ASCII, else False.
	"""
	return all(ord(ch) < 128 for ch in value)


#============================================
def get_verdict(svg_path: Path) -> str:
	"""Run the v3 normalizer on a file and return its primary reason code.

	This is the FIRST-WINS primary verdict (normalize_svg_file short-circuits
	on the first detector that fires). It is kept for backward continuity; the
	new all-reasons model lives in collect_reasons.

	The output is written to a throwaway path that is removed immediately;
	only the verdict is kept.

	Args:
		svg_path: Path to the SVG.

	Returns:
		"normalized" if accepted, else the primary rejection reason code.
	"""
	out_path = REPORTS_DIR / "_census_scratch_out.svg"
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_path, out_path)
	if out_path.exists():
		out_path.unlink()
	if result.normalized:
		return "normalized"
	if result.rejection is not None:
		return result.rejection.code
	return "rejected:UNKNOWN"


# Every standalone detector in normalize_svg_v3, each taking the parsed root and
# returning a RejectionReason or None. These are run independently (no first-wins
# short-circuit) so a file's FULL set of applicable reasons is recorded. The
# DOCTYPE/ENTITY raw-text scan is handled separately in collect_reasons because
# its signature takes source text, not the parsed root.
_STANDALONE_DETECTORS = (
	tools.svg_normalizer.document._detect_text_elements,
	tools.svg_normalizer.sanitization._detect_script_or_handler,
	tools.svg_normalizer.sanitization._detect_animation_elements,
	tools.svg_normalizer.sanitization._detect_foreignobject,
	tools.svg_normalizer.sanitization._detect_use_or_symbol,
	tools.svg_normalizer.sanitization._detect_filter,
	tools.svg_normalizer.sanitization._detect_mask,
	tools.svg_normalizer.sanitization._detect_marker,
	tools.svg_normalizer.sanitization._detect_image,
	tools.svg_normalizer.sanitization._detect_external_href,
	tools.svg_normalizer.clips._detect_clippath,
	tools.svg_normalizer.clips._detect_style_geometry,
	tools.svg_normalizer.clips._detect_pattern,
)


#============================================
def collect_reasons(svg_path: Path) -> list[str]:
	"""Return EVERY applicable rejection reason code for one file.

	Unlike get_verdict (first-wins), this runs all detectors independently and
	records every distinct reason that applies, so files with multiple stacked
	blockers are visible.

	Pipeline:
	  - Read the raw text. A non-UTF-8 file cannot be scanned -> PARSER_ERROR.
	  - Parse without recovery. A parse failure means the file's other reasons
	    cannot be assessed at all, so PARSER_ERROR is recorded ALONE. This is an
	    accepted limitation of the all-reasons model: a recovering parser is not
	    reimplemented here just to surface secondary reasons on broken XML.
	  - Run the raw-text DOCTYPE/ENTITY scan and add its code if it fires.
	  - Run every standalone detector on the parsed root and add each non-None
	    reason code (no first-wins short-circuit).

	Note: EMBEDDED_RASTER_UNSUPPORTED, EXTERNAL_RESOURCE_UNSUPPORTED,
	EMPTY_GEOMETRY, and CLIPPATH_UNSUPPORTED_COMPLEX are produced inside
	normalize_svg_file / flatten_clip_paths, not by a standalone detector, so
	they are intentionally outside this all-reasons scan.

	Args:
		svg_path: Path to the SVG.

	Returns:
		Sorted list of distinct reason codes; empty when the file normalizes.
	"""
	# A non-UTF-8 file cannot have its text or tree assessed; record PARSER_ERROR
	# alone (same limitation as the parse-failure case below).
	try:
		source_text = svg_path.read_text(encoding="utf-8")
	except UnicodeDecodeError:
		return ["PARSER_ERROR"]

	# Parse without recovery. A file that cannot be parsed cannot have its other
	# reasons assessed, so PARSER_ERROR is recorded alone (accepted limitation;
	# a recovering parser is deliberately NOT reimplemented in the census).
	parser = lxml.etree.XMLParser(
		recover=False,
		resolve_entities=False,
		no_network=True,
		huge_tree=False,
	)
	tree = _try_parse(svg_path, parser)
	if tree is None:
		return ["PARSER_ERROR"]

	root = tree.getroot()
	reasons: set[str] = set()

	# Raw-text DOCTYPE/ENTITY scan (signature takes source text, not the root).
	doctype_reason = tools.svg_normalizer.sanitization.detect_doctype_or_entity(source_text)
	if doctype_reason is not None:
		reasons.add(doctype_reason.code)

	# Run every standalone detector independently; add each non-None code.
	for detector in _STANDALONE_DETECTORS:
		reason = detector(root)
		if reason is not None:
			reasons.add(reason.code)

	return sorted(reasons)


#============================================
def collect_paths() -> list[Path]:
	"""Collect all SVG paths under OTHER_REPOS/, sorted for reproducibility.

	Returns:
		Sorted list of absolute SVG paths.
	"""
	return sorted(OTHER_REPOS.rglob("*.svg"))


#============================================
def build_census(paths: list[Path]) -> list[dict]:
	"""Scan features and verdict for every corpus file.

	Args:
		paths: All corpus SVG paths.

	Returns:
		List of per-file dicts: {file, verdict, reasons, primary_agrees, features}.
		verdict is the FIRST-WINS primary; reasons is the ALL-REASONS set.
	"""
	rows = []
	total = len(paths)
	for idx, svg_path in enumerate(paths):
		if idx % 250 == 0:
			pct = 100.0 * (idx + 1) / total
			print(f"  census [{idx + 1}/{total}] {pct:.0f}%")
		features = scan_svg_features(svg_path)
		verdict = get_verdict(svg_path)
		reasons = collect_reasons(svg_path)
		# The true gate is normalize_svg_file (the first-wins verdict). The all-
		# reasons scan only runs STANDALONE detectors, so inside-pipeline reject
		# codes (EMPTY_GEOMETRY, CLIPPATH_UNSUPPORTED_COMPLEX, raster, external)
		# never appear there. Fold the true verdict code into `reasons` for every
		# non-normalized file when it is not already present. After this fold,
		# len(reasons) == 0 holds if and only if the file truly normalizes, so the
		# multiplicity-zero bucket and the normalize rate match the real gate.
		if verdict != "normalized" and verdict not in reasons:
			reasons = sorted(set(reasons) | {verdict})
		# Cross-check: after folding, a normalized verdict has no reasons and a
		# rejected verdict's code is guaranteed present, so the two models agree
		# for single-blocker files and disagreement only flags genuine anomalies.
		if verdict == "normalized":
			primary_agrees = len(reasons) == 0
		else:
			primary_agrees = verdict in reasons
		rel = str(svg_path.relative_to(REPO_ROOT))
		rows.append({
			"file": rel,
			"verdict": verdict,
			"reasons": reasons,
			"primary_agrees": primary_agrees,
			"features": features,
		})
	return rows


#============================================
def tally_features(rows: list[dict]) -> dict:
	"""Count how many files carry each feature.

	Args:
		rows: Per-file census rows.

	Returns:
		Dict feature-name -> count of files with that feature.
	"""
	counts: dict[str, int] = {}
	for row in rows:
		for name, present in row["features"].items():
			if present:
				counts[name] = counts.get(name, 0) + 1
	return counts


#============================================
def tally_verdicts(rows: list[dict]) -> dict:
	"""Count files per verdict (normalized + each rejection reason).

	Args:
		rows: Per-file census rows.

	Returns:
		Dict verdict -> count.
	"""
	counts: dict[str, int] = {}
	for row in rows:
		v = row["verdict"]
		counts[v] = counts.get(v, 0) + 1
	return counts


#============================================
def crosstab_feature_verdict(rows: list[dict], feature: str) -> dict:
	"""For one feature, count verdicts among files that carry it.

	Args:
		rows: Per-file census rows.
		feature: Feature name to filter on.

	Returns:
		Dict verdict -> count, restricted to files with the feature.
	"""
	counts: dict[str, int] = {}
	for row in rows:
		if row["features"].get(feature):
			v = row["verdict"]
			counts[v] = counts.get(v, 0) + 1
	return counts


#============================================
def tally_reason_presence(rows: list[dict]) -> dict:
	"""Count, per reason code, how many files carry it anywhere in `reasons`.

	These are OVERLAPPING file-presence counts: a file with three reasons adds
	one to three different reason codes, so the columns do NOT sum to the corpus
	total.

	Args:
		rows: Per-file census rows.

	Returns:
		Dict reason-code -> count of files whose `reasons` include that code.
	"""
	counts: dict[str, int] = {}
	for row in rows:
		for code in row["reasons"]:
			counts[code] = counts.get(code, 0) + 1
	return counts


#============================================
def multiplicity_histogram(rows: list[dict]) -> dict:
	"""Bucket files by how many distinct reasons block them.

	Buckets: 0 (normalized), 1, 2, 3, and "4+".

	Args:
		rows: Per-file census rows.

	Returns:
		Dict bucket-label -> file count, with keys "0", "1", "2", "3", "4+".
	"""
	hist = {"0": 0, "1": 0, "2": 0, "3": 0, "4+": 0}
	for row in rows:
		n = len(row["reasons"])
		if n >= 4:
			hist["4+"] += 1
		else:
			hist[str(n)] += 1
	return hist


# Verdict code for the intentional, permanent raster-embedding rejection. An SVG
# embedding a raster image is by design out of scope and can never normalize, so
# it is excluded from the adjusted (supportable-corpus) scoring denominator.
RASTER_REJECT_VERDICT = "EMBEDDED_RASTER_UNSUPPORTED"


#============================================
def compute_scoring(rows: list[dict], normalized: int) -> dict:
	"""Compute raw and raster-adjusted normalize-rate scoring.

	The adjusted rate removes intentional raster-embedding rejects from the
	denominator. Membership uses the FIRST-WINS `verdict` field, because the
	raster code is produced inside normalize_svg_file and is therefore the
	verdict, not a standalone all-reasons code.

	Args:
		rows: Per-file census rows (each carries a `verdict`).
		normalized: Count of files that normalize (zero blockers).

	Returns:
		Dict with raw and adjusted totals and rates.
	"""
	total = len(rows)
	# Count files whose first-wins verdict is the intentional raster rejection.
	raster_reject_count = 0
	for row in rows:
		if row["verdict"] == RASTER_REJECT_VERDICT:
			raster_reject_count += 1
	# The supportable corpus excludes intentional raster rejects from scoring.
	supportable_total = total - raster_reject_count
	raw_rate = 100.0 * normalized / total if total else 0.0
	adjusted_rate = 100.0 * normalized / supportable_total if supportable_total else 0.0
	scoring = {
		"total_files": total,
		"normalized": normalized,
		"raster_reject_count": raster_reject_count,
		"supportable_total": supportable_total,
		"normalized_rate_raw": raw_rate,
		"normalized_rate_adjusted": adjusted_rate,
	}
	return scoring


#============================================
def cooccurrence_for_reason(rows: list[dict], code: str) -> dict:
	"""Measure stacked blockers for one reason bucket.

	For every file that carries `code`, report how many ALSO carry at least one
	other distinct reason. Those files would NOT normalize even if this one
	bucket were solved.

	Args:
		rows: Per-file census rows.
		code: The reason code to analyze.

	Returns:
		Dict with keys: "files" (files carrying code), "with_other" (of those,
		how many carry an additional distinct reason), and "solo" (carry only
		this reason).
	"""
	files = 0
	with_other = 0
	for row in rows:
		reasons = row["reasons"]
		if code not in reasons:
			continue
		files += 1
		# An additional distinct reason means solving this bucket alone is not
		# enough to make the file normalize.
		if len(reasons) > 1:
			with_other += 1
	solo = files - with_other
	return {"files": files, "with_other": with_other, "solo": solo}


# The three biggest reject buckets called out by the plan for the stacked-blocker
# co-occurrence view.
COOCCURRENCE_CODES = (
	"STYLE_GEOMETRY_UNSUPPORTED",
	"TEXT_UNSUPPORTED",
	"DOCTYPE_OR_ENTITY",
)


#============================================
def write_json(
	rows: list[dict],
	feature_counts: dict,
	verdict_counts: dict,
	reason_presence: dict,
	multiplicity: dict,
	cooccurrence: dict,
	scoring: dict,
) -> None:
	"""Write the machine-readable census report.

	Args:
		rows: Per-file census rows (each carries `reasons` and `features`).
		feature_counts: Feature -> file count.
		verdict_counts: First-wins verdict -> file count.
		reason_presence: Reason code -> overlapping file-presence count.
		multiplicity: Blocker-count bucket -> file count.
		cooccurrence: Reason code -> {files, with_other, solo}.
		scoring: Raw and raster-adjusted normalize-rate scoring.
	"""
	payload = {
		"meta": {
			"total_files": len(rows),
			"corpus_root": "OTHER_REPOS/",
			"raster_reject_count": scoring["raster_reject_count"],
			"supportable_total": scoring["supportable_total"],
			"normalized_rate_raw": scoring["normalized_rate_raw"],
			"normalized_rate_adjusted": scoring["normalized_rate_adjusted"],
			"scoring_note": (
				"normalized_rate_adjusted excludes intentional raster-embedding "
				"rejects (verdict EMBEDDED_RASTER_UNSUPPORTED) from the denominator: "
				"supportable_total = total_files - raster_reject_count. Such SVGs are "
				"by design out of scope and can never normalize."
			),
			"note": (
				"Feature presence is independent of verdict. A file may carry a "
				"clipPath and still be rejected for an unrelated reason. The "
				"`reasons` list per row is the ALL-REASONS set (every applicable "
				"rejection code, no first-wins short-circuit); `verdict` is the "
				"first-wins primary kept for backward continuity. PARSER_ERROR is "
				"recorded alone because a file that cannot parse cannot have its "
				"other reasons assessed."
			),
			"reason_presence_note": (
				"reason_presence counts are OVERLAPPING file-presence counts: a "
				"file with N reasons contributes to N codes, so these columns do "
				"NOT sum to total_files."
			),
		},
		"feature_counts": feature_counts,
		"verdict_counts": verdict_counts,
		"reason_presence": reason_presence,
		"multiplicity_histogram": multiplicity,
		"cooccurrence": cooccurrence,
		"rows": rows,
	}
	REPORTS_DIR.mkdir(parents=True, exist_ok=True)
	with open(JSON_REPORT, "w") as f:
		json.dump(payload, f, indent=2)
	print(f"JSON report: {JSON_REPORT}")


#============================================
def write_markdown(
	rows: list[dict],
	feature_counts: dict,
	verdict_counts: dict,
	reason_presence: dict,
	multiplicity: dict,
	cooccurrence: dict,
	scoring: dict,
) -> None:
	"""Write the human-readable census summary.

	Args:
		rows: Per-file census rows.
		feature_counts: Feature -> file count.
		verdict_counts: First-wins verdict -> file count.
		reason_presence: Reason code -> overlapping file-presence count.
		multiplicity: Blocker-count bucket -> file count.
		cooccurrence: Reason code -> {files, with_other, solo}.
		scoring: Raw and raster-adjusted normalize-rate scoring.
	"""
	total = len(rows)
	normalized = multiplicity["0"]
	raster = scoring["raster_reject_count"]
	supportable_total = scoring["supportable_total"]
	raw_rate = scoring["normalized_rate_raw"]
	adjusted_rate = scoring["normalized_rate_adjusted"]
	md = ""
	md += "# SVG corpus feature census\n\n"
	md += f"Corpus: every `*.svg` under `OTHER_REPOS/` ({total} files).  \n"
	md += "Feature presence is counted per file and is independent of the v3\n"
	md += "verdict: a file may carry a clipPath yet be rejected for text. Use\n"
	md += "this census to size each normalization requirement across the corpus.\n\n"

	# Normalize-rate scoring: raw, then adjusted to exclude intentional raster
	# rejects from the denominator (the supportable corpus).
	md += "## Normalize rate\n\n"
	md += "\"Normalized\" is defined as the true `normalize_svg_file` outcome (the\n"
	md += "first-wins verdict). Inside-pipeline reject codes (`EMPTY_GEOMETRY`,\n"
	md += "`CLIPPATH_UNSUPPORTED_COMPLEX`) are folded into each non-normalized\n"
	md += "file's reasons list from the verdict because they are not standalone\n"
	md += "detectors, so zero reasons means the file truly normalizes.\n\n"
	md += f"Normalized: {normalized} / {total} (raw {raw_rate:.1f}%)  \n"
	md += f"Normalized (excluding intentional raster rejects): {normalized} / "
	md += f"({total} - {raster}) = {normalized} / {supportable_total} "
	md += f"(adjusted {adjusted_rate:.1f}%)  \n"
	md += "Raster-embedding SVGs (verdict `EMBEDDED_RASTER_UNSUPPORTED`) are\n"
	md += "intentionally unsupported and excluded from the adjusted denominator.\n\n"

	# All-reasons reason presence. These counts overlap and do not sum to total.
	md += "## Reason presence (all-reasons, overlapping)\n\n"
	md += "Each file's full set of applicable rejection reasons is computed with\n"
	md += "no first-wins short-circuit. The counts below are overlapping file-\n"
	md += "presence counts: a file with several reasons is counted under each one,\n"
	md += "so these columns do NOT sum to the corpus total of "
	md += f"{total} files.\n\n"
	md += "| Reason | Files with reason | Percent of corpus |\n"
	md += "| --- | --- | --- |\n"
	for code, count in sorted(reason_presence.items(), key=lambda kv: kv[1], reverse=True):
		pct = 100.0 * count / total
		md += f"| {code} | {count} | {pct:.1f}% |\n"
	md += "\n"

	# Blocker-multiplicity histogram: how many independent reasons block a file.
	md += "## Blocker multiplicity histogram\n\n"
	md += "How many distinct rejection reasons apply to each file. Zero reasons\n"
	md += "means the file normalizes.\n\n"
	md += "| Distinct reasons | Files | Percent |\n"
	md += "| --- | --- | --- |\n"
	for bucket in ("0", "1", "2", "3", "4+"):
		count = multiplicity[bucket]
		pct = 100.0 * count / total
		label = f"{bucket} (normalized)" if bucket == "0" else bucket
		md += f"| {label} | {count} | {pct:.1f}% |\n"
	md += "\n"
	md += f"Normalized (zero reasons): {normalized} of {total} files "
	md += f"({100.0 * normalized / total:.1f}%).\n\n"

	# Stacked-blocker co-occurrence for the three biggest reject buckets.
	md += "## Stacked-blocker co-occurrence\n\n"
	md += "For each of the three biggest reject buckets, how many of its files\n"
	md += "ALSO carry at least one other distinct reason. Those files would NOT\n"
	md += "normalize even if that one bucket were fully solved.\n\n"
	md += "| Reason | Files with reason | Also blocked by another | Solved by this bucket alone |\n"
	md += "| --- | --- | --- | --- |\n"
	for code in COOCCURRENCE_CODES:
		stats = cooccurrence[code]
		md += f"| {code} | {stats['files']} | {stats['with_other']} | {stats['solo']} |\n"
	md += "\n"

	# Feature prevalence table, sorted by count descending.
	md += "## Feature prevalence\n\n"
	md += "| Feature | Files | Percent |\n"
	md += "| --- | --- | --- |\n"
	for name, count in sorted(feature_counts.items(), key=lambda kv: kv[1], reverse=True):
		pct = 100.0 * count / total
		md += f"| {name} | {count} | {pct:.1f}% |\n"
	md += "\n"

	# Verdict distribution.
	md += "## Verdict distribution\n\n"
	md += "| Verdict | Files | Percent |\n"
	md += "| --- | --- | --- |\n"
	for verdict, count in sorted(verdict_counts.items(), key=lambda kv: kv[1], reverse=True):
		pct = 100.0 * count / total
		md += f"| {verdict} | {count} | {pct:.1f}% |\n"
	md += "\n"

	# Clipping deep-dive, since it is the headline question.
	md += "## Clipping deep-dive\n\n"
	clip_total = feature_counts.get("clip_path", 0)
	md += f"Files containing a `clipPath`: {clip_total} "
	md += f"({100.0 * clip_total / total:.1f}% of corpus).  \n\n"
	clip_verdicts = crosstab_feature_verdict(rows, "clip_path")
	md += "Verdict among clipPath-bearing files:\n\n"
	md += "| Verdict | Files |\n"
	md += "| --- | --- |\n"
	for verdict, count in sorted(clip_verdicts.items(), key=lambda kv: kv[1], reverse=True):
		md += f"| {verdict} | {count} |\n"
	md += "\n"

	# Transform deep-dive, the other major normalization requirement.
	md += "## Transform deep-dive\n\n"
	tf_total = feature_counts.get("transform_attr", 0)
	md += f"Files containing a `transform=` attribute: {tf_total} "
	md += f"({100.0 * tf_total / total:.1f}% of corpus).  \n\n"
	tf_verdicts = crosstab_feature_verdict(rows, "transform_attr")
	md += "Verdict among transform-bearing files:\n\n"
	md += "| Verdict | Files |\n"
	md += "| --- | --- |\n"
	for verdict, count in sorted(tf_verdicts.items(), key=lambda kv: kv[1], reverse=True):
		md += f"| {verdict} | {count} |\n"
	md += "\n"

	REPORTS_DIR.mkdir(parents=True, exist_ok=True)
	with open(MD_REPORT, "w") as f:
		f.write(md)
	print(f"Markdown report: {MD_REPORT}")


#============================================
def main() -> None:
	"""Main orchestration entry point."""
	paths = collect_paths()
	print(f"Total SVG files under OTHER_REPOS/: {len(paths)}")

	rows = build_census(paths)
	feature_counts = tally_features(rows)
	verdict_counts = tally_verdicts(rows)
	reason_presence = tally_reason_presence(rows)
	multiplicity = multiplicity_histogram(rows)
	cooccurrence = {code: cooccurrence_for_reason(rows, code) for code in COOCCURRENCE_CODES}
	scoring = compute_scoring(rows, multiplicity["0"])

	write_json(
		rows, feature_counts, verdict_counts, reason_presence,
		multiplicity, cooccurrence, scoring,
	)
	write_markdown(
		rows, feature_counts, verdict_counts, reason_presence,
		multiplicity, cooccurrence, scoring,
	)

	print("\n=== Headline ===")
	print(f"Files: {len(rows)}")
	print(f"clipPath-bearing: {feature_counts.get('clip_path', 0)}")
	print(f"transform-bearing: {feature_counts.get('transform_attr', 0)}")
	print(f"text-bearing: {feature_counts.get('text', 0)}")
	print(f"normalized (all-reasons, zero blockers): {multiplicity['0']}")
	print(
		f"raster rejects: {scoring['raster_reject_count']}  "
		f"supportable total: {scoring['supportable_total']}"
	)
	print(
		f"normalize rate: raw {scoring['normalized_rate_raw']:.1f}%  "
		f"adjusted {scoring['normalized_rate_adjusted']:.1f}%"
	)
	print("Multiplicity histogram (distinct reasons -> files):")
	for bucket in ("0", "1", "2", "3", "4+"):
		print(f"  {bucket}: {multiplicity[bucket]}")
	print("Stacked-blocker co-occurrence (files / also-blocked-by-another):")
	for code in COOCCURRENCE_CODES:
		stats = cooccurrence[code]
		print(f"  {code}: {stats['files']} / {stats['with_other']}")


if __name__ == "__main__":
	main()
