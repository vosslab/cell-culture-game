"""Run one command with a bounded wall time and terminate its process group."""

from __future__ import annotations

import argparse
import os
import shlex
import signal
import subprocess
import sys
from collections.abc import Sequence

TIMEOUT_EXIT_CODE = 124
TERMINATION_GRACE_SECONDS = 5.0


def positive_seconds(value: str) -> float:
	"""Parse a strictly positive timeout value."""
	seconds = float(value)
	if seconds <= 0:
		raise argparse.ArgumentTypeError("timeout must be greater than zero")
	return seconds


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
	"""Parse the timeout and command without interpreting command arguments."""
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--seconds", required=True, type=positive_seconds)
	parser.add_argument("command", nargs=argparse.REMAINDER)
	args = parser.parse_args(argv)
	if args.command and args.command[0] == "--":
		args.command = args.command[1:]
	if not args.command:
		parser.error("a command is required after --")
	return args


def terminate_process_group(
	process: subprocess.Popen[bytes],
	grace_seconds: float = TERMINATION_GRACE_SECONDS,
) -> None:
	"""Terminate the command and descendants, escalating only if needed."""
	try:
		os.killpg(process.pid, signal.SIGTERM)
	except ProcessLookupError:
		process.wait()
		return
	try:
		process.wait(timeout=grace_seconds)
	except subprocess.TimeoutExpired:
		try:
			os.killpg(process.pid, signal.SIGKILL)
		except ProcessLookupError:
			pass
		process.wait()


def run_with_timeout(command: Sequence[str], seconds: float) -> int:
	"""Run *command* and return its exit code, or 124 after a timeout."""
	try:
		process = subprocess.Popen(command, start_new_session=True)
	except FileNotFoundError:
		print(f"ERROR: command not found: {command[0]}", file=sys.stderr)
		return 127

	try:
		return process.wait(timeout=seconds)
	except subprocess.TimeoutExpired:
		print(
			f"TIMEOUT: command exceeded {seconds:g}s: {shlex.join(command)}",
			file=sys.stderr,
		)
		terminate_process_group(process)
		return TIMEOUT_EXIT_CODE


def main(argv: Sequence[str] | None = None) -> int:
	"""Run the requested command."""
	args = parse_args(sys.argv[1:] if argv is None else argv)
	return run_with_timeout(args.command, args.seconds)


if __name__ == "__main__":
	raise SystemExit(main())
