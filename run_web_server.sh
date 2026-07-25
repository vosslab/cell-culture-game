#!/usr/bin/env bash
# run_web_server.sh - local dev preview for the GitHub Pages build.
#
# Front door: run this directly as ./run_web_server.sh. It is the interface
# for everyone, no npm knowledge required. The npm run serve alias is an
# optional mirror that points right back at this script.
#
# Always serves dist/ (the GitHub Pages artifact). Never serves the
# repo root or _site/.
#
# Lifecycle: this script owns ONLY the processes it starts -- the
# http.server child, its optional duration timer, and its own delayed browser-open helper.
# An
# idempotent cleanup trap kills only those owned PIDs on exit. It never
# scans for or kills any process it did not start (no pkill/pgrep/ps,
# no PID file). Residual: SIGKILL of this script is untrappable, so a
# kill -9 can still orphan the child; that is an inherent shell limit.

set -euo pipefail

usage() {
	cat <<'EOF'
Usage: ./run_web_server.sh [--duration SECONDS]

Build dist/ and serve it locally on a random port. Without --duration, the
server remains in the foreground until interrupted. With --duration, the
server stops cleanly after the requested positive whole number of seconds.
EOF
}

duration_seconds=""
while [ "$#" -gt 0 ]; do
	case "$1" in
		--duration)
			if [ "$#" -lt 2 ]; then
				echo "Missing value for --duration. Use a positive whole number of seconds." >&2
				exit 2
			fi
			duration_seconds="$2"
			shift 2
			;;
		--duration=*)
			duration_seconds="${1#--duration=}"
			shift
			;;
		-h | --help)
			usage
			exit 0
			;;
		*)
			echo "Unknown option: $1" >&2
			usage >&2
			exit 2
			;;
	esac
done

if [ -n "${duration_seconds}" ] && ! [[ "${duration_seconds}" =~ ^[1-9][0-9]*$ ]]; then
	echo "Invalid --duration value '${duration_seconds}'. Use a positive whole number of seconds." >&2
	exit 2
fi

cd "$(git rev-parse --show-toplevel)"

# Initialize owned-PID vars BEFORE installing the trap so cleanup is
# safe under set -u even if it fires before the server starts (e.g. a
# setup or build failure).
server_pid=""
opener_pid=""
timer_pid=""
timer_marker=""

#============================================
# Idempotent, exit-status-preserving cleanup. Kills only the PIDs this
# script started, and only if they are still live.
cleanup() {
	# Capture the triggering exit status as the very first action.
	local status=$?
	# Clear the trap so this runs exactly once (idempotent on re-entry).
	trap - EXIT INT TERM HUP
	# Kill the browser-open helper first, only if still alive. An
	# already-dead helper is normal, not an error.
	if [ -n "${opener_pid}" ] && kill -0 "${opener_pid}" 2>/dev/null; then
		kill "${opener_pid}" 2>/dev/null || true
	fi
	# Stop the optional duration timer before the server it controls.
	if [ -n "${timer_pid}" ] && kill -0 "${timer_pid}" 2>/dev/null; then
		kill "${timer_pid}" 2>/dev/null || true
	fi
	# Kill the server child, only if still alive.
	if [ -n "${server_pid}" ] && kill -0 "${server_pid}" 2>/dev/null; then
		kill "${server_pid}" 2>/dev/null || true
	fi
	# The marker belongs only to this invocation and records that the timer
	# reached its requested duration before terminating the server.
	if [ -n "${timer_marker}" ]; then
		rm -f "${timer_marker}" || true
	fi
	# Preserve the real exit status so failures are not masked.
	exit "${status}"
}
# HUP covers the tool-shell-termination case.
trap cleanup EXIT INT TERM HUP

# Auto-install dependencies on missing node_modules.
if [ ! -d node_modules ]; then
	if [ -f devel/setup_typescript.sh ]; then
		echo "node_modules missing. Running devel/setup_typescript.sh ..." >&2
		bash devel/setup_typescript.sh
	else
		echo "node_modules missing and devel/setup_typescript.sh not found." >&2
		echo "Install dependencies (npm install) or restore the setup script." >&2
		exit 1
	fi
