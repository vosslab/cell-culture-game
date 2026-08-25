#!/usr/bin/env python3
"""SVG asset audit tool.

Walks all object YAML files, identifies asset_name references in visual_states,
and cross-walks with recursively registered equipment SVGs and SOURCES.md to
classify each asset and detect orphans. Reports enriched per-asset metadata:
Servier provenance, modification status, attribution, normalization, forbidden
constructs, file size, subpart coverage, enum case coverage, and reuse counts.

Usage:
	python3 validation/svg/asset_audit.py
	python3 validation/svg/asset_audit.py --object gel_cassette
	python3 validation/svg/asset_audit.py --json
"""

import os
import sys
from pathlib import Path

import yaml

import validation.shared_toolkit.paths as toolkit_paths
import validation.shared_toolkit.interactive as toolkit_interactive
import validation.shared_toolkit.reporter as reporter
import validation.shared_toolkit.cli as toolkit_cli
import validation.shared_toolkit.verbosity as verbosity
import validation.svg.asset_inspection

#============================================
# setup
#============================================

OBJECTS_DIR = toolkit_paths.OBJECTS_DIR


def extract_asset_names_recursive(obj: object) -> set[str]:
	"""Recursively extract all asset_name values from a YAML object.

	Handles nested dicts and lists. Looks for dict keys named 'asset_name'.
	"""
	assets = set()

	if isinstance(obj, dict):
		for key, value in obj.items():
			if key == 'asset_name' and isinstance(value, str):
				assets.add(value)
			else:
				assets.update(extract_asset_names_recursive(value))
	elif isinstance(obj, list):
		for item in obj:
			assets.update(extract_asset_names_recursive(item))

	return assets

def load_object_yaml(path: str) -> tuple[str, str, set[str], dict[str, object]]:
	"""Load an object YAML file and extract object_name, label, asset_names, and full data.

	Returns: (object_name, label, asset_names_set, data)
	Raises: exception if file cannot be parsed or required fields are missing.
	"""
	with open(path, 'r', encoding='utf-8') as f:
		data = yaml.safe_load(f)

	if data is None:
		data = {}

	object_name = data.get('object_name', 'UNKNOWN')
	label = data.get('label', 'UNKNOWN')

	# Extract asset_names from the entire YAML
	assets = extract_asset_names_recursive(data)

	return object_name, label, assets, data

#============================================
# classification
#============================================

def classify_asset(
	asset_name: str,
	disk_svgs: set[str],
	servier: set[str]
) -> str:
	"""Classify the source of an asset_name.

	Returns one of: 'servier', 'other', 'missing'.
	"""
	if asset_name not in disk_svgs:
		return 'missing'

	if asset_name in servier:
		return 'servier'

	return 'other'

#============================================
# audit logic
#============================================

def audit_repo(
	disk_svgs: set[str],
	servier: set[str],
	servier_sources: dict[str, tuple[str, str]]
) -> tuple[dict[str, dict[str, object]], list[str], set[str], dict[str, int], dict[str, object]]:
	"""Audit all objects and return per-object data, missing items, orphans, and metadata.

	Returns: (objects_dict, missing_items, orphan_svgs, asset_reuse_count, per_asset_metadata)

	objects_dict: { object_name: {
		'label': str,
		'assets': { asset_name: classification },
		'sources': set of classifications present,
		'yaml_data': full YAML dict for enum/structure checks
	}}

	missing_items: list of "(object_name, asset_name)" strings for missing files

	orphan_svgs: set of svg basenames found on disk but not referenced by any object

	asset_reuse_count: { asset_name: count }

	per_asset_metadata: { asset_name: { all rich metadata } }
	"""
	objects = {}
	referenced_svgs = set()
	missing_items = []
	asset_reuse = {}
	per_asset_metadata = {}

	if not os.path.isdir(OBJECTS_DIR):
		orphan_svgs = disk_svgs - referenced_svgs
		return objects, missing_items, orphan_svgs, asset_reuse, per_asset_metadata

	# Walk every .yaml file in content/objects/ recursively
	for path in sorted(Path(OBJECTS_DIR).rglob('*.yaml')):
		try:
			object_name, label, asset_names, yaml_data = load_object_yaml(str(path))
		except Exception as e:
			# Broad catch to keep audit running across malformed YAML; logs error.
			print(f"WARN: failed to parse {path}: {e}", file=sys.stderr)
			continue

		# Skip objects with no visual_states (no SVG references)
		if not asset_names:
			continue

		# Classify each asset and collect data
		assets_dict = {}
		sources_set = set()

		for asset_name in sorted(asset_names):
			classification = classify_asset(asset_name, disk_svgs, servier)
			assets_dict[asset_name] = classification
			sources_set.add(classification)

			# Track referenced SVGs and missing items
			if classification != 'missing':
				referenced_svgs.add(asset_name)
				asset_reuse[asset_name] = asset_reuse.get(asset_name, 0) + 1
			else:
				missing_items.append(f"{object_name} -> {asset_name}")

		objects[object_name] = {
			'label': label,
			'assets': assets_dict,
			'sources': sources_set,
			'yaml_data': yaml_data
		}

	# Build per-asset metadata for all referenced SVGs
	for asset_name in sorted(referenced_svgs):
		meta = build_asset_metadata(asset_name, servier, servier_sources)
		per_asset_metadata[asset_name] = meta

	# Find orphan SVGs: on disk but not referenced
	orphan_svgs = disk_svgs - referenced_svgs

	return objects, missing_items, orphan_svgs, asset_reuse, per_asset_metadata

