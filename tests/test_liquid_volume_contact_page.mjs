import assert from "node:assert/strict";
import test from "node:test";

import {
  assignAssetColors,
  effectiveFillDiagnostics,
  formatCreationTimestamp,
  formatDebugNumber,
  generateRandomColors,
  parseArgs,
  parseColorList,
  parseVolumeList,
  previousAssetColors,
} from "../tools/liquid_volume_contact_page.mjs";

test("contact page formats a visible Chicago creation timestamp", () => {
  assert.equal(
    formatCreationTimestamp("2026-08-01T20:04:05.000Z"),
    "August 1, 2026 at 3:04:05 PM CDT",
  );
  assert.throws(() => formatCreationTimestamp("not-a-date"), /valid date/);
});

test("contact page uses a useful default volume series", () => {
  assert.deepEqual(parseArgs(["falcon_15ml"]), {
    assetNames: ["falcon_15ml"],
    assetNotes: {},
    colors: null,
    volumes: [0, 5, 10, 25, 50, 75, 85, 90, 100],
  });
});

test("contact page accepts explicit color and volume series", () => {
  assert.deepEqual(
    parseArgs(["bottle_medium_pink", "--color", "#C2015A", "--volumes", "0,33.3,100"]),
    {
      assetNames: ["bottle_medium_pink"],
      assetNotes: {},
      colors: ["#c2015a"],
      volumes: [0, 33.3, 100],
    },
  );
});

test("contact page accepts several assets for one fleet sheet", () => {
  assert.deepEqual(parseArgs(["falcon_15ml", "falcon_50ml", "microtube"]), {
    assetNames: ["falcon_15ml", "falcon_50ml", "microtube"],
    assetNotes: {},
    colors: null,
    volumes: [0, 5, 10, 25, 50, 75, 85, 90, 100],
  });
});

test("contact page accepts an explicit palette when requested", () => {
  const colors = parseColorList("#076DAD,#8E44AD,#1B7F5A");
  assert.deepEqual(colors, ["#076dad", "#8e44ad", "#1b7f5a"]);
  assert.deepEqual(assignAssetColors(["a", "b", "c", "d", "e"], colors), [
    "#076dad",
    "#8e44ad",
    "#1b7f5a",
    "#076dad",
    "#8e44ad",
  ]);
  assert.throws(() => parseColorList("red,#076dad"), /#rrggbb/);
});

test("contact page generates distinct random colors and avoids the prior sheet", () => {
  const byteTriples = [
    Uint8Array.from([7, 109, 173]),
    Uint8Array.from([17, 34, 51]),
    Uint8Array.from([68, 85, 102]),
  ];
  let index = 0;
  const generated = generateRandomColors(2, new Set(["#076dad"]), () => byteTriples[index++]);
  assert.deepEqual(generated, ["#112233", "#445566"]);
  assert.throws(() => generateRandomColors(0), /positive integer/);
  assert.throws(
    () => generateRandomColors(1, new Set(), () => Uint8Array.from([1, 2])),
    /three bytes/,
  );
});

test("contact page reads colors from current and legacy sheets", () => {
  assert.deepEqual(previousAssetColors(null), new Set());
  assert.deepEqual(
    previousAssetColors('<section data-asset-color="#AABBCC" style="--asset-color: #112233">'),
    new Set(["#aabbcc", "#112233"]),
  );
});

test("contact page accepts a reviewed asset calibration note", () => {
  assert.deepEqual(
    parseArgs([
      "bottle_medium_pink",
      "--note",
      "bottle_medium_pink=Requests above 85% render identically at 85%.",
    ]),
    {
      assetNames: ["bottle_medium_pink"],
      assetNotes: {
        bottle_medium_pink: "Requests above 85% render identically at 85%.",
      },
      colors: null,
      volumes: [0, 5, 10, 25, 50, 75, 85, 90, 100],
    },
  );
  assert.throws(
    () => parseArgs(["falcon_15ml", "--note", "bottle_medium_pink=This asset was not selected."]),
    /unselected asset/,
  );
});

test("bottle fill diagnostics plateau at its compiler-owned 85 percent cap", () => {
  assert.deepEqual(
    [85, 90, 100].map((requested) => effectiveFillDiagnostics(requested, 85)),
    [
      { effectivePercent: 85, clamped: false },
      { effectivePercent: 85, clamped: true },
      { effectivePercent: 85, clamped: true },
    ],
  );
});

test("contact-page diagnostics preserve empty and clamp a nonzero minimum fill", () => {
  assert.deepEqual(effectiveFillDiagnostics(5, 100, 10), {
    effectivePercent: 10,
    clamped: true,
  });
  assert.deepEqual(effectiveFillDiagnostics(0, 100, 10), {
    effectivePercent: 0,
    clamped: false,
  });
});

test("uncapped asset diagnostics retain their requested fill", () => {
  assert.deepEqual(effectiveFillDiagnostics(100, null), {
    effectivePercent: 100,
    clamped: false,
  });
});

test("contact-page diagnostics round finite values to three decimals", () => {
  assert.equal(formatDebugNumber(184.49780000000004), "184.498");
  assert.equal(formatDebugNumber(4), "4");
  assert.equal(formatDebugNumber(-0.0001), "0");
});

test("contact page rejects invalid volume values", () => {
  assert.throws(() => parseVolumeList("0,101"), /in \[0, 100\]/);
  assert.throws(() => parseVolumeList("0,nope"), /in \[0, 100\]/);
});
