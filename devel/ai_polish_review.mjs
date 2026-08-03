#!/usr/bin/env node

// devel/ai_polish_review.mjs
//
// M2 / WP-VISAI1: Claude visual-polish reviewer (report-only).
//
// RELOCATION NOTE: the plan files this tool under tools/ai_polish_review.mjs.
// It lives in devel/ for now because the user is actively editing tools/ for a
// v3 SVG normalizer; move it to tools/ (via `git mv`) once that work lands, and
// update package.json + docs/FILE_STRUCTURE.md in the same patch.
//
// What it does:
//   - Captures (or reuses) canonical 16:9 before/after PNG screenshots per scene
//     by invoking the existing read-only renderer tools/scene_to_png.mjs.
//   - Sends the before/after images plus scene metadata and a fixed visual-polish
//     rubric to Claude's vision-capable model.
//   - Requests a structured JSON verdict scoring each rubric item, plus an
//     overall_polish score, a confidence band, blocking_findings, and a
//     review_required flag.
//   - Saves the structured JSON report beside the scorecard report under
//     docs/active_plans/reports/.
//
// REPORT-ONLY: this tool records results and gates NOTHING. It is not part of
// the deterministic build (build_github_pages.sh / check_codebase.sh) and must
// never break a build or a local test. On missing credentials or any API
// failure it emits a `visual_review_unavailable` result per scene (routing to
// human review) and exits 0.
//
// Build-safe by design: local, unit, and build tests run WITHOUT any live Claude
// call. Use --dry-run to exercise the full packaging path (render + payload
// assembly) with no network request; the report then records
// `visual_review_unavailable` for every scene.
//
// Usage (bare node, run from repo root):
//   node devel/ai_polish_review.mjs --calibration            # the 8 named + positive-control scenes
//   node devel/ai_polish_review.mjs --scene staining_bench   # one scene
//   node devel/ai_polish_review.mjs --calibration --dry-run  # no network; show payload shape
//   node devel/ai_polish_review.mjs --calibration --show-payload  # print the request that would be sent
//
// Flags:
//   --scene <name>     Review one scene (before == after; single render).
//   --calibration      Review the calibration set (named scenes + positive controls).
//   --dry-run          Render + assemble payload but DO NOT call Claude. Emits
//                      visual_review_unavailable for every scene. Build-safe proof.
//   --show-payload     Print the assembled request payload (model, image-block
//                      shapes with base64 elided, rubric prompt) to stderr.
//   --reuse-pngs       Do not re-render; reuse existing PNGs under test-results/scenes/.
//   --out <path>       Output report path (default docs/active_plans/reports/ai_polish_review.json).
//
// Credentials / model:
//   ANTHROPIC_API_KEY      Standard Anthropic credential. Absent -> unavailable.
//   CLAUDE_VISION_MODEL    Vision-capable model id. Default DEFAULT_VISION_MODEL
//                          below (Claude's strongest available vision model). A
//                          model-name change here must not break the tool.

import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

//============================================
// Paths and constants
//============================================

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, "..");

const SCENE_TO_PNG = path.join(REPO_ROOT, "tools", "scene_to_png.mjs");
const MANIFEST_PATH = path.join(REPO_ROOT, "generated", "scene_manifest.json");
const PNG_DIR = path.join(REPO_ROOT, "test-results", "scenes");
const DEFAULT_REPORT_PATH = path.join(
  REPO_ROOT,
  "docs",
  "active_plans",
  "reports",
  "ai_polish_review.json",
);

// Strongest available vision-capable Claude model. Overridable via
// CLAUDE_VISION_MODEL so a model-name change does not require a code edit.
const DEFAULT_VISION_MODEL = "claude-opus-4-8";

const ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages";
const ANTHROPIC_VERSION = "2023-06-01";
// Request a bounded, JSON-only response. The verdict is small; no streaming.
const MAX_TOKENS = 1024;
// Single network attempt per scene; on any failure we route to human review.
const REQUEST_TIMEOUT_MS = 60000;

