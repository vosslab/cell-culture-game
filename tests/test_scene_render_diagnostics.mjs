// Deterministic tests for tools/scene_render_diagnostics.mjs.
//
// These cases model browser DOM facts rather than individual scientific
// objects, so renderer diagnostics remain correct across every SVG asset.
//
// Run via:
//   node --test tests/test_scene_render_diagnostics.mjs

import assert from "node:assert/strict";
import { test } from "node:test";

import {
  classifyRenderedItem,
  isLoadedStaticSvgImage,
  selectVisualBbox,
} from "../tools/scene_render_diagnostics.mjs";

const PLACEHOLDER_KEYS = new Set(["known_placeholder_art"]);
const PLACEMENT_BOX = { x: 10, y: 20, width: 200, height: 100 };
const IMAGE_BOX = { x: 30, y: 20, width: 120, height: 100 };
const SVG_BOX = { x: 20, y: 25, width: 80, height: 90 };

function makeSnapshot(overrides = {}) {
  return {
    placeholderKind: null,
    hasMissingSvgMarker: false,
    assetKey: "real_asset",
    hasInlineSvg: false,
    hasDomSvgHost: false,
    staticImage: null,
    placementBbox: PLACEMENT_BOX,
    inlineSvgBbox: null,
    staticImageBbox: null,
    ...overrides,
  };
}

test("a loaded static SVG image is real and supplies the visual bounding box", () => {
  const staticImage = { present: true, complete: true, naturalWidth: 640, naturalHeight: 320 };
  const snapshot = makeSnapshot({ staticImage, staticImageBbox: IMAGE_BOX });

  assert.equal(isLoadedStaticSvgImage(staticImage), true);
  assert.deepEqual(classifyRenderedItem(snapshot, PLACEHOLDER_KEYS), {
    isPlaceholder: false,
    placeholderKind: null,
  });
  assert.deepEqual(selectVisualBbox(snapshot), IMAGE_BOX);
});

test("inline SVG remains real and supplies the visual bounding box", () => {
  const snapshot = makeSnapshot({ hasInlineSvg: true, inlineSvgBbox: SVG_BOX });

  assert.deepEqual(classifyRenderedItem(snapshot, PLACEHOLDER_KEYS), {
    isPlaceholder: false,
    placeholderKind: null,
  });
  assert.deepEqual(selectVisualBbox(snapshot), SVG_BOX);
});

test("explicit placeholder diagnostics override successfully rendered artwork", () => {
  const snapshot = makeSnapshot({
    placeholderKind: "missing-object",
    hasInlineSvg: true,
    inlineSvgBbox: SVG_BOX,
  });

  assert.deepEqual(classifyRenderedItem(snapshot, PLACEHOLDER_KEYS), {
    isPlaceholder: true,
    placeholderKind: "missing-object",
  });
  assert.deepEqual(selectVisualBbox(snapshot), SVG_BOX);
});

test("a registered placeholder-art asset remains a placeholder", () => {
  const snapshot = makeSnapshot({
    assetKey: "known_placeholder_art",
    staticImage: { present: true, complete: true, naturalWidth: 300, naturalHeight: 300 },
    staticImageBbox: IMAGE_BOX,
  });

  assert.deepEqual(classifyRenderedItem(snapshot, PLACEHOLDER_KEYS), {
    isPlaceholder: true,
    placeholderKind: "placeholder-art",
  });
});

test("a broken or unloaded static image is a missing SVG, not a real object", () => {
  for (const staticImage of [
    { present: true, complete: false, naturalWidth: 0, naturalHeight: 0 },
    { present: true, complete: true, naturalWidth: 0, naturalHeight: 0 },
  ]) {
    const snapshot = makeSnapshot({ staticImage, staticImageBbox: IMAGE_BOX });
    assert.equal(isLoadedStaticSvgImage(staticImage), false);
    assert.deepEqual(classifyRenderedItem(snapshot, PLACEHOLDER_KEYS), {
      isPlaceholder: true,
      placeholderKind: "missing-svg",
    });
    assert.deepEqual(selectVisualBbox(snapshot), PLACEMENT_BOX);
  }
});

test("a failed base DOM-SVG host is missing even when a subpart overlay has SVG art", () => {
  // The browser collector deliberately reports only the SVG nested in the
  // base DOM-SVG host as hasInlineSvg. A well/material overlay is unrelated
  // to whether the placement's declared base asset loaded.
  const snapshot = makeSnapshot({
    hasDomSvgHost: true,
    hasOverlaySvg: true,
    inlineSvgBbox: SVG_BOX,
  });

  assert.deepEqual(classifyRenderedItem(snapshot, PLACEHOLDER_KEYS), {
    isPlaceholder: true,
    placeholderKind: "missing-svg",
  });
  assert.deepEqual(selectVisualBbox(snapshot), PLACEMENT_BOX);
});

test("an item with no graphic host is diagnosed as a missing object", () => {
  assert.deepEqual(classifyRenderedItem(makeSnapshot(), PLACEHOLDER_KEYS), {
    isPlaceholder: true,
    placeholderKind: "missing-object",
  });
});