def build_asset_metadata(
	asset_name: str,
	servier: set[str],
	servier_sources: dict[str, tuple[str, str]]
) -> dict[str, object]:
	"""Build rich metadata for one asset."""
	meta = {
		'asset_name': asset_name,
	}

	# Servier source and category
	if asset_name in servier_sources:
		source_path, category = servier_sources[asset_name]
		meta['servier_source_path'] = source_path
		meta['bioicons_category'] = category
	else:
		meta['servier_source_path'] = None
		meta['bioicons_category'] = None

	# Modification status
	if asset_name in servier:
		mod_status = validation.svg.asset_inspection.check_modification_status(asset_name, servier_sources)
		meta['modification_status'] = mod_status
	else:
		meta['modification_status'] = None

	# Attribution
	if asset_name in servier:
		attr = validation.svg.asset_inspection.check_attribution(asset_name, servier, servier_sources)
		meta['attribution'] = attr
	else:
		meta['attribution'] = None

	# Normalization
	norm_status, norm_reason = validation.svg.asset_inspection.check_normalization(asset_name)
	meta['normalization'] = norm_status
	meta['normalization_reason'] = norm_reason

	# Forbidden constructs
	forbidden = validation.svg.asset_inspection.check_forbidden_constructs(asset_name)
	meta['forbidden_constructs'] = forbidden

	# File size
	size_kb = validation.svg.asset_inspection.get_file_size_kb(asset_name)
	meta['file_size_kb'] = size_kb

	# Subpart IDs
	subpart_ids = validation.svg.asset_inspection.extract_subpart_ids(asset_name)
	meta['subpart_ids'] = sorted(subpart_ids)

	return meta

#============================================
# reporting
#============================================

