#!/usr/bin/env python3
"""Census proposed liquid-color families in anchored equipment SVGs.

This is deliberately a proposal tool. It measures the paired liquid anchors,
then identifies non-neutral paint inside their shared geometry. Later work
assigns semantic ids; it must not reuse these paint guesses as identity.
"""

# Standard Library
import copy
import io
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

# PIP3 modules
import cairosvg
import lxml.etree
import PIL.Image
import PIL.ImageDraw

from validation.svg.asset_registry import build_svg_asset_registry


EXPECTED_DONOR_NEUTRAL_PALETTE = frozenset({
	"#333", "#55919f", "#90bac4", "#9d869a", "#a9cad2", "#b6d2d9",
	"#b9d6dd", "#c0b0ba", "#c4c4c4", "#dde9ec", "#e3eef1", "#e7e0e3",
	"#ebebeb", "#f6fafb", "#f7f4f4", "#fff",
})
DONOR_VARIANTS = (
	"bottle_pink.svg",
	"bottle_orange.svg",
	"bottle_green.svg",
)
EXPECTED_ANCHORED_FLEET = (
	"aspirating_pipette.svg",
	"biohazard_decant.svg",
	"biohazard_decant_bin.svg",
	"bottle.svg",
	"bottle_green.svg",
	"bottle_medium_pink.svg",
	"bottle_orange.svg",
	"bottle_pink.svg",
	"electrophoresis_tank_inner_chamber.svg",
	"electrophoresis_tank_outer_chamber.svg",
	"ethanol_spray.svg",
	"falcon_15ml.svg",
	"falcon_50ml.svg",
	"hemocytometer_slide.svg",
	"microtube.svg",
	"mtt_vial.svg",
	"multichannel_pipette.svg",
	"p10_micropipette_empty.svg",
	"p10_micropipette_filled.svg",
	"p200_micropipette_empty.svg",
	"p200_micropipette_filled.svg",
	"protein_ladder_tube.svg",
	"protein_sample_tube.svg",
	"running_buffer_1x_carboy.svg",
	"serological_pipette.svg",
	"staining_tray_empty.svg",
	"t75_flask.svg",
	"t75_flask_servier.svg",
	"t75_flask_v2.svg",
	"t75_flask_v3.svg",
	"t75_flask_v4.svg",
	"t75_flask_v5.svg",
	"waste_container.svg",
)
STRUCTURED_EVIDENCE = (
	"96well_pcr_plate.svg",
	"gel_cassette_empty.svg",
	"tube_rack.svg",
)
HIGHLIGHT_COLOR = "#ff00a8"
THUMBNAIL_SIZE = 180
DRAWABLE_TAGS = frozenset({"path", "rect", "circle", "ellipse", "polygon", "polyline"})


@dataclass(frozen=True)
class Bbox:
	"""A measured SVG coordinate rectangle."""
	min_x: float
	min_y: float
	max_x: float
	max_y: float


@dataclass(frozen=True)
class Paint:
	"""The visible paint attributes used for one drawable element."""
	fill: str
	stroke: str
	fill_opacity: str
	stroke_opacity: str


@dataclass(frozen=True)
class Candidate:
	"""A single drawable element proposed as part of a liquid band."""
	element: lxml.etree._Element
	index: int
	paint: Paint
	candidate_paints: tuple[str, ...]
	bbox: Bbox
	transform: bool


@dataclass(frozen=True)
class PhaseProposal:
	"""A document-order phase proposal for one drawable path."""
	index: int
	phase: str
	candidate: bool
	paint: Paint


@dataclass(frozen=True)
class CensusRecord:
	"""All durable reporting fields for one anchored asset."""
	asset: str
	fills: tuple[str, ...]
	shared_neutral_paints: tuple[str, ...]
	candidate_paints: tuple[str, ...]
	candidates: tuple[Candidate, ...]
	merge_estimate: int
	classification: str
	phase_records: tuple[PhaseProposal, ...]
	evidence: Path
	anchor_bounds: Bbox
	clip_bounds: Bbox
	paired_bounds: Bbox


