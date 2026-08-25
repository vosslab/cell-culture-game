#!/usr/bin/env python3
"""
Render a mini-protocol YAML to a human-readable lab manual.

Third gate after `validation/yaml/content_lint.py` (syntax) and
`validation/stepper/step_check.py` (semantic flow). This tool renders the
authored YAML to markdown prose so a pedagogy reviewer can read every
mini end-to-end without parsing YAML. Reading prose surfaces a bug
class that neither static validation nor flow simulation can catch:
click-centric prompts, action-vs-end-state divergence, material
identity drift, inverted cause-effect modeling, and over-atomization
of steps.

Usage:
	source source_me.sh && python3 validation/manual/protocol_manual.py <protocol_name>
	source source_me.sh && python3 validation/manual/protocol_manual.py -p NAME [NAME ...]
	source source_me.sh && python3 validation/manual/protocol_manual.py --interactive
	source source_me.sh && python3 validation/manual/protocol_manual.py --list-protocols
	source source_me.sh && python3 validation/manual/protocol_manual.py --all

Single mode writes `./manual_<protocol_name>.md` to the current working
directory. `--all` writes every protocol to `./output_manuals/manual_*.md`.
Override the directory with `--out-dir <dir>`, or use `--stdout` to print
the rendered markdown to stdout instead of writing files.

Use `--lint` to emit authoring warnings to stderr (does not alter rendered
output). Use `--validate` to run the lint pass and emit findings in
structured format (JSON or NDJSON). Checks for click-centric prompts,
material-identity drift, set-volume vs computed-delta mismatches, and
aspirate-vs-draw terminology.

Reuses no validator or stepper code; reads YAML directly via pyyaml.
Translation templates are heuristic and live in this file. A future
plan can move per-object verbs into the object YAML schema so the
templates become content-driven rather than tool-driven.
"""

import os
import sys

import validation.shared_toolkit.paths as toolkit_paths
import validation.shared_toolkit.protocols as toolkit_protocols
import validation.shared_toolkit.interactive as toolkit_interactive
import validation.shared_toolkit.reporter as toolkit_reporter
import validation.shared_toolkit.cli as toolkit_cli
import validation.shared_toolkit.findings as toolkit_findings
import validation.shared_toolkit.emit as toolkit_emit
import validation.shared_toolkit.verbosity as toolkit_verbosity
import validation.manual.protocol_manual_interactions
import validation.manual.protocol_manual_state

REPO_ROOT = toolkit_paths.REPO_ROOT
CONTENT_ROOT = toolkit_paths.CONTENT_ROOT
PROTOCOLS_DIR = toolkit_paths.PROTOCOLS_DIR
OBJECTS_DIR = toolkit_paths.OBJECTS_DIR

# Bulk-write directory. Per REPO_STYLE.md, reuse a stable CWD-relative
# folder ("output_*") instead of /tmp so the artifacts are visible next
# to the repo and survive across runs.
DEFAULT_BULK_OUT_DIR = "output_manuals"

# Prompt keywords that indicate a verification step. When a step prompt
# begins with one of these, a bare-click interaction on a tracked object
# renders as "Verify the X" instead of "Pick up the X".
VERIFY_PROMPT_KEYWORDS = ("verify", "confirm", "review", "check", "inspect")


#============================================
def render_learning_block(learning: object) -> object:
	"""Render the learning block."""
	lines = ["## Learning", ""]
	objectives = learning.get("objectives", "") or ""
	outcomes = learning.get("outcomes", "") or ""
	goals = learning.get("goals", "") or ""
	if objectives:
		lines.append(f"**Objectives.** {objectives}")
		lines.append("")
	if outcomes:
		lines.append(f"**Outcomes.** {outcomes}")
		lines.append("")
	if goals:
		lines.append(f"**Goals.** {goals}")
		lines.append("")
	return lines


