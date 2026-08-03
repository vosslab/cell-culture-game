#!/usr/bin/env python3
"""Aggregate validation entry: runs every validation stage.

Coordinates yaml, svg, and stepper validators in a unified CLI with
consistent flags and output formatting. Supports whole-suite or focused runs,
stage filtering, and multiple output formats (text, json, ndjson).

Existing per-stage validators remain untouched and runnable independently.
This aggregate dispatches to them via subprocess and aggregates results.
"""

import json
import os
import re
import sys
import subprocess
from pathlib import Path

import validation.shared_toolkit.cli
import validation.shared_toolkit.console
import validation.shared_toolkit.repo_root


REPO_ROOT = validation.shared_toolkit.repo_root.REPO_ROOT


# Match "N errors" / "N warnings" / "N advisories" tokens in any stage summary.
# Used to wrap non-zero counts in Rich markup. Rich's Console strips markup
# automatically when stdout is not a TTY (or when NO_COLOR is set), so piped
# output stays plain text.
_ERRORS_RE = re.compile(r"(\d+)\s+errors\b")
_WARNINGS_RE = re.compile(r"(\d+)\s+warnings\b")
_ADVISORIES_RE = re.compile(r"(\d+)\s+advisories\b")


def _extract_counts(stdout: str) -> tuple:
	"""
	Pull (errors, warnings, advisories) from a stage's summary line.

	Reads the last line that carries the canonical "<N> errors" token so the
	aggregate scoreboard can sum stages without re-parsing findings. Returns
	(0, 0, 0) when no summary line is present.
	"""
	errors = warnings = advisories = 0
	for line in stdout.splitlines():
		if _ERRORS_RE.search(line):
			err_match = _ERRORS_RE.search(line)
			warn_match = _WARNINGS_RE.search(line)
			adv_match = _ADVISORIES_RE.search(line)
			errors = int(err_match.group(1))
			warnings = int(warn_match.group(1)) if warn_match else 0
			advisories = int(adv_match.group(1)) if adv_match else 0
	return errors, warnings, advisories


def _print_scoreboard(console, all_stage_outputs: list) -> None:
	"""
	Print the aggregate TOTAL line and, on failure, the stages with errors.

	One verdict for the whole run. The verdict is ERROR-driven: any error fails
	(FAIL); zero errors with warnings/advisories is PASS (warnings only); a
	fully clean run is PASS. Counts are colored by severity only.
	"""
	total_errors = total_warnings = total_advisories = 0
	error_stages = []
	for stage_name, _exit_code, stdout in all_stage_outputs:
		errors, warnings, advisories = _extract_counts(stdout)
		total_errors += errors
		total_warnings += warnings
		total_advisories += advisories
		if errors:
			error_stages.append(stage_name.upper())

	stage_count = len(all_stage_outputs)
	counts_text = (
		f"{total_errors} errors. {total_warnings} warnings. "
		f"{total_advisories} advisories across {stage_count} stages."
	)
	counts_text = _colorize_summary(counts_text)

	if total_errors:
		verdict = "[bold red]FAIL[/bold red]"
	elif total_warnings or total_advisories:
		verdict = "[green]PASS[/green] (warnings only)"
	else:
		verdict = "[green]PASS[/green]"

	console.print(f"\n[bold]TOTAL:[/bold] {counts_text}  ->  {verdict}")
	if error_stages:
		console.print(f"  ERROR stages: {', '.join(error_stages)}")


def _colorize_summary(text: str) -> str:
	"""
	Color the three severity-tier counts by severity only: non-zero
	"N errors" bold red, "N warnings" yellow, "N advisories" dim. Zero counts
	stay unstyled. Severity is the only thing color encodes here; category
	accents live in the per-stage rollups, not in this summary line.

	Uses Rich markup tokens ([bold red]...[/bold red]) not raw ANSI escape
	codes - Rich's console.print sanitizes raw \\033[...] sequences and emits
	them as literal text on TTY. Rich handles TTY-gating: markup is stripped
	automatically on non-tty output or when NO_COLOR is set.
	"""
	def make_sub(style: str):
		def sub(match: re.Match) -> str:
			count = int(match.group(1))
			if count == 0:
				return match.group(0)
			return f"[{style}]{match.group(0)}[/{style}]"
		return sub

	colored = _ERRORS_RE.sub(make_sub("bold red"), text)
	colored = _WARNINGS_RE.sub(make_sub("yellow"), colored)
	colored = _ADVISORIES_RE.sub(make_sub("dim"), colored)
	return colored


def build_parser():
	"""Build argparse parser with unified flags for aggregate validation."""
	parser = validation.shared_toolkit.cli.build_parser(
		prog='validate',
		description='Aggregate validation suite: runs yaml, svg, stepper, structure, manual, scene-lint, and scene-design validators.',
	)
	return parser


