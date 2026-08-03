// Developer/test browser surface for the real compiled-liquid injection and writer.

import { injectSvgFromManifest } from "../src/scene_runtime/renderer/inject_svg.js";
import { render_liquid_material_effects } from "../src/scene_runtime/renderer/liquid_paint.js";
import type { AnchorMaterialEffect } from "../src/scene_runtime/renderer/visual_state_resolver.js";

type LiquidRenderHarness = {
  injectAndRender(
    host: HTMLElement,
    asset_name: string,
    instance_key: string,
    color: string | null,
    fill_percent: number,
  ): Promise<boolean>;
  render(host: HTMLElement, color: string | null, fill_percent: number): boolean;
};

declare global {
  interface Window {
    liquidRenderHarness: LiquidRenderHarness;
  }
}

function render(host: HTMLElement, color: string | null, fill_percent: number): boolean {
  const effect: AnchorMaterialEffect = {
    type: "anchor_material",
    field_name: "volume_ml",
    render_effect: "fill_height",
    target: "anchor_liquid_bounds",
    clip: "anchor_liquid_clip",
    fill_percent,
    material_name: color === null ? "empty" : "contact_material",
    color,
  };
  return render_liquid_material_effects(host, [effect]);
}

async function injectAndRender(
  host: HTMLElement,
  asset_name: string,
  instance_key: string,
  color: string | null,
  fill_percent: number,
): Promise<boolean> {
  await injectSvgFromManifest(host, asset_name, instance_key);
  return render(host, color, fill_percent);
}

window.liquidRenderHarness = { injectAndRender, render };
