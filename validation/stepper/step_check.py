#!/usr/bin/env python3
"""
Protocol stepper CLI: second content gate after validate_content_yaml.py.

Walks authored mini-protocols and sequence runners semantically (in
memory, no browser) and emits ERROR / WARNING findings for broken flow,
undeclared materials, invalid state mutations, sequence-runner handoff
gaps, and cross-mini production gaps.

CLI is aligned with shared toolkit parser:
  --list-protocols           List shipped protocol names and exit.
  --interactive              Pick one protocol from a numbered menu.
  -p / --protocol  NAME...   Step one or more named protocols (or paths).
  -q / --quiet               Final pass/fail only (one line).
  -v / --verbose             Diagnostic summary: top codes, per-protocol counts.
With no selection flags, every shipped mini-protocol and sequence
runner is walked.
"""

import sys
from pathlib import Path

import validation.stepper.loader
import validation.stepper.runner
import validation.stepper.dashboard as dashboard
import validation.stepper.findings
import validation.stepper.sentinels
import validation.shared_toolkit.cli as toolkit_cli
import validation.shared_toolkit.protocols as toolkit_protocols
import validation.shared_toolkit.interactive as toolkit_interactive
import validation.shared_toolkit.reporter as reporter
import validation.shared_toolkit.findings as shared_findings
import validation.shared_toolkit.emit as emit
import validation.shared_toolkit.verbosity as verbosity
import validation.shared_toolkit.console


# Stage-owned display map: raw stepper code -> friendly category label. The
# raw `code` stays on the finding (and in --json); this only governs the human
# rollup label. Severity is decided by the finding's level, not by this map.
_CODE_TO_CATEGORY = {
	'placement_name_collision': 'placement-collision',
	'ambiguous_target_in_scene': 'ambiguous-target',
	'undeclared_state_field': 'invalid-state',
	'object_state_change_invalid_state': 'invalid-state',
	'state_value_not_allowed': 'invalid-state',
	'state_value_type_mismatch': 'invalid-state',
	'broken_next_step': 'flow-broken',
	'flow_cycle': 'flow-broken',
	'flow_unreachable_step': 'flow-broken',
	'flow_multi_terminal': 'flow-broken',
	'entry_step_missing': 'flow-broken',
	'entry_step_not_found': 'flow-broken',
	'runner_of_runner': 'flow-broken',
	'scene_change_unresolved': 'scene-op-invalid',
	'scene_change_missing_to_scene': 'scene-op-invalid',
	'scene_change_internal_error': 'scene-op-invalid',
	'cursor_attach_missing_target': 'scene-op-invalid',
	'object_state_change_missing_target': 'scene-op-invalid',
	'timed_wait_missing_duration': 'scene-op-invalid',
	'timed_wait_invalid_duration': 'scene-op-invalid',
	'unknown_scene_operation_type': 'scene-op-invalid',
	'subpart_group_internal_error': 'scene-op-invalid',
	'unknown_target_active_scene': 'unresolved-target',
	'unknown_object_in_scene': 'unresolved-target',
	'unknown_placement': 'unresolved-target',
	'no_active_scene_at_resolution': 'unresolved-target',
	'no_initial_scene_found': 'unresolved-target',
	'unknown_active_scene': 'unresolved-target',
	's-unused': 'unused',
	's-unreachable': 'unused',
	'unknown_material': 'unused',
	'cross_mini_unknown_material': 'unused',
	's-state-jump': 'state-jump',
}


def _build_severity_rollup(walks: list) -> str:
	"""
	Group every walk's findings by severity tier and friendly category.

	INFO is the advisory tier. Unmapped codes fall back to the raw code so a
	new stepper code is still visible (just not yet friendly-labeled).
	"""
	tiers = {'error': {}, 'warning': {}, 'advisory': {}}
	for _name, _ptype, _steps, _interactions, emitter in walks:
		for finding in emitter.findings:
			if finding.level == shared_findings.Severity.ERROR:
				bucket = tiers['error']
			elif finding.level == shared_findings.Severity.WARNING:
				bucket = tiers['warning']
			else:
				bucket = tiers['advisory']
			label = _CODE_TO_CATEGORY.get(finding.code, finding.code or 'unknown')
			bucket[label] = bucket.get(label, 0) + 1
	return verbosity.severity_rollup(
		list(tiers['error'].items()),
		list(tiers['warning'].items()),
		list(tiers['advisory'].items()),
	)




