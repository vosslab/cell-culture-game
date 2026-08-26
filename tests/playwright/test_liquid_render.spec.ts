import { expect, test } from "@playwright/test";
import path from "node:path";
import fs from "node:fs";
import os from "node:os";
import { spawnSync } from "node:child_process";

let harnessBundle = "";
const MATERIALS = ["#076dad", "#c2015a", "#5a8f20"];

type Rect = { x: number; y: number; width: number; height: number };

type LiquidState = {
  volume: number;
  color: string | null;
  display: string | null;
  clipPath: string | null;
  reveal: Rect;
  parts: Array<{ part: "bottom" | "body" | "surface"; stationary: boolean }>;
  paints: Array<{ role: string; fill: string; stroke: string; property: string }>;
  ids: string[];
};

test.beforeAll(() => {
  const harnessDirectory = fs.mkdtempSync(path.join(os.tmpdir(), "liquid_render_harness_"));
  harnessBundle = path.join(harnessDirectory, "harness.js");
  const esbuild = path.resolve("node_modules/.bin/esbuild");
  const result = spawnSync(
    esbuild,
    [
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

test("compiled variable-volume assets render isolated, clipped liquid", async ({ page }) => {
  await page.goto("/bench_basic.html");
  await page.setContent("<!doctype html><div id='matrix'></div>");
  await page.addScriptTag({ path: harnessBundle });

  const reports = await page.evaluate(async (materials) => {
    type ManifestEntry = {
      region_handle: string;
      reveal_handle: string;
      min_fill_percent: number | null;
      max_fill_percent: number | null;
      body_start_fill_percent: number | null;
      paints: Array<{
        element_handle: string;
        paint_handle: string;
        paint_role: string;
        liquid_part: "bottom" | "body" | "surface";
      }>;
    };
    const response = await fetch("assets/liquid_regions.json");
    const manifest = (await response.json()) as Record<string, ManifestEntry>;
    const matrix = document.querySelector("#matrix");
    if (!(matrix instanceof HTMLElement)) {
      throw new Error("matrix host missing");
    }

    function rectAttributes(element: SVGRectElement): Rect {
      return {
        x: Number(element.getAttribute("x")),
        y: Number(element.getAttribute("y")),
        width: Number(element.getAttribute("width")),
        height: Number(element.getAttribute("height")),
      };
    }

    const reports: Array<{
      asset: string;
      samples: number[];
      states: LiquidState[];
    }> = [];
    for (const [asset, entry] of Object.entries(manifest)) {
      const supportedRangeStart = 0;
      const supportedRangeEnd = 100;
      const midpoint = (supportedRangeStart + supportedRangeEnd) / 2;
      const samples = [
        supportedRangeStart,
        midpoint,
        supportedRangeEnd,
        entry.min_fill_percent,
        entry.max_fill_percent,
        entry.body_start_fill_percent,
      ]
        .filter((value): value is number => value !== null)
        .sort((first, second) => first - second)
        .filter((value, index, values) => index === 0 || value !== values[index - 1]);
      const states: LiquidState[] = [];
      for (const [colorIndex, color] of materials.entries()) {
        const host = document.createElement("div");
        matrix.append(host);
        const rendered = await window.liquidRenderHarness.injectAndRender(
          host,
          asset,
          `${asset}_${colorIndex}`,
          null,
          0,
        );
        if (!rendered) {
          throw new Error(`${asset} did not dispatch to compiled liquid rendering`);
        }
        for (const volume of samples) {
          const material = volume === 0 ? null : color;
          if (!window.liquidRenderHarness.render(host, material, volume)) {
            throw new Error(`${asset} did not render liquid state`);
          }
          const all = Array.from(host.querySelectorAll("*"));
          const region = all.find((element) => element.id.endsWith(`__${entry.region_handle}`));
          const reveal = all.find((element) => element.id.endsWith(`__${entry.reveal_handle}`));
          if (!(region instanceof SVGGElement) || !(reveal instanceof SVGRectElement)) {
            throw new Error(`${asset} liquid region is incomplete`);
          }
          const parts = entry.paints.map((paint) => {
            const element = all.find((candidate) =>
              candidate.id.endsWith(`__${paint.element_handle}`),
            );
            if (!(element instanceof SVGElement)) {
              throw new Error(`${asset} paint element missing`);
            }
            return {
              part: paint.liquid_part,
              stationary: element.getAttribute("transform") === null,
            };
          });
          const paints = entry.paints.map((paint) => {
            const element = all.find((candidate) =>
              candidate.id.endsWith(`__${paint.element_handle}`),
            );
            if (!(element instanceof SVGElement)) {
              throw new Error(`${asset} paint element missing`);
            }
            const painted =
              element.querySelector("path,rect,circle,ellipse,line,polyline,polygon") ?? element;
            const style = getComputedStyle(painted);
            return {
              role: paint.paint_role,
              fill: style.fill,
              stroke: style.stroke,
              property: host.style.getPropertyValue(`--${paint.paint_handle}`),
            };
          });
          states.push({
            volume,
            color: material,
            display: region.getAttribute("display"),
            clipPath: region.getAttribute("clip-path"),
            reveal: rectAttributes(reveal),
            parts,
            paints,
            ids: all.flatMap((element) => (element.id.length > 0 ? [element.id] : [])),
          });
        }
      }
      reports.push({ asset, samples, states });
    }
    return reports;
  }, MATERIALS);

  for (const report of reports) {
    expect(report.samples).toContain(0);
    expect(report.samples).toContain((0 + 100) / 2);
    expect(report.samples).toContain(100);
    for (const state of report.states) {
      expect(new Set(state.ids).size).toBe(state.ids.length);
      expect(state.clipPath).toContain("anchor_liquid_clip");
      expect(state.display).toBe(state.volume === 0 ? "none" : "inline");
      if (state.volume === 0) {
        continue;
      }
      expect(state.reveal.height).toBeGreaterThan(0);
      const basePaints = state.paints.filter((paint) => paint.role === "base");
      expect(basePaints.length).toBeGreaterThan(0);
      for (const paint of state.paints) {
        expect(paint.property).toMatch(/^#[0-9a-f]{6}$/);
        expect(paint.fill !== "none" || paint.stroke !== "none").toBe(true);
      }
      for (const paint of basePaints) {
        expect(paint.property).toBe(state.color);
      }
    }

    const allIds = report.states
      .filter((_, index) => index % report.samples.length === 0)
      .flatMap((state) => state.ids);
    expect(new Set(allIds).size).toBe(allIds.length);

    for (const colorIndex of MATERIALS.keys()) {
      const states = report.states.slice(
        colorIndex * report.samples.length,
        (colorIndex + 1) * report.samples.length,
      );
      const nonempty = states.filter((state) => state.volume > 0);
      const bottomParts = nonempty.flatMap((state) =>
        state.parts.filter((part) => part.part === "bottom"),
      );
      expect(bottomParts.length).toBeGreaterThan(0);
      for (const part of bottomParts) {
        expect(part.stationary).toBe(true);
      }
      const responsiveStates = nonempty.filter((state) =>
        state.parts.some((part) => part.part !== "bottom" && !part.stationary),
      );
      expect(responsiveStates.length).toBeGreaterThan(0);
      expect(
        new Set(responsiveStates.map((state) => JSON.stringify(state.reveal))).size,
      ).toBeGreaterThan(1);
    }
  }
});
