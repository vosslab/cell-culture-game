#!/usr/bin/env python3
"""
Generate the SVG asset manifest as a TypeScript module.

Validates all SVGs under assets/**/*.svg, then emits one output:

1. generated/svg_manifest.ts (the durable runtime output): maps each asset_name
   to its RELATIVE built-site path (assets/svg/<category>/<name>.svg, no leading
   slash so it resolves under the GitHub Pages project subpath
   /virtual-lab-protocol-simulation/), plus a DERIVED per-asset
   requires_dom_svg boolean computed from object declarations. No inline SVG
   markup is emitted to runtime: the giant SVG_REGISTRY markup blob left the
   bundle in the registry-to-manifest cutover.
"""

import os
import re
import shutil
import sys
import subprocess
from pathlib import Path

import yaml
import lxml.etree
from validation.svg.layer_recipe_validator import (
	MaterialSvgValidationError,
	validate_material_svg,
	validate_reserved_attributes,
)
from validation.svg.asset_taxonomy_validator import validate_asset_taxonomy
from validation.svg.asset_registry import build_svg_asset_registry

# Import the shared validator (lives in tools/ as a dev-tool helper).
# pipeline/ generator scripts add the sibling tools/ dir to sys.path so the
# bare-name import remains valid per docs/PYTHON_STYLE.md. This insert is
# still required: PYTHONPATH (repo root) does not cover a bare-name import
# of a tools/ dev-tool module.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import svg_validate

# Roots scanned for SVG-key references. A key not referenced in any of these
# trees is treated as orphan and dropped from the shipped registry. Authors
# can keep the .svg file on disk; only the bundled emission is filtered.
USAGE_SCAN_ROOTS = (
	"src",
	"tests",
	"content",
	"generated",
)

# File extensions that may legitimately reference an SVG key by name.
USAGE_SCAN_SUFFIXES = (".ts", ".tsx", ".mts", ".js", ".mjs", ".yaml", ".yml", ".json", ".py", ".html")

# No explicit namespace registration is needed here: unlike ElementTree,
# lxml.etree preserves the original prefix-to-namespace bindings (nsmap) found
# on each element when it was parsed, so re-serializing with lxml.etree.tostring
# reproduces the source file's own xmlns="...svg" / xmlns:xlink="..." prefixes
# (the standard SVG normalization every asset in assets/ already uses) without
# needing a global prefix registration step.

# requires_dom_svg means the object needs access to the INTERNAL structure of
# its SVG (reach inside the asset to clip a liquid region, target a subpart id,
# or layer real internal subparts). It does NOT mean "has any visual state". An
# object that only labels over the asset, swaps the whole asset, or is merely
# clickable can render as an opaque <img>.
#
# The predicate is derived from signals that EXIST in object YAML /
# generated object_library.ts TODAY (verified against content/objects/**/*.yaml
# and generated/object_library.ts). It deliberately does NOT use the
# forward-looking material vocabulary named in the plan (render_effect:
# material_tint / fill_height, target: subpart_geometry, anchor_liquid_bounds /
# anchor_liquid_clip): those field names are not emitted into generated data yet
# and introducing them into YAML is closure-gated under
# docs/specs/SPEC_DESIGN_CHECKLIST.md (separate approval, out of scope here).
#
# Derive requires_dom_svg = TRUE when ANY of the following holds:
#   1. a capability of 'material_container' (holds material, so its internal
#      liquid region must be DOM-reachable) or 'structured_surface'
#      (plates/racks whose subparts use generated internal overlay geometry);
#   2. any visual_states entry carrying a 'fill_height(' formula (the live
#      stand-in for a liquid fill region clip into the internal SVG);
#   3. a visual_states entry of kind 'composite' whose 'composite' list is
#      NON-EMPTY (actual internal subpart layers to target);
#   4. a visual_states entry of any UNKNOWN/unrecognized kind (SAFE BIAS:
#      an unrecognized declaration that could target internals defaults to TRUE
#      so a future internal-SVG effect is never silently rendered as an <img>).
#
# Derive FALSE (img-eligible) when the object has ONLY: generic 'overlay'-kind
# states (text/label layer drawn OVER the asset as a separate DOM layer), an
# EMPTY 'composite: []' (no internal subparts to target), whole-asset 'svg'-kind
# swaps (just change the <img> src), and/or clickable-only capabilities. None of
# those needs internal SVG access.
DOM_SVG_CAPABILITY_TOKENS = (
	"material_container",
	"structured_surface",
)
# visual_state.kind values that are KNOWN to be img-eligible on their own (they
# never need internal SVG access). A kind NOT in this set and NOT handled by an
# explicit internal-access rule below triggers the SAFE BIAS default-true.
DOM_SVG_IMG_ELIGIBLE_KINDS = (
	# text/label layer rendered as a separate DOM layer OVER the asset
	"overlay",
	# whole-asset swap: just changes the <img> src, no internal access
	"svg",
)
# Formula token marking a visual_state that clips/animates an internal liquid
# region (today's live stand-in for a declared fill-height render effect).
DOM_SVG_FILL_HEIGHT_TOKEN = "fill_height("