def _post_walk_material_checks(
	tree: object,
	protocol_name: object,
	emitter: object,
	referenced_materials: object,
) -> None:
	"""
	Perform post-walk material consistency checks:
	- S-UNUSED: materials declared but never referenced.

	S-UNREGISTERED is checked during op time in scene_ops.py.

	Args:
		tree: LoadedContentTree.
		protocol_name: Name of the protocol.
		emitter: FindingEmitter with collected findings from the walk.
		referenced_materials: Set of material names found during execution.
	"""
	protocol = tree.get_protocol(protocol_name)
	if not protocol:
		return

	declared_materials = tree.get_protocol_materials(protocol_name)
	if declared_materials is None:
		return

	# S-UNUSED: materials declared but never referenced
	declared_keys = set(declared_materials.keys())
	unused_materials = declared_keys - referenced_materials

	for material_name in sorted(unused_materials):
		emitter.emit_finding(validation.stepper.findings.Finding(
			level=shared_findings.Severity.INFO,
			protocol_name=protocol_name,
			step_name=None,
			interaction_index=None,
			target=None,
			file_path=f"content/protocols/{protocol_name}/materials.yaml",
			code="s-unused",
			message=f"material '{material_name}' declared but never referenced in execution",
			spec_cite="docs/specs/MATERIAL_CONVENTION.md",
		))


def parse_args() -> object:
	"""Parse command-line arguments using unified toolkit parser."""
	# Extras callback for tool-specific flags (none for stepper)
	def add_stepper_extras(parser: object) -> None:
		# No stepper-specific flags
		pass

	parser = toolkit_cli.build_parser(
		prog='step_check',
		description='Step through authored protocols and report semantic findings.',
		extras=add_stepper_extras
	)

	# Parse and map shared args to local expectations
	args = parser.parse_args()

	# Map shared 'protocols' to 'protocol_names' for backward compat with _resolve_selection
	args.protocol_names = args.protocols

	return args


def _resolve_selection(args: object, repo_root: object, tree: object) -> object:
	"""
	Resolve which protocol names to walk based on CLI flags.

	Returns a list of protocol names, or None if the caller should exit.
	"""
	# --interactive: pick one
	if args.interactive:
		names = toolkit_protocols.list_protocols()
		selected = toolkit_interactive.pick_protocol_interactively(names)
		if selected is None:
			return None
		return [selected]

	# -p / --protocol: resolve each name-or-path to a protocol name
	if args.protocol_names:
		resolved = []
		for name_or_path in args.protocol_names:
			# If the user passed a name that loaded into the tree, use as-is.
			# Otherwise try the path resolver and derive the directory name.
			if name_or_path in tree.protocols:
				resolved.append(name_or_path)
				continue
			path = toolkit_protocols.resolve_protocol_path(name_or_path, repo_root=str(repo_root))
			if path is None:
				reporter.print_error(f"Protocol '{name_or_path}' not found.")
				return None
			resolved.append(toolkit_protocols.protocol_name_from_path(path))
		return resolved

	# Default: every shipped protocol (runners first, then minis)
	names = validation.stepper.runner.discover_sequence_runners(tree)
	names.extend(validation.stepper.runner.discover_mini_protocols(tree))
	return names


def _build_diagnostic_data(counts: object) -> object:
	"""
	Build a verbosity.DiagnosticData from aggregated walk counts.

	Per the verbosity contract's per-stage table, the stepper VERBOSE
	diagnostic block carries two sections:
	  - top_codes: failing finding codes by occurrence count.
	  - top_offenders: noisy protocols by combined error + warning count.

	Truncation and sort order are handled by verbosity.diagnostic_summary;
	this builder only assembles the (name, count) tuples.

	Args:
		counts: dict from dashboard.aggregate().

	Returns:
		A verbosity.DiagnosticData value.
	"""
	# Top failing codes: code -> total occurrences across all protocols.
	top_codes = [
		(code, entry['count'])
		for code, entry in counts['findings_by_code'].items()
	]

	# Top offenders: protocols carrying any error or warning, ranked by the
	# combined finding count. The formatter sorts and truncates.
	top_offenders = [
		(name, entry['errors'] + entry['warnings'])
		for name, entry in counts['per_protocol'].items()
		if entry['errors'] > 0 or entry['warnings'] > 0
	]

	data = verbosity.DiagnosticData(
		top_codes=top_codes,
		top_offenders=top_offenders,
	)
	return data


