#!/usr/bin/env python3
"""End-to-end checks for the exhaustive runner's subprocess timeout helper.

This check belongs in ``tests/e2e`` because it launches real child processes,
including one that must be terminated by the timeout boundary.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER = REPO_ROOT / "tools" / "run_with_timeout.py"


def run_helper(*arguments: str) -> subprocess.CompletedProcess[str]:
	"""Invoke the helper through the repository Python interpreter."""
	return subprocess.run(
		[sys.executable, str(RUNNER), *arguments],
		check=False,
		capture_output=True,
		text=True,
		timeout=10,
	)


def check_wrapped_command_status() -> None:
	"""Require the helper to preserve ordinary success and failure statuses."""
	success = run_helper("--seconds", "2", "--", sys.executable, "-c", "pass")
	failure = run_helper(
		"--seconds",
		"2",
		"--",
		sys.executable,
		"-c",
		"raise SystemExit(7)",
	)

	if success.returncode != 0:
		raise SystemExit(
			f"wrapped successful command returned {success.returncode}: {success.stderr}"
		)
	if failure.returncode != 7:
		raise SystemExit(
			f"wrapped failing command returned {failure.returncode}; expected 7"
		)


def check_timeout_status() -> None:
	"""Require timeout termination and the documented timeout status."""
	result = run_helper(
		"--seconds",
		"0.1",
		"--",
		sys.executable,
		"-c",
		"import time; time.sleep(10)",
	)

	if result.returncode != 124:
		raise SystemExit(
			f"timed-out command returned {result.returncode}; expected 124"
		)
	if "TIMEOUT: command exceeded 0.1s" not in result.stderr:
		raise SystemExit(
			"timeout helper did not report the configured 0.1-second boundary"
		)


def main() -> int:
	"""Run the real subprocess checks."""
	check_wrapped_command_status()
	check_timeout_status()
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
