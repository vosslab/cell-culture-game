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



# Floor-shadow removal (D1)
#
# Test fixtures use a synthetic asset pattern: a tall object path (the "real"
# object) plus a wide-flat low-opacity grey ellipse in the bottom band.
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
# fill-opacity=0.3 < 0.5 -> shadow signal.
_SHADOW_PATH_OPACITY = (
	'<path d="M 20 160 A 80 7.5 0 1 0 180 160 A 80 7.5 0 1 0 20 160 Z"'
	' fill="#888" fill-opacity="0.3"/>'
)

# A wide-flat grey fill path (no explicit fill-opacity, uses grey colour signal).
# fill=#808080 -> R=128,G=128,B=128: max=128 <= 180, max-min=0 <= 30 -> grey.
_SHADOW_PATH_GREY = (
	'<path d="M 20 160 A 80 7.5 0 1 0 180 160 A 80 7.5 0 1 0 20 160 Z"'
	' fill="#808080"/>'
)

# A wide-flat path with id containing "shadow".
_SHADOW_PATH_ID = (
	'<path d="M 20 160 A 80 7.5 0 1 0 180 160 A 80 7.5 0 1 0 20 160 Z"'
	' id="floor_shadow_ellipse" fill="#ccc"/>'
)

# A wide-flat bottom path that is NOT a shadow: full-opacity saturated red.
_NOT_SHADOW_PATH = (
	'<path d="M 20 160 A 80 7.5 0 1 0 180 160 A 80 7.5 0 1 0 20 160 Z"'
	' fill="#ff0000"/>'
)


def _parse_svg_root(svg_text: str) -> "lxml.etree._Element":
	"""Parse SVG text and return the root element."""
	return lxml.etree.fromstring(svg_text.encode("utf-8"))


#============================================
# Detection-function unit tests (pure, no file I/O)
#============================================

@pytest.mark.parametrize("shadow_path,expected_signal", [
	(_SHADOW_PATH_OPACITY, "fill_opacity"),
	(_SHADOW_PATH_GREY, "grey_fill"),
	(_SHADOW_PATH_ID, "id_class"),
])
def test_d1_detect_shadow_candidate_found(shadow_path: str, expected_signal: str) -> None:
	"""detect_floor_shadow_candidates finds the wide-flat bottom shadow element.

	Three synthetic shadow signals are tested: fill-opacity, grey fill, id_class.
	Each must produce exactly one candidate with the expected signal name.
	"""
	svg_text = _make_shadow_svg(_REAL_OBJECT_PATH, shadow_path)
	root = _parse_svg_root(svg_text)
	# Compute overall bbox from the two paths.
	overall_bbox = tools.svg_normalizer.geometry.compute_bbox(root)
	candidates = tools.svg_normalizer.shadows.detect_floor_shadow_candidates(root, overall_bbox)
	assert len(candidates) == 1, f"expected 1 candidate for signal={expected_signal}, got {len(candidates)}"
	assert candidates[0].signal == expected_signal


def test_d1_detect_no_false_positive_saturated_color() -> None:
	"""detect_floor_shadow_candidates must NOT flag a saturated-color bottom path.

	A wide-flat bottom element with full-opacity saturated red fill and no
	shadow id/class is not a shadow -- no false positive.
	"""
	svg_text = _make_shadow_svg(_REAL_OBJECT_PATH, _NOT_SHADOW_PATH)
	root = _parse_svg_root(svg_text)
	overall_bbox = tools.svg_normalizer.geometry.compute_bbox(root)
	candidates = tools.svg_normalizer.shadows.detect_floor_shadow_candidates(root, overall_bbox)
	assert len(candidates) == 0, f"false positive: got {len(candidates)} candidate(s)"


def test_d1_detect_no_candidate_when_not_bottom_band() -> None:
	"""An element in the top half is not a floor-shadow candidate even if wide-flat.

	The shadow shape is moved to y=10..25 (top region): its center_y is well
	above the bottom-band threshold.
	"""
	# Wide-flat low-opacity path at the TOP (y=10..25, center_y=17.5).
	top_shadow = (
		'<path d="M 20 10 A 80 7.5 0 1 0 180 10 A 80 7.5 0 1 0 20 10 Z"'
		' fill="#888" fill-opacity="0.3"/>'
	)
	svg_text = _make_shadow_svg(_REAL_OBJECT_PATH, top_shadow)
	root = _parse_svg_root(svg_text)
	overall_bbox = tools.svg_normalizer.geometry.compute_bbox(root)
	candidates = tools.svg_normalizer.shadows.detect_floor_shadow_candidates(root, overall_bbox)
	assert len(candidates) == 0, "wide-flat top element should not be a shadow candidate"


def test_d1_detect_no_candidate_when_not_wide_flat() -> None:
	"""A squarish bottom element is not a floor-shadow candidate even with low opacity.

	A square-ish path (aspect ~1.0) in the bottom band with fill-opacity=0.2
	should not be detected (fails the wide-flat criterion).
	"""
	# A square-ish low-opacity path at the bottom (w=20, h=15, aspect=1.3 < 3).
	squarish_bottom = (
		'<path d="M 85 160 L 105 160 L 105 175 L 85 175 Z"'
		' fill="#888" fill-opacity="0.2"/>'
	)
	svg_text = _make_shadow_svg(_REAL_OBJECT_PATH, squarish_bottom)
	root = _parse_svg_root(svg_text)
	overall_bbox = tools.svg_normalizer.geometry.compute_bbox(root)
	candidates = tools.svg_normalizer.shadows.detect_floor_shadow_candidates(root, overall_bbox)
	assert len(candidates) == 0, "non-wide-flat bottom element should not be a shadow candidate"


