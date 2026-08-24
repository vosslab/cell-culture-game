// eslint.config.local.js - consumer-owned ESLint overrides.
//
// Add repo-specific ESLint config objects here: extra browser-context globs,
// per-tool globals, or local rule tweaks. This file ships once via the noexist
// bucket and is never overwritten by propagation, so your edits survive. The
// canonical eslint.config.js imports and spreads this array AFTER its own config,
// so entries here refine or override the canonical rules.
//
// Example: give two named node tools browser globals for page.evaluate() use,
// without loosening no-undef across all tools.
//
//   import globals from "globals";
//   export default [
//     {
//       files: ["tools/scene_to_png.mjs", "tools/svg_picker/**"],
//       languageOptions: { globals: { ...globals.browser } },
//     },
//   ];
//
import globals from "globals";

// Browser-context tool files: Playwright automation scripts whose page.evaluate /
// page.waitForFunction callbacks reference window/document inside the browser page,
// not Node. Scoped narrowly so node-only tools keep no-undef for real bugs.
//
// tests/test_walker_debug.mjs stubs `window` on globalThis itself (see file header)
// and reads it back; it lives under tests/ rather than tests/playwright/ or
// tests/e2e/, so it needs the same browser-global allowance here.
export default [
  {
    files: [
      "tools/protocol_to_png.mjs",
      "tools/scene_to_png.mjs",
      "tools/scorecard_m2.mjs",
      "tools/svg_picker/**",
      "tests/test_walker_debug.mjs",
    ],
    languageOptions: { globals: { ...globals.browser } },
  },
  {
    // Background-agent git worktree checkouts live under .claude/worktrees/agent-*
    // at the repo root. Each worktree is a full repo copy with its own
    // eslint.config.js and tsconfig.json, so the canonical '**/*.{ts,tsx,...}'
    // glob picks up hundreds of duplicate files and typescript-eslint fails
    // every one of them with a "multiple candidate TSConfigRootDirs" parsing
    // error. Ignore the whole .claude/ tree the same way OTHER_REPOS/** is
    // ignored for sibling-repo checkouts.
    ignores: [".claude/**"],
  },
  {
    // generated/ is machine-emitted, gitignored build output rebuilt from source
    // on every run (see generated/precomputed_layout.ts). ESLint source-authoring
    // rules are mis-scoped here: no-loss-of-precision flags machine-emitted
    // 16-significant-digit floats that round-trip exactly, which is correct
    // generated output, not a source-style violation. tsc still type-checks
    // this tree via tsconfig.json; only ESLint's source-style rules are skipped.
    // The canonical eslint.config.js already ignores dist/** (another
    // machine-generated build-output tree); this mirrors that for generated/**.
    ignores: ["generated/**", "test-results/**"],
  },
];