def main() -> None:
	"""Main entry point."""
	repo_root = _get_repo_root()
	assets_dir = os.path.join(repo_root, "assets")
	generated_dir = os.path.join(repo_root, "generated")
	if "--publish-to" in sys.argv:
		flag_index = sys.argv.index("--publish-to")
		if flag_index + 1 >= len(sys.argv):
			raise SystemExit("--publish-to requires a repo-relative output directory")
		output_dir = Path(sys.argv[flag_index + 1])
		if output_dir.is_absolute() or ".." in output_dir.parts:
			raise SystemExit("--publish-to must be a repo-relative output directory")
		publish_svg_tree(Path(assets_dir), Path(generated_dir), Path(repo_root) / output_dir)
		return
	validate_asset_taxonomy(Path(assets_dir), Path(repo_root) / "content" / "objects")
	asset_registry = build_svg_asset_registry(Path(assets_dir))

	# Ensure generated/ exists
	os.makedirs(generated_dir, exist_ok=True)

	# Collect all SVG files
	svg_files = [entry.source_path for entry in asset_registry.entries]

	print(f"Found {len(svg_files)} SVG files under {assets_dir}")

	registry = {}
	failed_files = []

	for svg_path in svg_files:
		abs_path = str(svg_path)

		print(f"processing {abs_path}")

		try:
			report = svg_validate.validate(abs_path)
			if not report.ok:
				failed_files.append((abs_path, report.error_message))
				continue
		except (FileNotFoundError, ValueError) as e:
			failed_files.append((abs_path, str(e)))
			continue

		# Parse and sanitize. Hardened lxml parser: resolve_entities=False blocks
		# XXE entity expansion, no_network=True blocks external DTD/entity network
		# fetches. First-party repo asset, but the parser stays hardened
		# regardless of source trust.
		try:
			parser = lxml.etree.XMLParser(resolve_entities=False, no_network=True)
			tree = lxml.etree.parse(abs_path, parser)
			root = tree.getroot()
		except lxml.etree.XMLSyntaxError as e:
			failed_files.append((abs_path, f"XML parse error: {e}"))
			continue

		# Reserved material attributes have a closed placement/value contract. They
		# are retained for the material compiler rather than silently stripped.
		try:
			is_material = validate_reserved_attributes(root)
			if is_material:
				validate_material_svg(root)
		except MaterialSvgValidationError as e:
			failed_files.append((abs_path, str(e)))
			continue
		# Strip unsafe attributes (onclick, onload, etc. are already caught by validator)
		_strip_unsafe_attrs(root, preserve_material_semantics=is_material)
		if is_material:
			try:
				validate_material_svg(root)
			except MaterialSvgValidationError as e:
				failed_files.append((abs_path, f"sanitized material SVG invalid: {e}"))
				continue

		# Convert back to string. lxml accepts encoding="unicode" for
		# ElementTree-API compatibility and returns a str (not bytes).
		svg_str = lxml.etree.tostring(root, encoding="unicode")

		# Derive registry key from filename (no extension)
		key = svg_path.stem

		registry[key] = svg_str

	# If there are failures, report and exit non-zero
	if failed_files:
		print("\nVALIDATION FAILURES:", file=sys.stderr)
		for path, error in failed_files:
			print(f"  {path}: {error}", file=sys.stderr)
		print(f"\nTotal: {len(failed_files)} file(s) failed", file=sys.stderr)
		raise SystemExit(1)

	# Filter orphans: drop keys that no source/content file references.
	# Pass --include-orphans to bypass (e.g. for asset-authoring previews).
	include_orphans = "--include-orphans" in sys.argv
	if include_orphans:
		shipped = registry
		dropped = {}
	else:
		referenced_keys = _scan_referenced_keys(repo_root, set(registry.keys()))
		shipped = {k: v for k, v in registry.items() if k in referenced_keys}
		dropped = {k: v for k, v in registry.items() if k not in referenced_keys}

	if dropped:
		dropped_bytes = sum(len(v) for v in dropped.values())
		print(f"\nDropped {len(dropped)} orphan SVG entries (~{dropped_bytes:,} bytes pre-escape).")
		print("Pass --include-orphans to ship them anyway. Orphan keys:")
		for key in sorted(dropped):
			print(f"  - {key}")

	# Emit the durable SVG manifest: relative built-site paths + derived
	# requires_dom_svg. This is the output the runtime moves to in the cutover.
	shipped_keys = set(shipped.keys())
	category_map = _build_asset_category_map(assets_dir, svg_files)
	requires_dom_svg = _derive_requires_dom_svg(repo_root, shipped_keys)
	manifest_file = os.path.join(generated_dir, "svg_manifest.ts")
	_emit_ts_manifest(manifest_file, shipped_keys, category_map, requires_dom_svg)

	dom_svg_count = sum(1 for k in shipped_keys if requires_dom_svg[k])
	print(f"\nGenerated {len(shipped_keys)} SVG entries into {manifest_file}")
	print(f"Derived requires_dom_svg = true for {dom_svg_count} asset(s).")

	print("Exit code: 0")

	# Remove outputs retired by manifest and strict-resolution cutovers. Direct
	# generator runs must converge an older generated tree just like the full
	# build, which starts from an empty generated directory.
	for stale_name in ("svg_registry.ts", "svg_placeholder_keys.ts"):
		stale_file = os.path.join(generated_dir, stale_name)
		if os.path.exists(stale_file):
			os.remove(stale_file)
			print(f"Removed stale {stale_file} (this output is no longer emitted).")


