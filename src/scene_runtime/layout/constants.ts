// Layout engine constants, mirrors `docs/specs/LAYOUT_ENGINE.md` and the
// reference impl in `design_advice/pipeline.jsx`. Closed sets only.

export const ALIGN_MODES = ["left", "right", "center", "justify", "tab-stops"] as const;
export const ALIGN_STOPS = ["left", "center", "right"] as const;
export const ANCHOR_YS = ["bottom", "tip", "top"] as const;
// Closed enum: where a scene-object label renders relative to its artwork.
// top (default) seeds the label above the object; bottom is the legacy below.
export const LABEL_PLACEMENTS = ["top", "bottom"] as const;
export const DEPTHS = ["back", "mid", "front"] as const;
export const KINDS = [
  "plate",
  "bottle",
  "flask",
  "pipette",
  "rack",
  "waste",
  "equipment",
  "decoration",
] as const;
export const WORKSPACES = [
  "bench",
  "hood",
  "microscope",
  "incubator",
  "plate_reader",
  "cell_counter",
] as const;
export const CAPABILITIES = [
  "clickable",
  "material_container",
  "instrument_with_setpoint",
  "structured_surface",
  "cursor_attachable",
  "decoration_only",
] as const;
export const SCALE_SOURCES = [
  "cm_model",
  "fallback_no_workspace",
  "fallback_authored",
  "skipped_error",
] as const;
export const STAGES = [
  "normalize",
  "inheritance",
  "bind",
  "scale",
  "group",
  "horizontal",
  "vertical",
  "labels",
  "clamp",
  "meta",
] as const;
export const DIAGNOSTIC_KINDS = [
  "unknown_row",
  "unknown_object",
  "unknown_workspace",
  "unknown_zone",
  "zone_overflow_negative_gap",
  "tab_stop_overflow",
  "item_escapes_zone_vertically",
  "label_collision_residual",
  "label_row_staggered",
  "zone_clamped_to_bounds",
  "max_iterations_reached",
  // Cross-zone final-placed-item overlap: two items from DIFFERENT
  // zones landed in the same computed band and their artwork boxes coincide.
  // Emitted by diagnostics/item_overlap.ts against the FINAL item array, so it
  // fires independent of band membership (unlike the per-band checks above).
  "item_overlap",
] as const;

// Numeric constants
export const ZONE_PADDING = 1.5;
export const MIN_SCALE = 0.55;
// The vertical terminal-fallback floor. When the reflowed content extent exceeds
// the scene range, the terminal uniform object rescale shrinks every object by one
// scene-wide factor; this is the LOWEST that factor may reach. It is DISTINCT from
// MIN_SCALE (the horizontal packer floor, which stays 0.55). Set conservatively
// below the densest scene's computed requirement so every non-fixture scene fits
// through the uniform rescale without overflow. The horizontal stage keeps its own
// 0.55 floor untouched.
export const UNIFORM_RESCALE_MIN_SCALE = 0.27;
// The readable-size floor for the D2 "unfittable asset" WARNING (unfittable_asset).
// An item whose final rendered scale falls BELOW this value only reaches that state
// through the terminal uniform rescale (the horizontal stage floors at MIN_SCALE),
// so it signals an object shrunk past a comfortably readable size. It is tied to
// MIN_SCALE on purpose: MIN_SCALE is the largest shrink the horizontal packer will
// apply, so anything below it is a sub-floor rescale, i.e. the asset could not be
// fit at a readable size. The signal is advisory only (failBuild false); it makes
// the degradation legible without blocking the build on the dense shrink scenes.
export const READABLE_FLOOR_SCALE = MIN_SCALE;
// labelDominant review threshold. After the uniform rescale, a scene is
// flagged labelDominant when its label strip is at least this fraction of the
// scaled object height (labelBoxHeight / scaledObjectHeight >= ratio). A label
// that grows visually dominant relative to its shrunken object is surfaced for
// review rather than silently shipped.
export const LABEL_DOMINANT_RATIO = 0.35;
export const MAX_FOOTPRINT_RATIO = 2.5;
export const PX_PER_SCENE_PERCENT = 11.52;
// Average glyph advance as a fraction of label_font_size, used by wrap_label
// and the stagger reserve to estimate label width. Tuned for the condensed
// proportional face PT Sans Narrow (see render_label.ts); its mean advance is
// ~0.45em, much narrower than the 0.6 used when labels were monospace.
export const AVG_CHAR_WIDTH_PCT = 0.45;
export const MAX_LAYOUT_PASSES = 3;
export const LAYOUT_SHRINK_FACTOR = 0.9;

