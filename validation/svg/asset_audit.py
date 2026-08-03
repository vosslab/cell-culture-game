#!/usr/bin/env python3
"""SVG asset audit tool.

Walks all object YAML files, identifies asset_name references in visual_states,
and cross-walks with recursively registered equipment SVGs and source manifests
(SOURCES.md, MISSING_SVG_PLACEHOLDERS.md) to classify each asset and detect
orphans. Reports enriched per-asset metadata: Servier provenance, modification
status, attribution, normalization, forbidden constructs, file size, subpart
coverage, enum case coverage, and reuse counts.

Usage:
	python3 validation/svg/asset_audit.py
	python3 validation/svg/asset_audit.py --object gel_cassette
	python3 validation/svg/asset_audit.py --json
"""

import os
import re
import sys
import hashlib
from functools import lru_cache
from pathlib import Path

import yaml
import lxml.etree

import validation.shared_toolkit.paths as toolkit_paths
import validation.shared_toolkit.interactive as toolkit_interactive
import validation.shared_toolkit.reporter as reporter
import validation.shared_toolkit.cli as toolkit_cli
import validation.shared_toolkit.verbosity as verbosity
from validation.svg.asset_registry import build_svg_asset_registry

#============================================
# setup
#============================================

REPO_ROOT = toolkit_paths.REPO_ROOT
OBJECTS_DIR = toolkit_paths.OBJECTS_DIR
ASSETS_DIR = os.path.join(REPO_ROOT, "assets", "equipment")
SOURCES_MD = os.path.join(ASSETS_DIR, "SOURCES.md")
PLACEHOLDERS_MD = os.path.join(ASSETS_DIR, "MISSING_SVG_PLACEHOLDERS.md")
OTHER_REPOS_ROOT = os.path.join(REPO_ROOT, "..", "OTHER_REPOS")


@lru_cache(maxsize=1)
def _equipment_registry():
	"""Return the shared recursive equipment registry for path lookups."""
	return build_svg_asset_registry(Path(ASSETS_DIR))


def _asset_path(asset_name: str) -> str:
	"""Resolve one logical equipment asset name to its current source path."""
	try:
		return str(_equipment_registry().asset_path(asset_name))
	except KeyError:
		return os.path.join(ASSETS_DIR, f"{asset_name}.svg")

#============================================
# servier source and category parsing
#============================================

def parse_servier_sources() -> dict[str, tuple[str, str]]:
	"""Extract Servier-adopted SVG info from SOURCES.md.

	Returns dict mapping asset_basename -> (source_path, category)
	where source_path is the Servier path and category is the bioicons
	category (Lab_apparatus, Chemistry, Microbiology, etc).
	"""
	sources_map = {}
	if not os.path.isfile(SOURCES_MD):
		return sources_map

	with open(SOURCES_MD, 'r', encoding='utf-8') as f:
		lines = f.readlines()

	in_table = False

	for line in lines:
		stripped = line.strip()

		# Detect table start: the header separator row (contains ---)
		if '---' in line and '|' in line:
			in_table = True
			continue

		# Parse table rows
		if in_table and stripped.startswith('|') and stripped.endswith('|'):
			parts = [p.strip() for p in stripped.split('|')]
			if len(parts) >= 3:
				cell = parts[1]
				# Extract backtick-wrapped filename and Servier path
				if cell.startswith('`') and cell.endswith('.svg`'):
					filename = cell[1:-5]  # remove ` and .svg`
					servier_cell = parts[2]
					# Extract backtick-wrapped path
					if servier_cell.startswith('`') and servier_cell.endswith('.svg`'):
						servier_path = servier_cell[1:-5]
						# Extract category from servier_path (e.g., "Microbiology/Servier/...")
						path_parts = servier_path.split('/')
						if len(path_parts) >= 2:
							category = path_parts[0]
							full_path = f"OTHER_REPOS/bioicons/static/icons/cc-by-3.0/{servier_path}.svg"
							sources_map[filename] = (full_path, category)

	return sources_map

