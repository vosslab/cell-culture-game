"""Command-line interface and self-test support for SVG normalization."""

import argparse
import json
import pathlib
import re
import shutil
import sys
import tempfile

import lxml.etree

import tools.svg_normalizer.document
import tools.svg_normalizer.geometry
import tools.svg_normalizer.model
import tools.svg_normalizer.sanitization
import tools.svg_normalizer.shadows
import tools.svg_normalizer.transform_geometry
import tools.svg_normalizer.transform_tree
import tools.svg_normalizer.workflow


def output_path_for(input_path: pathlib.Path, output_dir: pathlib.Path | None, suffix: str, in_place: bool) -> pathlib.Path:
	"""Return the destination selected by in-place, directory, then suffix mode.

	Args:
		input_path: Source SVG path.
		output_dir: Explicit destination directory when supplied.
		suffix: Suffix inserted before the source extension in default mode.
		in_place: Whether normalization replaces the source file.

	Returns:
		The selected output path without creating its parent directory.
	"""
	if in_place:
		return input_path
	if output_dir is not None:
		return output_dir / input_path.name
	return input_path.with_name(f"{input_path.stem}{suffix}{input_path.suffix}")


#============================================
def _shadow_dry_run_report(input_path: pathlib.Path) -> None:
	"""Run the D1 dry-run for one file: detect shadow candidates and print a report.

	Parses, classifies, flattens, converts shapes to paths, and removes editor
	cruft (same setup as tools.svg_normalizer.workflow.normalize_svg_file up to B1), then computes the
	pre-removal overall bbox and runs tools.svg_normalizer.shadows.detect_floor_shadow_candidates.  Does NOT
	delete elements, does NOT write output.

	Prints a human-readable report to stdout per candidate:
	  SHADOW-CANDIDATE: <path> | bbox=... | signal=... | crop_delta=...
	If the file is malformed or would be rejected, prints a short SHADOW-SKIP line.

	Args:
		input_path: pathlib.Path to the SVG file to inspect.
	"""
	try:
		source_text = input_path.read_text(encoding="utf-8")
	except (UnicodeDecodeError, OSError) as exc:
		print(f"SHADOW-SKIP: {input_path} (read error: {exc})")
		return
	if tools.svg_normalizer.sanitization.detect_doctype_or_entity(source_text) is not None:
		print(f"SHADOW-SKIP: {input_path} (DOCTYPE/ENTITY)")
		return
	try:
		tree = tools.svg_normalizer.document.parse_svg(input_path)
	except lxml.etree.XMLSyntaxError as exc:
		print(f"SHADOW-SKIP: {input_path} (parse error: {exc})")
		return
	root = tree.getroot()
	if tools.svg_normalizer.document.classify(root) is not None:
		print(f"SHADOW-SKIP: {input_path} (would be rejected by classifier)")
		return
	tools.svg_normalizer.sanitization.make_ascii_clean(root)
	try:
		tools.svg_normalizer.transform_tree.flatten_transforms(root)
		tools.svg_normalizer.geometry.convert_shapes_to_paths(root)
	except (tools.svg_normalizer.transform_geometry.UnsupportedTransformError, tools.svg_normalizer.transform_geometry.NonScalingStrokeError, tools.svg_normalizer.model.UnsupportedUnitError) as exc:
		print(f"SHADOW-SKIP: {input_path} (prep error: {exc})")
		return
	tools.svg_normalizer.document.remove_editor_cruft(root)
	try:
		pre_bbox = tools.svg_normalizer.geometry.compute_bbox(root)
	except (tools.svg_normalizer.model.UnsupportedUnitError, ValueError) as exc:
		print(f"SHADOW-SKIP: {input_path} (no geometry: {exc})")
		return
	candidates = tools.svg_normalizer.shadows.detect_floor_shadow_candidates(root, pre_bbox)
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
			f"w_shrink_up_to={elem_b.width:.3f} "
			f"h_shrink_up_to={elem_b.height:.3f}"
		)
		print(
			f"SHADOW-CANDIDATE: {input_path} | "
			f"xpath={cand.element_location} | "
			f"bbox=({tools.svg_normalizer.model.fmt(elem_b.min_x)},{tools.svg_normalizer.model.fmt(elem_b.min_y)},{tools.svg_normalizer.model.fmt(elem_b.max_x)},{tools.svg_normalizer.model.fmt(elem_b.max_y)}) | "
			f"signal={cand.signal} | "
			f"crop_delta=({crop_delta_str})"
		)


#============================================
def path_data_list(svg_path: pathlib.Path) -> list[str]:
	"""Return every non-empty path-data attribute in an SVG document.

	Args:
		svg_path: SVG document to inspect.

	Returns:
		Path-data strings in document order.
	"""
	root = lxml.etree.parse(str(svg_path)).getroot()
	data: list[str] = []
	for elem in root.iter():
		if isinstance(elem.tag, str) and tools.svg_normalizer.model.local_name(elem.tag) == "path" and elem.get("d"):
			data.append(elem.get("d"))
	return data


#============================================
def check_no_relative_hvz(svg_path: pathlib.Path) -> None:
	"""Raise if any output path still contains relative h/v/z commands.

	Args:
		svg_path: pathlib.Path to a normalized SVG.

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
def write_svg(path: pathlib.Path, body: str, view_box: str = "0 0 100 100") -> None:
	"""Write a compact SVG fixture with body under the canonical namespace.

	Args:
		path: Destination fixture path.
		body: Raw SVG child markup.
		view_box: Root viewBox value for the fixture.
	"""
	path.write_text(f'<svg xmlns="{tools.svg_normalizer.model.SVG_NS}" viewBox="{view_box}">\n{body}\n</svg>\n', encoding="utf-8")


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
	temp_dir = pathlib.Path(tempfile.mkdtemp(prefix="normalize-svg-v3-self-test-"))
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
		output_path = temp_dir / f"{pathlib.Path(name).stem}.normalized.svg"
		write_svg(input_path, body)
		result = tools.svg_normalizer.workflow.normalize_svg_file(input_path, output_path, padding=2.0)
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
	meta_result = tools.svg_normalizer.workflow.normalize_svg_file(meta_in, meta_out, padding=2.0)
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
	bad_result = tools.svg_normalizer.workflow.normalize_svg_file(bad_in, bad_out, padding=2.0)
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
	bad_inplace = tools.svg_normalizer.workflow.normalize_svg_file(bad_in, bad_in, padding=2.0)
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
	parser.add_argument("-o", "--output-dir", dest="output_dir", type=pathlib.Path, default=None, help="Directory for normalized SVGs.")
	parser.add_argument("--in-place", dest="in_place", action="store_true", help="Overwrite input SVG files in place.")
	# --suffix removed: output suffix is hardcoded as '.normalized' (PYTHON_STYLE argparse minimalism).
	parser.add_argument("-p", "--padding", dest="padding", type=float, default=2.0, help="Padding around content in user units. Default: 2")
	parser.add_argument("--self-test", dest="self_test", action="store_true", help="Run built-in fixture tests.")
	parser.add_argument("-r", "--report-json", dest="report_json", type=pathlib.Path, default=None, help="Write a JSON report of the run to this path.")
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
		input_path = pathlib.Path(input_text)
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

		result = tools.svg_normalizer.workflow.normalize_svg_file(
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
				f"bbox=({tools.svg_normalizer.model.fmt(bbox.min_x)}, {tools.svg_normalizer.model.fmt(bbox.min_y)}, {tools.svg_normalizer.model.fmt(bbox.max_x)}, {tools.svg_normalizer.model.fmt(bbox.max_y)}) | "
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