def _scan_referenced_keys(repo_root: str, candidate_keys: set) -> set:
	"""Return the subset of candidate_keys referenced anywhere under USAGE_SCAN_ROOTS.

	A reference is any whole-word match of the key in a scannable source file.
	The svg_registry.ts file itself is excluded so its own keys do not
	count as references.
	"""
	# Build one combined regex of all candidate keys for a single pass per file
	if not candidate_keys:
		return set()
	# Sort to make scanning deterministic
	keys_sorted = sorted(candidate_keys, key=len, reverse=True)
	combined = re.compile(r'\b(' + '|'.join(re.escape(k) for k in keys_sorted) + r')\b')

	referenced = set()
	for root_name in USAGE_SCAN_ROOTS:
		root = Path(repo_root) / root_name
		if not root.exists():
			continue
		for path in root.rglob("*"):
			if not path.is_file():
				continue
			if path.suffix not in USAGE_SCAN_SUFFIXES:
				continue
			# Skip generated registries so their own keys do
			# not self-reference (every asset_name appears in them by construction).
			if path.name in ("svg_registry.ts", "svg_manifest.ts", "svg_placeholder_keys.ts"):
				continue
			try:
				text = path.read_text(errors="ignore")
			except OSError:
				continue
			for match in combined.finditer(text):
				referenced.add(match.group(1))
				if len(referenced) == len(candidate_keys):
					return referenced
	return referenced


