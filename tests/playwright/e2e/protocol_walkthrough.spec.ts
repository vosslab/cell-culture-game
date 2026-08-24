// tests/playwright/e2e/protocol_walkthrough.spec.ts
//
// Runner-model acceptance walker sweep. This is the hard acceptance spine for
// PRIMARY_CONTRACT.md item 4: a mini-protocol is complete only when the visible
// interaction works. It emits ONE test() per curriculum protocol, so Playwright's
// native workers parallelize the sweep, and each test drives that protocol end to
// end through the SAME visible-UI walk engine the legacy CLI walker used
// (helper_walker.mjs -> walker_helpers.mjs). Real visible clicks / fill+commits
// only; NO internal-API progress; the structured material-area oracle runs around
// every material-writing interaction; screenshots land under test-results/.
//
// Convergence away from the library model (Phase 3):
//   - Discovery: helper_protocol_discovery.mjs enumerates content/protocols/**/
//     protocol.yaml (extracted so the spec does not import walk_all_protocols.mjs,
//     whose top-level main() would launch the old sweep on import).
//   - Server: the playwright.config.ts webServer block owns ONE built-and-served
//     dist/ for every worker. The custom CLI server-spawn/--server-url injection
//     and the bounded --jobs worker pool are REMOVED here, superseded by
//     the config webServer + Playwright workers. Each test navigates via baseURL.
//   - Honesty: a protocol that does not complete through visible UI FAILS its
//     test via expect(). There is no expected-failure registry: every discovered
//     curriculum protocol is part of the same acceptance contract.
//
// walk_all_protocols.mjs and protocol_walkthrough_yaml.mjs remain in place for
// Phase 4 removal; this spec is self-sufficient and never shells out to them.

import path from "node:path";

import { test, expect } from "@playwright/test";

import { REPO_ROOT } from "../repo_root.mjs";
import { PROTOCOLS } from "../../../generated/protocols.js";
import { discoverProtocolIds } from "./helper_protocol_discovery.mjs";
import { runProtocolWalk } from "./helper_walker.mjs";

// Per-protocol wall-clock budget for one walk. Generous headroom over a typical
// multi-step protocol; the engine's own 10-minute run budget is the hard ceiling.
const WALK_TIMEOUT_MS = 240_000;

// Every discovered curriculum protocol becomes one test below.
const PROTOCOL_IDS = discoverProtocolIds();

// Isolated results directory per protocol so parallel workers never share a
// report or screenshot path. Resolved against REPO_ROOT so a worker's cwd does
// not shift where evidence lands.
function resultsDirFor(protocol: string): string {
  return path.join(REPO_ROOT, "test-results", "walker", "runs", protocol);
}

//============================================
// Positive sweep: one visible-UI walk per protocol, run in parallel
//============================================

test.describe("walker sweep", () => {
  // Native Playwright parallelism across workers (the config sets fullyParallel
  // false for the deterministic smoke lane; this describe opts INTO parallel).
  test.describe.configure({ mode: "parallel", timeout: WALK_TIMEOUT_MS });

  for (const protocol of PROTOCOL_IDS) {
    test(`walks ${protocol} to completion through visible UI`, async ({ page, baseURL }) => {
      expect(baseURL, "config must provide a baseURL (webServer)").toBeTruthy();
      const authoredProtocol = PROTOCOLS[protocol];
      if (authoredProtocol === undefined) {
        throw new Error(`discovered protocol '${protocol}' is missing from generated/protocols.ts`);
      }

      const outcome = await runProtocolWalk(page, {
        protocol,
        baseUrl: baseURL as string,
        resultsDir: resultsDirFor(protocol),
        authoredProtocol,
      });

      // Honest acceptance: the protocol must complete through visible clicks.
      // A genuinely-incomplete protocol fails here with its diagnostics attached.
      expect(
        outcome.passed,
        `protocol '${protocol}' did not complete through visible UI:\n  ${outcome.diagnostics}`,
      ).toBe(true);
      expect(
        outcome.checkpointManifest.length,
        `protocol '${protocol}' recorded no target checkpoints`,
      ).toBeGreaterThan(0);
      expect(
        outcome.checkpointManifestValid,
        `protocol '${protocol}' recorded an invalid target checkpoint manifest:\n  ${outcome.diagnostics}`,
      ).toBe(true);
    });
  }
});

//============================================
// Negative check: a wrong-object click must never advance the step
//============================================

// A known-good protocol with both whole-object and structured-subpart DOM
// surfaces, driven in wrong-order mode: before each correct visible click the
// engine injects a real visible click on a DIFFERENT actionable scene object and
// asserts the runtime rejects it (wrongOrderClicks increments, the step position
// does not move). The protocol must still complete through the correct clicks.
// This catches inert subpart nodes being mistaken for clickable alternatives as
// well as the "clicking the wrong object does not advance" guarantee.
const WRONG_ORDER_PROTOCOL = "cell_seeding_plate_setup";

test.describe("walker wrong-order negative", () => {
  test.describe.configure({ timeout: WALK_TIMEOUT_MS });

  test(`wrong-object clicks are rejected while ${WRONG_ORDER_PROTOCOL} still completes`, async ({
    page,
    baseURL,
  }) => {
    expect(baseURL, "config must provide a baseURL (webServer)").toBeTruthy();
    const authoredProtocol = PROTOCOLS[WRONG_ORDER_PROTOCOL];
    if (authoredProtocol === undefined) {
      throw new Error(
        `wrong-order protocol '${WRONG_ORDER_PROTOCOL}' is missing from generated data`,
      );
    }

    const outcome = await runProtocolWalk(page, {
      protocol: WRONG_ORDER_PROTOCOL,
      baseUrl: baseURL as string,
      wrongOrder: true,
      resultsDir: path.join(REPO_ROOT, "test-results", "walker", "wrong_order"),
      authoredProtocol,
    });

    expect(
      outcome.passed,
      `wrong-order walk of '${WRONG_ORDER_PROTOCOL}' failed (a wrong click advanced, ` +
        `or the protocol did not complete):\n  ${outcome.diagnostics}`,
    ).toBe(true);
    expect(
      outcome.checkpointManifest.length,
      "wrong-order walk recorded no target checkpoints",
    ).toBeGreaterThan(0);
    expect(outcome.checkpointManifestValid, "wrong-order walk checkpoint manifest is invalid").toBe(
      true,
    );
  });
});
