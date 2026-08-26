"""Tests for the focused SVG normalizer modules."""

import pathlib
import lxml.etree
import pytest
import re
import tools.svg_normalizer.cli
import tools.svg_normalizer.document
import tools.svg_normalizer.geometry
import tools.svg_normalizer.model
import tools.svg_normalizer.shadows
import tools.svg_normalizer.workflow

SVG_NS = tools.svg_normalizer.model.SVG_NS


#============================================
def _write_svg(path: pathlib.Path, body: str) -> None:
	"""Write a minimal SVG wrapper around body to path."""
	path.write_text(
		f'<svg xmlns="{SVG_NS}" viewBox="0 0 100 100">\n{body}\n</svg>\n',
		encoding="utf-8",
	)


#============================================
def _write_raw_svg(path: pathlib.Path, raw: str) -> None:
	"""Write raw SVG text (no wrapper) to path."""
	path.write_text(raw, encoding="utf-8")



# Floor-shadow removal
#
# Test fixtures use a synthetic asset pattern: a tall object path (the "real"
# object) plus a wide-flat ellipse in the bottom band explicitly marked as an
# editorial floor shadow.
# The real object occupies the upper region; the shadow sits in the lowest ~20%
# and is visually much wider than it is tall.
#
# Detection function: detect_floor_shadow_candidates (pure, testable).
# Wiring: normalize_svg_file with remove_floor_shadow=True deletes before the
# single bbox pass; flag False (default) is a no-op.
# Dry-run: _shadow_dry_run_report reports without deleting (tested via the
# detection function directly, since _shadow_dry_run_report is a CLI helper).
#============================================


def _make_shadow_svg(real_body: str, shadow_body: str) -> str:
	"""Compose a minimal SVG with a real-object path and a shadow path.

	Both bodies are raw element strings (already <path> elements).
	The SVG viewBox is large enough to contain both.

	Args:
		real_body: The <path ...> string for the real object.
		shadow_body: The <path ...> string for the floor shadow.

	Returns:
		Complete SVG text string.
	"""
	svg_text = (
		f'<svg xmlns="{SVG_NS}" viewBox="0 0 200 200">'
		f'{real_body}'
		f'{shadow_body}'
		f'</svg>'
	)
	return svg_text


# A tall rect representing the "real" object (upper region, 20x80).
_REAL_OBJECT_PATH = (
	'<path d="M 80 10 L 100 10 L 100 90 L 80 90 Z" fill="#333"/>'
)

# A wide-flat low-opacity grey ellipse in the bottom band (y=160..175, w=160, h=15).
# width/height = 160/15 ~ 10.7 >> 3.0, center_y=167.5 > 200*0.8=160 -> bottom band.
# The explicit semantic marker, not its opacity or colour, authorizes removal.
_SHADOW_PATH_OPACITY = (
	'<path d="M 20 160 A 80 7.5 0 1 0 180 160 A 80 7.5 0 1 0 20 160 Z"'
	' fill="#888" fill-opacity="0.3" data-editorial-floor-shadow="true"/>'
)

# A wide-flat shadow may use any visual treatment once it has the exact marker.
_SHADOW_PATH_MARKED = (
	'<path d="M 20 160 A 80 7.5 0 1 0 180 160 A 80 7.5 0 1 0 20 160 Z"'
	' id="floor-shadow-ellipse" fill="#4c97b1" data-editorial-floor-shadow="true"/>'
)

# A visually shadow-like bottom path that is not semantically a shadow.
_UNMARKED_BASE_PATH = (
	'<path d="M 20 160 A 80 7.5 0 1 0 180 160 A 80 7.5 0 1 0 20 160 Z"'
	' id="floor_shadow_ellipse" fill="#808080" fill-opacity="0.3"/>'
)


def _parse_svg_root(svg_text: str) -> "lxml.etree._Element":
	"""Parse SVG text and return the root element."""
	return lxml.etree.fromstring(svg_text.encode("utf-8"))


#============================================
# Detection-function unit tests (pure, no file I/O)
#============================================

@pytest.mark.parametrize("shadow_path", [_SHADOW_PATH_OPACITY, _SHADOW_PATH_MARKED])
def test_detect_explicitly_marked_shadow_candidate_found(shadow_path: str) -> None:
	"""detect_floor_shadow_candidates finds the wide-flat bottom shadow element.

	The exact data attribute, not incidental presentation values, is the sole
	removal signal.
	"""
	svg_text = _make_shadow_svg(_REAL_OBJECT_PATH, shadow_path)
	root = _parse_svg_root(svg_text)
	# Compute overall bbox from the two paths.
	overall_bbox = tools.svg_normalizer.geometry.compute_bbox(root)
	candidates = tools.svg_normalizer.shadows.detect_floor_shadow_candidates(root, overall_bbox)
	assert len(candidates) == 1
	assert candidates[0].signal == "explicit_marker"


