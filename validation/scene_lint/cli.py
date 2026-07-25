"""Scene lint CLI and main entry point."""

import sys
import json
from pathlib import Path

from validation.scene_lint.findings import Finding, Verdict
from validation.scene_lint.confusion import load_labeled_corpus, compute_confusion, write_confusion_markdown
import validation.shared_toolkit.cli as toolkit_cli
import validation.shared_toolkit.reporter as reporter
import validation.shared_toolkit.verbosity as verbosity


def _add_scene_lint_extras(parser):
	"""Register scene_lint-specific flags beyond the shared flag set."""
	parser.add_argument(
		'--report-only',
		dest='report_only',
		action='store_true',
		help='Print findings without exiting non-zero (for diagnostics)',
	)
	parser.add_argument(
		'--validate-against',
		dest='validate_against',
		type=str,
		metavar='LABELED_CORPUS_YAML',
		help='Path to labeled corpus YAML for confusion-table validation',
	)
	parser.add_argument(
		'--emit-confusion',
		dest='emit_confusion',
		type=str,
		metavar='OUT_MD',
		help='Output path stem for per-rule confusion-table Markdown reports',
	)
	parser.add_argument(
		'--suppressions',
		dest='suppressions_path',
		type=str,
		metavar='SUPPRESSIONS_YAML',
		help='Path to suppressions.yaml manifest for Group B advisory findings',
	)
	parser.add_argument(
		'--promotions',
		dest='promotions_path',
		type=str,
		metavar='PROMOTIONS_YAML',
		help='Path to promotions.yaml config; defaults to validation/scene_lint/promotions.yaml',
	)
	parser.add_argument(
		'--no-promotions',
		dest='no_promotions',
		action='store_true',
		help='Disable promotion loading (override --promotions and default)',
	)


def parse_args():
	"""Parse command-line arguments for scene_lint."""
	parser = toolkit_cli.build_parser(
		prog='scene_lint',
		description='Scene lint: build-time render-failure predictor for scene YAML.',
		extras=_add_scene_lint_extras,
	)
	args = parser.parse_args()
	return args


def resolve_paths(path_specs: list[str]) -> list[Path]:
	"""
	Resolve path specs (file paths and globs) to concrete YAML files.
	Raises RuntimeError if any spec yields no files or points to a missing directory.
	"""
	resolved: list[Path] = []
	for spec in path_specs:
		spec_path = Path(spec)
		if '*' in spec or '?' in spec:
			matches = list(Path.cwd().glob(spec))
			if not matches:
				raise RuntimeError(f'Glob pattern matched no files: {spec}')
			resolved.extend(sorted(matches))
		else:
			if not spec_path.exists():
				raise RuntimeError(f'Path does not exist: {spec}')
			if spec_path.is_dir():
				raise RuntimeError(f'Path is a directory, not a YAML file: {spec}')
			resolved.append(spec_path)
	return resolved


def check_confusion_flags(args) -> None:
	"""
	Validate confusion-table CLI flags for mutual consistency.
	--emit-confusion requires --validate-against (corpus is the input).
	Exits with code 2 (invocation error) on invalid flag combinations.
	"""
	if args.emit_confusion and not args.validate_against:
		print(
			'Error: --emit-confusion requires --validate-against <corpus.yaml>.',
			file=sys.stderr,
		)
		sys.exit(2)


def _yaml_parse_error_finding(path: Path, exc: Exception) -> Finding:
	"""Create a Finding for YAML parse failure."""
	from validation.scene_lint.findings import Confidence
	return Finding(
		scene=path.stem,
		placement_name=None,
		rule='yaml_parse_error',
		verdict=Verdict.BLOCKED,
		confidence=Confidence.HIGH,
		message=f"Failed to parse {path}: {str(exc)}",
		evidence={'path': str(path), 'error': str(exc)},
	)


