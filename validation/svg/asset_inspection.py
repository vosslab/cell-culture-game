"""Inspect repository-owned SVG assets and their declared source metadata."""

import functools
import hashlib
import os
import pathlib
import re

import lxml.etree

import validation.shared_toolkit.paths
import validation.svg.asset_registry


REPO_ROOT = validation.shared_toolkit.paths.REPO_ROOT
ASSETS_DIR = os.path.join(REPO_ROOT, 'assets', 'equipment')
# ASVS 5.3.2: provenance metadata is read only from this fixed repo-owned path.
SOURCES_MD = os.path.join(ASSETS_DIR, 'SOURCES.md')


@functools.lru_cache(maxsize=1)
def _equipment_registry() -> object:
	"""Return the shared recursive equipment registry for path lookups."""
	return validation.svg.asset_registry.build_svg_asset_registry(pathlib.Path(ASSETS_DIR))


def _asset_path(asset_name: str) -> str:
	"""Resolve one logical equipment asset name to its current source path."""
	try:
		return str(_equipment_registry().asset_path(asset_name))
	except KeyError:
		return os.path.join(ASSETS_DIR, f'{asset_name}.svg')


def parse_servier_source_rows(lines: list[str]) -> dict[str, tuple[str, str]]:
	"""Extract Servier-adopted SVG info from Markdown table rows."""
	sources_map = {}
	for line in lines:
		stripped = line.strip()
		if not (stripped.startswith('|') and stripped.endswith('|')):
			continue

		parts = [part.strip() for part in stripped.split('|')]
		if len(parts) < 4:
			continue

		asset_match = re.fullmatch(r'`([^`/]+)\.svg`', parts[1])
		servier_match = re.fullmatch(
			r'`([^/`]+)/Servier/([^`]+\.svg)`',
			parts[2],
		)
		if not asset_match or not servier_match:
			continue

		filename = asset_match.group(1)
		category = servier_match.group(1)
		servier_path = f"{category}/Servier/{servier_match.group(2)}"
		full_path = f'OTHER_REPOS/bioicons/static/icons/cc-by-3.0/{servier_path}'
		sources_map[filename] = (full_path, category)

	return sources_map


def parse_servier_sources() -> dict[str, tuple[str, str]]:
	"""Extract Servier-adopted SVG info from the repository source ledger."""
	if not os.path.isfile(SOURCES_MD):
		return {}

	with open(SOURCES_MD, 'r', encoding='utf-8') as file_handle:
		return parse_servier_source_rows(file_handle.readlines())


def compute_file_hash(path: str) -> str:
	"""Compute the SHA-256 hash of one file."""
	sha256_hash = hashlib.sha256()
	with open(path, 'rb') as file_handle:
		for chunk in iter(lambda: file_handle.read(4096), b''):
			sha256_hash.update(chunk)
	return sha256_hash.hexdigest()


def check_modification_status(
	asset_name: str,
	servier_sources: dict[str, tuple[str, str]],
) -> str:
	"""Classify a Servier-adopted SVG as pristine, adapted, or unavailable."""
	if asset_name not in servier_sources:
		return 'pristine'

	source_path_rel, _ = servier_sources[asset_name]
	source_path_abs = os.path.join(REPO_ROOT, source_path_rel)
	if not os.path.isfile(source_path_abs):
		return 'source_missing'

	our_hash = compute_file_hash(_asset_path(asset_name))
	source_hash = compute_file_hash(source_path_abs)
	return 'pristine' if our_hash == source_hash else 'adapted'


def check_attribution(
	asset_name: str,
	servier: set[str],
	servier_sources: dict[str, tuple[str, str]],
) -> str:
	"""Classify the attribution evidence for a Servier-adopted SVG."""
	if asset_name not in servier:
		return 'attributed_both'

	has_inline_attribution = False
	svg_path = _asset_path(asset_name)
	if os.path.isfile(svg_path):
		try:
			with open(svg_path, 'r', encoding='utf-8') as file_handle:
				content = file_handle.read(2000)
				has_inline_attribution = bool(re.search(
					r'<!--.*?[Ss]ervier.*?[Cc][Cc]\s+[Bb][Yy].*?-->',
					content,
					re.DOTALL,
				))
		except (OSError, UnicodeDecodeError):
			pass

	in_manifest = asset_name in servier_sources
	if has_inline_attribution and in_manifest:
		return 'attributed_both'
	if has_inline_attribution:
		return 'attributed_inline'
	if in_manifest:
		return 'attributed_manifest'
	return 'unattributed'