def _strip_unsafe_attrs(elem: lxml.etree._Element, preserve_material_semantics: bool = False) -> None:
	"""Recursively strip attributes that could be sanitization risks.

	The safe_attrs set uses both bare names (e.g. 'xlink:href') and
	Clark-notation namespace-expanded forms (e.g. '{http://...}href') because
	lxml.etree, like ElementTree, stores namespace-prefixed attributes using
	the Clark-notation expanded form internally. Without both forms, namespace-
	qualified attributes like xlink:href are silently dropped at serialization.

	Attributes stripped (not safe): event handlers (onclick, onload, etc.),
	javascript: href values, and any attribute not in the allow list. The
	validator (svg_validate.py) already rejects files with event handlers and
	script content; this strip is a defense-in-depth pass.
	"""
	# Namespace expansion used by lxml.etree (and ElementTree) internally.
	XLINK_NS = "http://www.w3.org/1999/xlink"

	# Attributes that are safe to keep: standard SVG/XML attributes.
	# Include both bare form and ET-internal namespace-expanded form so that
	# xlink:href and similar namespace-qualified attributes survive round-trip.
	safe_attrs = {
		# --- identity and namespace declarations ---
		"xmlns",
		"version",
		# --- presentation and layout ---
		"viewBox",
		"preserveAspectRatio",
		"width",
		"height",
		"x",
		"y",
		"x1",
		"y1",
		"x2",
		"y2",
		"cx",
		"cy",
		"r",
		"rx",
		"ry",
		"d",
		"points",
		"pathLength",
		# --- paint ---
		"fill",
		"stroke",
		"stroke-width",
		"stroke-linecap",
		"stroke-linejoin",
		"stroke-miterlimit",
		"stroke-dasharray",
		"stroke-dashoffset",
		"fill-opacity",
		"stroke-opacity",
		"fill-rule",
		"clip-path",
		"clip-rule",
		"color",
		"color-interpolation-filters",
		# --- filter and gradient ---
		"gradientUnits",
		"gradientTransform",
		"patternUnits",
		"patternTransform",
		"spreadMethod",
		"offset",
		"stop-color",
		"stop-opacity",
		"filterUnits",
		"primitiveUnits",
		"result",
		"in",
		"in2",
		"type",
		"values",
		"stdDeviation",
		"dx",
		"dy",
		"k1",
		"k2",
		"k3",
		"k4",
		"operator",
		"edgeMode",
		"flood-color",
		"flood-opacity",
		"lighting-color",
		# --- markers and text ---
		"marker-start",
		"marker-mid",
		"marker-end",
		"markerWidth",
		"markerHeight",
		"markerUnits",
		"refX",
		"refY",
		"orient",
		"font-size",
		"font-family",
		"font-weight",
		"font-style",
		"text-anchor",
		"dominant-baseline",
		"letter-spacing",
		"word-spacing",
		"textLength",
		"lengthAdjust",
		# --- structural ---
		"id",
		"class",
		"style",
		"transform",
		"opacity",
		"visibility",
		"display",
		"overflow",
		"clip",
		"clip-path",
		"mask",
		"enable-background",
		"shape-rendering",
		"image-rendering",
		"text-rendering",
		"color-rendering",
		# --- linking (bare form, used when no namespace prefix registered) ---
		"href",
		"xlink:href",
		# --- ET-internal Clark-notation expanded form for xlink:href.
		#     Python's ET stores 'xlink:href' as '{ns}href' internally;
		#     without this entry the attribute is treated as unsafe and stripped. ---
		"{%s}href" % XLINK_NS,
		# --- repo-specific data attributes ---
		"data-item-id",
		"data-well-id",
		"data-tube-id",
		"data-plate-id",
		"data-name",
	}
	if preserve_material_semantics:
		safe_attrs.update({
			"data-vlab-rendering",
			"data-vlab-max-fill-percent",
			"data-vlab-min-fill-percent",
			"data-vlab-body-start-fill-percent",
			"data-vlab-fill-height-exponent",
			"data-vlab-layer-name",
			"data-vlab-layer-kind",
			"data-vlab-paint-role",
			"data-vlab-adjustment",
			"data-vlab-liquid-part",
		})

	# Remove attributes not in safe list
	attrs_to_remove = [key for key in elem.attrib.keys() if key not in safe_attrs]
	for key in attrs_to_remove:
		del elem.attrib[key]

	for child in elem:
		_strip_unsafe_attrs(child, preserve_material_semantics=preserve_material_semantics)