def _render_normal_totals(counts: object) -> None:
	"""
	Render the compact NORMAL-level totals block (no color, no dashboard).

	NORMAL keeps the per-protocol fail lines (printed during the walk) plus
	these aggregate totals, and stays within the 40-line stdout budget. The
	exhaustive per-protocol dashboard and findings-by-code breakdown move to
	VERBOSE.

	Args:
		counts: dict from dashboard.aggregate().
	"""
	type_strs = [f"{t} {n}" for t, n in sorted(counts['by_type'].items())]
	by_type = ', '.join(type_strs) if type_strs else '(none)'
	fail_count = len(counts['failed_protocols'])
	pass_count = len(counts['clean_protocols'])

	lines = []
	lines.append("Stepped content YAML (totals)")
	lines.append(f"  Protocols: {counts['total_protocols']} ({by_type})")
	lines.append(
		f"  Steps: {counts['total_steps']}   "
		f"Interactions: {counts['total_interactions']}"
	)
	lines.append(f"  Pass: {pass_count}   Fail: {fail_count}")
	lines.append(f"  Errors: {counts['errors']}   Warnings: {counts['warnings']}")
	print('\n'.join(lines))


def _to_shared_finding(finding: object) -> object:
	"""
	Convert a stepper Finding into a shared_toolkit Finding.

	The stepper Finding uses attribute names (level, protocol_name,
	step_name, file_path) that do not line up with emit.finding_to_dict's
	expected names (severity, protocol, step, path). Converting to the
	shared Finding gives emit_findings the canonical attribute names so the
	normalized dict carries the correct values.

	Args:
		finding: A validation.stepper.findings.Finding instance.

	Returns:
		A validation.shared_toolkit.findings.Finding instance.
	"""
	shared = shared_findings.Finding(
		severity=finding.level,
		tool='stepper',
		code=finding.code,
		message=finding.message,
		path=finding.file_path,
		line=None,
		protocol=finding.protocol_name,
		scene=None,
		step=finding.step_name,
		target=finding.target,
	)
	return shared


