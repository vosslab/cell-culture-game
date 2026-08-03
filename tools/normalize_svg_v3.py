#!/usr/bin/env python3
"""
SVG normalizer v3: lxml core port of normalize_svg_v2.py plus the shared
normalize-or-reject skeleton.

v3 is the ingestion gate for asset SVGs (see the SVG-normalizer-v3 plan and
docs/PRIMARY_CONTRACT.md item 3). Every SVG is run through v3 before it is added
to assets/. The tool has exactly one job: it either NORMALIZES a file to a
guaranteed-safe result or REJECTS it with a stable reason code and a suggested
author fix. There is no "success with a warning" path and no --strict mode.

This file provides the shared v3 normalization framework. It establishes:

- The pure-math geometry backend (path tokenizer, rel->abs path conversion,
  exact elliptical-arc extrema, curve/path/element bbox). These helpers operate
  on strings and PathSegment tuples, never on XML nodes, so later WPs reuse them
  unchanged.
- The lxml parse/serialize core with S4 canonical serialization: stable
  namespace prefixes (no ns0:/ns1: renaming), UTF-8, and a trailing newline.
- The rejection model: RejectionReason (code/message/fix/element), the
  REASON_CODES token set, and NormalizeResult. On rejection v3 writes NO output
  and leaves the input untouched (especially under --in-place), and the CLI
  exits non-zero.
- The classify() seam, which combines the supported feature detectors without
  redefining the public functions established here.

The ordinary-asset policy crops to the drawn bbox, shifts it to the origin, and
rewrites the viewBox. The material-asset policy preserves its authored root
frame and structural-anchor coordinates. Both policies convert relative path
commands to absolute (M/m L/l H/h V/v C/c S/s
Q/q T/t A/a Z/z), ASCII-clean id/data-name and rewrite references, preserve
dc/cc/rdf/xlink/sodipodi/inkscape namespace prefixes, preserve pre-root
comments, in-root comments, <title>, and <desc>.

The implementation flattens transforms and supported clip paths, converts
supported shapes to paths, computes stroke-aware bounds, rejects unsupported
text and features, verifies references, and removes floor shadows.

Bounding boxes for cubic and quadratic curves are approximate: they use the
control points and endpoints (a conservative superset of the true curve, so the
box never undershoots). Elliptical arcs ARE solved exactly: arc_extrema computes
the true axis-aligned extrema, accounting for rotation, the large-arc flag, and
the sweep flag, so a bulging arc is fully contained.

Examples:
  source source_me.sh && python3 tools/normalize_svg_v3.py -i microtube.svg
  source source_me.sh && python3 tools/normalize_svg_v3.py -i a.svg -o normalized/
  source source_me.sh && python3 tools/normalize_svg_v3.py --self-test
"""

from __future__ import annotations

# Standard Library
import re
import sys
import json
import math
import shutil
import argparse
import tempfile
import unicodedata
from dataclasses import dataclass
from decimal import Context, Decimal, getcontext
from pathlib import Path
from collections.abc import Iterable

# PIP3 modules
import shapely  # shapely
import lxml.etree  # lxml
import tinycss2  # tinycss2
import shapely.geometry  # shapely
from validation.svg.layer_recipe_validator import (
	MaterialSvgValidationError,
	inject_normalizer_boundary_tokens,
	material_boundary_signature,
	remove_normalizer_boundary_tokens,
	validate_reserved_attributes,
)

SVG_NS = "http://www.w3.org/2000/svg"

# Matches an event-handler attribute name (onclick, onload, onmouseover, ...).
# Module scope avoids recompiling this expression for each SVG.
# recompile it on every call.
_ON_HANDLER_RE = re.compile(r"^on[a-zA-Z]")

# Canonical namespace prefixes preserved on serialization. Without pinning these
# in the root nsmap, lxml renames foreign-namespace prefixes to ns0:/ns1:/... on
# write, breaking downstream attribution parsers (Dublin Core, Creative Commons
# RDF) and human readability. This is the S4 "no ns0:" guarantee.
CANONICAL_NS_PREFIXES = {
	"dc": "http://purl.org/dc/elements/1.1/",
	"cc": "http://creativecommons.org/ns#",
	"rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
	"xlink": "http://www.w3.org/1999/xlink",
	"sodipodi": "http://sodipodi.sourceforge.net/DTD/sodipodi-0.0.dtd",
	"inkscape": "http://www.inkscape.org/namespaces/inkscape",
}

COMMAND_RE = re.compile(r"([AaCcHhLlMmQqSsTtVvZz])|([-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?)")
COMMAND_ARITY = {
	"M": 2,
	"L": 2,
	"H": 1,
	"V": 1,
	"C": 6,
	"S": 4,
	"Q": 4,
	"T": 2,
	"A": 7,
	"Z": 0,
}
COORD_ATTRS_X = {"x", "x1", "x2", "cx"}
COORD_ATTRS_Y = {"y", "y1", "y2", "cy"}
# Shape tags for bbox and shape->path processing. "text" is deliberately absent:
# text elements are rejected by the classifier (A5 TEXT_UNSUPPORTED) and must
# never contribute geometry. "tspan" and "textPath" are children of text
# and are handled by the same classifier path.
SHAPE_TAGS = {"path", "rect", "circle", "ellipse", "line", "polyline", "polygon"}

# Runtime material overlays resolve this clip after the SVG has been injected
# into the scene DOM.  It intentionally has no source-SVG clip-path user, so
# local-reference pruning must retain this one closed contract anchor.
RUNTIME_EXTERNAL_CLIP_IDS = frozenset({"anchor_liquid_clip"})

# The material renderer reads this hidden SVGRectElement's x/y/width/height
# directly after instance injection.  Keeping it as a rect is therefore a DOM
# contract, not an incidental source-art representation.  It is intentionally
# excluded from the otherwise path-only visible-art invariant.
RUNTIME_BOUNDS_RECT_ID = "anchor_liquid_bounds"

# Stable rejection reason tokens emitted by the feature detectors.
# these; the set itself is the shared vocabulary so reports, tests, and future
# automation agree on codes. Sourced from the plan's Rejection reason schema.
class UnsupportedUnitError(Exception):
	"""Raised when a required shape attribute carries a non-user-unit (e.g. %).

	Carries the element location string for the rejection report.
	"""
	def __init__(self, element_location: str) -> None:
		super().__init__(f"Non-user unit on required size attribute at {element_location}")
		self.element_location = element_location


REASON_CODES = frozenset({
	"TEXT_UNSUPPORTED",
	"USE_OR_SYMBOL_UNSUPPORTED",
	"FILTER_UNSUPPORTED",
	"MASK_UNSUPPORTED",
	"MARKER_UNSUPPORTED",
	"CLIPPATH_UNSUPPORTED_COMPLEX",
	"FOREIGNOBJECT_UNSUPPORTED",
	"EXTERNAL_RESOURCE_UNSUPPORTED",
	"EMBEDDED_RASTER_UNSUPPORTED",
	"DOCTYPE_OR_ENTITY",
	"SCRIPT_OR_HANDLER",
	"ANIMATION_UNSUPPORTED",
	"STYLE_GEOMETRY_UNSUPPORTED",
	"STYLE_UNPARSEABLE",
	"UNSUPPORTED_TRANSFORM",
	"UNSUPPORTED_UNIT",
	"NONSCALING_STROKE_UNRESOLVED",
	"PARSER_ERROR",
	"UNRESOLVED_REFERENCE",
	"PATTERN_UNSUPPORTED",
	"EMPTY_GEOMETRY",
	"MATERIAL_SEMANTIC_INVALID",
	"MATERIAL_BOUNDARY_LOST",
})


#============================================
@dataclass(frozen=True)
class PathSegment:
	cmd: str
	nums: tuple[float, ...]


#============================================
@dataclass(frozen=True)
class BBox:
	min_x: float
	min_y: float
	max_x: float
	max_y: float

	def union(self, other: "BBox") -> "BBox":
		return BBox(
			min(self.min_x, other.min_x),
			min(self.min_y, other.min_y),
			max(self.max_x, other.max_x),
			max(self.max_y, other.max_y),
		)

	@property
	def width(self) -> float:
		return self.max_x - self.min_x

	@property
	def height(self) -> float:
		return self.max_y - self.min_y


#============================================
@dataclass(frozen=True)
class RejectionReason:
	"""One classified reason a file was refused by the v3 gate.

	This is the stable rejection shape used by the CLI, the wild runner report,
	and tests. Later WPs construct these for each detector they add; they must
	not change the field set.

	Attributes:
		code: A stable token from REASON_CODES.
		message: Human-readable explanation of why the file was rejected.
		fix: Suggested author action to make the file ingestible.
		element: XPath-like location of the offending node when available, else "".
	"""
	code: str
	message: str
	fix: str
	element: str = ""


#============================================
@dataclass
class NormalizeResult:
	"""Outcome of attempting to normalize one SVG file.

	Exactly one of the two outcomes holds:

	- NORMALIZED: rejection is None, bbox and view_box describe the result, and
	  output_written is True (an output file was emitted).
	- REJECTED: rejection is a RejectionReason, output_written is False, and no
	  output file was written (the input is left untouched).

	Attributes:
		input_path: The source SVG path.
		output_path: Where output was (or would be) written.
		rejection: The RejectionReason when rejected, else None.
		bbox: The original drawn BBox when normalized, else None.
		view_box: The new viewBox string when normalized, else None.
		output_written: True only when a normalized file was written to disk.
		secondary_reason_codes: Extra reason codes for files that hit more than
			one issue (reported by --report-json; the CLI exit uses the primary
			rejection only).
	"""
	input_path: Path
	output_path: Path
	rejection: RejectionReason | None = None
	bbox: BBox | None = None
	view_box: str | None = None
	output_written: bool = False
	secondary_reason_codes: tuple[str, ...] = ()

	@property
	def normalized(self) -> bool:
		return self.rejection is None


#============================================
def local_name(tag: str) -> str:
	if "}" in tag:
		return tag.rsplit("}", 1)[1]
	return tag


#============================================
def fmt(value: float) -> str:
	if abs(value) < 1e-9:
		value = 0.0
	text = f"{value:.6f}".rstrip("0").rstrip(".")
	return text if text else "0"


# Precision contexts for fmt_precise (ported BY HAND from scour scour.py,
# Apache-2.0, function scourUnitlessLength). The normal context handles
# coordinates; the control-point context uses one fewer digit.
# Default: 6 significant digits (matches v2 6-decimal-place output at the
# same precision level). This is a hardcoded sensible default per plan A4;
# no CLI flag is added.
_COORD_PRECISION = 6
_CTRL_PRECISION = 5
_SCOUR_COORD_CTX = Context(prec=_COORD_PRECISION)
_SCOUR_CTRL_CTX = Context(prec=_CTRL_PRECISION)


#============================================
def fmt_precise(value: float, is_control_point: bool = False) -> str:
	"""Format a coordinate with scour-style precision: leading-zero strip,
	shortest of decimal vs scientific notation.

	Ported BY HAND from scour (Apache-2.0) scour.py scourUnitlessLength.
	Dual Decimal.Context: normal context (6 sig-figs) and control-point context
	(5 sig-figs). Leading-zero strip: 0.5 -> .5, -0.5 -> -.5. Scientific
	notation chosen when strictly shorter than decimal form.

	Args:
		value: The float coordinate to format.
		is_control_point: Use the reduced-precision control-point context.

	Returns:
		Shortest correct string representation of the rounded coordinate.
	"""
	if abs(value) < 1e-9:
		value = 0.0
	# Convert to Decimal in full precision, then quantize to output precision.
	initial = getcontext().create_decimal(str(value))
	ctx = _SCOUR_CTRL_CTX if is_control_point else _SCOUR_COORD_CTX
	# ctx.plus() rounds to ctx.prec significant digits.
	length = ctx.plus(initial)
	# Remove trailing zeros: if equal to its integer value, cast to int.
	int_length = length.to_integral_value()
	if length == int_length:
		length = Decimal(int_length)
	else:
		length = length.normalize()
	# Non-scientific decimal representation; re-quantize from initial to avoid
	# rounding loss (e.g. 123.4 rounds to 123 not 120).
	nonsci = f"{length:f}"
	nonsci = f"{initial.quantize(Decimal(nonsci)):f}"
	# Leading-zero strip: 0.xyz -> .xyz, -0.xyz -> -.xyz.
	if len(nonsci) > 2 and nonsci[:2] == "0.":
		nonsci = nonsci[1:]
	elif len(nonsci) > 3 and nonsci[:3] == "-0.":
		nonsci = "-" + nonsci[2:]
	result = nonsci
	# Try scientific notation when decimal form is > 3 chars; pick shorter.
	if len(nonsci) > 3:
		exponent = length.adjusted()
		sci_mantissa = length.scaleb(-exponent).normalize()
		sci = f"{sci_mantissa}e{exponent}"
		if len(sci) < len(nonsci):
			result = sci
	return result if result else "0"


#============================================
def parse_float(value: str | None, default: float = 0.0) -> float:
	if value is None:
		return default
	match = re.match(r"\s*([-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?)", value)
	if not match:
		return default
	return float(match.group(1))


# Matches an optional sign + numeric part at the start of an attribute value.
# Used to detect numeric prefix in parse_float_required.
_NUMERIC_RE = re.compile(r"\s*([-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?)(.*)")

# Unit suffixes that are NOT user units.  "px" is a user-unit alias (1px == 1uu in SVG).
# Matching is case-insensitive; we check for any trailing % or alphabetic suffix.
# The check order in parse_float_required is: "" -> unitless (ok), "px" -> ok,
# everything else containing [a-z%]+ -> UNSUPPORTED_UNIT.
_UNSUPPORTED_UNIT_RE = re.compile(r"[a-z%]+", re.IGNORECASE)
_PX_UNIT_RE = re.compile(r"\s*px\s*$", re.IGNORECASE)

# Reason code returned (as a sentinel string) by parse_float_required when the
# value carries a non-user-unit suffix.  The caller (element_bbox) checks for
# this sentinel and propagates it so normalize_svg_file can emit UNSUPPORTED_UNIT.
_UNIT_SENTINEL = "__UNSUPPORTED_UNIT__"


#============================================
def parse_float_required(value: str | None) -> float | str | None:
	"""Parse a float from a REQUIRED SVG size attribute.

	Unlike parse_float, this distinguishes three outcomes:
	  - None         : attribute absent or non-numeric (no bbox, treated as
	                   missing required attr -> EMPTY_GEOMETRY path).
	  - _UNIT_SENTINEL : attribute has a numeric prefix but carries a non-user-
	                   unit suffix (%, mm, cm, in, pt, pc, em, ex, ...).  The
	                   caller must propagate this to an UNSUPPORTED_UNIT rejection
	                   rather than silently using the stripped number.
	  - float        : a valid user-unit value (bare number or "px" suffix).

	Args:
		value: The raw attribute string, or None when the attribute is absent.

	Returns:
		float for a valid user-unit value, _UNIT_SENTINEL for a bad unit, None
		when the attribute is absent or non-numeric.
	"""
	if value is None:
		return None
	match = _NUMERIC_RE.match(value)
	if not match:
		return None
	number_str = match.group(1)
	# The rest of the string after the numeric prefix (stripped of whitespace).
	rest = match.group(2).strip()
	if rest == "" or _PX_UNIT_RE.match(rest):
		# Unitless (user units) or explicit px (== 1 user unit in SVG).
		return float(number_str)
	if _UNSUPPORTED_UNIT_RE.search(rest):
		# Any other alphabetic suffix is a non-user unit (%, mm, cm, in, pt, pc, em, ex).
		return _UNIT_SENTINEL
	# Trailing non-alpha junk (e.g. bare "+") after the number -- treat as missing.
	return None


#============================================
def tokenize_path(d_attr: str) -> list[str]:
	tokens: list[str] = []
	for match in COMMAND_RE.finditer(d_attr):
		tokens.append(match.group(1) or match.group(2))
	return tokens


#============================================
def is_command(token: str) -> bool:
	return len(token) == 1 and token.isalpha()


#============================================
def parse_path_to_absolute(d_attr: str) -> list[PathSegment]:
	"""Parse common SVG path data and convert commands to absolute form."""
	tokens = tokenize_path(d_attr)
	segments: list[PathSegment] = []
	index = 0
	current_cmd: str | None = None
	x = 0.0
	y = 0.0
	start_x = 0.0
	start_y = 0.0
	last_c_ctrl: tuple[float, float] | None = None
	last_q_ctrl: tuple[float, float] | None = None

	def read_numbers(count: int) -> tuple[float, ...] | None:
		nonlocal index
		if index + count > len(tokens):
			return None
		values: list[float] = []
		for offset in range(count):
			token = tokens[index + offset]
			if is_command(token):
				return None
			values.append(float(token))
		index += count
		return tuple(values)

	while index < len(tokens):
		token = tokens[index]
		if is_command(token):
			current_cmd = token
			index += 1
		elif current_cmd is None:
			raise ValueError(f"Path data begins with number instead of command: {d_attr[:80]}")

		if current_cmd is None:
			break

		cmd = current_cmd
		upper = cmd.upper()
		relative = cmd.islower()
		arity = COMMAND_ARITY.get(upper)
		if arity is None:
			raise ValueError(f"Unsupported path command: {cmd}")

		if upper == "Z":
			segments.append(PathSegment("Z", ()))
			x, y = start_x, start_y
			last_c_ctrl = None
			last_q_ctrl = None
			current_cmd = None
			continue

		first_moveto = upper == "M"
		consumed_any = False
		while index < len(tokens):
			if is_command(tokens[index]):
				break
			nums = read_numbers(arity)
			if nums is None:
				break
			consumed_any = True

			if upper == "M":
				nx, ny = nums
				if relative:
					nx += x
					ny += y
				x, y = nx, ny
				start_x, start_y = x, y
				segments.append(PathSegment("M", (x, y)))
				# Subsequent coordinate pairs after M/m are implicit L/l.
				upper = "L"
				arity = COMMAND_ARITY[upper]
				current_cmd = "l" if relative else "L"
				last_c_ctrl = None
				last_q_ctrl = None
				continue

			if upper == "L":
				nx, ny = nums
				if relative:
					nx += x
					ny += y
				x, y = nx, ny
				segments.append(PathSegment("L", (x, y)))
				last_c_ctrl = None
				last_q_ctrl = None

			elif upper == "H":
				(nx,) = nums
				if relative:
					nx += x
				x = nx
				segments.append(PathSegment("L", (x, y)))
				last_c_ctrl = None
				last_q_ctrl = None

			elif upper == "V":
				(ny,) = nums
				if relative:
					ny += y
				y = ny
				segments.append(PathSegment("L", (x, y)))
				last_c_ctrl = None
				last_q_ctrl = None

			elif upper == "C":
				x1, y1, x2, y2, nx, ny = nums
				if relative:
					x1 += x; y1 += y; x2 += x; y2 += y; nx += x; ny += y
				segments.append(PathSegment("C", (x1, y1, x2, y2, nx, ny)))
				x, y = nx, ny
				last_c_ctrl = (x2, y2)
				last_q_ctrl = None

			elif upper == "S":
				x2, y2, nx, ny = nums
				if last_c_ctrl is None:
					x1, y1 = x, y
				else:
					x1, y1 = 2 * x - last_c_ctrl[0], 2 * y - last_c_ctrl[1]
				if relative:
					x2 += x; y2 += y; nx += x; ny += y
				segments.append(PathSegment("C", (x1, y1, x2, y2, nx, ny)))
				x, y = nx, ny
				last_c_ctrl = (x2, y2)
				last_q_ctrl = None

			elif upper == "Q":
				x1, y1, nx, ny = nums
				if relative:
					x1 += x; y1 += y; nx += x; ny += y
				segments.append(PathSegment("Q", (x1, y1, nx, ny)))
				x, y = nx, ny
				last_q_ctrl = (x1, y1)
				last_c_ctrl = None

			elif upper == "T":
				nx, ny = nums
				if last_q_ctrl is None:
					x1, y1 = x, y
				else:
					x1, y1 = 2 * x - last_q_ctrl[0], 2 * y - last_q_ctrl[1]
				if relative:
					nx += x; ny += y
				segments.append(PathSegment("Q", (x1, y1, nx, ny)))
				x, y = nx, ny
				last_q_ctrl = (x1, y1)
				last_c_ctrl = None

			elif upper == "A":
				rx, ry, rot, large, sweep, nx, ny = nums
				if relative:
					nx += x; ny += y
				segments.append(PathSegment("A", (rx, ry, rot, large, sweep, nx, ny)))
				x, y = nx, ny
				last_c_ctrl = None
				last_q_ctrl = None

			if first_moveto:
				first_moveto = False

		if not consumed_any and index < len(tokens) and not is_command(tokens[index]):
			raise ValueError(f"Could not parse path near token {tokens[index]!r}")

	return segments


#============================================
def path_segments_to_d(segments: Iterable[PathSegment], dx: float = 0.0, dy: float = 0.0) -> str:
	parts: list[str] = []
	for seg in segments:
		cmd = seg.cmd
		nums = list(seg.nums)
		if cmd in {"M", "L"}:
			nums[0] += dx
			nums[1] += dy
		elif cmd == "C":
			nums[0] += dx; nums[1] += dy
			nums[2] += dx; nums[3] += dy
			nums[4] += dx; nums[5] += dy
		elif cmd == "Q":
			nums[0] += dx; nums[1] += dy
			nums[2] += dx; nums[3] += dy
		elif cmd == "A":
			# rx ry rot large sweep x y; only endpoint shifts.
			nums[5] += dx
			nums[6] += dy
		elif cmd == "Z":
			parts.append("Z")
			continue
		# Emit coordinates with fmt_precise (A4 precision). For cubic bezier (C)
		# the first four numbers are control points (lower precision); for
		# quadratic bezier (Q) the first two numbers are control points.
		if cmd == "C":
			# C: cp1x cp1y cp2x cp2y ex ey (6 nums; first 4 are control points)
			formatted = [fmt_precise(n, is_control_point=True) for n in nums[:4]]
			formatted += [fmt_precise(n) for n in nums[4:]]
		elif cmd == "Q":
			# Q: cpx cpy ex ey (4 nums; first 2 are control points)
			formatted = [fmt_precise(n, is_control_point=True) for n in nums[:2]]
			formatted += [fmt_precise(n) for n in nums[2:]]
		else:
			formatted = [fmt_precise(n) for n in nums]
		parts.append(cmd + " " + " ".join(formatted))
	return " ".join(parts)


#============================================
def _arc_center_params(
	x0: float, y0: float, rx: float, ry: float, phi_deg: float,
	large_arc: float, sweep: float, x1: float, y1: float,
) -> tuple[float, float, float, float] | None:
	"""Convert an SVG endpoint-form arc to center parameterization.

	Implements the F.6.5 / F.6.6 endpoint-to-center conversion from the SVG
	spec. Returns the ellipse center, the start angle, and the signed sweep
	angle (delta), all in radians. Returns None when the arc degenerates to a
	straight line (zero radius or coincident endpoints), since such an arc has
	no bulge beyond its endpoints.

	Args:
		x0, y0: Arc start point (absolute user units).
		rx, ry: Ellipse radii as authored (may need correction).
		phi_deg: X-axis rotation of the ellipse, in degrees.
		large_arc: Large-arc flag (0 or 1).
		sweep: Sweep flag (0 or 1).
		x1, y1: Arc end point (absolute user units).

	Returns:
		Tuple (cx, cy, theta1, delta_theta) in radians, or None if degenerate.
	"""
	rx = abs(rx)
	ry = abs(ry)
	# Zero radius means the arc is just a line to the endpoint; no bulge.
	if rx == 0.0 or ry == 0.0:
		return None
	# Coincident endpoints render nothing (per spec); treat as no bulge.
	if x0 == x1 and y0 == y1:
		return None
	phi = math.radians(phi_deg % 360.0)
	cos_phi = math.cos(phi)
	sin_phi = math.sin(phi)
	# Step 1: compute (x1p, y1p), the midpoint delta in the rotated frame.
	dx2 = (x0 - x1) / 2.0
	dy2 = (y0 - y1) / 2.0
	x1p = cos_phi * dx2 + sin_phi * dy2
	y1p = -sin_phi * dx2 + cos_phi * dy2
	# Correct out-of-range radii (spec F.6.6 step 3).
	radii_check = (x1p * x1p) / (rx * rx) + (y1p * y1p) / (ry * ry)
	if radii_check > 1.0:
		scale = math.sqrt(radii_check)
		rx *= scale
		ry *= scale
	# Step 2: compute the transformed center (cxp, cyp).
	num = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p
	den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
	# Numerical guard: clamp tiny negative numerators to zero.
	if num < 0.0:
		num = 0.0
	if den == 0.0:
		return None
	coef = math.sqrt(num / den)
	# Sign per spec: negative when large_arc != sweep.
	if int(large_arc) == int(sweep):
		coef = -coef
	cxp = coef * (rx * y1p) / ry
	cyp = coef * (-ry * x1p) / rx
	# Step 3: map the center back to the original coordinate frame.
	cx = cos_phi * cxp - sin_phi * cyp + (x0 + x1) / 2.0
	cy = sin_phi * cxp + cos_phi * cyp + (y0 + y1) / 2.0

	# Step 4: compute the start angle theta1 and sweep delta.
	def angle(ux: float, uy: float, vx: float, vy: float) -> float:
		dot = ux * vx + uy * vy
		mag = math.sqrt((ux * ux + uy * uy) * (vx * vx + vy * vy))
		# Clamp to [-1, 1] to absorb floating point drift before acos.
		ratio = max(-1.0, min(1.0, dot / mag))
		result = math.acos(ratio)
		if ux * vy - uy * vx < 0.0:
			result = -result
		return result

	ux = (x1p - cxp) / rx
	uy = (y1p - cyp) / ry
	vx = (-x1p - cxp) / rx
	vy = (-y1p - cyp) / ry
	theta1 = angle(1.0, 0.0, ux, uy)
	delta = angle(ux, uy, vx, vy)
	# Honor the sweep flag direction per spec.
	if int(sweep) == 0 and delta > 0.0:
		delta -= 2.0 * math.pi
	elif int(sweep) == 1 and delta < 0.0:
		delta += 2.0 * math.pi
	return cx, cy, theta1, delta


#============================================
def _arc_point(
	cx: float, cy: float, rx: float, ry: float, cos_phi: float, sin_phi: float, t: float,
) -> tuple[float, float]:
	"""Return the (x, y) point on the rotated ellipse at angle t (radians)."""
	cos_t = math.cos(t)
	sin_t = math.sin(t)
	x = cx + rx * cos_t * cos_phi - ry * sin_t * sin_phi
	y = cy + rx * cos_t * sin_phi + ry * sin_t * cos_phi
	return x, y


