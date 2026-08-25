"""
Shared output helpers for tools/ CLIs.

Goal: every tool's stdout follows the same pattern so authors learn it
once. Section headers wrap a block. Per-file PASS/FAIL lines name the
file. A summary line closes the run with counts.

All helpers respect a `quiet` flag where the tool wants per-file output
suppressed on success but summary still printed.
"""

import sys

import validation.shared_toolkit.verbosity as verbosity


def print_section_header(name: object) -> None:
	"""Print a `=== name ===` section header to stdout."""
	print(f"=== {name} ===")


def print_pass(label: object) -> None:
	"""Print a `PASS: label` line."""
	print(f"PASS: {label}")


def print_fail(label: object, reason: object=None) -> None:
	"""Print a `FAIL: label` line, with optional reason on the same line."""
	if reason:
		print(f"FAIL: {label} - {reason}")
	else:
		print(f"FAIL: {label}")


def print_warning(label: object, reason: object=None) -> None:
	"""Print a `WARN: label` line, with optional reason on the same line."""
	if reason:
		print(f"WARN: {label} - {reason}")
	else:
		print(f"WARN: {label}")


def print_error(message: object) -> None:
	"""Print an error line to stderr."""
	print(f"ERROR: {message}", file=sys.stderr)


def print_summary_line(total: object, errors: object, *, item_label: object="files", warnings: object=0, advisories: object=0) -> None:
	"""
	Print the canonical stage summary line.

	Delegates to verbosity.summary_line so there is exactly one summary
	string in the codebase. The line always prints all three severity-tier
	counts, including zeros:
	  "Checked N files. E errors. W warnings. A advisories."

	Severity is closed at three tiers: error (blocks the run), warning
	(should fix), advisory (cleanup/info). The second positional arg is the
	blocking ERROR count.
	"""
	line = verbosity.summary_line(
		total, errors, item_label=item_label, warnings=warnings, advisories=advisories
	)
	print(line)