def run_all_rules(paths: list[Path]) -> list[Finding]:
	"""
	Load all scene YAMLs and run Group A and Group B rules.

	Group A rules (data blockers) run first.
	Group B rules (geometry predictors) require the SIM dump and run after
	Group A; each scene's dump is computed once and reused across all B rules.

	Args:
		paths: List of scene YAML file paths.

	Returns:
		List of all findings from all rules.
	"""
	from validation.scene_lint.rules_group_a import (
		check_duplicate_scene_name,
		check_duplicate_placement_name,
		check_forbidden_source_geometry,
		check_missing_svg_asset,
		check_invalid_svg_viewbox,
		check_inheritance_errors,
		check_inheritance_dangling_ref,
	)
	from validation.scene_lint.rules_group_b import (
		check_aspect_distorted_predicted,
		check_item_taller_than_zone,
		check_row_footprint_overflow,
		check_placement_bbox_outside_scene,
		check_placement_bbox_outside_zone,
		check_item_item_overlap,
		check_label_offscreen,
		check_label_object_overlap,
		check_invisible_placement,
		check_zone_overlap,
	)
	from validation.scene_calc.dump import dump_scene_geometry, MissingRenderEvidenceError
	from validation.scene_lint.findings import Confidence
	from validation.shared_toolkit.yaml_io import load_yaml
	import yaml

	findings: list[Finding] = []

	scenes = {}
	for path in paths:
		try:
			scene = load_yaml(path)
			scenes[str(path)] = scene
		except (yaml.YAMLError, OSError, RuntimeError) as e:
			findings.append(_yaml_parse_error_finding(path, e))

	if not findings:
		dup_scene_findings = check_duplicate_scene_name(scenes)
		findings.extend(dup_scene_findings)

	for path_str, scene in scenes.items():
		scene_name = scene.get('scene_name', Path(path_str).stem)
		path = Path(path_str)

		# Group A rules: deterministic data blockers.
		findings.extend(check_duplicate_placement_name(scene, scene_name))
		findings.extend(check_forbidden_source_geometry(scene, scene_name))
		findings.extend(check_missing_svg_asset(scene, scene_name))
		findings.extend(check_invalid_svg_viewbox(scene, scene_name))
		findings.extend(check_inheritance_errors(scene, scene_name, path))
		findings.extend(check_inheritance_dangling_ref(scene, scene_name))

		# Group B rules: geometry predictors that require the SIM dump.
		# Compute dump once per scene and reuse across all B rules.
		try:
			dump_data = dump_scene_geometry(path)
		except MissingRenderEvidenceError as e:
			# Render-evidence prerequisite failure: the per-scene stats.json is
			# missing or load-failed. Emit a precise prerequisite message naming
			# the fix command. Validation never renders; rendering is a separate
			# explicit evidence step (node tools/scene_to_png.mjs --all).
			message = (
				"SCENE-LINT blocked: rendered scene stats are missing.\n"
				"Generate render evidence first:\n"
				"  node tools/scene_to_png.mjs --all"
			)
			findings.append(Finding(
				scene=scene_name,
				placement_name=None,
				rule='missing_render_evidence',
				verdict=Verdict.BLOCKED,
				confidence=Confidence.HIGH,
				message=message,
				evidence={'error': str(e)},
			))
			continue
		except (OSError, RuntimeError, KeyError) as e:
			# Other dump failures (not render-evidence). Skip Group B for this
			# scene; Group A findings (e.g., missing_svg_asset) flag the root cause.
			findings.append(Finding(
				scene=scene_name,
				placement_name=None,
				rule='dump_error',
				verdict=Verdict.BLOCKED,
				confidence=Confidence.LOW,
				message=f"Scene geometry dump failed; Group B rules skipped: {e}",
				evidence={'error': str(e)},
			))
			continue

		findings.extend(check_aspect_distorted_predicted(scene, scene_name, dump_data))
		findings.extend(check_item_taller_than_zone(scene, scene_name, dump_data))
		findings.extend(check_row_footprint_overflow(scene, scene_name, dump_data))
		findings.extend(check_placement_bbox_outside_scene(scene, scene_name, dump_data))
		findings.extend(check_placement_bbox_outside_zone(scene, scene_name, dump_data))
		findings.extend(check_item_item_overlap(scene, scene_name, dump_data))
		findings.extend(check_label_offscreen(scene, scene_name, dump_data))
		findings.extend(check_label_object_overlap(scene, scene_name, dump_data))
		findings.extend(check_invisible_placement(scene, scene_name, dump_data))
		findings.extend(check_zone_overlap(scene, scene_name, dump_data))

	return findings


