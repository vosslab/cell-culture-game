#!/usr/bin/env python3
"""
Protocol folder layout structure validation.

Enforces the three-cluster grouping (cell_culture, sdspage, runners) with
strict depth, naming, and ownership rules. See docs/specs/TARGET_FILE_STRUCTURE.md
for the canonical rule definitions.

This validator implements the eight layout rules as reusable helper functions
that return Finding objects, and provides a CLI entry point compatible with
validation/validate.py integration.

Standalone tool. Not a pytest. Not imported by build pipeline or src/.
"""

import sys
from pathlib import Path

import yaml

import validation.shared_toolkit.cli
import validation.shared_toolkit.console
import validation.shared_toolkit.emit
import validation.shared_toolkit.repo_root
import validation.shared_toolkit.verbosity
from validation.shared_toolkit.findings import Finding, Severity


def load_protocol_data(protocols_dir: Path) -> dict:
	"""
	Load all protocol.yaml files in content/protocols/.

	Returns: dict mapping path_str -> parsed_yaml_dict
	"""
	data = {}
	if protocols_dir.is_dir():
		for protocol_yaml in protocols_dir.rglob("protocol.yaml"):
			with open(protocol_yaml, 'r') as f:
				content = yaml.safe_load(f)
				data[str(protocol_yaml)] = content
	return data


#============================================
# Rule 1: Closed cluster set
#============================================

def check_cluster_set_closed(protocols_dir: Path) -> list[Finding]:
	"""
	Rule 1: Only three top-level subdirectories permitted under content/protocols/.
	The set is closed: cell_culture, sdspage, runners.

	Returns list of Finding objects; empty list on pass.
	"""
	findings = []
	allowed_clusters = {"cell_culture", "sdspage", "runners"}

	if protocols_dir.is_dir():
		top_level_dirs = {
			d.name for d in protocols_dir.iterdir()
			if d.is_dir() and not d.name.startswith('.')
		}

		bad_clusters = top_level_dirs - allowed_clusters
		if bad_clusters:
			for cluster_name in sorted(bad_clusters):
				findings.append(Finding(
					severity=Severity.ERROR,
					tool='layout_check',
					code='cluster_not_allowed',
					message=f"Invalid top-level cluster '{cluster_name}' under content/protocols/. "
						f"Only {sorted(allowed_clusters)} are permitted.",
					path=f"content/protocols/{cluster_name}",
				))

	return findings


#============================================
# Rule 2: Relative depth shape
#============================================

def check_relative_depth_shape(protocols_dir: Path) -> list[Finding]:
	"""
	Rule 2: Every protocol.yaml lives at exactly two path segments below content/protocols/.
	Shape: <cluster>/<name>/protocol.yaml. Depth is relative to content/protocols/, not repo root.

	Returns list of Finding objects; empty list on pass.
	"""
	findings = []

	if protocols_dir.is_dir():
		for protocol_yaml in protocols_dir.rglob("protocol.yaml"):
			try:
				rel_path = protocol_yaml.relative_to(protocols_dir)
			except ValueError:
				findings.append(Finding(
					severity=Severity.ERROR,
					tool='layout_check',
					code='depth_invalid',
					message=f"Protocol.yaml not under {protocols_dir}",
					path=str(protocol_yaml),
				))
				continue

			# rel_path.parts should be exactly 3: cluster, name, 'protocol.yaml'
			if len(rel_path.parts) != 3 or rel_path.parts[2] != "protocol.yaml":
				findings.append(Finding(
					severity=Severity.ERROR,
					tool='layout_check',
					code='depth_incorrect',
					message=f"Protocol.yaml at incorrect depth '{rel_path}'; "
						f"expected <cluster>/<name>/protocol.yaml",
					path=str(rel_path),
				))

	return findings


#============================================
# Rule 3: Exactly one protocol.yaml per leaf
#============================================