@dataclass(frozen=True)
class StructuredRecord:
	"""Source-only visual evidence for a non-anchored structured asset."""
	asset: str
	fills: tuple[str, ...]
	evidence: Path


#============================================
def repo_root() -> Path:
	"""Return the repository root resolved by git."""
	result = subprocess.run(
		["git", "rev-parse", "--show-toplevel"], capture_output=True,
		text=True, check=True,
	)
	root = Path(result.stdout.strip())
	return root


#============================================
def local_tag(elem: lxml.etree._Element) -> str:
	"""Return an element tag without its namespace."""
	if not isinstance(elem.tag, str):
		return ""
	tag = lxml.etree.QName(elem).localname.lower()
	return tag


#============================================
def normalized_hex(value: str) -> str | None:
	"""Normalize CSS hexadecimal colors to six-digit lowercase form."""
	if not value.startswith("#"):
		return None
	if len(value) == 4:
		result = "#" + "".join(char * 2 for char in value[1:])
		return result
	if len(value) == 7:
		return value
	return None


#============================================
def canonical_paint(value: str) -> str:
	"""Return a comparable paint spelling without inventing CSS conversions."""
	normalized = normalized_hex(value)
	if normalized is not None:
		return normalized
	return value


#============================================
def normalized_expected_donor_neutral_palette() -> frozenset[str]:
	"""Return the plan-evidenced donor intersection used only for drift detection."""
	palette = frozenset(canonical_paint(value) for value in EXPECTED_DONOR_NEUTRAL_PALETTE)
	return palette


#============================================
def paint_values(elem: lxml.etree._Element) -> Paint:
	"""Return normalized visible paint values used for census comparisons."""
	paint = Paint(
		fill=elem.get("fill", "black").lower(),
		stroke=elem.get("stroke", "none").lower(),
		fill_opacity=elem.get("fill-opacity", "1"),
		stroke_opacity=elem.get("stroke-opacity", "1"),
	)
	return paint


#============================================
def element_bbox(elem: lxml.etree._Element) -> Bbox | None:
	"""Measure one SVG shape with the repository normalizer geometry helper."""
	import normalize_svg_v3

	bbox = normalize_svg_v3.element_bbox(elem)
	if bbox is None or isinstance(bbox, str):
		return None
	result = Bbox(bbox.min_x, bbox.min_y, bbox.max_x, bbox.max_y)
	return result


#============================================
def intersection(left: Bbox, right: Bbox) -> Bbox | None:
	"""Return the shared rectangle of two bbox approximations."""
	result = Bbox(
		max(left.min_x, right.min_x), max(left.min_y, right.min_y),
		min(left.max_x, right.max_x), min(left.max_y, right.max_y),
	)
	if result.min_x >= result.max_x or result.min_y >= result.max_y:
		return None
	return result


#============================================
def union(boxes: list[Bbox]) -> Bbox:
	"""Return the enclosing rectangle for required measured geometry."""
	if not boxes:
		raise ValueError("anchor_liquid_clip has no measurable drawable children")
	result = Bbox(
		min(box.min_x for box in boxes), min(box.min_y for box in boxes),
		max(box.max_x for box in boxes), max(box.max_y for box in boxes),
	)
	return result


#============================================
def required_coordinate(elem: lxml.etree._Element, name: str, svg_path: Path) -> float:
	"""Read a required user-unit anchor coordinate and fail clearly if absent."""
	value = elem.get(name)
	if value is None:
		raise ValueError(f"Missing {name} on anchor_liquid_bounds: {svg_path}")
	try:
		result = float(value)
	except ValueError as error:
		raise ValueError(f"Invalid {name} on anchor_liquid_bounds: {svg_path}") from error
	return result


#============================================
def find_required_anchor(root: lxml.etree._Element, anchor_id: str, svg_path: Path) -> lxml.etree._Element:
	"""Find exactly one required anchor element."""
	matches = [elem for elem in root.iter() if elem.get("id") == anchor_id]
	if len(matches) != 1:
		raise ValueError(f"Expected exactly one {anchor_id}: {svg_path}")
	return matches[0]