def test_detect_no_false_positive_for_unmarked_base_geometry() -> None:
	"""A low-opacity grey bottom plinth is retained without the exact marker.

	This reproduces the pre-repair audit failure: grey, low, wide base geometry
	must never be deleted based on visual resemblance to a floor shadow.
	"""
	svg_text = _make_shadow_svg(_REAL_OBJECT_PATH, _UNMARKED_BASE_PATH)
	root = _parse_svg_root(svg_text)
	overall_bbox = tools.svg_normalizer.geometry.compute_bbox(root)
	candidates = tools.svg_normalizer.shadows.detect_floor_shadow_candidates(root, overall_bbox)
	assert candidates == []


def test_detect_no_candidate_when_not_bottom_band() -> None:
	"""An element in the top half is not a floor-shadow candidate even if wide-flat.

	The shadow shape is moved to y=10..25 (top region): its center_y is well
	above the bottom-band threshold.
	"""
	# Wide-flat marked path at the TOP (y=10..25, center_y=17.5).
	top_shadow = (
		'<path d="M 20 10 A 80 7.5 0 1 0 180 10 A 80 7.5 0 1 0 20 10 Z"'
		' fill="#888" data-editorial-floor-shadow="true"/>'
	)
	svg_text = _make_shadow_svg(_REAL_OBJECT_PATH, top_shadow)
	root = _parse_svg_root(svg_text)
	overall_bbox = tools.svg_normalizer.geometry.compute_bbox(root)
	candidates = tools.svg_normalizer.shadows.detect_floor_shadow_candidates(root, overall_bbox)
	assert len(candidates) == 0, "wide-flat top element should not be a shadow candidate"


def test_detect_no_candidate_when_not_wide_flat() -> None:
	"""A squarish marked bottom element is not a floor-shadow candidate.

	A square-ish path (aspect ~1.0) in the bottom band with the exact marker
	still fails the wide-flat criterion.
	"""
	# A square-ish marked path at the bottom (w=20, h=15, aspect=1.3 < 3).
	squarish_bottom = (
		'<path d="M 85 160 L 105 160 L 105 175 L 85 175 Z"'
		' fill="#888" data-editorial-floor-shadow="true"/>'
	)
	svg_text = _make_shadow_svg(_REAL_OBJECT_PATH, squarish_bottom)
	root = _parse_svg_root(svg_text)
	overall_bbox = tools.svg_normalizer.geometry.compute_bbox(root)
	candidates = tools.svg_normalizer.shadows.detect_floor_shadow_candidates(root, overall_bbox)
	assert len(candidates) == 0, "non-wide-flat bottom element should not be a shadow candidate"


#============================================
# Explicit-marker boundary tests
#============================================

@pytest.mark.parametrize("marker_value", ["True", "1", "yes", " false ", ""], ids=[
	"case_variant", "numeric", "word", "whitespace", "empty",
])
def test_requires_exact_explicit_marker_value(marker_value: str) -> None:
	"""Only the exact allowlisted marker value may authorize removal."""
	svg_text = (
		f'<svg xmlns="{SVG_NS}" viewBox="0 0 200 200">'
		+ _REAL_OBJECT_PATH
		+ '<path d="M 20 160 A 80 7.5 0 1 0 180 160 A 80 7.5 0 1 0 20 160 Z"'
		f' fill="#808080" fill-opacity="0.2" data-editorial-floor-shadow="{marker_value}"/>'
		'</svg>'
	)
	root = _parse_svg_root(svg_text)
	overall_bbox = tools.svg_normalizer.geometry.compute_bbox(root)
	candidates = tools.svg_normalizer.shadows.detect_floor_shadow_candidates(root, overall_bbox)
	assert candidates == []


#============================================
# normalize_svg_file integration tests (flag-off vs flag-on)
#============================================

def test_flag_off_retains_shadow(tmp_path: pathlib.Path) -> None:
	"""With remove_floor_shadow=False (default), the shadow element is NOT removed.

	The viewBox must include the shadow's geometry (bbox includes the bottom band).
	"""
	svg_text = _make_shadow_svg(_REAL_OBJECT_PATH, _SHADOW_PATH_OPACITY)
	svg_in = tmp_path / "shadow_off.svg"
	svg_out = tmp_path / "shadow_off.out.svg"
	svg_in.write_text(svg_text, encoding="utf-8")

	# Default: remove_floor_shadow=False.
	result = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out, padding=0.0)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	# With shadow retained, the bbox must include the shadow region (min_y ~ 152.5
	# because the arc bottom extends past y=160).  The real object ends at y=90.
	# So bbox height must be significantly larger than 80 (the real object height).
	bb = result.bbox
	assert bb is not None
	assert (bb.max_y - bb.min_y) > 100.0, (
		"flag-off: shadow retained so bbox height should exceed 100"
	)