def plan_svg_publication(source_path: Path, assets_dir: Path, generated_dir: Path) -> Path:
	"""Return the sole publishable artifact for one source SVG.

	Ordinary art publishes directly from source. A root-declared material form
	publishes only from its matching compiler artifact.
	"""
	parser = lxml.etree.XMLParser(resolve_entities=False, no_network=True)
	root = lxml.etree.parse(str(source_path), parser).getroot()
	try:
		is_material = validate_reserved_attributes(root)
		if is_material:
			validate_material_svg(root)
	except MaterialSvgValidationError as exc:
		raise ValueError(f"invalid SVG semantic attributes: {exc}") from exc
	if not is_material:
		return source_path
	artifact = generated_dir / "material_svg" / source_path.relative_to(assets_dir)
	if not artifact.is_file():
		raise FileNotFoundError(f"material SVG requires compiled artifact: {artifact}")
	return artifact


def publish_svg_tree(assets_dir: Path, generated_dir: Path, output_dir: Path) -> None:
	"""Publish each SVG at its stable logical URL, independent of source folders."""
	registry = build_svg_asset_registry(assets_dir)
	for entry in registry.entries:
		source_path = entry.source_path
		publication_path = plan_svg_publication(source_path, assets_dir, generated_dir)
		output_path = output_dir / entry.public_relative_path
		output_path.parent.mkdir(parents=True, exist_ok=True)
		shutil.copyfile(publication_path, output_path)


def _build_asset_category_map(assets_dir: str, svg_files: list) -> dict:
	"""Map each asset_name to its category directory under assets/.

	The asset_name is the SVG filename stem; the category is the immediate
	parent directory name relative to assets/ (for example 'equipment'). The
	built-site path mirrors this layout under assets/svg/<category>/<name>.svg.

	Args:
		assets_dir: absolute path to the assets/ directory.
		svg_files: list of Path objects for every assets/**/*.svg file.

	Returns:
		dict mapping asset_name -> category directory name.
	"""
	category_map = {}
	assets_root = Path(assets_dir)
	for svg_path in svg_files:
		# Relative path under assets/, e.g. equipment/bottle.svg.
		rel = svg_path.relative_to(assets_root)
		# The first path component is the category directory.
		category = rel.parts[0]
		stem = svg_path.stem
		# The manifest keys by bare asset_name (stem); a stem reused across two
		# categories would map one URL onto the other's key. Fail loudly rather
		# than silently overwriting, since the registry also keys by bare stem.
		if stem in category_map and category_map[stem] != category:
			raise RuntimeError(
				f"cross-category SVG basename collision: '{stem}.svg' exists under "
				f"both assets/{category_map[stem]}/ and assets/{category}/. "
				"Asset basenames must be unique across categories."
			)
		category_map[stem] = category
	return category_map