#============================================
def anchor_bounds(root: lxml.etree._Element, svg_path: Path) -> Bbox:
	"""Read the required liquid-bounds rectangle without silent coordinates."""
	elem = find_required_anchor(root, "anchor_liquid_bounds", svg_path)
	if local_tag(elem) != "rect":
		raise ValueError(f"anchor_liquid_bounds must be a rect: {svg_path}")
	if uses_transform(elem):
		raise ValueError(f"anchor_liquid_bounds has unflattened transform geometry: {svg_path}")
	x = required_coordinate(elem, "x", svg_path)
	y = required_coordinate(elem, "y", svg_path)
	width = required_coordinate(elem, "width", svg_path)
	height = required_coordinate(elem, "height", svg_path)
	if width <= 0 or height <= 0:
		raise ValueError(f"anchor_liquid_bounds must have positive dimensions: {svg_path}")
	bounds = Bbox(x, y, x + width, y + height)
	return bounds


#============================================
def uses_transform(elem: lxml.etree._Element) -> bool:
	"""Return whether an element or ancestor has unflattened transform geometry."""
	for ancestor in [elem, *elem.iterancestors()]:
		if ancestor.get("transform") is not None:
			return True
	return False


#============================================
def clip_geometry_bounds(root: lxml.etree._Element, svg_path: Path) -> Bbox:
	"""Measure drawable child geometry of the required liquid clip anchor."""
	clip = find_required_anchor(root, "anchor_liquid_clip", svg_path)
	if local_tag(clip) != "clippath":
		raise ValueError(f"anchor_liquid_clip must be a clipPath: {svg_path}")
	if clip.get("clipPathUnits", "userSpaceOnUse") != "userSpaceOnUse":
		raise ValueError(f"anchor_liquid_clip must use userSpaceOnUse coordinates: {svg_path}")
	boxes = []
	for child in clip.iterdescendants():
		if local_tag(child) not in DRAWABLE_TAGS:
			continue
		if uses_transform(child):
			raise ValueError(f"anchor_liquid_clip has unflattened transform geometry: {svg_path}")
		# Clip geometry can be display="none" because it is a resource, not art.
		measure_child = copy.deepcopy(child)
		measure_child.attrib.pop("display", None)
		# The normalizer quite correctly ignores a fully transparent drawing, but a
		# clip resource has geometry even when its paint is deliberately none.
		measure_child.set("fill", "#000")
		measure_child.set("stroke", "none")
		bbox = element_bbox(measure_child)
		if bbox is None:
			raise ValueError(f"Unmeasurable anchor_liquid_clip child geometry: {svg_path}")
		boxes.append(bbox)
	bounds = union(boxes)
	return bounds


#============================================
def paired_anchor_bounds(root: lxml.etree._Element, svg_path: Path) -> tuple[Bbox, Bbox, Bbox]:
	"""Measure and validate the paired clip/bounds anchor approximation."""
	bounds = anchor_bounds(root, svg_path)
	clip_bounds = clip_geometry_bounds(root, svg_path)
	paired = intersection(bounds, clip_bounds)
	if paired is None:
		raise ValueError(f"anchor_liquid_clip and anchor_liquid_bounds do not overlap: {svg_path}")
	return bounds, clip_bounds, paired


#============================================
def drawable_elements(root: lxml.etree._Element) -> list[lxml.etree._Element]:
	"""Return document-order artwork shapes, excluding anchors and definitions."""
	drawables = []
	for elem in root.iter():
		if local_tag(elem) not in DRAWABLE_TAGS:
			continue
		if elem.get("id", "").startswith("anchor_"):
			continue
		if any(local_tag(parent) in {"defs", "clippath"} for parent in elem.iterancestors()):
			continue
		drawables.append(elem)
	return drawables


