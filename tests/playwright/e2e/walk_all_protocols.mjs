// tests/playwright/e2e/walk_all_protocols.mjs
//
// All-protocols walker sweep runner.
//
// Enumerates every curriculum protocol under content/protocols/**/protocol.yaml
// and runs the existing single-protocol schema-driven walker
// (protocol_walkthrough_yaml.mjs) against each one. This script never
// reimplements the walker and adds no per-protocol branches; it only spawns the
// existing walker once per discovered protocol id and classifies the outcome
// from its exit code plus that run's own playthrough_report.json.
//
// Concurrency: protocols run through a bounded worker pool. The sweep starts ONE
// shared read-only static server on an OS-assigned port and injects its URL into
// every walker child (--server-url). A static serve is read-only, so all
// concurrent walks safely share the one server; per-walk isolation comes from
// each walker running as its own child process (fresh browser context, fresh
// gameState/localStorage) with its own results out-dir
// (test-results/walker/runs/<id>/). The server helper waits for the spawned
// child to report its actual bound port before this runner gives its URL to any
// walker. The default job count is min(8, max(1, cpus - 2)) -- a bound that
// leaves cores for each walker's own Chromium child; override it with --jobs N.
//
// Usage:
//   node tests/playwright/e2e/walk_all_protocols.mjs [--jobs N]
//
// Prerequisite: build dist/ first (npm run build), same as the single walker.
//
// Output:
//   test-results/walker/sweep_summary.json   - machine-readable worst-first summary
//   test-results/walker/reports/<id>.json    - per-protocol walker report, copied
//                                               out of that protocol's run dir so
//                                               downstream tooling reads a stable path
//   test-results/walker/runs/<id>/           - per-protocol walker out-dir
//                                               (report + screenshots), isolated
//                                               per run so parallel workers do not
//                                               overwrite each other

import { spawn } from "node:child_process";
import os from "node:os";
import fs from "node:fs";
import path from "node:path";

import { REPO_ROOT } from "../repo_root.mjs";
import {
  resolveSelfServePort,
  startOwnedStaticServer,
  stopOwnedStaticServer,
} from "./walker_server.mjs";

const CONTENT_DIR = path.join(REPO_ROOT, "content", "protocols");
const DIST_DIR = path.join(REPO_ROOT, "dist");
const WALKER_SCRIPT = path.join(
  REPO_ROOT,
  "tests",
  "playwright",
  "e2e",
  "protocol_walkthrough_yaml.mjs",
);
const RESULTS_DIR = path.join(REPO_ROOT, "test-results", "walker");
const REPORTS_DIR = path.join(RESULTS_DIR, "reports");
const RUNS_DIR = path.join(RESULTS_DIR, "runs");
const SUMMARY_PATH = path.join(RESULTS_DIR, "sweep_summary.json");

// Per-protocol wall-clock budget. Mirrors the single walker's own 10-minute
// RUN_BUDGET_MS with headroom for process spawn and teardown overhead.
const PER_PROTOCOL_TIMEOUT_MS = 660000;

//============================================
// Concurrency + color
//============================================

// Safe default worker count: leave a couple of cores for each walker's Chromium
// child (the shared static server is one process, not one-per-walk), cap at 8 so
// a big-core host does not spawn a browser storm, floor at 1 on tiny hosts.
function defaultJobCount() {
  const cpus = os.cpus().length;
  return Math.min(8, Math.max(1, cpus - 2));
}

function parseArgs() {
  const argv = process.argv.slice(2);
  const result = { jobs: defaultJobCount() };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--jobs" && i + 1 < argv.length) {
      const parsed = Number.parseInt(argv[i + 1], 10);
      if (!Number.isInteger(parsed) || parsed < 1) {
        console.error(`Invalid --jobs value '${argv[i + 1]}'. Expected a positive integer.`);
        process.exit(1);
      }
      result.jobs = parsed;
      i++;
    }
  }
  return result;
}