def _stage_scripts(stage_name: str) -> list[str]:
	"""
	Return the list of validator scripts that compose a stage.

	The svg stage runs asset_audit.py, which checks SVG files for
	well-formedness and author-review issues.
	pipeline_check.py (SVG generation determinism + coverage gate) was
	previously listed here but the file no longer exists in the repo;
	it was removed from active dispatch to stop the "Stage script not
	found" error. See docs/archive/decisions/pipeline_check_dispatch.md.
	"""
	stage_map = {
		'yaml': ['validation/yaml_schema/content_lint.py'],
		'svg': ['validation/svg/asset_audit.py'],
		'stepper': ['validation/stepper/step_check.py'],
		'structure': ['validation/structure/layout_check.py'],
		'manual': ['validation/manual/protocol_manual.py'],
		'scene-lint': ['validation/scene_lint/cli.py'],
		'scene-design': ['validation/scene_design/cli.py'],
	}
	return stage_map.get(stage_name, [])


def run_stage(stage_name: str, args, repo_root: Path) -> tuple[int, str]:
	"""
	Run one validation stage and return (exit_code, captured_stdout).

	Args:
		stage_name: one of 'yaml', 'svg', 'stepper', 'structure', 'manual', 'scene-lint', 'scene-design'
		args: argparse.Namespace from build_parser().parse_args()
		repo_root: repo root path

	Returns:
		(exit_code, stdout_str) tuple. For composite stages (e.g. svg), exit
		code is the max across sub-scripts; stdout concatenates each sub-script
		output with a one-line header naming the sub-script.
	"""
	scripts = _stage_scripts(stage_name)
	if not scripts:
		return 1, f"Unknown stage: {stage_name}"

	all_outputs = []
	all_exit_codes = []
	for script_rel in scripts:
		script_path = repo_root / script_rel
		if not script_path.exists():
			all_exit_codes.append(1)
			all_outputs.append(f"Stage script not found: {script_path}")
			continue
		sub_exit, sub_stdout = _run_one_script(script_path, args, repo_root)
		all_exit_codes.append(sub_exit)
		# Prefix multi-script stages with sub-script name for readability
		if len(scripts) > 1:
			sub_name = Path(script_rel).stem
			all_outputs.append(f"[{sub_name}]\n{sub_stdout}")
		else:
			all_outputs.append(sub_stdout)

	combined_exit = max(all_exit_codes) if all_exit_codes else 0
	combined_stdout = "\n".join(all_outputs)
	return combined_exit, combined_stdout


def _run_one_script(script_path: Path, args, repo_root: Path) -> tuple[int, str]:
	"""Invoke a single validator script as subprocess; return (exit_code, stdout)."""
	# Build command for the stage
	cmd = [
		'python3',
		str(script_path),
	]

	# Pass through compatible flags
	if args.quiet:
		cmd.append('-q')
	if args.verbose:
		cmd.append('-v')
	if args.errors_only:
		cmd.append('-e')
	if args.strict:
		cmd.append('-s')
	if args.no_color:
		cmd.append('--no-color')
	if args.list_only:
		cmd.append('-l')
	if args.interactive:
		cmd.append('-i')
	if args.focus:
		cmd.append('--focus')

	# Pass protocol/object/scene selectors if present and not in focus mode
	if not args.focus:
		if args.protocols:
			cmd.extend(['-p'] + args.protocols)
		if args.objects:
			cmd.extend(['-o'] + args.objects)
		if args.scenes:
			cmd.extend(['-S'] + args.scenes)

	# Special case for manual stage: run in validate mode, add --all if no protocols selected and no focus
	if str(script_path).endswith('protocol_manual.py'):
		cmd.append('--validate')
		if not args.protocols and not args.focus:
			cmd.append('--all')

	# Special case for scene stages: when no -S scenes selected, auto-discover all base scenes.
	# scene-lint and scene-design require at least one scene path via -S.
	# In a whole-suite run (no --scene selector), pass all content/base_scenes/*.yaml files.
	is_scene_stage = (
		str(script_path).endswith('scene_lint/cli.py')
		or str(script_path).endswith('scene_design/cli.py')
	)
	if is_scene_stage and not args.scenes and not args.focus:
		base_scenes_dir = repo_root / 'content' / 'base_scenes'
		scene_yaml_files = sorted(base_scenes_dir.glob('*.yaml'))
		if scene_yaml_files:
			# Remove the -S args already added above (none were added since args.scenes is empty)
			cmd.extend(['-S'] + [str(f) for f in scene_yaml_files])

	# Pass output format flags if JSON/NDJSON
	if args.output_format == 'json':
		cmd.append('--json')
	elif args.output_format == 'ndjson':
		cmd.append('--ndjson')

	# Stage-specific flag adaptations (if needed; for now just dispatch stdout)

	# Build environment with PYTHONPATH set for subprocess access to validation/ + pipeline/
	env = dict(os.environ)
	pythonpath_entries = [str(repo_root)]
	if 'PYTHONPATH' in env:
		pythonpath_entries.append(env['PYTHONPATH'])
	env['PYTHONPATH'] = os.pathsep.join(pythonpath_entries)

	try:
		result = subprocess.run(
			cmd,
			cwd=str(repo_root),
			capture_output=True,
			text=True,
			timeout=300,
			env=env,
		)
		return result.returncode, result.stdout
	except subprocess.TimeoutExpired:
		return 1, f"Script {script_path.name} timed out"