#============================================
def prewalk_touched_objects(protocol: object, catalog: object) -> object:
	"""
	Walk the protocol step chain (entry_step + next_step) and collect all
	interaction targets. Returns a set of object names (parent only, no subparts).
	Kind filtering to purchasable objects happens in render_equipment_section.
	"""
	touched = set()
	steps_by_name = {}
	for step in protocol.get("steps", []) or []:
		steps_by_name[step["step_name"]] = step
	current_name = protocol.get("entry_step")
	visited = set()
	while current_name is not None:
		if current_name in visited:
			break
		visited.add(current_name)
		step = steps_by_name.get(current_name)
		if step is None:
			break
		for interaction in step.get("sequence", []) or []:
			target = interaction.get("target", "")
			if target:
				# Extract parent name (before the dot if it's a subpart).
				parent = target.split(".", 1)[0]
				touched.add(parent)
		current_name = step.get("next_step")
	return touched


#============================================
def collect_referenced_materials(protocol: object) -> object:
	"""
	Walk the protocol's interactions and scene_operations to collect all
	material_name and held_material_name values actually referenced.
	Returns a set of material names.
	"""
	referenced = set()
	steps_by_name = {}
	for step in protocol.get("steps", []) or []:
		steps_by_name[step["step_name"]] = step
	current_name = protocol.get("entry_step")
	visited = set()
	while current_name is not None:
		if current_name in visited:
			break
		visited.add(current_name)
		step = steps_by_name.get(current_name)
		if step is None:
			break
		for interaction in step.get("sequence", []) or []:
			response = interaction.get("response", {}) or {}
			for op in response.get("scene_operations", []) or []:
				if op.get("type") == "ObjectStateChange":
					state = op.get("state", {}) or {}
					for material_field in ("material_name", "held_material_name"):
						if material_field in state:
							mat = state[material_field]
							if mat:
								referenced.add(mat)
		current_name = step.get("next_step")
	return referenced


#============================================
def render_materials_section(material_labels: object, protocol: object=None) -> object:
	"""
	Render the ## Materials section. Emits nothing if material_labels is empty.
	When protocol is provided, filter material_labels to only those referenced
	in the protocol's interactions. Returns list of markdown lines.
	"""
	if not material_labels:
		return []
	labels_to_render = material_labels
	if protocol is not None:
		referenced = collect_referenced_materials(protocol)
		labels_to_render = {
			k: v for k, v in material_labels.items() if k in referenced
		}
	if not labels_to_render:
		return []
	lines = ["## Materials", ""]
	for label in sorted(labels_to_render.values()):
		lines.append(f"- {label}")
	lines.append("")
	return lines


#============================================
def render_equipment_section(touched_objects: object, catalog: object) -> object:
	"""
	Render the ## Equipment section. Emits nothing if touched_objects is empty.
	Filters to only objects with kinds in the purchasable set.
	Returns list of markdown lines.
	"""
	# Kinds that a student would shop for on a bench setup list. Object schema
	# kinds outside this set (scene-change targets, abstract slots, UI helpers)
	# are excluded from the equipment header. Update when content/objects/ adds a
	# new shoppable kind.
	purchasable_kinds = {"pipette", "bottle", "tube", "plate", "rack", "flask", "instrument", "container", "vial"}
	filtered = []
	for obj_name in sorted(touched_objects):
		kind = catalog.kind(obj_name)
		if kind in purchasable_kinds:
			label = catalog.label(obj_name)
			filtered.append(label)
	if not filtered:
		return []
	lines = ["## Equipment", ""]
	for label in sorted(set(filtered)):
		lines.append(f"- {label}")
	lines.append("")
	return lines


