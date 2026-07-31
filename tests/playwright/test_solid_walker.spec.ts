// Focused acceptance that the Solid protocol host completes one protocol
// through the canonical learner-visible walker. This intentionally shares the
// same driver as the full protocol sweep: Playwright actionability-checked
// clicks, visible adjustment cues, painted affordance proof, wrong-sibling
// rejection, and declared-state verification. No page-side element.click(),
// internal emitter dispatch, answer projection, or protocol-specific branch.

import path from "node:path";

import { test, expect } from "@playwright/test";

import { runProtocolWalk } from "./e2e/helper_walker.mjs";
import { REPO_ROOT } from "./repo_root.mjs";

const PROTOCOL = "sdspage_heat_denature_samples";
const RESULTS_DIR = path.join(REPO_ROOT, "test-results", "solid_walker", PROTOCOL);

test("solid walker: SDS heat denaturation completes through honest visible UI", async ({
  page,
  baseURL,
}) => {
  expect(baseURL, "Playwright config must provide the built application URL").toBeTruthy();

  const outcome = await runProtocolWalk(page, {
    protocol: PROTOCOL,
    baseUrl: baseURL as string,
    resultsDir: RESULTS_DIR,
  });

  expect(outcome.passed, `visible walk failed:\n${outcome.diagnostics}`).toBe(true);
  expect(
    outcome.checkpointManifest.length,
    "the walk must record visible target proof",
  ).toBeGreaterThan(0);
  expect(
    outcome.checkpointManifestValid,
    `checkpoint manifest failed integrity validation:\n${outcome.diagnostics}`,
  ).toBe(true);
});
