# Usage

This repository compiles YAML-authored biology lab protocols, scenes, and
SVG-backed objects into a GitHub Pages-ready browser simulation.

## Setup

Follow [INSTALL.md](INSTALL.md) for prerequisites. From a fresh clone, install
the Node dependencies used by the build and checks:

```bash
bash devel/setup_typescript.sh
```

Browser tests also need the locally installed Playwright browsers:

```bash
bash devel/setup_playwright.sh
```

Repo-local Python commands must run through the repository environment:

```bash
source source_me.sh && python3 --version
```

## Build and preview

Build the deployment artifact and generated protocol data:

```bash
bash build_github_pages.sh
```

The result is `dist/`, including the launcher, protocol pages, and scene
viewer. For a loopback-only preview, use the server front door; it builds
`dist/`, chooses a random local port, and opens the launcher when interactive:

```bash
bash run_web_server.sh
```

For a bounded smoke preview that stops itself after a positive whole number of
seconds:

```bash
bash run_web_server.sh --duration 30
```

## Validation and walkthroughs

Use the fast gate during normal development. It builds, checks TypeScript,
runs Python tests, and validates content against the generated render evidence:

```bash
./run_fast_checks.sh
```

For the exhaustive suite, including non-browser E2E tests and all Playwright
tests, run:

```bash
./super_all_tests.sh
```

Run the browser suite through its repository-owned runner. To exercise the
visible-UI protocol walkthrough specifically:

```bash
bash run_playwright_tests.sh tests/playwright/e2e/protocol_walkthrough.spec.ts
```

The walkthrough starts its own configured server and follows the same visible
controls that a student uses. See [E2E_TESTS.md](E2E_TESTS.md) and
[PLAYWRIGHT_USAGE.md](PLAYWRIGHT_USAGE.md) for test conventions.

## Authoring routes

Curriculum content lives under
`content/protocols/<cluster>/<protocol_name>/`. Author YAML stays within the
closed vocabularies and is compiled by the normal build; do not hand-edit
`generated/` or `dist/`.

Start with these references:

- [PRIMARY_CONTRACT.md](PRIMARY_CONTRACT.md): hard project invariants.
- [PROTOCOL_AUTHORING_GUIDE.md](specs/PROTOCOL_AUTHORING_GUIDE.md): worked
  protocol-authoring example.
- [PROTOCOL_YAML_FORMAT.md](specs/PROTOCOL_YAML_FORMAT.md): protocol schema.
- [SCENE_YAML_FORMAT.md](specs/SCENE_YAML_FORMAT.md): scene declarations and
  layout inputs.
- [OBJECT_YAML_FORMAT.md](specs/OBJECT_YAML_FORMAT.md): object definitions and
  state.
- [MATERIAL_YAML_FORMAT.md](specs/MATERIAL_YAML_FORMAT.md): material state and
  rendering inputs.
- [SVG_PIPELINE.md](specs/SVG_PIPELINE.md): SVG ingestion and normalization.

## SVG text preparation

Keep source SVG art language-neutral. Identity, state, and instructional prose
belong in layout-manager DOM labels or object data, not in SVG artwork. Sparse
intrinsic markings such as units, symbols, graduations, polarity, and plate
coordinates may remain.

When a rare approved intrinsic marking arrives as live SVG text, prefer
`rsvg-convert` from librsvg to prepare a separate path-only output, then run the
repository normalizer:

```bash
rsvg-convert --format svg --output outlined.svg raw.svg
source source_me.sh && python3 tools/normalize_svg_v3.py -i outlined.svg -o assets/equipment/static/
```

`normalize_svg_v3.py -o` takes an output directory, not an output filename.
The repository has no desktop-editor adapter. Neither librsvg nor the
normalizer authorizes prose inside SVG art; learner-facing text belongs in
accessible, localizable DOM or object data.

## Variable-volume contact sheet

Rebuild the published assets and render every variable-volume family into one
self-contained HTML contact sheet plus a PNG:

```bash
./tools/render_liquid_volume_contact_sheet.sh
```

Each rebuild generates a fresh random liquid color for every vessel family. The
sheet records those exact colors, its creation time, its build ID, and per-card
rendered-fill diagnostics, so a result is reproducible without replacing the
random input with a curated palette. Persistent, gitignored outputs are
`rendered-reports/liquid_volume_contacts/all_variable_volume_assets.html` and
`rendered-reports/liquid_volume_contacts/all_variable_volume_assets.png`.

## Equipment SVG visual review

Regenerate the current human review page from the authored equipment tree:

```bash
node tools/render_svg_library_review.mjs
```

Open `docs/figures/equipment_kit/review.html`. This intentional generated,
shipped static page live-links every current authored equipment SVG in a
searchable, behavior-filtered inventory and works through `file://`. It does
not embed scene captures or reproduce runtime material painting.

Use that page to inspect source-art shape, source-card transparency, and
coverage. To inspect every asset through its actual shipping renderer, run
`./run_web_server.sh` and append `/equipment_review.html` to the printed HTTP
origin. That built page uses the same shared SVG host as production scenes:
DOM-required art is fetched, ID-namespaced, and injected, while ordinary art
remains an image. It provides render-mode, backdrop, search, and size controls.
Because the inline path fetches built artifacts, use HTTP rather than
`file://` for this page.

For scene scale, layout, and runtime material painting in context, use a route
such as `/scene_viewer.html?scene=bench_basic` from the same server.

`docs/figures/equipment_kit/candidates/review.html` redirects to the gallery.
The D01-D05 candidate artifacts and the older
[EQUIPMENT_SVG_CONTACT_SHEET.md](EQUIPMENT_SVG_CONTACT_SHEET.md) are rejected
historical snapshots, not current-production review surfaces.
