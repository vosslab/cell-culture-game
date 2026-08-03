# AI visual-polish review: usage and calibration set

Decision record and usage note for the Claude visual-polish reviewer
(`devel/ai_polish_review.mjs`, M2 / WP-VISAI1). The tool is report-only: it
records structured verdicts and gates nothing. It is not part of the
deterministic build and must never break a build or a local test.

## What the tool does

- Renders canonical 16:9 before/after PNG screenshots per scene by invoking the
  read-only renderer `tools/scene_to_png.mjs` (it does not edit `tools/`).
- Packages the before/after images, geometry-free scene metadata (the manifest
  entry: scene name, outcome, expected placement names), and a fixed
  visual-polish rubric into one Claude Messages API request per scene.
- Requests a structured JSON verdict and saves the combined report beside the
  scorecard report at `docs/active_plans/reports/ai_polish_review.json`.

## Model and credentials

- Model: set by the `CLAUDE_VISION_MODEL` environment variable. Default is
  `claude-opus-4-8` (Claude's strongest available vision-capable model). A
  model-name change is a config edit only; it does not require a code change and
  does not break the tool.
- Credentials: the standard `ANTHROPIC_API_KEY` environment variable. The tool
  uses raw HTTPS (`fetch`) against the Messages API, so it adds no npm
  dependency and the credentials-absent path needs no install.

## Build-safe fallback (report-only, gates nothing)

- When `ANTHROPIC_API_KEY` is absent, or the API call fails, or the model
  returns a malformed verdict, the tool emits a `visual_review_unavailable`
  result for that scene with `review_required: true` (routing to human review)
  and continues.
- The tool always exits `0`, even when every scene routed to
  `visual_review_unavailable`. Local, unit, and build tests run without any live
  Claude call.

## Usage

Run from the repo root (so Node resolves `playwright` from `node_modules`):

```sh
# Build-safe proof: render + assemble payload, no network, exits 0.
node devel/ai_polish_review.mjs --calibration --dry-run --reuse-pngs

# Inspect the exact request that would be sent (base64 image data elided).
node devel/ai_polish_review.mjs --scene staining_bench --dry-run --show-payload

# Live review of one scene (requires ANTHROPIC_API_KEY).
node devel/ai_polish_review.mjs --scene staining_bench

# Live review of the calibration set.
node devel/ai_polish_review.mjs --calibration
```

Flags: `--scene <name>`, `--calibration`, `--dry-run` (no network),
`--show-payload`, `--reuse-pngs` (reuse existing PNGs under
`test-results/scenes/`), `--out <path>` (default report path above).

Note: M2 has one production layout path, so the "before" and "after" image
slots currently carry the same render. The payload keeps two labelled slots so
the same request shape works once a pre-change baseline render is supplied.

## Output JSON schema (per scene)

A reviewed scene records:

```json
{
  "scene": "staining_bench",
  "status": "reviewed",
  "overall_polish": 82,
  "primary_object_prominence": 4,
  "label_readability": 3,
  "label_attachment": 2,
  "object_spacing": 3,
  "physical_plausibility": 4,
  "scientific_asset_preservation": 5,
  "confidence": "medium",
  "blocking_findings": ["Two labels appear detached from their intended objects."],
  "review_required": true,
  "role": "named"
}
```

Each rubric item is scored 1-5 (5 best); `overall_polish` is 0-100; `confidence`
is `low | medium | high`. An unavailable scene records instead:

```json
{
  "scene": "staining_bench",
  "status": "visual_review_unavailable",
  "reason": "ANTHROPIC_API_KEY not set",
  "review_required": true,
  "role": "named"
}
```

## Escalation gate (report-only first)

The reviewer runs report-only until calibration shows stable, useful results.
`review_required` is set when any of these hold:

- the model returns `review_required: true`,
- `confidence` is `low`,
- `blocking_findings` is non-empty, or
- the scene is `visual_review_unavailable`.

Gating is first on confidence plus blocking findings. A numeric polish-score
cutoff is deferred until calibration data shows stable score distributions; it
is not hand-picked.

## Calibration set

8 to 12 scenes spanning known-bad (the eight named scenes from the plan's
evidence table) and known-good (positive controls). Fill the human label and
agreement columns after a live run.

| scene | role | known issue / control | human label | AI overall | AI confidence | blocking findings | agreement | promotion rec |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| cell_counter_basic | named | tiny primary object | | | | | | |
| staining_bench | named | label overlaps | | | | | | |
| sample_prep_bench | named | vertical overflow | | | | | | |
| hood_basic | named | vertical overflow | | | | | | |
| seeding_workspace | named | residual label collisions | | | | | | |
| electrophoresis_bench | named | layout drift | | | | | | |
| heat_block_bench | named | layout drift | | | | | | |
| passage_hood_detachment_microscope_view | named | layout drift | | | | | | |
| bench_basic | positive_control | stable bench, no known defect | | | | | | |
| plate_workspace | positive_control | stable plate workspace | | | | | | |
| microscope_basic | positive_control | stable microscope view | | | | | | |

The positive controls are stable scenes with no known layout defect, picked from
the current scene manifest. Adjust the lists in `devel/ai_polish_review.mjs`
(`NAMED_SCENES`, `POSITIVE_CONTROL_SCENES`) if the manifest changes.

## Calibration cadence

Run when the reviewer is introduced, then re-run after milestones that change
visual output (M4, M5, M6), whenever the vision model or the rubric changes, and
before promoting the reviewer from report-only to a gate.

## Relocation follow-up

The plan files this tool under `tools/ai_polish_review.mjs`. It currently lives
in `devel/` because `tools/` is being actively edited for a v3 SVG normalizer.
Move it to `tools/` with `git mv` once that work lands, and update
`package.json` and `docs/FILE_STRUCTURE.md` in the same patch.