def _visual_state_needs_dom_svg(vs_def: dict) -> bool:
	"""Return True when a single visual_state declaration needs internal SVG DOM.

	requires_dom_svg means INTERNAL SVG access, not "has any visual state". A
	visual_state needs internal access when it:
	  - carries a 'fill_height(' formula (clips an internal liquid region), or
	  - is a 'composite' kind whose 'composite' list is NON-EMPTY (real internal
	    subpart layers to target), or
	  - is an UNKNOWN/unrecognized kind (SAFE BIAS: default TRUE so a future
	    internal-SVG effect is never silently rendered as an opaque <img>).

	A generic 'overlay' (text/label layer over the asset), an EMPTY composite
	('composite: []', no internal subparts), and a whole-asset 'svg' swap are all
	img-eligible on their own and return False.

	See the module-level signal notes; the forward-looking render_effect / target
	/ anchor vocabulary is intentionally not consulted (not emitted yet,
	closure-gated).

	Args:
		vs_def: one visual_states entry mapping from object YAML.

	Returns:
		True if this visual_state forces injected SVG DOM rendering.
	"""
	# A fill_height(...) formula clips/animates an internal liquid region, so the
	# formula text is an internal-access signal regardless of kind.
	formula = vs_def.get("formula", "")
	if isinstance(formula, str) and DOM_SVG_FILL_HEIGHT_TOKEN in formula:
		return True

	kind = vs_def.get("kind")

	# A composite kind needs internal access only when it actually layers internal
	# subparts. An empty 'composite: []' targets nothing internal and is
	# img-eligible.
	if kind == "composite":
		composite = vs_def.get("composite", [])
		# Non-empty composite list => real internal subpart layers => DOM SVG.
		return isinstance(composite, list) and len(composite) > 0

	# Known img-eligible kinds (overlay, svg) never need internal access alone.
	if kind in DOM_SVG_IMG_ELIGIBLE_KINDS:
		return False

	# SAFE BIAS: an unknown/unrecognized kind could target internals; default
	# TRUE so a real material/internal effect is never silently img-rendered.
	return True


def _object_needs_dom_svg(obj_data: dict) -> bool:
	"""Return True when an object's declaration requires internal SVG DOM render.

	requires_dom_svg means the object needs access to the INTERNAL structure of
	its SVG, not merely that it has a visual state. Derived from DECLARATIONS that
	exist today, never from current material/visual state: an empty
	material_container still declares the capability, so it stays DOM-SVG-required.
	Triggers (all live signals):
	  - a capability of 'material_container' or 'structured_surface';
	  - a visual_states entry carrying a 'fill_height(' formula;
	  - a visual_states entry of kind 'composite' with a NON-EMPTY composite list;
	  - a visual_states entry of an unknown kind (SAFE BIAS default-true).
	A generic 'overlay' (label over the asset), an empty 'composite: []', and a
	whole-asset 'svg' swap are img-eligible and do NOT trigger DOM SVG.

	Args:
		obj_data: parsed object YAML mapping.

	Returns:
		True if any declared capability needs injected SVG DOM.
	"""
	# Capability signal: material_container / structured_surface objects expose an
	# internal liquid region or generated subpart geometry that must be DOM-reachable.
	capabilities = obj_data.get("capabilities", [])
	if isinstance(capabilities, list):
		for capability in capabilities:
			if capability in DOM_SVG_CAPABILITY_TOKENS:
				return True

	# Visual-state signal: composite/overlay kind, or a fill_height formula.
	visual_states = obj_data.get("visual_states", {})
	if isinstance(visual_states, dict):
		for vs_def in visual_states.values():
			if isinstance(vs_def, dict) and _visual_state_needs_dom_svg(vs_def):
				return True

	return False


def _object_asset_names(obj_data: dict) -> set:
	"""Collect every asset_name an object references.

	An object may name a primary asset via the top-level 'asset' field and one or
	more asset_name values inside visual_states svg/composite cases. Every such
	asset inherits the object's DOM-SVG requirement.

	Args:
		obj_data: parsed object YAML mapping.

	Returns:
		set of asset_name strings referenced by this object.
	"""
	asset_names = set()

	# Top-level primary asset override.
	primary = obj_data.get("asset")
	if isinstance(primary, str) and primary:
		asset_names.add(primary)

	# Scan visual_states cases for asset_name outputs (handles nested outputs by
	# walking the YAML structure generically).
	visual_states = obj_data.get("visual_states", {})
	if isinstance(visual_states, dict):
		_collect_asset_names_recursive(visual_states, asset_names)

	return asset_names


def _collect_asset_names_recursive(node, asset_names: set):
	"""Walk a nested YAML node and collect every 'asset_name' string value."""
	if isinstance(node, dict):
		for key, value in node.items():
			if key == "asset_name" and isinstance(value, str) and value:
				asset_names.add(value)
			else:
				_collect_asset_names_recursive(value, asset_names)
	elif isinstance(node, list):
		for item in node:
			_collect_asset_names_recursive(item, asset_names)