def print_full_report(
	objects: dict[str, dict[str, object]],
	missing_items: list[str],
	orphan_svgs: set[str],
	disk_svgs: set[str],
	asset_reuse: dict[str, int],
	per_asset_metadata: dict[str, object],
	quiet: bool = False,
	verbose: bool = False
) -> int:
	"""Print the full audit report with enriched metadata.

	Three-tier verbosity:
	-q (quiet): ONLY the final summary line.
	default: section headers + count tables + actionable findings totals + summary line.
	-v (verbose): full per-asset detail INCLUDING raw item lists.
	"""

	# Count breakdown by source
	servier_objs = 0
	other_objs = 0
	mixed_objs = 0
	missing_objs = 0

	servier_assets = 0
	other_assets = 0
	missing_assets = 0

	for obj_data in objects.values():
		sources = obj_data['sources']

		# Object-level classification
		if 'missing' in sources:
			missing_objs += 1
		elif len(sources) > 1:
			mixed_objs += 1
		elif 'servier' in sources:
			servier_objs += 1
		elif 'other' in sources:
			other_objs += 1

		# Asset-level counts
		for asset_name, classification in obj_data['assets'].items():
			if classification == 'servier':
				servier_assets += 1
			elif classification == 'other':
				other_assets += 1
			elif classification == 'missing':
				missing_assets += 1

	# Compute counts for actionable findings (computed early, needed by all modes).
	# check_normalization returns status 'normalized' or 'failed' (NOT 'OK'); a
	# non-normalized asset is anything that did not come back 'normalized'.
	# Split by reason: a parse/XML failure is a blocking error (malformed SVG);
	# every other normalization miss is a non-normalized warning.
	MALFORMED_REASONS = ('xml_parse_error', 'parse_exception')
	malformed_count = 0
	non_normalized_count = 0
	for m in per_asset_metadata.values():
		if m.get('normalization') == 'normalized':
			continue
		if m.get('normalization_reason') in MALFORMED_REASONS:
			malformed_count += 1
		else:
			non_normalized_count += 1
	normalization_failures = malformed_count + non_normalized_count
	forbidden_construct_count = sum(
		1 for m in per_asset_metadata.values()
		if m.get('forbidden_constructs')
	)
	unattributed_servier = sum(
		1 for m in per_asset_metadata.values()
		if m.get('servier_source_path') and not m.get('attribution')
	)

	# Resolve verbosity level once via the shared helper.
	level = verbosity.resolve_level(quiet=quiet, verbose=verbose)

	# Compute totals needed by all modes, split into the three severity tiers.
	#   error    = malformed SVG (unparseable) + forbidden constructs
	#   warning  = non-normalized SVG + unattributed Servier adoptions
	#   advisory = orphan SVGs (cleanup, do not block)
	total_checked = len(objects)
	error_count = malformed_count + forbidden_construct_count
	warning_count = non_normalized_count + unattributed_servier
	advisory_count = len(orphan_svgs)

	# QUIET mode: exactly one canonical summary line.
	if level == verbosity.VerbosityLevel.QUIET:
		reporter.print_summary_line(
			total_checked, error_count, item_label="objects",
			warnings=warning_count, advisories=advisory_count,
		)
		return error_count

	# NORMAL and VERBOSE: section header + per-object source breakdown + actionable findings
	print(f"=== SVG asset audit ({len(objects)} objects / {len(disk_svgs)} SVGs) ===")
	print()

	# Per-object source breakdown table (always shown in NORMAL and VERBOSE).
	print("Per-object source breakdown:")
	print(f"  servier:     {servier_objs} objects, {servier_assets} svgs")
	print(f"  other:       {other_objs} objects, {other_assets} svgs")
	print(f"  mixed:       {mixed_objs} objects (uses Servier and other-source art)")
	print(f"  missing:     {missing_objs} objects (one or more asset_name has no .svg)")
	print()

	# Cleanup surface section: counts always shown; item listings only in VERBOSE.
	is_verbose = (level == verbosity.VerbosityLevel.VERBOSE)
	print_cleanup_surface_section(orphan_svgs, verbose=is_verbose)
	print()

	# Actionable findings summary (NORMAL and VERBOSE).
	print("Actionable findings:")
	print(f"  Orphan SVG files: {len(orphan_svgs)}")
	print(f"  Normalization failures: {normalization_failures}")
	print(f"  Forbidden constructs: {forbidden_construct_count}")
	print(f"  Unattributed Servier adoptions: {unattributed_servier}")
	print()

	# Final summary line (NORMAL and VERBOSE).
	reporter.print_summary_line(
		total_checked, error_count, item_label="objects",
		warnings=warning_count, advisories=advisory_count,
	)

	# VERBOSE: append the shared diagnostic summary block.
	if level == verbosity.VerbosityLevel.VERBOSE:
		# Build top_offenders: objects ranked by subpart mismatch count.
		mismatch_counts = {}
		for obj_name in objects.keys():
			obj_data = objects[obj_name]
			yaml_data = obj_data.get('yaml_data', {})
			expected_subparts = validation.svg.asset_inspection.get_expected_subparts(obj_name, yaml_data)
			if expected_subparts:
				for asset_name in obj_data['assets'].keys():
					if asset_name in per_asset_metadata:
						meta = per_asset_metadata[asset_name]
						svg_subparts = set(meta.get('subpart_ids', []))
						missing_sp = expected_subparts - svg_subparts
						extra_sp = svg_subparts - expected_subparts
						mismatch_count = len(missing_sp) + len(extra_sp)
						if mismatch_count > 0:
							if obj_name not in mismatch_counts:
								mismatch_counts[obj_name] = 0
							mismatch_counts[obj_name] += mismatch_count
		top_offenders_list = list(mismatch_counts.items())

		# Build category_counts: asset classification breakdown.
		category_counts_list = [
			("servier", servier_assets),
			("other", other_assets),
			("missing", missing_assets),
		]

		diag_data = verbosity.DiagnosticData(
			top_offenders=top_offenders_list,
			category_counts=category_counts_list,
		)
		print()
		print(verbosity.diagnostic_summary(diag_data))

	return error_count