def emit_findings_json_document(findings: list[Finding], output) -> None:
	"""
	Emit findings as a single JSON document: {"findings": [...]}.

	This is the --json shape consumed by validation/validate.py, which calls
	json.loads on the whole stdout. Unlike --ndjson (one finding object per
	line), --json must be one parseable document.
	"""
	# Build the wrapped document; serialize each finding via to_dict.
	document = {'findings': [finding.to_dict() for finding in findings]}
	json.dump(document, output, separators=(',', ':'))
	output.write('\n')


#============================================
# Text-output diagnostic helpers
#============================================

def count_top_codes(findings: list[Finding]) -> list:
	"""
	Count findings grouped by a rule+verdict code, returned as (code, count).

	The code is "<rule>/<verdict>" so the same rule firing at different
	verdicts stays distinguishable in the diagnostic block.
	"""
	code_counts: dict[str, int] = {}
	for finding in findings:
		code = f'{finding.rule}/{finding.verdict.value}'
		code_counts[code] = code_counts.get(code, 0) + 1
	return list(code_counts.items())


def count_top_offenders(findings: list[Finding]) -> list:
	"""Count findings per scene, returned as (scene_name, count)."""
	scene_counts: dict[str, int] = {}
	for finding in findings:
		scene_counts[finding.scene] = scene_counts.get(finding.scene, 0) + 1
	return list(scene_counts.items())


def render_top_findings(findings: list[Finding], limit: int = 10) -> list:
	"""
	Build up to `limit` one-line text descriptions of the top findings.

	Each line names the scene, rule, and verdict so the NORMAL text level
	shows what fired without dumping every finding (full detail lives in
	--json / --ndjson).
	"""
	lines: list[str] = []
	# Show BLOCKED first, then ESCAPE_REQUIRED, then the rest, for relevance.
	order = {Verdict.BLOCKED: 0, Verdict.ESCAPE_REQUIRED: 1, Verdict.CLEAN: 2}
	ranked = sorted(findings, key=lambda f: (order[f.verdict], f.scene, f.rule))
	for finding in ranked[:limit]:
		lines.append(f'  {finding.scene}: {finding.rule} [{finding.verdict.value}]')
	remainder = len(ranked) - len(ranked[:limit])
	if remainder > 0:
		lines.append(f'  ... and {remainder} more')
	return lines