#============================================
def visible_paints(drawables: list[lxml.etree._Element]) -> frozenset[str]:
	"""Return normalized visible fill and stroke paints, excluding transparent values."""
	paints = set()
	for elem in drawables:
		paint = paint_values(elem)
		for value in (paint.fill, paint.stroke):
			if value not in {"none", "transparent"}:
				paints.add(canonical_paint(value))
	result = frozenset(paints)
	return result


#============================================
def derived_donor_neutral_palette(assets_dir: Path) -> frozenset[str]:
	"""Derive the shared neutral palette from the three approved bottle donors."""
	registry = build_svg_asset_registry(assets_dir)
	donor_paths = [registry.asset_path(Path(name).stem) for name in DONOR_VARIANTS]
	missing = [path.name for path in donor_paths if not path.is_file()]
	if missing:
		raise FileNotFoundError(f"Missing required donor asset(s): {', '.join(missing)}")
	paint_sets = []
	for donor_path in donor_paths:
		root = lxml.etree.parse(str(donor_path)).getroot()
		paint_sets.append(visible_paints(drawable_elements(root)))
	palette = frozenset.intersection(*paint_sets)
	expected = normalized_expected_donor_neutral_palette()
	if palette != expected:
		difference = sorted(palette.symmetric_difference(expected))
		raise ValueError(
			"Derived donor neutral palette differs from plan-evidenced palette; "
			f"difference: {', '.join(difference)}"
		)
	return palette


#============================================
def expected_anchored_paths(assets_dir: Path) -> list[Path]:
	"""Validate the fixed M1 fleet and return its deterministic asset paths."""
	registry = build_svg_asset_registry(assets_dir)
	expected = set(EXPECTED_ANCHORED_FLEET)
	missing_files = sorted(
		name for name in expected if Path(name).stem not in registry.asset_names
	)
	anchor_deficient = []
	for name in sorted(expected - set(missing_files)):
		text = registry.asset_path(Path(name).stem).read_text(encoding="utf-8")
		missing_anchors = [
			anchor for anchor in ("anchor_liquid_clip", "anchor_liquid_bounds")
			if anchor not in text
		]
		if missing_anchors:
			anchor_deficient.append(f"{name} ({', '.join(missing_anchors)})")
	discovered = set()
	for entry in registry.entries:
		svg_path = entry.source_path
		text = svg_path.read_text(encoding="utf-8")
		if "anchor_liquid_clip" in text and "anchor_liquid_bounds" in text:
			discovered.add(svg_path.name)
	unexpected = sorted(discovered - expected)
	missing_discovered = sorted(expected - discovered)
	if missing_files or anchor_deficient or unexpected or missing_discovered:
		details = []
		if missing_files:
			details.append(f"missing expected assets: {', '.join(missing_files)}")
		if anchor_deficient:
			details.append(f"anchor-deficient expected assets: {'; '.join(anchor_deficient)}")
		if unexpected:
			details.append(f"unexpected both-anchor assets: {', '.join(unexpected)}")
		if missing_discovered:
			details.append(f"expected assets absent from both-anchor discovery: {', '.join(missing_discovered)}")
		raise ValueError("Anchored M1 fleet inventory mismatch: " + " | ".join(details))
	return [registry.asset_path(Path(name).stem) for name in EXPECTED_ANCHORED_FLEET]


#============================================
def non_neutral_paints(paint: Paint, neutral_palette: frozenset[str]) -> tuple[str, ...]:
	"""Return every visible fill or stroke outside the shared neutral palette."""
	values = []
	for value in (paint.fill, paint.stroke):
		if value in {"none", "transparent"}:
			continue
		canonical = canonical_paint(value)
		if canonical in neutral_palette:
			continue
		if canonical not in values:
			values.append(canonical)
	result = tuple(values)
	return result


#============================================
def center_in_bounds(bounds: Bbox, bbox: Bbox) -> bool:
	"""Return whether an element bbox center falls inside paired anchor bounds."""
	center_x = (bbox.min_x + bbox.max_x) / 2
	center_y = (bbox.min_y + bbox.max_y) / 2
	result = bounds.min_x <= center_x <= bounds.max_x and bounds.min_y <= center_y <= bounds.max_y
	return result