def check_exactly_one_protocol_yaml_per_leaf(protocols_dir: Path) -> list[Finding]:
	"""
	Rule 3: Each <cluster>/<name>/ directory contains exactly one protocol.yaml.
	Duplicates (copies, backups, stray files) fail the test.

	Returns list of Finding objects; empty list on pass.
	"""
	findings = []

	if protocols_dir.is_dir():
		for cluster_dir in protocols_dir.iterdir():
			if not cluster_dir.is_dir() or cluster_dir.name.startswith('.'):
				continue

			for leaf_dir in cluster_dir.iterdir():
				if not leaf_dir.is_dir() or leaf_dir.name.startswith('.'):
					continue

				# Count protocol.yaml files in this leaf
				protocol_yamls = list(leaf_dir.glob("protocol.yaml"))
				if len(protocol_yamls) != 1:
					rel_path = str(leaf_dir.relative_to(protocols_dir))
					findings.append(Finding(
						severity=Severity.ERROR,
						tool='layout_check',
						code='protocol_yaml_count_incorrect',
						message=f"Leaf directory {rel_path} contains {len(protocol_yamls)} "
							f"protocol.yaml file(s); expected 1",
						path=f"content/protocols/{rel_path}",
					))

	return findings


#============================================
# Rule 4: Type matches cluster
#============================================

def check_type_matches_cluster(protocols_dir: Path, protocol_data: dict) -> list[Finding]:
	"""
	Rule 4: protocol_type must match the cluster.
	- cell_culture/<name>/protocol.yaml: protocol_type: mini_protocol
	- sdspage/<name>/protocol.yaml: protocol_type: mini_protocol
	- runners/<name>/protocol.yaml: protocol_type: sequence_runner

	Returns list of Finding objects; empty list on pass.
	"""
	findings = []

	type_map = {
		"cell_culture": "mini_protocol",
		"sdspage": "mini_protocol",
		"runners": "sequence_runner",
	}

	if protocols_dir.is_dir():
		for protocol_yaml in protocols_dir.rglob("protocol.yaml"):
			rel_path = protocol_yaml.relative_to(protocols_dir)
			cluster = rel_path.parts[0]

			# Skip invalid clusters (caught by check_cluster_set_closed)
			if cluster not in type_map:
				continue

			protocol_dict = protocol_data.get(str(protocol_yaml), {})
			actual_type = protocol_dict.get("protocol_type", "<missing>")
			expected_type = type_map[cluster]

			if actual_type != expected_type:
				findings.append(Finding(
					severity=Severity.ERROR,
					tool='layout_check',
					code='type_mismatch_cluster',
					message=f"Protocol in cluster '{cluster}' has type '{actual_type}'; "
						f"expected '{expected_type}'",
					path=str(rel_path),
				))

	return findings


#============================================
# Rule 5: Folder name equals protocol_name
#============================================

def check_folder_name_equals_protocol_name(protocols_dir: Path, protocol_data: dict) -> list[Finding]:
	"""
	Rule 5: The leaf folder basename must equal the protocol_name field inside protocol.yaml.
	This prevents identity drift (folder 'foo' carrying protocol_name: 'bar').

	Returns list of Finding objects; empty list on pass.
	"""
	findings = []

	if protocols_dir.is_dir():
		for protocol_yaml in protocols_dir.rglob("protocol.yaml"):
			rel_path = protocol_yaml.relative_to(protocols_dir)
			folder_name = rel_path.parts[1]

			protocol_dict = protocol_data.get(str(protocol_yaml), {})
			protocol_name = protocol_dict.get("protocol_name", "<missing>")

			if folder_name != protocol_name:
				findings.append(Finding(
					severity=Severity.ERROR,
					tool='layout_check',
					code='folder_protocol_name_mismatch',
					message=f"Folder '{folder_name}' does not match protocol_name '{protocol_name}'",
					path=str(rel_path),
				))

	return findings


#============================================
# Rule 6: Unique protocol_name
#============================================

def check_protocol_name_unique(protocols_dir: Path, protocol_data: dict) -> list[Finding]:
	"""
	Rule 6: Every protocol_name is unique across the whole content/protocols/ tree.
	A duplicate fails with both offending paths.

	Returns list of Finding objects; empty list on pass.
	"""
	findings = []

	name_to_paths = {}  # protocol_name -> list of paths
	if protocols_dir.is_dir():
		for protocol_yaml in protocols_dir.rglob("protocol.yaml"):
			protocol_dict = protocol_data.get(str(protocol_yaml), {})
			protocol_name = protocol_dict.get("protocol_name", "<missing>")

			rel_path = str(protocol_yaml.relative_to(protocols_dir))
			if protocol_name not in name_to_paths:
				name_to_paths[protocol_name] = []
			name_to_paths[protocol_name].append(rel_path)

	duplicates = {
		name: paths for name, paths in name_to_paths.items()
		if len(paths) > 1
	}

	if duplicates:
		for name in sorted(duplicates.keys()):
			paths = duplicates[name]
			for path in sorted(paths):
				findings.append(Finding(
					severity=Severity.ERROR,
					tool='layout_check',
					code='protocol_name_duplicate',
					message=f"Duplicate protocol_name '{name}' also appears in {len(paths) - 1} other location(s)",
					path=path,
				))

	return findings


