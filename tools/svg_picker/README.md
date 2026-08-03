# SVG Picker Workflow

Static three-pane review queue for assigning missing object SVGs.

## Quick start

### 1. Build manifests (one-time or before each picking session)

```bash
source source_me.sh && python3 tools/svg_picker/build_candidate_manifest.py
source source_me.sh && python3 tools/svg_picker/build_missing_targets.py
source source_me.sh && python3 tools/svg_picker/build_ranked_suggestions.py
```

All three emit JSON files under `tools/svg_picker/`: `candidates.json`, `missing_targets.json`, `suggestions.json`. These are gitignored.

### 2. Open the picker

**Firefox (supports `file://` fetch):**

```bash
open tools/svg_picker/index.html
```

**Chrome (blocks `file://` cross-origin fetch):**
Chrome and some browsers block `fetch()` of sibling files when opened via `file://` protocol. Use the Python fallback server:

```bash
python3 -m http.server --directory tools/svg_picker 8127
```

Then visit `http://127.0.0.1:8127/` in your browser.

### 3. Review and export decisions

- **Navigate:** use arrow keys or `/` to search; `n` jumps to next unassigned; `[` / `]` previous/next target.
- **Assign:** highlight a candidate, press `Enter` to assign it.
- **Defer:** press `d` to mark current target for later review.
- **Ignore intentional:** press `i` and enter a reason (e.g., "custom vector needed").
- **Hide candidate:** press `x` to hide from current target; press `X` to hide from entire family.
- **Batch actions:** shift+click targets to multi-select; action bar offers defer-all, assign-same-to-all, ignore-all-with-shared-reason.
- **Session autosave:** all decisions persist to localStorage; reload prompts "resume" vs "start fresh".
- **Export:** click "Export decisions" button to download `decisions.json`.

See the **Shortcuts** button in the picker footer for full keyboard reference.

### 4. Apply decisions

Once you have `decisions.json` in the repo root:

```bash
source source_me.sh && python3 tools/svg_picker/apply_decisions.py --dry-run decisions.json
```

Review the dry-run output to verify the plan. Then apply for real:

```bash
source source_me.sh && python3 tools/svg_picker/apply_decisions.py decisions.json
```

The applier validates every decision before writing to disk:

- All required fields are present (asset_name, state, candidate_id for assigned).
- Assigned decisions reference existing candidates from the current `candidates.json`.
- Source files (from OTHER_REPOS or assets/equipment) still exist on disk.
- No duplicate asset_names in the decision set.
- No target logical `asset_name` already exists anywhere below `assets/equipment/`
  (unless `--force`).
- In-repo sources (source_repo == "assets/equipment") require `--rename-existing` flag.

On success, the applier:

- Copies or moves SVGs into `assets/equipment/<behavior>/<asset_name>.svg` using
  the behavior category projected into `missing_targets.json` from object YAML.
- Runs normalization via `tools/normalize_svg_v3.py -i <target_file> --in-place`.
- Appends attribution rows to `docs/SVG_ATTRIBUTION.md` for CC BY sources.
- Prints a summary: "X assigned, Y deferred, Z ignored, N attribution rows appended".

### 5. Regenerate SVG globals

After applying decisions:

```bash
source source_me.sh && python3 pipeline/gen_svg_manifest.py
```

This regenerates the TypeScript constant exports that make the SVG assets available to the scene renderer.

### 6. Run gate test

Verify no new gaps:

```bash
pytest tests/test_object_asset_refs.py -v
```

## Browser compatibility

- **Firefox:** `file://` works natively.
- **Chrome / Safari / Edge:** use `python3 -m http.server` fallback (see step 2 above).

If the picker shows an error banner about fetch failures, you are likely using Chrome with `file://` - switch to the http.server approach.

## Manifest freshness

The three manifest builders are fast (< 1 second each). If you update `OTHER_REPOS/` (e.g., clone a newer version or add a new library), rebuild manifests before picking:

```bash
source source_me.sh && python3 tools/svg_picker/build_*.py
```

The applier re-reads `candidates.json` at apply time and verifies every source file still exists; if a manifest is stale, the applier will fail with a clear "rebuild manifest" message.

## localStorage session

Decisions are auto-saved to `localStorage['svg_picker.session.v1']` on every state change. Closing the tab or browser and returning later presents a "resume session" prompt. You can also click "Start fresh" to clear and begin anew.

Export always produces the same `decisions.json` shape, whether resumed or freshly started.

## Light/dark theme

Click the theme toggle (light / dark) in the top-right corner. Your choice is persisted via localStorage.

## Performance

- Candidate grid is virtualized: renders at most 100 tiles at a time (top 50 from ranked suggestions + up to 50 search hits).
- Search is client-side: substring match on filename and search-token corpus.
- All state changes rebuild the three panes; diffing is not implemented because the performance cost is negligible for ~74 targets and a small candidate grid.

