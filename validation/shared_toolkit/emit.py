"""Unified findings emitter for multiple output formats.

Renders findings in text (via rich), JSON, or newline-delimited JSON format.
Normalizes Finding dataclasses from different tools via duck-typing + getattr fallbacks.
"""

import json
import validation.shared_toolkit.console as toolkit_console


def finding_to_dict(finding: object) -> dict:
	"""
	Convert a Finding-like dataclass to a normalized dict for JSON export.

	Handles different field names across domain-specific Finding classes by using
	getattr with fallbacks. Strips None values.

	Args:
		finding: A Finding instance or duck-typed object with severity/tool/code/message fields.

	Returns:
		dict with keys: severity, tool, code, message, and optional path/line/protocol/scene/step/target/extras.
	"""
	# Map canonical field names to potential alternatives in domain-specific Finding classes
	output = {
		'severity': getattr(finding, 'severity', None),
		'tool': getattr(finding, 'tool', None),
		'code': getattr(finding, 'code', None),
		'message': getattr(finding, 'message', None),
	}

	# Optional fields with aliases
	path = getattr(finding, 'path', None)
	if path is not None:
		output['path'] = path

	line = getattr(finding, 'line', None)
	if line is not None:
		output['line'] = line

	protocol = getattr(finding, 'protocol', None)
	if protocol is not None:
		output['protocol'] = protocol

	scene = getattr(finding, 'scene', None)
	if scene is not None:
		output['scene'] = scene

	step = getattr(finding, 'step', None)
	if step is not None:
		output['step'] = step

	target = getattr(finding, 'target', None)
	if target is not None:
		output['target'] = target

	extras = getattr(finding, 'extras', None)
	if extras is not None:
		output['extras'] = extras

	# Normalize Severity enum to its string value for JSON serialization.
	if hasattr(output['severity'], 'value'):
		output['severity'] = output['severity'].value

	return output


def emit_findings(findings: list, output_format: str = 'text', console: object=None) -> None:
	"""
	Render a list of findings in the requested output format.

	Args:
		findings: list of Finding objects (or duck-typed Finding-like objects).
		output_format: one of 'text', 'json', or 'ndjson'.
		console: optional rich.console.Console instance. If None and format is 'text',
		         a new console is created with no_color=False.

	Output behavior:
		- 'text': prints findings table via rich.Console. Color-codes by severity.
		- 'json': prints single JSON doc: {"findings": [...]} to stdout.
		- 'ndjson': prints one JSON object per line to stdout (no enclosing array).
	"""
	if output_format == 'text':
		# Use provided console or create a default one
		if console is None:
			console = toolkit_console.make_console(no_color=False)

		# Render findings as a simple table via rich
		# Summary: for now, print severity-colored lines; full table layout
		# can be enhanced later.
		for finding in findings:
			severity_str = getattr(finding.severity, 'value', str(finding.severity))
			msg = f"{severity_str:7} {finding.tool:12} {finding.code:20} {finding.message}"
			if finding.path:
				msg += f" [{finding.path}"
				if finding.line:
					msg += f":{finding.line}"
				msg += "]"

			# Color by severity
			if severity_str == 'ERROR':
				msg_styled = f"[bold red]{msg}[/bold red]"
			elif severity_str == 'WARNING':
				msg_styled = f"[bold yellow]{msg}[/bold yellow]"
			else:
				msg_styled = f"[blue]{msg}[/blue]"

			console.print(msg_styled)

	elif output_format == 'json':
		# Single JSON document
		findings_dicts = [finding_to_dict(f) for f in findings]
		output_dict = {'findings': findings_dicts}
		json_str = json.dumps(output_dict, indent=2)
		print(json_str)

	elif output_format == 'ndjson':
		# Newline-delimited JSON (one object per line)
		for finding in findings:
			finding_dict = finding_to_dict(finding)
			json_str = json.dumps(finding_dict)
			print(json_str)
