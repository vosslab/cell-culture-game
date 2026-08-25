"""
Compact rich dashboard for stepper walk results.

The validator renders a colored dashboard at the end of every whole-tree
run via tools/validators/compiled_summary.py. This module is the stepper
analogue: aggregate (protocol, type, steps, interactions, emitter)
tuples and render an indented panel covering totals, per-type counts,
PASS/FAIL split, and the top finding codes with sample messages.

Per `docs/REPO_STYLE.md`, every third-party import is declared in
pip_requirements.txt; `rich` was already a transitive dep of the
validator dashboard but was not declared. The stepper inherits it.
"""

from collections import Counter, defaultdict

import validation.shared_toolkit.console
import validation.stepper.findings


def aggregate(walks: object) -> object:
	"""
	Aggregate a list of walk results into a single counts dict.

	Args:
		walks: list of tuples
			(protocol_name, protocol_type, step_count, interaction_count, emitter)

	Returns:
		dict consumable by render().
	"""
	by_type = Counter()
	total_steps = 0
	total_interactions = 0
	error_count = 0
	warning_count = 0
	findings_by_code = defaultdict(
		lambda: {"level": None, "count": 0, "samples": []}
	)
	failed_protocols = []
	clean_protocols = []
	# Per-protocol rollup: name -> {errors, warnings, codes: Counter()}.
	# Codes Counter tracks how many of each finding code this protocol
	# emitted, so the dashboard can show which rule fired where.
	per_protocol = {}

	for name, ptype, steps, interactions, emitter in walks:
		by_type[ptype or "unknown"] += 1
		total_steps += steps
		total_interactions += interactions

		proto_errors = 0
		proto_warnings = 0
		proto_codes = Counter()

		for finding in emitter.findings:
			level_value = finding.level.value
			if finding.level == validation.stepper.findings.Level.ERROR:
				error_count += 1
				proto_errors += 1
			else:
				warning_count += 1
				proto_warnings += 1
			proto_codes[(level_value, finding.code)] += 1
			entry = findings_by_code[finding.code]
			entry["level"] = level_value
			entry["count"] += 1
			# Keep a couple of example messages so the dashboard line is
			# self-explanatory without forcing the reader to grep for
			# the first occurrence.
			if len(entry["samples"]) < 2:
				entry["samples"].append(finding.message)

		per_protocol[name] = {
			"errors": proto_errors,
			"warnings": proto_warnings,
			"codes": dict(proto_codes),
			"step_count": steps,
			"interaction_count": interactions,
		}

		if proto_errors > 0:
			failed_protocols.append(name)
		else:
			clean_protocols.append(name)

	counts = {
		"total_protocols": len(walks),
		"by_type": dict(by_type),
		"total_steps": total_steps,
		"total_interactions": total_interactions,
		"errors": error_count,
		"warnings": warning_count,
		"failed_protocols": failed_protocols,
		"clean_protocols": clean_protocols,
		"findings_by_code": dict(findings_by_code),
		"per_protocol": per_protocol,
	}
	return counts