#============================================
# Style-class no-guess test: shadow signal via <style> class only -> no candidate
#============================================

def test_d1_no_guess_on_style_class_only_signal() -> None:
	"""A shadow signal living ONLY in a <style> class rule is not used (no guessing).

	A wide-flat bottom path whose fill-opacity:0.2 is set only by a <style> class
	rule (no inline style, no presentation attribute) and whose id/class do NOT
	contain "shadow" and whose fill is saturated (not grey) must produce NO
	candidate: v3 reads only the inline cascade and never resolves a class rule.

	The file would be rejected by _detect_style_geometry (fill-opacity in
	<style>), so the detection function is exercised directly on a prepared root.
	"""
	svg_text = (
		f'<svg xmlns="{SVG_NS}" viewBox="0 0 200 200">'
		'<style>.band { fill-opacity: 0.2; }</style>'
		+ _REAL_OBJECT_PATH
		+ '<path d="M 20 160 A 80 7.5 0 1 0 180 160 A 80 7.5 0 1 0 20 160 Z"'
		' class="band" id="floorband" fill="#0044ff"/>'
		'</svg>'
	)
	root = _parse_svg_root(svg_text)
	overall_bbox = tools.svg_normalizer.geometry.compute_bbox(root)
	candidates = tools.svg_normalizer.shadows.detect_floor_shadow_candidates(root, overall_bbox)
	# fill-opacity is only in <style> (ignored); fill #0044ff is not grey; neither
	# id nor class contains "shadow" -> the no-guess rule yields zero candidates.
	assert len(candidates) == 0


def test_d1_no_fill_opacity_signal_from_style_class() -> None:
	"""fill-opacity from a <style> class rule is NOT used as a shadow signal.

	A wide-flat bottom path with its fill-opacity set only via a <style> block
	(the element itself has no inline fill-opacity and no presentation attribute)
	must NOT trigger the fill_opacity sub-criterion.  The id and class are neutral
	(no 'shadow' substring).  The fill colour is saturated blue (#0000ff) so
	grey_fill is also absent.  Result: no candidate.
	"""
	# This SVG would normally be REJECTED by _detect_style_geometry (fill-opacity
	# in a <style> block is in _STYLE_GEOMETRY_PROPS).  We test the detection
	# function directly with a pre-prepared root (bypassing the classifier).
	svg_text = (
		f'<svg xmlns="{SVG_NS}" viewBox="0 0 200 200">'
		'<style>.accent { fill-opacity: 0.1; }</style>'
		+ _REAL_OBJECT_PATH
		+ '<path d="M 20 160 A 80 7.5 0 1 0 180 160 A 80 7.5 0 1 0 20 160 Z"'
		' class="accent" id="bottomband" fill="#0000ff"/>'
		'</svg>'
	)
	root = _parse_svg_root(svg_text)
	overall_bbox = tools.svg_normalizer.geometry.compute_bbox(root)
	candidates = tools.svg_normalizer.shadows.detect_floor_shadow_candidates(root, overall_bbox)
	# fill="#0000ff": max channel 255 > _SHADOW_GREY_MAX_VALUE -> not grey.
	# fill-opacity is only in <style> -> no fill_opacity signal.
	# id="bottomband", class="accent": neither contains "shadow" -> no id_class.
	assert len(candidates) == 0, (
		f"no shadow signal should fire on a saturated fill with "
		f"fill-opacity only in <style>; got {len(candidates)} candidate(s)"
	)


#============================================
# normalize_svg_file integration tests (flag-off vs flag-on)
#============================================

def test_d1_flag_off_shadow_retained(tmp_path: pathlib.Path) -> None:
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


def test_d1_flag_on_shadow_removed_viewbox_tightens(tmp_path: pathlib.Path) -> None:
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


def test_d1_dry_run_reports_numeric_geometry_without_mutating_input(
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


@pytest.mark.parametrize(
	"hex_fill",
	[
		"#808080",  # classic mid-grey
		"#404040",  # dark grey
		"#888",     # 3-hex grey -> #888888 (max=136 <= 180, delta=0 <= 30)
	],
	ids=["mid_grey", "dark_grey", "short_hex_grey"],
)
def test_d1_grey_fill_signal_true(hex_fill: str) -> None:
	"""_fill_is_desaturated_grey accepts desaturated mid/low grey hex fills."""
	assert tools.svg_normalizer.shadows._fill_is_desaturated_grey(hex_fill)


@pytest.mark.parametrize(
	"hex_fill",
	[
		"#f0f0f0",  # near-white: max channel 240 > 180
		"#ff0000",  # saturated red: per-channel delta 255 >> 30
		"grey",     # named colour, not a parseable hex value
	],
	ids=["near_white", "saturated_red", "named_colour"],
)
def test_d1_grey_fill_signal_false(hex_fill: str) -> None:
	"""_fill_is_desaturated_grey rejects near-white, saturated, and non-hex fills."""
	assert not tools.svg_normalizer.shadows._fill_is_desaturated_grey(hex_fill)


def test_d1_output_passes_reference_integrity(tmp_path: pathlib.Path) -> None:
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