def parse_servier_assets() -> set[str]:
	"""Extract Servier-adopted SVG filenames from SOURCES.md.

	Scans markdown table rows for backtick-wrapped filenames in the first column.
	Returns the set of basenames without .svg extension.
	"""
	servier = set()
	if not os.path.isfile(SOURCES_MD):
		return servier

	with open(SOURCES_MD, 'r', encoding='utf-8') as f:
		lines = f.readlines()

	in_table = False
	for line in lines:
		line = line.strip()
		# Detect table start: the header separator row (contains ---)
		if '---' in line and '|' in line:
			in_table = True
			continue

		# Parse table rows
		if in_table and line.startswith('|') and line.endswith('|'):
			parts = line.split('|')
			if len(parts) >= 3:
				# First cell after the leading |
				cell = parts[1].strip()
				# Extract backtick-wrapped filename
				if cell.startswith('`') and cell.endswith('.svg`'):
					filename = cell[1:-5]  # remove ` and .svg`
					servier.add(filename)

	return servier

def parse_placeholder_assets() -> set[str]:
	"""Extract placeholder SVG filenames from MISSING_SVG_PLACEHOLDERS.md.

	Scans markdown table rows for backtick-wrapped filenames in the first column.
	Returns the set of basenames without .svg extension.
	"""
	placeholders = set()
	if not os.path.isfile(PLACEHOLDERS_MD):
		return placeholders

	with open(PLACEHOLDERS_MD, 'r', encoding='utf-8') as f:
		lines = f.readlines()

	in_table = False
	for line in lines:
		line = line.strip()
		# Detect table start: the header separator row (contains ---)
		if '---' in line and '|' in line:
			in_table = True
			continue

		# Parse table rows
		if in_table and line.startswith('|') and line.endswith('|'):
			parts = line.split('|')
			if len(parts) >= 3:
				# First cell after the leading |
				cell = parts[1].strip()
				# Extract backtick-wrapped filename
				if cell.startswith('`') and cell.endswith('.svg`'):
					filename = cell[1:-5]  # remove ` and .svg`
					placeholders.add(filename)

	return placeholders

#============================================
# asset metadata checks
#============================================

def compute_file_hash(path: str) -> str:
	"""Compute SHA-256 hash of a file."""
	sha256_hash = hashlib.sha256()
	with open(path, 'rb') as f:
		for chunk in iter(lambda: f.read(4096), b''):
			sha256_hash.update(chunk)
	return sha256_hash.hexdigest()

def check_modification_status(
	asset_name: str,
	servier_sources: dict[str, tuple[str, str]]
) -> str:
	"""Check if a Servier-adopted SVG has been modified.

	Returns: 'pristine', 'adapted', or 'source_missing'.
	"""
	if asset_name not in servier_sources:
		return 'pristine'  # not a Servier asset, skip

	source_path_rel, _ = servier_sources[asset_name]
	source_path_abs = os.path.join(REPO_ROOT, source_path_rel)

	if not os.path.isfile(source_path_abs):
		return 'source_missing'

	our_svg = _asset_path(asset_name)
	our_hash = compute_file_hash(our_svg)
	source_hash = compute_file_hash(source_path_abs)

	return 'pristine' if our_hash == source_hash else 'adapted'

def check_attribution(
	asset_name: str,
	servier: set[str],
	servier_sources: dict[str, tuple[str, str]]
) -> str:
	"""Check attribution for a Servier-adopted SVG.

	Returns: 'attributed_inline', 'attributed_manifest', 'attributed_both', or 'unattributed'.
	"""
	if asset_name not in servier:
		return 'attributed_both'  # not a Servier asset, no check needed

	svg_path = _asset_path(asset_name)
	has_inline_attribution = False

	# Check for inline XML comment with Servier + CC BY
	if os.path.isfile(svg_path):
		try:
			with open(svg_path, 'r', encoding='utf-8') as f:
				content = f.read(2000)  # check first 2000 chars for comment
				if re.search(r'<!--.*?[Ss]ervier.*?[Cc][Cc]\s+[Bb][Yy].*?-->', content, re.DOTALL):
					has_inline_attribution = True
		except (IOError, OSError, UnicodeDecodeError):
			pass

	in_manifest = asset_name in servier_sources

	if has_inline_attribution and in_manifest:
		return 'attributed_both'
	elif has_inline_attribution:
		return 'attributed_inline'
	elif in_manifest:
		return 'attributed_manifest'
	else:
		return 'unattributed'

