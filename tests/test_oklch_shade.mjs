// Behavioral properties for perceptual material shade derivation.

import { describe, test } from "node:test";
import assert from "node:assert/strict";

import { derive_oklch_shade, oklch_lightness } from "../src/scene_runtime/renderer/oklch_shade.ts";

const BASE_COLORS = ["#076dad", "#c2015a", "#5a8f20", "#f2c14e", "#301050"];

describe("OKLCH liquid shade derivation", () => {
  test("base paint preserves the material registry scalar", () => {
    assert.equal(derive_oklch_shade("#076DAD", "base", null), "#076dad");
  });

  test("highlight and shadow move perceived lightness in the declared direction", () => {
    for (const base of BASE_COLORS) {
      const highlight = derive_oklch_shade(base, "highlight", 0.18);
      const shadow = derive_oklch_shade(base, "shadow", -0.18);
      assert.ok(oklch_lightness(highlight) > oklch_lightness(base), base);
      assert.ok(oklch_lightness(shadow) < oklch_lightness(base), base);
    }
  });

  test("derived colors stay in lowercase six-digit sRGB notation", () => {
    for (const base of BASE_COLORS) {
      assert.match(derive_oklch_shade(base, "highlight", 0.5), /^#[0-9a-f]{6}$/);
      assert.match(derive_oklch_shade(base, "shadow", -0.5), /^#[0-9a-f]{6}$/);
    }
  });

  test("the closed role and adjustment grammar fails loudly", () => {
    assert.throws(() => derive_oklch_shade("#076dad", "base", 0.1), /base role/);
    assert.throws(() => derive_oklch_shade("#076dad", "highlight", -0.1), /highlight/);
    assert.throws(() => derive_oklch_shade("#076dad", "shadow", 0.1), /shadow/);
    assert.throws(() => derive_oklch_shade("blue", "base", null), /#rrggbb/);
  });
});