#============================================
def proposed_candidates(
	drawables: list[lxml.etree._Element], paired_bounds: Bbox,
	neutral_palette: frozenset[str],
) -> tuple[Candidate, ...]:
	"""Find non-neutral painted elements whose bbox centers are in paired bounds."""
	candidates = []
	for document_index, elem in enumerate(drawables, start=1):
		bbox = element_bbox(elem)
		if bbox is None or not center_in_bounds(paired_bounds, bbox):
			continue
		paint = paint_values(elem)
		candidate_paints = non_neutral_paints(paint, neutral_palette)
		if not candidate_paints:
			continue
		candidates.append(Candidate(
			element=elem, index=document_index, paint=paint,
			candidate_paints=candidate_paints, bbox=bbox, transform=uses_transform(elem),
		))
	result = tuple(candidates)
	return result


#============================================
def merge_estimate(candidates: tuple[Candidate, ...]) -> int:
	"""Estimate adjacent same-paint candidate joins for later human review."""
	joins = 0
	for left, right in zip(candidates, candidates[1:]):
		if right.index == left.index + 1 and left.paint == right.paint:
			joins += 1
	return joins


#============================================
def classification(candidates: tuple[Candidate, ...]) -> str:
	"""Classify proposal difficulty; no_liquid_drawn means no qualifying paint candidate, not no liquid art."""
	if not candidates:
		return "no_liquid_drawn"
	paints = {paint for candidate in candidates for paint in candidate.candidate_paints}
	if len(candidates) < 3 or len(paints) < 3:
		return "hand_art"
	if any(candidate.paint.fill == "none" or candidate.transform for candidate in candidates):
		return "hand_art"
	return "mechanical"


#============================================
def proposed_phases(drawables: list[lxml.etree._Element], candidates: tuple[Candidate, ...]) -> tuple[PhaseProposal, ...]:
	"""Assign a phase to every path; remain explicitly unresolved without a band."""
	candidate_indices = {candidate.index for candidate in candidates}
	if not candidate_indices:
		result = tuple(PhaseProposal(index, "unresolved", False, paint_values(elem)) for index, elem in enumerate(drawables, start=1))
		return result
	band_start = min(candidate_indices)
	band_end = max(candidate_indices)
	proposals = []
	for index, elem in enumerate(drawables, start=1):
		if index < band_start:
			phase = "back"
		elif index <= band_end:
			phase = "middle"
		else:
			phase = "front"
		proposals.append(PhaseProposal(index, phase, index in candidate_indices, paint_values(elem)))
	result = tuple(proposals)
	return result


#============================================
def build_isolation_svg(root: lxml.etree._Element, candidate: Candidate) -> bytes:
	"""Build one standalone SVG showing a proposed candidate in magenta."""
	isolation = lxml.etree.Element(root.tag, nsmap=root.nsmap)
	for key, value in root.attrib.items():
		isolation.set(key, value)
	for child in root:
		if local_tag(child) == "defs":
			isolation.append(copy.deepcopy(child))
	chosen = copy.deepcopy(candidate.element)
	chosen.set("fill", HIGHLIGHT_COLOR)
	chosen.set("fill-opacity", "1")
	chosen.set("stroke", HIGHLIGHT_COLOR)
	chosen.set("stroke-opacity", "1")
	isolation.append(chosen)
	data = lxml.etree.tostring(isolation, encoding="utf-8")
	return data


