// Declarative object-level material renderer. It owns only the SVG mutation
// needed to place authored effects into an already injected SVG instance; state
// and material resolution stay pure in visual_state_resolver.ts.

import type { AnchorMaterialEffect } from "./visual_state_resolver.js";
import { resolveSvgAnchor, type ResolvedSvgAnchor } from "./inject_svg.js";

const SVG_NS = "http://www.w3.org/2000/svg";
const OVERLAY_ATTR = "data-anchor-material-overlay";

interface MaterialOverlayInstance {
  group: SVGGElement;
  fields: Map<string, SVGRectElement>;
}

// Per injected SVG host. The overlay structure is created once and subsequent
// state changes update attributes on the same rects, matching the static-overlay
// contract (never remove/reorder SVG nodes on each volume write).
const instances = new WeakMap<HTMLElement, MaterialOverlayInstance>();

function anchor_box(anchor: Element, field_name: string): SVGRect {
  // The anchor contract normally uses a hidden <rect>. getBBox() on a
  // display:none element has browser-dependent behavior, so read an authored
  // rectangle's geometry directly. This remains a geometry read, not state.
  if (anchor instanceof SVGRectElement) {
    const box = {
      x: anchor.x.baseVal.value,
      y: anchor.y.baseVal.value,
      width: anchor.width.baseVal.value,
      height: anchor.height.baseVal.value,
    } as SVGRect;
    if (!Number.isFinite(box.x) || !Number.isFinite(box.y) || box.width <= 0 || box.height <= 0) {
      throw new Error(
        `anchor material renderer: '${field_name}' bounds anchor has invalid geometry`,
      );
    }
    return box;
  }
  if (!(anchor instanceof SVGGraphicsElement)) {
    throw new Error(`anchor material renderer: '${field_name}' bounds anchor is not SVG geometry`);
  }
  const box = anchor.getBBox();
  if (!Number.isFinite(box.x) || !Number.isFinite(box.y) || box.width <= 0 || box.height <= 0) {
    throw new Error(`anchor material renderer: '${field_name}' bounds anchor has invalid geometry`);
  }
  return box;
}

function required_anchor(
  host: HTMLElement,
  bare_id: string,
  field_name: string,
): ResolvedSvgAnchor {
  const anchor = resolveSvgAnchor(host, bare_id);
  if (anchor === null) {
    throw new Error(`anchor material renderer: '${field_name}' requires SVG anchor '${bare_id}'`);
  }
  return anchor;
}

function overlay_parent(host: HTMLElement, svg: SVGSVGElement): SVGElement {
  const overlay_root = resolveSvgAnchor(host, "overlay_root");
  if (overlay_root === null) {
    return svg;
  }
  if (!(overlay_root.element instanceof SVGGElement)) {
    throw new Error("anchor material renderer: overlay_root must be an SVG group");
  }
  if (overlay_root.element.ownerSVGElement !== svg) {
    throw new Error("anchor material renderer: overlay_root belongs to another SVG root");
  }
  return overlay_root.element;
}

function hide_all_fields(instance: MaterialOverlayInstance): void {
  for (const rect of instance.fields.values()) {
    rect.setAttribute("display", "none");
  }
}

function rect_for_effect(
  instance: MaterialOverlayInstance,
  host: HTMLElement,
  effect: AnchorMaterialEffect,
): SVGRectElement {
  if (effect.target !== "anchor_liquid_bounds") {
    throw new Error(
      `anchor material renderer: '${effect.field_name}' target must be anchor_liquid_bounds`,
    );
  }
  let rect = instance.fields.get(effect.field_name);
  if (rect === undefined) {
    rect = document.createElementNS(SVG_NS, "rect");
    rect.setAttribute("data-anchor-material-field", effect.field_name);
    rect.setAttribute("pointer-events", "none");
    instance.group.append(rect);
    instance.fields.set(effect.field_name, rect);
  }
  const bounds_anchor = required_anchor(host, "anchor_liquid_bounds", effect.field_name);
  const bounds = anchor_box(bounds_anchor.element, effect.field_name);
  const fill_height = (bounds.height * effect.fill_percent) / 100;
  rect.setAttribute("data-material-name", effect.material_name);
  rect.setAttribute("x", String(bounds.x));
  rect.setAttribute("y", String(bounds.y + bounds.height - fill_height));
  rect.setAttribute("width", String(bounds.width));
  rect.setAttribute("height", String(fill_height));
  // `fill` is intentionally the registry scalar itself: a screenshot/test can
  // verify the authored material identity without a renderer-created palette.
  rect.setAttribute("fill", effect.color ?? "transparent");
  rect.setAttribute(
    "display",
    effect.color === null || effect.fill_percent <= 0 ? "none" : "inline",
  );
  if (effect.clip === "anchor_liquid_clip") {
    const clip = required_anchor(host, "anchor_liquid_clip", effect.field_name);
    clip.applyClipPath(rect);
  } else if (effect.clip !== undefined) {
    throw new Error(
      `anchor material renderer: '${effect.field_name}' clip must be anchor_liquid_clip`,
    );
  }
  return rect;
}

// Creates the instance overlay once, then updates declared attributes in place.
// Throws on missing or malformed anchors; SceneItem catches and routes that
// error through its normal visible degradation channel.
export function render_anchor_material_effects(
  host: HTMLElement,
  effects: readonly AnchorMaterialEffect[],
): void {
  const existing = instances.get(host);
  if (effects.length === 0) {
    if (existing !== undefined) {
      hide_all_fields(existing);
    }
    return;
  }
  if (existing !== undefined) {
    hide_all_fields(existing);
  }
  const first_bounds = required_anchor(host, "anchor_liquid_bounds", effects[0]!.field_name);
  if (!(first_bounds.element instanceof SVGElement)) {
    throw new Error("anchor material renderer: bounds anchor is not an SVG element");
  }
  const svg = first_bounds.element.ownerSVGElement;
  if (svg === null) {
    throw new Error("anchor material renderer: bounds anchor has no SVG root");
  }
  const parent = overlay_parent(host, svg);
  let instance = existing;
  if (
    instance === undefined ||
    instance.group.ownerSVGElement !== svg ||
    !svg.contains(instance.group) ||
    instance.group.parentNode !== parent
  ) {
    const group = document.createElementNS(SVG_NS, "g");
    group.setAttribute(OVERLAY_ATTR, "true");
    parent.append(group);
    instance = { group, fields: new Map<string, SVGRectElement>() };
    instances.set(host, instance);
  }
  // Hide first so a removed effect, a partial update, or a later thrown effect
  // cannot leave an earlier state visible. The group and rect nodes stay in
  // place; only declared attributes change.
  hide_all_fields(instance);
  try {
    for (const effect of effects) {
      rect_for_effect(instance, host, effect);
    }
  } catch (err) {
    hide_all_fields(instance);
    throw err;
  }
}