#============================================
def arc_extrema(
	x0: float, y0: float, rx: float, ry: float, phi_deg: float,
	large_arc: float, sweep: float, x1: float, y1: float,
) -> tuple[list[float], list[float]]:
	"""Solve the true x/y extrema of an SVG elliptical arc.

	Evaluates the arc endpoints plus the axis-aligned extrema (the parametric
	angles where dx/dt = 0 and dy/dt = 0), keeping only those that fall inside
	the arc's actual angular sweep. This accounts for rotation, the large-arc
	flag, and the sweep flag, so an arc that bulges past its endpoints
	contributes the bulge to the bounding box.

	Args:
		x0, y0: Arc start point (absolute user units).
		rx, ry: Ellipse radii as authored.
		phi_deg: X-axis rotation of the ellipse, in degrees.
		large_arc: Large-arc flag (0 or 1).
		sweep: Sweep flag (0 or 1).
		x1, y1: Arc end point (absolute user units).

	Returns:
		Tuple (xs, ys) of candidate x and y coordinates whose min/max bound the
		arc. Always includes the two endpoints.
	"""
	xs = [x0, x1]
	ys = [y0, y1]
	params = _arc_center_params(x0, y0, rx, ry, phi_deg, large_arc, sweep, x1, y1)
	if params is None:
		# Degenerate arc: endpoints already bound it.
		return xs, ys
	cx, cy, theta1, delta = params
	# Re-derive the corrected radii in the same way the center conversion did,
	# so the extrema math matches the center we computed.
	rx = abs(rx)
	ry = abs(ry)
	phi = math.radians(phi_deg % 360.0)
	cos_phi = math.cos(phi)
	sin_phi = math.sin(phi)
	# Recompute the radius correction for consistency with the center solve.
	dx2 = (x0 - x1) / 2.0
	dy2 = (y0 - y1) / 2.0
	x1p = cos_phi * dx2 + sin_phi * dy2
	y1p = -sin_phi * dx2 + cos_phi * dy2
	radii_check = (x1p * x1p) / (rx * rx) + (y1p * y1p) / (ry * ry)
	if radii_check > 1.0:
		scale = math.sqrt(radii_check)
		rx *= scale
		ry *= scale
	# Candidate angles where the x derivative is zero:
	#   x(t) = cx + rx cos t cos_phi - ry sin t sin_phi
	#   dx/dt = -rx sin t cos_phi - ry cos t sin_phi = 0
	#   => tan t = -(ry sin_phi) / (rx cos_phi)
	# Two solutions, t and t + pi.
	t_x = math.atan2(-ry * sin_phi, rx * cos_phi)
	# Candidate angles where the y derivative is zero:
	#   y(t) = cy + rx cos t sin_phi + ry sin t cos_phi
	#   dy/dt = -rx sin t sin_phi + ry cos t cos_phi = 0
	#   => tan t = (ry cos_phi) / (rx sin_phi)
	t_y = math.atan2(ry * cos_phi, rx * sin_phi)
	candidate_base = [t_x, t_x + math.pi, t_y, t_y + math.pi]
	theta2 = theta1 + delta
	lo = min(theta1, theta2)
	hi = max(theta1, theta2)
	for t in candidate_base:
		# The sweep covers [lo, hi]; shift t by multiples of 2pi to test
		# whether the extremum angle lies within that swept interval.
		k = math.ceil((lo - t) / (2.0 * math.pi))
		t_shifted = t + k * 2.0 * math.pi
		if lo - 1e-9 <= t_shifted <= hi + 1e-9:
			px, py = _arc_point(cx, cy, rx, ry, cos_phi, sin_phi, t_shifted)
			xs.append(px)
			ys.append(py)
	return xs, ys


#============================================
def path_bbox_from_segments(segments: Iterable[PathSegment]) -> BBox | None:
	xs: list[float] = []
	ys: list[float] = []
	current_start: tuple[float, float] | None = None
	# Track the current pen position so an arc can solve its true extrema from
	# its start point (previous endpoint) through its own end point.
	cur_x = 0.0
	cur_y = 0.0
	for seg in segments:
		cmd = seg.cmd
		nums = seg.nums
		if cmd == "M":
			xs.append(nums[0]); ys.append(nums[1])
			current_start = (nums[0], nums[1])
			cur_x, cur_y = nums[0], nums[1]
		elif cmd == "L":
			xs.append(nums[0]); ys.append(nums[1])
			cur_x, cur_y = nums[0], nums[1]
		elif cmd == "C":
			xs.extend([nums[0], nums[2], nums[4]])
			ys.extend([nums[1], nums[3], nums[5]])
			cur_x, cur_y = nums[4], nums[5]
		elif cmd == "Q":
			xs.extend([nums[0], nums[2]])
			ys.extend([nums[1], nums[3]])
			cur_x, cur_y = nums[2], nums[3]
		elif cmd == "A":
			# Solve true arc extrema (rotation, large-arc, sweep) instead of
			# using only the endpoint, which undershoots a bulging arc.
			rx, ry, rot, large, sweep, end_x, end_y = nums
			arc_xs, arc_ys = arc_extrema(
				cur_x, cur_y, rx, ry, rot, large, sweep, end_x, end_y
			)
			xs.extend(arc_xs)
			ys.extend(arc_ys)
			cur_x, cur_y = end_x, end_y
		elif cmd == "Z" and current_start is not None:
			xs.append(current_start[0]); ys.append(current_start[1])
			cur_x, cur_y = current_start
	if not xs:
		return None
	return BBox(min(xs), min(ys), max(xs), max(ys))


#============================================
# Transform flattening.
#
# Math ported BY HAND from svgo (MIT) plugins/_transforms.js (transform2js,
# transformToMatrix, multiplyTransformMatrices, transformsMultiply, transformArc)
# and plugins/applyTransforms.js (stroke-distortion guard, point transforms,
# per-command application). No svgo file is copied into this repo.
#
# A 2D affine transform is the 6-tuple matrix [a, b, c, d, e, f] meaning:
#   x' = a*x + c*y + e
#   y' = b*x + d*y + f
# This matches the SVG/CSS matrix(a,b,c,d,e,f) convention and svgo's data layout.
#============================================