def main() -> None:
	"""Run aggregate validation across selected stages.

	Verbosity contract (text output line targets):
	  -q / --quiet   : 1 line per stage (final pass/fail with key numbers)
	  default        : 5-40 lines per stage (stage summary, totals, top categories)
	  -v / --verbose : 40-<200 lines per stage (per-content-file breakdown, grouped, summarized)
	  -j / --json    : full machine-readable detail (no bound)
	  -J / --ndjson  : streamed full detail (no bound)
	Aggregate output ~3x per-stage bound in text mode (one stage per section).
	Raw per-step / per-asset internals go to JSON only, NOT text.
	"""
	parser = build_parser()
	args = parser.parse_args()

	# Determine which stages to run
	stages = args.stages if args.stages else ['yaml', 'svg', 'stepper', 'structure', 'manual', 'scene-lint', 'scene-design']

	# Determine scope
	# --focus is forwarded to each per-stage subprocess. Per-stage
	# scripts that consume it filter their own scope; per-stage scripts
	# that do not yet implement focus filtering accept the flag as a
	# no-op. iter_focus() in shared_toolkit/discovery.py is available
	# for aggregate-level scope narrowing if a future patch wants it.

	console = validation.shared_toolkit.console.make_console(no_color=args.no_color)

	# Run each stage
	all_stage_outputs = []
	all_exit_codes = []

	for stage_name in stages:
		exit_code, stdout = run_stage(stage_name, args, REPO_ROOT)
		all_exit_codes.append(exit_code)
		all_stage_outputs.append((stage_name, exit_code, stdout))

	# Compute max exit code now (used in both text and JSON output)
	max_exit = max(all_exit_codes) if all_exit_codes else 0

	# Render output based on format
	if args.output_format == 'text':
		# Group by stage with rich rule separators
		for stage_name, exit_code, stdout in all_stage_outputs:
			if args.quiet:
				# Quiet mode: one line per stage (last non-empty line of stdout).
				# No banner, no blanks, no per-stage failure line; aggregate exit code is the machine signal.
				non_empty_lines = [line for line in stdout.strip().splitlines() if line.strip()]
				if non_empty_lines:
					summary_line = _colorize_summary(non_empty_lines[-1])
					console.print(f"[bold cyan]{stage_name.upper()}[/bold cyan]: {summary_line}")
				continue
			console.print(f"\n[bold cyan]--- {stage_name.upper()} ---[/bold cyan]")
			if stdout.strip():
				console.print(_colorize_summary(stdout.rstrip()))
			if exit_code != 0:
				console.print(f"[bold red][{stage_name}] failed with exit code {exit_code}[/bold red]")

		# Aggregate scoreboard: one verdict line so a human does not sum stages
		# by hand. Severity drives the color and the verdict; advisories never
		# fail the run.
		_print_scoreboard(console, all_stage_outputs)

	elif args.output_format in ('json', 'ndjson'):
		# For JSON output: merge findings from all stages
		all_findings = []
		all_tools = set()

		for stage_name, exit_code, stdout in all_stage_outputs:
			if stdout.strip():
				# Each stage emits JSON; parse it and extract findings
				stage_data = json.loads(stdout)

				# If it's a top-level findings array or findings key, extract findings
				findings_list = []
				if isinstance(stage_data, list):
					findings_list = stage_data
				elif isinstance(stage_data, dict):
					if 'findings' in stage_data:
						findings_list = stage_data['findings']
					elif 'finding' in stage_data:
						findings_list = [stage_data['finding']]

				# Tag each finding with tool source if not already present
				for finding in findings_list:
					if isinstance(finding, dict):
						if 'tool' not in finding:
							finding['tool'] = f'validation.{stage_name}'
						all_findings.append(finding)
						all_tools.add(f'validation.{stage_name}')

		aggregate_result = {
			'stages': list(all_tools),
			'findings': all_findings,
			'exit_code': max_exit if all_exit_codes else 0,
		}

		if args.output_format == 'json':
			print(json.dumps(aggregate_result, indent=2))
		else:  # ndjson
			# Emit aggregate summary first, then each finding on its own line
			print(json.dumps({
				'stages': list(all_tools),
				'total_findings': len(all_findings),
				'exit_code': max_exit if all_exit_codes else 0,
			}))
			for finding in all_findings:
				print(json.dumps(finding))

	sys.exit(max_exit)


if __name__ == '__main__':
	main()