fi

# Random port per session: each port is its own browser origin, so the
# cache is effectively invalidated every run. PORT env var overrides.
PORT="${PORT:-$((8000 + RANDOM % 1000))}"

# Build the GitHub Pages artifact into dist/ (no args; contract is stable).
./build_github_pages.sh

# Open the browser after a short delay when interactive. Capture the
# helper subshell PID so cleanup can kill only this helper, never the
# browser or the opened app.
if command -v open >/dev/null 2>&1 && [ -t 0 ]; then
	(sleep 1 && open "http://127.0.0.1:${PORT}/") &
	opener_pid=$!
fi

# Bind explicitly to IPv4 loopback. Besides keeping this development preview
# off the LAN, this makes an occupied loopback port fail consistently instead
# of allowing a second server to claim the same number on IPv6.
#
# Start the server in the background to capture its PID, then wait on it to
# hold the foreground. Capturing wait's status (rather than masking it with
# || true) lets a genuine server startup/exit failure surface, while a
# trap-initiated kill is treated as a clean shutdown.
python3 -m http.server "${PORT}" --bind 127.0.0.1 --directory dist &
server_pid=$!

if [ -n "${duration_seconds}" ]; then
	# A private marker removes the race between a timer-triggered TERM and the
	# server's exit: only an elapsed timer may turn that expected TERM into a
	# successful script exit. The timer and marker are both owned by this script.
	timer_marker="$(mktemp "${TMPDIR:-/tmp}/run_web_server_timer.XXXXXX")"
	(
		timer_sleep_pid=""
		timer_cleanup() {
			local status=$?
			trap - EXIT INT TERM HUP
			if [ -n "${timer_sleep_pid}" ] && kill -0 "${timer_sleep_pid}" 2>/dev/null; then
				kill "${timer_sleep_pid}" 2>/dev/null || true
				wait "${timer_sleep_pid}" 2>/dev/null || true
			fi
			exit "${status}"
		}
		trap timer_cleanup EXIT INT TERM HUP
		sleep "${duration_seconds}" &
		timer_sleep_pid=$!
		wait "${timer_sleep_pid}"
		printf 'elapsed\n' >"${timer_marker}"
		if kill -0 "${server_pid}" 2>/dev/null; then
			kill -TERM "${server_pid}"
		else
			exit 1
		fi
	) &
	timer_pid=$!
fi

if wait "${server_pid}"; then
	wait_status=0
else
	wait_status=$?
fi

if [ -n "${duration_seconds}" ]; then
	if [ -s "${timer_marker}" ]; then
		if wait "${timer_pid}"; then
			timer_status=0
		else
			timer_status=$?
		fi
		if [ "${timer_status}" -ne 0 ]; then
			echo "Duration timer could not stop the web server cleanly." >&2
			exit "${timer_status}"
		fi
		# Python exits 143 when TERM ends http.server. A server that handles TERM
		# and returns 0 is also a clean, timer-requested shutdown.
		if [ "${wait_status}" -eq 0 ] || [ "${wait_status}" -eq 143 ]; then
			echo "Web server stopped after ${duration_seconds} seconds."
			exit 0
		fi
		echo "Web server exited with status ${wait_status} after the duration timer elapsed." >&2
		exit "${wait_status}"
	fi

	# The server ended before the owned timer elapsed. Cancel the timer before
	# failing, so no helper remains after an unexpected server exit.
	if kill -0 "${timer_pid}" 2>/dev/null; then
		kill "${timer_pid}" 2>/dev/null || true
	fi
	wait "${timer_pid}" 2>/dev/null || true
	echo "Web server exited before --duration ${duration_seconds} elapsed." >&2
	if [ "${wait_status}" -eq 0 ]; then
		exit 1
	fi
	exit "${wait_status}"
fi

# A trap-initiated kill terminates the script inside cleanup before
# reaching here, so this exit carries the server's own exit status when
# it stops on its own.
exit "${wait_status}"