#============================================
def render_highlight_sheet(root: lxml.etree._Element, candidates: tuple[Candidate, ...], output_path: Path) -> None:
	"""Render source plus deterministic isolated-magenta candidate evidence tiles."""
	output_path.parent.mkdir(parents=True, exist_ok=True)
	root_data = lxml.etree.tostring(root, encoding="utf-8")
	tiles = [cairosvg.svg2png(bytestring=root_data, output_width=THUMBNAIL_SIZE, output_height=THUMBNAIL_SIZE)]
	for candidate in candidates:
		tiles.append(cairosvg.svg2png(
			bytestring=build_isolation_svg(root, candidate), output_width=THUMBNAIL_SIZE,
			output_height=THUMBNAIL_SIZE,
		))
	columns = 4
	rows = (len(tiles) + columns - 1) // columns
	sheet = PIL.Image.new("RGBA", (columns * THUMBNAIL_SIZE, rows * (THUMBNAIL_SIZE + 22)), "white")
	draw = PIL.ImageDraw.Draw(sheet)
	for index, tile_data in enumerate(tiles):
		tile = PIL.Image.open(io.BytesIO(tile_data)).convert("RGBA")
		x = (index % columns) * THUMBNAIL_SIZE
		y = (index // columns) * (THUMBNAIL_SIZE + 22)
		sheet.alpha_composite(tile, (x, y))
		label = "source" if index == 0 else f"path {candidates[index - 1].index}"
		draw.text((x + 4, y + THUMBNAIL_SIZE + 3), label, fill="black")
	sheet.convert("RGB").save(output_path)


#============================================
def shared_neutral_paints(
	drawables: list[lxml.etree._Element], neutral_palette: frozenset[str],
) -> tuple[str, ...]:
	"""Return visible fill/stroke paints shared by the derived donor intersection."""
	shared = set()
	for elem in drawables:
		paint = paint_values(elem)
		for value in (paint.fill, paint.stroke):
			if value in {"none", "transparent"}:
				continue
			canonical = canonical_paint(value)
			if canonical in neutral_palette:
				shared.add(canonical)
	result = tuple(sorted(shared))
	return result


#============================================
def census_asset(
	svg_path: Path, evidence_dir: Path, neutral_palette: frozenset[str],
) -> CensusRecord:
	"""Collect one anchored asset census record and render its proof sheet."""
	tree = lxml.etree.parse(str(svg_path))
	root = tree.getroot()
	bounds, clip_bounds, paired_bounds = paired_anchor_bounds(root, svg_path)
	drawables = drawable_elements(root)
	fills = tuple(sorted({paint_values(elem).fill for elem in drawables if paint_values(elem).fill != "none"}))
	candidates = proposed_candidates(drawables, paired_bounds, neutral_palette)
	candidate_paints = tuple(sorted({paint for candidate in candidates for paint in candidate.candidate_paints}))
	evidence_path = evidence_dir / f"{svg_path.stem}_highlight.png"
	render_highlight_sheet(root, candidates, evidence_path)
	record = CensusRecord(
		asset=svg_path.name, fills=fills,
		shared_neutral_paints=shared_neutral_paints(drawables, neutral_palette),
		candidate_paints=candidate_paints, candidates=candidates,
		merge_estimate=merge_estimate(candidates), classification=classification(candidates),
		phase_records=proposed_phases(drawables, candidates), evidence=evidence_path,
		anchor_bounds=bounds, clip_bounds=clip_bounds, paired_bounds=paired_bounds,
	)
	return record


#============================================
def census_structured_asset(svg_path: Path, evidence_dir: Path) -> StructuredRecord:
	"""Render non-anchored structured evidence without inventing liquid geometry."""
	tree = lxml.etree.parse(str(svg_path))
	root = tree.getroot()
	drawables = drawable_elements(root)
	fills = tuple(sorted({paint_values(elem).fill for elem in drawables if paint_values(elem).fill != "none"}))
	evidence_path = evidence_dir / f"{svg_path.stem}_highlight.png"
	render_highlight_sheet(root, (), evidence_path)
	record = StructuredRecord(svg_path.name, fills, evidence_path)
	return record


#============================================
def bbox_text(bbox: Bbox) -> str:
	"""Format a bbox deterministically for the report."""
	result = ", ".join(f"{value:.1f}" for value in (bbox.min_x, bbox.min_y, bbox.max_x, bbox.max_y))
	return result


#============================================
def markdown_report(
	records: list[CensusRecord], structured_records: list[StructuredRecord], repo: Path,
	neutral_palette: frozenset[str],
) -> str:
	"""Build the durable M1 Markdown report."""
	counts = Counter(record.classification for record in records)
	lines = [
		"# Liquid asset census", "",
		"Generated by `tools/svg_liquid_census.py`. This is an M1 proposal census:",
		"paint clusters help assign later semantic ids, but they are not identity.", "",
		"## Method", "",
		"- The anchored fleet is the approved current-state inventory of 33 exact filenames.",
		"  Before processing, the tool confirms every expected file exists and contains both",
		"  required anchors, then rejects any unexpected or missing both-anchor asset.",
		"- Anchored assets carry both `anchor_liquid_clip` and `anchor_liquid_bounds`.",
		"  The tool measures every drawable child of the clip with",
		"  `normalize_svg_v3.element_bbox`, unions those child bboxes, and pairs that",
		"  result with the bounds-rectangle bbox by rectangular intersection.",
		"- Candidate membership uses the candidate drawable bbox center inside that paired",
		"  rectangle. This is deliberately a bbox-center approximation: it does not perform",
		"  a boolean path/clip intersection. Missing, incompatible, transformed, or",
		"  non-overlapping anchors fail the census loudly.",
		"- Candidate paint means a fill or stroke inside the paired anchor rectangle that is",
		"  outside the derived shared donor neutral palette. There is no saturation filter.",
		"- The shared neutral palette is the exact intersection of normalized visible fill and",
		"  stroke paints from the donor files `bottle_pink.svg`, `bottle_orange.svg`, and",
		"  `bottle_green.svg` (excluding `none` and `transparent`).",
		f"  Derived intersection: `{', '.join(sorted(neutral_palette))}`.",
		"  The tool fails if that runtime-derived intersection differs from the plan-evidenced palette.",
		"  As recovered-candidate evidence, `bottle_pink.svg` includes the",
		"  expected pink fill/stroke ramp: `#88016c, #8f0164, #95207d, #b64392, #dba6cb, #eacbe1`.",
		"- The first and last candidates define a proposed liquid band. Without a candidate",
		"  band, every drawable path is explicitly `unresolved`; the census does not invent",
		"  back/middle/front certainty. Candidate clustering remains proposal-only.",
		"- Merge estimate counts adjacent candidates with identical fill, stroke, and opacity.",
		"- Highlight sheets show the source plus each candidate in isolation; they are review",
		"  evidence under `test-results/`, not committed documentation.", "",
		"## Totals", "",
		f"- Anchored assets classified: {len(records)}",
		f"- Mechanical proposals: {counts['mechanical']}",
		f"- Hand-art proposals: {counts['hand_art']}",
		f"- No-liquid-drawn proposals (no qualifying paint candidate): {counts['no_liquid_drawn']}",
		"  This is not proof that no liquid art exists.",
		f"- Structured evidence assets rendered: {len(structured_records)}", "",
		"## Anchored fleet", "",
		"| Asset | Distinct fills | Neutral-shared paints | Candidate paints in paired bounds | Candidate paths | Merge estimate | Classification | Evidence |",
		"| --- | --- | --- | --- | ---: | ---: | --- | --- |",
	]
	for record in records:
		fills = ", ".join(record.fills)
		shared = ", ".join(record.shared_neutral_paints) or "none"
		candidates = ", ".join(record.candidate_paints) or "none"
		evidence = record.evidence.relative_to(repo)
		lines.append(
			f"| `{record.asset}` | `{fills}` | `{shared}` | `{candidates}` | {len(record.candidates)} | "
			f"{record.merge_estimate} | {record.classification} | `{evidence}` |"
		)
	lines.extend([
		"", "## Structured-object evidence", "",
		"These plate, gel, and rack assets are not counted in the anchored fleet. They have no",
		"`anchor_liquid_clip` classification surface, so the census deliberately makes no liquid",
		"proposal. Their source-only sheets are the M8 visual evidence for the later structured",
		"subpart decision.", "",
		"| Asset | Distinct fills | Liquid proposal | Evidence |",
		"| --- | --- | --- | --- |",
	])
	for record in structured_records:
		fills = ", ".join(record.fills)
		evidence = record.evidence.relative_to(repo)
		lines.append(f"| `{record.asset}` | `{fills}` | no anchor; none | `{evidence}` |")
	lines.extend(["", "## Candidate detail", ""])
	for record in records:
		lines.extend([
			f"### `{record.asset}`", "",
			f"Anchor bounds bbox: `{bbox_text(record.anchor_bounds)}`; clip-child bbox: `{bbox_text(record.clip_bounds)}`; paired bbox: `{bbox_text(record.paired_bounds)}`.",
			"",
		])
		if record.candidates:
			lines.extend([
				"| Document path | Proposed phase | Candidate paints | Fill | Stroke | Bbox |",
				"| ---: | --- | --- | --- | --- | --- |",
			])
			for candidate in record.candidates:
				candidate_paints = ", ".join(candidate.candidate_paints)
				lines.append(
					f"| {candidate.index} | middle | `{candidate_paints}` | `{candidate.paint.fill}` | "
					f"`{candidate.paint.stroke}` | `{bbox_text(candidate.bbox)}` |"
				)
			lines.extend(["", "Phase proposal for every drawable path:", ""])
		else:
			lines.extend([
				"No qualifying non-neutral painted element has its bbox center in the paired anchor bounds.",
				"Every phase is unresolved because there is no candidate liquid band from which to infer document-order phases.",
				"",
			])
		lines.extend([
			"| Document path | Phase | Candidate | Fill | Stroke |",
			"| ---: | --- | --- | --- | --- |",
		])
		for proposal in record.phase_records:
			candidate_mark = "yes" if proposal.candidate else "no"
			lines.append(
				f"| {proposal.index} | {proposal.phase} | {candidate_mark} | "
				f"`{proposal.paint.fill}` | `{proposal.paint.stroke}` |"
			)
		lines.append("")
	report = "\n".join(lines) + "\n"
	return report


#============================================
def main() -> None:
	"""Run the M1 anchored-fleet census and write evidence/report artifacts."""
	repo = repo_root()
	sys.path.insert(0, str(repo / "tools"))
	assets_dir = repo / "assets" / "equipment"
	evidence_dir = repo / "test-results" / "svg_liquid_census"
	report_path = repo / "docs" / "active_plans" / "audits" / "liquid_asset_census.md"
	anchored = expected_anchored_paths(assets_dir)
	neutral_palette = derived_donor_neutral_palette(assets_dir)
	registry = build_svg_asset_registry(assets_dir)
	structured_paths = [registry.asset_path(Path(name).stem) for name in STRUCTURED_EVIDENCE]
	missing_structured = [path for path in structured_paths if not path.is_file()]
	if missing_structured:
		missing = ", ".join(str(path.relative_to(repo)) for path in missing_structured)
		raise FileNotFoundError(f"Missing required structured evidence asset(s): {missing}")
	records = [census_asset(svg_path, evidence_dir, neutral_palette) for svg_path in anchored]
	structured_records = [census_structured_asset(path, evidence_dir) for path in structured_paths]
	report_path.parent.mkdir(parents=True, exist_ok=True)
	report_path.write_text(
		markdown_report(records, structured_records, repo, neutral_palette), encoding="utf-8",
	)
	no_liquid = sum(record.classification == "no_liquid_drawn" for record in records)
	print(f"Anchored assets: {len(records)}")
	print(f"No-liquid-drawn proposals (no qualifying paint candidate): {no_liquid}")
	print("This is not proof that no liquid art exists.")
	print(f"Report: {report_path.relative_to(repo)}")
	print(f"Evidence: {evidence_dir.relative_to(repo)}")


if __name__ == "__main__":
	main()
