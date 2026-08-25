"""Coordinate safe SVG normalization from parsed source to canonical output."""

import pathlib

import lxml.etree

import validation.svg.layer_recipe_validator
import tools.svg_normalizer.clips
import tools.svg_normalizer.document
import tools.svg_normalizer.geometry
import tools.svg_normalizer.model
import tools.svg_normalizer.sanitization
import tools.svg_normalizer.shadows
import tools.svg_normalizer.transform_geometry
import tools.svg_normalizer.transform_tree


def normalize_svg_file(
	input_path: pathlib.Path,
	output_path: pathlib.Path,
	padding: float = 2.0,
	remove_floor_shadow: bool = False,
) -> tools.svg_normalizer.model.NormalizeResult:
	"""Normalize an SVG, or reject it; the single public entry point.

	Pipeline: parse once (no recover) -> tools.svg_normalizer.document.classify ->
	ASCII-clean ids -> flatten transforms (A1) -> shape->path (A2) ->
	B1 editor-cruft removal -> [D1 floor-shadow removal when enabled] ->
	compute bbox -> ordinary: shift to origin/rewrite viewBox; material: retain
	authored root frame -> canonical serialize
	(S4) -> write output.

	D1 (floor-shadow removal) runs BEFORE tools.svg_normalizer.geometry.compute_bbox so the single crop
	tightens around the real object.  It is gated by remove_floor_shadow; with
	that False (the default) the normal output path is unchanged.

	On rejection no output is written and the input is left untouched, even when
	output_path equals input_path (the --in-place case): the write only happens
	after every gate passes.

	Args:
		input_path: pathlib.Path to source SVG.
		output_path: pathlib.Path to write the normalized SVG.
		padding: Padding around drawn content, in user units. Default 2.
		remove_floor_shadow: When True, detect and remove floor-shadow elements
			before the bbox pass (D1).  Default False (no-op for gate verdict).

	Returns:
		A tools.svg_normalizer.model.NormalizeResult: normalized (rejection is None, output_written True) or
		rejected (rejection set, output_written False, no file written).
	"""
	try:
		source_text = input_path.read_text(encoding="utf-8")
	except UnicodeDecodeError as exc:
		# Non-UTF-8 files are rejected as PARSER_ERROR: v3 requires UTF-8 (S4).
		return tools.svg_normalizer.document._reject(
			input_path, output_path,
			code="PARSER_ERROR",
			message=f"SVG is not valid UTF-8: {exc}",
			fix="Re-save the SVG as UTF-8 before ingestion.",
		)
	pre_root_comments = tools.svg_normalizer.document.extract_pre_root_comments(source_text)

	# Check raw text for DOCTYPE and entities before parsing. tools.svg_normalizer.document.parse_svg uses
	# resolve_entities=False so a DOCTYPE may parse without error; we reject it
	# explicitly here so the gate is cheap and correct.
	doctype_rejection = tools.svg_normalizer.sanitization.detect_doctype_or_entity(source_text)
	if doctype_rejection is not None:
		return tools.svg_normalizer.model.NormalizeResult(
			input_path=input_path,
			output_path=output_path,
			rejection=doctype_rejection,
			output_written=False,
		)

	# Parse once without recovery. A parse failure is a hard reject; never
	# normalize recovered XML.
	try:
		tree = tools.svg_normalizer.document.parse_svg(input_path)
	except lxml.etree.XMLSyntaxError as exc:
		return tools.svg_normalizer.document._reject(
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
		is_material = validation.svg.layer_recipe_validator.validate_reserved_attributes(root)
		if is_material:
			validation.svg.layer_recipe_validator.inject_normalizer_boundary_tokens(root)
			material_signature = validation.svg.layer_recipe_validator.material_boundary_signature(root, allow_normalizer_tokens=True)
		else:
			material_signature = None
	except validation.svg.layer_recipe_validator.MaterialSvgValidationError as exc:
		return tools.svg_normalizer.document._reject(
			input_path, output_path,
			code="MATERIAL_SEMANTIC_INVALID",
			message=str(exc),
			fix="Repair the closed data-vlab material layer contract before normalization.",
		)

	# Feature classification returns one stable rejection reason when needed.
	# non-None result short-circuits to a rejection before any geometry edit.
	rejection = tools.svg_normalizer.document.classify(root)
	if rejection is not None:
		return tools.svg_normalizer.model.NormalizeResult(
			input_path=input_path,
			output_path=output_path,
			rejection=rejection,
			output_written=False,
		)

	# Rename non-ASCII id/data-name values to ASCII and update in-file references.
	tools.svg_normalizer.sanitization.make_ascii_clean(root)

	# Flatten element/group transforms into absolute root-coordinate geometry
	# (A1) BEFORE bbox computation, so the bbox is measured on final coordinates
	# and the canonical invariant (no geometry transform remaining) holds. A
	# transform v3 cannot safely apply -> rejection (no output written).
	try:
		tools.svg_normalizer.transform_tree.flatten_transforms(root)
	except tools.svg_normalizer.transform_geometry.UnsupportedTransformError as exc:
		return tools.svg_normalizer.document._reject(
			input_path, output_path,
			code="UNSUPPORTED_TRANSFORM",
			message=f"A transform could not be safely flattened. ({exc})",
			fix=(
				"Pre-flatten the transform or ungroup transformed groups in the "
				"source editor before ingestion."
			),
			element=exc.element_location,
		)
	except tools.svg_normalizer.transform_geometry.NonScalingStrokeError as exc:
		return tools.svg_normalizer.document._reject(
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
	except tools.svg_normalizer.model.UnsupportedUnitError as exc:
		return tools.svg_normalizer.document._reject(
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
	# carried a transform were rewritten by tools.svg_normalizer.transform_tree.flatten_transforms above; this pass
	# covers transform-free shapes and ensures the output is path-only for all
	# supported geometry.  Runs after flattening so geometry is in root coords.
	try:
		tools.svg_normalizer.geometry.convert_shapes_to_paths(root)
	except tools.svg_normalizer.model.UnsupportedUnitError as exc:
		return tools.svg_normalizer.document._reject(
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
	# geometry) and BEFORE tools.svg_normalizer.geometry.compute_bbox/S1 (so the bbox is measured on the clipped
	# region and S1 never sees the dropped clip ref). A clip outside the simple
	# allowlist -> CLIPPATH_UNSUPPORTED_COMPLEX rejection (no output written).
	try:
		# The material clip is compiler-owned: authored semantic groups never
		# carry clip-path, while anchor_liquid_clip remains in defs for the derived
		# compiled gravity-part region. Generic clips on ordinary nested artwork still use
		# the shared supported flattening behavior.
		tools.svg_normalizer.clips.flatten_clip_paths(root)
	except tools.svg_normalizer.transform_geometry.ComplexClipError as exc:
		return tools.svg_normalizer.document._reject(
			input_path, output_path,
			code="CLIPPATH_UNSUPPORTED_COMPLEX",
			message=f"A clipPath could not be flattened. ({exc.detail})",
			fix=(
				"Apply the clip in your editor (flatten to the clipped path), or "
				"simplify it to a single filled clip shape, before ingestion."
			),
			element=exc.element_location,
		)

	# B1: remove known editor-namespace cruft before the bbox
	# pass. This is a positive allowlist: only editor-namespace elements and
	# attributes are removed; every SVG render attr, def, id, and dc/cc/rdf
	# attribution is preserved. Cruft removal never changes the verdict; it only
	# cleans non-portable editor state.
	tools.svg_normalizer.document.remove_editor_cruft(root)

	# Floor-shadow removal runs before tools.svg_normalizer.geometry.compute_bbox so the single
	# crop tightens around the real object after shadow removal.  A preliminary
	# bbox pass is needed to identify the bottom-band threshold; this is a cheap
	# pass over the already-prepared geometry.  Removal does NOT affect the gate
	# verdict -- if removing a shadow breaks ref integrity or leaves no geometry,
	# the file is rejected like any other (handled below).
	if remove_floor_shadow and not is_material:
		try:
			pre_bbox = tools.svg_normalizer.geometry.compute_bbox(root)
		except (tools.svg_normalizer.model.UnsupportedUnitError, ValueError):
			# No geometry or bad units -- let the real bbox pass produce the rejection.
			pre_bbox = None
		if pre_bbox is not None:
			shadow_candidates = tools.svg_normalizer.shadows.detect_floor_shadow_candidates(root, pre_bbox)
			if shadow_candidates:
				tools.svg_normalizer.shadows.remove_floor_shadow_elements(root, shadow_candidates)

	# Compute the drawn bbox. No drawable geometry is an EMPTY_GEOMETRY reject;
	# a non-user unit on a required size attr is an UNSUPPORTED_UNIT reject.
	# Neither writes output.
	try:
		bbox = tools.svg_normalizer.geometry.compute_bbox(root)
	except tools.svg_normalizer.model.UnsupportedUnitError as exc:
		return tools.svg_normalizer.document._reject(
			input_path, output_path,
			code="UNSUPPORTED_UNIT",
			message=(
				"A required size attribute uses a non-user unit (%, mm, cm, in, pt, pc, em, ex). "
				f"({exc})"
			),
			fix=(
				"Convert all geometry to user units (unitless or px) in the source "
				"editor before ingestion, then export or save."
			),
			element=exc.element_location,
		)
	except ValueError as exc:
		return tools.svg_normalizer.document._reject(
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
				tools.svg_normalizer.geometry.shift_element(elem, dx, dy)
		# Use fmt_precise for the viewBox and width/height attrs (A4 precision).
		root.set("viewBox", f"0 0 {tools.svg_normalizer.model.fmt_precise(new_width)} {tools.svg_normalizer.model.fmt_precise(new_height)}")
		# Width/height attrs often disagree with viewBox after cropping. Keep them in
		# sync if present.
		if root.get("width") is not None:
			root.set("width", tools.svg_normalizer.model.fmt_precise(new_width))
		if root.get("height") is not None:
			root.set("height", tools.svg_normalizer.model.fmt_precise(new_height))
		view_box = root.get("viewBox")

	# Rebuild the root under a canonical nsmap when new prefixes are needed so
	# attribution prefixes serialize as dc:/cc:/rdf: (S4 no-ns0 guarantee).
	root = tools.svg_normalizer.document._reroot_with_nsmap(root)
	if material_signature is not None:
		try:
			if validation.svg.layer_recipe_validator.material_boundary_signature(root, allow_normalizer_tokens=True) != material_signature:
				return tools.svg_normalizer.document._reject(
					input_path, output_path,
					code="MATERIAL_BOUNDARY_LOST",
					message="Normalization changed a material semantic boundary.",
					fix="Keep semantic groups, their order, and liquid anchors intact.",
				)
		except validation.svg.layer_recipe_validator.MaterialSvgValidationError as exc:
			return tools.svg_normalizer.document._reject(
				input_path, output_path,
				code="MATERIAL_SEMANTIC_INVALID",
				message=str(exc),
				fix="Repair the material semantic contract after normalization.",
			)
		validation.svg.layer_recipe_validator.remove_normalizer_boundary_tokens(root)

	# S1 reference-integrity hard gate: runs AFTER every rewrite (ASCII rename,
	# F8 style rewrite, transform flatten, shape->path, cruft removal) and BEFORE
	# the final write. Any dangling internal url(#id)/href="#id" reference rejects
	# the file with UNRESOLVED_REFERENCE and writes no output.
	ref_rejection = tools.svg_normalizer.document.check_reference_integrity(root)
	if ref_rejection is not None:
		return tools.svg_normalizer.model.NormalizeResult(
			input_path=input_path,
			output_path=output_path,
			rejection=ref_rejection,
			output_written=False,
		)

	# Serialize to canonical bytes (S4). Build the final text only after this
	# point so a failure above never writes partial output.
	body = tools.svg_normalizer.document.serialize_canonical(root).decode("utf-8")
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

	result = tools.svg_normalizer.model.NormalizeResult(
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
#         (case-insensitive); editor-specific page shadows are already removed
#         by B1.
#   Blur filter alone is NOT sufficient (filters are rejected by the classifier
#   before D1 can run; D1 is therefore never called when a filter is present).
#   If the fill-opacity or fill signal would require reading a <style> class rule
#   (i.e. the property is absent from inline style and presentation attribute),
#   treat it as "no signal" from that sub-criterion -- do NOT guess.
#
# By this stage all shapes are <path>; detection uses
# _element_geometry_bbox (pure geometry, no stroke pad) to avoid double-counting.
#============================================
