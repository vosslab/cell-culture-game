#!/usr/bin/env python3
"""
run_smoke.py - Python wrapper for browser smoke test.

Builds the app and runs the Playwright smoke test at
tests/playwright/test_game_ui.mjs to verify the app loads, renders key UI
elements, and runs through the first 9 gates of the bench scene.

This is a fast check (not a full protocol playthrough).

For a real end-to-end protocol playthrough, use tools/run_protocol_walkthrough.py.

Usage:
  source source_me.sh && python3 tools/run_smoke.py
  source source_me.sh && python3 tools/run_smoke.py --no-build

Exit codes:
  0  build green AND smoke passed all 9 gates
  1  build failed
  2  smoke failed
"""

import subprocess
import pathlib
import argparse
import sys
import os


def get_repo_root() -> object:
	"""Determine REPO_ROOT via git rev-parse --show-toplevel."""
	result = subprocess.run(
		['git', 'rev-parse', '--show-toplevel'],
		capture_output=True,
		text=True,
	)
	if result.returncode != 0:
		raise RuntimeError(f"Failed to find repo root: {result.stderr}")
	return pathlib.Path(result.stdout.strip())


def parse_args() -> object:
	"""Parse command-line arguments."""
	parser = argparse.ArgumentParser(
		description='Fast browser smoke test for the cell culture game.',
	)
	parser.add_argument(
		'-b', '--no-build',
		dest='no_build',
		action='store_true',
		help='Skip build step; run smoke test only',
	)
	args = parser.parse_args()
	return args


def main() -> object:
	args = parse_args()
	repo_root = get_repo_root()

	# Check for node_modules
	node_modules = repo_root / 'node_modules'
	if not node_modules.is_dir():
		print("node_modules missing. Run 'npm install' first.", file=sys.stderr)
		return 1

	# Warn if Playwright browsers may be missing
	playwright_cache_macos = pathlib.Path.home() / 'Library' / 'Caches' / 'ms-playwright'
	playwright_cache_linux = pathlib.Path.home() / '.cache' / 'ms-playwright'
	if not playwright_cache_macos.is_dir() and not playwright_cache_linux.is_dir():
		print("Playwright browsers may be missing. If the smoke fails to launch chromium,", file=sys.stderr)
		print("run 'npx playwright install chromium' and retry.", file=sys.stderr)

	# Build step (unless --no-build)
	if not args.no_build:
		print("==> Building dist/ ...")
		build_script = repo_root / 'build_github_pages.sh'
		result = subprocess.run(['bash', str(build_script)], cwd=str(repo_root), env=os.environ.copy())
		if result.returncode != 0:
			print("BUILD FAILED", file=sys.stderr)
			return 1

	# Run the smoke test
	print()
	print("==> Running browser smoke test ...")
	smoke_script = repo_root / 'tests' / 'playwright' / 'test_game_ui.mjs'
	result = subprocess.run(['node', str(smoke_script)], cwd=str(repo_root), env=os.environ.copy())
	if result.returncode != 0:
		print("SMOKE TEST FAILED", file=sys.stderr)
		return 2

	print()
	print("All gates passed. Screenshot: test-results/test_game_ui.png")
	return 0


if __name__ == '__main__':
	sys.exit(main())
