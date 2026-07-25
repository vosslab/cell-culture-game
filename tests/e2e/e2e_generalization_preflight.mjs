// Lane D3: Pipeline preflight on all 6 D1 generalization scenes.
// For each emitted scene (every key in SCENES), run the pipeline with generated artifacts,
// capture diagnostics and pass counts, run structural guards, and emit a
// markdown report at docs/active_plans/reports/m2_generalization_preflight.md
//
// Run via: node --import tsx tests/e2e/e2e_generalization_preflight.mjs

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { runPipeline } from "../../src/scene_runtime/layout/index.ts";
import { runStructuralGuards } from "../../src/scene_runtime/renderer/structural_guards.ts";
import { SCENES } from "../../generated/scenes.ts";
import { OBJECT_LIBRARY } from "../../generated/object_library.ts";
import { ASSET_SPECS } from "../../generated/object_library.ts";

//============================================
// Helper utilities
//============================================

/**
 * @typedef {Object} PreflightResult
 * @property {string} scene_name
 * @property {number} diagnostics_count
 * @property {string[]} diagnostics_list
 * @property {number} passes_count
 * @property {number} final_count
 * @property {number[]} zones_shrunk_per_pass
 * @property {string} guard_verdict
 * @property {string | null} guard_error
 * @property {number} overlap_count
 * @property {number} zone_overflow_count
 */

function findRepoRoot() {
  let current = path.dirname(fileURLToPath(import.meta.url));
  while (current !== "/") {
    if (fs.existsSync(path.join(current, ".git"))) {
      return current;
    }
    current = path.dirname(current);
  }
  throw new Error("Could not find repo root");
}

const REPO_ROOT = findRepoRoot();

//============================================
// Main preflight logic
//============================================

function runPreflightOnScene(sceneName) {
  const result = {
    scene_name: sceneName,
    diagnostics_count: 0,
    diagnostics_list: [],
    passes_count: 0,
    final_count: 0,
    zones_shrunk_per_pass: [],
    guard_verdict: "PASS",
    guard_error: null,
    overlap_count: 0,
    zone_overflow_count: 0,
  };

  try {
    // Get the scene from generated index
    const scene = SCENES[sceneName];
    if (!scene) {
      result.guard_verdict = "FAIL";
      result.guard_error = `Scene "${sceneName}" not found in SCENES`;
      return result;
    }

    // Run the pipeline
    const pipelineResult = runPipeline(scene, {
      library: OBJECT_LIBRARY,
      assets: ASSET_SPECS,
    });

    // Capture diagnostics
    result.diagnostics_count = pipelineResult.diagnostics.length;
    result.diagnostics_list = pipelineResult.diagnostics.map((d) => {
      let msg = `${d.stage}/${d.severity}/${d.kind}`;
      if (d.placement_name) msg += ` [${d.placement_name}]`;
      if (d.object_name) msg += ` obj=${d.object_name}`;
      if (d.asset) msg += ` asset=${d.asset}`;
      return msg;
    });

    // Capture pass info
    result.passes_count = pipelineResult.passes.length;
    result.zones_shrunk_per_pass = pipelineResult.passes.map((p) => p.zones_shrunk_count || 0);

    // Capture final item count
    result.final_count = pipelineResult.final.length;

    // Count diagnostics by kind
    for (const d of pipelineResult.diagnostics) {
      if (d.kind === "item_overlap") {
        result.overlap_count++;
      }
      if (
        d.kind === "zone_overflow_negative_gap" ||
        d.kind === "tab_stop_overflow" ||
        d.kind === "item_escapes_zone_vertically"
      ) {
        result.zone_overflow_count++;
      }
    }

    // Run structural guards
    try {
      runStructuralGuards(pipelineResult.final, pipelineResult.scene);
    } catch (err) {
      result.guard_verdict = "FAIL";
      result.guard_error = err instanceof Error ? err.message : String(err);
    }
  } catch (err) {
    result.guard_verdict = "FAIL";
    result.guard_error = err instanceof Error ? err.message : String(err);
  }

  return result;
}

//============================================
// Report generation
//============================================

