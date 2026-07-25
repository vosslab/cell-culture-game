# source_me.sh - shell environment for running this repo's Python.
# Usage: source source_me.sh && python3 ...
# This is a bash script sourced into your shell, not run directly.

# Require bash: the checks below and the repo's tab-indented shell style are
# bash-specific. Fail loudly rather than misbehave under another shell.
set | grep -q '^BASH_VERSION=' || echo "use bash for your shell"
set | grep -q '^BASH_VERSION=' || exit 1
ulimit -Sn 65536

# Source ~/.bashrc FIRST, before any repo-specific environment extension below.
# ~/.bashrc applies local shell setup (PATH, etc.) and resets some variables --
# it clears PYTHONPATH (verified). Anything that sets PYTHONPATH must run after
# this line, or ~/.bashrc would wipe it.
source ~/.bashrc

# Python runtime defaults: unbuffered stdout/stderr, and no .pyc/__pycache__
# files written on import.
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

# --- Repo-root import path (enabled for this repo) ---------------------------
# This repo needs its repo-root packages importable package-qualified (for
# example `import pipeline.entity_decode`, `import validation.*`) when generators
# and scripts run from a subdirectory or without installing the repo.
# Must come after sourcing ~/.bashrc, which clears PYTHONPATH.
# Assumes the repo is inside a Git work tree (git rev-parse).
REPO_ROOT="$(git rev-parse --show-toplevel)"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"
unset REPO_ROOT
