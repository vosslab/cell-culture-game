"""Unified argparse builder for validation and analysis tools.

Creates a consistent flag set across all entry-point CLIs so users learn
the interface once. Returns a parser with all ratified flags; callers do not
invoke parse_args() themselves -- they let adopters handle the final parse.
"""

import argparse
import os


def build_parser(prog: str, description: str, extras: object=None) -> argparse.ArgumentParser:
	"""
	Build and return a unified argparse.ArgumentParser with ratified flags.

	Args:
		prog: program name for help text.
		description: one-line description of the tool.
		extras: optional callable(parser) invoked after shared flags to register tool-specific flags.

	Returns:
		argparse.ArgumentParser configured with unified flags (but not yet parsed).

	Shared flags (final argparse table from M3 ratification):
		--focus / -f: isolate to focus patterns only.
		--protocol / -p: select specific protocols (nargs='+').
		--object / -o, --asset / -A: select specific objects (nargs='+').
		--scene / -S: select specific scenes (nargs='+').
		--list / -l: list only; do not validate or run.
		--interactive / -i: enter interactive selection mode.
		--quiet / -q: show final pass/fail only (one line).
		--verbose / -v: show diagnostic summary (grouped findings + top offenders).
		--errors-only / -e: show only failures.
		--strict / -s: enforce strict mode (fail on warnings).
		--no-color: suppress color output.
		--json / -j: emit JSON format.
		--ndjson / -J: emit newline-delimited JSON.
		--only / -O: filter to specific stages (nargs='+', choices=['yaml','svg','stepper','structure']).

	Selection rules (not enforced here; document in epilog):
		- --focus and per-domain selectors (--protocol, --object, --scene) are
		  mutually exclusive. Focus mode runs against focus patterns; selectors
		  run against specific named items. Document the choice in help text.
		- --quiet and --verbose are mutually exclusive (verbosity group).
		- --json and --ndjson are mutually exclusive (format group).
	"""
	parser = argparse.ArgumentParser(
		prog=prog,
		description=description,
		formatter_class=argparse.RawDescriptionHelpFormatter,
	)

	# Selection group (mutual exclusion deferred to caller validation)
	selection_group = parser.add_argument_group('Selection')
	selection_group.add_argument(
		'-f', '--focus',
		dest='focus',
		action='store_true',
		default=False,
		help='Run against focus patterns only (mutually exclusive with --protocol, --object, --scene).'
	)
	selection_group.add_argument(
		'-p', '--protocol',
		dest='protocols',
		nargs='+',
		default=None,
		help='Select specific protocols to validate (space-separated names or paths).'
	)
	selection_group.add_argument(
		'-o', '--object',
		dest='objects',
		nargs='+',
		default=None,
		help='Select specific objects to validate (space-separated names).'
	)
	selection_group.add_argument(
		'-A', '--asset',
		dest='objects',
		nargs='+',
		default=None,
		help='Alias for --object.'
	)
	selection_group.add_argument(
		'-S', '--scene',
		dest='scenes',
		nargs='+',
		default=None,
		help='Select specific scenes to validate (space-separated names).'
	)

	# List and interactive
	list_group = parser.add_argument_group('List and discovery')
	list_group.add_argument(
		'-l', '--list',
		dest='list_only',
		action='store_true',
		default=False,
		help='List items matching filters; do not validate or run.'
	)
	list_group.add_argument(
		'-i', '--interactive',
		dest='interactive',
		action='store_true',
		default=False,
		help='Enter interactive selection mode.'
	)

	# Verbosity group (mutually exclusive: quiet or verbose)
	verbosity_group = parser.add_mutually_exclusive_group()
	verbosity_group.add_argument(
		'-q', '--quiet',
		dest='quiet',
		action='store_true',
		default=False,
		help='Show final pass/fail summary only (one line).'
	)
	verbosity_group.add_argument(
		'-v', '--verbose',
		dest='verbose',
		action='store_true',
		default=False,
		help='Show diagnostic summaries: per-stage counts, grouped findings, top '
		'offenders, and selected PASS details. For full per-step or per-asset '
		'data, use --json or --ndjson.'
	)

	# Output control
	output_group = parser.add_argument_group('Output control')
	output_group.add_argument(
		'-e', '--errors-only',
		dest='errors_only',
		action='store_true',
		default=False,
		help='Show only findings at ERROR level; suppress warnings and info.'
	)
	output_group.add_argument(
		'-s', '--strict',
		dest='strict',
		action='store_true',
		default=False,
		help='Strict mode: fail if warnings present.'
	)
	output_group.add_argument(
		'--no-color',
		dest='no_color',
		action='store_true',
		default=bool(os.environ.get('NO_COLOR')),
		help='Suppress color output (also respects NO_COLOR env var).'
	)

	# Format group (mutually exclusive)
	format_group = parser.add_mutually_exclusive_group()
	format_group.add_argument(
		'-j', '--json',
		dest='output_format',
		action='store_const',
		const='json',
		default='text',
		help='Emit JSON format: {"findings": [...]}'
	)
	format_group.add_argument(
		'-J', '--ndjson',
		dest='output_format',
		action='store_const',
		const='ndjson',
		default='text',
		help='Emit newline-delimited JSON (one finding per line).'
	)

	# Staging filter
	stage_group = parser.add_argument_group('Staging')
	stage_group.add_argument(
		'-O', '--only',
		dest='stages',
		nargs='+',
		choices=['yaml', 'svg', 'stepper', 'structure', 'manual', 'scene-lint', 'scene-design'],
		default=None,
		help='Filter to specific stages: yaml (content validation), svg (asset validation), stepper (walker), structure (folder layout), manual (protocol manuals), scene-lint (Group A render-failure predictor), scene-design (composition scorecard).'
	)

	# Call extras callback if provided
	if extras is not None:
		extras(parser)

	return parser