// Color is gated on an interactive TTY AND the absence of the NO_COLOR env var
// (https://no-color.org). When off, every line is plain text so piped/CI output
// and the JSON summary stay uncolored and parseable.
const USE_COLOR = Boolean(process.stdout.isTTY) && !("NO_COLOR" in process.env);
const ANSI = {
  reset: "\x1b[0m",
  green: "\x1b[32m",
  red: "\x1b[31m",
  yellow: "\x1b[33m",
};

// Strip SGR ANSI escape sequences (color/dim/reset) from a string. A walker
// child's failure reason can embed Playwright's own dim-styled locator-timeout
// text (e.g. "\x1b[2m  - waiting for locator(...)"); that formatting must never
// reach the reason column or the JSON summary, so file output stays plain and a
// piped sweep shows zero escape bytes. The sweep's own PASS/FAIL coloring is
// still gated separately on an interactive TTY.
// eslint-disable-next-line no-control-regex
const SGR_ANSI = /\x1b\[[0-9;]*m/g;
function stripAnsi(text) {
  if (typeof text !== "string") return text;
  return text.replace(SGR_ANSI, "");
}

function verdictColor(verdict) {
  if (verdict === "PASS") return ANSI.green;
  if (verdict === "FAIL" || verdict === "error") return ANSI.red;
  if (verdict === "unsupported_gesture") return ANSI.yellow;
  return "";
}

// Paint already-width-correct text (pad the visible string BEFORE calling this
// so column alignment accounts for the visible characters, not the escape
// bytes). A no-op when color is disabled.
function paintVerdict(text, verdict) {
  if (!USE_COLOR) return text;
  const color = verdictColor(verdict);
  if (color === "") return text;
  return `${color}${text}${ANSI.reset}`;
}

//============================================
// Discovery
//============================================

// Recursively find every protocol.yaml under content/protocols and return the
// sorted list of protocol ids (the parent directory name of each file, which
// matches the authored protocol_name field for every curriculum protocol).
export function discoverProtocolIds(contentDir) {
  const ids = [];
  walkForProtocolYaml(contentDir, ids);
  ids.sort();
  return ids;
}

function walkForProtocolYaml(dirPath, ids) {
  const entries = fs.readdirSync(dirPath, { withFileTypes: true });
  for (const entry of entries) {
    const entryPath = path.join(dirPath, entry.name);
    if (entry.isDirectory()) {
      walkForProtocolYaml(entryPath, ids);
    } else if (entry.isFile() && entry.name === "protocol.yaml") {
      ids.push(path.basename(dirPath));
    }
  }
}

//============================================
// Single-protocol run
//============================================

// Spawn the existing single-protocol walker for one protocol id and resolve
// with its exit code plus captured stdout/stderr. Never rejects on a nonzero
// exit code; the caller classifies pass/fail from the exit code plus report.
// serverUrl points every walker at the one shared server; outDir isolates this
// run's report + screenshots from every other concurrent walker. The walker
// child is a separate process, so its browser context, gameState, and
// localStorage are fully isolated even though the server is shared.
function runWalkerForProtocol(protocolId, serverUrl, outDir) {
  return new Promise((resolve) => {
    const startedAt = Date.now();
    const child = spawn(
      "node",
      [WALKER_SCRIPT, "--protocol", protocolId, "--server-url", serverUrl, "--out-dir", outDir],
      {
        cwd: REPO_ROOT,
        stdio: ["ignore", "pipe", "pipe"],
      },
    );

    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });

    let timedOut = false;
    const timer = setTimeout(() => {
      timedOut = true;
      child.kill("SIGKILL");
    }, PER_PROTOCOL_TIMEOUT_MS);

    child.on("error", (err) => {
      clearTimeout(timer);
      resolve({
        protocolId,
        exitCode: null,
        spawnError: err.message,
        timedOut: false,
        durationMs: Date.now() - startedAt,
        stdout,
        stderr,
      });
    });

    child.on("close", (exitCode) => {
      clearTimeout(timer);
      resolve({
        protocolId,
        exitCode,
        spawnError: null,
        timedOut,
        durationMs: Date.now() - startedAt,
        stdout,
        stderr,
      });
    });
  });
}