// The eight named scenes from the plan's required evidence table, in order, plus
// 2-4 already-acceptable positive controls. Calibration spans known-bad (named)
// and known-good (controls) layouts so the human labels can be compared against
// the AI scores. Positive controls are picked from stable benches with no known
// layout defect; adjust here if the manifest changes.
const NAMED_SCENES = [
  "cell_counter_basic",
  "staining_bench",
  "sample_prep_bench",
  "hood_basic",
  "seeding_workspace",
  "electrophoresis_bench",
  "heat_block_bench",
  "passage_hood_detachment_microscope_view",
];
const POSITIVE_CONTROL_SCENES = ["bench_basic", "plate_workspace", "microscope_basic"];

//============================================
// Fixed visual-polish rubric (from the plan)
//============================================

// Each rubric item is scored 1-5 (5 best). The keys here are the JSON fields the
// model must return; the text is the human-readable criterion shown to the model.
const RUBRIC_ITEMS = [
  ["primary_object_prominence", "The primary teaching object is visually prominent."],
  ["label_readability", "Labels are legible and read clearly against their background."],
  ["label_attachment", "Labels point near their intended objects and read attached, not detached."],
  ["object_spacing", "Objects have comfortable spacing without looking artificially scattered."],
  ["physical_plausibility", "The bench layout looks physically plausible."],
  [
    "scientific_asset_preservation",
    "Labels and objects preserve scientific meaning; every scientific asset is " +
      "fully shown, with no cropping, misleading overlap, or hidden important object.",
  ],
];

//============================================
// CLI argument parser
//============================================

function parse_args(argv) {
  const args = {
    scene: null,
    calibration: false,
    dry_run: false,
    show_payload: false,
    reuse_pngs: false,
    out: DEFAULT_REPORT_PATH,
  };

  let i = 2;
  while (i < argv.length) {
    const tok = argv[i];
    if (tok === "--scene") {
      args.scene = argv[++i];
    } else if (tok === "--calibration") {
      args.calibration = true;
    } else if (tok === "--dry-run") {
      args.dry_run = true;
    } else if (tok === "--show-payload") {
      args.show_payload = true;
    } else if (tok === "--reuse-pngs") {
      args.reuse_pngs = true;
    } else if (tok === "--out") {
      args.out = path.resolve(argv[++i]);
    } else {
      throw new Error(`Unknown argument: ${tok}`);
    }
    i++;
  }

  if (!args.scene && !args.calibration) {
    throw new Error("Specify --scene <name> or --calibration");
  }
  if (args.scene && args.calibration) {
    throw new Error("--scene and --calibration are mutually exclusive");
  }

  return args;
}

//============================================
// Scene metadata from the manifest
//============================================

// Reads the per-scene manifest entry for the scene-metadata block we attach to
// the Claude request. Returns a minimal, geometry-free summary so the model
// knows what the scene is supposed to contain. Returns null when absent.
function read_scene_metadata(scene_name) {
  if (!fs.existsSync(MANIFEST_PATH)) {
    return null;
  }
  const parsed = JSON.parse(fs.readFileSync(MANIFEST_PATH, "utf8"));
  const entry = parsed.scenes.find((s) => s.name === scene_name);
  if (!entry) {
    return null;
  }
  return {
    scene: entry.name,
    outcome: entry.outcome,
    source_placement_count: entry.source_placement_count ?? null,
    source_placement_names: entry.source_placement_names ?? [],
  };
}

//============================================
// Rendering (read-only invocation of scene_to_png.mjs)
//============================================

// Renders a single scene to a canonical 16:9 PNG by invoking the existing
// read-only renderer. Does not edit tools/. Returns the PNG path, or null if the
// render failed. The 16:9 viewport (1920x1080) matches the canonical scene size.
function render_scene_png(scene_name) {
  const result = spawnSync(
    process.execPath,
    [SCENE_TO_PNG, "--scene", scene_name, "--png", "--viewport", "1920x1080"],
    { cwd: REPO_ROOT, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] },
  );
  const png_path = path.join(PNG_DIR, `${scene_name}.png`);
  if (result.status !== 0 || !fs.existsSync(png_path)) {
    const detail = (result.stderr || result.stdout || "").trim().split("\n").slice(-3).join(" | ");
    console.warn(`  render failed for ${scene_name}: ${detail || "no PNG produced"}`);
    return null;
  }
  return png_path;
}

