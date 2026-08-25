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
dc/cc/rdf/xlink attribution namespace prefixes, preserve pre-root comments,
in-root comments, <title>, and <desc>.

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

import collections.abc
import dataclasses
import decimal
import math
import pathlib
import re

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

# Stable rejection reason tokens emitted by the feature detectors. Detectors
# report only these tokens so reports, tests, and future automation share one
# vocabulary. Sourced from the plan's Rejection reason schema.
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
@dataclasses.dataclass(frozen=True)
class PathSegment:
	cmd: str
	nums: tuple[float, ...]


#============================================
@dataclasses.dataclass(frozen=True)
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
@dataclasses.dataclass(frozen=True)
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
@dataclasses.dataclass
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
	input_path: pathlib.Path
	output_path: pathlib.Path
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
_SCOUR_COORD_CTX = decimal.Context(prec=_COORD_PRECISION)
_SCOUR_CTRL_CTX = decimal.Context(prec=_CTRL_PRECISION)


#============================================
def fmt_precise(value: float, is_control_point: bool = False) -> str:
	"""Format a coordinate with scour-style precision: leading-zero strip,
	shortest of decimal vs scientific notation.

	Ported BY HAND from scour (Apache-2.0) scour.py scourUnitlessLength.
	Dual decimal.Decimal.decimal.Context: normal context (6 sig-figs) and control-point context
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
	# Convert to decimal.Decimal in full precision, then quantize to output precision.
	initial = decimal.getcontext().create_decimal(str(value))
	ctx = _SCOUR_CTRL_CTX if is_control_point else _SCOUR_COORD_CTX
	# ctx.plus() rounds to ctx.prec significant digits.
	length = ctx.plus(initial)
	# Remove trailing zeros: if equal to its integer value, cast to int.
	int_length = length.to_integral_value()
	if length == int_length:
		length = decimal.Decimal(int_length)
	else:
		length = length.normalize()
	# Non-scientific decimal representation; re-quantize from initial to avoid
	# rounding loss (e.g. 123.4 rounds to 123 not 120).
	nonsci = f"{length:f}"
	nonsci = f"{initial.quantize(decimal.Decimal(nonsci)):f}"
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
			raise ValueError(f"pathlib.Path data begins with number instead of command: {d_attr[:80]}")

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
def path_segments_to_d(segments: collections.abc.Iterable[PathSegment], dx: float = 0.0, dy: float = 0.0) -> str:
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
def path_bbox_from_segments(segments: collections.abc.Iterable[PathSegment]) -> BBox | None:
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


def parse_points(points: str) -> list[tuple[float, float]]:
	"""Parse an SVG polyline or polygon points attribute into coordinate pairs."""
	values = [float(value) for value in re.findall(r'[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?', points)]
	return list(zip(values[::2], values[1::2]))


_USERSPACE_PAINT_TAGS = frozenset({'linearGradient', 'radialGradient', 'pattern'})


def matrix_to_transform_str(matrix: tuple[float, ...]) -> str:
	"""Serialize a six-value affine matrix for a gradient or pattern transform."""
	return 'matrix(' + ','.join(fmt_precise(component) for component in matrix) + ')'


#============================================
