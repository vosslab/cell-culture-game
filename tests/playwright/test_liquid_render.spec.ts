import { expect, test } from "@playwright/test";
import path from "node:path";
import fs from "node:fs";
import os from "node:os";
import { spawnSync } from "node:child_process";

let harnessBundle = "";
const VARIABLE_VOLUME_ASSETS = [
  "bottle_medium_pink",
  "falcon_15ml",
  "falcon_50ml",
  "microtube",
  "serological_pipette",
];
const MATERIALS = ["#076dad", "#c2015a", "#5a8f20"];
const VOLUMES = [0, 5, 10, 25, 50, 60, 75, 85, 90, 100];

function formatSvgNumber(value: number): string {
  const rounded = Number(value.toFixed(9));
  return Object.is(rounded, -0) ? "0" : String(rounded);
}

function calibratedSurfaceY(
  boundsY: number,
  boundsHeight: number,
  bodyAnchorY: number | null,
  bodyStartFillPercent: number | null,
  fillHeightExponent: number | null,
  maxFillPercent: number | null,
  fillPercent: number,
): number {
  const boundsBottom = boundsY + boundsHeight;
  if (fillHeightExponent !== null) {
    const normalizedFill = Math.max(0, Math.min(1, fillPercent / (maxFillPercent ?? 100)));
    return boundsBottom - boundsHeight * normalizedFill ** fillHeightExponent;
  }
  if (bodyStartFillPercent === null) {
    return boundsY + boundsHeight * (1 - fillPercent / 100);
  }
  if (bodyAnchorY === null) {
    throw new Error("body-start calibration is missing its body anchor");
  }
  if (fillPercent <= bodyStartFillPercent) {
    return boundsBottom - (boundsBottom - bodyAnchorY) * (fillPercent / bodyStartFillPercent);
  }
  return (
    bodyAnchorY -
    (bodyAnchorY - boundsY) * ((fillPercent - bodyStartFillPercent) / (100 - bodyStartFillPercent))
  );
}

test("normalized fill-height exponent follows the capped perceptual curve", () => {
  const boundsY = 10;
  const boundsHeight = 200;
  expect(calibratedSurfaceY(boundsY, boundsHeight, null, null, null, null, 50)).toBe(110);
  const exponent = 0.45;
  const maximum = 85;
  expect(calibratedSurfaceY(boundsY, boundsHeight, null, null, exponent, maximum, 0)).toBe(210);
  const target = 210 - 200 * (50 / 85) ** exponent;
  expect(calibratedSurfaceY(boundsY, boundsHeight, null, null, exponent, maximum, 50)).toBeCloseTo(
    target,
    10,
  );
  const atCap = calibratedSurfaceY(boundsY, boundsHeight, null, null, exponent, maximum, 85);
  expect(atCap).toBe(10);
  expect(calibratedSurfaceY(boundsY, boundsHeight, null, null, exponent, maximum, 100)).toBe(atCap);
});

function effectiveFillPercent(
  requestedPercent: number,
  minFillPercent: number | null,
  maxFillPercent: number | null,
): number {
  const upperBoundedPercent = Math.min(requestedPercent, maxFillPercent ?? 100);
  return upperBoundedPercent === 0 ? 0 : Math.max(upperBoundedPercent, minFillPercent ?? 0);
}

function surfaceTransform(
  boundsX: number,
  boundsWidth: number,
  surfaceReferenceY: number,
  surfaceY: number,
  bodyStartFillPercent: number | null,
  fillPercent: number,
): string {
  const offset = formatSvgNumber(surfaceY - surfaceReferenceY);
  if (bodyStartFillPercent === null || fillPercent >= bodyStartFillPercent) {
    return `translate(0, ${offset})`;
  }
  const scale = fillPercent / bodyStartFillPercent;
  const centerX = boundsX + boundsWidth / 2;
  return `translate(0, ${offset}) translate(${formatSvgNumber(centerX)}, ${formatSvgNumber(surfaceReferenceY)}) scale(${formatSvgNumber(scale)}) translate(${formatSvgNumber(-centerX)}, ${formatSvgNumber(-surfaceReferenceY)})`;
}

