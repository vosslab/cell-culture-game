// Derived interaction geometry for precomputed scenes.
//
// Visual layout and learner hit areas are different contracts: SVG artwork
// stays at its authored visual box, while clickable placements receive a
// transparent envelope with a 44 CSS-pixel core. This module is pure so the
// precompute pipeline can validate the same artifact the browser consumes.

import type {
  ComputedItem,
  InteractionEnvelopeGeometry,
  SceneInteractionGeometry,
} from "./types.js";

export const INTERACTION_HIT_CORE_PX = 44;
const SCENE_ASPECT_RATIO = 16 / 9;
const MINIMUM_FRAME_HEIGHT_PX = 180;

interface EnvelopeRectPx {
  placement_name: string;
  left: number;
  right: number;
  top: number;
  bottom: number;
}

function envelope_for_item(item: ComputedItem): InteractionEnvelopeGeometry {
  return {
    placement_name: item.placement_name,
    center_x_percent: item._centerX,
    center_y_percent: item._top + item._height / 2,
    visual_width_percent: item._visualWidth,
    visual_height_percent: item._height,
  };
}

function rect_at_frame(
  envelope: InteractionEnvelopeGeometry,
  width: number,
  height: number,
): EnvelopeRectPx {
  const center_x = (envelope.center_x_percent / 100) * width;
  const center_y = (envelope.center_y_percent / 100) * height;
  const envelope_width = Math.max(
    INTERACTION_HIT_CORE_PX,
    (envelope.visual_width_percent / 100) * width,
  );
  const envelope_height = Math.max(
    INTERACTION_HIT_CORE_PX,
    (envelope.visual_height_percent / 100) * height,
  );
  return {
    placement_name: envelope.placement_name,
    left: center_x - envelope_width / 2,
    right: center_x + envelope_width / 2,
    top: center_y - envelope_height / 2,
    bottom: center_y + envelope_height / 2,
  };
}

function has_positive_overlap(a: EnvelopeRectPx, b: EnvelopeRectPx): boolean {
  return a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;
}

function frame_is_valid(
  envelopes: readonly InteractionEnvelopeGeometry[],
  width: number,
  height: number,
): boolean {
  const rects = envelopes.map((envelope) => rect_at_frame(envelope, width, height));
  if (
    rects.some(
      (rect) => rect.left < 0 || rect.top < 0 || rect.right > width || rect.bottom > height,
    )
  ) {
    return false;
  }
  for (let index = 0; index < rects.length; index += 1) {
    for (let other = index + 1; other < rects.length; other += 1) {
      if (has_positive_overlap(rects[index]!, rects[other]!)) {
        return false;
      }
    }
  }
  return true;
}

// Find the smallest 16:9 scene frame (up to the canonical 1080px height) in
// which every clickable envelope lies inside the canvas and clickable envelopes
// are unambiguous. A scene with overlapping visual clickable geometry cannot be
// repaired by a larger transparent target and fails loudly during precompute.
function minimum_valid_frame(envelopes: readonly InteractionEnvelopeGeometry[]): {
  width_px: number;
  height_px: number;
} | null {
  if (envelopes.length === 0) {
    return {
      width_px: Math.ceil(MINIMUM_FRAME_HEIGHT_PX * SCENE_ASPECT_RATIO),
      height_px: MINIMUM_FRAME_HEIGHT_PX,
    };
  }
  for (let height = MINIMUM_FRAME_HEIGHT_PX; height <= 1080; height += 1) {
    // The browser consumes this serialized integer width, not an ideal
    // fractional 16:9 value. Validate the exact emitted frame so rounding can
    // never turn just-touching envelopes into an ambiguous overlap.
    const width = Math.ceil(height * SCENE_ASPECT_RATIO);
    if (frame_is_valid(envelopes, width, height)) {
      return { width_px: width, height_px: height };
    }
  }
  return null;
}

export function derive_scene_interaction_geometry(
  items: readonly ComputedItem[],
): SceneInteractionGeometry {
  const clickable = items.filter((item) => item.capabilities.includes("clickable"));
  const envelope_list = clickable.map(envelope_for_item);
  const envelopes: Record<string, InteractionEnvelopeGeometry> = {};
  for (const envelope of envelope_list) {
    envelopes[envelope.placement_name] = envelope;
  }
  const minimum_frame = minimum_valid_frame(envelope_list);
  if (minimum_frame === null) {
    return {
      envelopes,
      valid: false,
      issues: [
        {
          kind: "no_valid_frame",
          placements: envelope_list.map((envelope) => envelope.placement_name),
        },
      ],
    };
  }
  return {
    minimum_frame: { hit_core_px: INTERACTION_HIT_CORE_PX, ...minimum_frame },
    envelopes,
    valid: true,
  };
}

// The shared layout engine must remain usable for intentionally overfull
// diagnostics fixtures. The production precompute boundary calls this explicit
// gate before it emits browser-consumed geometry.
export function assert_valid_scene_interaction_geometry(geometry: SceneInteractionGeometry): void {
  if (!geometry.valid) {
    const details = geometry.issues
      .map((issue) => `${issue.kind}: ${issue.placements.join(", ")}`)
      .join("; ");
    throw new Error(`interaction_geometry: ${details}`);
  }
}
