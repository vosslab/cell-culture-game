#!/usr/bin/env bash
# build_github_pages.sh - canonical production build for GitHub Pages.
#
# WP-3-10 extension. The build now produces:
#
#   dist/index.html              -- launcher entry (from src/launcher/index.html)
#   dist/launcher.js             -- launcher bundle (src/launcher_entry.tsx)
#   dist/protocol_host.js        -- protocol host bundle (src/protocol_host_entry.tsx)
#   dist/scene_viewer.js         -- scene viewer bundle (src/dist_entry.tsx)
#   dist/style.css               -- copied verbatim from src/style.css
#   dist/bench_basic.html        -- preserved bench page as a render smoke target
#                                   (renamed from the legacy dist/index.html)
#   dist/scene_viewer.html       -- minimal host: only #scene-root, loads ?scene=<name>
#                                   (from src/scene_viewer_template.html)
#   dist/<protocol_name>.html    -- one per entry in generated PROTOCOLS_INDEX,
#                                   templated from src/protocol_host_template.html
#   dist/.nojekyll               -- GitHub Pages flag
#
# Contract:
#   - Wipes dist/ from scratch.
#   - Verifies required source files: src/dist_entry.tsx,
#     src/launcher_entry.tsx, src/protocol_host_entry.tsx,
#     src/launcher/index.html, src/protocol_host_template.html,
#     src/scene_viewer_template.html, src/index.html (bench),
#     src/style.css. Aborts on missing.
#   - Type-checks via 'tsc --noEmit -p tsconfig.json'.
#   - Bundles three entry points with esbuild (ESM, es2020, browser,
#     minified, sourcemap, Solid JSX flags):
#     src/launcher_entry.tsx       -> dist/launcher.js
#     src/protocol_host_entry.tsx  -> dist/protocol_host.js
#     src/dist_entry.tsx           -> dist/scene_viewer.js
#   - Copies src/launcher/index.html  -> dist/index.html (launcher page).
#   - Copies src/index.html           -> dist/bench_basic.html (bench page).
#   - Copies src/style.css            -> dist/style.css.
#   - Reads PROTOCOLS_INDEX entries from generated/protocols.ts via
#     pipeline/list_protocols.py and instantiates src/protocol_host_template.html
#     once per entry, substituting {{PROTOCOL_NAME}}.
#   - Writes dist/.nojekyll.
#   - Asserts the canonical artifacts exist before exiting.
#
# Hard rule: never produces single-file output. ESM only.

set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

# Require dependencies, but never install them here: this script must stay
# clean for CI / GitHub Pages, where the workflow installs deps (npm ci) before
# building. Local dev convenience (auto-install) lives in run_web_server.sh.
if [ ! -d node_modules ]; then
	echo "ERROR: node_modules missing. Run 'bash devel/setup_typescript.sh' or 'npm ci' first." >&2
	exit 1
fi

# Regenerate the generated/ artifact tree directly (no npm lifecycle hooks).
# build_generated.sh is the single source of truth for generator order.
bash pipeline/build_generated.sh

# Precompute the static scene layout at the canonical 16:9 frame
# (1920x1080) and emit generated/precomputed_layout.ts. Runs AFTER
# build_generated.sh because it imports the generated SCENES, OBJECT_LIBRARY,
# and ASSET_SPECS that step produces. The browser loads these positions
# instead of recomputing layout at runtime (WP-PRECOMP1).
node --import tsx pipeline/precompute_layout.mjs

# Two-bundle split (see docs/active_plans/active/web_ui/bundle_audit.md):
#   src/launcher_entry.tsx       -> dist/launcher.js       (lightweight)
#   src/protocol_host_entry.tsx  -> dist/protocol_host.js  (runtime + renderer + SVGs)

# Verify required source inputs before any destructive step.
REQUIRED_SOURCES=(
	"src/launcher_entry.tsx"
	"src/protocol_host_entry.tsx"
	"src/dist_entry.tsx"
	"src/launcher/index.html"
	"src/protocol_host_template.html"
	"src/scene_viewer_template.html"
	"src/index.html"
	"src/style.css"
	"generated/protocols.ts"
	"generated/protocols_index_slim.ts"
	"pipeline/list_protocols.py"
)
for required in "${REQUIRED_SOURCES[@]}"; do
	if [ ! -f "$required" ]; then
		echo "ERROR: required source file missing: $required" >&2
		exit 1
	fi
done

# Wipe and recreate dist/.
rm -rf dist
mkdir -p dist

# 1. Typecheck.
npx tsc --noEmit -p tsconfig.json

# 2. Bundle the single dist entry via esbuild-plugin-solid (Node API).
#    The plugin runs Solid's babel transform on JSX so reactivity is
#    fine-grained. The plain esbuild CLI cannot do this transform.
node pipeline/build_main_bundle.mjs

# 3. Copy launcher HTML as the dist root (dist/index.html).
cp src/launcher/index.html dist/index.html

# 4. Copy bench HTML to bench_basic.html as a render smoke target.
#    The legacy bench page used to be dist/index.html; it is preserved
#    under a stable name so existing smoke paths keep working.
cp src/index.html dist/bench_basic.html

# 5. Copy scene viewer host HTML.
#    Minimal page: only #scene-root (no #shell-root, no window.__PROTOCOL_NAME__).
#    dist_entry.tsx route() reads ?scene=<name> and calls mount_scene_viewer.
#    Served as dist/scene_viewer.html?scene=<name> by tools and smoke tests.
cp src/scene_viewer_template.html dist/scene_viewer.html

# 6. Copy stylesheet.
cp src/style.css dist/style.css

# 6b. Copy bundled fonts so the @font-face url() in style.css resolves.
#     style.css references assets/fonts/*.woff2 relative to dist/style.css;
#     both the PNG render server (tools/scene_to_png.mjs) and GitHub Pages
#     serve dist/, so the font must live under dist/assets/fonts/.
mkdir -p dist/assets/fonts
cp assets/fonts/*.woff2 dist/assets/fonts/

# 6c. Copy SVG source files so the manifest's relative paths resolve.
#     generated/svg_manifest.ts maps each asset to assets/svg/<category>/<name>.svg
#     relative to the served dist/ root. Both the PNG render server
#     (tools/scene_to_png.mjs) and GitHub Pages serve dist/, so SVGs must live
#     under dist/assets/svg/<category>/. Mirror the assets/<category>/ layout.
mkdir -p dist/assets/svg
for category_dir in assets/*/; do
	category=$(basename "$category_dir")
	# Only categories that actually contain SVG files (skip fonts, etc.).
	if compgen -G "${category_dir}*.svg" > /dev/null; then
		mkdir -p "dist/assets/svg/${category}"
		cp "${category_dir}"*.svg "dist/assets/svg/${category}/"
	fi
done

# 7. Generate dist/<protocol_name>.html for every PROTOCOLS_INDEX entry.
#    list_protocols.py 'emit' parses PROTOCOLS_INDEX from generated/protocols.ts
#    and writes one dist/<name>.html per entry, substituting {{PROTOCOL_NAME}}.
python3 pipeline/list_protocols.py emit \
	--template src/protocol_host_template.html \
	--out-dir dist

# 8. GitHub Pages marker.
touch dist/.nojekyll

# 9. Assert the canonical artifacts exist.
test -f dist/index.html
test -f dist/launcher.js
test -f dist/protocol_host.js
test -f dist/scene_viewer.js
test -f dist/style.css
test -f dist/bench_basic.html
test -f dist/scene_viewer.html

echo "Built dist/ (GitHub Pages-ready)."
