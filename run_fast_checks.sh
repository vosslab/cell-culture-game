#!/usr/bin/env bash
# run_fast_checks.sh - single umbrella fast verification gate.
#
# Front door: run this directly as ./run_fast_checks.sh. It is the one
# always-run local FAST gate: regenerate generated/, then run every fast
# check in sequence. It does not run the browser walker sweep (that stays a
# separate, slower step run via ./run_playwright_tests.sh).
#
# Runs (in order):
#   1. Full build (./build_github_pages.sh). Regenerates generated/
#      (object_library, svg_manifest, scenes, protocols), precomputes the
#      static scene layout, type-checks, and bundles into dist/.
#   2. Render scene statistics with Playwright
#      (node tools/scene_to_png.mjs --all). This is REQUIRED before
#      validation: SCENE-LINT's geometry checks read the stats files, and
#      without them validation reports missing_render_evidence instead of a
#      real geometry result.
#   3. TypeScript gate (./check_codebase.sh: tsc, tsc --lint config,
#      eslint, prettier --check, node --test).
#   4. Python tests (pytest tests/).
#   5. Content validation (bash run_validate.sh), which reads the renderer
#      evidence produced in step 2.
#
# Exit code is 0 only when every step passes. A step failure prints a
# summary and exits non-zero immediately; it does not mask or skip later
# steps by continuing past a failure.
#
# This script uses run_validate.sh's default severity policy: errors fail;
# warnings and advisories remain visible but non-failing. Release callers that
# require a warning-free corpus can use `./run_validate.sh --strict`.

set -eo pipefail

# Usage
usage() {
	cat <<'USAGE'
Usage: run_fast_checks.sh [-h|--help]

  -h, --help          Print this help and exit 0.

Each step runs its own script directly; nothing here re-implements or
weakens the underlying check.
USAGE
}

# Parse flags
while [ "$#" -gt 0 ]; do
	case "$1" in
		-h|--help)
			usage
			exit 0
			;;
		*)
			echo "ERROR: unknown flag: $1" >&2
			usage >&2
			exit 2
			;;
	esac
done

cd "$(git rev-parse --show-toplevel)"

if ! command -v node >/dev/null 2>&1; then
	echo "ERROR: node not found on PATH." >&2
	exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
	echo "ERROR: python3 not found on PATH." >&2
	exit 1
fi

# Step tracking (bash 3.2 compatible)
STEP_NAMES=()
STEP_STATUS=()
SUMMARY_ENABLED=0

# step_record <name> <status>
step_record() {
	STEP_NAMES+=("$1")
	STEP_STATUS+=("$2")
}

# step_run <name> <command...>
# Runs the given command. Records PASS or FAIL+summary+exit 1.
step_run() {
	local name="$1"
	shift
	echo "==> $name"
	local rc=0
	set +e
	"$@"
	rc=$?
	set -e
	if [ "$rc" -eq 0 ]; then
		step_record "$name" "PASS"
	else
		step_record "$name" "FAIL"
		print_summary
		trap - EXIT
		exit 1
	fi
}

# Summary
print_summary() {
	if [ "$SUMMARY_ENABLED" != "1" ]; then
		return 0
	fi
	local total=${#STEP_NAMES[@]}
	local failed=0
	local i=0
	echo "Summary:"
	while [ "$i" -lt "$total" ]; do
		local name="${STEP_NAMES[$i]}"
		local status="${STEP_STATUS[$i]}"
		if [ "$status" = "FAIL" ]; then
			failed=$((failed + 1))
		fi
		echo "  [$status] $name"
		i=$((i + 1))
	done
	if [ "$failed" -eq 0 ]; then
		echo "PASS: $total checks passed."
	else
		echo "FAIL: $failed of $total checks failed."
	fi
}

trap print_summary EXIT

SUMMARY_ENABLED=1

# 1. Full build: regenerates generated/, precomputes layout, type-checks,
#    and bundles dist/.
step_run build bash build_github_pages.sh

# 2. Render evidence for run_validate.sh's SCENE-LINT stage below.
step_run render_stats node tools/scene_to_png.mjs --all

# 3. TypeScript gate (typecheck, typecheck:lint, lint, format:check, test:node).
step_run typescript ./check_codebase.sh

# 4. Python tests.
step_run pytest pytest tests/

# 5. Content validation against generated evidence.
step_run validate bash run_validate.sh

# All steps complete; summary prints via EXIT trap. Exit 0 (failure paths
# exit 1 directly above).
exit 0