def main() -> None:
	"""Dispatch by selection mode and walk the chosen protocols.

	Verbosity contract (text output line targets):
	  -q / --quiet   : 1 line (final pass/fail with key numbers)
	  default        : 5-40 lines (stage summary, totals, top categories)
	  -v / --verbose : 40-<200 lines (per-content-file breakdown, grouped, summarized)
	  -j / --json    : full machine-readable detail (no bound)
	  -J / --ndjson  : streamed full detail (no bound)
	Raw per-step / per-asset internals go to JSON only, NOT text.
	"""
	args = parse_args()
	repo_root = Path(__file__).resolve().parent.parent.parent

	# --list is filesystem-based and fast; do not load the tree.
	if args.list_only:
		for name in toolkit_protocols.list_protocols():
			print(name)
		sys.exit(0)

	tree = validation.stepper.loader.load_content_tree(repo_root)

	protocol_names = _resolve_selection(args, repo_root, tree)
	if protocol_names is None:
		sys.exit(1)

	# Resolve the output level once and switch on the enum. The walker
	# itself stays quiet in every level; main() owns all text output, so
	# the level mapping is direct with no inverted double-negative.
	level = verbosity.resolve_level(quiet=args.quiet, verbose=args.verbose)

	# Output model (verbosity contract):
	#   QUIET:   only the closing summary line (one line).
	#   NORMAL:  per-protocol fail lines, compact totals, summary line.
	#   VERBOSE: per-protocol fail lines, diagnostic block (top codes, top
	#            offenders), full dashboard, summary line.
	# The fail lines appear in BOTH NORMAL and VERBOSE.
	# In machine-readable modes the JSON / NDJSON document is the sole stdout
	# content, so the per-protocol fail lines must be suppressed there.
	machine_format = args.output_format in ('json', 'ndjson')
	show_fail_lines = (not machine_format) and level in (
		verbosity.VerbosityLevel.NORMAL, verbosity.VerbosityLevel.VERBOSE,
	)

	walks = []
	has_error = False
	total = 0
	# failed_protocols is the protocol-level count (how many protocols had >=1
	# error); errors/warnings/advisories are FINDING-level counts. The summary
	# line reports findings; the parenthetical reports the protocol span.
	failed_protocols = 0
	errors = 0
	warnings = 0
	advisories = 0

	for protocol_name in protocol_names:
		total += 1
		protocol = tree.get_protocol(protocol_name)
		protocol_type = toolkit_protocols.classify_protocol(protocol)

		if protocol_type == "sequence_runner":
			leaf_count, interaction_count, emitter = validation.stepper.runner.walk_sequence_runner(
				tree, protocol_name, verbose=False, quiet=True,
			)
			step_count = leaf_count
		else:
			step_count, interaction_count, emitter = validation.stepper.runner.walk_protocol(
				tree, protocol_name, verbose=False, quiet=True,
			)

		# Post-walk material consistency checks
		_post_walk_material_checks(
			tree,
			protocol_name,
			emitter,
			emitter.referenced_materials,
		)

		walks.append(
			(protocol_name, protocol_type, step_count, interaction_count, emitter)
		)

		if emitter.has_errors():
			has_error = True
			failed_protocols += 1
			# Name each failing protocol immediately in NORMAL and VERBOSE
			# so the reader does not have to wait for the totals/dashboard
			# to learn what blew up.
			if show_fail_lines:
				reporter.print_fail(protocol_name)
		# Finding-level severity tallies. Severity is closed at three tiers:
		# ERROR blocks, WARNING should-fix, INFO is the advisory tier.
		for f in emitter.findings:
			if f.level == shared_findings.Severity.ERROR:
				errors += 1
			elif f.level == shared_findings.Severity.WARNING:
				warnings += 1
			else:
				advisories += 1

	# Machine-readable output (JSON / NDJSON) is the SOLE stdout content in
	# those modes: no text totals, dashboard, or summary line. The exit code
	# stays identical to the text path (exit 1 when any emitter had errors,
	# which is already captured in has_error above).
	if args.output_format in ('json', 'ndjson'):
		all_findings = []
		for _name, _ptype, _steps, _interactions, emitter in walks:
			for finding in emitter.findings:
				all_findings.append(_to_shared_finding(finding))
		emit.emit_findings(all_findings, output_format=args.output_format)
		sys.exit(1 if has_error else 0)

	counts = dashboard.aggregate(walks)

	if level == verbosity.VerbosityLevel.NORMAL:
		# Compact totals only; the exhaustive breakdown is VERBOSE-only so
		# NORMAL stays within the line budget.
		_render_normal_totals(counts)
		# Grouped per-code rollup so the reader sees WHAT blocks without --json.
		rollup = _build_severity_rollup(walks)
		if rollup:
			console = validation.shared_toolkit.console.make_console()
			console.print(rollup)
	elif level == verbosity.VerbosityLevel.VERBOSE:
		# Diagnostic block first, then the full colorized dashboard.
		print()
		diagnostic_data = _build_diagnostic_data(counts)
		print(verbosity.diagnostic_summary(diagnostic_data))
		print()
		dashboard.render(counts)
		print()

	reporter.print_summary_line(
		total, errors, item_label="protocols",
		warnings=warnings, advisories=advisories,
	)
	# State the counting unit explicitly: the line counts findings, this counts
	# protocols. Only shown when errors exist, and never in QUIET (the summary
	# line must stay the last line so the aggregate runner can read it).
	if errors and level != verbosity.VerbosityLevel.QUIET:
		print(f"  (errors span {failed_protocols} of {total} protocols)")

	sys.exit(1 if has_error else 0)


if __name__ == '__main__':
	main()