def print_provenance_section(per_asset_metadata: dict[str, object], asset_filter: set[str] | None = None) -> None:
	"""Print provenance section: source, license, attribution, modification status.

	Verbose-only: per-asset detail walk. Default mode has no output from this section.
	"""
	print("=== Provenance ===")
	if not per_asset_metadata:
		print("(no assets)")
		return

	for asset_name in sorted(per_asset_metadata.keys()):
		if asset_filter and asset_name not in asset_filter:
			continue
		meta = per_asset_metadata[asset_name]
		print(f"{asset_name}:")
		if meta.get('servier_source_path'):
			print(f"  Source: {meta['servier_source_path']}")
			print("  License: CC BY 3.0")
		else:
			print("  Source: (not a Servier asset)")
		attr = meta.get('attribution') or 'unknown'
		print(f"  Attribution: {attr}")
		mod = meta.get('modification_status') or 'unknown'
		print(f"  Modification: {mod}")

def print_svg_health_section(per_asset_metadata: dict[str, object], asset_filter: set[str] | None = None) -> None:
	"""Print SVG health section: pipeline, viewBox, size, forbidden constructs, base64.

	Verbose-only: per-asset detail walk. Default mode has no output from this section.
	"""
	print("=== SVG health ===")
	if not per_asset_metadata:
		print("(no assets)")
		return

	for asset_name in sorted(per_asset_metadata.keys()):
		if asset_filter and asset_name not in asset_filter:
			continue
		meta = per_asset_metadata[asset_name]
		print(f"{asset_name}:")
		norm = meta.get('normalization', 'unknown')
		reason = meta.get('normalization_reason')
		if reason:
			print(f"  Normalization: {norm} ({reason})")
		else:
			print(f"  Normalization: {norm}")
		size = meta.get('file_size_kb')
		if size:
			flag_str = " [LARGE]" if size > 50 else ""
			print(f"  File size: {size:.1f} KB{flag_str}")
		forbidden = meta.get('forbidden_constructs', [])
		if forbidden:
			print(f"  Forbidden constructs: {', '.join(forbidden)}")

def print_object_alignment_section(objects: dict[str, dict[str, object]], asset_reuse: dict[str, int], object_filter: str | None = None) -> None:
	"""Print object alignment section: refs, coverage.

	Verbose-only: per-asset detail walk. Default mode has no output from this section.
	"""
	print("=== Object alignment ===")
	if not objects:
		print("(no objects)")
		return

	for obj_name in sorted(objects.keys()):
		if object_filter and obj_name != object_filter:
			continue
		obj_data = objects[obj_name]
		assets = obj_data['assets']

		if not assets:
			continue

		print(f"{obj_name}:")
		for asset_name in sorted(assets.keys()):
			classification = assets[asset_name]
			reuse = asset_reuse.get(asset_name, 0)
			print(f"  {asset_name}: {classification} (used {reuse}x)")

		# Enum coverage
		coverage = validation.svg.asset_inspection.check_enum_coverage(obj_name, obj_data.get('yaml_data', {}))
		if coverage:
			print("  Enum coverage:")
			for field, (covered, total, missing) in sorted(coverage.items()):
				if missing:
					print(f"    {field}: {covered}/{total} [missing: {', '.join(missing)}]")
				else:
					print(f"    {field}: {covered}/{total}")

def print_subpart_alignment_section(objects: dict[str, dict[str, object]], per_asset_metadata: dict[str, object], object_filter: str | None = None) -> None:
	"""Print subpart alignment section.

	Verbose-only: per-asset detail walk. Default mode has no output from this section.
	"""
	print("=== Subpart alignment ===")
	any_printed = False

	for obj_name in sorted(objects.keys()):
		if object_filter and obj_name != object_filter:
			continue

		obj_data = objects[obj_name]
		yaml_data = obj_data.get('yaml_data', {})
		expected_subparts = validation.svg.asset_inspection.get_expected_subparts(obj_name, yaml_data)

		if not expected_subparts:
			continue

		any_printed = True
		print(f"{obj_name}:")
		print(f"  Expected subparts: {len(expected_subparts)}")

		for asset_name in sorted(obj_data['assets'].keys()):
			if asset_name not in per_asset_metadata:
				continue
			meta = per_asset_metadata[asset_name]
			svg_subparts = set(meta.get('subpart_ids', []))

			missing = expected_subparts - svg_subparts
			extra = svg_subparts - expected_subparts

			if missing or extra:
				print(f"  {asset_name}:")
				if missing:
					print(f"    Missing in SVG: {', '.join(sorted(missing))}")
				if extra:
					print(f"    Extra in SVG: {', '.join(sorted(extra))}")

	if not any_printed:
		print("(no structured objects)")