// Resolves the before/after PNG paths for a scene. M2 has a single production
// layout path, so "before" and "after" are the same rendered image here; the
// payload still carries two labelled image slots so the same shape works once a
// pre-change baseline image is supplied. Returns { before, after } paths or null
// if no usable PNG is available.
function resolve_scene_pngs(scene_name, reuse_pngs) {
  const existing = path.join(PNG_DIR, `${scene_name}.png`);
  const png_path = reuse_pngs && fs.existsSync(existing) ? existing : render_scene_png(scene_name);
  if (!png_path) {
    return null;
  }
  // Single-render mode: the after image is the current layout; before mirrors it
  // until a separate baseline render is wired in.
  return { before: png_path, after: png_path };
}

//============================================
// Request payload assembly
//============================================

// Builds the rubric prompt text shown to the model. The model is told to score
// each item 1-5, give an overall_polish 0-100, a confidence band, blocking
// findings, and whether human review is required.
function build_rubric_prompt(metadata) {
  const lines = [];
  lines.push(
    "You are a visual-polish reviewer for a virtual lab scene. Two screenshots " +
      "follow: a BEFORE layout and an AFTER layout of the same scene. Judge the " +
      "AFTER layout against the fixed rubric below. Use the BEFORE image only as " +
      "context for what changed.",
  );
  lines.push("");
  lines.push("Scene metadata (geometry-free; names of expected objects):");
  lines.push(JSON.stringify(metadata, null, 2));
  lines.push("");
  lines.push("Rubric (score each 1-5, where 5 is best):");
  for (const [key, text] of RUBRIC_ITEMS) {
    lines.push(`- ${key}: ${text}`);
  }
  lines.push("");
  lines.push(
    "Also judge: the scene reads uncrowded unless crowding is pedagogically " +
      "intended, and important objects stay above pedagogical-usefulness size.",
  );
  lines.push("");
  lines.push(
    "Return ONLY a single JSON object (no prose, no code fences) with exactly " + "these keys:",
  );
  lines.push(
    '{"scene": string, "overall_polish": integer 0-100, ' +
      RUBRIC_ITEMS.map(([k]) => `"${k}": integer 1-5`).join(", ") +
      ', "confidence": "low" | "medium" | "high", ' +
      '"blocking_findings": array of short strings (empty if none), ' +
      '"review_required": boolean}.',
  );
  lines.push(
    "Set review_required to true when confidence is low, when any scientific " +
      "asset is cropped/hidden/misrepresented, when the primary object is not " +
      "prominent, or when labels read detached from their objects.",
  );
  const prompt = lines.join("\n");
  return prompt;
}

// Reads a PNG and returns a base64 image content block for the Messages API.
function image_block(png_path) {
  const data = fs.readFileSync(png_path).toString("base64");
  const block = {
    type: "image",
    source: { type: "base64", media_type: "image/png", data },
  };
  return block;
}

// Assembles the full Messages API request body for one scene. The content is a
// labelled BEFORE image, a labelled AFTER image, and the rubric prompt text.
function build_request_body(model, scene_name, pngs, metadata) {
  const content = [
    { type: "text", text: "BEFORE layout:" },
    image_block(pngs.before),
    { type: "text", text: "AFTER layout:" },
    image_block(pngs.after),
    { type: "text", text: build_rubric_prompt(metadata) },
  ];
  const body = {
    model,
    max_tokens: MAX_TOKENS,
    messages: [{ role: "user", content }],
  };
  return body;
}

// Produces a redacted copy of a request body for --show-payload: image base64 is
// replaced with a length marker so the structure is visible without dumping
// megabytes of pixels.
function redact_body_for_display(body) {
  const clone = {
    model: body.model,
    max_tokens: body.max_tokens,
    messages: body.messages.map((m) => ({
      role: m.role,
      content: m.content.map((block) => {
        if (block.type === "image") {
          return {
            type: "image",
            source: {
              type: block.source.type,
              media_type: block.source.media_type,
              data: `<base64 ${block.source.data.length} chars elided>`,
            },
          };
        }
        return block;
      }),
    })),
  };
  return clone;
}