## Preview tiles

- **Fixed square** (normalized across libraries).
- **Checkerboard background** (makes transparency visible).
- **Filename below** (line-clamped to 2 lines).
- **Match label** (color-coded: green = strong name match, yellow = partial, blue = same parent folder, purple = trusted existing asset, grey = weak).
- **Tooltip**: hover over match label to see the numeric score.

## Large side-by-side preview

Below the target context in the middle pane, the currently highlighted candidate renders at full size. This lets you compare the candidate against the target's visual states without leaving the keyboard flow.

## Examples

### Assign a strong name match

1. Select a target in the left pane (auto-focuses first unassigned).
2. Ranked candidates appear in the right pane (best match at top).
3. Press `Enter` to assign the highlighted (first) candidate.
4. Picker jumps to next unassigned.

### Batch defer all variant-looking in a family

1. Click a group header in the left pane to multi-select the whole family.
2. Click "Defer all X selected" in the action bar.
3. All targets in that family are marked defer.

### Search for a specific candidate

1. Press `/` to focus the search box.
2. Type a name or token (e.g., "pipette" or "p300").
3. Ranked list is replaced with search results.
4. Press `Escape` to clear focus, or clear the search box to return to ranked view.

### Hide a candidate from a family

1. Highlight a candidate that appears in many targets.
2. Press `X` to hide it from every target in the current state family.
3. The decision's `hidden_candidates` list is persisted; re-import restores the filter.

## Troubleshooting

**Picker shows error banner about fetch failures**
-> You are likely using Chrome with `file://`. Use the Python fallback server (step 2).

**Preview tiles show broken images**
-> Manifests are stale or `OTHER_REPOS/` has moved. Rebuild manifests and restart the picker.

**Session doesn't resume after reload**
-> Check browser console for errors. localStorage quota may be exceeded, or cookies/storage are disabled. Refresh and click "Start fresh".

**Keyboard shortcuts don't work**
-> Make sure the search box is not focused. Press `Escape` to blur it, or click elsewhere.

**Export button downloads blank file**
-> Browser may have blocked the download. Check console and try exporting again.

## License attribution

Attribution data lives in two files:

- [docs/THIRD_PARTY_ASSETS.md](../../docs/THIRD_PARTY_ASSETS.md): **handwritten** narrative provenance for curated assets (Servier, hand-integrated bioicons). Source of truth for curated entries; includes anchor-system docs and recoloring notes.
- [docs/SVG_ATTRIBUTION.md](../../docs/SVG_ATTRIBUTION.md): **derived** per-asset attribution table. The applier appends rows for picker-applied SVGs that carry `attribution_required: true` (typically CC BY). Each row: asset_name, source_repo, original_rel_path, license_tag, license_confidence, license_url.

The two-file split keeps curated narrative separate from machine-appended rows. Do not hand-edit `SVG_ATTRIBUTION.md`; edit `THIRD_PARTY_ASSETS.md` instead.

## Gate test

The gate test `tests/test_object_asset_refs.py` verifies that every `asset_name`
referenced in `content/objects/<kind>/*.yaml` resolves uniquely through the
recursive equipment registry.

On the first picking pass, the test runs in **soft-reporter mode**: it prints the current gap (list of missing asset_names) but exits 0 and does not block CI. The baseline gap is 74 missing slots; the test tracks this via `BASELINE_MISSING_COUNT=74`. If the count grows, the test fails loudly with an error message.

Run the gate test after each picking pass to track progress:

```bash
pytest tests/test_object_asset_refs.py -v
```

A follow-up patch will harden this to a strict `assert` once the picking pass closes most gaps (>= 90% filled).

## Decision states

Each target in the picker can be marked with one of three decision states:

- **assigned** - you found a suitable candidate and assigned it. The applier
  copies or moves this SVG into its projected `assets/equipment/<behavior>/`
  directory.
- **defer** - you want to review this target later. The picker saves it in decisions.json for a follow-up pass. The applier skips deferred decisions.
- **ignore_intentional** - you've reviewed this target and determined no available candidate is suitable (e.g., a custom vector is needed). You must provide a non-empty reason. The applier skips ignored decisions and records the reason for future reference.

All three states export to `decisions.json`. The applier processes `assigned` decisions, skips `defer` and `ignore_intentional`, and reports counts in the summary.

## Architecture

- `index.html` - minimal scaffold, three-pane grid layout, modals.
- `picker.css` - three-pane grid, tile normalization, light/dark theme, responsive layout.
- `picker.js` - vanilla ES2020+ state management, rendering, keyboard, localStorage, export.

No framework, no build step, no server code. Static HTML + JSON consumers.