def test_flag_on_removes_shadow_and_tightens_viewbox(tmp_path: pathlib.Path) -> None:
	"""With remove_floor_shadow=True, the shadow is removed and the viewBox tightens.

	After removal the bbox must NOT extend into the shadow's y-range; the tightened
	viewBox height must be smaller than when the shadow is retained.
	"""
	svg_text = _make_shadow_svg(_REAL_OBJECT_PATH, _SHADOW_PATH_OPACITY)
	svg_in = tmp_path / "shadow_on.svg"
	svg_out_off = tmp_path / "shadow_on_off.out.svg"
	svg_out_on = tmp_path / "shadow_on_on.out.svg"
	svg_in.write_text(svg_text, encoding="utf-8")

	result_off = tools.svg_normalizer.workflow.normalize_svg_file(svg_in, svg_out_off, padding=0.0)
	result_on = tools.svg_normalizer.workflow.normalize_svg_file(
		svg_in, svg_out_on, padding=0.0, remove_floor_shadow=True
	)
	assert result_off.normalized, f"flag-off unexpected rejection: {result_off.rejection}"
	assert result_on.normalized, f"flag-on unexpected rejection: {result_on.rejection}"

	height_off = result_off.bbox.max_y - result_off.bbox.min_y
	height_on = result_on.bbox.max_y - result_on.bbox.min_y
	# After shadow removal the bbox must be strictly smaller.
	assert height_on < height_off, (
		f"flag-on bbox height {height_on:.2f} should be less than flag-off {height_off:.2f}"
	)
	# The real object occupies y=10..90 (height=80); after shadow removal the
	# tightened bbox height should be close to 80 (within a small tolerance).
	assert abs(height_on - 80.0) < 5.0, (
		f"tightened bbox height {height_on:.2f} should be ~80 (real object only)"
	)


def test_dry_run_reports_numeric_geometry_without_mutating_input(
	tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str],
) -> None:
	"""The dry-run report formats numeric bounds and preserves source bytes."""
	svg_in = tmp_path / "dry_run_shadow.svg"
	svg_text = _make_shadow_svg(_REAL_OBJECT_PATH, _SHADOW_PATH_OPACITY)
	svg_in.write_text(svg_text, encoding="utf-8")
	original_bytes = svg_in.read_bytes()

	tools.svg_normalizer.cli._shadow_dry_run_report(svg_in)

	report = capsys.readouterr().out
	assert re.search(
		r"SHADOW-CANDIDATE: .*bbox=\([^)]*\).*"
		r"crop_delta=\(w_shrink_up_to=\d+(?:\.\d+)? "
		r"h_shrink_up_to=\d+(?:\.\d+)?\)",
		report,
	)
	assert svg_in.read_bytes() == original_bytes


def test_output_passes_reference_integrity(tmp_path: pathlib.Path) -> None:
	"""After shadow removal the output still passes S1 reference integrity.

	A shadow path that has no url(#) references; removing it must leave all
	other references intact.
	"""
	svg_text = _make_shadow_svg(_REAL_OBJECT_PATH, _SHADOW_PATH_OPACITY)
	svg_in = tmp_path / "ref_int.svg"
	svg_out = tmp_path / "ref_int.out.svg"
	svg_in.write_text(svg_text, encoding="utf-8")
	result = tools.svg_normalizer.workflow.normalize_svg_file(
		svg_in, svg_out, padding=0.0, remove_floor_shadow=True
	)
	assert result.normalized, f"unexpected rejection: {result.rejection}"
	# Re-parse output and confirm reference integrity passes.
	out_root = lxml.etree.parse(str(svg_out)).getroot()
	ref_rejection = tools.svg_normalizer.document.check_reference_integrity(out_root)
	assert ref_rejection is None, f"S1 reference integrity failed after shadow removal: {ref_rejection}"


def test_rejects_marked_shadow_when_an_internal_reference_would_dangle(

	tmp_path: pathlib.Path,
) -> None:
	"""Shadow removal fails closed when the selected path remains referenced.

	The explicit marker and geometry gates select the detached shadow. The S1
	gate must then reject the removal rather than serialize an SVG whose local
	paint reference points to the detached id.
	"""
	shadow_with_id = _SHADOW_PATH_OPACITY.replace(
		'data-editorial-floor-shadow="true"',
		'id="editorial-shadow" data-editorial-floor-shadow="true"',
	)
	reference_holder = (
		'<path d="M 120 20 L 140 20 L 140 40 L 120 40 Z" '
		'fill="url(#editorial-shadow)"/>'
	)
	svg_in = tmp_path / "referenced_shadow.svg"
	svg_out = tmp_path / "referenced_shadow.out.svg"
	svg_in.write_text(
		_make_shadow_svg(_REAL_OBJECT_PATH + reference_holder, shadow_with_id),
		encoding="utf-8",
	)

	result = tools.svg_normalizer.workflow.normalize_svg_file(
		svg_in, svg_out, padding=0.0, remove_floor_shadow=True,
	)

	assert result.rejection is not None and result.rejection.code == "UNRESOLVED_REFERENCE"
	assert not result.output_written and not svg_out.exists()
