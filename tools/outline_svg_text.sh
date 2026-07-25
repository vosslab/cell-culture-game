#!/usr/bin/env bash
# Prepare approved intrinsic SVG markings as paths with Inkscape without changing the source by default.

set -euo pipefail

usage() {
	cat >&2 <<'EOF'
Usage:
  tools/outline_svg_text.sh INPUT.svg OUTPUT.svg
  tools/outline_svg_text.sh --in-place INPUT.svg

Use this only for approved physically intrinsic markings (for example, numbers,
units, polarity, graduations, and plate coordinates), including when preparing
a legacy or imported asset.
When an SVG contains prose identity, state, or instruction labels, remove that
prose and recreate it in layout-manager DOM or object data. This wrapper never
path-converts prose merely to pass normalization or blind-recognition assessment.

The default form refuses an existing output file. --in-place is the only form
that replaces an SVG, and it publishes a fully validated temporary file.
EOF
}

fail() {
	echo "ERROR: $*" >&2
	exit 1
}

require_svg_path() {
	local path="$1"
	if [[ "${path##*.}" != "svg" ]]; then
		fail "SVG paths must use the .svg extension: ${path}"
	fi
}

validate_svg_output() {
	local path="$1"
	local root_name
	local remaining_count
	if ! xmllint --noout "${path}"; then
		fail "Inkscape output is not valid XML: ${path}"
	fi
	root_name="$(xmllint --xpath 'local-name(/*)' "${path}")" || fail "could not inspect SVG root: ${path}"
	if [[ "${root_name}" != "svg" ]]; then
		fail "Inkscape output root is not an <svg> element: ${path}"
	fi
	remaining_count="$(xmllint --xpath 'count(//*[local-name()="text" or local-name()="tspan" or local-name()="textPath"])' "${path}")" || fail "could not inspect SVG text elements: ${path}"
	if [[ "${remaining_count}" != "0" ]]; then
		fail "Inkscape output still contains live SVG text elements: ${path}"
	fi
}

file_mode() {
	if stat --version >/dev/null 2>&1; then
		stat -c '%a' "$1"
	else
		stat -f '%Lp' "$1"
	fi
}

publish_new_output() {
	local temporary_path="$1"
	local output_path="$2"
	if ! ln "${temporary_path}" "${output_path}"; then
		fail "refusing to overwrite existing output: ${output_path}"
	fi
	rm -f "${temporary_path}"
}

repo_root="$(git rev-parse --show-toplevel)" || fail "run from a Git repository"
cd "${repo_root}"

in_place=false
case "$#" in
	1)
		if [[ "$1" == "--help" || "$1" == "-h" ]]; then
			usage
			exit 0
		fi
		usage
		exit 2
		;;
	2)
		if [[ "$1" == "--in-place" ]]; then
			in_place=true
			input_path="$2"
			output_path="$2"
		else
			input_path="$1"
			output_path="$2"
		fi
		;;
	*)
		usage
		exit 2
		;;
esac

require_svg_path "${input_path}"
require_svg_path "${output_path}"
if [[ ! -f "${input_path}" ]]; then
	fail "input SVG is not a regular file: ${input_path}"
fi
if [[ "${in_place}" == false && -e "${output_path}" ]]; then
	fail "refusing to overwrite existing output: ${output_path}"
fi

output_dir="$(dirname "${output_path}")"
if [[ ! -d "${output_dir}" ]]; then
	fail "output directory does not exist: ${output_dir}"
fi
if [[ ! -w "${output_dir}" ]]; then
	fail "output directory is not writable: ${output_dir}"
fi
if ! command -v inkscape >/dev/null 2>&1; then
	fail "This optional authoring tool requires Inkscape; install it on demand (for example: brew install --cask inkscape)."
fi
if ! command -v xmllint >/dev/null 2>&1; then
	fail "This optional authoring tool requires xmllint to validate SVG output."
fi

temporary_path="$(mktemp "${output_dir}/.$(basename "${output_path}").outline.XXXXXX.svg")"
cleanup() {
	if [[ -n "${temporary_path:-}" && -e "${temporary_path}" ]]; then
		rm -f "${temporary_path}"
	fi
}
trap cleanup EXIT INT TERM HUP
rm -f "${temporary_path}"

if ! inkscape "${input_path}" --export-type=svg --export-text-to-path --export-filename="${temporary_path}"; then
	fail "Inkscape could not outline SVG text; source remains unchanged: ${input_path}"
fi

validate_svg_output "${temporary_path}"
source_mode="$(file_mode "${input_path}")" || fail "could not read input permissions: ${input_path}"
chmod "${source_mode}" "${temporary_path}" || fail "could not preserve SVG permissions: ${temporary_path}"
if [[ "${in_place}" == true ]]; then
	mv -f "${temporary_path}" "${output_path}"
else
	publish_new_output "${temporary_path}" "${output_path}"
fi
temporary_path=""

echo "Outlined SVG text: ${input_path} -> ${output_path}"
