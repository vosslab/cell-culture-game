#!/usr/bin/env python3
"""
analyze_protocol_audit.py - Audit protocol steps for completeness and consistency.

Validates protocol YAML against a set of status rules:
- [OK] Step has interactionSequence and every requiredItem is in usedItems
- [INFO] Step has no interactionSequence (modal/direct/runtime flow)
- [WARN] Step has interactionSequence but requiredItems not all in usedItems
- [ERROR] Missing item/reagent, or unused non-visual item

Usage:
  source source_me.sh && python3 tools/analyze_protocol_audit.py --list-protocols
  source source_me.sh && python3 tools/analyze_protocol_audit.py --protocol cell_culture
  source source_me.sh && python3 tools/analyze_protocol_audit.py --protocol cell_culture --strict
"""

import subprocess
import pathlib
import sys
import yaml

import validation.shared_toolkit.cli as toolkit_cli


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


def load_yaml_file(path: object) -> object:
	"""Load a YAML file and return parsed content."""
	with open(path, 'r') as f:
		return yaml.safe_load(f)


def derive_used_items(step: object) -> object:
	"""Derive usedItems from interactionSequence in first-use order (tool -> source -> destination, de-duplicated)."""
	seen = set()
	used = []
	for interaction in step.get('interactionSequence', []):
		if interaction.get('tool') and interaction['tool'] not in seen:
			seen.add(interaction['tool'])
			used.append(interaction['tool'])
		if interaction.get('source') and interaction['source'] not in seen:
			seen.add(interaction['source'])
			used.append(interaction['source'])
		if interaction.get('destination') and interaction['destination'] not in seen:
			seen.add(interaction['destination'])
			used.append(interaction['destination'])
	return used


def discover_protocols(repo_root: object) -> object:
	"""Discover available protocols by globbing content/protocols/*/protocol.yaml."""
	content_dir = repo_root / 'content' / 'protocols'
	if not content_dir.is_dir():
		return []

	protocols = []
	for subdir in content_dir.iterdir():
		if subdir.is_dir():
			protocol_yaml = subdir / 'protocol.yaml'
			if protocol_yaml.exists():
				protocols.append(subdir.name)

	return sorted(protocols)


def classify_step(step: object, items: object, reagents: object, item_index: object) -> object:
	"""
	Classify a step and return (status, message).

	Status: 'OK', 'INFO', 'WARN', 'ERROR'
	"""
	required_items = step.get('requiredItems', [])
	interactions = step.get('interactionSequence', [])
	used_items = derive_used_items(step)

	# Check for missing items in requiredItems or usedItems
	for item_id in required_items:
		if item_id not in item_index:
			return ('ERROR', f"required item '{item_id}' not in items.yaml")
	for item_id in used_items:
		if item_id not in item_index:
			return ('ERROR', f"used item '{item_id}' not in items.yaml")

	# Rule 1: If no interactionSequence, return INFO (modal/direct flow)
	if not interactions:
		return ('INFO', 'no interactionSequence (modal/direct flow)')

	# Rule 2: Check if every requiredItem is in usedItems
	missing = set(required_items) - set(used_items)
	if missing:
		missing_str = ', '.join(sorted(missing))
		return ('WARN', f"missing required item in interaction: {missing_str}")

	# Rule 3: Everything matches
	return ('OK', '')


def audit_protocol(repo_root: object, protocol_name: object, items_data: object, reagents_data: object, protocol_data: object) -> object:
	"""Audit a protocol and return list of (status, step_index, step_id, message)."""
	steps = protocol_data['steps']
	items = items_data['items']
	reagents = reagents_data['reagents']

	# Build item index
	item_index = set(items.keys())

	# Track which items are used (requiredItems across all steps)
	item_usage = {item_id: [] for item_id in items.keys()}

	# Audit each step
	results = []
	for step_index, step in enumerate(steps):
		step_id = step['id']
		required_items = step.get('requiredItems', [])

		# Track usage
		for item_id in required_items:
			if item_id in item_usage:
				item_usage[item_id].append(step_id)

		# Classify the step
		status, msg = classify_step(step, items, reagents, item_index)
		results.append((status, step_index + 1, step_id, msg, required_items))

	# Check for unused non-visual items
	unused_errors = []
	for item_id, usage_list in item_usage.items():
		if not usage_list:
			item_def = items[item_id]
			# visualOnly is optional; keep .get() for genuinely optional field
			if not item_def.get('visualOnly'):
				unused_errors.append((item_id, item_def))

	return results, unused_errors


def parse_args() -> object:
	"""Parse command-line arguments using unified toolkit parser."""
	# Extras callback for tool-specific flags
	def add_audit_extras(parser: object) -> None:
		# No additional protocol-audit-specific flags
		pass

	parser = toolkit_cli.build_parser(
		prog='protocol_audit',
		description='Audit protocol steps for completeness and consistency.',
		extras=add_audit_extras
	)

	# Parse and return
	args = parser.parse_args()

	# Set default protocol name if none specified
	if not args.protocols:
		args.protocols = ['cell_culture']

	return args


def main() -> object:
	args = parse_args()
	repo_root = get_repo_root()

	# Handle --list
	if args.list_only:
		protocols = discover_protocols(repo_root)
		for p in protocols:
			print(p)
		return 0

	# Load protocol (first one from args.protocols list)
	protocol_name = args.protocols[0]
	protocol_dir = repo_root / 'content' / 'protocols' / protocol_name
	if not protocol_dir.is_dir():
		print(f"Error: Protocol directory not found: {protocol_dir}", file=sys.stderr)
		return 1

	protocol_path = protocol_dir / 'protocol.yaml'

	if not protocol_path.exists():
		print(f"Error: Missing file: {protocol_path}", file=sys.stderr)
		return 1

	# NOTE: This script was designed for the old items.yaml/reagents.yaml schema
	# which no longer exists in the current repo. The current schema uses
	# protocol.yaml with steps. This is a placeholder that acknowledges
	# the protocol exists but cannot audit it with the old schema.
	print('=' * 80)
	print(f'PROTOCOL AUDIT: {protocol_name}')
	print('=' * 80)
	print(f"Protocol found at {protocol_path}")
	print("Note: audit functionality currently requires legacy items.yaml/reagents.yaml schema")
	print(f"Current repo uses protocol.yaml schema. Consider running: validation/yaml/validate.py -p {protocol_name}")
	print('=' * 80)

	return 0


if __name__ == '__main__':
	sys.exit(main())