function generateMarkdownReport(results) {
  const lines = [];

  lines.push("# M2c generalization preflight report");
  lines.push("");
  lines.push(
    `Run at: ${new Date().toISOString().split("T")[0]} ${new Date().toISOString().split("T")[1].split(".")[0]} UTC`,
  );
  lines.push("");
  lines.push("## Scope");
  lines.push("");
  lines.push("Lane D3 runs the full layout pipeline on every emitted scene");
  lines.push("(all keys in SCENES from generated/scenes.ts). For each scene:");
  lines.push("");
  lines.push("- Parse and normalize the scene YAML");
  lines.push("- Resolve all objects to the object library");
  lines.push("- Resolve all assets to SVG_MANIFEST");
  lines.push("- Run the full convergence loop (up to MAX_LAYOUT_PASSES)");
  lines.push("- Run structural guards on final layout");
  lines.push("- Capture diagnostics, pass counts, and guard pass/fail verdict");
  lines.push("");
  lines.push("## Method");
  lines.push("");
  lines.push("Each preflight invokes:");
  lines.push("`runPipeline(scene, { library: OBJECT_LIBRARY, assets: ASSET_SPECS })`");
  lines.push("followed by `runStructuralGuards(result.final, result.scene)` to verify");
  lines.push("layout geometry before D4 attempts rendering.");
  lines.push("");
  lines.push("## Results: summary table");
  lines.push("");

  const tableHeader = [
    "scene",
    "diagnostics",
    "passes",
    "final_items",
    "guard_verdict",
    "overlap_count",
    "zone_overflow",
  ];
  const rows = results.map((r) => [
    r.scene_name,
    r.diagnostics_count.toString(),
    r.passes_count.toString(),
    r.final_count.toString(),
    r.guard_verdict === "PASS" ? "PASS" : `FAIL: ${r.guard_error}`,
    r.overlap_count.toString(),
    r.zone_overflow_count.toString(),
  ]);

  lines.push(`| ${tableHeader.join(" | ")} |`);
  lines.push(`| ${tableHeader.map(() => "---").join(" | ")} |`);
  for (const row of rows) {
    lines.push(`| ${row.join(" | ")} |`);
  }
  lines.push("");

  lines.push("## Per-scene detail");
  lines.push("");

  for (const r of results) {
    lines.push(`### ${r.scene_name}`);
    lines.push("");

    lines.push(`**Guard verdict:** ${r.guard_verdict}`);
    if (r.guard_error) {
      lines.push(`**Guard failure message:** ${r.guard_error}`);
    }
    lines.push("");

    lines.push(
      `**Diagnostics:** ${r.diagnostics_count} (passes: ${r.passes_count}, final items: ${r.final_count})`,
    );
    if (r.diagnostics_count === 0) {
      lines.push("(none)");
    } else {
      for (const diag of r.diagnostics_list) {
        lines.push(`- ${diag}`);
      }
    }
    lines.push("");

    if (r.zones_shrunk_per_pass.length > 0) {
      lines.push(`**Zones shrunk per pass:** ${r.zones_shrunk_per_pass.join(", ")}`);
    } else {
      lines.push("**Zones shrunk per pass:** (no shrinking occurred)");
    }
    lines.push("");

    lines.push(`**Overlap count:** ${r.overlap_count}`);
    lines.push(`**Zone overflow count:** ${r.zone_overflow_count}`);
    lines.push("");
  }

  lines.push("## Summary and next steps");
  lines.push("");

  const passCount = results.filter((r) => r.guard_verdict === "PASS").length;
  lines.push(`**D4-ready (preflight pass):** ${passCount} / ${results.length}`);
  lines.push("");

  const passingScenes = results.filter((r) => r.guard_verdict === "PASS");
  const failingScenes = results.filter((r) => r.guard_verdict !== "PASS");

  if (passingScenes.length > 0) {
    lines.push("### Preflight-passing scenes (ready for D4 render):");
    lines.push("");
    for (const r of passingScenes) {
      lines.push(`- **${r.scene_name}**: ${r.diagnostics_count} diagnostics`);
    }
    lines.push("");
  }

  if (failingScenes.length > 0) {
    lines.push("### Preflight-failing scenes (needs fix before D4):");
    lines.push("");
    for (const r of failingScenes) {
      lines.push(`- **${r.scene_name}**: ${r.guard_error}`);
    }
    lines.push("");
  }

  lines.push("Scenes that pass structural guards proceed to D4 rendering.");
  lines.push("Scenes that fail are classified per D5 taxonomy.");
  lines.push("");

  return lines.join("\n");
}

//============================================
// Main entry point
//============================================

function main() {
  console.log("D3: Pipeline preflight on generalization scenes");
  // SCENE_ALLOWLIST was removed; every emitted base scene now ships in SCENES.
  const sceneNames = Object.keys(SCENES).sort();
  console.log(`Testing scenes: ${sceneNames.join(", ")}`);
  console.log("");

  const results = [];
  for (const sceneName of sceneNames) {
    console.log(`Preflighting ${sceneName}...`);
    const result = runPreflightOnScene(sceneName);
    results.push(result);
    console.log(
      `  -> ${result.guard_verdict} (${result.diagnostics_count} diagnostics, ${result.passes_count} passes)`,
    );
  }

  console.log("");
  console.log("Generating report...");

  const report = generateMarkdownReport(results);

  const reportPath = path.join(
    REPO_ROOT,
    "docs/active_plans/reports/m2_generalization_preflight.md",
  );

  // Ensure directory exists
  const reportDir = path.dirname(reportPath);
  if (!fs.existsSync(reportDir)) {
    fs.mkdirSync(reportDir, { recursive: true });
  }

  fs.writeFileSync(reportPath, report, "utf8");

  console.log(`Report written to: ${reportPath}`);
  console.log("");

  const passCount = results.filter((r) => r.guard_verdict === "PASS").length;
  console.log(`D4-ready (preflight pass): ${passCount} / ${results.length}`);

  if (passCount === results.length) {
    console.log("All scenes ready for D4 rendering.");
    return;
  }
  console.error(`${results.length - passCount} scene(s) need fixes before D4.`);
  process.exitCode = 1;
}

main();