test.beforeAll(() => {
  fs.mkdirSync("test-results", { recursive: true });
  const harnessDirectory = fs.mkdtempSync(path.join(os.tmpdir(), "liquid_render_harness_"));
  harnessBundle = path.join(harnessDirectory, "harness.js");
  const result = spawnSync(
    "npx",
    [
      "esbuild",
      "tools/liquid_render_harness.ts",
      "--bundle",
      "--format=iife",
      "--target=es2020",
      "--platform=browser",
      `--outfile=${harnessBundle}`,
    ],
    { encoding: "utf8" },
  );
  if (result.status !== 0) {
    throw new Error(`liquid harness build failed:\n${result.stderr || result.stdout}`);
  }
});

test("compiled variable-volume fleet uses gravity parts and stationary clipping", async ({
  page,
}) => {
  await page.goto("/bench_basic.html");
  await page.setContent(
    "<!doctype html><style>body{background:white}#matrix{display:grid;grid-template-columns:repeat(4,160px);gap:8px}.cell{width:150px;height:210px;border:1px solid #ddd}.cell svg{width:100%;height:100%}</style><div id='matrix'></div>",
  );
  await page.addScriptTag({ path: harnessBundle });

  for (const asset of VARIABLE_VOLUME_ASSETS) {
    const report = await page.evaluate(
      async ({ asset, materials, volumes }) => {
        const manifestResponse = await fetch("assets/liquid_regions.json");
        const manifest = (await manifestResponse.json()) as Record<
          string,
          {
            region_handle: string;
            reveal_handle: string;
            bounds: { x: number; y: number; width: number; height: number };
            surface_reference_y: number | null;
            body_anchor_y: number | null;
            surface_base_depth: number;
            max_fill_percent: number | null;
            min_fill_percent: number | null;
            body_start_fill_percent: number | null;
            fill_height_exponent: number | null;
            paints: Array<{
              element_handle: string;
              paint_handle: string;
              paint_role: string;
              liquid_part: "bottom" | "body" | "surface";
            }>;
          }
        >;
        const entry = manifest[asset];
        if (entry === undefined) {
          throw new Error(`missing liquid manifest entry for ${asset}`);
        }
        const matrix = document.querySelector("#matrix");
        if (!(matrix instanceof HTMLElement)) {
          throw new Error("matrix host missing");
        }
        matrix.replaceChildren();
        const rows: Array<{
          volume: number;
          color: string;
          part_transforms: Array<{ part: string; transform: string | null }>;
          reveal_y: number;
          reveal_height: number;
          display: string | null;
          node_count_stable: boolean;
          no_semantic_attributes: boolean;
          computed_paints: Array<{
            role: string;
            fill: string;
            stroke: string;
            property: string;
          }>;
          ids: string[];
          clip_path: string | null;
          primary_surface_bottom: number | null;
          body_top_to_surface_base_bottom: number | null;
        }> = [];
        for (const color of materials) {
          for (const volume of volumes) {
            const host = document.createElement("div");
            host.className = "cell";
            matrix.append(host);
            const rendered = await window.liquidRenderHarness.injectAndRender(
              host,
              asset,
              `${asset}_${color}_${volume}`,
              volume === 0 ? null : color,
              volume,
            );
            if (!rendered) {
              throw new Error(`${asset} did not dispatch to compiled liquid rendering`);
            }
            const all = Array.from(host.querySelectorAll("*"));
            const countAfterRender = all.length;
            window.liquidRenderHarness.render(host, volume === 0 ? null : color, volume);
            const region = all.find((element) => element.id.endsWith(`__${entry.region_handle}`));
            if (!(region instanceof SVGGElement)) {
              throw new Error(`${asset} region group missing`);
            }
            const reveal = all.find((element) => element.id.endsWith(`__${entry.reveal_handle}`));
            if (!(reveal instanceof SVGRectElement)) {
              throw new Error(`${asset} reveal rect missing`);
            }
            const paintElements = entry.paints.map((paint) => {
              const element = all.find((candidate) =>
                candidate.id.endsWith(`__${paint.element_handle}`),
              );
              if (!(element instanceof SVGElement)) {
                throw new Error(`${asset} paint element missing`);
              }
              return element;
            });
            rows.push({
              volume,
              color,
              part_transforms: paintElements.map((element, index) => ({
                part: entry.paints[index]!.liquid_part,
                transform: element.getAttribute("transform"),
              })),
              reveal_y: Number(reveal.getAttribute("y")),
              reveal_height: Number(reveal.getAttribute("height")),
              display: region.getAttribute("display"),
              node_count_stable: countAfterRender === host.querySelectorAll("*").length,
              no_semantic_attributes:
                host.querySelector(
                  "[data-vlab-rendering], [data-vlab-layer-kind], [data-vlab-paint-role], [data-vlab-liquid-part]",
                ) === null,
              computed_paints: paintElements.map((element, index) => {
                const painted =
                  element.querySelector("path,rect,circle,ellipse,line,polyline,polygon") ??
                  element;
                const paint = entry.paints[index]!;
                const style = getComputedStyle(painted);
                return {
                  role: paint.paint_role,
                  fill: style.fill,
                  stroke: style.stroke,
                  property: host.style.getPropertyValue(`--${paint.paint_handle}`),
                };
              }),
              ids: all.flatMap((element) => (element.id.length > 0 ? [element.id] : [])),
              clip_path: region.getAttribute("clip-path"),
              primary_surface_bottom: ((): number | null => {
                const primarySurfaceIndex = entry.paints.findIndex(
                  (paint) => paint.liquid_part === "surface" && paint.paint_role === "highlight",
                );
                if (primarySurfaceIndex === -1) {
                  return null;
                }
                const primarySurface = paintElements[primarySurfaceIndex]!;
                const geometry = primarySurface.querySelector("path,rect,ellipse,circle");
                if (!(geometry instanceof SVGGraphicsElement)) {
                  throw new Error(`${asset} primary surface geometry missing`);
                }
                const svg = geometry.ownerSVGElement;
                const geometryMatrix = geometry.getCTM();
                const svgMatrix = svg === null ? null : svg.getCTM();
                if (svg === null || geometryMatrix === null || svgMatrix === null) {
                  throw new Error(`${asset} primary surface SVG transform missing`);
                }
                const box = geometry.getBBox();
                // getBBox() is in the geometry's local coordinate system, while
                // getCTM() includes the page's scaled SVG viewport. Convert the
                // local bounding-box corners back into the root SVG user space
                // before comparing them to authored graduation coordinates.
                const localToSvg = svgMatrix.inverse().multiply(geometryMatrix);
                return Math.max(
                  ...[
                    new DOMPoint(box.x, box.y),
                    new DOMPoint(box.x + box.width, box.y),
                    new DOMPoint(box.x, box.y + box.height),
                    new DOMPoint(box.x + box.width, box.y + box.height),
                  ].map((point) => point.matrixTransform(localToSvg).y),
                );
              })(),
              body_top_to_surface_base_bottom: ((): number | null => {
                const baseBodyIndex = entry.paints.findIndex(
                  (paint) => paint.liquid_part === "body" && paint.paint_role === "base",
                );
                const baseSurfaceIndex = entry.paints.findIndex(
                  (paint) => paint.liquid_part === "surface" && paint.paint_role === "base",
                );
                if (baseBodyIndex === -1 || baseSurfaceIndex === -1) {
                  return null;
                }
                const body = paintElements[baseBodyIndex]!.querySelector(
                  "path,rect,ellipse,circle",
                );
                const surface = paintElements[baseSurfaceIndex]!.querySelector(
                  "path,rect,ellipse,circle",
                );
                if (
                  !(body instanceof SVGGraphicsElement) ||
                  !(surface instanceof SVGGraphicsElement)
                ) {
                  throw new Error(`${asset} base body or surface geometry missing`);
                }
                function rootSvgYExtents(geometry: SVGGraphicsElement): {
                  min: number;
                  max: number;
                } {
                  const svg = geometry.ownerSVGElement;
                  const geometryMatrix = geometry.getCTM();
                  const svgMatrix = svg === null ? null : svg.getCTM();
                  if (svg === null || geometryMatrix === null || svgMatrix === null) {
                    throw new Error(`${asset} base liquid geometry SVG transform missing`);
                  }
                  const box = geometry.getBBox();
                  const localToSvg = svgMatrix.inverse().multiply(geometryMatrix);
                  const ys = [
                    new DOMPoint(box.x, box.y),
                    new DOMPoint(box.x + box.width, box.y),
                    new DOMPoint(box.x, box.y + box.height),
                    new DOMPoint(box.x + box.width, box.y + box.height),
                  ].map((point) => point.matrixTransform(localToSvg).y);
                  return { min: Math.min(...ys), max: Math.max(...ys) };
                }
                const bodyExtents = rootSvgYExtents(body);
                const surfaceExtents = rootSvgYExtents(surface);
                // The body begins exactly beneath the base meniscus.  This is
                // measured from browser-applied CTMs rather than from the
                // authored formula so numeric serialization cannot hide a seam.
                return bodyExtents.min - surfaceExtents.max;
              })(),
            });
          }
        }
        return {
          rows,
          bounds_height: entry.bounds.height,
          bounds_width: entry.bounds.width,
          bounds_x: entry.bounds.x,
          bounds_y: entry.bounds.y,
          surface_reference_y: entry.surface_reference_y,
          body_anchor_y: entry.body_anchor_y,
          surface_base_depth: entry.surface_base_depth,
          max_fill_percent: entry.max_fill_percent,
          min_fill_percent: entry.min_fill_percent,
          body_start_fill_percent: entry.body_start_fill_percent,
          fill_height_exponent: entry.fill_height_exponent,
        };
      },
      { asset, materials: MATERIALS, volumes: VOLUMES },
    );

    expect(report.rows).toHaveLength(MATERIALS.length * VOLUMES.length);
    for (const row of report.rows) {
      const renderedVolume = effectiveFillPercent(
        row.volume,
        report.min_fill_percent,
        report.max_fill_percent,
      );
      const surfaceY = calibratedSurfaceY(
        report.bounds_y,
        report.bounds_height,
        report.body_anchor_y,
        report.body_start_fill_percent,
        report.fill_height_exponent,
        report.max_fill_percent,
        renderedVolume,
      );
      expect(row.reveal_y).toBeCloseTo(surfaceY, 2);
      expect(row.reveal_height).toBeCloseTo(report.bounds_y + report.bounds_height - surfaceY, 2);
      expect(row.display).toBe(row.volume === 0 ? "none" : "inline");
      expect(row.node_count_stable).toBe(true);
      expect(row.no_semantic_attributes).toBe(true);
      expect(row.clip_path).toContain("anchor_liquid_clip");
      for (const part of row.part_transforms) {
        if (part.part === "bottom") {
          expect(part.transform).toBeNull();
        } else if (part.part === "surface") {
          expect(part.transform).toBe(
            surfaceTransform(
              report.bounds_x,
              report.bounds_width,
              report.surface_reference_y!,
              surfaceY,
              report.body_start_fill_percent,
              renderedVolume,
            ),
          );
        } else {
          const surfaceScale =
            report.body_start_fill_percent === null ||
            renderedVolume >= report.body_start_fill_percent
              ? 1
              : renderedVolume / report.body_start_fill_percent;
          const scale =
            Math.max(
              0,
              report.body_anchor_y! - (surfaceY + report.surface_base_depth * surfaceScale),
            ) /
            (report.body_anchor_y! - report.surface_reference_y!);
          const translateY = report.body_anchor_y! * (1 - scale);
          expect(part.transform).toBe(
            `matrix(1 0 0 ${formatSvgNumber(scale)} 0 ${formatSvgNumber(translateY)})`,
          );
        }
      }
      expect(new Set(row.ids).size).toBe(row.ids.length);
      const surfaceScale =
        report.body_start_fill_percent === null || renderedVolume >= report.body_start_fill_percent
          ? 1
          : renderedVolume / report.body_start_fill_percent;
      const bodyHeight =
        report.body_anchor_y === null
          ? 0
          : report.body_anchor_y - (surfaceY + report.surface_base_depth * surfaceScale);
      if (
        asset === "microtube" &&
        row.volume > 0 &&
        bodyHeight > 0 &&
        row.body_top_to_surface_base_bottom !== null
      ) {
        // Chromium's normalized-arc getBBox has a <0.005-unit numerical
        // residual.  A sub-hundredth-unit bound still rejects the old
        // three-decimal transform error (0.037--0.117 SVG units).
        expect(
          Math.abs(row.body_top_to_surface_base_bottom),
          `${asset} ${row.volume}% transformed body-to-meniscus seam: ${row.body_top_to_surface_base_bottom}`,
        ).toBeLessThan(0.01);
      }
      if (row.volume > 0) {
        const basePaints = row.computed_paints.filter((paint) => paint.role === "base");
        expect(basePaints.length).toBeGreaterThan(0);
        for (const paint of row.computed_paints) {
          expect(paint.property).toMatch(/^#[0-9a-f]{6}$/);
          expect(paint.fill !== "none" || paint.stroke !== "none").toBe(true);
        }
        for (const paint of basePaints) {
          expect(paint.property).toBe(row.color);
        }
      }
    }
    const allIds = report.rows.flatMap((row) => row.ids);
    expect(new Set(allIds).size).toBe(allIds.length);
    if (report.max_fill_percent !== null) {
      for (const color of MATERIALS) {
        const cappedRows = report.rows.filter(
          (row) => row.color === color && row.volume >= report.max_fill_percent!,
        );
        const ceiling = cappedRows.find((row) => row.volume === report.max_fill_percent);
        expect(ceiling).toBeDefined();
        for (const row of cappedRows) {
          expect(row.reveal_y).toBeCloseTo(ceiling!.reveal_y, 8);
          expect(row.reveal_height).toBeCloseTo(ceiling!.reveal_height, 8);
          expect(row.part_transforms).toEqual(ceiling!.part_transforms);
        }
      }
    }
    if (report.min_fill_percent !== null) {
      for (const color of MATERIALS) {
        const floor = report.rows.find(
          (row) => row.color === color && row.volume === report.min_fill_percent,
        );
        expect(floor).toBeDefined();
        const belowFloorRows = report.rows.filter(
          (row) => row.color === color && row.volume > 0 && row.volume < report.min_fill_percent!,
        );
        for (const row of belowFloorRows) {
          expect(row.reveal_y).toBeCloseTo(floor!.reveal_y, 8);
          expect(row.reveal_height).toBeCloseTo(floor!.reveal_height, 8);
          expect(row.part_transforms).toEqual(floor!.part_transforms);
        }
      }
    }
    const taperScaleExpectations: Record<string, Array<[number, number]>> = {
      microtube: [
        [5, 5 / 35.98],
        [10, 10 / 35.98],
        [50, 1],
        [100, 1],
      ],
      serological_pipette: [
        [5, 5 / 7.3394495],
        [10, 1],
        [50, 1],
        [100, 1],
      ],
      falcon_15ml: [
        [5, 1],
        [10, 1],
      ],
      falcon_50ml: [
        [5, 1],
        [10, 1],
      ],
    };
    for (const [requestedVolume, expectedScale] of taperScaleExpectations[asset] ?? []) {
      const row = report.rows.find(
        (candidate) => candidate.color === MATERIALS[0] && candidate.volume === requestedVolume,
      );
      expect(row).toBeDefined();
      const renderedVolume = effectiveFillPercent(
        requestedVolume,
        report.min_fill_percent,
        report.max_fill_percent,
      );
      const surfaceY = calibratedSurfaceY(
        report.bounds_y,
        report.bounds_height,
        report.body_anchor_y,
        report.body_start_fill_percent,
        report.fill_height_exponent,
        report.max_fill_percent,
        renderedVolume,
      );
      const expectedTransform = surfaceTransform(
        report.bounds_x,
        report.bounds_width,
        report.surface_reference_y!,
        surfaceY,
        expectedScale === 1 ? null : report.body_start_fill_percent,
        expectedScale === 1 ? renderedVolume : renderedVolume,
      );
      expect(
        report.body_start_fill_percent === null || renderedVolume >= report.body_start_fill_percent
          ? 1
          : renderedVolume / report.body_start_fill_percent,
      ).toBeCloseTo(expectedScale, 6);
      for (const part of row!.part_transforms.filter((part) => part.part === "surface")) {
        expect(part.transform).toBe(expectedTransform);
      }
    }
    const graduationCheck = {
      falcon_50ml: { half: 228.302, full: 76.714 },
      falcon_15ml: { half: 209.0745, full: 40.377 },
    }[asset];
    if (graduationCheck !== undefined) {
      const halfVolume = report.rows.find((row) => row.color === MATERIALS[0] && row.volume === 50);
      const fullVolume = report.rows.find(
        (row) => row.color === MATERIALS[0] && row.volume === 100,
      );
      expect(halfVolume?.primary_surface_bottom).not.toBeNull();
      expect(fullVolume?.primary_surface_bottom).not.toBeNull();
      expect(halfVolume!.primary_surface_bottom).toBeCloseTo(graduationCheck.half, 3);
      expect(fullVolume!.primary_surface_bottom).toBeCloseTo(graduationCheck.full, 3);
    }
    await page.locator("#matrix").screenshot({
      path: `test-results/liquid_matrix_${asset}.png`,
    });
  }
});

test("mutating one compiled instance leaves its sibling unchanged", async ({ page }) => {
  await page.goto("/bench_basic.html");
  await page.setContent("<!doctype html><div id='first'></div><div id='second'></div>");
  await page.addScriptTag({ path: harnessBundle });
  const transforms = await page.evaluate(async () => {
    const first = document.querySelector("#first");
    const second = document.querySelector("#second");
    if (!(first instanceof HTMLElement) || !(second instanceof HTMLElement)) {
      throw new Error("instance hosts missing");
    }
    await window.liquidRenderHarness.injectAndRender(
      first,
      "serological_pipette",
      "first",
      "#076dad",
      25,
    );
    await window.liquidRenderHarness.injectAndRender(
      second,
      "serological_pipette",
      "second",
      "#c2015a",
      60,
    );
    function levelTransform(host: HTMLElement): string | null {
      const level = Array.from(host.querySelectorAll("g")).find((group) =>
        group.getAttribute("transform")?.includes("translate(0, "),
      );
      return level?.getAttribute("transform") ?? null;
    }
    const secondBefore = levelTransform(second);
    await window.liquidRenderHarness.injectAndRender(
      first,
      "serological_pipette",
      "first_again",
      "#5a8f20",
      100,
    );
    return { first: levelTransform(first), secondBefore, secondAfter: levelTransform(second) };
  });
  expect(transforms.first).toBe("translate(0, 0)");
  expect(transforms.secondAfter).toBe(transforms.secondBefore);
});