# Splits a transform attribute into (name, raw-args) chunks. Mirrors svgo's
# regTransformSplit. Only the closed transform vocabulary is accepted; anything
# else (e.g. a CSS transform function v3 cannot apply) is treated as unsupported.
_TRANSFORM_SPLIT_RE = re.compile(
	r"\s*(matrix|translate|scale|rotate|skewX|skewY)\s*\(\s*(.+?)\s*\)[\s,]*"
)
_TRANSFORM_NUM_RE = re.compile(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")
_TRANSFORM_NAMES = frozenset({"matrix", "translate", "scale", "rotate", "skewX", "skewY"})

IDENTITY_MATRIX = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


#============================================
class UnsupportedTransformError(Exception):
	"""Raised when a transform attribute names a function v3 cannot flatten.

	Carries the element location string for the rejection report so the caller
	can emit an UNSUPPORTED_TRANSFORM rejection rather than guessing geometry.
	"""
	def __init__(self, element_location: str, detail: str) -> None:
		super().__init__(f"Unsupported transform at {element_location}: {detail}")
		self.element_location = element_location
		self.detail = detail


#============================================
class NonScalingStrokeError(Exception):
	"""Raised when a non-scaling-stroke element cannot be safely flattened.

	Non-scaling stroke geometry under a transform is not resolved, so an
	element carrying vector-effect=non-scaling-stroke together with a transform
	that actually changes stroke width is refused (NONSCALING_STROKE_UNRESOLVED)
	rather than emitting wrong geometry.
	"""
	def __init__(self, element_location: str) -> None:
		super().__init__(f"Unresolvable non-scaling stroke at {element_location}")
		self.element_location = element_location


#============================================
class ComplexClipError(Exception):
	"""Raised when a clip-path usage falls outside the simple-clip allowlist (A6).

	The clip-flattening pass (flatten_clip_paths) raises this for any clip it
	cannot safely flatten with shapely. normalize_svg_file turns it into a
	CLIPPATH_UNSUPPORTED_COMPLEX rejection with no output. The detail string
	records which allowlist rule failed (for the rejection message); the location
	is the offending clipped element or clipPath.
	"""
	def __init__(self, element_location: str, detail: str) -> None:
		super().__init__(f"Complex clipPath at {element_location}: {detail}")
		self.element_location = element_location
		self.detail = detail


#============================================
def parse_transform_list(transform_str: str, element_location: str) -> list[tuple[str, tuple[float, ...]]]:
	"""Parse a transform attribute into an ordered list of (name, args).

	Ported from svgo transform2js. The transform list is applied left to right
	(outermost first), matching SVG semantics: transform="A B" means apply B to
	the local coordinates, then A.

	Args:
		transform_str: The raw transform attribute value.
		element_location: XPath-like location for error reporting.

	Returns:
		Ordered list of (function-name, numeric-args) tuples.

	Raises:
		UnsupportedTransformError: When the string contains a function v3 does
			not support, or args do not match the function arity.
	"""
	items: list[tuple[str, tuple[float, ...]]] = []
	# Reject any non-whitespace residue that the split regex did not consume; a
	# stray token means an unsupported function (e.g. a CSS transform) is present.
	consumed = _TRANSFORM_SPLIT_RE.sub(" ", transform_str)
	if consumed.strip() != "":
		raise UnsupportedTransformError(element_location, f"unparseable transform {transform_str!r}")
	for match in _TRANSFORM_SPLIT_RE.finditer(transform_str):
		name = match.group(1)
		args = tuple(float(n) for n in _TRANSFORM_NUM_RE.findall(match.group(2)))
		if name not in _TRANSFORM_NAMES:
			raise UnsupportedTransformError(element_location, f"unsupported function {name}")
		items.append((name, args))
	return items


#============================================
def transform_to_matrix(name: str, args: tuple[float, ...], element_location: str) -> tuple[float, ...]:
	"""Convert a single transform function to a 6-tuple matrix [a,b,c,d,e,f].

	Ported from svgo transformToMatrix. Handles translate/scale/rotate (with
	optional cx,cy)/skewX/skewY/matrix.

	Args:
		name: Transform function name.
		args: Numeric arguments as authored.
		element_location: XPath-like location for error reporting.

	Returns:
		The 6-tuple affine matrix.

	Raises:
		UnsupportedTransformError: When argument count is invalid for the function.
	"""
	if name == "matrix":
		if len(args) != 6:
			raise UnsupportedTransformError(element_location, "matrix() needs 6 args")
		return tuple(args)
	if name == "translate":
		# translate(tx [ty]); ty defaults to 0.
		if len(args) not in (1, 2):
			raise UnsupportedTransformError(element_location, "translate() needs 1 or 2 args")
		tx = args[0]
		ty = args[1] if len(args) == 2 else 0.0
		return (1.0, 0.0, 0.0, 1.0, tx, ty)
	if name == "scale":
		# scale(sx [sy]); sy defaults to sx.
		if len(args) not in (1, 2):
			raise UnsupportedTransformError(element_location, "scale() needs 1 or 2 args")
		sx = args[0]
		sy = args[1] if len(args) == 2 else sx
		return (sx, 0.0, 0.0, sy, 0.0, 0.0)
	if name == "rotate":
		# rotate(angle [cx cy]); rotation about (cx,cy) defaults to origin.
		if len(args) not in (1, 3):
			raise UnsupportedTransformError(element_location, "rotate() needs 1 or 3 args")
		angle = math.radians(args[0])
		cos = math.cos(angle)
		sin = math.sin(angle)
		cx = args[1] if len(args) == 3 else 0.0
		cy = args[2] if len(args) == 3 else 0.0
		# rotate(a,cx,cy) == translate(cx,cy) rotate(a) translate(-cx,-cy).
		e = (1.0 - cos) * cx + sin * cy
		f = (1.0 - cos) * cy - sin * cx
		return (cos, sin, -sin, cos, e, f)
	if name == "skewX":
		if len(args) != 1:
			raise UnsupportedTransformError(element_location, "skewX() needs 1 arg")
		return (1.0, 0.0, math.tan(math.radians(args[0])), 1.0, 0.0, 0.0)
	if name == "skewY":
		if len(args) != 1:
			raise UnsupportedTransformError(element_location, "skewY() needs 1 arg")
		return (1.0, math.tan(math.radians(args[0])), 0.0, 1.0, 0.0, 0.0)
	raise UnsupportedTransformError(element_location, f"unsupported function {name}")


#============================================
def multiply_matrices(a: tuple[float, ...], b: tuple[float, ...]) -> tuple[float, ...]:
	"""Multiply two affine matrices (a then b applied as a*b on column vectors).

	Ported from svgo multiplyTransformMatrices. The result transforms a point by
	first b, then a (standard matrix product), so feeding a left-to-right
	transform list through reduce gives the correct composed transform.

	Args:
		a: Left 6-tuple matrix.
		b: Right 6-tuple matrix.

	Returns:
		The composed 6-tuple matrix.
	"""
	result = (
		a[0] * b[0] + a[2] * b[1],
		a[1] * b[0] + a[3] * b[1],
		a[0] * b[2] + a[2] * b[3],
		a[1] * b[2] + a[3] * b[3],
		a[0] * b[4] + a[2] * b[5] + a[4],
		a[1] * b[4] + a[3] * b[5] + a[5],
	)
	return result


#============================================
def transforms_multiply(items: list[tuple[str, tuple[float, ...]]], element_location: str) -> tuple[float, ...]:
	"""Compose an ordered transform list into a single matrix.

	Ported from svgo transformsMultiply. Each item is converted to a matrix and
	the matrices are multiplied left to right (outermost-to-element order), which
	is the order SVG applies a transform="A B C" list.

	Args:
		items: Ordered (name, args) list from parse_transform_list.
		element_location: XPath-like location for error reporting.

	Returns:
		The single composed 6-tuple matrix (identity when the list is empty).
	"""
	matrix = IDENTITY_MATRIX
	for index, (name, args) in enumerate(items):
		m = transform_to_matrix(name, args, element_location)
		if index == 0:
			matrix = m
		else:
			matrix = multiply_matrices(matrix, m)
	return matrix


#============================================
def matrix_is_identity(matrix: tuple[float, ...], tol: float = 1e-12) -> bool:
	"""Return True when the matrix is (within tol) the identity transform."""
	return all(abs(matrix[i] - IDENTITY_MATRIX[i]) <= tol for i in range(6))


#============================================
def transform_point(matrix: tuple[float, ...], x: float, y: float) -> tuple[float, float]:
	"""Apply an affine matrix to an absolute point. Ported from svgo transformAbsolutePoint."""
	nx = matrix[0] * x + matrix[2] * y + matrix[4]
	ny = matrix[1] * x + matrix[3] * y + matrix[5]
	return nx, ny


#============================================
def transform_arc(
	cur_x: float, cur_y: float, arc: tuple[float, ...], matrix: tuple[float, ...],
) -> tuple[float, float, float, float, float]:
	"""Recompute an elliptical-arc's (rx, ry, x-axis-rotation, large, sweep) under a matrix.

	Ported BY HAND from svgo plugins/_transforms.js transformArc. Represents the
	ellipse as a matrix, multiplies by the transform, and uses an SVD to recover
	the new rx, ry, and rotation. Flips the sweep flag when the transform mirrors
	the coordinate system (determinant sign change: matrix[0]<0 XOR matrix[3]<0).
	The arc endpoint is transformed separately by the caller.

	Args:
		cur_x, cur_y: Absolute arc start point (previous pen position).
		arc: The seven absolute arc params (rx, ry, rot_deg, large, sweep, x, y).
		matrix: The composed 6-tuple affine matrix.

	Returns:
		Tuple (new_rx, new_ry, new_rot_deg, large_flag, sweep_flag).
	"""
	# Displacement from arc start to arc end (svgo works in this local frame).
	x = arc[5] - cur_x
	y = arc[6] - cur_y
	a = arc[0]
	b = arc[1]
	rot = math.radians(arc[2])
	cos = math.cos(rot)
	sin = math.sin(rot)
	large = arc[3]
	sweep = arc[4]
	# Correct out-of-range radii exactly as svgo does (skip when radius is 0).
	if a > 0.0 and b > 0.0:
		h = (
			math.pow(x * cos + y * sin, 2) / (4.0 * a * a)
			+ math.pow(y * cos - x * sin, 2) / (4.0 * b * b)
		)
		if h > 1.0:
			h = math.sqrt(h)
			a *= h
			b *= h
	# Ellipse-as-matrix, then composed with the transform.
	ellipse = (a * cos, a * sin, -b * sin, b * cos, 0.0, 0.0)
	m = multiply_matrices(matrix, ellipse)
	# SVD of the 2x2 part to recover major/minor axes and rotation.
	last_col = m[2] * m[2] + m[3] * m[3]
	square_sum = m[0] * m[0] + m[1] * m[1] + last_col
	root = math.hypot(m[0] - m[3], m[1] + m[2]) * math.hypot(m[0] + m[3], m[1] - m[2])
	if root == 0.0:
		# Degenerates to a circle.
		new_rx = math.sqrt(square_sum / 2.0)
		new_ry = new_rx
		new_rot_deg = 0.0
	else:
		major_axis_sqr = (square_sum + root) / 2.0
		minor_axis_sqr = (square_sum - root) / 2.0
		major = abs(major_axis_sqr - last_col) > 1e-6
		sub = (major_axis_sqr if major else minor_axis_sqr) - last_col
		rows_sum = m[0] * m[2] + m[1] * m[3]
		term1 = m[0] * sub + m[2] * rows_sum
		term2 = m[1] * sub + m[3] * rows_sum
		new_rx = math.sqrt(major_axis_sqr)
		new_ry = math.sqrt(minor_axis_sqr)
		# Sign selection mirrors svgo's conditional exactly.
		sign = -1.0 if (term2 < 0.0 if major else term1 > 0.0) else 1.0
		numer = term1 if major else term2
		hyp = math.hypot(term1, term2)
		if hyp == 0.0:
			# Degenerate case: both terms are zero -> no well-defined rotation angle.
			# Emit 0 degrees (safe fallback; the arc is already degenerate).
			new_rot_deg = 0.0
		else:
			new_rot_deg = sign * math.degrees(math.acos(numer / hyp))
	# Flip the sweep flag on a single-axis mirror (determinant sign change).
	if (matrix[0] < 0.0) != (matrix[3] < 0.0):
		sweep = 1.0 - sweep
	return new_rx, new_ry, new_rot_deg, large, sweep


#============================================
def apply_matrix_to_segments(
	segments: list[PathSegment], matrix: tuple[float, ...],
) -> list[PathSegment]:
	"""Apply an affine matrix to a list of ABSOLUTE path segments.

	The segments must already be absolute (parse_path_to_absolute output: only
	M/L/C/Q/A/Z, with H/V already folded into L). Each endpoint and control point
	is transformed; arcs go through transform_arc for new radii/rotation/sweep.

	Args:
		segments: Absolute PathSegment list.
		matrix: The composed 6-tuple affine matrix.

	Returns:
		A new list of transformed PathSegments (input is not mutated; PathSegment
		is frozen).
	"""
	out: list[PathSegment] = []
	cur_x = 0.0
	cur_y = 0.0
	start_x = 0.0
	start_y = 0.0
	for seg in segments:
		cmd = seg.cmd
		nums = seg.nums
		if cmd == "M":
			nx, ny = transform_point(matrix, nums[0], nums[1])
			out.append(PathSegment("M", (nx, ny)))
			cur_x, cur_y = nums[0], nums[1]
			start_x, start_y = nums[0], nums[1]
		elif cmd == "L":
			nx, ny = transform_point(matrix, nums[0], nums[1])
			out.append(PathSegment("L", (nx, ny)))
			cur_x, cur_y = nums[0], nums[1]
		elif cmd == "C":
			x1, y1 = transform_point(matrix, nums[0], nums[1])
			x2, y2 = transform_point(matrix, nums[2], nums[3])
			ex, ey = transform_point(matrix, nums[4], nums[5])
			out.append(PathSegment("C", (x1, y1, x2, y2, ex, ey)))
			cur_x, cur_y = nums[4], nums[5]
		elif cmd == "Q":
			x1, y1 = transform_point(matrix, nums[0], nums[1])
			ex, ey = transform_point(matrix, nums[2], nums[3])
			out.append(PathSegment("Q", (x1, y1, ex, ey)))
			cur_x, cur_y = nums[2], nums[3]
		elif cmd == "A":
			rx, ry, rot_deg, large, sweep = transform_arc(cur_x, cur_y, nums, matrix)
			ex, ey = transform_point(matrix, nums[5], nums[6])
			out.append(PathSegment("A", (rx, ry, rot_deg, large, sweep, ex, ey)))
			cur_x, cur_y = nums[5], nums[6]
		elif cmd == "Z":
			out.append(PathSegment("Z", ()))
			cur_x, cur_y = start_x, start_y
	return out


#============================================
def shape_to_segments(elem: lxml.etree._Element, element_location: str) -> list[PathSegment] | None:
	"""Convert a basic shape element to an equivalent absolute PathSegment list.

	This flattens a transform onto a non-path shape (so the
	transform can be removed and the invariant holds). It covers rect (sharp and
	rounded), circle, ellipse, line, polyline, and polygon. The path converter owns the
	general transform-free shape->path DOM rewrite and may reuse this helper.

	A circle/ellipse is emitted as two arc halves; a rounded rect uses arc
	corners. These are the same primitives the bbox math already solves exactly.

	Args:
		elem: The shape element.
		element_location: XPath-like location for error reporting.

	Returns:
		Absolute PathSegment list, or None when the shape has no usable geometry
		(absent required attributes / non-user unit handled by element_bbox).
	"""
	tag = local_name(elem.tag)
	if tag == "path":
		d_attr = elem.get("d")
		if not d_attr:
			return None
		return parse_path_to_absolute(d_attr)
	if tag == "rect":
		x = parse_float(elem.get("x"))
		y = parse_float(elem.get("y"))
		w = parse_float_required(elem.get("width"))
		h = parse_float_required(elem.get("height"))
		if w is _UNIT_SENTINEL or h is _UNIT_SENTINEL:
			raise UnsupportedUnitError(element_location)
		if w is None or h is None:
			return None
		w_f = float(w)
		h_f = float(h)
		# Resolve corner radii (rx/ry); per spec each defaults to the other.
		rx_raw = parse_float_required(elem.get("rx"))
		ry_raw = parse_float_required(elem.get("ry"))
		if rx_raw is _UNIT_SENTINEL or ry_raw is _UNIT_SENTINEL:
			raise UnsupportedUnitError(element_location)
		rx = float(rx_raw) if isinstance(rx_raw, float) else None
		ry = float(ry_raw) if isinstance(ry_raw, float) else None
		if rx is None and ry is not None:
			rx = ry
		if ry is None and rx is not None:
			ry = rx
		if rx is None:
			rx = 0.0
		if ry is None:
			ry = 0.0
		# Clamp radii to half the side length (SVG spec).
		rx = min(rx, w_f / 2.0)
		ry = min(ry, h_f / 2.0)
		return _rect_segments(x, y, w_f, h_f, rx, ry)
	if tag == "circle":
		cx = parse_float(elem.get("cx"))
		cy = parse_float(elem.get("cy"))
		r = parse_float_required(elem.get("r"))
		if r is _UNIT_SENTINEL:
			raise UnsupportedUnitError(element_location)
		if r is None:
			return None
		r_f = float(r)
		return _ellipse_segments(cx, cy, r_f, r_f)
	if tag == "ellipse":
		cx = parse_float(elem.get("cx"))
		cy = parse_float(elem.get("cy"))
		rx_raw = parse_float_required(elem.get("rx"))
		ry_raw = parse_float_required(elem.get("ry"))
		if rx_raw is _UNIT_SENTINEL or ry_raw is _UNIT_SENTINEL:
			raise UnsupportedUnitError(element_location)
		if rx_raw is None or ry_raw is None:
			return None
		return _ellipse_segments(cx, cy, float(rx_raw), float(ry_raw))
	if tag == "line":
		has_any = any(elem.get(a) is not None for a in ("x1", "y1", "x2", "y2"))
		if not has_any:
			return None
		x1 = parse_float(elem.get("x1"))
		y1 = parse_float(elem.get("y1"))
		x2 = parse_float(elem.get("x2"))
		y2 = parse_float(elem.get("y2"))
		return [PathSegment("M", (x1, y1)), PathSegment("L", (x2, y2))]
	if tag in {"polyline", "polygon"}:
		points = parse_points(elem.get("points", ""))
		if not points:
			return None
		segs: list[PathSegment] = [PathSegment("M", (points[0][0], points[0][1]))]
		for px, py in points[1:]:
			segs.append(PathSegment("L", (px, py)))
		if tag == "polygon":
			segs.append(PathSegment("Z", ()))
		return segs
	return None


#============================================
def _rect_segments(x: float, y: float, w: float, h: float, rx: float, ry: float) -> list[PathSegment]:
	"""Build absolute path segments for a rect, sharp or rounded.

	Sharp rect (rx==0 or ry==0) is four lines. Rounded rect uses four quarter
	arcs (sweep=1, large=0) at the corners, matching svgo convertShapeToPath.
	"""
	if rx <= 0.0 or ry <= 0.0:
		return [
			PathSegment("M", (x, y)),
			PathSegment("L", (x + w, y)),
			PathSegment("L", (x + w, y + h)),
			PathSegment("L", (x, y + h)),
			PathSegment("Z", ()),
		]
	# Rounded rectangle: start after the top-left horizontal radius, then walk
	# clockwise placing a quarter-arc at each corner.
	segs = [
		PathSegment("M", (x + rx, y)),
		PathSegment("L", (x + w - rx, y)),
		PathSegment("A", (rx, ry, 0.0, 0.0, 1.0, x + w, y + ry)),
		PathSegment("L", (x + w, y + h - ry)),
		PathSegment("A", (rx, ry, 0.0, 0.0, 1.0, x + w - rx, y + h)),
		PathSegment("L", (x + rx, y + h)),
		PathSegment("A", (rx, ry, 0.0, 0.0, 1.0, x, y + h - ry)),
		PathSegment("L", (x, y + ry)),
		PathSegment("A", (rx, ry, 0.0, 0.0, 1.0, x + rx, y)),
		PathSegment("Z", ()),
	]
	return segs


#============================================
def _ellipse_segments(cx: float, cy: float, rx: float, ry: float) -> list[PathSegment]:
	"""Build absolute path segments for a circle/ellipse using two half arcs."""
	segs = [
		PathSegment("M", (cx - rx, cy)),
		PathSegment("A", (rx, ry, 0.0, 1.0, 0.0, cx + rx, cy)),
		PathSegment("A", (rx, ry, 0.0, 1.0, 0.0, cx - rx, cy)),
		PathSegment("Z", ()),
	]
	return segs


# Presentation attributes that carry url(#id) paint/clip references. These are
# copied verbatim when a shape is rewritten to a <path>; their referenced
# geometry (gradients/clips) lives in defs and is paint-space exempt.
# Note: "transform" is intentionally ABSENT -- _convert_shape_element_to_path
# always strips the transform (geometry is baked into the path d), so copying
# it would re-introduce the very attribute the flattening pass just removed.
_COPY_THROUGH_ATTRS = frozenset({
	"fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin",
	"stroke-miterlimit", "stroke-dasharray", "stroke-dashoffset", "stroke-opacity",
	"fill-opacity", "fill-rule", "opacity", "clip-path", "clip-rule", "mask",
	"filter", "vector-effect", "style", "class", "id", "data-name", "display",
	"visibility", "color", "data-vlab-normalizer-boundary-token",
})


#============================================
def _stroke_distortion_unsafe(elem: lxml.etree._Element, matrix: tuple[float, ...]) -> bool:
	"""Return True when applying matrix to a stroked element would distort the stroke.

	Ported from svgo applyTransforms: a stroke can only be applied when the matrix
	is a uniform scale plus rotation, optionally with a single-axis flip. That is
	exactly when (a==d and b==-c) OR (a==-d and b==c). A non-uniform scale or skew
	would turn a round stroke into an ellipse, which v3 must never emit. A visible
	stroke under such a matrix is refused upstream as UNSUPPORTED_TRANSFORM.

	Args:
		elem: The element being flattened.
		matrix: The composed 6-tuple affine matrix.

	Returns:
		True when the element has a visible stroke and the matrix is non-uniform
		or skewed (so flattening would distort the stroke); False otherwise.
	"""
	stroke = elem.get("stroke")
	# An inline style may also set stroke; check it minimally (inline-only cascade).
	if stroke is None:
		style = elem.get("style") or ""
		stroke_match = re.search(r"(?:^|;)\s*stroke\s*:\s*([^;]+)", style)
		if stroke_match:
			stroke = stroke_match.group(1).strip()
	if stroke is None or stroke == "none":
		return False
	a, b, c, d = matrix[0], matrix[1], matrix[2], matrix[3]
	uniform = (abs(a - d) < 1e-9 and abs(b + c) < 1e-9)
	flipped = (abs(a + d) < 1e-9 and abs(b - c) < 1e-9)
	return not (uniform or flipped)


#============================================
def _is_geometry_transform_attr(elem: lxml.etree._Element) -> str | None:
	"""Return the geometry-affecting transform attribute value, or None.

	gradientTransform and patternTransform are paint-space and are NOT returned
	(they are exempt from the canonical invariant). Only the plain `transform`
	attribute on a drawable element / group affects geometry.
	"""
	val = elem.get("transform")
	if val is not None and val.strip() != "":
		return val
	return None


#============================================
# Matches a stroke-width declaration inside an inline style attribute, capturing
# the numeric value (user units; svgo only scales unitless / px stroke widths).
_STYLE_STROKE_WIDTH_RE = re.compile(
	r"(stroke-width\s*:\s*)([-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?)(\s*(?:px)?\s*)(;|$)",
	re.IGNORECASE,
)


#============================================
def _scale_stroke_width(elem: lxml.etree._Element, scale: float) -> None:
	"""Multiply an element's stroke-width by a uniform scale factor.

	Handles both the presentation attribute (stroke-width="...") and an inline
	style declaration (style="...;stroke-width:...;..."). Only user-unit values
	(unitless or px) are scaled; a non-user unit is left untouched (such files are
	rejected elsewhere for unsupported units). When no stroke-width is declared the
	SVG default is 1 user unit; that case is left implicit and unscaled because the
	stroke-distortion guard already refuses visibly-stroked non-uniform transforms,
	and a default-width hairline change is below the visual-integrity threshold.

	Args:
		elem: The drawable element whose geometry is being baked.
		scale: The uniform scale factor (matrix major-axis length).
	"""
	# Identity scale changes nothing; skip to avoid reformatting attributes.
	if abs(scale - 1.0) < 1e-12:
		return
	# Presentation attribute form.
	attr_val = elem.get("stroke-width")
	if attr_val is not None:
		parsed = parse_float_required(attr_val)
		if isinstance(parsed, float):
			elem.set("stroke-width", fmt_precise(parsed * scale))
	# Inline style form. Rewrite the first stroke-width:NUM occurrence in place.
	style = elem.get("style")
	if style is not None and "stroke-width" in style:
		def _repl(match: "re.Match[str]") -> str:
			scaled = float(match.group(2)) * scale
			return match.group(1) + fmt_precise(scaled) + match.group(3) + match.group(4)
		new_style = _STYLE_STROKE_WIDTH_RE.sub(_repl, style, count=1)
		elem.set("style", new_style)


#============================================
def _flatten_one(elem: lxml.etree._Element, matrix: tuple[float, ...]) -> None:
	"""Bake an already-composed matrix into one drawable element's geometry.

	The element's own transform attribute (if any) must already be folded into
	matrix by the caller. After this call the element carries no geometry
	transform.

	Args:
		elem: A drawable shape/path element (not a container).
		matrix: The composed 6-tuple matrix from root down to this element.

	Raises:
		UnsupportedTransformError: When a visible stroke would be distorted.
		NonScalingStrokeError: When a non-scaling stroke cannot be resolved.
		UnsupportedUnitError: When a required size attr carries a non-user unit.
	"""
	location = elem.getroottree().getpath(elem)
	# A material bounds anchor is a hidden runtime resource, not visible artwork.
	# The renderer deliberately reads SVGRectElement geometry instead of getBBox()
	# because getBBox() on display:none content is browser-dependent.  Preserve a
	# valid authored rect in root coordinates; a non-identity own or inherited
	# transform would require path conversion, so reject it through the normal
	# transform path instead of emitting a runtime-incompatible anchor.
	if (
		local_name(elem.tag) == "rect"
		and elem.get("id") == RUNTIME_BOUNDS_RECT_ID
	):
		if not matrix_is_identity(matrix):
			raise UnsupportedTransformError(
				location,
				"anchor_liquid_bounds must be an untransformed root-coordinate rect",
			)
		if elem.get("transform") is not None:
			del elem.attrib["transform"]
		return
	# If the composed matrix is identity, only strip the (now-redundant) attr.
	if matrix_is_identity(matrix):
		if elem.get("transform") is not None:
			del elem.attrib["transform"]
		return
	# Non-scaling stroke under a transform that changes scale is unresolved here.
	if elem.get("vector-effect") == "non-scaling-stroke":
		scale = math.hypot(matrix[0], matrix[1])
		if abs(scale - 1.0) > 1e-9:
			raise NonScalingStrokeError(location)
	# A visible stroke under a non-uniform / skew matrix would be distorted.
	if _stroke_distortion_unsafe(elem, matrix):
		raise UnsupportedTransformError(
			location, "non-uniform/skew transform on a stroked element"
		)
	# Scale stroke-width by the matrix's uniform scale factor. Baking the matrix
	# into geometry shrinks/grows the shape, so a fixed stroke-width would render at
	# the wrong thickness (the cpu.svg mesh-greyout bug: a stroke authored under a
	# 0.415 scale stayed at full width after flatten and filled the holes). The
	# distortion guard above guarantees the matrix is a uniform scale + rotation
	# (optionally flipped) whenever a visible stroke is present, so a single scalar
	# scale is exact. Non-scaling-stroke elements were handled (and rejected when
	# scale != 1) above, so they never reach here with a scaling matrix.
	_scale_stroke_width(elem, math.hypot(matrix[0], matrix[1]))
	segments = shape_to_segments(elem, location)
	if segments is None:
		# No drawable geometry (e.g. shape missing required attrs). Just drop the
		# transform attribute so the invariant holds; bbox treats it as empty.
		if elem.get("transform") is not None:
			del elem.attrib["transform"]
		return
	flattened = apply_matrix_to_segments(segments, matrix)
	tag = local_name(elem.tag)
	if tag == "path":
		# Rewrite path d in place; keep all other attributes.
		elem.set("d", path_segments_to_d(flattened))
		if elem.get("transform") is not None:
			del elem.attrib["transform"]
		return
	# Convert a basic shape element into a <path>, preserving paint/ref attributes.
	_convert_shape_element_to_path(elem, flattened)


#============================================
def _convert_shape_element_to_path(elem: lxml.etree._Element, segments: list[PathSegment]) -> None:
	"""Rewrite a basic-shape element in place as a <path> with flattened geometry.

	Preserves id/data-name, paint attributes, and url(#) references so reference
	integrity is unaffected. Shape-specific geometry attributes (x/width/cx/r/...)
	are dropped because they are now encoded in the path d. The transform
	attribute is removed (geometry is baked in).

	Args:
		elem: The shape element to convert.
		segments: The already-flattened absolute path segments.
	"""
	# Capture attributes to carry forward (paint, refs, identity), drop geometry.
	carried: list[tuple[str, str]] = []
	for name, value in elem.attrib.items():
		local = local_name(name) if isinstance(name, str) else name
		if local == "transform":
			continue
		if local in _COPY_THROUGH_ATTRS:
			carried.append((name, value))
	# Retag the element as a path in the SVG namespace and reset its attributes.
	elem.tag = f"{{{SVG_NS}}}path"
	for name in list(elem.attrib):
		del elem.attrib[name]
	for name, value in carried:
		elem.set(name, value)
	elem.set("d", path_segments_to_d(segments))


# Paint elements whose userSpaceOnUse coordinates live in the same coordinate
# space as the referencing geometry. When that geometry is moved by transform
# flattening, the paint must be moved with it or the paint resolves out of
# bounds and collapses to its nearest stop color (the cpu.svg grey-out bug).
_USERSPACE_PAINT_TAGS = frozenset({"linearGradient", "radialGradient", "pattern"})


#============================================
def _element_paint_ref_ids(elem: lxml.etree._Element) -> list[str]:
	"""Return the url(#id) fragment ids referenced by an element's fill/stroke.

	Resolves fill and stroke through the inline-only cascade (inline style= wins
	over the presentation attribute of the same name), matching the v3 CSS scope.
	Only paint references (fill/stroke) are returned; clip/mask/filter refs are
	handled by their own passes and are paint-space exempt here.

	Args:
		elem: The drawable element being flattened.

	Returns:
		List of fragment ids (without the leading #) for each url(#id) paint ref.
	"""
	ids: list[str] = []
	for prop in ("fill", "stroke"):
		value = _resolved_property(elem, prop)
		if not value:
			continue
		match = _URL_REF_RE.search(value)
		if match is not None:
			ids.append(match.group(1))
	return ids


#============================================
def _userspace_paint_defs(root: lxml.etree._Element) -> dict[str, lxml.etree._Element]:
	"""Map id -> paint element for every userSpaceOnUse gradient/pattern in the tree.

	A gradient defaults to gradientUnits=objectBoundingBox and a pattern defaults
	to patternUnits=objectBoundingBox; only an explicit userSpaceOnUse value puts
	the paint in absolute (geometry) coordinate space and therefore needs to move
	with flattened geometry. objectBoundingBox paints are bbox-relative and
	transform-invariant, so they are not collected.

	Args:
		root: The parsed SVG root element.

	Returns:
		Dict mapping fragment id to the paint element (userSpaceOnUse only).
	"""
	defs: dict[str, lxml.etree._Element] = {}
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		tag = local_name(elem.tag)
		if tag not in _USERSPACE_PAINT_TAGS:
			continue
		paint_id = elem.get("id")
		if paint_id is None:
			continue
		# gradientUnits applies to gradients; patternUnits applies to patterns.
		units_attr = "patternUnits" if tag == "pattern" else "gradientUnits"
		units = elem.get(units_attr)
		if units is not None and units.strip() == "userSpaceOnUse":
			defs[paint_id] = elem
	return defs


#============================================
def _collect_paint_referrers(
	root: lxml.etree._Element,
) -> dict[str, list[tuple[lxml.etree._Element, tuple[float, ...]]]]:
	"""Build paint-id -> [(referring element, composed matrix), ...] before flattening.

	Walks the tree exactly as _flatten_recurse does (composing the ancestor
	transform chain plus each element's own transform), recording the matrix that
	would be baked into each drawable element. For every paint reference on that
	element it appends a (element, matrix) entry under the paint's id. Built BEFORE
	any geometry mutation so the recorded matrices are the true flatten matrices,
	and so shared-paint safety can be decided up front.

	Defs content (gradients/clips/patterns) is paint/clip space and is skipped, so
	a paint referenced from inside another def is not counted as a geometry
	referrer.

	Args:
		root: The parsed SVG root element.

	Returns:
		Dict mapping paint fragment id to a list of (element, composed-matrix)
		tuples for each geometry element that references it.
	"""
	referrers: dict[str, list[tuple[lxml.etree._Element, tuple[float, ...]]]] = {}
	_collect_referrers_recurse(root, IDENTITY_MATRIX, False, referrers)
	return referrers


#============================================
def _collect_referrers_recurse(
	elem: lxml.etree._Element,
	parent_matrix: tuple[float, ...],
	in_defs: bool,
	referrers: dict[str, list[tuple[lxml.etree._Element, tuple[float, ...]]]],
) -> None:
	"""Recursive worker for _collect_paint_referrers (mirrors _flatten_recurse)."""
	if not isinstance(elem.tag, str):
		return
	tag = local_name(elem.tag)
	entering_defs = in_defs or tag == "defs"
	own_matrix = parent_matrix
	own_transform = _is_geometry_transform_attr(elem) if not entering_defs else None
	if own_transform is not None:
		location = elem.getroottree().getpath(elem)
		items = parse_transform_list(own_transform, location)
		this_matrix = transforms_multiply(items, location)
		own_matrix = multiply_matrices(parent_matrix, this_matrix)
	# Record paint references on drawable leaves with their composed matrix.
	if (not entering_defs) and tag in SHAPE_TAGS:
		for paint_id in _element_paint_ref_ids(elem):
			referrers.setdefault(paint_id, []).append((elem, own_matrix))
		return
	for child in list(elem):
		_collect_referrers_recurse(child, own_matrix, entering_defs, referrers)


#============================================
def _matrix_to_transform_str(matrix: tuple[float, ...]) -> str:
	"""Serialize a 6-tuple affine matrix as an SVG matrix(...) transform string."""
	parts = [fmt_precise(component) for component in matrix]
	result = "matrix(" + ",".join(parts) + ")"
	return result


#============================================
def transform_userspace_paints(root: lxml.etree._Element) -> None:
	"""Move userSpaceOnUse gradients/patterns in sync with flattened geometry (Fix B).

	When transform flattening bakes a non-identity matrix M into an element that
	paints with a userSpaceOnUse gradient or pattern, the paint's absolute
	coordinates must move by the same M or the paint resolves out of bounds and
	collapses to its nearest stop color. The correct, paint-space-preserving fix
	is to prepend M to the paint's gradientTransform/patternTransform
	(new = M * existing); the paint's own coordinates and stops are left untouched.

	Shared-paint safety: a paint referenced by more than one geometry element, or
	by elements whose composed matrices differ, cannot have a single matrix baked
	into the shared def. Such a file is rejected upstream as UNSUPPORTED_TRANSFORM.

	Must run BEFORE the geometry recursion of flatten_transforms so the recorded
	matrices match the matrices the recursion will bake into geometry.

	Args:
		root: The parsed SVG root element. Modified in place.

	Raises:
		UnsupportedTransformError: When a userSpaceOnUse paint is shared by
			geometry under differing transforms (cannot bake one matrix safely).
	"""
	paint_defs = _userspace_paint_defs(root)
	if not paint_defs:
		return
	referrers = _collect_paint_referrers(root)
	for paint_id, paint_elem in paint_defs.items():
		uses = referrers.get(paint_id, [])
		# Only the non-identity referrers actually move the paint.
		moving = [(elem, m) for (elem, m) in uses if not matrix_is_identity(m)]
		if not moving:
			# Paint is unreferenced or only referenced by untransformed geometry;
			# its coordinates already align with the (unmoved) geometry.
			continue
		first_matrix = moving[0][1]
		# Shared-paint safety: more than one referrer always rejects regardless of
		# matrix values (one bake cannot satisfy two different element positions).
		# The divergence loop below only runs for the single-referrer case (len==1),
		# where it is a tautology and never fires; it is kept for defensive clarity.
		shared_unsafe = len(uses) > 1
		if not shared_unsafe:
			for _elem, matrix in uses:
				if not _matrices_equal(matrix, first_matrix):
					shared_unsafe = True
					break
		if shared_unsafe:
			location = paint_elem.getroottree().getpath(paint_elem)
			raise UnsupportedTransformError(
				location,
				"a userSpaceOnUse paint is shared by elements under differing "
				"transforms; pre-flatten the transform or give each element its "
				"own paint",
			)
		# Single-use paint: prepend M to its existing paint transform.
		transform_attr = "patternTransform" if local_name(paint_elem.tag) == "pattern" else "gradientTransform"
		existing = paint_elem.get(transform_attr)
		composed = first_matrix
		if existing is not None and existing.strip() != "":
			location = paint_elem.getroottree().getpath(paint_elem)
			items = parse_transform_list(existing, location)
			existing_matrix = transforms_multiply(items, location)
			composed = multiply_matrices(first_matrix, existing_matrix)
		paint_elem.set(transform_attr, _matrix_to_transform_str(composed))


#============================================
def _matrices_equal(a: tuple[float, ...], b: tuple[float, ...], tol: float = 1e-9) -> bool:
	"""Return True when two 6-tuple affine matrices are equal within tol."""
	return all(abs(a[i] - b[i]) <= tol for i in range(6))


#============================================
def flatten_transforms(root: lxml.etree._Element) -> None:
	"""Flatten every geometry transform into absolute root-coordinate geometry.

	Walks the tree from the root, composing each element's transform with its
	ancestor-group chain (outermost-to-element order). Drawable leaf elements
	(paths and basic shapes) get the composed matrix baked into their geometry
	and their transform attribute removed; container groups have their transform
	attribute removed after their children are flattened. Content inside <defs>
	(gradients, clipPaths, patterns) is NOT flattened here: it is paint/clip
	space, handled by other WPs, and gradientTransform/patternTransform are
	invariant-exempt.

	After this call the canonical invariant holds for visible geometry: no
	geometry-affecting transform remains on any normalized visible element.

	Args:
		root: The parsed SVG root element. Modified in place.

	Raises:
		UnsupportedTransformError / NonScalingStrokeError / UnsupportedUnitError:
			propagated from _flatten_one for the caller to turn into a rejection.
	"""
	# Depth-first recursion carrying the composed ancestor matrix. The root <svg>
	# element's own transform attribute (non-standard in SVG) IS flattened: it is
	# treated as the starting matrix for the root's children, and after all
	# children are flattened the root-level transform attribute is removed.
	# _flatten_recurse handles this transparently because the root is passed in
	# as `elem` with parent_matrix=IDENTITY; its own transform is composed in and
	# then stripped after its children are processed.
	#
	# Fix B: before mutating any geometry, move every userSpaceOnUse gradient /
	# pattern in sync with the transforms about to be baked into the geometry that
	# references it. This must precede the recursion so the matrices it reads match
	# the matrices the recursion will apply. It may raise UnsupportedTransformError
	# for a shared paint under differing transforms, in which case no geometry has
	# been touched yet and the caller rejects the file with no output.
	transform_userspace_paints(root)
	_flatten_recurse(root, IDENTITY_MATRIX, in_defs=False)


#============================================
def _flatten_recurse(
	elem: lxml.etree._Element, parent_matrix: tuple[float, ...], in_defs: bool,
) -> None:
	"""Recursive worker for flatten_transforms.

	Args:
		elem: Current element.
		parent_matrix: Composed matrix of all ancestors above elem.
		in_defs: True when elem lives inside a <defs> subtree (paint/clip space,
			not flattened).
	"""
	if not isinstance(elem.tag, str):
		# Comment / PI: nothing to flatten, but descend is unnecessary.
		return
	tag = local_name(elem.tag)
	entering_defs = in_defs or tag == "defs"
	# Compose this element's own transform with the inherited matrix.
	own_matrix = parent_matrix
	own_transform = _is_geometry_transform_attr(elem) if not entering_defs else None
	if own_transform is not None:
		location = elem.getroottree().getpath(elem)
		items = parse_transform_list(own_transform, location)
		this_matrix = transforms_multiply(items, location)
		own_matrix = multiply_matrices(parent_matrix, this_matrix)

	# Drawable leaves carry the composed matrix into their geometry.
	# text is not in SHAPE_TAGS (rejected by classifier before this runs).
	if (not entering_defs) and tag in SHAPE_TAGS:
		_flatten_one(elem, own_matrix)
		# A leaf shape has no element children to recurse into.
		return

	# Recurse into children with the composed matrix. Copy the child list first
	# because _flatten_one may retag shape children (changing the live list).
	for child in list(elem):
		_flatten_recurse(child, own_matrix, entering_defs)

	# After children are flattened, the container's transform is fully baked in;
	# remove it so no geometry transform remains (groups outside defs only).
	if (not entering_defs) and own_transform is not None:
		if elem.get("transform") is not None:
			del elem.attrib["transform"]


#============================================
def find_geometry_transform_violation(root: lxml.etree._Element) -> str | None:
	"""Canonical-invariant checker: locate any remaining geometry transform.

	After flatten_transforms + shape conversion, all visible geometry must be
	absolute path data in root coordinates with no geometry-affecting transform
	remaining. gradientTransform / patternTransform (paint-space) and anything
	inside <defs> are exempt.

	Args:
		root: The parsed (and normalized) SVG root element.

	Returns:
		The XPath-like location of the first violating element, or None when the
		invariant holds.
	"""
	def visit(elem: lxml.etree._Element, in_defs: bool) -> str | None:
		if not isinstance(elem.tag, str):
			return None
		tag = local_name(elem.tag)
		entering_defs = in_defs or tag == "defs"
		if not entering_defs:
			if _is_geometry_transform_attr(elem) is not None:
				return elem.getroottree().getpath(elem)
		for child in elem:
			found = visit(child, entering_defs)
			if found is not None:
				return found
		return None

	return visit(root, False)


#============================================
# Shape-to-path conversion.
#
# Math ported BY HAND from svgo (MIT) plugins/convertShapeToPath.js:
#   - rect (sharp): M/H/V/H/z template.
#   - line:         M/L template.
#   - polyline:     M + repeated L.
#   - polygon:      M + repeated L + z.
#   - circle/ellipse: two-arc trick (ported from svgo convertShapeToPath.js
#       with convertArcs=true path); v3 uses a left-right split (M cx-rx cy /
#       A cx+rx cy / A cx-rx cy / Z) from _ellipse_segments, which is
#       geometrically equivalent to svgo's top-bottom split.
#   - rounded-rect: svgo omits this case; authored here as four quarter-arcs
#       (sweep=1, large-arc=0) with straight edges between them, matching the
#       _rect_segments implementation.
# No svgo file is copied into this repo.
#============================================


#============================================
def convert_shapes_to_paths(root: lxml.etree._Element) -> None:
	"""Convert every supported shape element in the tree to an absolute <path>.

	This is the general (transform-free) shape->path DOM rewrite (A2). It runs
	AFTER flatten_transforms so all geometry is already in root coordinates.
	Shapes that already went through _flatten_one (because they had a transform)
	were already rewritten to <path>; this pass covers the remaining shapes
	(no-transform rect/circle/ellipse/line/polyline/polygon elements).

	Elements inside <defs> are NOT converted: clipPath geometry and paint-only
	shapes in defs are handled separately; converting them here would change
	the structure those WPs expect.

	Each shape's presentation attributes (fill, stroke, id, class, clip-path,
	url(#) refs, etc.) are preserved on the new <path> via _COPY_THROUGH_ATTRS
	so reference integrity and ASCII-id rewriting remain correct.

	Args:
		root: The parsed SVG root element. Modified in place.

	Raises:
		UnsupportedUnitError: When a required size attribute uses a non-user unit
			(%, mm, cm, ...). The caller should propagate this to a rejection.
	"""
	# Collect shape elements outside defs to avoid mutating the tree while
	# iterating. We need their location for UnsupportedUnitError reporting.
	shapes_to_convert: list[lxml.etree._Element] = []
	_collect_shapes(root, in_defs=False, out=shapes_to_convert)
	for elem in shapes_to_convert:
		location = elem.getroottree().getpath(elem)
		segments = shape_to_segments(elem, location)
		if segments is None:
			# Missing required attributes -- leave element as-is (treated as no
			# drawable geometry by compute_bbox, consistent with element_bbox).
			continue
		# Rewrite the element in-place as a <path> with no transform.
		_convert_shape_element_to_path(elem, segments)


#============================================
def _collect_shapes(
	elem: lxml.etree._Element,
	in_defs: bool,
	out: list[lxml.etree._Element],
) -> None:
	"""Recursively collect shape elements outside <defs> into out.

	Args:
		elem: Current element.
		in_defs: True when elem is inside a <defs> subtree.
		out: List to append matching elements to.
	"""
	if not isinstance(elem.tag, str):
		return
	tag = local_name(elem.tag)
	entering_defs = in_defs or tag == "defs"
	# Shapes in defs are paint/clip space -- skip them.
	if (
		not entering_defs
		and tag in {"rect", "circle", "ellipse", "line", "polyline", "polygon"}
		and not (tag == "rect" and elem.get("id") == RUNTIME_BOUNDS_RECT_ID)
	):
		out.append(elem)
		# Basic shapes have no element children to recurse into.
		return
	for child in elem:
		_collect_shapes(child, entering_defs, out)


#============================================
def parse_points(points: str) -> list[tuple[float, float]]:
	nums = [float(x) for x in re.findall(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?", points)]
	pairs = [(nums[i], nums[i + 1]) for i in range(0, len(nums) - 1, 2)]
	return pairs


#============================================
def format_points(points: list[tuple[float, float]], dx: float, dy: float) -> str:
	# Use fmt_precise for emitted point coordinates (A4 precision).
	return " ".join(f"{fmt_precise(x + dx)},{fmt_precise(y + dy)}" for x, y in points)


# Default stroke-related SVG property values (SVG spec).
_DEFAULT_STROKE_WIDTH = 1.0
_DEFAULT_MITERLIMIT = 4.0

# Inline style property regex: matches "prop: value" pairs (separated by ;).
_STYLE_PROP_RE = re.compile(r"(?:^|;)\s*([\w-]+)\s*:\s*([^;]+?)(?=\s*(?:;|$))")


#============================================
def _parse_inline_style(style: str) -> dict[str, str]:
	"""Parse an SVG inline style= attribute into a {prop: value} dict.

	Only parses the flat key:value structure; does not apply cascade.

	Args:
		style: The raw style= attribute value.

	Returns:
		Dict of lowercase property name to stripped value string.
	"""
	props: dict[str, str] = {}
	for match in _STYLE_PROP_RE.finditer(style):
		props[match.group(1).lower().strip()] = match.group(2).strip()
	return props


#============================================
def _resolve_stroke_props(elem: lxml.etree._Element) -> dict[str, str]:
	"""Resolve stroke presentation properties for one element (inline cascade only).

	Per the v3 support contract (CSS scope: inline-only cascade), only inline
	style= and presentation attributes are checked. Presentation attributes are
	the fallback when the inline style does not set a property. No class/stylesheet
	resolution.

	Properties resolved: stroke, stroke-width, stroke-linecap, stroke-linejoin,
	stroke-miterlimit.

	Args:
		elem: The SVG element.

	Returns:
		Dict of resolved property values. Keys present only when found on this
		element. Values are raw strings.
	"""
	# Read inline style block first (higher specificity than presentation attrs).
	style_str = elem.get("style") or ""
	inline = _parse_inline_style(style_str)
	result: dict[str, str] = {}
	stroke_props = (
		"stroke", "stroke-width", "stroke-linecap",
		"stroke-linejoin", "stroke-miterlimit",
	)
	for prop in stroke_props:
		# Inline style wins over presentation attribute.
		if prop in inline:
			result[prop] = inline[prop]
		else:
			val = elem.get(prop)
			if val is not None:
				result[prop] = val
	return result


#============================================
def _path_is_open(segments: list[PathSegment]) -> bool:
	"""Return True when a non-empty absolute path does not end with a Z segment.

	An open path has exposed endpoints that the round/square linecap extends.
	Butt linecap (SVG default) does not extend endpoints, so this only matters
	for round or square linecap values. An empty path is treated as closed
	(no endpoint extension).

	Args:
		segments: Absolute PathSegment list.

	Returns:
		True when segments is non-empty and the last segment is not Z.
	"""
	return bool(segments) and segments[-1].cmd != "Z"


#============================================
def _stroke_padded_bbox(geom_bbox: BBox, elem: lxml.etree._Element) -> BBox:
	"""Expand a geometry bbox by the visible stroke envelope for one element.

	Implements the plan A3 stroke-pad rule:
	  pad = stroke_width / 2 * max(1, miterlimit)
	  round/square linecap: open path endpoints additionally extend by
	    stroke_width / 2 on each end (captured here by including the endpoint
	    pad in the uniform bbox expansion, which is conservative for non-trivial
	    paths but correct for the bbox contract).
	  butt linecap (default): no endpoint extension.
	  dashed strokes: treated as solid envelope (same pad).
	  markers: not padded (markers are rejected by the classifier).
	  vector-effect=non-scaling-stroke: stroke is already unscaled in root coords
	    (elements that cannot be resolved are rejected by flatten_transforms before
	    bbox is computed); pad uses stroke-width directly.

	Args:
		geom_bbox: The pure geometry bbox for this element.
		elem: The SVG element (already in root coordinates after flattening).

	Returns:
		Geometry bbox expanded by the visible stroke envelope. When the element
		has no visible stroke, returns geom_bbox unchanged.
	"""
	props = _resolve_stroke_props(elem)
	stroke = props.get("stroke")
	# No stroke or explicitly none/transparent -> no pad.
	if stroke is None or stroke.lower() in {"none", "transparent"}:
		return geom_bbox

	# Resolve stroke-width (default 1 when stroke is set but width is not).
	sw_raw = props.get("stroke-width")
	if sw_raw is None:
		stroke_width = _DEFAULT_STROKE_WIDTH
	else:
		stroke_width = parse_float(sw_raw, _DEFAULT_STROKE_WIDTH)
	if stroke_width <= 0.0:
		return geom_bbox

	# Resolve miterlimit (default 4; only relevant for miter linejoin).
	linejoin = props.get("stroke-linejoin", "miter").lower()
	if linejoin == "miter":
		ml_raw = props.get("stroke-miterlimit")
		if ml_raw is None:
			miterlimit = _DEFAULT_MITERLIMIT
		else:
			miterlimit = parse_float(ml_raw, _DEFAULT_MITERLIMIT)
	else:
		miterlimit = 1.0  # round/bevel: no miter extension beyond stroke_width/2

	# Core pad: half stroke width * max(1, miterlimit).
	pad = stroke_width / 2.0 * max(1.0, miterlimit)

	# Linecap extension for open paths: round and square extend endpoints
	# by stroke_width/2. Butt (default) does not.
	linecap = props.get("stroke-linecap", "butt").lower()
	if linecap in {"round", "square"}:
		# Parse the path d to determine if it is open (needs endpoint pad).
		# By the time bbox is computed, shapes have been converted to paths,
		# so elem should be a <path>. If not, fall through without endpoint pad.
		d_attr = elem.get("d")
		if d_attr:
			segments = parse_path_to_absolute(d_attr)
			if _path_is_open(segments):
				# Round/square linecap extends each open endpoint by stroke_width/2
				# BEYOND the miter-join pad. This is additive (not max) so that an
				# open path with round/square always produces a strictly larger bbox
				# than the same path with butt linecap. Butt linecap keeps no
				# endpoint extension.
				endpoint_pad = stroke_width / 2.0
				pad += endpoint_pad

	# Expand the geometry bbox symmetrically in all four directions.
	padded = BBox(
		geom_bbox.min_x - pad,
		geom_bbox.min_y - pad,
		geom_bbox.max_x + pad,
		geom_bbox.max_y + pad,
	)
	return padded


#============================================
def _element_geometry_bbox(elem: lxml.etree._Element) -> "BBox | str | None":
	"""Compute the pure geometry bbox of a single SVG shape element (no stroke pad).

	Returns:
		BBox for a fully resolvable shape.
		_UNIT_SENTINEL (str) when a REQUIRED size attribute carries a non-user-unit
		  (%, mm, cm, in, pt, pc, em, ex).
		None for non-shape tags, hidden elements, and shapes with absent/bad
		  required attributes.
	"""
	tag = local_name(elem.tag)
	if tag not in SHAPE_TAGS:
		return None
	# Visibility checks resolve through the inline-only cascade (style= wins over
	# the presentation attribute) so style="display:none" and
	# style="fill:none;stroke:none" exclude the element from the bbox, matching
	# the bare-attribute semantics. fill:none alone with a visible stroke still
	# contributes geometry; both none -> excluded.
	if _resolved_property(elem, "display") == "none":
		return None
	if _resolved_property(elem, "fill") == "none" and _resolved_property(elem, "stroke") == "none":
		return None

	if tag == "path":
		d_attr = elem.get("d")
		if not d_attr:
			return None
		return path_bbox_from_segments(parse_path_to_absolute(d_attr))

	if tag == "rect":
		# x/y default to 0 per SVG spec; width/height are required.
		# A % or other non-user unit is an UNSUPPORTED_UNIT rejection (not phantom 0).
		x = parse_float(elem.get("x"))
		y = parse_float(elem.get("y"))
		w = parse_float_required(elem.get("width"))
		h = parse_float_required(elem.get("height"))
		if w is _UNIT_SENTINEL or h is _UNIT_SENTINEL:
			# Return the sentinel so the caller can build the rejection.
			return _UNIT_SENTINEL
		if w is None or h is None:
			return None
		# w and h are floats at this point.
		return BBox(x, y, x + float(w), y + float(h))

	if tag == "circle":
		# cx/cy default to 0 per SVG spec; r is required.
		cx = parse_float(elem.get("cx"))
		cy = parse_float(elem.get("cy"))
		r = parse_float_required(elem.get("r"))
		if r is _UNIT_SENTINEL:
			return _UNIT_SENTINEL
		if r is None:
			return None
		r_f = float(r)
		return BBox(cx - r_f, cy - r_f, cx + r_f, cy + r_f)

	if tag == "ellipse":
		# cx/cy default to 0 per SVG spec; rx/ry are required.
		cx = parse_float(elem.get("cx"))
		cy = parse_float(elem.get("cy"))
		rx = parse_float_required(elem.get("rx"))
		ry = parse_float_required(elem.get("ry"))
		if rx is _UNIT_SENTINEL or ry is _UNIT_SENTINEL:
			return _UNIT_SENTINEL
		if rx is None or ry is None:
			return None
		rx_f = float(rx)
		ry_f = float(ry)
		return BBox(cx - rx_f, cy - ry_f, cx + rx_f, cy + ry_f)

	if tag == "line":
		# If NONE of the four endpoint attrs are authored, the line contributes
		# no geometry (consistent with rect/circle required-attr handling).
		# Per SVG spec x1/y1/x2/y2 all default to 0 when absent, so if at least
		# one is authored we use that spec default for the missing ones.
		has_any = any(elem.get(a) is not None for a in ("x1", "y1", "x2", "y2"))
		if not has_any:
			return None
		x1 = parse_float(elem.get("x1"))
		y1 = parse_float(elem.get("y1"))
		x2 = parse_float(elem.get("x2"))
		y2 = parse_float(elem.get("y2"))
		return BBox(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))

	if tag in {"polyline", "polygon"}:
		points = parse_points(elem.get("points", ""))
		if not points:
			return None
		xs = [p[0] for p in points]
		ys = [p[1] for p in points]
		return BBox(min(xs), min(ys), max(xs), max(ys))

	if tag == "text":
		# Text elements are rejected by classify() (A5 TEXT_UNSUPPORTED) before
		# bbox is ever computed. Return None here so that if a text element somehow
		# reaches bbox computation it is silently skipped rather than contributing
		# a phantom zero-size point (previously v2 returned a zero-size
		# bbox as a placeholder).
		return None

	return None


#============================================
def element_bbox(elem: lxml.etree._Element) -> "BBox | str | None":
	"""Compute the stroke-padded bounding box of a single SVG shape element.

	Returns the geometry bbox expanded by the visible stroke envelope (A3).
	When the element has no visible stroke the geometry bbox is returned unchanged.

	Returns:
		BBox (possibly stroke-padded) for a fully resolvable shape.
		_UNIT_SENTINEL (str) when a REQUIRED size attribute carries a non-user-unit.
		None for non-shape tags, hidden elements, and shapes with absent/bad
		  required attributes.
	"""
	geom = _element_geometry_bbox(elem)
	# Propagate sentinel and None unchanged; only pad real BBox instances.
	if geom is None or geom is _UNIT_SENTINEL:
		return geom
	return _stroke_padded_bbox(geom, elem)


#============================================
def compute_bbox(root: lxml.etree._Element) -> BBox:
	"""Compute the drawn bounding box of every visible shape under root.

	Backend note: this iterates lxml elements but delegates all geometry math to
	the backend-agnostic helpers (element_bbox -> path_bbox_from_segments ->
	arc_extrema). Later WPs that flatten transforms feed already-flattened
	coordinates through these same helpers.

	Args:
		root: The parsed SVG root element.

	Returns:
		The union BBox of all drawable elements.

	Raises:
		ValueError: When no drawable SVG elements are found.
	"""
	bbox: BBox | None = None
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			# Skip comments and processing instructions (lxml yields these).
			continue
		# Definitions are paint, clip, and runtime-anchor resources, not rendered
		# artwork.  Their geometry must not influence the visible crop.
		if _is_definition_content(elem):
			continue
		eb = element_bbox(elem)
		if eb is None:
			continue
		if eb is _UNIT_SENTINEL:
			# A required size attribute carries a non-user unit (%, mm, cm, ...).
			# Build an XPath-like location string for the rejection report.
			location = elem.getroottree().getpath(elem)
			raise UnsupportedUnitError(location)
		bbox = eb if bbox is None else bbox.union(eb)
	if bbox is None:
		raise ValueError("No drawable SVG elements found")
	return bbox


#============================================
def _is_definition_content(elem: lxml.etree._Element) -> bool:
	"""Return True when elem is nested in a SVG <defs> resource subtree."""
	node: lxml.etree._Element | None = elem
	while node is not None:
		if isinstance(node.tag, str) and local_name(node.tag) == "defs":
			return True
		node = node.getparent()
	return False


#============================================
def _shift_userspace_paint(elem: lxml.etree._Element, dx: float, dy: float) -> None:
	"""Shift a userSpaceOnUse gradient/pattern by (dx, dy) in ROOT space.

	A userSpaceOnUse paint resolves its coordinate attributes (cx/cy/r/fx/fy or
	x1/y1/x2/y2; pattern x/y/width/height) THROUGH its gradientTransform /
	patternTransform. After transform flattening (transform_userspace_paints)
	that transform already holds the baked element matrix M, so the paint paints
	at M * coords. The crop-to-origin pass then shifts all geometry by (dx, dy)
	in root space; to keep the paint aligned, the SAME root-space shift must be
	applied to the paint OUTPUT, i.e. translate(dx, dy) is prepended to the paint
	transform (new = T(dx,dy) * existing).

	Adding (dx, dy) to the raw coordinate attributes instead is WRONG: those
	attributes are pre-transform, so the shift would be re-scaled (and re-skewed)
	by the paint transform and the paint would land off the geometry, collapsing
	to a single stop color (the cpu.svg grey-out bug). This function is the
	coordinate-preserving correction.

	Args:
		elem: The userSpaceOnUse gradient or pattern element. Modified in place.
		dx, dy: The root-space crop-to-origin shift.
	"""
	transform_attr = "patternTransform" if local_name(elem.tag) == "pattern" else "gradientTransform"
	translate = (1.0, 0.0, 0.0, 1.0, dx, dy)
	existing = elem.get(transform_attr)
	composed = translate
	if existing is not None and existing.strip() != "":
		location = elem.getroottree().getpath(elem)
		items = parse_transform_list(existing, location)
		existing_matrix = transforms_multiply(items, location)
		composed = multiply_matrices(translate, existing_matrix)
	elem.set(transform_attr, _matrix_to_transform_str(composed))


#============================================
def _is_userspace_paint_element(elem: lxml.etree._Element) -> bool:
	"""Return True for a gradient/pattern explicitly in userSpaceOnUse units."""
	tag = local_name(elem.tag)
	if tag not in _USERSPACE_PAINT_TAGS:
		return False
	units_attr = "patternUnits" if tag == "pattern" else "gradientUnits"
	units = elem.get(units_attr)
	return units is not None and units.strip() == "userSpaceOnUse"


#============================================
def shift_element(elem: lxml.etree._Element, dx: float, dy: float) -> None:
	tag = local_name(elem.tag)
	# Gradient/pattern paint elements are never shifted by adding (dx,dy) to their
	# coordinate attributes. userSpaceOnUse paints resolve THROUGH their paint
	# transform, so the crop shift is prepended to that transform instead.
	# objectBoundingBox paints (the default) use bbox-relative 0..1 fractions and
	# are crop-invariant, so they are left untouched entirely. Shifting either
	# coordinate set directly mis-places the paint (the cpu.svg grey-out bug).
	if local_name(elem.tag) in _USERSPACE_PAINT_TAGS:
		if _is_userspace_paint_element(elem):
			_shift_userspace_paint(elem, dx, dy)
		return
	if tag == "path" and elem.get("d"):
		segments = parse_path_to_absolute(elem.get("d"))
		elem.set("d", path_segments_to_d(segments, dx, dy))
		return
	if tag in {"polyline", "polygon"} and elem.get("points"):
		elem.set("points", format_points(parse_points(elem.get("points")), dx, dy))
		return
	for attr in COORD_ATTRS_X:
		val = elem.get(attr)
		if val is not None:
			# Use fmt_precise for emitted geometry coordinates (A4 precision).
			elem.set(attr, fmt_precise(parse_float(val) + dx))
	for attr in COORD_ATTRS_Y:
		val = elem.get(attr)
		if val is not None:
			elem.set(attr, fmt_precise(parse_float(val) + dy))


#============================================
def _ascii_id(value: str, seen_ids: dict[str, str]) -> str:
	"""Return an ASCII replacement for a non-ASCII id or data-name attribute value.

	Checks seen_ids to avoid collisions within a single file. The mapping is
	recorded in seen_ids so in-file references can be updated consistently.

	Args:
		value: The original attribute value (may contain non-ASCII).
		seen_ids: Mutable dict mapping original value -> replacement (in-file state).

	Returns:
		An ASCII replacement string.
	"""
	if value in seen_ids:
		return seen_ids[value]
	# Strip or transliterate each character to its ASCII equivalent.
	# For layer-style ids with CJK characters we drop non-ASCII bytes;
	# for unknown scripts we fall back to removing non-ASCII entirely
	# and then deduplicate against already-seen names.
	ascii_chars: list[str] = []
	for ch in value:
		if ord(ch) < 128:
			# Already ASCII -- keep as-is.
			ascii_chars.append(ch)
		else:
			# Try NFKD decomposition first (e.g. accented Latin).
			decomposed = unicodedata.normalize("NFKD", ch)
			ascii_part = decomposed.encode("ascii", "ignore").decode("ascii")
			if ascii_part:
				ascii_chars.append(ascii_part)
			else:
				# Non-decomposable (e.g. CJK). Drop the character.
				pass
	candidate = "".join(ascii_chars).strip("_").strip()
	# If the entire value was non-ASCII and everything was dropped, use a
	# generic fallback name.
	if not candidate:
		candidate = "layer"
	# Deduplicate: if candidate already taken by a *different* original, append counter.
	reverse = {v: k for k, v in seen_ids.items()}
	base = candidate
	counter = 2
	while candidate in reverse and reverse[candidate] != value:
		candidate = f"{base}_{counter}"
		counter += 1
	seen_ids[value] = candidate
	return candidate


#============================================
def make_ascii_clean(root: lxml.etree._Element) -> None:
	"""Replace non-ASCII id and data-name attribute VALUES with ASCII equivalents.

	Also updates any in-file references (href="#...", xlink:href="#...",
	url(#...) in fill/stroke/clip-path/mask attributes) to match renamed ids.
	Other non-ASCII text content (comments, text nodes) is not touched here.

	The function modifies *root* in place.

	Args:
		root: The parsed SVG root element.
	"""
	# First pass: collect all non-ASCII ids and build the rename map.
	# seen_ids maps original_value -> ascii_replacement (shared state for uniqueness).
	seen_ids: dict[str, str] = {}
	id_renames: dict[str, str] = {}
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		for attr in ("id", "data-name"):
			val = elem.get(attr)
			if val is None:
				continue
			if any(ord(ch) >= 128 for ch in val):
				new_val = _ascii_id(val, seen_ids)
				id_renames[val] = new_val
				elem.set(attr, new_val)
	if not id_renames:
		# Nothing to fix; return early.
		return
	# Second pass: update references to renamed ids.
	# References appear in href="#id", xlink:href="#id",
	# and as url(#id) inside fill, stroke, clip-path, mask, filter attributes.
	ref_attrs = {"fill", "stroke", "clip-path", "mask", "filter", "marker-start",
		"marker-mid", "marker-end", "color-profile", "cursor", "href"}
	xlink_href = "{http://www.w3.org/1999/xlink}href"
	# Use the shared quote-tolerant url() regex so quoted attribute references
	# (url('#id'), url("#id")) are rewritten too, matching the F8 <style> rewrite
	# and the S1 reference scan (fix (a): unify on _URL_REF_RE).
	url_pat = _URL_REF_RE

	# Defined once per call (not per-iteration) so there is no repeated closure
	# redefinition inside the loops below (fix (d): hoist replace_url_ref).
	def replace_url_ref(m: re.Match) -> str:
		frag = m.group(1)
		return "url(#" + id_renames.get(frag, frag) + ")"

	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		# Handle xlink:href and href as direct fragment references.
		for attr_name in (xlink_href, "href"):
			val = elem.get(attr_name)
			if val and val.startswith("#"):
				frag = val[1:]
				if frag in id_renames:
					elem.set(attr_name, "#" + id_renames[frag])
		# Handle url(#id) in presentation attributes.
		for attr_name in ref_attrs:
			val = elem.get(attr_name)
			if not val:
				continue
			new_val = url_pat.sub(replace_url_ref, val)
			if new_val != val:
				elem.set(attr_name, new_val)

	# F8: rewrite url(#oldid) references inside <style> block text so CSS refs
	# to a renamed id stay valid. Uses the shared url() regex (tolerant of quotes)
	# rather than the attribute-only url_pat above.
	for style_elem in _iter_style_blocks(root):
		css_text = style_elem.text
		if not css_text:
			continue
		new_css = _rewrite_style_url_refs(css_text, id_renames)
		if new_css != css_text:
			style_elem.text = new_css


# Matches a url(#id) reference, capturing the fragment id. Tolerates optional
# quotes around the fragment: url(#a), url('#a'), url("#a"). Used by F8 (style
# rewrite) and S1 (reference integrity).
_URL_REF_RE = re.compile(r"""url\(\s*['"]?\s*#([^)'"\s]+)\s*['"]?\s*\)""")

# Presentation attributes that may carry a url(#id) paint/clip/effect reference.
# Used by the reference-integrity gate to collect every internal reference.
_URL_REF_ATTRS = frozenset({
	"fill", "stroke", "clip-path", "mask", "filter", "marker-start",
	"marker-mid", "marker-end", "marker", "color-profile", "cursor",
})

# Attributes that may carry a direct fragment (href="#id") reference.
_HREF_ATTRS = ("{http://www.w3.org/1999/xlink}href", "href")


#============================================
def _iter_style_blocks(root: lxml.etree._Element) -> "list[lxml.etree._Element]":
	"""Return every <style> element in the document tree, in document order.

	Args:
		root: The parsed SVG root element.

	Returns:
		List of <style> elements (may be empty).
	"""
	blocks: list[lxml.etree._Element] = []
	for elem in root.iter():
		if isinstance(elem.tag, str) and local_name(elem.tag) == "style":
			blocks.append(elem)
	return blocks


#============================================
def _rewrite_style_url_refs(css_text: str, id_renames: dict[str, str]) -> str:
	"""Rewrite url(#oldid) references inside CSS text using an id-rename map (F8).

	Used after make_ascii_clean renames a non-ASCII id so that references to it
	inside a <style> block stay valid. The rewrite is a targeted substitution on
	the url(#...) token only; the rest of the CSS text is untouched.

	Args:
		css_text: The raw CSS text from a <style> block.
		id_renames: Mapping of original id -> ASCII replacement.

	Returns:
		The CSS text with renamed url(#id) references updated.
	"""
	def replace(match: re.Match) -> str:
		frag = match.group(1)
		new_frag = id_renames.get(frag, frag)
		return "url(#" + new_frag + ")"
	return _URL_REF_RE.sub(replace, css_text)


#============================================
def _detect_script_or_handler(root: lxml.etree._Element) -> RejectionReason | None:
	"""Detect <script> elements or on* event-handler attributes anywhere in the SVG.

	Security + non-determinism: scripts and event handlers are never supported by
	the normalizer gate. Any file containing them is rejected with SCRIPT_OR_HANDLER.

	Reject script elements and inline event handlers.

	Args:
		root: The parsed SVG root element.

	Returns:
		RejectionReason with code SCRIPT_OR_HANDLER when found, else None.
	"""
	# _ON_HANDLER_RE is a module-level constant reused across elements.
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		tag = local_name(elem.tag)
		if tag == "script":
			element_location = elem.getroottree().getpath(elem)
			reason = RejectionReason(
				code="SCRIPT_OR_HANDLER",
				message="Script elements are not supported and rejected for security.",
				fix="Remove all <script> elements and on* event handler attributes before ingestion.",
				element=element_location,
			)
			return reason
		# Check for on* event handler attributes on any element.
		for attr_name in elem.attrib:
			local_attr = local_name(attr_name) if isinstance(attr_name, str) else attr_name
			if isinstance(local_attr, str) and _ON_HANDLER_RE.match(local_attr):
				element_location = elem.getroottree().getpath(elem)
				reason = RejectionReason(
					code="SCRIPT_OR_HANDLER",
					message=f"Event handler attribute '{local_attr}' is not supported.",
					fix="Remove all <script> elements and on* event handler attributes before ingestion.",
					element=element_location,
				)
				return reason
	return None


#============================================
def _detect_animation_elements(root: lxml.etree._Element) -> RejectionReason | None:
	"""Detect SVG animation elements: <animate>, <animateTransform>, <animateMotion>, <set>.

	Animation introduces non-determinism and is never supported. Any file containing
	animation elements is rejected with ANIMATION_UNSUPPORTED.

	Reject animation elements.

	Args:
		root: The parsed SVG root element.

	Returns:
		RejectionReason with code ANIMATION_UNSUPPORTED when found, else None.
	"""
	_ANIMATION_TAGS = {"animate", "animateTransform", "animateMotion", "set"}
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		tag = local_name(elem.tag)
		if tag in _ANIMATION_TAGS:
			element_location = elem.getroottree().getpath(elem)
			reason = RejectionReason(
				code="ANIMATION_UNSUPPORTED",
				message=f"Animation element <{tag}> is not supported by the v3 normalizer.",
				fix="Remove all animation elements before ingestion.",
				element=element_location,
			)
			return reason
	return None


#============================================
def _detect_foreignobject(root: lxml.etree._Element) -> RejectionReason | None:
	"""Detect <foreignObject> elements anywhere in the SVG.

	foreignObject embeds HTML and renders inconsistently across renderers. Any file
	containing it is rejected with FOREIGNOBJECT_UNSUPPORTED.

	Reject foreignObject elements.

	Args:
		root: The parsed SVG root element.

	Returns:
		RejectionReason with code FOREIGNOBJECT_UNSUPPORTED when found, else None.
	"""
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		tag = local_name(elem.tag)
		if tag == "foreignObject":
			element_location = elem.getroottree().getpath(elem)
			reason = RejectionReason(
				code="FOREIGNOBJECT_UNSUPPORTED",
				message="<foreignObject> embeds HTML and renders inconsistently.",
				fix="Remove all <foreignObject> elements before ingestion.",
				element=element_location,
			)
			return reason
	return None


#============================================
def detect_doctype_or_entity(source_text: str) -> RejectionReason | None:
	"""Detect DOCTYPE declarations or ENTITY definitions in raw SVG text.

	parse_svg uses resolve_entities=False so a DOCTYPE may parse without error, but
	DOCTYPE and ENTITY declarations introduce parser/security complexity that v3 does
	not handle. This check is done on raw text BEFORE (or after) parsing to catch
	files that slipped through the lxml recovery guard.

	The check is cheap: scan the first 4096 bytes for "<!DOCTYPE" or "<!ENTITY".
	Case-insensitive to catch unusual capitalizations.

	Reject unsafe document declarations before XML parsing.

	Args:
		source_text: Raw text content of the SVG file.

	Returns:
		RejectionReason with code DOCTYPE_OR_ENTITY when found, else None.
	"""
	# Only scan the document preamble (first 4096 chars) for efficiency; DOCTYPE /
	# ENTITY declarations must appear before the root element.
	head = source_text[:4096].upper()
	if "<!DOCTYPE" in head or "<!ENTITY" in head:
		reason = RejectionReason(
			code="DOCTYPE_OR_ENTITY",
			message="DOCTYPE or ENTITY declarations are not supported.",
			fix="Remove the DOCTYPE declaration and all ENTITY definitions before ingestion.",
			element="",
		)
		return reason
	return None


#============================================
# Feature reject detectors and reference-integrity helpers.
#
# Each detector takes root and returns a
# RejectionReason or None, matching the classify() composition contract. They
# are composed into classify() in priority order (see classify()).
#============================================


#============================================
def _detect_use_or_symbol(root: lxml.etree._Element) -> RejectionReason | None:
	"""Reject any file containing a <use> or <symbol> element.

	Symbol expansion is not implemented in v3; refusing the whole file is simpler
	and safe for the gate (per the support contract). A later WP may add symbol
	expansion and carve this back.

	Args:
		root: The parsed SVG root element.

	Returns:
		RejectionReason with code USE_OR_SYMBOL_UNSUPPORTED when found, else None.
	"""
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		tag = local_name(elem.tag)
		if tag in {"use", "symbol"}:
			location = elem.getroottree().getpath(elem)
			reason = RejectionReason(
				code="USE_OR_SYMBOL_UNSUPPORTED",
				message=f"<{tag}> is not supported (symbol expansion is not implemented in v3).",
				fix="Expand <use>/<symbol> into concrete geometry in your editor before ingestion.",
				element=location,
			)
			return reason
	return None


#============================================
def _detect_filter(root: lxml.etree._Element) -> RejectionReason | None:
	"""Reject any file using a filter (a <filter> element or a filter= reference).

	Filters (including feGaussianBlur) can extend or alter visible pixels beyond
	the geometry bbox, which would violate contract item 3 (bbox must bound the
	visible art). Any <filter> definition, any filter primitive, or any element
	carrying a non-none filter= reference is rejected.

	Args:
		root: The parsed SVG root element.

	Returns:
		RejectionReason with code FILTER_UNSUPPORTED when found, else None.
	"""
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		tag = local_name(elem.tag)
		# A <filter> definition or any fe* filter primitive (feGaussianBlur, etc.).
		if tag == "filter" or tag.startswith("fe"):
			location = elem.getroottree().getpath(elem)
			reason = RejectionReason(
				code="FILTER_UNSUPPORTED",
				message=f"<{tag}> filters can alter visible pixels beyond the geometry bbox.",
				fix="Remove filters (rasterize or bake the effect) before ingestion.",
				element=location,
			)
			return reason
		# A filter= reference (presentation attribute or inline style) on any element.
		filter_ref = _resolved_property(elem, "filter")
		if filter_ref is not None and filter_ref.strip().lower() not in {"", "none"}:
			location = elem.getroottree().getpath(elem)
			reason = RejectionReason(
				code="FILTER_UNSUPPORTED",
				message="A filter reference can alter visible pixels beyond the geometry bbox.",
				fix="Remove the filter reference (rasterize or bake the effect) before ingestion.",
				element=location,
			)
			return reason
	return None


#============================================
def _detect_mask(root: lxml.etree._Element) -> RejectionReason | None:
	"""Reject any file using a mask (a <mask> element or a mask= reference).

	Masks change which pixels are visible in ways not computable from geometry
	alone, so the bbox guarantee cannot hold. Any <mask> definition or any
	element carrying a non-none mask= reference is rejected.

	Args:
		root: The parsed SVG root element.

	Returns:
		RejectionReason with code MASK_UNSUPPORTED when found, else None.
	"""
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		tag = local_name(elem.tag)
		if tag == "mask":
			location = elem.getroottree().getpath(elem)
			reason = RejectionReason(
				code="MASK_UNSUPPORTED",
				message="<mask> changes visible pixels in ways not computable from geometry.",
				fix="Bake or remove the mask before ingestion.",
				element=location,
			)
			return reason
		mask_ref = _resolved_property(elem, "mask")
		if mask_ref is not None and mask_ref.strip().lower() not in {"", "none"}:
			location = elem.getroottree().getpath(elem)
			reason = RejectionReason(
				code="MASK_UNSUPPORTED",
				message="A mask reference changes visible pixels in ways not computable from geometry.",
				fix="Bake or remove the mask before ingestion.",
				element=location,
			)
			return reason
	return None


#============================================
def _detect_marker(root: lxml.etree._Element) -> RejectionReason | None:
	"""Reject any file using a marker (a <marker> element or marker-* reference).

	Markers draw extra geometry at path vertices that is not part of the path's
	own bbox, so the geometry bbox would undershoot. Any <marker> definition or
	any element carrying a non-none marker / marker-start / marker-mid /
	marker-end reference is rejected.

	Args:
		root: The parsed SVG root element.

	Returns:
		RejectionReason with code MARKER_UNSUPPORTED when found, else None.
	"""
	marker_props = ("marker", "marker-start", "marker-mid", "marker-end")
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		tag = local_name(elem.tag)
		if tag == "marker":
			location = elem.getroottree().getpath(elem)
			reason = RejectionReason(
				code="MARKER_UNSUPPORTED",
				message="<marker> draws extra geometry the bbox cannot account for.",
				fix="Remove markers (convert them to explicit path geometry) before ingestion.",
				element=location,
			)
			return reason
		for prop in marker_props:
			ref = _resolved_property(elem, prop)
			if ref is not None and ref.strip().lower() not in {"", "none"}:
				location = elem.getroottree().getpath(elem)
				reason = RejectionReason(
					code="MARKER_UNSUPPORTED",
					message=f"A {prop} reference draws extra geometry the bbox cannot account for.",
					fix="Remove markers (convert them to explicit path geometry) before ingestion.",
					element=location,
				)
				return reason
	return None


# A data: URI (embedded resource, e.g. base64 raster). Matches the scheme prefix.
_DATA_URI_RE = re.compile(r"^\s*data:", re.IGNORECASE)
# An external resource scheme (http, https, file, ftp) or a protocol-relative URL.
_EXTERNAL_SCHEME_RE = re.compile(r"^\s*(?:[a-zA-Z][a-zA-Z0-9+.-]*:|//)")


#============================================
def _href_value(elem: lxml.etree._Element) -> str | None:
	"""Return the href / xlink:href value of an element, or None when absent."""
	for attr in _HREF_ATTRS:
		val = elem.get(attr)
		if val is not None:
			return val
	return None


#============================================
def _detect_image(root: lxml.etree._Element) -> RejectionReason | None:
	"""Reject <image> elements: embedded raster (data:) or external href.

	An <image> with a data: URI embeds a raster (EMBEDDED_RASTER_UNSUPPORTED);
	an <image> with any other href references an external resource
	(EXTERNAL_RESOURCE_UNSUPPORTED). A bare in-document fragment (#id) on an image
	is still rejected as external, since v3 does not resolve image content.

	Args:
		root: The parsed SVG root element.

	Returns:
		RejectionReason with the appropriate code when an <image> is found, else None.
	"""
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		if local_name(elem.tag) != "image":
			continue
		location = elem.getroottree().getpath(elem)
		href = _href_value(elem)
		if href is not None and _DATA_URI_RE.match(href):
			reason = RejectionReason(
				code="EMBEDDED_RASTER_UNSUPPORTED",
				message="<image> embeds a raster (data: URI); v3 normalizes vector geometry only.",
				fix="Recreate the artwork as vector paths before ingestion.",
				element=location,
			)
			return reason
		# Any other <image> (external href, relative path, or no href) is external.
		reason = RejectionReason(
			code="EXTERNAL_RESOURCE_UNSUPPORTED",
			message="<image> references an external resource; v3 normalizes self-contained vector SVGs only.",
			fix="Inline the artwork as vector paths before ingestion.",
			element=location,
		)
		return reason
	return None


#============================================
def _detect_external_href(root: lxml.etree._Element) -> RejectionReason | None:
	"""Reject any href / xlink:href that points outside the document.

	An internal fragment reference (href="#id") is allowed (resolved by S1).
	A data: URI or any scheme/relative/protocol-relative href is an external
	resource and rejected with EXTERNAL_RESOURCE_UNSUPPORTED. <image> is handled
	earlier by _detect_image; this catches external hrefs on any other element
	(e.g. a <use>-like ref that slipped past, or a feImage, or a pattern child).

	Args:
		root: The parsed SVG root element.

	Returns:
		RejectionReason with code EXTERNAL_RESOURCE_UNSUPPORTED when found, else None.
	"""
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		href = _href_value(elem)
		if href is None:
			continue
		stripped = href.strip()
		if stripped == "" or stripped.startswith("#"):
			# Internal fragment ref (or empty): handled by S1, not external.
			continue
		location = elem.getroottree().getpath(elem)
		reason = RejectionReason(
			code="EXTERNAL_RESOURCE_UNSUPPORTED",
			message=f"href {href!r} references a resource outside this document.",
			fix="Inline the referenced content (or remove the reference) before ingestion.",
			element=location,
		)
		return reason
	return None


#============================================
# Simple clipPath flattening.
#
# Flattens a SIMPLE clipPath into the clipped target's path geometry using
# shapely, then drops the clip reference and the now-unused clipPath def. Curves
# (cubic/quadratic bezier and elliptical arcs) are flattened to polylines within
# a fixed tolerance before intersection. Anything outside the simple-clip
# allowlist is refused with ComplexClipError -> CLIPPATH_UNSUPPORTED_COMPLEX.
#
# Clip-side allowlist (all must hold, else ComplexClipError):
#   - the clipPath holds exactly one child path/shape (one geometry node);
#   - no nested clipPaths;
#   - no mask/filter/text/image/use inside the clipPath;
#   - clipPathUnits is userSpaceOnUse (objectBoundingBox is rejected);
#   - the clip geometry converts to a path in root coordinates.
#
# Target-side handling (after the clip side passes):
#   - no-op clip (the clip region already contains the painted target envelope,
#     the common editor page-bounds case): drop the clip ref, keep the target d
#     UNCHANGED. Runs for both filled and stroke-only (fill:none) targets and is
#     render-identical by construction with no precision loss.
#   - filled target, genuinely clipped: emit target INTERSECT clip as the new d
#     (must be expressible as absolute path data).
#   - stroke-only target, genuinely clipped: rejected (a real stroke trim needs
#     stroke-to-path expansion, which is out of scope).
#
# Curve-flattening tolerance: _CLIP_FLATTEN_TOLERANCE user units (~0.1). This is
# the maximum chord deviation used when subdividing a bezier/arc into line
# segments before building shapely polygons. Documented like the A4 precision
# constant; not CLI-tunable.
#============================================

# Maximum chord deviation (user units) when flattening curves to polylines for
# the shapely intersection. Smaller -> more segments -> tighter clip boundary.
# 0.1 user units is well below the A4 coordinate precision and is invisible at
# asset scale.
_CLIP_FLATTEN_TOLERANCE = 0.1

# Margin (user units) by which a clip polygon is SHRUNK before the no-op
# containment test. A clip is a no-op only when the SHRUNK clip still fully
# contains the target envelope, meaning the target clears the real clip edge
# by at least this margin. Shrinking makes the test CONSERVATIVE (harder to
# pass): a target that protrudes even slightly outside the clip fails the test
# and the clip is kept. The margin equals a small multiple of the
# curve-flattening tolerance so polyline-approximation slop on the clip
# boundary never causes a genuine trim to be misread as a no-op.
_CLIP_NOOP_MARGIN = 2.0 * _CLIP_FLATTEN_TOLERANCE

# Minimum half-width (user units) for a stroke envelope buffer. A stroke-only
# target with a zero or hairline stroke-width still has a nonzero rendered
# footprint; this floor keeps its envelope from collapsing to a zero-area line
# (which shapely.contains would treat inconsistently). Kept at the flattening
# tolerance so it is invisible at asset scale.
_STROKE_ENVELOPE_MIN_HALF = _CLIP_FLATTEN_TOLERANCE

# Geometry tags allowed as the single child of a simple clipPath (after the
# shape->path pass, a clip child may still be a basic shape because defs content
# is not converted by convert_shapes_to_paths).
_CLIP_GEOMETRY_TAGS = frozenset({
	"path", "rect", "circle", "ellipse", "polygon", "polyline", "line",
})

# Tags that, if present inside a clipPath, make the clip complex (not flattened).
_CLIP_FORBIDDEN_CHILD_TAGS = frozenset({
	"mask", "filter", "text", "tspan", "textPath", "image", "use", "clipPath",
})


#============================================
def _cubic_points(
	p0: tuple[float, float], p1: tuple[float, float],
	p2: tuple[float, float], p3: tuple[float, float], tol: float,
) -> list[tuple[float, float]]:
	"""Adaptively flatten a cubic bezier to a polyline within chord tolerance tol.

	Recursively subdivides until the control points lie within tol of the chord.
	Returns the interior and end points (the start point p0 is added by caller).

	Args:
		p0, p1, p2, p3: Cubic bezier control points (absolute).
		tol: Maximum allowed chord deviation in user units.

	Returns:
		List of points approximating the curve, excluding p0, including p3.
	"""
	# Flatness test: distance of control points p1, p2 from the chord p0-p3.
	dx = p3[0] - p0[0]
	dy = p3[1] - p0[1]
	# Use the unnormalized cross-product distance; guard the degenerate chord.
	chord_len = math.hypot(dx, dy)
	if chord_len < 1e-12:
		d1 = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
		d2 = math.hypot(p2[0] - p0[0], p2[1] - p0[1])
		flat = max(d1, d2) <= tol
	else:
		d1 = abs((p1[0] - p0[0]) * dy - (p1[1] - p0[1]) * dx) / chord_len
		d2 = abs((p2[0] - p0[0]) * dy - (p2[1] - p0[1]) * dx) / chord_len
		flat = max(d1, d2) <= tol
	if flat:
		return [p3]
	# Subdivide at t=0.5 using de Casteljau.
	p01 = ((p0[0] + p1[0]) / 2.0, (p0[1] + p1[1]) / 2.0)
	p12 = ((p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0)
	p23 = ((p2[0] + p3[0]) / 2.0, (p2[1] + p3[1]) / 2.0)
	p012 = ((p01[0] + p12[0]) / 2.0, (p01[1] + p12[1]) / 2.0)
	p123 = ((p12[0] + p23[0]) / 2.0, (p12[1] + p23[1]) / 2.0)
	mid = ((p012[0] + p123[0]) / 2.0, (p012[1] + p123[1]) / 2.0)
	left = _cubic_points(p0, p01, p012, mid, tol)
	right = _cubic_points(mid, p123, p23, p3, tol)
	return left + right


#============================================
def _quadratic_points(
	p0: tuple[float, float], p1: tuple[float, float], p2: tuple[float, float], tol: float,
) -> list[tuple[float, float]]:
	"""Flatten a quadratic bezier by elevating it to a cubic, then flattening that.

	A quadratic with control point p1 is the cubic with control points
	c1 = p0 + 2/3 (p1 - p0) and c2 = p2 + 2/3 (p1 - p2).

	Args:
		p0, p1, p2: Quadratic bezier control points (absolute).
		tol: Maximum allowed chord deviation in user units.

	Returns:
		List of points approximating the curve, excluding p0, including p2.
	"""
	c1 = (p0[0] + 2.0 / 3.0 * (p1[0] - p0[0]), p0[1] + 2.0 / 3.0 * (p1[1] - p0[1]))
	c2 = (p2[0] + 2.0 / 3.0 * (p1[0] - p2[0]), p2[1] + 2.0 / 3.0 * (p1[1] - p2[1]))
	return _cubic_points(p0, c1, c2, p2, tol)


#============================================
def _arc_points(
	x0: float, y0: float, arc: tuple[float, ...], tol: float,
) -> list[tuple[float, float]]:
	"""Flatten an elliptical arc to a polyline within chord tolerance tol.

	Uses the center parameterization (_arc_center_params) and samples the arc at
	a step fine enough that the chord deviation stays under tol. A degenerate arc
	(zero radius / coincident endpoints) reduces to a single line to the endpoint.

	Args:
		x0, y0: Arc start point (absolute).
		arc: The seven absolute arc params (rx, ry, rot_deg, large, sweep, x, y).
		tol: Maximum allowed chord deviation in user units.

	Returns:
		List of points approximating the arc, excluding (x0,y0), including the end.
	"""
	rx, ry, rot_deg, large, sweep, x1, y1 = arc
	params = _arc_center_params(x0, y0, rx, ry, rot_deg, large, sweep, x1, y1)
	if params is None:
		# Degenerate arc: straight line to the endpoint.
		return [(x1, y1)]
	cx, cy, theta1, delta = params
	rx = abs(rx)
	ry = abs(ry)
	phi = math.radians(rot_deg % 360.0)
	cos_phi = math.cos(phi)
	sin_phi = math.sin(phi)
	# Re-apply the radius correction so sampling matches the solved center.
	dx2 = (x0 - x1) / 2.0
	dy2 = (y0 - y1) / 2.0
	x1p = cos_phi * dx2 + sin_phi * dy2
	y1p = -sin_phi * dx2 + cos_phi * dy2
	radii_check = (x1p * x1p) / (rx * rx) + (y1p * y1p) / (ry * ry)
	if radii_check > 1.0:
		scale = math.sqrt(radii_check)
		rx *= scale
		ry *= scale
	# Choose a step count so the chord deviation of a circle of radius max(rx,ry)
	# stays under tol: deviation ~= r (1 - cos(step/2)). Solve for step.
	r_max = max(rx, ry)
	if r_max <= tol:
		# The whole arc is smaller than the tolerance: one segment suffices.
		return [(x1, y1)]
	# 1 - cos(a) <= tol/r  ->  a <= 2 * acos(1 - tol/r_max).
	ratio = 1.0 - tol / r_max
	ratio = max(-1.0, min(1.0, ratio))
	max_step = 2.0 * math.acos(ratio)
	if max_step <= 1e-9:
		max_step = abs(delta)
	steps = max(1, int(math.ceil(abs(delta) / max_step)))
	points: list[tuple[float, float]] = []
	for i in range(1, steps + 1):
		t = theta1 + delta * (i / steps)
		px, py = _arc_point(cx, cy, rx, ry, cos_phi, sin_phi, t)
		points.append((px, py))
	return points


#============================================
def segments_to_rings(
	segments: list[PathSegment], tol: float,
) -> list[list[tuple[float, float]]]:
	"""Flatten absolute path segments into a list of closed point rings.

	Each subpath (M..Z or M.. up to the next M) becomes one ring. Curves are
	flattened to polylines within tol. Open subpaths are implicitly closed (clip
	regions are filled areas, so each subpath bounds a region). Rings with fewer
	than 3 distinct points are dropped (no area).

	Args:
		segments: Absolute PathSegment list (M/L/C/Q/A/Z only).
		tol: Curve-flattening chord tolerance in user units.

	Returns:
		List of rings; each ring is a list of (x, y) points.
	"""
	rings: list[list[tuple[float, float]]] = []
	current: list[tuple[float, float]] = []
	cur_x = 0.0
	cur_y = 0.0
	start_x = 0.0
	start_y = 0.0
	for seg in segments:
		cmd = seg.cmd
		nums = seg.nums
		if cmd == "M":
			# Starting a new subpath: flush the previous ring.
			if len(current) >= 3:
				rings.append(current)
			current = [(nums[0], nums[1])]
			cur_x, cur_y = nums[0], nums[1]
			start_x, start_y = nums[0], nums[1]
		elif cmd == "L":
			current.append((nums[0], nums[1]))
			cur_x, cur_y = nums[0], nums[1]
		elif cmd == "C":
			pts = _cubic_points(
				(cur_x, cur_y), (nums[0], nums[1]),
				(nums[2], nums[3]), (nums[4], nums[5]), tol,
			)
			current.extend(pts)
			cur_x, cur_y = nums[4], nums[5]
		elif cmd == "Q":
			pts = _quadratic_points(
				(cur_x, cur_y), (nums[0], nums[1]), (nums[2], nums[3]), tol,
			)
			current.extend(pts)
			cur_x, cur_y = nums[2], nums[3]
		elif cmd == "A":
			pts = _arc_points(cur_x, cur_y, nums, tol)
			current.extend(pts)
			cur_x, cur_y = nums[5], nums[6]
		elif cmd == "Z":
			# Close back to the subpath start; flush.
			if current and (cur_x, cur_y) != (start_x, start_y):
				current.append((start_x, start_y))
			if len(current) >= 3:
				rings.append(current)
			current = []
			cur_x, cur_y = start_x, start_y
	# Flush a trailing open subpath (implicitly closed).
	if len(current) >= 3:
		rings.append(current)
	return rings


#============================================
def _polygon_from_segments(
	segments: list[PathSegment], fill_rule: str, tol: float,
) -> "shapely.geometry.base.BaseGeometry":
	"""Build a (possibly multi) shapely polygon from absolute path segments.

	Each subpath ring becomes a shapely polygon; the rings are combined with the
	requested fill rule. nonzero (the SVG default) and evenodd both map cleanly
	to shapely's set operations after make_valid normalizes self-intersections:
	  - evenodd: symmetric_difference of all rings (overlaps cancel).
	  - nonzero: union of all rings (overlaps accumulate as filled).
	make_valid handles self-touching / bowtie rings so the result is a valid
	(Multi)Polygon. An empty ring set yields an empty geometry.

	Args:
		segments: Absolute PathSegment list.
		fill_rule: "evenodd" or "nonzero".
		tol: Curve-flattening chord tolerance in user units.

	Returns:
		A shapely Polygon / MultiPolygon (possibly empty).
	"""
	rings = segments_to_rings(segments, tol)
	if not rings:
		return shapely.geometry.Polygon()
	polys = [shapely.make_valid(shapely.geometry.Polygon(ring)) for ring in rings]
	combined = polys[0]
	for poly in polys[1:]:
		if fill_rule == "evenodd":
			combined = combined.symmetric_difference(poly)
		else:
			combined = combined.union(poly)
	# Normalize the result so downstream emission sees clean (Multi)Polygon parts.
	return shapely.make_valid(combined)


#============================================
def _resolve_fill_rule(elem: lxml.etree._Element, prop: str) -> str:
	"""Return 'evenodd' or 'nonzero' (default) for a fill-rule / clip-rule property.

	Reads inline style then presentation attribute (inline-only cascade).

	Args:
		elem: The element.
		prop: "fill-rule" (target) or "clip-rule" (clip child).

	Returns:
		"evenodd" when the property is set to evenodd, else "nonzero".
	"""
	val = _resolved_property(elem, prop)
	if val is not None and val.strip().lower() == "evenodd":
		return "evenodd"
	return "nonzero"


#============================================
def _geometry_to_path_d(geometry: "shapely.geometry.base.BaseGeometry") -> str:
	"""Serialize a shapely Polygon / MultiPolygon to absolute SVG path data.

	Each polygon emits its exterior ring as a clockwise-wound subpath and each
	interior hole as a reverse-wound subpath, so the SVG nonzero winding rule
	renders the holes as cut-outs. Coordinates use fmt_precise (A4 precision).
	An empty geometry returns "".

	Args:
		geometry: A shapely Polygon or MultiPolygon (already make_valid).

	Returns:
		Absolute SVG path data string (M/L/Z subpaths), or "" when empty.
	"""
	if geometry.is_empty:
		return ""
	# Normalize to a flat list of Polygon parts.
	if geometry.geom_type == "Polygon":
		polygons = [geometry]
	elif geometry.geom_type == "MultiPolygon":
		polygons = list(geometry.geoms)
	elif geometry.geom_type == "GeometryCollection":
		# Keep only polygonal parts (lines/points from degenerate clips are dropped).
		polygons = [g for g in geometry.geoms if g.geom_type == "Polygon"]
	else:
		# Lower-dimensional result (LineString/Point): no fillable area.
		return ""
	parts: list[str] = []
	for poly in polygons:
		if poly.is_empty:
			continue
		# Exterior ring clockwise; holes counter-clockwise (opposite winding) so
		# the SVG nonzero rule subtracts them.
		exterior = _ring_coords(poly.exterior, clockwise=True)
		if exterior:
			parts.append(_ring_to_subpath(exterior))
		for interior in poly.interiors:
			hole = _ring_coords(interior, clockwise=False)
			if hole:
				parts.append(_ring_to_subpath(hole))
	return " ".join(parts)


#============================================
def _ring_coords(ring: "shapely.geometry.base.BaseGeometry", clockwise: bool) -> list[tuple[float, float]]:
	"""Return a ring's coordinates wound in the requested direction (no closing dup).

	Shapely rings repeat the first point as the last; that duplicate is dropped
	(the Z command closes the subpath). The winding is enforced via is_ccw.

	Args:
		ring: A shapely LinearRing.
		clockwise: True to return clockwise points, False for counter-clockwise.

	Returns:
		List of (x, y) points without the closing duplicate.
	"""
	coords = list(ring.coords)
	if len(coords) > 1 and coords[0] == coords[-1]:
		coords = coords[:-1]
	# ring.is_ccw is True when the stored ring is counter-clockwise.
	is_ccw = ring.is_ccw
	want_ccw = not clockwise
	if is_ccw != want_ccw:
		coords = list(reversed(coords))
	return [(float(x), float(y)) for x, y in coords]


#============================================
def _ring_to_subpath(points: list[tuple[float, float]]) -> str:
	"""Emit one closed subpath (M + L* + Z) from a ring's points using fmt_precise."""
	first = points[0]
	parts = [f"M {fmt_precise(first[0])} {fmt_precise(first[1])}"]
	for x, y in points[1:]:
		parts.append(f"L {fmt_precise(x)} {fmt_precise(y)}")
	parts.append("Z")
	return " ".join(parts)


#============================================
def _clip_child_geometry_node(clip_elem: lxml.etree._Element, location: str) -> lxml.etree._Element:
	"""Return the single geometry child of a clipPath, enforcing the allowlist.

	Raises ComplexClipError when the clipPath does not hold exactly one geometry
	child, contains a forbidden child (mask/filter/text/image/use/nested clip),
	or uses clipPathUnits=objectBoundingBox.

	Args:
		clip_elem: The <clipPath> element.
		location: XPath-like location of the clipped target (for the error).

	Returns:
		The single geometry child element.

	Raises:
		ComplexClipError: When the clipPath is outside the simple allowlist.
	"""
	clip_location = clip_elem.getroottree().getpath(clip_elem)
	# clipPathUnits default is userSpaceOnUse; objectBoundingBox is rejected.
	units = clip_elem.get("clipPathUnits")
	if units is not None and units.strip() != "userSpaceOnUse":
		raise ComplexClipError(clip_location, f"clipPathUnits={units!r} is not supported")
	geometry_children: list[lxml.etree._Element] = []
	for child in clip_elem:
		if not isinstance(child.tag, str):
			continue
		child_tag = local_name(child.tag)
		if child_tag in _CLIP_FORBIDDEN_CHILD_TAGS:
			raise ComplexClipError(
				clip_location, f"clipPath contains forbidden <{child_tag}>"
			)
		if child_tag in _CLIP_GEOMETRY_TAGS:
			geometry_children.append(child)
		# Any other element type (e.g. a group) makes the clip non-simple.
		elif child_tag not in {"title", "desc", "metadata"}:
			raise ComplexClipError(
				clip_location, f"clipPath contains unsupported <{child_tag}>"
			)
	if len(geometry_children) != 1:
		raise ComplexClipError(
			clip_location,
			f"clipPath must hold exactly one path/shape, found {len(geometry_children)}",
		)
	return geometry_children[0]


#============================================
def _target_is_stroke_only(elem: lxml.etree._Element) -> bool:
	"""Return True when the clip target is stroke-only (fill resolves to none).

	A stroke-only target carries no filled area, so clipping it is a stroke trim
	rather than a filled-area intersection. The no-op short circuit handles the
	common page-bounds case; a genuine stroke trim stays rejected.

	Args:
		elem: The clipped target element.

	Returns:
		True when fill is explicitly "none", else False.
	"""
	fill = _resolved_property(elem, "fill")
	return fill is not None and fill.strip().lower() == "none"


#============================================
def _target_segments_for_clip(elem: lxml.etree._Element, location: str) -> list[PathSegment]:
	"""Return the absolute segments of a clip TARGET path.

	After flatten_transforms + convert_shapes_to_paths a supported target is a
	<path>. This returns the target geometry without enforcing the fill rule;
	callers decide how to treat a stroke-only target (no-op drop vs reject).

	Args:
		elem: The clipped target element.
		location: XPath-like location (for the error).

	Returns:
		Absolute PathSegment list of the target geometry.

	Raises:
		ComplexClipError: When the target is not path geometry or has no path data.
	"""
	tag = local_name(elem.tag)
	if tag != "path":
		raise ComplexClipError(location, f"clip target <{tag}> is not path geometry")
	d_attr = elem.get("d")
	if not d_attr:
		raise ComplexClipError(location, "clip target has no path data")
	return parse_path_to_absolute(d_attr)


#============================================
def _resolved_stroke_width(elem: lxml.etree._Element) -> float:
	"""Return the element's stroke-width in user units (SVG default 1.0 when absent).

	After flatten_transforms a uniform scale is baked into the geometry and the
	stroke-width is rewritten to match, so the value read here is already in root
	coordinates. A trailing "px" unit is tolerated; any other unit or an
	unparseable value falls back to the SVG default rather than guessing.

	Args:
		elem: The clipped target element.

	Returns:
		The stroke-width as a float, defaulting to 1.0.
	"""
	raw = _resolved_property(elem, "stroke-width")
	if raw is None:
		return _DEFAULT_STROKE_WIDTH
	text = raw.strip().lower()
	if text.endswith("px"):
		text = text[:-2].strip()
	# A bare number (optionally with a px unit) is the only supported form; any
	# other unit or junk falls back to the default so the envelope stays sane.
	if not _TRANSFORM_NUM_RE.fullmatch(text):
		return _DEFAULT_STROKE_WIDTH
	return float(text)


#============================================
def _target_envelope_polygon(
	elem: lxml.etree._Element, target_segments: list[PathSegment],
) -> "shapely.geometry.base.BaseGeometry":
	"""Build the target's rendered envelope: filled area unioned with stroke envelope.

	The envelope is the region the target actually paints, used by the no-op
	containment test. It is the union of:
	  - the filled polygon (empty for a stroke-only fill:none target);
	  - the stroke envelope: each ring buffered by half the stroke-width (with a
	    small floor so a hairline stroke still has area).
	A pure-stroke target yields the stroke buffer alone; a filled target with no
	stroke still yields its filled polygon.

	Args:
		elem: The clipped target element (for fill-rule and stroke-width).
		target_segments: The target's absolute path segments.

	Returns:
		A shapely geometry covering the target's painted area (possibly empty).
	"""
	target_rule = _resolve_fill_rule(elem, "fill-rule")
	filled = _polygon_from_segments(target_segments, target_rule, _CLIP_FLATTEN_TOLERANCE)
	# Stroke envelope: buffer every flattened ring by half the stroke-width.
	half = max(_resolved_stroke_width(elem) / 2.0, _STROKE_ENVELOPE_MIN_HALF)
	stroke_parts: list["shapely.geometry.base.BaseGeometry"] = []
	for ring in segments_to_rings(target_segments, _CLIP_FLATTEN_TOLERANCE):
		if len(ring) >= 2:
			stroke_parts.append(shapely.geometry.LineString(ring).buffer(half))
	if stroke_parts:
		stroke_env = shapely.union_all(stroke_parts)
	else:
		stroke_env = shapely.geometry.Polygon()
	# Union the filled area with the stroke envelope; either part may be empty.
	if filled.is_empty:
		envelope = stroke_env
	elif stroke_env.is_empty:
		envelope = filled
	else:
		envelope = filled.union(stroke_env)
	return shapely.make_valid(envelope)


#============================================
def flatten_clip_paths(root: lxml.etree._Element) -> None:
	"""Flatten every simple clip-path reference into the target's path geometry (A6).

	Runs AFTER flatten_transforms + convert_shapes_to_paths so both target and
	clip geometry are absolute root-coordinate paths/shapes. For each visible
	element carrying clip-path="url(#cid)":
	  - resolve <clipPath id=cid>; enforce the simple-clip allowlist;
	  - compute target-geometry INTERSECT clip-geometry via shapely (curves
	    flattened to polylines within _CLIP_FLATTEN_TOLERANCE);
	  - set the target's d to the clipped path data (empty d when the
	    intersection is empty), handling Polygon and MultiPolygon (holes emitted
	    as reverse-wound subpaths);
	  - remove the clip-path attribute.
	After all references are processed, remove every ordinary <clipPath> def that
	is no longer referenced anywhere.  The closed runtime material anchor remains
	available even though it is referenced only after DOM injection.

	Args:
		root: The parsed (transform-flattened, shape-converted) SVG root. Modified
			in place.

	Raises:
		ComplexClipError: When any clip-path usage is outside the simple allowlist.
	"""
	# Map clipPath id -> element, scanning the whole tree (clipPaths live in defs).
	clip_defs: dict[str, lxml.etree._Element] = {}
	for elem in root.iter():
		if isinstance(elem.tag, str) and local_name(elem.tag) == "clipPath":
			cid = elem.get("id")
			if cid is not None:
				clip_defs[cid] = elem

	# Collect target elements first (do not mutate the tree while iterating).
	targets: list[tuple[lxml.etree._Element, str]] = []
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		if local_name(elem.tag) == "clipPath":
			# Skip clip definitions themselves; only visible targets are processed.
			continue
		clip_ref = _resolved_property(elem, "clip-path")
		if clip_ref is None or clip_ref.strip().lower() in {"", "none"}:
			continue
		cid = _clip_ref_id(clip_ref)
		if cid is None:
			location = elem.getroottree().getpath(elem)
			raise ComplexClipError(location, f"unparseable clip-path {clip_ref!r}")
		targets.append((elem, cid))

	for elem, cid in targets:
		location = elem.getroottree().getpath(elem)
		clip_elem = clip_defs.get(cid)
		if clip_elem is None:
			# A clip-path pointing at a missing/non-clipPath id: the S1 gate would
			# otherwise reject; treat as complex (cannot flatten an absent clip).
			raise ComplexClipError(location, f"clip-path references unknown id #{cid}")
		_flatten_one_clip(elem, clip_elem, location)

	# Remove clipPath defs that are no longer referenced anywhere (S1-safe).
	_remove_unreferenced_clip_defs(root)


#============================================
def _composed_clip_matrix(
	clip_child: lxml.etree._Element, clip_elem: lxml.etree._Element, location: str,
) -> tuple[float, ...]:
	"""Compose the transform chain from the clipPath down to its geometry child.

	clipPath content lives in <defs>, which flatten_transforms intentionally
	skips, so a transform on the clip child (or on the clipPath element itself)
	is still live and must be applied to put the clip geometry in root
	coordinates. The chain is composed outermost-first: clipPath transform, then
	the child transform.

	Args:
		clip_child: The single geometry child of the clipPath.
		clip_elem: The <clipPath> element.
		location: XPath-like location for error reporting.

	Returns:
		The composed 6-tuple affine matrix (identity when no transforms present).

	Raises:
		ComplexClipError: When a transform on the clip chain cannot be parsed.
	"""
	# Build the ancestor chain from clipPath (outermost) down to the clip child.
	chain: list[lxml.etree._Element] = []
	node: lxml.etree._Element | None = clip_child
	while node is not None:
		chain.append(node)
		if node is clip_elem:
			break
		node = node.getparent()
	chain.reverse()
	matrix = IDENTITY_MATRIX
	for elem in chain:
		transform_attr = _is_geometry_transform_attr(elem)
		if transform_attr is None:
			continue
		try:
			items = parse_transform_list(transform_attr, location)
			this_matrix = transforms_multiply(items, location)
		except UnsupportedTransformError as exc:
			# A transform v3 cannot flatten inside a clip makes the clip complex.
			raise ComplexClipError(location, f"clip transform unsupported: {exc.detail}")
		matrix = multiply_matrices(matrix, this_matrix)
	return matrix


#============================================
def _clip_polygon_for_flatten(
	clip_elem: lxml.etree._Element, location: str,
) -> "shapely.geometry.base.BaseGeometry":
	"""Build the clip region polygon in root coordinates from a simple clipPath.

	Enforces the simple-clip-side allowlist via _clip_child_geometry_node (which
	rejects multi-child, nested, forbidden-child, and objectBoundingBox clips),
	then composes any live transform on the clip chain and applies the clip-rule.
	This is the single source of the clip polygon shared by the no-op containment
	test and the fall-through intersection.

	Args:
		clip_elem: The resolved <clipPath> element.
		location: XPath-like location of the target (for errors).

	Returns:
		A shapely polygon for the clip region (possibly empty).

	Raises:
		ComplexClipError: When the clip side is outside the simple allowlist.
	"""
	clip_child = _clip_child_geometry_node(clip_elem, location)
	clip_child_location = clip_child.getroottree().getpath(clip_child)
	clip_segments = shape_to_segments(clip_child, clip_child_location)
	if not clip_segments:
		raise ComplexClipError(location, "clipPath child has no usable geometry")
	# The clipPath lives in defs, so flatten_transforms never baked the clip
	# child's own transform (or transforms on ancestors up to the clipPath) into
	# its geometry. Compose that transform chain now and apply it so the clip
	# geometry is in root coordinates, matching the already-flattened target.
	clip_matrix = _composed_clip_matrix(clip_child, clip_elem, clip_child_location)
	if not matrix_is_identity(clip_matrix):
		clip_segments = apply_matrix_to_segments(clip_segments, clip_matrix)
	clip_rule = _resolve_fill_rule(clip_child, "clip-rule")
	return _polygon_from_segments(clip_segments, clip_rule, _CLIP_FLATTEN_TOLERANCE)


#============================================
def _clip_is_noop(
	clip_poly: "shapely.geometry.base.BaseGeometry",
	target_envelope: "shapely.geometry.base.BaseGeometry",
) -> bool:
	"""Return True when the clip region fully contains the target's painted envelope.

	The clip polygon is SHRUNK by _CLIP_NOOP_MARGIN before the containment
	test. A no-op fires only when the target fits inside the clip with this margin
	to spare. Shrinking makes the test CONSERVATIVE (harder to pass): a target
	that protrudes even a sub-pixel amount past the clip edge fails the test and
	the clip is kept. This guards against polyline-approximation slop on the clip
	boundary causing a genuine trim to be misread as a no-op.

	When the shrunk clip collapses to empty geometry (very thin clip polygon),
	the test conservatively returns False (not a no-op).

	An empty clip or empty envelope is never a no-op (an empty clip would
	clip everything away, not nothing).

	Args:
		clip_poly: The clip region polygon (root coordinates).
		target_envelope: The target's painted envelope (filled + stroke).

	Returns:
		True when the clip changes nothing visible (a dead page-bounds clip).
	"""
	if clip_poly.is_empty or target_envelope.is_empty:
		return False
	# Shrink the clip by the margin; if it collapses, keep the clip (conservative).
	shrunk = clip_poly.buffer(-_CLIP_NOOP_MARGIN)
	if shrunk.is_empty:
		return False
	return bool(shrunk.contains(target_envelope))


#============================================
def _flatten_one_clip(
	elem: lxml.etree._Element, clip_elem: lxml.etree._Element, location: str,
) -> None:
	"""Flatten one target/clip pair: intersect, drop a no-op ref, or reject.

	The clip side must be a simple clip (else ComplexClipError). For the target:
	  - no-op clip (region already contains the painted target): drop the
	    clip-path reference and leave the target d UNCHANGED. This is render-
	    identical by construction (intersecting a shape with a region that
	    contains it returns the shape) and avoids any precision loss. Runs for
	    both filled and stroke-only targets.
	  - filled target, genuinely clipped: emit the target INTERSECT clip as the
	    new d (existing behavior).
	  - stroke-only target, genuinely clipped: ComplexClipError (a real stroke
	    trim needs stroke-to-path expansion, which is out of scope).

	Args:
		elem: The clipped target element (a <path> after shape conversion).
		clip_elem: The resolved <clipPath> element.
		location: XPath-like location of the target (for errors).

	Raises:
		ComplexClipError: When the allowlist fails or a genuine stroke trim is hit.
	"""
	# Target geometry (no fill check) and the simple-clip-side polygon. The clip
	# polygon build raises ComplexClipError for any complex clip side, so a
	# complex clip is rejected even when the target would otherwise be a no-op.
	target_segments = _target_segments_for_clip(elem, location)
	clip_poly = _clip_polygon_for_flatten(clip_elem, location)

	# No-op short circuit: the painted target envelope is fully inside the clip.
	target_envelope = _target_envelope_polygon(elem, target_segments)
	if _clip_is_noop(clip_poly, target_envelope):
		# Render-identical drop: keep the target d, just remove the dead clip ref.
		_remove_clip_path_reference(elem)
		return

	# Not a no-op. A stroke-only target would need a genuine stroke trim, which
	# v3 does not support; reject it as complex (matches the prior behavior).
	if _target_is_stroke_only(elem):
		raise ComplexClipError(location, "clip target is stroke-only (fill:none)")

	# Filled target genuinely clipped: emit target INTERSECT clip as the new d.
	target_rule = _resolve_fill_rule(elem, "fill-rule")
	target_poly = _polygon_from_segments(target_segments, target_rule, _CLIP_FLATTEN_TOLERANCE)
	if target_poly.is_empty or clip_poly.is_empty:
		# Degenerate input geometry: nothing fillable to clip.
		clipped = shapely.geometry.Polygon()
	else:
		clipped = shapely.make_valid(target_poly.intersection(clip_poly))

	# Emit the clipped geometry as absolute path data (empty string when empty).
	new_d = _geometry_to_path_d(clipped)
	if new_d:
		elem.set("d", new_d)
	else:
		# Empty intersection: the element keeps no drawable geometry. Set an empty
		# d so the element contributes nothing to the bbox; compute_bbox treats a
		# path with no segments as no geometry (EMPTY_GEOMETRY applies only when
		# the whole document has none).
		elem.set("d", "")
	# Drop the now-applied clip reference (presentation attr and inline style).
	_remove_clip_path_reference(elem)


#============================================
def _clip_ref_id(clip_ref: str) -> str | None:
	"""Extract the fragment id from a clip-path value, or None.

	Accepts url(#id), url('#id'), url("#id"). A bare #id is not valid clip-path
	syntax and returns None.
	"""
	match = _URL_REF_RE.search(clip_ref)
	if match:
		return match.group(1)
	return None


#============================================
def _remove_clip_path_reference(elem: lxml.etree._Element) -> None:
	"""Remove the clip-path reference from an element (attribute and inline style)."""
	if elem.get("clip-path") is not None:
		del elem.attrib["clip-path"]
	style_str = elem.get("style")
	if style_str:
		props = _parse_inline_style(style_str)
		if "clip-path" in props:
			del props["clip-path"]
			# Rebuild the style string without the clip-path declaration.
			if props:
				elem.set("style", "; ".join(f"{k}: {v}" for k, v in props.items()))
			else:
				del elem.attrib["style"]


#============================================
def _remove_unreferenced_clip_defs(root: lxml.etree._Element) -> None:
	"""Remove <clipPath> defs no longer referenced by any clip-path in the tree.

	S1-safe: a clipPath whose id still appears in some clip-path reference is
	kept; only fully-unreferenced ordinary clipPath defs are detached.  The closed
	runtime material anchor is also kept because the renderer references it only
	after DOM injection.  Removing other dead defs keeps the document free of
	dead resources without creating a dangling reference.

	Args:
		root: The parsed SVG root element. Modified in place.
	"""
	# Collect every clip-path id still referenced anywhere.
	referenced: set[str] = set()
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		clip_ref = _resolved_property(elem, "clip-path")
		if clip_ref is None:
			continue
		cid = _clip_ref_id(clip_ref)
		if cid is not None:
			referenced.add(cid)
	# Detach clipPath defs whose id is neither locally referenced nor a closed
	# runtime material anchor.
	to_remove: list[lxml.etree._Element] = []
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		if local_name(elem.tag) != "clipPath":
			continue
		cid = elem.get("id")
		if cid is None or (cid not in referenced and cid not in RUNTIME_EXTERNAL_CLIP_IDS):
			to_remove.append(elem)
	for elem in to_remove:
		parent = elem.getparent()
		if parent is not None:
			parent.remove(elem)


#============================================
def _detect_clippath(root: lxml.etree._Element) -> RejectionReason | None:
	"""Detect only COMPLEX clip-path usage; simple clips are flattened, not rejected.

	The simple-clip allowlist permits the supported cases while the classifier rejects
	actual flattening (and the complex-clip rejection) is performed by
	flatten_clip_paths inside normalize_svg_file, which raises ComplexClipError ->
	CLIPPATH_UNSUPPORTED_COMPLEX for anything outside the allowlist. Because the
	flattening step is the authority on simple-vs-complex, this classifier no
	longer rejects clip-path on its own: doing so would wrongly refuse the simple
	unsupported clips.

	The function is kept in classify()'s detector list (signature unchanged) so
	the composition contract is preserved; it simply always returns None now. The
	real verdict comes from flatten_clip_paths.

	Args:
		root: The parsed SVG root element.

	Returns:
		Always None (clip handling moved to flatten_clip_paths).
	"""
	return None


# Geometry-affecting CSS properties. A <style> rule that sets any of these
# triggers STYLE_GEOMETRY_UNSUPPORTED (v3 resolves geometry from inline style
# only; a stylesheet rule would need a selector/specificity engine v3 does not
# have). Note: fill and fill-opacity ARE in this set and ARE rejected in a
# <style> rule -- they affect whether geometry is drawn (fill:none) and the
# floor-shadow signal, so v3 cannot leave them to an unresolved cascade. Only
# properties absent from this set (e.g. color, stop-color, paint-order) may
# remain in a preserved <style> block.
_STYLE_GEOMETRY_PROPS = frozenset({
	"display", "visibility", "opacity", "fill", "fill-opacity",
	"stroke", "stroke-width", "stroke-opacity", "vector-effect",
	"filter", "clip-path", "mask",
	"marker", "marker-start", "marker-mid", "marker-end",
})


#============================================
def _detect_style_geometry(root: lxml.etree._Element) -> RejectionReason | None:
	"""Classify <style> blocks: reject geometry-affecting or unparseable CSS.

	Per the support contract, <style> blocks are preserved (paint/color rules
	stay) and only their url(#id) refs are rewritten on rename (F8). But a rule
	that sets a geometry-affecting property would change rendering in a way the
	inline-only cascade cannot resolve, so it is rejected
	(STYLE_GEOMETRY_UNSUPPORTED). A <style> block tinycss2 cannot parse is
	rejected (STYLE_UNPARSEABLE).

	Args:
		root: The parsed SVG root element.

	Returns:
		RejectionReason (STYLE_UNPARSEABLE or STYLE_GEOMETRY_UNSUPPORTED) when a
		style block is unparseable or sets a geometry property, else None.
	"""
	for style_elem in _iter_style_blocks(root):
		css_text = style_elem.text or ""
		location = style_elem.getroottree().getpath(style_elem)
		# tinycss2 is error-tolerant: it returns ParseError nodes rather than
		# raising. Treat any ParseError as STYLE_UNPARSEABLE.
		rules = tinycss2.parse_stylesheet(
			css_text, skip_comments=True, skip_whitespace=True
		)
		for node in rules:
			if node.type == "error":
				reason = RejectionReason(
					code="STYLE_UNPARSEABLE",
					message="A <style> block could not be parsed as CSS.",
					fix="Repair or remove the malformed <style> block before ingestion.",
					element=location,
				)
				return reason
			# Only qualified rules (selector { declarations }) carry properties we
			# care about. At-rules (e.g. @font-face) are not geometry-affecting here.
			if node.type != "qualified-rule":
				continue
			geometry_reason = _style_rule_geometry_reason(node, location)
			if geometry_reason is not None:
				return geometry_reason
	return None


#============================================
def _style_rule_geometry_reason(
	rule: "tinycss2.ast.QualifiedRule", location: str,
) -> RejectionReason | None:
	"""Return a STYLE_GEOMETRY_UNSUPPORTED reason if a CSS rule sets a geometry prop.

	Parses the rule's declaration block and checks each declared property name
	against _STYLE_GEOMETRY_PROPS.

	Args:
		rule: A tinycss2 qualified-rule node.
		location: XPath-like location of the owning <style> element.

	Returns:
		RejectionReason when a geometry-affecting property is declared, else None.
	"""
	declarations = tinycss2.parse_declaration_list(
		rule.content, skip_comments=True, skip_whitespace=True
	)
	for decl in declarations:
		if decl.type == "error":
			# A malformed declaration inside an otherwise-parseable rule -> unparseable.
			reason = RejectionReason(
				code="STYLE_UNPARSEABLE",
				message="A <style> declaration could not be parsed as CSS.",
				fix="Repair or remove the malformed <style> block before ingestion.",
				element=location,
			)
			return reason
		if decl.type != "declaration":
			continue
		prop_name = decl.lower_name
		if prop_name in _STYLE_GEOMETRY_PROPS:
			reason = RejectionReason(
				code="STYLE_GEOMETRY_UNSUPPORTED",
				message=(
					f"A <style> rule sets the geometry-affecting property '{prop_name}'. "
					"v3 resolves geometry from inline style only."
				),
				fix=(
					"Move geometry-affecting properties to inline style= attributes "
					"(or bake them into the geometry) before ingestion."
				),
				element=location,
			)
			return reason
	return None


#============================================
def _detect_pattern(root: lxml.etree._Element) -> RejectionReason | None:
	"""Classify <pattern> elements: preserve paint-only, reject anything with content.

	Per the support contract, a pattern is preserved only when it is paint-only:
	it has no child GEOMETRY, no images, no external refs, no transform, and no
	unresolved refs. Any pattern with child geometry (shapes/paths), an <image>,
	an external href, a patternTransform, or a transform is rejected with
	PATTERN_UNSUPPORTED (avoids a hidden pattern renderer). The image/external/
	transform cases are already caught by earlier detectors when they appear
	anywhere; this detector specifically catches a pattern whose CHILD content is
	drawable geometry (the case earlier detectors do not reject on their own).

	Args:
		root: The parsed SVG root element.

	Returns:
		RejectionReason with code PATTERN_UNSUPPORTED when an unsupported pattern
		is found, else None.
	"""
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		if local_name(elem.tag) != "pattern":
			continue
		location = elem.getroottree().getpath(elem)
		# A patternTransform makes the pattern non-paint-only for v3's purposes.
		if elem.get("patternTransform") is not None or elem.get("transform") is not None:
			reason = RejectionReason(
				code="PATTERN_UNSUPPORTED",
				message="A <pattern> with a transform is not supported.",
				fix="Bake the pattern into explicit geometry before ingestion.",
				element=location,
			)
			return reason
		# Any drawable child geometry makes this a content pattern (would need a
		# pattern renderer to bbox correctly).
		for child in elem.iter():
			if child is elem or not isinstance(child.tag, str):
				continue
			child_tag = local_name(child.tag)
			if child_tag in SHAPE_TAGS or child_tag in {"image", "use"}:
				reason = RejectionReason(
					code="PATTERN_UNSUPPORTED",
					message="A <pattern> with child geometry is not supported (no pattern renderer).",
					fix="Bake the pattern into explicit geometry before ingestion.",
					element=location,
				)
				return reason
	return None


#============================================
def _resolved_property(elem: lxml.etree._Element, prop: str) -> str | None:
	"""Return the value of a property from inline style= or presentation attribute.

	Inline-only cascade (per the v3 CSS scope): the inline style= block wins over
	the presentation attribute of the same name. No class/stylesheet resolution.

	Args:
		elem: The SVG element.
		prop: The property/attribute name (e.g. "filter", "clip-path").

	Returns:
		The resolved value string, or None when the property is set nowhere on
		this element.
	"""
	style_str = elem.get("style") or ""
	if style_str:
		inline = _parse_inline_style(style_str)
		if prop in inline:
			return inline[prop]
	return elem.get(prop)


#============================================
# B1 editor-cruft removal (positive allowlist). Removes ONLY elements and
# attributes in the Inkscape, Sodipodi, and Adobe Illustrator namespaces. Every
# SVG rendering attribute, every def, every id, and all dc/cc/rdf/title/desc are
# preserved. Ported by hand in spirit from scour removeNamespacedElements /
# removeNamespacedAttributes (Apache-2.0); no scour file is copied.
#============================================

# Namespace URIs whose elements and attributes are editor cruft (B1 allowlist).
_EDITOR_CRUFT_NS = frozenset({
	"http://www.inkscape.org/namespaces/inkscape",
	"http://sodipodi.sourceforge.net/DTD/sodipodi-0.0.dtd",
	"http://ns.adobe.com/AdobeIllustrator/10.0/",
	"http://ns.adobe.com/AdobeSVGViewerExtensions/3.0/",
	"http://ns.adobe.com/Extensibility/1.0/",
	"http://ns.adobe.com/Flows/1.0/",
	"http://ns.adobe.com/GenericCustomNamespace/1.0/",
	"http://ns.adobe.com/ImageReplacement/1.0/",
	"http://ns.adobe.com/SaveForWeb/1.0/",
	"http://ns.adobe.com/Variables/1.0/",
	"http://ns.adobe.com/XPath/1.0/",
	"http://ns.adobe.com/pdf/1.3/",
})


#============================================
def _namespace_uri_of(name: str) -> str | None:
	"""Return the namespace URI of a Clark-notation tag/attr name, or None."""
	if isinstance(name, str) and name.startswith("{"):
		return name[1:].split("}", 1)[0]
	return None


#============================================
def remove_editor_cruft(root: lxml.etree._Element) -> None:
	"""Remove editor-namespace elements and attributes (B1 positive allowlist).

	Removes only elements whose tag is in an editor-cruft namespace (Inkscape,
	Sodipodi, Adobe) and only attributes whose name is in one of those
	namespaces. Preserves every SVG-namespace rendering attribute, every def,
	every id, and all dc/cc/rdf attribution and <title>/<desc>. Modifies root in
	place.

	Args:
		root: The parsed SVG root element.
	"""
	# Collect editor-cruft elements first (do not mutate while iterating).
	to_remove: list[lxml.etree._Element] = []
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		ns = _namespace_uri_of(elem.tag)
		if ns is not None and ns in _EDITOR_CRUFT_NS:
			to_remove.append(elem)
	for elem in to_remove:
		parent = elem.getparent()
		if parent is not None:
			parent.remove(elem)
	# Strip editor-cruft attributes from every remaining element.
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		cruft_attrs = [
			name for name in elem.attrib
			if _namespace_uri_of(name) in _EDITOR_CRUFT_NS
		]
		for name in cruft_attrs:
			del elem.attrib[name]


#============================================
def collect_internal_references(root: lxml.etree._Element) -> list[tuple[str, str]]:
	"""Collect every internal (#fragment) reference in the document (S1 input).

	Scans presentation attributes carrying url(#id), href/xlink:href fragments,
	and url(#id) references inside <style> block text. Each entry is a
	(fragment-id, element-location) pair.

	Args:
		root: The parsed SVG root element.

	Returns:
		List of (referenced_id, element_location) tuples for every internal ref.
	"""
	refs: list[tuple[str, str]] = []
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		location = elem.getroottree().getpath(elem)
		# href / xlink:href direct fragment references.
		href = _href_value(elem)
		if href is not None and href.strip().startswith("#"):
			refs.append((href.strip()[1:], location))
		# url(#id) references in presentation attributes and inline style.
		for attr in _URL_REF_ATTRS:
			val = _resolved_property(elem, attr)
			if not val:
				continue
			for match in _URL_REF_RE.finditer(val):
				refs.append((match.group(1), location))
	# url(#id) references inside <style> block text.
	for style_elem in _iter_style_blocks(root):
		css_text = style_elem.text or ""
		location = style_elem.getroottree().getpath(style_elem)
		for match in _URL_REF_RE.finditer(css_text):
			refs.append((match.group(1), location))
	return refs


#============================================
def collect_defined_ids(root: lxml.etree._Element) -> set[str]:
	"""Return the set of all id values declared anywhere in the document (S1)."""
	ids: set[str] = set()
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		id_val = elem.get("id")
		if id_val is not None:
			ids.add(id_val)
	return ids


#============================================
def check_reference_integrity(root: lxml.etree._Element) -> RejectionReason | None:
	"""S1 hard gate: confirm every internal reference resolves to a defined id.

	Runs AFTER all rewrites (ASCII rename, F8, transform flatten, shape->path)
	and BEFORE the final write. If any internal url(#id) / href="#id" reference
	names an id that does not exist in the output tree, the file is rejected with
	UNRESOLVED_REFERENCE (no output written). External refs are already rejected
	earlier; this gate protects predictable rendering of internal refs.

	Args:
		root: The (already normalized) SVG root element.

	Returns:
		RejectionReason with code UNRESOLVED_REFERENCE for the first dangling ref,
		else None.
	"""
	defined = collect_defined_ids(root)
	for ref_id, location in collect_internal_references(root):
		if ref_id not in defined:
			reason = RejectionReason(
				code="UNRESOLVED_REFERENCE",
				message=f"Internal reference '#{ref_id}' does not resolve to any id in the output.",
				fix="Define the referenced id, or remove the dangling reference, before ingestion.",
				element=location,
			)
			return reason
	return None


#============================================
def _detect_text_elements(root: lxml.etree._Element) -> RejectionReason | None:
	"""Detect <text>, <tspan>, or <textPath> anywhere in the document (A5).

	Text elements cannot be normalized by v3 (glyph geometry is font-dependent
	and not computable from path math alone). Prose belongs in layout-manager DOM
	or object data; only approved intrinsic markings may be converted to paths
	before ingestion. Any file containing a text element is rejected with
	TEXT_UNSUPPORTED.

	The classifier calls this detector as part of its single-reason-return flow.

	Args:
		root: The parsed SVG root element.

	Returns:
		RejectionReason with code TEXT_UNSUPPORTED when any text element is found,
		else None.
	"""
	text_local_names = {"text", "tspan", "textPath"}
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		tag = local_name(elem.tag)
		if tag in text_local_names:
			# Build an XPath-like location for the offending element.
			element_location = elem.getroottree().getpath(elem)
			reason = RejectionReason(
				code="TEXT_UNSUPPORTED",
				message="Text elements are not normalized by v3.",
				fix=(
					"Remove prose text and move it to layout-manager DOM or object data; "
					"convert only approved intrinsic markings to paths before ingestion."
				),
				element=element_location,
			)
			return reason
	return None


#============================================
def _detect_runtime_bounds_anchor(root: lxml.etree._Element) -> RejectionReason | None:
	"""Reject an ambiguous or runtime-incompatible material bounds anchor.

	The bounds anchor is optional for generic SVGs. When present, the material
	runtime needs exactly one bare, outside-``defs`` ``<rect>`` to read after
	injection. A duplicate id cannot resolve to one target, and a non-rect or
	definition-space element cannot supply direct rectangle geometry.

	Args:
		root: Parsed SVG root before normalization mutates geometry.

	Returns:
		A UNRESOLVED_REFERENCE reason for an invalid bounds-anchor declaration, or
		None when the optional anchor is absent or valid.
	"""
	anchors = [
		elem
		for elem in root.iter()
		if isinstance(elem.tag, str) and elem.get("id") == RUNTIME_BOUNDS_RECT_ID
	]
	if not anchors:
		return None
	if len(anchors) != 1:
		return RejectionReason(
			code="UNRESOLVED_REFERENCE",
			message=(
				"Material anchor 'anchor_liquid_bounds' must resolve to exactly one "
				"outside-defs rect."
			),
			fix=(
				"Keep one bare id='anchor_liquid_bounds' on the hidden bounds rect; "
				"remove that id from clip geometry and all other elements."
			),
			element=anchors[0].getroottree().getpath(anchors[0]),
		)
	anchor = anchors[0]
	if local_name(anchor.tag) != "rect":
		return RejectionReason(
			code="UNRESOLVED_REFERENCE",
			message="Material anchor 'anchor_liquid_bounds' must resolve to an outside-defs rect.",
			fix="Move the bare id='anchor_liquid_bounds' to one hidden outside-defs rect.",
			element=anchor.getroottree().getpath(anchor),
		)
	parent = anchor.getparent()
	while parent is not None:
		if isinstance(parent.tag, str) and local_name(parent.tag) == "defs":
			return RejectionReason(
				code="UNRESOLVED_REFERENCE",
				message="Material anchor 'anchor_liquid_bounds' must resolve outside <defs>.",
				fix="Move the hidden bounds rect outside <defs>; keep clip geometry under anchor_liquid_clip.",
				element=anchor.getroottree().getpath(anchor),
			)
		parent = parent.getparent()
	return None


#============================================
def classify(root: lxml.etree._Element) -> RejectionReason | None:
	"""Classify the parsed SVG for unsupported features (S2 seam).

	This is the shared classifier seam. It checks text, structural, effect,
	resource, clip, and style features without changing this signature.

	Each detector is a function that takes root and returns a RejectionReason or
	None. They are called in priority order; the first non-None reason is returned
	as the primary rejection reason.

	Args:
		root: The parsed SVG root element.

	Returns:
		A RejectionReason when an unsupported feature is found, else None.
	"""
	# Reject text, tspan, and textPath elements.
	reason = _detect_text_elements(root)
	if reason is not None:
		return reason
	reason = _detect_runtime_bounds_anchor(root)
	if reason is not None:
		return reason

	# Always reject scripts, event handlers, animation, and foreignObject.
	reason = _detect_script_or_handler(root)
	if reason is not None:
		return reason
	reason = _detect_animation_elements(root)
	if reason is not None:
		return reason
	reason = _detect_foreignobject(root)
	if reason is not None:
		return reason

	# Remaining feature rejects use the same single-reason contract.
	# Order: structural rejects (use/symbol), effect rejects (filter/mask/marker),
	# resource rejects (image embedded/external, external href), clip, style, then
	# pattern. The first non-None reason wins as the primary rejection.
	for detector in (
		_detect_use_or_symbol,
		_detect_filter,
		_detect_mask,
		_detect_marker,
		_detect_image,
		_detect_external_href,
		_detect_clippath,
		_detect_style_geometry,
		_detect_pattern,
	):
		reason = detector(root)
		if reason is not None:
			return reason
	return None


#============================================
def parse_svg(input_path: Path) -> lxml.etree._ElementTree:
	"""Parse an SVG once with lxml, WITHOUT recovery.

	The v3 gate parses exactly once and never normalizes recovered XML. A parse
	failure is the caller's signal to reject the file with PARSER_ERROR; the
	feature classification may separately re-parse with recover only to classify
	the likely feature, but the normalizer here does not.

	Args:
		input_path: Path to the source SVG.

	Returns:
		The parsed lxml ElementTree.

	Raises:
		lxml.etree.XMLSyntaxError: When the document is not well-formed.
	"""
	# recover=False: malformed input is a hard parse failure, not silently fixed.
	# resolve_entities=False / no_network=True: do not expand entities or fetch
	# external resources during parse (defense in depth; DOCTYPE/entity files are
	# rejected by the classifier in a later WP).
	parser = lxml.etree.XMLParser(
		recover=False,
		resolve_entities=False,
		no_network=True,
		huge_tree=False,
	)
	tree = lxml.etree.parse(str(input_path), parser=parser)
	return tree


#============================================
def _build_canonical_nsmap(root: lxml.etree._Element) -> dict[str | None, str]:
	"""Build a serialization nsmap that pins canonical prefixes.

	Starts from the parsed root's own nsmap (so the default SVG namespace and any
	author-declared prefixes are kept) and adds the canonical attribution/editor
	prefixes for any namespace the document actually uses, so lxml never emits
	ns0:/ns1:. This is the core of the S4 "no ns0:" guarantee.

	Args:
		root: The parsed SVG root element.

	Returns:
		A prefix -> uri mapping suitable for an lxml nsmap.
	"""
	# Collect every namespace URI actually used by elements or attributes so we
	# only pin prefixes the document needs (avoids declaring unused namespaces).
	used_uris: set[str] = set()
	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		if elem.tag.startswith("{"):
			used_uris.add(elem.tag[1:].split("}", 1)[0])
		for attr_name in elem.attrib:
			if isinstance(attr_name, str) and attr_name.startswith("{"):
				used_uris.add(attr_name[1:].split("}", 1)[0])

	# Start from the root's declared nsmap (default SVG ns + author prefixes).
	nsmap: dict[str | None, str] = dict(root.nsmap)
	# Ensure the default namespace is SVG when present.
	if None not in nsmap:
		nsmap[None] = SVG_NS

	# Invert to find which URIs already have a prefix, so we do not double-map.
	mapped_uris = set(nsmap.values())
	for prefix, uri in CANONICAL_NS_PREFIXES.items():
		if uri in used_uris and uri not in mapped_uris:
			nsmap[prefix] = uri
			mapped_uris.add(uri)
	return nsmap


#============================================
def _reroot_with_nsmap(root: lxml.etree._Element) -> lxml.etree._Element:
	"""Return root rebuilt under a canonical nsmap if new prefixes are needed.

	lxml fixes an element's nsmap at creation time; you cannot add a namespace
	prefix to an existing element. To guarantee canonical prefixes (no ns0:),
	build a fresh root element with the full canonical nsmap and move the
	original children, attributes, text, and tail onto it.

	Args:
		root: The parsed SVG root element.

	Returns:
		Either the original root (when no new prefixes were needed) or a new root
		carrying the canonical nsmap with identical content.
	"""
	desired = _build_canonical_nsmap(root)
	# If the root already declares every desired prefix->uri, no reroot needed.
	current = dict(root.nsmap)
	if all(current.get(p) == u for p, u in desired.items()):
		return root
	# Build a replacement root with the desired nsmap and copy everything over.
	new_root = lxml.etree.Element(root.tag, nsmap=desired)
	for name, value in root.attrib.items():
		new_root.set(name, value)
	new_root.text = root.text
	new_root.tail = root.tail
	for child in list(root):
		new_root.append(child)
	return new_root


#============================================
def serialize_canonical(tree_or_root: lxml.etree._Element) -> bytes:
	"""Serialize an SVG element to canonical S4 bytes.

	S4 guarantees: UTF-8 encoding, a single trailing newline, and stable
	namespace prefixes (no ns0:/ns1: renaming). The XML declaration is omitted
	(v2 wrote none); any pre-root comments are re-injected by the caller.

	Args:
		tree_or_root: The SVG root element to serialize.

	Returns:
		UTF-8 bytes ending in exactly one newline.
	"""
	# pretty_print=False keeps author whitespace; we only guarantee a final
	# newline. xml_declaration=False matches v2 (caller may add a preamble).
	data = lxml.etree.tostring(
		tree_or_root,
		encoding="utf-8",
		xml_declaration=False,
		pretty_print=False,
	)
	# Guarantee exactly one trailing newline.
	text = data.decode("utf-8").rstrip("\n") + "\n"
	return text.encode("utf-8")


#============================================
def extract_pre_root_comments(source_text: str) -> list[str]:
	"""Return XML comments that appear before the <svg> root element.

	Comments between <?xml ...?> and <svg ...> are otherwise dropped on
	round-trip, stripping attribution credit lines. lxml keeps comments inside
	the root via the tree, but pre-root siblings are re-injected by the caller.

	Args:
		source_text: Full raw text of an SVG file.

	Returns:
		Each captured comment as its full <!-- ... --> form, in source order.
	"""
	pre_root_match = re.search(r"^(.*?)<svg\b", source_text, re.DOTALL)
	if not pre_root_match:
		return []
	return re.findall(r"<!--.*?-->", pre_root_match.group(1), re.DOTALL)


#============================================
def _reject(
	input_path: Path, output_path: Path, code: str, message: str, fix: str, element: str = "",
) -> NormalizeResult:
	"""Build a REJECTED NormalizeResult (no output written, input untouched).

	Args:
		input_path: The source SVG path.
		output_path: Where output would have been written.
		code: A stable token from REASON_CODES.
		message: Why the file was rejected.
		fix: Suggested author fix.
		element: XPath-like location when available.

	Returns:
		A NormalizeResult carrying the rejection; output_written is False.
	"""
	reason = RejectionReason(code=code, message=message, fix=fix, element=element)
	result = NormalizeResult(
		input_path=input_path,
		output_path=output_path,
		rejection=reason,
		output_written=False,
	)
	return result


#============================================
def normalize_svg_file(
	input_path: Path,
	output_path: Path,
	padding: float = 2.0,
	remove_floor_shadow: bool = False,
) -> NormalizeResult:
	"""Normalize an SVG, or reject it; the single public entry point.

	Pipeline: parse once (no recover) -> classify ->
	ASCII-clean ids -> flatten transforms (A1) -> shape->path (A2) ->
	B1 editor-cruft removal -> [D1 floor-shadow removal when enabled] ->
	compute bbox -> ordinary: shift to origin/rewrite viewBox; material: retain
	authored root frame -> canonical serialize
	(S4) -> write output.

	D1 (floor-shadow removal) runs BEFORE compute_bbox so the single crop
	tightens around the real object.  It is gated by remove_floor_shadow; with
	that False (the default) the normal output path is unchanged.

	On rejection no output is written and the input is left untouched, even when
	output_path equals input_path (the --in-place case): the write only happens
	after every gate passes.

	Args:
		input_path: Path to source SVG.
		output_path: Path to write the normalized SVG.
		padding: Padding around drawn content, in user units. Default 2.
		remove_floor_shadow: When True, detect and remove floor-shadow elements
			before the bbox pass (D1).  Default False (no-op for gate verdict).

	Returns:
		A NormalizeResult: normalized (rejection is None, output_written True) or
		rejected (rejection set, output_written False, no file written).
	"""
	try:
		source_text = input_path.read_text(encoding="utf-8")
	except UnicodeDecodeError as exc:
		# Non-UTF-8 files are rejected as PARSER_ERROR: v3 requires UTF-8 (S4).
		return _reject(
			input_path, output_path,
			code="PARSER_ERROR",
			message=f"SVG is not valid UTF-8: {exc}",
			fix="Re-save the SVG as UTF-8 before ingestion.",
		)
	pre_root_comments = extract_pre_root_comments(source_text)

	# Check raw text for DOCTYPE and entities before parsing. parse_svg uses
	# resolve_entities=False so a DOCTYPE may parse without error; we reject it
	# explicitly here so the gate is cheap and correct.
	doctype_rejection = detect_doctype_or_entity(source_text)
	if doctype_rejection is not None:
		return NormalizeResult(
			input_path=input_path,
			output_path=output_path,
			rejection=doctype_rejection,
			output_written=False,
		)

	# Parse once without recovery. A parse failure is a hard reject; never
	# normalize recovered XML.
	try:
		tree = parse_svg(input_path)
	except lxml.etree.XMLSyntaxError as exc:
		return _reject(
			input_path, output_path,
			code="PARSER_ERROR",
			message=f"SVG is not well-formed XML: {exc}",
			fix="Repair the XML so it parses without recovery, then re-run v3.",
		)

	root = tree.getroot()
	# Material-rendered SVGs use the same geometry/security normalizer, but their
	# authored semantic groups are a closed contract rather than disposable art
	# grouping. Validate before any destructive transform and retain a signature
	# that the normalized result must reproduce.
	try:
		is_material = validate_reserved_attributes(root)
		if is_material:
			inject_normalizer_boundary_tokens(root)
			material_signature = material_boundary_signature(root, allow_normalizer_tokens=True)
		else:
			material_signature = None
	except MaterialSvgValidationError as exc:
		return _reject(
			input_path, output_path,
			code="MATERIAL_SEMANTIC_INVALID",
			message=str(exc),
			fix="Repair the closed data-vlab material layer contract before normalization.",
		)

	# Feature classification returns one stable rejection reason when needed.
	# non-None result short-circuits to a rejection before any geometry edit.
	rejection = classify(root)
	if rejection is not None:
		return NormalizeResult(
			input_path=input_path,
			output_path=output_path,
			rejection=rejection,
			output_written=False,
		)

	# Rename non-ASCII id/data-name values to ASCII and update in-file references.
	make_ascii_clean(root)

	# Flatten element/group transforms into absolute root-coordinate geometry
	# (A1) BEFORE bbox computation, so the bbox is measured on final coordinates
	# and the canonical invariant (no geometry transform remaining) holds. A
	# transform v3 cannot safely apply -> rejection (no output written).
	try:
		flatten_transforms(root)
	except UnsupportedTransformError as exc:
		return _reject(
			input_path, output_path,
			code="UNSUPPORTED_TRANSFORM",
			message=f"A transform could not be safely flattened. ({exc})",
			fix=(
				"Pre-flatten the transform in your editor (in Inkscape: select the "
				"object, then Object > Transform > Apply, or ungroup transformed "
				"groups) before ingestion."
			),
			element=exc.element_location,
		)
	except NonScalingStrokeError as exc:
		return _reject(
			input_path, output_path,
			code="NONSCALING_STROKE_UNRESOLVED",
			message=(
				"A vector-effect=non-scaling-stroke element sits under a scaling "
				f"transform that v3 cannot resolve. ({exc})"
			),
			fix=(
				"Remove the non-scaling-stroke effect or pre-flatten the transform "
				"before ingestion."
			),
			element=exc.element_location,
		)
	except UnsupportedUnitError as exc:
		return _reject(
			input_path, output_path,
			code="UNSUPPORTED_UNIT",
			message=(
				"A required size attribute uses a non-user unit (%, mm, cm, in, pt, pc, em, ex). "
				f"({exc})"
			),
			fix=(
				"Convert all geometry to user units (unitless or px) before ingestion."
			),
			element=exc.element_location,
		)

	# Convert every remaining shape element (rect, circle, ellipse, line,
	# polyline, polygon) to an absolute <path> (A2). Elements that already
	# carried a transform were rewritten by flatten_transforms above; this pass
	# covers transform-free shapes and ensures the output is path-only for all
	# supported geometry.  Runs after flattening so geometry is in root coords.
	try:
		convert_shapes_to_paths(root)
	except UnsupportedUnitError as exc:
		return _reject(
			input_path, output_path,
			code="UNSUPPORTED_UNIT",
			message=(
				"A required size attribute uses a non-user unit (%, mm, cm, in, pt, pc, em, ex). "
				f"({exc})"
			),
			fix="Convert all geometry to user units (unitless or px) before ingestion.",
			element=exc.element_location,
		)

	# A6: flatten simple clipPaths into the clipped target's path geometry, drop
	# the clip ref, and remove unreferenced clipPath defs. Runs AFTER
	# transform-flatten + shape->path (so target and clip are absolute root-coord
	# geometry) and BEFORE compute_bbox/S1 (so the bbox is measured on the clipped
	# region and S1 never sees the dropped clip ref). A clip outside the simple
	# allowlist -> CLIPPATH_UNSUPPORTED_COMPLEX rejection (no output written).
	try:
		# The material clip is compiler-owned: authored semantic groups never
		# carry clip-path, while anchor_liquid_clip remains in defs for the derived
		# compiled gravity-part region. Generic clips on ordinary nested artwork still use
		# the shared supported flattening behavior.
		flatten_clip_paths(root)
	except ComplexClipError as exc:
		return _reject(
			input_path, output_path,
			code="CLIPPATH_UNSUPPORTED_COMPLEX",
			message=f"A clipPath could not be flattened. ({exc.detail})",
			fix=(
				"Apply the clip in your editor (flatten to the clipped path), or "
				"simplify it to a single filled clip shape, before ingestion."
			),
			element=exc.element_location,
		)

	# B1: remove editor-namespace cruft (Inkscape/Sodipodi/Adobe) before the bbox
	# pass. This is a positive allowlist: only editor-namespace elements and
	# attributes are removed; every SVG render attr, def, id, and dc/cc/rdf
	# attribution is preserved. Cruft removal never changes the verdict; it only
	# cleans non-portable editor state.
	remove_editor_cruft(root)

	# Floor-shadow removal runs before compute_bbox so the single
	# crop tightens around the real object after shadow removal.  A preliminary
	# bbox pass is needed to identify the bottom-band threshold; this is a cheap
	# pass over the already-prepared geometry.  Removal does NOT affect the gate
	# verdict -- if removing a shadow breaks ref integrity or leaves no geometry,
	# the file is rejected like any other (handled below).
	if remove_floor_shadow and not is_material:
		try:
			pre_bbox = compute_bbox(root)
		except (UnsupportedUnitError, ValueError):
			# No geometry or bad units -- let the real bbox pass produce the rejection.
			pre_bbox = None
		if pre_bbox is not None:
			shadow_candidates = detect_floor_shadow_candidates(root, pre_bbox)
			if shadow_candidates:
				remove_floor_shadow_elements(root, shadow_candidates)

	# Compute the drawn bbox. No drawable geometry is an EMPTY_GEOMETRY reject;
	# a non-user unit on a required size attr is an UNSUPPORTED_UNIT reject.
	# Neither writes output.
	try:
		bbox = compute_bbox(root)
	except UnsupportedUnitError as exc:
		return _reject(
			input_path, output_path,
			code="UNSUPPORTED_UNIT",
			message=(
				"A required size attribute uses a non-user unit (%, mm, cm, in, pt, pc, em, ex). "
				f"({exc})"
			),
			fix=(
				"Convert all geometry to user units (unitless or px) before ingestion. "
				"In Inkscape: File > Document Properties > Scale to 1px = 1 user unit, "
				"then export or save."
			),
			element=exc.element_location,
		)
	except ValueError as exc:
		return _reject(
			input_path, output_path,
			code="EMPTY_GEOMETRY",
			message=f"No drawable SVG geometry found: {exc}",
			fix="Ensure the SVG contains at least one visible shape or path.",
		)

	if is_material:
		# Material assets have structural anchors and compiled gravity-part
		# operations expressed in their authored root coordinate system.  Unlike an
		# ordinary decorative SVG, their canvas is part of the semantic contract:
		# bbox cropping would translate both painted artwork and the anchors, change
		# the root viewBox, and make an otherwise identical compiled fallback render
		# at a different scale.  Keep the complete authored viewport (including
		# width/height when supplied) while retaining the shared geometry/security
		# normalization above.  `bbox` remains useful normalization evidence; it is
		# deliberately not a material-frame rewrite input.
		view_box = root.get("viewBox")
	else:
		dx = -bbox.min_x + padding
		dy = -bbox.min_y + padding
		new_width = bbox.width + 2 * padding
		new_height = bbox.height + 2 * padding
		for elem in root.iter():
			if isinstance(elem.tag, str):
				shift_element(elem, dx, dy)
		# Use fmt_precise for the viewBox and width/height attrs (A4 precision).
		root.set("viewBox", f"0 0 {fmt_precise(new_width)} {fmt_precise(new_height)}")
		# Width/height attrs often disagree with viewBox after cropping. Keep them in
		# sync if present.
		if root.get("width") is not None:
			root.set("width", fmt_precise(new_width))
		if root.get("height") is not None:
			root.set("height", fmt_precise(new_height))
		view_box = root.get("viewBox")

	# Rebuild the root under a canonical nsmap when new prefixes are needed so
	# attribution prefixes serialize as dc:/cc:/rdf: (S4 no-ns0 guarantee).
	root = _reroot_with_nsmap(root)
	if material_signature is not None:
		try:
			if material_boundary_signature(root, allow_normalizer_tokens=True) != material_signature:
				return _reject(
					input_path, output_path,
					code="MATERIAL_BOUNDARY_LOST",
					message="Normalization changed a material semantic boundary.",
					fix="Keep semantic groups, their order, and liquid anchors intact.",
				)
		except MaterialSvgValidationError as exc:
			return _reject(
				input_path, output_path,
				code="MATERIAL_SEMANTIC_INVALID",
				message=str(exc),
				fix="Repair the material semantic contract after normalization.",
			)
		remove_normalizer_boundary_tokens(root)

	# S1 reference-integrity hard gate: runs AFTER every rewrite (ASCII rename,
	# F8 style rewrite, transform flatten, shape->path, cruft removal) and BEFORE
	# the final write. Any dangling internal url(#id)/href="#id" reference rejects
	# the file with UNRESOLVED_REFERENCE and writes no output.
	ref_rejection = check_reference_integrity(root)
	if ref_rejection is not None:
		return NormalizeResult(
			input_path=input_path,
			output_path=output_path,
			rejection=ref_rejection,
			output_written=False,
		)

	# Serialize to canonical bytes (S4). Build the final text only after this
	# point so a failure above never writes partial output.
	body = serialize_canonical(root).decode("utf-8")
	# Re-inject any pre-root comments stripped by the parser so attribution lines
	# like `<!-- Created by Author, CC-BY-3.0 -->` survive normalization.
	if pre_root_comments:
		svg_index = body.find("<svg")
		if svg_index >= 0:
			preamble = body[:svg_index]
			rest = body[svg_index:]
			comment_block = "\n".join(pre_root_comments) + "\n"
			body = preamble + comment_block + rest

	# All gates passed: write the normalized output exactly once.
	output_path.parent.mkdir(parents=True, exist_ok=True)
	output_path.write_text(body, encoding="utf-8")

	result = NormalizeResult(
		input_path=input_path,
		output_path=output_path,
		rejection=None,
		bbox=bbox,
		view_box=view_box,
		output_written=True,
	)
	return result


#============================================
# Floor-shadow removal.
#
# Detection: a path element is a floor-shadow CANDIDATE when ALL three criteria hold:
#   1. Wide-flat: its own bbox width/height > _SHADOW_ASPECT_THRESHOLD.
#   2. Bottom-band: its own bbox center_y falls in the lowest _SHADOW_BAND_FRAC
#      of the overall drawing bbox (i.e. center_y > overall_bbox.min_y +
#      (1 - _SHADOW_BAND_FRAC) * overall_bbox.height).
#   3. Shadow signal: AT LEAST ONE of:
#      a. Resolved fill-opacity < _SHADOW_OPACITY_THRESHOLD (inline style or
#         presentation attribute; inline wins).
#      b. Desaturated near-grey fill: an #rrggbb or #rgb hex fill where each
#         channel is approximately equal (max delta <= _SHADOW_GREY_TOLERANCE)
#         AND the value is mid/low (max channel <= _SHADOW_GREY_MAX_VALUE).
#      c. The element's id= or class= attribute contains the substring "shadow"
#         (case-insensitive); this also catches inkscape:pageshadow if it were
#         not already removed by B1.
#   Blur filter alone is NOT sufficient (filters are rejected by the classifier
#   before D1 can run; D1 is therefore never called when a filter is present).
#   If the fill-opacity or fill signal would require reading a <style> class rule
#   (i.e. the property is absent from inline style and presentation attribute),
#   treat it as "no signal" from that sub-criterion -- do NOT guess.
#
# By this stage all shapes are <path>; detection uses
# _element_geometry_bbox (pure geometry, no stroke pad) to avoid double-counting.
#============================================

# Shadow-detection thresholds (not CLI-tunable; plan A4 minimalism).
_SHADOW_ASPECT_THRESHOLD = 3.0   # width/height > this -> wide-flat
_SHADOW_BAND_FRAC = 0.20          # center_y must be in lowest 20% of overall height
_SHADOW_OPACITY_THRESHOLD = 0.5  # fill-opacity < this -> shadow signal
_SHADOW_GREY_TOLERANCE = 30       # max per-channel delta for near-grey (0-255 range)
_SHADOW_GREY_MAX_VALUE = 180      # max channel value for "mid/low" grey (0-255 range)

# Hex colour patterns for fill detection (#rrggbb or #rgb).
_HEX_RGB_FULL = re.compile(r"^#([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})$")
_HEX_RGB_SHORT = re.compile(r"^#([0-9a-fA-F])([0-9a-fA-F])([0-9a-fA-F])$")


#============================================
def _fill_is_desaturated_grey(fill_value: str) -> bool:
	"""Return True when a hex fill colour is a desaturated near-grey at mid/low value.

	Matches both 6-hex (#rrggbb) and 3-hex (#rgb) formats.  The grey test is:
	  - Max channel minus min channel <= _SHADOW_GREY_TOLERANCE (approx equal RGB).
	  - Max channel value <= _SHADOW_GREY_MAX_VALUE (mid/low, not near-white).

	Only hex colours are tested; named colours ("grey", "silver", etc.) are NOT
	parsed here to keep the inline-only-cascade contract (no guessing).

	Args:
		fill_value: The raw fill attribute value string.

	Returns:
		True when the colour is a desaturated mid-to-low grey.
	"""
	fill_value = fill_value.strip()
	m6 = _HEX_RGB_FULL.match(fill_value)
	if m6:
		r = int(m6.group(1), 16)
		g = int(m6.group(2), 16)
		b = int(m6.group(3), 16)
	else:
		m3 = _HEX_RGB_SHORT.match(fill_value)
		if not m3:
			# Not a parseable hex colour; no signal.
			return False
		# Expand 3-hex to 6-hex: #rgb -> #rrggbb.
		r = int(m3.group(1) * 2, 16)
		g = int(m3.group(2) * 2, 16)
		b = int(m3.group(3) * 2, 16)
	channels = [r, g, b]
	max_ch = max(channels)
	min_ch = min(channels)
	# Both criteria must hold: near-equal channels AND mid/low luminance.
	return (max_ch - min_ch) <= _SHADOW_GREY_TOLERANCE and max_ch <= _SHADOW_GREY_MAX_VALUE


#============================================
@dataclass(frozen=True)
class ShadowCandidate:
	"""One floor-shadow candidate element detected by detect_floor_shadow_candidates.

	Attributes:
		element: The lxml element node.
		element_location: XPath-like location string (for dry-run reporting).
		element_bbox: The pure geometry bbox of the element.
		signal: A short string naming which shadow signal matched ("fill_opacity",
			"grey_fill", or "id_class").
	"""
	element: lxml.etree._Element
	element_location: str
	element_bbox: BBox
	signal: str


#============================================
def detect_floor_shadow_candidates(
	root: lxml.etree._Element,
	overall_bbox: BBox,
) -> list[ShadowCandidate]:
	"""Detect floor-shadow candidates from the element set given the overall bbox.

	This is the D1 pure detection function.  It reads only inline style and
	presentation attributes (inline-only cascade); if a needed signal would require
	a <style> class rule, that sub-criterion is treated as no signal.  Blur filter
	alone is never a signal (filters are already rejected by the classifier).

	By this stage all shapes are <path>, so element geometry is
	available from _element_geometry_bbox.

	A candidate satisfies ALL three criteria:
	  1. Wide-flat: element_bbox.width / element_bbox.height > _SHADOW_ASPECT_THRESHOLD.
	  2. Bottom-band: element_bbox center_y > overall_bbox.min_y +
	     (1 - _SHADOW_BAND_FRAC) * overall_bbox.height.
	  3. Shadow signal (at least one of):
	     a. Resolved fill-opacity < _SHADOW_OPACITY_THRESHOLD.
	     b. Resolved fill is a desaturated near-grey hex colour.
	     c. id= or class= contains the substring "shadow" (case-insensitive).

	Args:
		root: The parsed SVG root element (after classify, flatten, and shape->path).
		overall_bbox: The overall drawing bbox (computed BEFORE any removal).

	Returns:
		Ordered list of ShadowCandidate records (document order); empty when none.
	"""
	candidates: list[ShadowCandidate] = []
	# The overall drawing height must be positive for the band calculation.
	overall_height = overall_bbox.height
	if overall_height <= 0.0:
		return candidates
	# Bottom-band threshold: center_y must exceed this y value.
	band_threshold_y = overall_bbox.min_y + (1.0 - _SHADOW_BAND_FRAC) * overall_height

	for elem in root.iter():
		if not isinstance(elem.tag, str):
			continue
		tag = local_name(elem.tag)
		if tag != "path":
			# All geometry is <path> at this stage; skip non-path nodes.
			continue
		# Criterion 1: compute element geometry bbox (no stroke pad).
		elem_geom = _element_geometry_bbox(elem)
		if elem_geom is None or isinstance(elem_geom, str):
			# No bbox or UNIT_SENTINEL -> skip.
			continue
		elem_h = elem_geom.height
		if elem_h <= 0.0:
			# Zero-height element: cannot compute a meaningful aspect ratio.
			continue
		# Criterion 1: wide-flat check.
		aspect = elem_geom.width / elem_h
		if aspect <= _SHADOW_ASPECT_THRESHOLD:
			continue
		# Criterion 2: bottom-band check.
		center_y = (elem_geom.min_y + elem_geom.max_y) / 2.0
		if center_y <= band_threshold_y:
			continue
		# Criterion 3: shadow signal (inline-only cascade; no class/stylesheet guessing).
		location = elem.getroottree().getpath(elem)
		signal = _shadow_signal(elem)
		if signal is None:
			continue
		candidates.append(ShadowCandidate(
			element=elem,
			element_location=location,
			element_bbox=elem_geom,
			signal=signal,
		))
	return candidates


#============================================
def _shadow_signal(elem: lxml.etree._Element) -> str | None:
	"""Return the matched shadow signal name for an element, or None.

	Checks in this order: fill-opacity sub-criterion (a), then grey fill (b),
	then id/class substring (c).  Returns the FIRST matching signal name so
	the caller can report which signal caused the match.

	Only inline style and presentation attributes are read (no class/stylesheet).

	Args:
		elem: The SVG path element to test.

	Returns:
		"fill_opacity", "grey_fill", "id_class", or None.
	"""
	# Sub-criterion (a): resolved fill-opacity < threshold.
	fill_opacity_str = _resolved_property(elem, "fill-opacity")
	if fill_opacity_str is not None:
		fill_opacity = parse_float(fill_opacity_str, default=1.0)
		if fill_opacity < _SHADOW_OPACITY_THRESHOLD:
			return "fill_opacity"

	# Sub-criterion (b): desaturated near-grey hex fill.
	fill_str = _resolved_property(elem, "fill")
	if fill_str is not None and _fill_is_desaturated_grey(fill_str):
		return "grey_fill"

	# Sub-criterion (c): id or class contains "shadow" (case-insensitive).
	id_val = elem.get("id") or ""
	class_val = elem.get("class") or ""
	if "shadow" in id_val.lower() or "shadow" in class_val.lower():
		return "id_class"

	return None


#============================================
def remove_floor_shadow_elements(
	root: lxml.etree._Element,
	candidates: list[ShadowCandidate],
) -> int:
	"""Remove the detected floor-shadow candidate elements from the tree.

	Modifies root in place by detaching each candidate element.  Returns the
	number of elements actually removed.  If a candidate's parent is None
	(already detached), it is silently skipped.

	Args:
		root: The parsed SVG root element.
		candidates: List of ShadowCandidate records from detect_floor_shadow_candidates.

	Returns:
		Number of elements removed.
	"""
	removed = 0
	for candidate in candidates:
		parent = candidate.element.getparent()
		if parent is not None:
			parent.remove(candidate.element)
			removed += 1
	return removed


#============================================
def output_path_for(input_path: Path, output_dir: Path | None, suffix: str, in_place: bool) -> Path:
	if in_place:
		return input_path
	if output_dir is not None:
		return output_dir / input_path.name
	return input_path.with_name(f"{input_path.stem}{suffix}{input_path.suffix}")


#============================================
def _shadow_dry_run_report(input_path: Path) -> None:
	"""Run the D1 dry-run for one file: detect shadow candidates and print a report.

	Parses, classifies, flattens, converts shapes to paths, and removes editor
	cruft (same setup as normalize_svg_file up to B1), then computes the
	pre-removal overall bbox and runs detect_floor_shadow_candidates.  Does NOT
	delete elements, does NOT write output.

	Prints a human-readable report to stdout per candidate:
	  SHADOW-CANDIDATE: <path> | bbox=... | signal=... | crop_delta=...
	If the file is malformed or would be rejected, prints a short SHADOW-SKIP line.

	Args:
		input_path: Path to the SVG file to inspect.
	"""
	try:
		source_text = input_path.read_text(encoding="utf-8")
	except (UnicodeDecodeError, OSError) as exc:
		print(f"SHADOW-SKIP: {input_path} (read error: {exc})")
		return
	if detect_doctype_or_entity(source_text) is not None:
		print(f"SHADOW-SKIP: {input_path} (DOCTYPE/ENTITY)")
		return
	try:
		tree = parse_svg(input_path)
	except lxml.etree.XMLSyntaxError as exc:
		print(f"SHADOW-SKIP: {input_path} (parse error: {exc})")
		return
	root = tree.getroot()
	if classify(root) is not None:
		print(f"SHADOW-SKIP: {input_path} (would be rejected by classifier)")
		return
	make_ascii_clean(root)
	try:
		flatten_transforms(root)
		convert_shapes_to_paths(root)
	except (UnsupportedTransformError, NonScalingStrokeError, UnsupportedUnitError) as exc:
		print(f"SHADOW-SKIP: {input_path} (prep error: {exc})")
		return
	remove_editor_cruft(root)
	try:
		pre_bbox = compute_bbox(root)
	except (UnsupportedUnitError, ValueError) as exc:
		print(f"SHADOW-SKIP: {input_path} (no geometry: {exc})")
		return
	candidates = detect_floor_shadow_candidates(root, pre_bbox)
	if not candidates:
		print(f"SHADOW-NONE: {input_path} (no floor-shadow candidates detected)")
		return
	for cand in candidates:
		# Estimate crop delta: how much the viewBox would shrink if this element
		# were removed.  We do NOT actually remove; we approximate by checking
		# how much the overall bbox shrinks when this element is excluded.
		# A simple conservative estimate: the bbox contributed by this element.
		elem_b = cand.element_bbox
		crop_delta_str = (
			f"w_shrink_up_to={fmt(elem_b.width):.3f} "
			f"h_shrink_up_to={fmt(elem_b.height):.3f}"
		)
		print(
			f"SHADOW-CANDIDATE: {input_path} | "
			f"xpath={cand.element_location} | "
			f"bbox=({fmt(elem_b.min_x)},{fmt(elem_b.min_y)},{fmt(elem_b.max_x)},{fmt(elem_b.max_y)}) | "
			f"signal={cand.signal} | "
			f"crop_delta=({crop_delta_str})"
		)


#============================================
def path_data_list(svg_path: Path) -> list[str]:
	root = lxml.etree.parse(str(svg_path)).getroot()
	data: list[str] = []
	for elem in root.iter():
		if isinstance(elem.tag, str) and local_name(elem.tag) == "path" and elem.get("d"):
			data.append(elem.get("d"))
	return data


#============================================
def check_no_relative_hvz(svg_path: Path) -> None:
	"""Raise if any output path still contains relative h/v/z commands.

	Args:
		svg_path: Path to a normalized SVG.

	Raises:
		ValueError: When lowercase h/v/z survive in any path d attribute.
	"""
	bad: list[str] = []
	for d_attr in path_data_list(svg_path):
		found = re.findall(r"[hvz]", d_attr)
		if found:
			bad.append(d_attr)
	if bad:
		raise ValueError(f"Output still contains lowercase h/v/z in {svg_path}: {bad[:2]}")


#============================================
def write_svg(path: Path, body: str, view_box: str = "0 0 100 100") -> None:
	path.write_text(f'<svg xmlns="{SVG_NS}" viewBox="{view_box}">\n{body}\n</svg>\n', encoding="utf-8")


METADATA_FIXTURE = '''<?xml version="1.0" encoding="UTF-8"?>
<!-- Created by Test Author, CC-BY-3.0 -->
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:dc="http://purl.org/dc/elements/1.1/"
     xmlns:cc="http://creativecommons.org/ns#"
     xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
     viewBox="0 0 100 100">
  <metadata>
    <rdf:RDF>
      <cc:Work rdf:about="">
        <dc:title>Test Asset</dc:title>
        <dc:creator><cc:Agent><dc:title>Test Author</dc:title></cc:Agent></dc:creator>
        <cc:license rdf:resource="https://creativecommons.org/licenses/by/3.0/"/>
        <dc:source>https://bioicons.com/</dc:source>
      </cc:Work>
    </rdf:RDF>
  </metadata>
  <title>Test Asset</title>
  <desc>Centrifuge icon by Test Author</desc>
  <rect x="10" y="10" width="80" height="80" fill="#333"/>
</svg>
'''


#============================================
def run_self_test() -> int:
	"""Run built-in fixture tests covering geometry parity and S4 serialization.

	Returns:
		0 on success, 1 on any failure (temp dir kept for inspection).
	"""
	temp_dir = Path(tempfile.mkdtemp(prefix="normalize-svg-v3-self-test-"))
	failures: list[str] = []
	fixtures = [
		("relative_hvz_rectangle.svg", '<path d="M 10 20 h 30 v 40 h -30 z" fill="#000" />', "0 0 34 44"),
		("relative_hvz_two_subpaths.svg", '<path d="M 10 20 h 30 v 10 z m 50 50 h 5 v 5 z" fill="#000" />', "0 0 59 59"),
		("mixed_absolute_relative.svg", '<path d="M 5 5 L 15 5 h 10 V 30 v 5 z" fill="#000" />', "0 0 24 34"),
		("gradient_ref.svg", '<defs><linearGradient id="a"><stop offset="0" stop-color="#000"/></linearGradient></defs><path fill="url(#a)" d="M 5 5 h 10 v 10 z" />', "0 0 14 14"),
		("relative_curves.svg", '<path d="M 10 10 c 5 0 5 10 10 10 q 5 5 10 0 s 4 4 8 0 t 8 0 z" fill="#000" />', None),
	]
	for name, body, expected_viewbox in fixtures:
		input_path = temp_dir / name
		output_path = temp_dir / f"{Path(name).stem}.normalized.svg"
		write_svg(input_path, body)
		result = normalize_svg_file(input_path, output_path, padding=2.0)
		if not result.normalized:
			failures.append(f"{name}: unexpectedly rejected ({result.rejection})")
			continue
		# Output must reparse and contain no relative h/v/z.
		lxml.etree.parse(str(output_path))
		try:
			check_no_relative_hvz(output_path)
		except ValueError as exc:
			failures.append(f"{name}: {exc}")
			continue
		if expected_viewbox is not None and result.view_box != expected_viewbox:
			failures.append(f"{name}: expected viewBox {expected_viewbox}, got {result.view_box}")

	# Attribution metadata preservation: dc:/cc:/rdf: prefixes must survive
	# round-trip (not be renamed to ns0:/ns1:/...). Top-of-file XML comments
	# and <title>/<desc> must also survive.
	meta_in = temp_dir / "attribution_metadata.svg"
	meta_out = temp_dir / "attribution_metadata.normalized.svg"
	meta_in.write_text(METADATA_FIXTURE, encoding="utf-8")
	meta_result = normalize_svg_file(meta_in, meta_out, padding=2.0)
	if not meta_result.normalized:
		failures.append(f"attribution_metadata.svg: unexpectedly rejected ({meta_result.rejection})")
	else:
		content = meta_out.read_text(encoding="utf-8")
		required = [
			("dc:creator", "<dc:creator"),
			("dc:title", "<dc:title"),
			("cc:license", "<cc:license"),
			("cc:Work", "<cc:Work"),
			("rdf:RDF", "<rdf:RDF"),
			("top XML comment", "Test Author, CC-BY-3.0"),
			("<title>", "<title>"),
			("<desc>", "<desc>"),
		]
		for label, needle in required:
			if needle not in content:
				failures.append(f"attribution_metadata.svg: metadata lost ({label} missing)")
		forbidden_prefixes = ("ns0:", "ns1:", "ns2:", "ns3:")
		for prefix in forbidden_prefixes:
			if prefix in content:
				failures.append(f"attribution_metadata.svg: namespace renamed to {prefix} (S4 violation)")
		# S4: trailing newline guarantee.
		if not content.endswith("\n"):
			failures.append("attribution_metadata.svg: output missing trailing newline (S4)")

	# Parser-error rejection: a malformed file must reject with PARSER_ERROR,
	# write no output, and leave the input untouched.
	bad_in = temp_dir / "malformed.svg"
	bad_out = temp_dir / "malformed.normalized.svg"
	bad_in.write_text('<svg xmlns="http://www.w3.org/2000/svg"><rect x="1"', encoding="utf-8")
	bad_before = bad_in.read_text(encoding="utf-8")
	bad_result = normalize_svg_file(bad_in, bad_out, padding=2.0)
	if bad_result.normalized:
		failures.append("malformed.svg: expected PARSER_ERROR rejection, got normalized")
	else:
		if bad_result.rejection.code != "PARSER_ERROR":
			failures.append(f"malformed.svg: expected PARSER_ERROR, got {bad_result.rejection.code}")
		if bad_result.output_written:
			failures.append("malformed.svg: output_written True on rejection")
		if bad_out.exists():
			failures.append("malformed.svg: output file written despite rejection")
	# Input must be untouched after a rejection (in-place safety contract).
	bad_inplace = normalize_svg_file(bad_in, bad_in, padding=2.0)
	if bad_inplace.normalized:
		failures.append("malformed.svg (in-place): expected rejection")
	if bad_in.read_text(encoding="utf-8") != bad_before:
		failures.append("malformed.svg: input mutated on in-place rejection")

	if failures:
		print("SELF-TEST FAILED")
		for failure in failures:
			print(f"FAIL: {failure}")
		print(f"Temp dir kept for inspection: {temp_dir}")
		return 1
	print("SELF-TEST PASSED")
	shutil.rmtree(temp_dir)
	return 0


#============================================
def parse_args() -> argparse.Namespace:
	"""Parse command-line arguments."""
	parser = argparse.ArgumentParser(
		description="SVG normalizer v3 (lxml core): normalize-or-reject ingestion gate.",
		formatter_class=argparse.RawDescriptionHelpFormatter,
		epilog=(
			"Examples:\n"
			"  python3 tools/normalize_svg_v3.py -i microtube.svg\n"
			"  python3 tools/normalize_svg_v3.py -i microtube.svg -o normalized/\n"
			"  python3 tools/normalize_svg_v3.py --self-test\n"
		),
	)
	# Value flags: -i/--input, -o/--output-dir, -p/--padding each have both short
	# and long forms.  Action flags (--in-place, --self-test) have no natural
	# single-letter abbreviation and stay long-form only.
	parser.add_argument("-i", "--input", dest="input", action="append", default=[], help="SVG input file. May be repeated.")
	parser.add_argument("-o", "--output-dir", dest="output_dir", type=Path, default=None, help="Directory for normalized SVGs.")
	parser.add_argument("--in-place", dest="in_place", action="store_true", help="Overwrite input SVG files in place.")
	# --suffix removed: output suffix is hardcoded as '.normalized' (PYTHON_STYLE argparse minimalism).
	parser.add_argument("-p", "--padding", dest="padding", type=float, default=2.0, help="Padding around content in user units. Default: 2")
	parser.add_argument("--self-test", dest="self_test", action="store_true", help="Run built-in fixture tests.")
	parser.add_argument("-r", "--report-json", dest="report_json", type=Path, default=None, help="Write a JSON report of the run to this path.")
	# D1 flags (distinct jobs; both default off; no-op when absent).
	parser.add_argument(
		"--remove-floor-shadow", dest="remove_floor_shadow", action="store_true",
		help=(
			"Remove detected floor-shadow elements before the bbox crop "
			"(D1, off by default). Tightens the viewBox to the real object."
		),
	)
	parser.add_argument(
		"--shadow-dry-run", dest="shadow_dry_run", action="store_true",
		help=(
			"Report floor-shadow candidates (id/xpath, bbox, signal, crop delta) "
			"without deleting them and without writing output (D1 dry-run)."
		),
	)
	return parser.parse_args()


#============================================
def main() -> int:
	args = parse_args()
	if args.self_test or not args.input:
		code = run_self_test()
		if code != 0 or not args.input:
			return code

	if args.output_dir is not None and args.in_place:
		print("ERROR: use either --output-dir or --in-place, not both", file=sys.stderr)
		return 2

	failed = False
	# Collect per-file records for --report-json output.
	report_records: list[dict] = []
	for input_text in args.input:
		input_path = Path(input_text)
		if not input_path.exists():
			print(f"ERROR: input not found: {input_path}", file=sys.stderr)
			failed = True
			continue
		if input_path.suffix.lower() != ".svg":
			print(f"ERROR: input is not an SVG: {input_path}", file=sys.stderr)
			failed = True
			continue
		out_path = output_path_for(input_path, args.output_dir, ".normalized", args.in_place)

		# --shadow-dry-run: report candidates without deleting or writing output.
		if args.shadow_dry_run:
			_shadow_dry_run_report(input_path)
			continue

		result = normalize_svg_file(
			input_path, out_path,
			padding=args.padding,
			remove_floor_shadow=args.remove_floor_shadow,
		)
		if not result.normalized:
			reason = result.rejection
			# Rejection: report the stable code, message, fix, and location; the
			# CLI exits non-zero. No output was written; input is untouched.
			print(
				f"REJECT: {input_path} | {reason.code}: {reason.message} | "
				f"fix: {reason.fix}"
				+ (f" | at: {reason.element}" if reason.element else ""),
				file=sys.stderr,
			)
			failed = True
		else:
			# Normalized: confirm the no-relative-hvz output invariant before claiming OK.
			check_no_relative_hvz(out_path)
			bbox = result.bbox
			print(
				f"OK: {input_path} -> {out_path} | "
				f"bbox=({fmt(bbox.min_x)}, {fmt(bbox.min_y)}, {fmt(bbox.max_x)}, {fmt(bbox.max_y)}) | "
				f"viewBox={result.view_box}"
			)
		# Build a per-file record for the JSON report.
		if args.report_json is not None:
			rejection = result.rejection
			record: dict = {
				"file": str(input_path),
				"verdict": "normalized" if result.normalized else "rejected",
				"primary_reason_code": rejection.code if rejection else None,
				"message": rejection.message if rejection else None,
				"fix": rejection.fix if rejection else None,
				"element": rejection.element if rejection else None,
				"secondary_reason_codes": list(result.secondary_reason_codes),
				"features_seen": [],
				"refs_checked": False,
				"output_written": result.output_written,
			}
			report_records.append(record)

	# Write the JSON report when --report-json was requested.
	if args.report_json is not None:
		args.report_json.parent.mkdir(parents=True, exist_ok=True)
		report_text = json.dumps(report_records, indent=2)
		args.report_json.write_text(report_text, encoding="utf-8")

	return 1 if failed else 0


if __name__ == "__main__":
	raise SystemExit(main())