//============================================
// Result shapes
//============================================

// Builds the visual_review_unavailable result for a scene. This is the
// build-safe fallback that routes to human review; gates nothing.
function unavailable_result(scene_name, reason) {
  const result = {
    scene: scene_name,
    status: "visual_review_unavailable",
    reason,
    review_required: true,
  };
  return result;
}

// Validates and normalizes the model's JSON verdict for a scene. On any shape
// problem we fall back to visual_review_unavailable so a malformed verdict never
// looks like a real score. Returns a result object.
function normalize_verdict(scene_name, raw_text) {
  let parsed;
  try {
    // Strip an accidental code fence if the model added one.
    const cleaned = raw_text
      .trim()
      .replace(/^```(?:json)?/, "")
      .replace(/```$/, "")
      .trim();
    parsed = JSON.parse(cleaned);
  } catch {
    return unavailable_result(scene_name, "model returned non-JSON verdict");
  }
  // Confidence and blocking findings drive the report-only escalation flag.
  const confidence =
    parsed.confidence === "low" || parsed.confidence === "medium" || parsed.confidence === "high"
      ? parsed.confidence
      : "low";
  const blocking_findings = Array.isArray(parsed.blocking_findings)
    ? parsed.blocking_findings.filter((f) => typeof f === "string")
    : [];
  // Gate first on confidence + blocking findings (numeric cutoffs deferred to
  // calibration). review_required is true if the model said so, or if confidence
  // is low, or if any blocking finding is present.
  const review_required =
    parsed.review_required === true || confidence === "low" || blocking_findings.length > 0;
  const result = {
    scene: scene_name,
    status: "reviewed",
    overall_polish: typeof parsed.overall_polish === "number" ? parsed.overall_polish : null,
    confidence,
    blocking_findings,
    review_required,
  };
  for (const [key] of RUBRIC_ITEMS) {
    result[key] = typeof parsed[key] === "number" ? parsed[key] : null;
  }
  return result;
}

//============================================
// Claude call (raw fetch; no SDK dependency)
//============================================

// Sends one assembled request to the Messages API and returns the model's text.
// Throws on any non-2xx or network error; the caller routes that to
// visual_review_unavailable. Never called in --dry-run mode.
async function call_claude(api_key, body) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const resp = await fetch(ANTHROPIC_API_URL, {
      method: "POST",
      headers: {
        "x-api-key": api_key,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
      },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    if (!resp.ok) {
      const detail = await resp.text();
      throw new Error(`HTTP ${resp.status}: ${detail.slice(0, 300)}`);
    }
    const json = await resp.json();
    // content is a list of blocks; pull the first text block.
    const textBlock = (json.content ?? []).find((b) => b.type === "text");
    if (!textBlock) {
      throw new Error("response had no text block");
    }
    return textBlock.text;
  } finally {
    clearTimeout(timer);
  }
}

//============================================
// Per-scene review
//============================================

// Reviews one scene end-to-end: render -> package -> (optionally) call Claude ->
// normalize. Returns a result object. Never throws; all failure modes route to
// visual_review_unavailable so the run stays green.
async function review_scene(scene_name, args, api_key, model) {
  const metadata = read_scene_metadata(scene_name) ?? { scene: scene_name };

  const pngs = resolve_scene_pngs(scene_name, args.reuse_pngs);
  if (!pngs) {
    return unavailable_result(scene_name, "no screenshot available (render failed)");
  }

  const body = build_request_body(model, scene_name, pngs, metadata);

  if (args.show_payload) {
    console.error(`\n--- request payload for ${scene_name} ---`);
    console.error(JSON.stringify(redact_body_for_display(body), null, 2));
  }

  // Build-safe path: no credentials, or dry-run -> never touch the network.
  if (args.dry_run) {
    return unavailable_result(scene_name, "dry-run: no Claude call made");
  }
  if (!api_key) {
    return unavailable_result(scene_name, "ANTHROPIC_API_KEY not set");
  }

  let text;
  try {
    text = await call_claude(api_key, body);
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return unavailable_result(scene_name, `Claude API failure: ${msg}`);
  }
  return normalize_verdict(scene_name, text);
}