//============================================
// Verdict classification
//============================================

// Classify one run's outcome from its exit code plus the walker's own
// playthrough_report.json. Reads the report's failureReason field only to
// tell "unsupported_gesture" apart from other failures; this is the same
// classification string the single walker already throws (see
// protocol_walkthrough_yaml.mjs), so no new per-protocol logic is added.
export function classifyRun(runResult, report) {
  if (runResult.spawnError !== null) {
    return { verdict: "error", reason: `spawn_error: ${runResult.spawnError}` };
  }
  if (runResult.timedOut) {
    return { verdict: "error", reason: `timeout after ${PER_PROTOCOL_TIMEOUT_MS}ms` };
  }
  if (report === null) {
    return { verdict: "error", reason: "no playthrough_report.json produced" };
  }

  const failureReason = report.summary ? report.summary.failureReason : null;
  if (typeof failureReason === "string" && failureReason.startsWith("unsupported_gesture:")) {
    return { verdict: "unsupported_gesture", reason: failureReason };
  }
  if (runResult.exitCode === 0) {
    return { verdict: "PASS", reason: null };
  }
  const reason = failureReason !== null ? failureReason : `nonzero exit code ${runResult.exitCode}`;
  return { verdict: "FAIL", reason };
}

//============================================
// Report archiving
//============================================

// Copy this protocol's isolated playthrough_report.json into the stable
// reports/<id>.json location (the path downstream tooling and the register
// read), and return its parsed contents (or null if missing). Each run has its
// own out-dir, so no shared-file race exists; the copy just preserves the
// historical reports/ path.
function archiveReport(protocolId, outDir) {
  const runReportPath = path.join(outDir, "playthrough_report.json");
  if (!fs.existsSync(runReportPath)) {
    return null;
  }
  const text = fs.readFileSync(runReportPath, "utf-8");
  const report = JSON.parse(text);
  if (!fs.existsSync(REPORTS_DIR)) {
    fs.mkdirSync(REPORTS_DIR, { recursive: true });
  }
  const archivedPath = path.join(REPORTS_DIR, `${protocolId}.json`);
  fs.writeFileSync(archivedPath, text);
  return report;
}

//============================================
// Summary printing
//============================================

const VERDICT_RANK = { FAIL: 0, error: 0, unsupported_gesture: 1, PASS: 2 };

function printSummaryTable(results) {
  const sorted = results.slice().sort((a, b) => VERDICT_RANK[a.verdict] - VERDICT_RANK[b.verdict]);
  console.log("\n=== Walker sweep summary (worst first) ===");
  console.log("verdict              protocol_id                                duration  reason");
  for (const r of sorted) {
    // Pad the visible verdict to the column width FIRST, then paint, so the
    // invisible ANSI bytes never disturb column alignment.
    const verdictCol = paintVerdict(r.verdict.padEnd(20), r.verdict);
    const idCol = r.protocolId.padEnd(42);
    const durationCol = `${(r.durationMs / 1000).toFixed(1)}s`.padEnd(9);
    const reasonCol = r.reason !== null ? r.reason.slice(0, 120) : "";
    console.log(`${verdictCol} ${idCol} ${durationCol} ${reasonCol}`);
  }

  const counts = { PASS: 0, unsupported_gesture: 0, FAIL: 0, error: 0 };
  for (const r of results) {
    counts[r.verdict]++;
  }
  console.log(
    `\nTotals: PASS=${counts.PASS} unsupported_gesture=${counts.unsupported_gesture} ` +
      `FAIL=${counts.FAIL} error=${counts.error} (of ${results.length})`,
  );
}

//============================================
// Main
//============================================