// Canvas-relative label font sizing. The live PNG render path mounts the scene
// root then calls renderScene without a viewport, so the renderer derives a
// font size from the root's actual pixel width. An absolute 16px on a ~1920px
// canvas is illegible (~0.8% of width); a fraction of canvas width scales with
// the render surface. LABEL_FONT_MIN_PX is the floor for small panels.
export const LABEL_FONT_WIDTH_FRACTION = 0.012;
export const LABEL_FONT_MIN_PX = 12;

// Vertical label stagger: when adjacent labels collide horizontally, lower
// labels drop to a new row. Row height is a multiple of the label line height,
// expressed in scene-percent. 2.2 spaces a 2-line label clear of the row below.
export const LABEL_LINE_HEIGHT_PCT = 2.2;

export const DEPTH_SCALE = { back: 0.8, mid: 1.0, front: 1.1 } as const;
export const DEPTH_BASELINE_OFFSET = { back: -4, mid: 0, front: 4 } as const;
// The depth spacing magnitude: the vertical step between two adjacent depth
// bands (mid -> front = 4). The zone-band reflow stage reuses this as the
// gap between stacked depth-tier rows (tierGap), so tier spacing matches the
// engine's existing depth spacing instead of inventing a new constant.
export const DEPTH_TIER_GAP = DEPTH_BASELINE_OFFSET.front - DEPTH_BASELINE_OFFSET.mid;
export const DEFAULT_VIEWPORT = { w: 1920, h: 1080 } as const;
export const DEFAULT_SCENE_BOUNDS = {
  left: 1,
  right: 99,
  top: 5,
  bottom: 95,
} as const;
export const DEFAULT_LAYOUT_RULES = {
  label_font_size: 16,
  label_line_height: 1.1,
  label_offset_y: 4,
  zone_gap: 2,
  default_align_stop: "center",
} as const;

// Per-workspace px_per_cm (SCALING_MODEL.md). Author writes display_width_cm
// on object; engine multiplies by per-workspace px_per_cm.
// Calibrated empirically so a fully-populated scene
// lands in 15-70% occupancy with no clip or item_escapes_zone diagnostics.
// bench: raised from the old 3.2 fallback width to 7.0;
//   at 7.0 a vortex (22 cm) -> width_scale ~2.2 -> ~13% of canvas, a media
//   bottle (12 cm) -> ~6%; 7 bench instruments together occupy ~55-65%.
// hood: kept at 8.0; hood items are mostly bottles and pipettes which are
//   smaller (3-12 cm) so 8.0 gives reasonable per-item widths (~3-8%).
// microscope: raised to 10.0 to make the microscope instrument (35 cm)
//   occupy ~25% of the workspace -- visible and prominent.
// incubator: raised to 9.0; incubator chamber items are medium-sized.
// plate_reader: kept at 8.0; plate reader (42 cm) -> ~25% at 8.0.
// cell_counter: raised to 9.0; cell counter (38 cm) -> ~24% at 9.0.
export const WORKSPACE_PX_PER_CM: Record<(typeof WORKSPACES)[number], number> = {
  bench: 5.5,
  hood: 8.0,
  microscope: 10.0,
  incubator: 9.0,
  plate_reader: 8.0,
  cell_counter: 9.0,
};