def check_normalization(asset_name: str) -> tuple[str, str | None]:
	"""Check SVG normalization.

	Returns: (status, reason) where status is 'normalized' or 'failed'.
	"""
	svg_path = _asset_path(asset_name)

	if not os.path.isfile(svg_path):
		return 'failed', 'file_not_found'

	try:
		# Hardened lxml parser: resolve_entities=False blocks XXE entity
		# expansion, no_network=True blocks external DTD/entity network fetches.
		# First-party repo asset, but the parser stays hardened regardless of
		# source trust.
		parser = lxml.etree.XMLParser(resolve_entities=False, no_network=True)
		tree = lxml.etree.parse(svg_path, parser)
		root = tree.getroot()

		# Check root element
		if not root.tag.endswith('svg'):
			return 'failed', 'root_not_svg'

		# Check viewBox
		viewbox = root.get('viewBox')
		if not viewbox:
			return 'failed', 'no_viewbox'

		# Try to parse viewBox as 4 numbers
		try:
			viewbox_parts = viewbox.split()
			if len(viewbox_parts) != 4:
				return 'failed', 'invalid_viewbox_format'
			for part in viewbox_parts:
				float(part)
		except (ValueError, AttributeError):
			return 'failed', 'viewbox_not_numeric'

		# Check xmlns. lxml folds the default namespace into the tag (root.tag
		# becomes '{http://www.w3.org/2000/svg}svg'); it does NOT expose 'xmlns'
		# as a gettable attribute, so root.get('xmlns') is always None for a
		# correctly-namespaced SVG. Detect normalization from the parsed tag
		# namespace instead.
		svg_namespace = '{http://www.w3.org/2000/svg}'
		if not root.tag.startswith(svg_namespace):
			return 'failed', 'bad_xmlns'

		return 'normalized', None

	except lxml.etree.XMLSyntaxError:
		return 'failed', 'xml_parse_error'
	except (IOError, OSError):
		return 'failed', 'parse_exception'

def check_forbidden_constructs(asset_name: str) -> list[str]:
	"""Check for forbidden SVG constructs.

	Returns list of findings (empty if none).
	"""
	findings = []
	svg_path = _asset_path(asset_name)

	if not os.path.isfile(svg_path):
		return findings

	try:
		with open(svg_path, 'r', encoding='utf-8') as f:
			content = f.read()

		# Check for script elements
		if re.search(r'<script[^>]*>', content, re.IGNORECASE):
			findings.append('script_element')

		# Check for foreignObject
		if re.search(r'<foreignObject[^>]*>', content, re.IGNORECASE):
			findings.append('foreignObject_element')

		# Check for base64 embedded images
		if re.search(r'data:image/[^;]+;base64,', content):
			findings.append('embedded_base64_image')

		# Check for inline event handlers
		if re.search(r'\bon[a-z]+\s*=', content, re.IGNORECASE):
			findings.append('inline_event_handler')

	except (IOError, OSError, UnicodeDecodeError):
		pass

	return findings

def get_file_size_kb(asset_name: str) -> float | None:
	"""Get file size in KB."""
	svg_path = _asset_path(asset_name)
	if os.path.isfile(svg_path):
		size_bytes = os.path.getsize(svg_path)
		return size_bytes / 1024.0
	return None