def render(counts: object, max_codes: object=10) -> None:
	"""
	Render the aggregated counts to stdout via a rich Console.

	max_codes limits the per-code breakdown to the top N rows so the
	dashboard stays scannable even on noisy runs.
	"""
	console = validation.shared_toolkit.console.make_console()
	output_lines = []

	#============================================
	# Totals
	output_lines.append("[bold cyan]Stepped content YAML[/bold cyan]")
	output_lines.append("[dim]Totals[/dim]")
	output_lines.append(f"  Protocols: {counts['total_protocols']}")
	type_strs = [f"{t} {n}" for t, n in sorted(counts['by_type'].items())]
	output_lines.append(f"  By type: {', '.join(type_strs) if type_strs else '(none)'}")
	output_lines.append(f"  Steps walked: {counts['total_steps']}")
	output_lines.append(f"  Interactions walked: {counts['total_interactions']}")

	fail_count = len(counts['failed_protocols'])
	pass_count = len(counts['clean_protocols'])
	pass_color = "green" if fail_count == 0 else "yellow"
	fail_color = "red" if fail_count > 0 else "dim"
	output_lines.append(
		f"  Pass: [{pass_color}]{pass_count}[/{pass_color}]   "
		f"Fail: [{fail_color}]{fail_count}[/{fail_color}]"
	)

	error_color = "red" if counts['errors'] > 0 else "green"
	warning_color = "yellow" if counts['warnings'] > 0 else "dim"
	output_lines.append(
		f"  Errors: [{error_color}]{counts['errors']}[/{error_color}]   "
		f"Warnings: [{warning_color}]{counts['warnings']}[/{warning_color}]"
	)

	#============================================
	# Findings by code (grouped, top N)
	if counts['findings_by_code']:
		output_lines.append("")
		output_lines.append("[bold yellow]Findings by code[/bold yellow] [dim](top results)[/dim]")
		# Order: ERROR codes first, then WARNING; within each, by count desc.
		def sort_key(item: object) -> object:
			_code, entry = item
			level_priority = 0 if entry['level'] == "ERROR" else 1
			return (level_priority, -entry['count'])
		sorted_codes = sorted(counts['findings_by_code'].items(), key=sort_key)
		for code, entry in sorted_codes[:max_codes]:
			level_color = "red" if entry['level'] == "ERROR" else "yellow"
			output_lines.append(
				f"  [{level_color}]{entry['level']}[/{level_color}]  "
				f"[bold]{code}[/bold]  x{entry['count']}"
			)
			# One sample message per code; trim long messages.
			if entry['samples']:
				sample = entry['samples'][0]
				if len(sample) > 110:
					sample = sample[:107] + "..."
				output_lines.append(f"    [dim]e.g.[/dim] {sample}")
		remaining = len(counts['findings_by_code']) - max_codes
		if remaining > 0:
			output_lines.append(f"  [dim]... and {remaining} more code(s)[/dim]")

	#============================================
	# Per-protocol breakdown: name, error/warning counts, and the codes
	# that fired in that protocol. Skip clean rows so the table stays
	# scannable on a tree with mostly-passing protocols.
	noisy_rows = [
		(name, entry)
		for name, entry in counts['per_protocol'].items()
		if entry['errors'] > 0 or entry['warnings'] > 0
	]
	if noisy_rows:
		output_lines.append("")
		output_lines.append(
			"[bold cyan]Per-protocol breakdown[/bold cyan] "
			"[dim](only protocols with findings)[/dim]"
		)
		# Sort errors-first, then by warning count desc, then by name.
		def proto_sort_key(item: object) -> object:
			_name, entry = item
			return (-entry['errors'], -entry['warnings'], _name)
		noisy_rows.sort(key=proto_sort_key)
		# Column widths: protocol name padded to longest, then E= and
		# W= columns, then the per-code breakdown after a separator.
		name_width = max(len(name) for name, _ in noisy_rows)
		for name, entry in noisy_rows:
			err = entry['errors']
			warn = entry['warnings']
			err_color = "red" if err > 0 else "dim"
			warn_color = "yellow" if warn > 0 else "dim"
			# Group codes by level so the line reads ERROR codes then
			# WARNING codes.
			codes = entry['codes']
			error_parts = []
			warning_parts = []
			for (level, code), count in sorted(
				codes.items(), key=lambda kv: (-kv[1], kv[0][1])
			):
				piece = f"{code} x{count}"
				if level == "ERROR":
					error_parts.append(piece)
				else:
					warning_parts.append(piece)
			breakdown_pieces = []
			if error_parts:
				breakdown_pieces.append("[red]" + ", ".join(error_parts) + "[/red]")
			if warning_parts:
				breakdown_pieces.append("[yellow]" + ", ".join(warning_parts) + "[/yellow]")
			breakdown = "  |  ".join(breakdown_pieces) if breakdown_pieces else "[dim](none)[/dim]"
			output_lines.append(
				f"  {name:<{name_width}}  "
				f"[{err_color}]E={err}[/{err_color}]  "
				f"[{warn_color}]W={warn}[/{warn_color}]  "
				f"{breakdown}"
			)

	#============================================
	# Failed protocols (named so the reader knows where to look). The
	# per-protocol breakdown above already names them, but this keeps a
	# bold red list at the bottom so a glance after a long run shows
	# what to fix first.
	if counts['failed_protocols']:
		output_lines.append("")
		output_lines.append("[bold red]Failed protocols[/bold red]")
		for name in counts['failed_protocols']:
			output_lines.append(f"  - {name}")

	console.print('\n'.join(output_lines))