#============================================
def render_protocol_manual(protocol_name: object, catalog: object, lint: object=None) -> object:
	"""
	Render a mini-protocol or sequence runner; return markdown string.
	When lint is not None, collects authoring warnings in the collector.
	"""
	resolved_path = toolkit_protocols.resolve_protocol_path(protocol_name)
	if resolved_path is None:
		raise FileNotFoundError(f"Protocol '{protocol_name}' not found")
	protocol = validation.manual.protocol_manual_state.load_yaml(str(resolved_path))
	protocol_type = protocol.get("protocol_type", "mini_protocol")

	lines = [f"# {protocol_type.replace('_', '-')}: {protocol_name.replace('_', ' ')}", ""]

	learning = protocol.get("learning", {}) or {}
	if learning:
		lines.extend(render_learning_block(learning))

	if protocol_type == "sequence_runner":
		constituents = protocol.get("mini_protocols", []) or []
		lines.append("## Constituent mini-protocols")
		lines.append("")
		for name in constituents:
			lines.append(f"- {name.replace('_', ' ')}")
		lines.append("")
		for iteration_num, name in enumerate(constituents, start=1):
			lines.append("---")
			lines.append("")
			iteration_header = f"### Iteration {iteration_num} of {len(constituents)}: {name.replace('_', ' ')}"
			lines.append(iteration_header)
			lines.append("")
			child_md = render_protocol_manual(name, catalog, lint)
			if child_md.startswith("# "):
				child_md = "## " + child_md[2:]
			lines.append(child_md)
		return "\n".join(lines)

	material_labels = validation.manual.protocol_manual_state.load_material_labels(protocol_name)
	sim = validation.manual.protocol_manual_state.StateSimulator(catalog)
	equipment_set = prewalk_touched_objects(protocol, catalog)

	steps_by_name = {}
	for step in protocol.get("steps", []) or []:
		steps_by_name[step["step_name"]] = step

	# Render materials and equipment sections between learning and procedure.
	lines.extend(render_materials_section(material_labels, protocol))
	lines.extend(render_equipment_section(equipment_set, catalog))

	lines.append("## Procedure")
	lines.append("")

	step_number = 1
	current_name = protocol.get("entry_step")
	visited = set()
	touched_objects = set()
	while current_name is not None:
		if current_name in visited:
			lines.append(f"*(cycle detected at {current_name}; halting render)*")
			break
		visited.add(current_name)
		step = steps_by_name.get(current_name)
		if step is None:
			lines.append(f"*(broken next_step reference: {current_name})*")
			break
		step_lines = validation.manual.protocol_manual_interactions.render_step(
			step, catalog, material_labels, sim, touched_objects, lint,
		)
		step_lines[0] = step_lines[0].replace("### ", f"### Step {step_number}. ")
		lines.extend(step_lines)
		step_number += 1
		current_name = step.get("next_step")

	return "\n".join(lines)


#============================================
def write_manual(name: object, markdown: object, out_dir: object) -> object:
	"""
	Write one rendered manual to <out_dir>/manual_<name>.md and return the path.

	Creates out_dir if missing. The output filename uses the manual_ prefix
	so a single .gitignore line (`manual_*.md`) catches all generated manuals
	regardless of output directory. Both single-mode (CWD) and bulk mode
	(output_manuals/) apply this prefix.
	"""
	os.makedirs(out_dir, exist_ok=True)
	out_path = os.path.join(out_dir, f"manual_{name}.md")
	with open(out_path, "w", encoding="utf-8") as handle:
		handle.write(markdown)
		handle.write("\n")
	return out_path