def extract_subpart_ids(asset_name: str) -> set[str]:
	"""Extract all data-subpart-id attribute values from SVG."""
	subpart_ids = set()
	svg_path = _asset_path(asset_name)

	if not os.path.isfile(svg_path):
		return subpart_ids

	try:
		# Hardened lxml parser: resolve_entities=False blocks XXE entity
		# expansion, no_network=True blocks external DTD/entity network fetches.
		# First-party repo asset, but the parser stays hardened regardless of
		# source trust.
		parser = lxml.etree.XMLParser(resolve_entities=False, no_network=True)
		tree = lxml.etree.parse(svg_path, parser)
		root = tree.getroot()

		for elem in root.iter():
			subpart_id = elem.get('data-subpart-id')
			if subpart_id:
				subpart_ids.add(subpart_id)

	except lxml.etree.XMLSyntaxError:
		pass

	return subpart_ids

def get_expected_subparts(object_name: str, object_data: dict[str, object]) -> set[str] | None:
	"""Extract expected subpart names from object YAML structure block."""
	if 'structure' not in object_data:
		return None

	structure = object_data['structure']
	explicit_names = structure.get('subpart_names')
	if isinstance(explicit_names, list):
		return set(explicit_names)
	name_pattern = structure.get('name_pattern')

	if not name_pattern:
		return None

	uses_row = '{row}' in name_pattern
	uses_row_letter = '{row_letter}' in name_pattern
	uses_col = '{col}' in name_pattern
	if not (uses_row or uses_row_letter or uses_col):
		return None

	# Structured grid names use the same row-major, 1-based numeric convention
	# as pipeline.gen_object_library. The authoring vocabulary deliberately
	# limits row letters to A..Z, so do not silently turn row 27 into '['.
	rows = int(structure.get('rows', 1))
	cols = int(structure.get('cols', 1))
	if uses_row_letter and rows > 26:
		raise ValueError(
			f"{object_name}: {{row_letter}} supports at most 26 rows (A..Z), "
			f"not {rows}"
		)

	row_indices = range(rows) if (uses_row or uses_row_letter) else range(1)
	col_indices = range(cols) if uses_col else range(1)
	subparts = set()
	for row_index in row_indices:
		for col_index in col_indices:
			name = name_pattern
			name = name.replace('{row_letter}', chr(ord('A') + row_index))
			name = name.replace('{row}', str(row_index + 1))
			name = name.replace('{col}', str(col_index + 1))
			subparts.add(name)
	return subparts


def check_enum_coverage(
	object_name: str,
	object_data: dict[str, object]
) -> dict[str, tuple[int, int, list[str]]]:
	"""Check enum case coverage in visual_states.

	Returns dict: field_name -> (covered_count, total_count, missing_values)
	Only includes fields with asset_name references and enum state_fields.
	"""
	coverage = {}

	if 'visual_states' not in object_data or 'state_fields' not in object_data:
		return coverage

	# Build state_field enum map
	enum_map = {}
	for field_def in object_data['state_fields']:
		if field_def.get('type') == 'enum':
			field_name = field_def['field_name']
			allowed = field_def.get('allowed', [])
			enum_map[field_name] = set(allowed)

	# Check visual_states that use asset_name
	visual_states = object_data['visual_states']
	for field_name, state_def in visual_states.items():
		if field_name not in enum_map:
			continue

		if state_def.get('kind') != 'svg':
			continue

		cases = state_def.get('cases', [])
		covered_values = set()

		for case in cases:
			when = case.get('when')
			output = case.get('output', {})
			if isinstance(output, dict) and 'asset_name' in output:
				covered_values.add(when)

		expected = enum_map[field_name]
		missing = expected - covered_values
		coverage[field_name] = (len(covered_values), len(expected), sorted(missing))

	return coverage

#============================================
# asset discovery
#============================================

def list_disk_svgs() -> set[str]:
	"""List logical SVG names from the recursive equipment registry."""
	if not os.path.isdir(ASSETS_DIR):
		return set()
	return set(_equipment_registry().asset_names)

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
	servier: set[str],
	placeholders: set[str]
) -> str:
	"""Classify the source of an asset_name.

	Returns one of: 'servier', 'placeholder', 'unknown', 'missing'.
	"""
	if asset_name not in disk_svgs:
		return 'missing'

	if asset_name in servier:
		return 'servier'

	if asset_name in placeholders:
		return 'placeholder'

	return 'unknown'