def print_cleanup_surface_section(orphan_svgs: set[str], verbose: bool = False) -> None:
	"""Print cleanup surface section for unreferenced retained SVGs.

	default mode: print section header and counts only, no item listings.
	verbose mode: print section header, counts, AND raw item listings.
	"""
	print("=== Cleanup surface ===")

	if orphan_svgs:
		print(f"Orphan SVGs ({len(orphan_svgs)}):")
		if verbose:
			for svg in sorted(orphan_svgs):
				print(f"  {svg}")
	else:
		print("Orphan SVGs: (none)")

#============================================
# cli
#============================================

def parse_args() -> object:
	"""Parse command-line arguments."""
	#============================================
	# extras callback registers SVG audit-specific flags
	#============================================
	def register_svg_audit_flags(parser: object) -> None:
		selection_group = parser.add_argument_group('SVG Audit')
		selection_group.add_argument(
			'--list-objects',
			dest='list_objects_flag',
			action='store_true',
			help='List available object names (one per line) and exit.'
		)

	parser = toolkit_cli.build_parser(
		prog='audit',
		description='SVG asset audit: walk objects and cross-walk with recursive equipment SVGs.',
		extras=register_svg_audit_flags
	)

	args = parser.parse_args()

	#============================================
	# Map shared CLI args to asset_audit expectations.
	# Shared CLI uses --object/--asset (dest='objects', nargs='+').
	# Asset audit expects --object to filter to ONE object (object_name).
	# Extract first object if provided; otherwise None.
	#============================================
	object_name = None
	if args.objects and len(args.objects) > 0:
		object_name = args.objects[0]
	args.object_name = object_name

	return args

def main() -> None:
	"""SVG asset audit: classify, inspect, and cross-validate assets.

	Verbosity contract (text output line targets):
	  -q / --quiet   : 1 line (final pass/fail with key numbers)
	  default        : 5-40 lines (stage summary, totals, top categories)
	  -v / --verbose : 40-<200 lines (per-content-file breakdown, grouped, summarized)
	  -j / --json    : full machine-readable detail (no bound)
	  -J / --ndjson  : streamed full detail (no bound)
	Raw per-step / per-asset internals go to JSON only, NOT text.
	"""
	args = parse_args()

	# Load the provenance ledger and discover assets.
	disk_svgs = validation.svg.asset_inspection.list_disk_svgs()
	servier_sources = validation.svg.asset_inspection.parse_servier_sources()
	servier = set(servier_sources)

	# Run the audit
	objects, missing_items, orphan_svgs, asset_reuse, per_asset_metadata = audit_repo(
		disk_svgs, servier, servier_sources
	)

	# --list-objects: print sorted list of object names and exit
	if args.list_objects_flag:
		for obj_name in sorted(objects.keys()):
			print(obj_name)
		return

	# --interactive: pick one object from numbered menu
	if args.interactive:
		object_names = sorted(objects.keys())
		selected = toolkit_interactive.pick_protocol_interactively(
			object_names,
			prompt="Select an object (number): ",
			intro="Available objects:"
		)
		if selected is None:
			sys.exit(1)
		args.object_name = selected

	# Route to output format (map 'text' from shared CLI to 'table' for this tool)
	output_format = args.output_format if args.output_format != 'text' else 'table'

	if output_format == 'json':
		print_json_report(args.object_name, objects, disk_svgs, asset_reuse, per_asset_metadata, orphan_svgs)
	else:
		# Table format
		if args.object_name:
			if args.object_name not in objects:
				reporter.print_error(f"Object '{args.object_name}' not found.")
				sys.exit(1)
			# Per-object mode always prints per-asset detail
			print_object_detail_table(args.object_name, objects, asset_reuse, per_asset_metadata, orphan_svgs)
		else:
			# Repo-wide mode: honor -q and -v. Exit is ERROR-only: warnings and
			# advisories (non-normalized, orphan) print but do not fail the run.
			error_count = print_full_report(
				objects, missing_items, orphan_svgs, disk_svgs, asset_reuse,
				per_asset_metadata, quiet=args.quiet, verbose=args.verbose
			)
			sys.exit(1 if error_count else 0)

