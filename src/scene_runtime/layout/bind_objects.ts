// Stage 4: Bind objects.
// For each placement, look up the object in the library and resolve the asset.
// Merges layout hints (per-placement layout overrides object defaults).
// Identity fields (kind, label, capabilities) and asset aspect cannot be
// overridden.

import type {
  AssetSpecs,
  BoundPlacement,
  Diagnostics,
  LayoutHint,
  ObjectLibrary,
  PlacementAuthored,
  ResolvedLayoutHint,
} from "./types.js";

function resolveLayout(
  override: Partial<LayoutHint>,
  fromObject: LayoutHint,
  defaultWidth: number,
  labelWidth: number,
): ResolvedLayoutHint {
  const cm = override.display_width_cm ?? fromObject.display_width_cm;
  const out: ResolvedLayoutHint = {
    default_width: override.default_width ?? fromObject.default_width ?? defaultWidth,
    label_width: override.label_width ?? fromObject.label_width ?? labelWidth,
    anchor_y: override.anchor_y ?? fromObject.anchor_y ?? "bottom",
    anchor_y_offset: override.anchor_y_offset ?? fromObject.anchor_y_offset ?? 0,
  };
  if (cm !== undefined) out.display_width_cm = cm;
  // label_placement is a scene-composition concern: only a placement may author
  // it (objects stay placement-agnostic). Copy it only when authored so an
  // unauthored placement adds no JSON key, mirroring display_width_cm above.
  if (override.label_placement !== undefined) out.label_placement = override.label_placement;
  return out;
}

export function bindObjects(
  placements: PlacementAuthored[],
  library: ObjectLibrary,
  assets: AssetSpecs,
  diagnostics: Diagnostics,
): BoundPlacement[] {
  return placements.map((p): BoundPlacement => {
    const obj = library[p.object_name];
    if (!obj) {
      // Object absent from the library. Record the diagnostic and bind an
      // internal render-error card so diagnostic renders retain the placement's
      // location. Authored and generated scenes resolve object names earlier.
      diagnostics.push({
        stage: "bind",
        severity: "error",
        kind: "unknown_object",
        placement_name: p.placement_name,
        object_name: p.object_name,
      });
      return {
        ...p,
        // decoration is a real KIND so downstream layout stages treat it as a
        // normal item; "unknown" is not a valid Kind for layout.
        kind: "decoration",
        label: p.object_name,
        asset: "",
        capabilities: [],
        aspect: 1.0,
        layout: {
          default_width: 10,
          label_width: 8,
          anchor_y: "bottom",
          anchor_y_offset: 0,
        },
        _render_error: "missing-object",
      };
    }
    const asset = assets[obj.asset];
    const layout = resolveLayout(
      p.layout ?? {},
      obj.layout,
      asset?.default_width ?? 10,
      asset?.label_width ?? 8,
    );
    return {
      ...p,
      kind: obj.kind,
      label: obj.label,
      asset: obj.asset,
      capabilities: obj.capabilities,
      aspect: asset?.aspect ?? 1.0,
      layout,
    };
  });
}