#============================================
def parse_args() -> object:
	"""Parse command-line arguments."""
	#============================================
	# extras callback registers protocol_manual-specific flags.
	# Note: shared CLI already provides -p/--protocol, -i/--interactive,
	# -l/--list, and -q/--quiet. We only add manual-specific flags here.
	#============================================
	def register_manual_flags(parser: object) -> None:
		selection_group = parser.add_argument_group("Manual Selection")
		selection_group.add_argument(
			"protocol", nargs="?",
			help="Protocol name or path to render (single-protocol mode). "
				"Positional argument; also see -p/--protocol from shared CLI.",
		)
		selection_group.add_argument(
			"-a", "--all", dest="render_all", action="store_true",
			help=f"Render every shipped protocol to {DEFAULT_BULK_OUT_DIR}/.",
		)
		selection_group.add_argument(
			"--list-protocols",
			dest="list_protocols_flag", action="store_true",
			help="List available protocols (alternative to shared -l/--list).",
		)

		output_group = parser.add_argument_group("Manual Output")
		output_group.add_argument(
			"--out-dir", dest="out_dir", default=None,
			help=(
				"Output directory. Default: CWD for single, "
				f"{DEFAULT_BULK_OUT_DIR}/ for --all."
			),
		)
		output_group.add_argument(
			"--stdout", dest="to_stdout", action="store_true",
			help="Print rendered markdown to stdout instead of writing a file.",
		)

		lint_group = parser.add_argument_group("Lint and Validation")
		lint_group.add_argument(
			"--lint", dest="lint", action="store_true",
			help="Emit authoring lint warnings to stderr (does not alter rendered output).",
		)
		lint_group.add_argument(
			"--validate", dest="validate", action="store_true",
			help="Run lint pass and emit findings; do NOT render markdown. Allows --json/--ndjson output format.",
		)

	parser = toolkit_cli.build_parser(
		prog='render',
		description=(
			'Render mini-protocol YAML to a human-readable lab manual. '
			'Single mode writes ./<name>.md to the current directory; '
			'--all writes to ./output_manuals/.'
		),
		extras=register_manual_flags
	)

	args = parser.parse_args()

	#============================================
	# Protocol manual does not support JSON output when rendering markdown.
	# When --validate is set, JSON/NDJSON is allowed (for findings).
	# Otherwise, reject if user passes --json or --ndjson.
	#============================================
	if args.output_format != 'text' and not args.validate:
		toolkit_reporter.print_error(
			'Format not supported: render renders markdown only. '
			'(--json and --ndjson do not apply to rendered manuals. '
			'Use --validate to emit findings in JSON/NDJSON format.)'
		)
		sys.exit(2)

	#============================================
	# Map shared CLI args (protocols) to protocol_manual internal name (protocol_names).
	#============================================
	args.protocol_names = args.protocols

	return args


#============================================
def _collect_selection(args: object) -> object:
	"""
	Resolve CLI flags to (list_of_protocol_names, is_bulk).

	Returns (None, _) if nothing was selected (caller prints help and exits).
	Resolves name-or-path inputs to canonical protocol names.
	"""
	# --all: every shipped protocol
	if args.render_all:
		return toolkit_protocols.list_protocols(), True

	# --interactive: numbered menu
	if args.interactive:
		names = toolkit_protocols.list_protocols()
		selected = toolkit_interactive.pick_protocol_interactively(names)
		if selected is None:
			return None, False
		return [selected], False

	# -p / --protocol (multi) OR positional (single)
	raw_inputs = []
	if args.protocol_names:
		raw_inputs.extend(args.protocol_names)
	if args.protocol:
		raw_inputs.append(args.protocol)
	if not raw_inputs:
		return None, False

	resolved = []
	for name_or_path in raw_inputs:
		path = toolkit_protocols.resolve_protocol_path(name_or_path)
		if path is None:
			toolkit_reporter.print_error(f"Protocol '{name_or_path}' not found.")
			return None, False
		resolved.append(toolkit_protocols.protocol_name_from_path(path))
	return resolved, False


