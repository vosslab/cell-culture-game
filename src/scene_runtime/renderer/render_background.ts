// Background rendering. Supports gradient and asset forms.
// Gradient form: linear-gradient(angle, from, to).
// Asset form: delegates to asset registry (not yet implemented).

import type { Background } from "../layout/types.js";

//============================================

/**
 * Render a background onto a host element.
 * Discriminates on background form: gradient vs asset.
 *
 * Gradient: linear-gradient(angle, from_color, to_color).
 * Asset: currently unimplemented; throws loudly.
 *
 * @param host - HTMLElement to apply background to
 * @param bg - Background object
 * @throws Error if background is asset-backed (not yet implemented)
 */
export function renderBackground(host: HTMLElement, bg: Background): void {
  // Discriminate: does bg have 'type' field? If so, it's gradient.
  if ("type" in bg && bg.type === "gradient") {
    const angle = bg.angle ?? 180;
    const gradient = `linear-gradient(${angle}deg, ${bg.from}, ${bg.to})`;
    host.style.background = gradient;
    return;
  }

  // Asset form: render a neutral fill until the asset registry is wired.
  // The scene must mount even when the YAML declares an asset
  // background. A real asset lookup is follow-up work, but throwing here
  // would block every protocol whose base scene uses an asset background
  // (electrophoresis_bench, microscope_view_bg, etc.).
  if ("asset" in bg) {
    host.style.background = "#F2EFE6";
    host.setAttribute("data-bg-asset-pending", bg.asset);
    return;
  }

  // Unknown form: loud failure
  throw new Error(`Unknown background form: ${JSON.stringify(bg)}`);
}