def main() -> None:
	"""Main entry point for scene_lint."""
	args = parse_args()
	check_confusion_flags(args)

	# Scene paths come from -S/--scene (shared flag). Fall back to empty list
	# so standalone invocation without -S gives a useful error.
	path_specs = args.scenes if args.scenes else []
	if not path_specs:
		print('Error: at least one scene path required (use -S/--scene)', file=sys.stderr)
		sys.exit(2)

	try:
		paths = resolve_paths(path_specs)
	except RuntimeError as e:
		print(f'Error: {e}', file=sys.stderr)
		sys.exit(2)

	findings = run_all_rules(paths)

	# Load suppressions and advisory findings (malformed, expired entries)
	suppressions = []
	advisory_from_suppressions = []
	if args.suppressions_path:
		from validation.scene_lint.suppressions import load_suppressions
		try:
			suppressions, advisory_from_suppressions = load_suppressions(Path(args.suppressions_path))
		except (OSError, RuntimeError) as e:
			print(f'Error loading suppressions manifest: {e}', file=sys.stderr)
			sys.exit(2)

		# Emit advisory findings from suppression loading (malformed, expired)
		findings.extend(advisory_from_suppressions)

		# Apply suppressions: remove matching Group B findings (suppressed list discarded).
		from validation.scene_lint.suppressions import apply_suppressions
		findings, _ = apply_suppressions(findings, suppressions)

	# Load promotions and advisory findings (malformed, below_bar entries).
	# --no-promotions short-circuits both --strict and the default-path lookup so
	# the flag works whether or not --strict is also present.
	promotions = []
	advisory_from_promotions = []
	if args.strict and not args.no_promotions:
		from validation.scene_lint.promotion import load_promotions
		# Resolve promotions path: explicit --promotions, else default.
		if args.promotions_path:
			promotions_path = Path(args.promotions_path)
		else:
			promotions_path = Path(__file__).parent / 'promotions.yaml'

		if promotions_path.exists():
			# Load promotions with optional corpus for re-validation
			corpus_path = None
			if args.validate_against:
				corpus_path = Path(args.validate_against)
			try:
				promotions, advisory_from_promotions = load_promotions(
					promotions_path,
					corpus_path,
				)
			except (OSError, RuntimeError) as e:
				print(f'Error loading promotions manifest: {e}', file=sys.stderr)
				sys.exit(2)

			# Emit advisory findings from promotion loading (malformed, below_bar)
			findings.extend(advisory_from_promotions)

	# Resolve verbosity level once from the (quiet, verbose) boolean pair.
	level = verbosity.resolve_level(quiet=args.quiet, verbose=args.verbose)

	# Branch on output format FIRST: machine formats bypass verbosity entirely.
	# --json emits a single JSON document {"findings": [...]} so validate.py's
	# json.loads(stdout) merge path succeeds. --ndjson keeps the legacy JSONL
	# shape (one finding object per line).
	if args.output_format == 'json':
		emit_findings_json_document(findings, sys.stdout)
	elif args.output_format == 'ndjson':
		from validation.scene_lint.writers import write_findings_jsonl
		write_findings_jsonl(findings, sys.stdout)
	else:
		# Text output: switch on the resolved level enum.
		# Failures map to BLOCKED findings (the verdict that drives exit 1);
		# warnings map to ESCAPE_REQUIRED (advisory unless promoted in strict).
		blocked = [f for f in findings if f.verdict == Verdict.BLOCKED]
		escape = [f for f in findings if f.verdict == Verdict.ESCAPE_REQUIRED]
		total_scenes = len(paths)
		failure_count = len(blocked)
		warning_count = len(escape)
		flagged = blocked + escape

		if level == verbosity.VerbosityLevel.QUIET:
			# QUIET: exactly one canonical summary line.
			reporter.print_summary_line(
				total_scenes, failure_count,
				item_label='scenes', warnings=warning_count,
			)
		elif level == verbosity.VerbosityLevel.NORMAL:
			# NORMAL: totals plus the top flagged findings, then the summary line.
			if flagged:
				print('Top findings:')
				for line in render_top_findings(flagged):
					print(line)
			reporter.print_summary_line(
				total_scenes, failure_count,
				item_label='scenes', warnings=warning_count,
			)
		else:
			# VERBOSE: NORMAL content plus the grouped diagnostic block.
			if flagged:
				print('Top findings:')
				for line in render_top_findings(flagged):
					print(line)
			diag_data = verbosity.DiagnosticData(
				top_codes=count_top_codes(flagged),
				top_offenders=count_top_offenders(flagged),
			)
			diag_block = verbosity.diagnostic_summary(diag_data)
			print(diag_block)
			reporter.print_summary_line(
				total_scenes, failure_count,
				item_label='scenes', warnings=warning_count,
			)

	# Confusion-table path: load corpus and emit per-rule report when requested
	if args.validate_against:
		corpus_path = Path(args.validate_against)
		corpus = load_labeled_corpus(corpus_path)

		if args.emit_confusion:
			emit_path = Path(args.emit_confusion)
			# Collect distinct rule names present in findings and corpus positives
			rule_names_in_findings = {f.rule for f in findings}
			rule_names_in_corpus = {p['mapped_rule'] for p in corpus['positives']}
			all_rule_names = rule_names_in_findings | rule_names_in_corpus

			# Emit one confusion markdown per rule
			for rule_name in sorted(all_rule_names):
				stats = compute_confusion(findings, corpus, rule_name)
				# Derive a per-rule output path from the base emit path
				stem = emit_path.stem
				suffix = emit_path.suffix or '.md'
				rule_out = emit_path.parent / f'{stem}_{rule_name}{suffix}'
				write_confusion_markdown(stats, rule_name, corpus, rule_out)

	group_a_findings = [f for f in findings if f.verdict == Verdict.BLOCKED]
	escape_required = [f for f in findings if f.verdict == Verdict.ESCAPE_REQUIRED]

	if not args.report_only:
		if group_a_findings:
			sys.exit(1)

		# Strict mode: exit 1 on ESCAPE_REQUIRED from promoted rules
		if args.strict and escape_required and promotions:
			promoted_rule_names = {p.rule for p in promotions}
			strict_violations = [
				f for f in escape_required
				if f.rule in promoted_rule_names
			]
			if strict_violations:
				sys.exit(1)


if __name__ == '__main__':
	main()