// Run one protocol end to end: spawn the isolated walker, archive its report to
// the stable reports/<id>.json path, and classify the verdict. Returns the
// summary entry the sweep collects.
async function runOneProtocol(protocolId, serverUrl) {
  const outDir = path.join(RUNS_DIR, protocolId);
  const runResult = await runWalkerForProtocol(protocolId, serverUrl, outDir);
  const report = archiveReport(protocolId, outDir);
  const { verdict, reason } = classifyRun(runResult, report);
  return {
    protocolId,
    verdict,
    // Sanitize any embedded Playwright ANSI so the table and JSON stay plain.
    reason: stripAnsi(reason),
    exitCode: runResult.exitCode,
    durationMs: runResult.durationMs,
    reportPath: report !== null ? path.join(REPORTS_DIR, `${protocolId}.json`) : null,
  };
}

// Print one live line as a protocol FINISHES. Under concurrency these interleave
// in completion order, so each line stands alone with its verdict, id, and
// duration; the worst-first table at the end gives the ordered view.
function printLiveLine(entry, doneCount, total) {
  const verdictTag = paintVerdict(entry.verdict.padEnd(20), entry.verdict);
  const durationText = `${(entry.durationMs / 1000).toFixed(1)}s`;
  const counter = `[${String(doneCount).padStart(2)}/${total}]`;
  console.log(`${counter} ${verdictTag} ${entry.protocolId} (${durationText})`);
}

// Bounded worker pool. Every worker points its walker child at the one shared
// server (serverUrl); it pulls the next protocol id off the shared queue until
// the queue drains. queue.shift() is synchronous and JS is single-threaded, so
// no two workers ever claim the same id. Results are collected in completion
// order (the final table re-sorts them).
async function runPool(protocolIds, jobs, serverUrl) {
  const queue = protocolIds.slice();
  const total = protocolIds.length;
  const results = [];

  async function worker() {
    while (queue.length > 0) {
      const protocolId = queue.shift();
      if (protocolId === undefined) {
        return;
      }
      const entry = await runOneProtocol(protocolId, serverUrl);
      results.push(entry);
      printLiveLine(entry, results.length, total);
    }
  }

  const workerCount = Math.min(jobs, total);
  const workers = [];
  for (let i = 0; i < workerCount; i++) {
    workers.push(worker());
  }
  await Promise.all(workers);
  return results;
}

async function main() {
  const args = parseArgs();
  const protocolIds = discoverProtocolIds(CONTENT_DIR);
  if (protocolIds.length === 0) {
    throw new Error(`no protocol.yaml files found under ${CONTENT_DIR}`);
  }
  const jobs = Math.min(args.jobs, protocolIds.length);

  if (!fs.existsSync(RESULTS_DIR)) {
    fs.mkdirSync(RESULTS_DIR, { recursive: true });
  }
  if (!fs.existsSync(RUNS_DIR)) {
    fs.mkdirSync(RUNS_DIR, { recursive: true });
  }

  let results;
  let ownedServer = null;
  try {
    ownedServer = await startOwnedStaticServer({
      port: resolveSelfServePort(null),
      directory: DIST_DIR,
      cwd: REPO_ROOT,
    });
    console.log(
      `Discovered ${protocolIds.length} protocols under content/protocols/ ` +
        `(running ${jobs} at a time, one shared server ready on port ${ownedServer.port})`,
    );
    results = await runPool(protocolIds, jobs, ownedServer.baseUrl);
  } finally {
    if (ownedServer !== null) {
      await stopOwnedStaticServer(ownedServer.child);
    }
  }

  printSummaryTable(results);

  const summary = {
    timestamp: new Date().toISOString(),
    totalProtocols: results.length,
    jobs,
    results,
  };
  fs.writeFileSync(SUMMARY_PATH, JSON.stringify(summary, null, 2));
  console.log(`\nSweep summary written to ${SUMMARY_PATH}`);

  const hasFailure = results.some((r) => r.verdict === "FAIL" || r.verdict === "error");
  process.exitCode = hasFailure ? 1 : 0;
}

main().catch((err) => {
  console.error("Fatal error in sweep runner:", err);
  process.exit(1);
});
