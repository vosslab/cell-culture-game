#!/usr/bin/env bash
# render_liquid_volume_contact_sheet.sh - rebuild and render every variable-volume form.
#
# Front door: run directly as ./render_liquid_volume_contact_sheet.sh.
# The contact sheet is developer evidence, written to
# rendered-reports/liquid_volume_contacts/all_variable_volume_assets.{html,png}.
# Each invocation generates fresh random colors and prints a visible build ID,
# making a stale local file immediately obvious during visual review.

set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

./build_github_pages.sh

node tools/liquid_volume_contact_page.mjs \
  bottle_medium_pink \
  falcon_15ml \
  falcon_50ml \
  microtube \
  serological_pipette \
  --volumes '0,5,10,25,50,75,85,90,100' \
  --note 'bottle_medium_pink=Requests above 85% are capped and render identically at 85%.'
