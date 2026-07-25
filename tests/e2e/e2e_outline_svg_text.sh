#!/usr/bin/env bash
# e2e_outline_svg_text.sh - prove the optional Inkscape outline wrapper is transactional.

set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

work_dir="$(mktemp -d "${TMPDIR:-/tmp}/e2e_outline_svg_text.XXXXXX")"
cleanup() {
	rm -rf "${work_dir}"
}
trap cleanup EXIT INT TERM HUP

svg_mode() {
	if stat --version >/dev/null 2>&1; then
		stat -c '%a' "$1"
	else
		stat -f '%Lp' "$1"
	fi
}

require_outlined_svg() {
	local path="$1"
	local remaining_count
	if ! xmllint --noout "${path}"; then
		echo "Outlined SVG is not well-formed XML: ${path}" >&2
		exit 1
	fi
	remaining_count="$(xmllint --xpath 'count(//*[local-name()="text" or local-name()="tspan" or local-name()="textPath"])' "${path}")"
	if [[ "${remaining_count}" != "0" ]]; then
		echo "Outlined SVG still contains live text elements: ${path}" >&2
		exit 1
	fi
}

if ! command -v xmllint >/dev/null 2>&1; then
	echo "xmllint is required for this E2E." >&2
	exit 1
fi

input_path="${work_dir}/input.svg"
output_path="${work_dir}/output.svg"
in_place_path="${work_dir}/in_place.svg"
source_copy="${work_dir}/source_before.svg"
output_copy="${work_dir}/output_before.svg"

printf '%s\n' \
	'<svg xmlns="http://www.w3.org/2000/svg" width="160" height="60" viewBox="0 0 160 60">' \
	'  <text x="8" y="36" font-family="DejaVu Sans" font-size="24"><tspan>120 V</tspan></text>' \
	'</svg>' >"${input_path}"
cp "${input_path}" "${source_copy}"
chmod 640 "${input_path}"
source_mode="$(svg_mode "${input_path}")"

tools/outline_svg_text.sh "${input_path}" "${output_path}"
if ! cmp -s "${input_path}" "${source_copy}"; then
	echo "Source SVG changed during non-destructive outline conversion." >&2
	exit 1
fi
if [[ ! -s "${output_path}" ]]; then
	echo "Outline conversion did not create a non-empty output SVG." >&2
	exit 1
fi

require_outlined_svg "${output_path}"

cp "${output_path}" "${output_copy}"
if tools/outline_svg_text.sh "${input_path}" "${output_path}"; then
	echo "Outline conversion overwrote an existing default output." >&2
	exit 1
fi
if ! cmp -s "${output_path}" "${output_copy}"; then
	echo "Existing output changed after overwrite refusal." >&2
	exit 1
fi
if ! cmp -s "${input_path}" "${source_copy}"; then
	echo "Source SVG changed after default-output refusal." >&2
	exit 1
fi

cp "${input_path}" "${in_place_path}"
chmod "${source_mode}" "${in_place_path}"
tools/outline_svg_text.sh --in-place "${in_place_path}"
if cmp -s "${in_place_path}" "${source_copy}"; then
	echo "Explicit in-place outline conversion did not replace the source SVG." >&2
	exit 1
fi
require_outlined_svg "${in_place_path}"
if [[ "$(svg_mode "${in_place_path}")" != "${source_mode}" ]]; then
	echo "In-place outline conversion did not preserve source file permissions." >&2
	exit 1
fi

echo "PASS: outline_svg_text wrapper preserves default inputs and outlines live text."