#============================================
def main() -> None:
	"""Dispatch by selection mode; write or print rendered manuals.

	# Verbosity contract (text output line targets):
	#   -q / --quiet   : 1 line (final pass/fail with key numbers)
	#   default        : 5-40 lines (stage summary, totals, top categories)
	#   -v / --verbose : 40-<200 lines (per-content-file breakdown, grouped, summarized)
	#   -j / --json    : full machine-readable detail (no bound)
	#   -J / --ndjson  : streamed full detail (no bound)
	# Raw per-step / per-asset internals go to JSON only, NOT text.
	# Manual renderer note: primary output is the rendered markdown file;
	# -j/-J reject (this tool emits markdown, not findings).
	"""
	args = parse_args()

	# --list-protocols is a fast filesystem operation.
	# Note: shared CLI also provides --list, but protocol_manual uses
	# --list-protocols specifically. --list is ignored for this tool.
	if args.list_protocols_flag:
		for name in toolkit_protocols.list_protocols():
			print(name)
		sys.exit(0)

	names, is_bulk = _collect_selection(args)
	if names is None:
		toolkit_reporter.print_error(
			"pass a <protocol> name, --protocol NAME..., --interactive, or --all."
		)
		sys.exit(2)

	catalog = validation.manual.protocol_manual_state.ObjectCatalog()

	#============================================
	# --validate mode: collect findings and emit in requested format.
	#============================================
	if args.validate:
		all_findings = []
		for name in names:
			lint = validation.manual.protocol_manual_state.LintCollector()
			_ = render_protocol_manual(name, catalog, lint)
			# Get the protocol path for the Finding.path field (repo-relative).
			resolved_path = toolkit_protocols.resolve_protocol_path(name)
			if resolved_path:
				# Convert to repo-relative path.
				try:
					protocol_path = os.path.relpath(resolved_path, REPO_ROOT)
				except (ValueError, TypeError):
					protocol_path = str(resolved_path)
			else:
				protocol_path = f"content/protocols/{name}/protocol.yaml"
			findings = lint.emit_findings(name, protocol_path)
			all_findings.extend(findings)

		# Count by severity (used for both summary line and exit code).
		error_count = sum(1 for f in all_findings if f.severity == toolkit_findings.Severity.ERROR)
		warning_count = sum(1 for f in all_findings if f.severity == toolkit_findings.Severity.WARNING)
		has_error = error_count > 0
		has_warning = warning_count > 0

		# Resolve verbosity level once for the entire output path.
		level = toolkit_verbosity.resolve_level(
			quiet=args.quiet,
			verbose=args.verbose,
		)

		# Emit findings and summary respecting the contracted output level.
		if args.output_format != 'text':
			# Machine formats (JSON, NDJSON) bypass the verbosity level entirely.
			toolkit_emit.emit_findings(all_findings, args.output_format)
		elif level == toolkit_verbosity.VerbosityLevel.QUIET:
			# QUIET: exactly one canonical summary line, no finding detail.
			toolkit_reporter.print_summary_line(
				len(names), error_count,
				item_label="manuals", warnings=warning_count,
			)
		elif level == toolkit_verbosity.VerbosityLevel.VERBOSE:
			# VERBOSE: summary + diagnostic block (top_codes per contract table).
			# The full findings dump is available via --json; text verbose stays
			# within the 199-line budget by emitting only the diagnostic summary.
			toolkit_reporter.print_summary_line(
				len(names), error_count,
				item_label="manuals", warnings=warning_count,
			)
			# Build top_codes from findings: count occurrences of each code.
			code_counts: dict = {}
			for f in all_findings:
				code_counts[f.code] = code_counts.get(f.code, 0) + 1
			diag_data = toolkit_verbosity.DiagnosticData(
				top_codes=list(code_counts.items()),
			)
			print(toolkit_verbosity.diagnostic_summary(diag_data))
		else:
			# NORMAL: summary totals only (no per-finding dump); within 40-line budget.
			toolkit_reporter.print_summary_line(
				len(names), error_count,
				item_label="manuals", warnings=warning_count,
			)

		exit_code = 0
		if has_error:
			exit_code = 1
		elif has_warning and args.strict:
			exit_code = 1
		sys.exit(exit_code)

	# Choose output sink. --stdout overrides everything; otherwise pick a
	# directory. Bulk defaults to output_manuals/; single defaults to CWD.
	if args.to_stdout:
		for name in names:
			if not args.quiet:
				toolkit_reporter.print_section_header(name)
			lint = validation.manual.protocol_manual_state.LintCollector() if args.lint else None
			md = render_protocol_manual(name, catalog, lint)
			print(md)
			if lint is not None:
				lint.emit_text(sys.stderr)
		sys.exit(0)

	if args.out_dir is not None:
		out_dir = args.out_dir
	elif is_bulk:
		out_dir = DEFAULT_BULK_OUT_DIR
	else:
		out_dir = "."

	failures = 0
	for name in names:
		if not args.quiet:
			toolkit_reporter.print_section_header(f"Rendering {name}")
		lint = validation.manual.protocol_manual_state.LintCollector() if args.lint else None
		md = render_protocol_manual(name, catalog, lint)
		out_path = write_manual(name, md, out_dir)
		if not args.quiet:
			toolkit_reporter.print_pass(out_path)
		if lint is not None:
			lint.emit_text(sys.stderr)

	if not args.quiet:
		toolkit_reporter.print_summary_line(
			len(names), failures, item_label="manuals",
		)

	sys.exit(0)


if __name__ == "__main__":
	main()