def check_normalization(asset_name: str) -> tuple[str, str | None]:
	"""Check an SVG's root namespace and numeric viewBox normalization."""
	svg_path = _asset_path(asset_name)
	if not os.path.isfile(svg_path):
		return 'failed', 'file_not_found'

	try:
		# ASVS 1.5.2: entity resolution and external network fetches stay disabled
		# even though SVG assets originate in this repository.
		parser = lxml.etree.XMLParser(resolve_entities=False, no_network=True)
		tree = lxml.etree.parse(svg_path, parser)
		root = tree.getroot()
		if not root.tag.endswith('svg'):
			return 'failed', 'root_not_svg'

		viewbox = root.get('viewBox')
		if not viewbox:
			return 'failed', 'no_viewbox'
		try:
			viewbox_parts = viewbox.split()
			if len(viewbox_parts) != 4:
				return 'failed', 'invalid_viewbox_format'
			for part in viewbox_parts:
				float(part)
		except (ValueError, AttributeError):
			return 'failed', 'viewbox_not_numeric'

		if not root.tag.startswith('{http://www.w3.org/2000/svg}'):
			return 'failed', 'bad_xmlns'
		return 'normalized', None
	except lxml.etree.XMLSyntaxError:
		return 'failed', 'xml_parse_error'
	except OSError:
		return 'failed', 'parse_exception'


def check_forbidden_constructs(asset_name: str) -> list[str]:
	"""Return security-relevant SVG constructs found in one source asset."""
	findings = []
	svg_path = _asset_path(asset_name)
	if not os.path.isfile(svg_path):
		return findings

	try:
		with open(svg_path, 'r', encoding='utf-8') as file_handle:
			content = file_handle.read()
		if re.search(r'<script[^>]*>', content, re.IGNORECASE):
			findings.append('script_element')
		if re.search(r'<foreignObject[^>]*>', content, re.IGNORECASE):
			findings.append('foreignObject_element')
		if re.search(r'data:image/[^;]+;base64,', content):
			findings.append('embedded_base64_image')
		if re.search(r'\bon[a-z]+\s*=', content, re.IGNORECASE):
			findings.append('inline_event_handler')
	except (OSError, UnicodeDecodeError):
		pass
	return findings


def get_file_size_kb(asset_name: str) -> float | None:
	"""Return the source SVG's size in kilobytes when it exists."""
	svg_path = _asset_path(asset_name)
	if os.path.isfile(svg_path):
		return os.path.getsize(svg_path) / 1024.0
	return None


def extract_subpart_ids(asset_name: str) -> set[str]:
	"""Extract data-subpart-id values from one SVG with hardened XML parsing."""
	subpart_ids = set()
	svg_path = _asset_path(asset_name)
	if not os.path.isfile(svg_path):
		return subpart_ids

	try:
		# ASVS 1.5.2: do not permit an SVG to resolve entities or use the network.
		parser = lxml.etree.XMLParser(resolve_entities=False, no_network=True)
		tree = lxml.etree.parse(svg_path, parser)
		for element in tree.getroot().iter():
			subpart_id = element.get('data-subpart-id')
			if subpart_id:
				subpart_ids.add(subpart_id)
	except lxml.etree.XMLSyntaxError:
		pass
	return subpart_ids


def get_expected_subparts(
	object_name: str,
	object_data: dict[str, object],
) -> set[str] | None:
	"""Expand the object schema's expected structured subpart names."""
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
	rows = int(structure.get('rows', 1))
	cols = int(structure.get('cols', 1))
	if uses_row_letter and rows > 26:
		raise ValueError(
			f'{object_name}: {{row_letter}} supports at most 26 rows (A..Z), '
			f'not {rows}',
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
	object_data: dict[str, object],
) -> dict[str, tuple[int, int, list[str]]]:
	"""Return enum visual-state coverage for SVG-backed object fields."""
	coverage = {}
	if 'visual_states' not in object_data or 'state_fields' not in object_data:
		return coverage

	enum_map = {}
	for field_def in object_data['state_fields']:
		if field_def.get('type') == 'enum':
			enum_map[field_def['field_name']] = set(field_def.get('allowed', []))
	for field_name, state_def in object_data['visual_states'].items():
		if field_name not in enum_map or state_def.get('kind') != 'svg':
			continue
		covered_values = set()
		for case in state_def.get('cases', []):
			output = case.get('output', {})
			if isinstance(output, dict) and 'asset_name' in output:
				covered_values.add(case.get('when'))
		expected = enum_map[field_name]
		coverage[field_name] = (
			len(covered_values),
			len(expected),
			sorted(expected - covered_values),
		)
	return coverage


def list_disk_svgs() -> set[str]:
	"""List logical SVG names from the recursive equipment registry."""
	if not os.path.isdir(ASSETS_DIR):
		return set()
	return set(_equipment_registry().asset_names)
