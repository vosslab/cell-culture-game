#!/usr/bin/env bash
# e2e_run_web_server_duration.sh - prove the bounded preview server stops cleanly.

set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
source source_me.sh

log_file="$(mktemp "${TMPDIR:-/tmp}/run_web_server_duration.XXXXXX")"
runner_pid=""
blocker_pid=""

cleanup() {
	if [ -n "${runner_pid}" ] && kill -0 "${runner_pid}" 2>/dev/null; then
		kill "${runner_pid}" 2>/dev/null || true
	fi
	if [ -n "${blocker_pid}" ] && kill -0 "${blocker_pid}" 2>/dev/null; then
		kill "${blocker_pid}" 2>/dev/null || true
	fi
	rm -f "${log_file}" || true
}
trap cleanup EXIT INT TERM HUP

wait_for_log_line() {
	local pattern="$1"
	local deadline=$((SECONDS + 30))
	while ! grep -q "${pattern}" "${log_file}"; do
		if [ "${SECONDS}" -ge "${deadline}" ]; then
			echo "Timed out waiting for server readiness: ${pattern}" >&2
			return 1
		fi
		sleep 0.1
	done
}

if ./run_web_server.sh --duration 0 >"${log_file}" 2>&1; then
	echo "Expected --duration 0 to be rejected." >&2
	exit 1
fi
if ! grep -q "Invalid --duration value" "${log_file}"; then
	echo "Missing clear invalid-duration error." >&2
	exit 1
fi

./run_web_server.sh --duration 1 >"${log_file}" 2>&1 &
runner_pid=$!

deadline=$((SECONDS + 120))
while kill -0 "${runner_pid}" 2>/dev/null; do
	if [ "${SECONDS}" -ge "${deadline}" ]; then
		echo "Timed web server did not exit within the E2E budget." >&2
		exit 1
	fi
	sleep 1
done

if ! wait "${runner_pid}"; then
	echo "Timed web server exited unsuccessfully." >&2
	exit 1
fi
runner_pid=""

if ! grep -q "Web server stopped after 1 seconds" "${log_file}"; then
	echo "Timed web server did not report its clean duration shutdown." >&2
	exit 1
fi

python3 -u -m http.server 0 --bind 127.0.0.1 --directory dist >"${log_file}" 2>&1 &
blocker_pid=$!
wait_for_log_line "Serving HTTP on"
if ! kill -0 "${blocker_pid}" 2>/dev/null; then
	echo "The E2E port-reserving server exited before it became ready." >&2
	exit 1
fi
port="$(sed -nE 's/.*port ([0-9]+).*/\1/p' "${log_file}" | head -n 1)"
if [ -z "${port}" ]; then
	echo "Could not read the E2E preview port from the ready server." >&2
	exit 1
fi

if PORT="${port}" ./run_web_server.sh --duration 300 >"${log_file}" 2>&1; then
	echo "Expected an occupied preview port to fail." >&2
	exit 1
fi
if ! grep -q "Web server exited before --duration 300 elapsed" "${log_file}"; then
	echo "Early server exit did not cancel its duration helper." >&2
	exit 1
fi

kill "${blocker_pid}" 2>/dev/null || true
wait "${blocker_pid}" 2>/dev/null || true
blocker_pid=""