#============================================
# Rule 7: Sidecar ownership
#============================================

def check_sidecar_ownership(protocols_dir: Path) -> list[Finding]:
	"""
	Rule 7: Every materials.yaml and scenes/ directory is a sibling of exactly one protocol.yaml.
	No nested scene sub-directories (scenes/<scene>.yaml only, not scenes/<sub>/<scene>.yaml).

	Returns list of Finding objects; empty list on pass.
	"""
	findings = []

	if protocols_dir.is_dir():
		# Check materials.yaml files
		for materials_yaml in protocols_dir.rglob("materials.yaml"):
			rel_path = materials_yaml.relative_to(protocols_dir)

			# materials.yaml must be in a leaf directory that also has protocol.yaml
			parent_dir = materials_yaml.parent
			sibling_protocol = parent_dir / "protocol.yaml"

			if not sibling_protocol.exists():
				findings.append(Finding(
					severity=Severity.ERROR,
					tool='layout_check',
					code='sidecar_no_protocol_sibling',
					message="materials.yaml has no sibling protocol.yaml",
					path=str(rel_path),
				))

		# Check scenes/ directories
		for scenes_dir in protocols_dir.rglob("scenes"):
			if not scenes_dir.is_dir():
				continue

			rel_path = scenes_dir.relative_to(protocols_dir)

			# scenes/ must be in a leaf directory that also has protocol.yaml
			parent_dir = scenes_dir.parent
			sibling_protocol = parent_dir / "protocol.yaml"

			if not sibling_protocol.exists():
				findings.append(Finding(
					severity=Severity.ERROR,
					tool='layout_check',
					code='sidecar_no_protocol_sibling',
					message="scenes/ directory has no sibling protocol.yaml",
					path=str(rel_path),
				))

			# Check for nested sub-directories inside scenes/
			for item in scenes_dir.iterdir():
				if item.is_dir() and not item.name.startswith('.'):
					findings.append(Finding(
						severity=Severity.ERROR,
						tool='layout_check',
						code='scene_nested_subdirectory',
						message="Nested subdirectory in scenes/; only direct children (scenes/<scene>.yaml) allowed",
						path=f"{str(rel_path)}/{item.name}",
					))

	return findings


#============================================
# Rule 8: Discovery round-trip
#============================================

def check_discovery_round_trip(protocols_dir: Path) -> list[Finding]:
	"""
	Rule 8: Verify that discovered protocol names match the filesystem folder names
	under content/protocols/. This closes the loop between filesystem layout and runtime
	identity by walking the actual filesystem structure under the three-cluster system.

	Returns list of Finding objects; empty list on pass.
	"""
	findings = []

	# Discover via filesystem walk of content/protocols/
	filesystem_names = set()
	if protocols_dir.is_dir():
		for protocol_yaml in protocols_dir.rglob("protocol.yaml"):
			rel_path = protocol_yaml.relative_to(protocols_dir)
			# Extract the folder name (cluster/name)
			folder_name = rel_path.parts[1]
			filesystem_names.add(folder_name)

	# Verify we have some protocols (basic sanity check)
	if not filesystem_names:
		findings.append(Finding(
			severity=Severity.ERROR,
			tool='layout_check',
			code='no_protocols_discovered',
			message="No protocols discovered under content/protocols/; expected at least one",
			path="content/protocols",
		))

	return findings


#============================================
# Main aggregation and CLI
#============================================

