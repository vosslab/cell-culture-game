#!/usr/bin/env bash
# super_all_tests.sh - run EVERY test and gate in the repo. Nothing skipped.
#
# This is the exhaustive suite (not the fast gate). It runs the build, the code
# and content gates, and then every test file in the repo -- including the ones
# that pytest and the fast gate skip: the tests/e2e/ suite and the browser tests
# in tests/playwright/. It keeps going when a step fails, so one red never hides
# the rest, and prints a PASS/FAIL summary at the end. Wall time does not matter
# here; running everything does.
#
# Browser tests run through the Playwright test runner front door
# (run_playwright_tests.sh, which invokes `npx playwright test`) -- this
# repo's single Playwright model per docs/PLAYWRIGHT_TEST_STYLE.md. The
# runner's config owns the shared webServer and covers every .spec.ts file,
# including the protocol walker sweep at tests/playwright/e2e/protocol_walkthrough.spec.ts.
#
# Full output is saved to SUPER_LOG.txt. A short PASS/FAIL line prints per step.
#
# E2E files with the supported e2e_*.py, e2e_*.mjs, and e2e_*.sh names run
# automatically.
#
# Usage:
#   ./super_all_tests.sh

set -u

# Always work from the repo root, wherever the script is called from.
cd "$(git rev-parse --show-toplevel)" || exit 1

# Set up the Python environment once, so every python3 / pytest call below works.
source source_me.sh

LOG="SUPER_LOG.txt"

# These lists record the outcome of each step, filled in by run(). STEP_CMDS
# holds the exact command each step ran, so the summary can show how to re-run
# any single test on its own.
STEP_NAMES=()
STEP_STATUS=()
STEP_SECONDS=()
STEP_CMDS=()

# Color codes for the screen only. Empty when stdout is not a terminal, so the
# log file (and piped output) never gets ANSI escapes. Only PASS/FAIL colored.
if [ -t 1 ]; then
	C_PASS=$'\033[32m'   # green
	C_FAIL=$'\033[31m'   # red
	C_OFF=$'\033[0m'     # reset
else
	C_PASS=''
	C_FAIL=''
	C_OFF=''
fi


# status_token - print the colored [PASS] or [FAIL] label for screen output.
status_token() {
	if [ "$1" = "PASS" ]; then
		printf '%s[PASS]%s' "$C_PASS" "$C_OFF"
	else
		printf '%s[FAIL]%s' "$C_FAIL" "$C_OFF"
	fi
}


# run - run one test or gate, save its output, and record pass or fail.
#
# Usage: run "a short name" the command to run...
# Example: run "pytest" pytest tests/
#          run "launcher" node tests/playwright/test_launcher.mjs
#
# It never stops the script on failure; it just records the result and moves on.
run() {
	name="$1"
	shift  # everything after the name is the command to run
	cmd="$*"  # the exact command, saved so the summary can show how to re-run it

	# Write a clear header into the log so each step is easy to find.
	{
		echo ""
		echo "################################################################"
		echo "# STEP: $name"
		echo "# CMD:  $*"
		echo "# TIME: $(date '+%Y-%m-%d %H:%M:%S')"
		echo "################################################################"
	} >> "$LOG"

	# Show which test is running before it starts (a step can take a while).
	printf 'RUN  %s\n' "$name"

	# Run the command. Send its output (normal + errors) to the log.
	start=$SECONDS
	if "$@" >> "$LOG" 2>&1; then
		result="PASS"
	else
		result="FAIL"
	fi
	seconds=$(( SECONDS - start ))

	# Close the block in the log and remember the result for the summary.
	echo "" >> "$LOG"
	echo "---------- END $name: $result (${seconds}s) ----------" >> "$LOG"
	STEP_NAMES+=("$name")
	STEP_STATUS+=("$result")
	STEP_SECONDS+=("$seconds")
	STEP_CMDS+=("$cmd")

	# Print a short live line to the screen (colored status token).
	printf '%s %-40s %5ds\n' "$(status_token "$result")" "$name" "$seconds"
}


# print_summary - print the table of results and the final verdict.
print_summary() {
	echo ""
	echo "========== SUMMARY =========="
	echo "Re-run any one test with the command shown after '->' (from the repo root)."
	failed=0
	total=${#STEP_NAMES[@]}
	i=0
	while [ "$i" -lt "$total" ]; do
		printf '  %s %-40s %5ds  ->  %s\n' \
			"$(status_token "${STEP_STATUS[$i]}")" "${STEP_NAMES[$i]}" \
			"${STEP_SECONDS[$i]}" "${STEP_CMDS[$i]}"
		if [ "${STEP_STATUS[$i]}" = "FAIL" ]; then
			failed=$(( failed + 1 ))
		fi
		i=$(( i + 1 ))
	done

	if [ "$failed" -eq 0 ]; then
		echo "ALL PASS ($total/$total)"
	else
		echo "FAILED $failed of $total"
	fi

	# Also save the summary into the log.
	{
		echo ""
		echo "========== SUMMARY =========="
		echo "Re-run any one test with the command shown after '->' (from the repo root)."
		i=0
		while [ "$i" -lt "$total" ]; do
			printf '  [%s] %-40s %5ds  ->  %s\n' \
				"${STEP_STATUS[$i]}" "${STEP_NAMES[$i]}" \
				"${STEP_SECONDS[$i]}" "${STEP_CMDS[$i]}"
			i=$(( i + 1 ))
		done
		echo "failed: $failed of $total"
	} >> "$LOG"

	if [ "$failed" -eq 0 ]; then
		return 0
	fi
	return 1
}


main() {
	# Start a fresh log.
	echo "super_all_tests.sh" > "$LOG"
	date >> "$LOG"
	echo "Running the full suite. Details in $LOG"
	echo ""

	# --- 1. Build first. validate, scene metrics, and the browser tests all
	#        read what this produces (generated/, dist/, render stats). ---
	run "build" bash build_github_pages.sh

	# --- 2. Code and content gates. ---
	run "check_codebase" ./check_codebase.sh
	run "pytest"         pytest tests/
	run "validate"       bash run_validate.sh
	run "scene_metrics"  python3 -m validation.scene_design.cli -S content/base_scenes/*.yaml

	# --- 3. End-to-end tests in tests/e2e/ (pytest skips this folder). ---
	#     Python E2E tests:
	for testfile in tests/e2e/e2e_*.py; do
		[ -e "$testfile" ] || continue        # skip if none match
		run "e2e: $(basename "$testfile")" python3 "$testfile"
	done
	#     Node E2E tests. Run under the tsx loader so a .mjs that imports .ts
	#     source is transformed at import time; a plain .mjs with no .ts import
	#     runs fine under tsx too. Mirrors check_codebase.sh (node --import tsx).
	for testfile in tests/e2e/e2e_*.mjs; do
		[ -e "$testfile" ] || continue
		run "e2e: $(basename "$testfile")" node --import tsx "$testfile"
	done
	#     Shell E2E tests run directly through bash, as documented in E2E_TESTS.
	for testfile in tests/e2e/e2e_*.sh; do
		[ -e "$testfile" ] || continue
		run "e2e: $(basename "$testfile")" bash "$testfile"
	done

	# --- 4. Browser tests in tests/playwright/ (pytest skips this folder). ---
	#     Runs every .spec.ts through the Playwright runner front door, which
	#     includes the protocol walker sweep spec.
	run "browser tests" bash run_playwright_tests.sh

	# --- Done: print the results table and return non-zero if anything failed. ---
	print_summary
}

main