def print_object_detail_table(
	object_name: str,
	objects: dict[str, dict[str, object]],
	asset_reuse: dict[str, int],
	per_asset_metadata: dict[str, object],
	orphan_svgs: set[str]
) -> None:
	"""Print detailed table report for one object.

	Per-object mode always prints per-asset detail regardless of -q/-v flag.
	"""
	print(f"Object: {object_name}")
	obj_data = objects[object_name]
	print(f"Label: {obj_data['label']}")
	print()

	# Filter to assets used in this object
	obj_assets = set(obj_data['assets'].keys())

	print_provenance_section(per_asset_metadata, obj_assets)
	print()

	print_svg_health_section(per_asset_metadata, obj_assets)
	print()

	print_object_alignment_section(objects, asset_reuse, object_name)
	print()

	print_subpart_alignment_section(objects, per_asset_metadata, object_name)
	print()

	print_cleanup_surface_section(orphan_svgs, verbose=True)

def print_json_report(
	object_name: str | None,
	objects: dict[str, dict[str, object]],
	disk_svgs: set[str],
	asset_reuse: dict[str, int],
	per_asset_metadata: dict[str, object],
	orphan_svgs: set[str]
) -> None:
	"""Print JSON report."""
	import json

	# Build summary
	summary = {
		'objects': len(objects),
		'svgs': len(disk_svgs),
		'servier_assets': sum(1 for m in per_asset_metadata.values() if m.get('servier_source_path')),
		'orphan_svgs': len(orphan_svgs),
	}

	# Build five sections
	provenance = []
	for asset_name in sorted(per_asset_metadata.keys()):
		meta = per_asset_metadata[asset_name]
		provenance.append({
			'asset': asset_name,
			'source': meta.get('servier_source_path'),
			'license': 'CC BY 3.0' if meta.get('servier_source_path') else None,
			'attribution': meta.get('attribution'),
			'modification_status': meta.get('modification_status'),
		})

	svg_health = []
	for asset_name in sorted(per_asset_metadata.keys()):
		meta = per_asset_metadata[asset_name]
		svg_health.append({
			'asset': asset_name,
			'normalization': meta.get('normalization'),
			'reason': meta.get('normalization_reason'),
			'file_size_kb': meta.get('file_size_kb'),
			'forbidden_constructs': meta.get('forbidden_constructs', []),
		})

	object_alignment = []
	for obj_name in sorted(objects.keys()):
		obj_data = objects[obj_name]
		for asset_name in sorted(obj_data['assets'].keys()):
			classification = obj_data['assets'][asset_name]
			object_alignment.append({
				'object': obj_name,
				'asset': asset_name,
				'classification': classification,
				'reuse_count': asset_reuse.get(asset_name, 0),
			})

	subpart_alignment = []
	for obj_name in sorted(objects.keys()):
		obj_data = objects[obj_name]
		yaml_data = obj_data.get('yaml_data', {})
		expected_subparts = validation.svg.asset_inspection.get_expected_subparts(obj_name, yaml_data)
		if expected_subparts:
			for asset_name in sorted(obj_data['assets'].keys()):
				if asset_name in per_asset_metadata:
					meta = per_asset_metadata[asset_name]
					svg_subparts = set(meta.get('subpart_ids', []))
					missing = expected_subparts - svg_subparts
					extra = svg_subparts - expected_subparts
					subpart_alignment.append({
						'object': obj_name,
						'asset': asset_name,
						'expected_subparts': sorted(expected_subparts),
						'svg_subparts': sorted(svg_subparts),
						'missing': sorted(missing),
						'extra': sorted(extra),
					})

	cleanup_surface = {
		'orphans': sorted(orphan_svgs),
	}

	# Build output
	output = {
		'summary': summary,
		'provenance': provenance,
		'svg_health': svg_health,
		'object_alignment': object_alignment,
		'subpart_alignment': subpart_alignment,
		'cleanup_surface': cleanup_surface,
	}

	# Filter by object if requested
	if object_name:
		obj_asset_names = set(objects.get(object_name, {}).get('assets', {}).keys())
		output['provenance'] = [p for p in output['provenance'] if p['asset'] in obj_asset_names]
		output['svg_health'] = [h for h in output['svg_health'] if h['asset'] in obj_asset_names]
		output['object_alignment'] = [a for a in output['object_alignment'] if a['object'] == object_name]
		output['subpart_alignment'] = [s for s in output['subpart_alignment'] if s['object'] == object_name]

	print(json.dumps(output, indent=2))

if __name__ == '__main__':
	main()