//============================================
// Scene-list resolution
//============================================

function resolve_scene_list(args) {
  if (args.scene) {
    return [{ scene: args.scene, role: "named" }];
  }
  const list = [];
  for (const name of NAMED_SCENES) {
    list.push({ scene: name, role: "named" });
  }
  for (const name of POSITIVE_CONTROL_SCENES) {
    list.push({ scene: name, role: "positive_control" });
  }
  return list;
}

//============================================
// Report writer
//============================================

function write_report(out_path, report) {
  fs.mkdirSync(path.dirname(out_path), { recursive: true });
  fs.writeFileSync(out_path, JSON.stringify(report, null, 2));
}

//============================================
// Main
//============================================

async function main() {
  let args;
  try {
    args = parse_args(process.argv);
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    console.error(`Usage error: ${msg}`);
    console.error(
      "Usage: node devel/ai_polish_review.mjs --scene <name> | --calibration [options]",
    );
    process.exit(1);
  }

  const api_key = process.env.ANTHROPIC_API_KEY ?? null;
  const model = process.env.CLAUDE_VISION_MODEL || DEFAULT_VISION_MODEL;

  const credentials_present = Boolean(api_key) && !args.dry_run;
  console.log("AI visual-polish reviewer (report-only; gates nothing)");
  console.log(`  model:        ${model}`);
  console.log(`  mode:         ${args.dry_run ? "dry-run (no network)" : "live"}`);
  console.log(`  credentials:  ${api_key ? "present" : "ABSENT -> visual_review_unavailable"}`);

  const targets = resolve_scene_list(args);
  const scenes = [];
  let reviewed = 0;
  let unavailable = 0;
  let review_required = 0;

  for (const target of targets) {
    console.log(`\nreviewing ${target.scene} (${target.role})`);
    const result = await review_scene(
      target.scene,
      args,
      credentials_present ? api_key : null,
      model,
    );
    result.role = target.role;
    scenes.push(result);
    if (result.status === "reviewed") {
      reviewed++;
      if (result.review_required) review_required++;
      console.log(
        `  -> overall ${result.overall_polish}, confidence ${result.confidence}, ` +
          `review_required ${result.review_required}` +
          (result.blocking_findings.length
            ? `, blocking: ${result.blocking_findings.join("; ")}`
            : ""),
      );
    } else {
      unavailable++;
      if (result.review_required) review_required++;
      console.log(`  -> visual_review_unavailable: ${result.reason}`);
    }
  }

  const report = {
    generated_at: new Date().toISOString(),
    tool: "devel/ai_polish_review.mjs",
    report_only: true,
    gates_nothing: true,
    model,
    dry_run: args.dry_run,
    credentials_present: Boolean(api_key),
    rubric_items: RUBRIC_ITEMS.map(([key, text]) => ({ key, text })),
    calibration_note:
      "Compare each scene's AI scores against the human calibration label in " +
      "docs/archive/decisions/ai_polish_review_calibration.md. Promotion to a " +
      "gate is deferred until calibration shows stable, useful results.",
    summary: {
      scene_count: scenes.length,
      reviewed,
      visual_review_unavailable: unavailable,
      review_required,
    },
    scenes,
  };

  write_report(args.out, report);
  console.log(`\nReport written to ${args.out}`);
  console.log(
    `  reviewed ${reviewed}, unavailable ${unavailable}, review_required ${review_required}`,
  );

  // Report-only: ALWAYS exit 0. Never break a build or local test, even when
  // every scene routed to visual_review_unavailable.
  process.exit(0);
}

main().catch((err) => {
  // A thrown error here would still be a tool bug, but it must not look like a
  // gating failure. Report it, write nothing, and exit 0 to stay build-safe.
  console.error("ai_polish_review unexpected error (report-only, exiting 0):", err);
  process.exit(0);
});
