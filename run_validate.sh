#!/bin/sh
#
# run_validate.sh validates the repository against EXISTING generated evidence.
# Scene layout validation reads renderer-produced stats from
# generated/scene_render_stats/<scene>.stats.json, produced by
# `node tools/scene_to_png.mjs --all` after building dist/.
# This script validates only: it never renders scenes or parses PNG pixels.
# If the stats are missing, validation fails clearly -- build, then render the
# scene statistics before running this script.
# Additional validator flags are forwarded, so release callers can run
# `./run_validate.sh --strict` to promote warnings to a failing exit status.
set -e
date
. ./source_me.sh
python3 ./validation/validate.py -q "$@"
echo ""