def _derive_requires_dom_svg(repo_root: str, asset_keys: set) -> dict:
	"""Derive requires_dom_svg for every asset from object declarations.

	Reads every content/objects/**/*.yaml object declaration. For each object
	that requires internal SVG DOM rendering, marks every asset it references as
	DOM-SVG-required. An asset not referenced by any DOM-SVG-required object is
	static (img-renderable).

	Derivation is from DECLARATIONS only, computed once at generation time. It is
	never authored and never read from runtime material/visual state.

	Args:
		repo_root: absolute repo root path.
		asset_keys: set of shipped asset_name keys to report on.

	Returns:
		dict mapping asset_name -> bool requires_dom_svg, for every asset_key.
	"""
	objects_dir = Path(repo_root) / "content" / "objects"

	# Start every shipped asset as static; promote to DOM-SVG-required when any
	# object referencing it declares an internal-SVG need.
	requires = {key: False for key in asset_keys}

	if not objects_dir.exists():
		raise RuntimeError(f"object declarations dir not found: {objects_dir}")

	for yaml_path in sorted(objects_dir.rglob("*.yaml")):
		with open(yaml_path, "r") as f:
			obj_data = yaml.safe_load(f)
		if not isinstance(obj_data, dict):
			continue
		if not _object_needs_dom_svg(obj_data):
			continue
		# This object needs DOM SVG; every asset it references inherits that.
		for asset_name in _object_asset_names(obj_data):
			if asset_name in requires:
				requires[asset_name] = True

	return requires


def _emit_ts_manifest(output_file: str, asset_keys: set,
		category_map: dict, requires_dom_svg: dict):
	"""Emit the SVG manifest as a TypeScript module.

	Emits SVG_MANIFEST mapping each asset_name to a per-asset entry with the
	relative built-site path and the derived requires_dom_svg boolean. Paths use
	the assets/svg/<category>/<name>.svg layout with NO leading slash so they
	resolve under a GitHub Pages project subpath.

	Args:
		output_file: absolute output path for svg_manifest.ts.
		asset_keys: set of shipped asset_name keys.
		category_map: asset_name -> category directory name.
		requires_dom_svg: asset_name -> derived bool.
	"""
	lines = []
	lines.append("// Auto-generated SVG manifest. Do not edit.")
	lines.append("// Generated by pipeline/gen_svg_manifest.py")
	lines.append("//")
	lines.append("// Maps each asset_name to its relative built-site SVG path and a")
	lines.append("// generation-time derived requires_dom_svg flag. Paths have no leading")
	lines.append("// slash so they resolve under the GitHub Pages project subpath.")
	lines.append("")
	lines.append("export interface SvgManifestEntry {")
	lines.append("  path: string;")
	lines.append("  requires_dom_svg: boolean;")
	lines.append("}")
	lines.append("")
	lines.append("export const SVG_MANIFEST: Record<string, SvgManifestEntry> = {")

	for key in sorted(asset_keys):
		category = category_map[key]
		# Relative path under the built site, mirroring the assets/ layout.
		rel_path = f"assets/svg/{category}/{key}.svg"
		needs_dom = "true" if requires_dom_svg[key] else "false"
		lines.append(f'  "{key}": {{ path: "{rel_path}", requires_dom_svg: {needs_dom} }},')

	lines.append("};")
	lines.append("")

	with open(output_file, "w") as f:
		f.write("\n".join(lines))


def _get_repo_root() -> str:
	"""Get repository root via git."""
	try:
		result = subprocess.run(
			["git", "rev-parse", "--show-toplevel"],
			capture_output=True,
			text=True,
			timeout=5,
		)
		if result.returncode == 0:
			return result.stdout.strip()
	except (OSError, subprocess.TimeoutExpired, subprocess.SubprocessError):
		pass

	raise RuntimeError("Could not determine repo root via git")


if __name__ == "__main__":
	main()