def run_all_checks(repo_root: Path) -> list[Finding]:
	"""
	Run all eight layout checks and return combined findings list.
	"""
	protocols_dir = repo_root / "content" / "protocols"
	protocol_data = load_protocol_data(protocols_dir)

	all_findings = []

	# Run all eight checks
	all_findings.extend(check_cluster_set_closed(protocols_dir))
	all_findings.extend(check_relative_depth_shape(protocols_dir))
	all_findings.extend(check_exactly_one_protocol_yaml_per_leaf(protocols_dir))
	all_findings.extend(check_type_matches_cluster(protocols_dir, protocol_data))
	all_findings.extend(check_folder_name_equals_protocol_name(protocols_dir, protocol_data))
	all_findings.extend(check_protocol_name_unique(protocols_dir, protocol_data))
	all_findings.extend(check_sidecar_ownership(protocols_dir))
	all_findings.extend(check_discovery_round_trip(protocols_dir))

	return all_findings


def parse_args() -> object:
	"""Build argparse parser with unified flags for structure validation."""
	parser = validation.shared_toolkit.cli.build_parser(
		prog='layout_check',
		description='Validate protocol folder layout structure.',
	)
	return parser.parse_args()


def main() -> int:
	"""
	Main entry point for layout_check validator.

	Verbosity contract (text output line targets):
	  -q / --quiet   : 1 line (final pass/fail with key numbers)
	  default        : 5-40 lines (summary per rule or cluster)
	  -v / --verbose : 40-<200 lines (per-protocol breakdown)
	  -j / --json    : full machine-readable detail (no bound)
	  -J / --ndjson  : streamed full detail (no bound)
	"""
	args = parse_args()
	repo_root = validation.shared_toolkit.repo_root.REPO_ROOT

	# Run all checks
	findings = run_all_checks(repo_root)

	# Separate errors (warnings not currently emitted by any rule;
	# add a warnings filter here if a rule grows that severity).
	errors = [f for f in findings if f.severity == Severity.ERROR]

	# Count protocol folders
	protocols_dir = repo_root / "content" / "protocols"
	protocol_count = 0
	if protocols_dir.is_dir():
		for protocol_yaml in protocols_dir.rglob("protocol.yaml"):
			protocol_count += 1

	# Render output based on format
	if args.output_format in ('json', 'ndjson'):
		validation.shared_toolkit.emit.emit_findings(findings, output_format=args.output_format)
	else:
		# Text format (default)
		console = validation.shared_toolkit.console.make_console(no_color=args.no_color)

		# Resolve verbosity level once; renderers switch on the enum.
		level = validation.shared_toolkit.verbosity.resolve_level(
			quiet=args.quiet, verbose=args.verbose
		)
		# Build the canonical summary line via the shared formatter.
		summary = validation.shared_toolkit.verbosity.summary_line(
			protocol_count, len(errors), item_label="protocol folders"
		)

		if level == validation.shared_toolkit.verbosity.VerbosityLevel.QUIET:
			# Quiet mode: exactly one canonical summary line.
			console.print(summary)

		elif level == validation.shared_toolkit.verbosity.VerbosityLevel.NORMAL:
			# Default mode: totals + top failures.
			if errors:
				console.print("[bold red]Layout Failures:[/bold red]")
				for err in errors[:10]:
					console.print(f"  {err.code}: {err.message} ({err.path})")
				if len(errors) > 10:
					console.print(f"  ... and {len(errors) - 10} more")
				console.print()
			# Summary line styled by pass/fail.
			if len(errors) == 0:
				console.print(f"[bold green]{summary}[/bold green]")
			else:
				console.print(f"[bold red]{summary}[/bold red]")

		else:
			# Verbose mode: summary + diagnostic block (top_codes by rule/error code).
			if len(errors) == 0:
				console.print(f"[bold green]{summary}[/bold green]")
			else:
				console.print(f"[bold red]{summary}[/bold red]")

			# Build code->count breakdown from layout failures.
			code_counts: dict = {}
			for err in errors:
				code_counts[err.code] = code_counts.get(err.code, 0) + 1
			top_codes = list(code_counts.items())

			diag = validation.shared_toolkit.verbosity.DiagnosticData(top_codes=top_codes)
			block = validation.shared_toolkit.verbosity.diagnostic_summary(diag)
			console.print(block)

	# Return exit code
	return 0 if len(errors) == 0 else 1


if __name__ == '__main__':
	sys.exit(main())
