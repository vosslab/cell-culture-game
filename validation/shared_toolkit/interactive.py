"""Numbered-menu picker shared by tools that offer --interactive selection."""

import sys


def pick_protocol_interactively(protocols: object, prompt: object="Select a protocol (number): ", intro: object="Available protocols:") -> object:
	"""
	Render a numbered menu of protocol names and return the chosen name.

	Returns the selected protocol name, or None if the user gave invalid
	input or there are no protocols. The caller decides how to handle
	None (typically print an error and exit 1).
	"""
	if not protocols:
		print("No protocols found.", file=sys.stderr)
		return None
	if not sys.stdin.isatty():
		print("Interactive mode requires a terminal.", file=sys.stderr)
		return None
	print(intro)
	for idx, name in enumerate(protocols, 1):
		print(f"  {idx}. {name}")
	raw = input(prompt).strip()
	# Empty input or non-numeric input returns None; caller reports.
	if not raw or not raw.lstrip("-").isdigit():
		print("Invalid input.", file=sys.stderr)
		return None
	choice_idx = int(raw) - 1
	if choice_idx < 0 or choice_idx >= len(protocols):
		print("Invalid selection.", file=sys.stderr)
		return None
	return protocols[choice_idx]
