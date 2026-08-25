#!/usr/bin/env python3
"""
run_protocol_walkthrough.py - Python wrapper for YAML-driven protocol walker.

Invokes tests/playwright/e2e/protocol_walkthrough_yaml.mjs via Node, with optional build step.

Usage:
  source source_me.sh && python3 tools/run_protocol_walkthrough.py --list-protocols
  source source_me.sh && python3 tools/run_protocol_walkthrough.py --protocol cell_culture
  source source_me.sh && python3 tools/run_protocol_walkthrough.py --protocol cell_culture --wrong-order
  source source_me.sh && python3 tools/run_protocol_walkthrough.py --protocol cell_culture --no-build
"""

import subprocess
import pathlib
import argparse
import sys


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


def discover_protocols(repo_root: object) -> object:
	"""
	Discover available protocols by recursively searching for protocol.yaml.

	Works with both flat layout (content/protocols/<name>) and clustered
	layout (content/protocols/<cluster>/<name>) by using rglob.
	"""
	protocols_dir = repo_root / 'content' / 'protocols'
	if not protocols_dir.is_dir():
		return []

	protocols = []
	for protocol_yaml in sorted(protocols_dir.rglob('protocol.yaml')):
		# Protocol directory is the parent of protocol.yaml
		protocol_dir = protocol_yaml.parent
		protocols.append(protocol_dir.name)

	return sorted(protocols)


def parse_args() -> object:
	"""Parse command-line arguments."""
	parser = argparse.ArgumentParser(
		description='YAML-driven protocol walker for UI regression testing.',
	)
	group = parser.add_mutually_exclusive_group()
	group.add_argument(
		'-p', '--protocol',
		dest='protocol',
		default='cell_culture',
		help='Protocol name to walk (default: cell_culture)',
	)
	group.add_argument(
		'-l', '--list-protocols',
		dest='list_protocols',
		action='store_true',
		help='List available protocols and exit',
	)
	parser.add_argument(
		'-w', '--wrong-order',
		dest='wrong_order',
		action='store_true',
		help='Enable wrong-order item injection',
	)
	parser.add_argument(
		'-b', '--no-build',
		dest='no_build',
		action='store_true',
		help='Skip build step; run walker only',
	)
	args = parser.parse_args()
	return args


def main() -> object:
	args = parse_args()
	repo_root = get_repo_root()

	# Handle --list-protocols
	if args.list_protocols:
		protocols = discover_protocols(repo_root)
		for p in protocols:
			print(p)
		return 0

	# Build step (unless --no-build)
	if not args.no_build:
		build_script = repo_root / 'build_github_pages.sh'
		if build_script.exists():
			result = subprocess.run(['bash', str(build_script)], cwd=str(repo_root))
			if result.returncode != 0:
				print(f"Error: build_github_pages.sh exited with code {result.returncode}", file=sys.stderr)
				return result.returncode
		else:
			print(f"Warning: build_github_pages.sh not found at {build_script}", file=sys.stderr)

	# Run the walker
	walker_script = repo_root / 'tests' / 'playwright' / 'e2e' / 'protocol_walkthrough_yaml.mjs'
	walker_cmd = ['node', str(walker_script)]

	# Add --protocol flag
	walker_cmd.extend(['--protocol', args.protocol])

	# Add --wrong-order if set
	if args.wrong_order:
		walker_cmd.append('--wrong-order')

	# Run walker and propagate exit code
	result = subprocess.run(walker_cmd, cwd=str(repo_root), check=False)
	return result.returncode


if __name__ == '__main__':
	sys.exit(main())