#============================================
# audit logic
#============================================

def audit_repo(
	disk_svgs: set[str],
	servier: set[str],
	placeholders: set[str],
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
			classification = classify_asset(asset_name, disk_svgs, servier, placeholders)
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
		mod_status = check_modification_status(asset_name, servier_sources)
		meta['modification_status'] = mod_status
	else:
		meta['modification_status'] = None

	# Attribution
	if asset_name in servier:
		attr = check_attribution(asset_name, servier, servier_sources)
		meta['attribution'] = attr
	else:
		meta['attribution'] = None

	# Normalization
	norm_status, norm_reason = check_normalization(asset_name)
	meta['normalization'] = norm_status
	meta['normalization_reason'] = norm_reason

	# Forbidden constructs
	forbidden = check_forbidden_constructs(asset_name)
	meta['forbidden_constructs'] = forbidden

	# File size
	size_kb = get_file_size_kb(asset_name)
	meta['file_size_kb'] = size_kb

	# Subpart IDs
	subpart_ids = extract_subpart_ids(asset_name)
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
	servier: set[str],
	placeholders: set[str],
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
	placeholder_objs = 0
	mixed_objs = 0
	missing_objs = 0
	unknown_objs = 0

	servier_assets = 0
	placeholder_assets = 0
	missing_assets = 0
	unknown_assets = 0

	for obj_data in objects.values():
		sources = obj_data['sources']

		# Object-level classification
		if 'missing' in sources:
			missing_objs += 1
		elif 'unknown' in sources:
			unknown_objs += 1
		elif len(sources) > 1:  # mixed servier + placeholder
			mixed_objs += 1
		elif 'placeholder' in sources:
			placeholder_objs += 1
		elif 'servier' in sources:
			servier_objs += 1

		# Asset-level counts
		for asset_name, classification in obj_data['assets'].items():
			if classification == 'servier':
				servier_assets += 1
			elif classification == 'placeholder':
				placeholder_assets += 1
			elif classification == 'missing':
				missing_assets += 1
			elif classification == 'unknown':
				unknown_assets += 1

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

	# Compute unknown SVGs: on disk but in neither manifest
	referenced_in_objects = set()
	for obj_data in objects.values():
		referenced_in_objects.update(obj_data['assets'].keys())
	unknown_svgs = disk_svgs - referenced_in_objects
	for asset_name in list(unknown_svgs):
		if asset_name in per_asset_metadata:
			unknown_svgs.discard(asset_name)

	# Deduplicate: orphan takes precedence over unknown
	truly_unknown = unknown_svgs - orphan_svgs

	# Resolve verbosity level once via the shared helper.
	level = verbosity.resolve_level(quiet=quiet, verbose=verbose)

	# Compute totals needed by all modes, split into the three severity tiers.
	#   error    = malformed SVG (unparseable) + forbidden constructs
	#   warning  = non-normalized SVG + unattributed Servier adoptions
	#   advisory = orphan SVGs + unknown SVGs (cleanup, do not block)
	total_checked = len(objects)
	error_count = malformed_count + forbidden_construct_count
	warning_count = non_normalized_count + unattributed_servier
	advisory_count = len(orphan_svgs) + len(truly_unknown)

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
	print(f"  placeholder: {placeholder_objs} objects, {placeholder_assets} svgs")
	print(f"  mixed:       {mixed_objs} objects (uses both servier and placeholder)")
	print(f"  missing:     {missing_objs} objects (one or more asset_name has no .svg)")
	print(f"  unknown:     {unknown_objs} objects (one or more .svg in neither manifest)")
	print()

	# Cleanup surface section: counts always shown; item listings only in VERBOSE.
	is_verbose = (level == verbosity.VerbosityLevel.VERBOSE)
	print_cleanup_surface_section(orphan_svgs, unknown_svgs, verbose=is_verbose)
	print()

	# Actionable findings summary (NORMAL and VERBOSE).
	print("Actionable findings:")
	print(f"  Orphan SVG files: {len(orphan_svgs)}")
	print(f"  Unknown SVG files: {len(truly_unknown)}")
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
			expected_subparts = get_expected_subparts(obj_name, yaml_data)
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
			("placeholder", placeholder_assets),
			("unknown", unknown_assets),
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
		coverage = check_enum_coverage(obj_name, obj_data.get('yaml_data', {}))
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
		expected_subparts = get_expected_subparts(obj_name, yaml_data)

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

def print_cleanup_surface_section(orphan_svgs: set[str], unknown_svgs: set[str], quiet: bool = False, verbose: bool = False) -> None:
	"""Print cleanup surface section: orphans, unknowns, superseded.

	quiet mode: return early (handled by caller).
	default mode: print section header and counts only, no item listings.
	verbose mode: print section header, counts, AND raw item listings.
	"""
	# Orphan and unknown may overlap: a file can have no object reference AND not be
	# in a manifest. Deduplicate so each appears only once, with orphan taking precedence.
	truly_unknown = unknown_svgs - orphan_svgs

	print("=== Cleanup surface ===")

	if orphan_svgs:
		print(f"Orphan SVGs ({len(orphan_svgs)}):")
		if verbose:
			for svg in sorted(orphan_svgs):
				print(f"  {svg}")
	else:
		print("Orphan SVGs: (none)")

	if truly_unknown:
		print(f"Unknown SVGs ({len(truly_unknown)}):")
		if verbose:
			for svg in sorted(truly_unknown):
				print(f"  {svg}")
	else:
		print("Unknown SVGs: (none)")

	print("Superseded files: (none)")

#============================================
# cli
#============================================

def parse_args():
	"""Parse command-line arguments."""
	#============================================
	# extras callback registers SVG audit-specific flags
	#============================================
	def register_svg_audit_flags(parser):
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

def main():
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

	# Load manifests and discover assets
	disk_svgs = list_disk_svgs()
	servier = parse_servier_assets()
	placeholders = parse_placeholder_assets()
	servier_sources = parse_servier_sources()

	# Run the audit
	objects, missing_items, orphan_svgs, asset_reuse, per_asset_metadata = audit_repo(
		disk_svgs, servier, placeholders, servier_sources
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
		print_json_report(args.object_name, objects, disk_svgs, servier, placeholders, asset_reuse, per_asset_metadata, orphan_svgs)
	else:
		# Table format
		if args.object_name:
			if args.object_name not in objects:
				reporter.print_error(f"Object '{args.object_name}' not found.")
				sys.exit(1)
			# Per-object mode always prints per-asset detail
			print_object_detail_table(args.object_name, objects, asset_reuse, per_asset_metadata, orphan_svgs, servier, placeholders)
		else:
			# Repo-wide mode: honor -q and -v. Exit is ERROR-only: warnings and
			# advisories (non-normalized, orphan) print but do not fail the run.
			error_count = print_full_report(
				objects, missing_items, orphan_svgs, disk_svgs, servier, placeholders,
				asset_reuse, per_asset_metadata, quiet=args.quiet, verbose=args.verbose
			)
			sys.exit(1 if error_count else 0)

def print_object_detail_table(
	object_name: str,
	objects: dict[str, dict[str, object]],
	asset_reuse: dict[str, int],
	per_asset_metadata: dict[str, object],
	orphan_svgs: set[str],
	servier: set[str],
	placeholders: set[str]
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

	print_cleanup_surface_section(orphan_svgs, set(), verbose=True)

def print_json_report(
	object_name: str | None,
	objects: dict[str, dict[str, object]],
	disk_svgs: set[str],
	servier: set[str],
	placeholders: set[str],
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
		expected_subparts = get_expected_subparts(obj_name, yaml_data)
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
		'unknown': [],
		'superseded': [],
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
