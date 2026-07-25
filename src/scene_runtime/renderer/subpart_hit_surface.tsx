// src/scene_runtime/renderer/subpart_hit_surface.tsx
//
// Generic visible click surfaces for declared structured-object subparts.
// Geometry belongs to the object declaration; this renderer only turns valid
// generated circle/rect geometry into SVG hit shapes at the active placement.

import type { Accessor, JSXElement } from "solid-js";
import { createMemo, For } from "solid-js";

import type { ObjectDef, SubpartGeometry } from "../layout/types.js";
import { type ActiveAffordanceAccessor, compute_affordance_kind } from "../protocol/affordance.js";

// A hit surface exists only for a complete, finite generated geometry entry.
// This defensive boundary means malformed generated data degrades to no hit
// target instead of creating a broad or phantom click target.
export function is_interactable_subpart_geometry(geometry: SubpartGeometry): boolean {
  if (geometry.shape === "circle") {
    return (
      Number.isFinite(geometry.cx) &&
      Number.isFinite(geometry.cy) &&
      Number.isFinite(geometry.r) &&
      geometry.r > 0
    );
  }
  return (
    Number.isFinite(geometry.x) &&
    Number.isFinite(geometry.y) &&
    Number.isFinite(geometry.w) &&
    Number.isFinite(geometry.h) &&
    geometry.w > 0 &&
    geometry.h > 0
  );
}

// A whole-object interaction must retain the item's existing click target.
// Subpart shapes become pointer targets only while the active target resolves
// to a declared subpart of this exact placement.
export function active_target_is_placement_subpart(
  active_target: string | null,
  placement_name: string,
): active_target is string {
  if (active_target === null) {
    return false;
  }
  const prefix = `${placement_name}.`;
  return active_target.startsWith(prefix) && active_target.length > prefix.length;
}

function SubpartHitShape(props: {
  placement_name: string;
  subpart_name: string;
  geometry: SubpartGeometry;
  activeAffordance?: ActiveAffordanceAccessor | undefined;
  candidateTargets: ReadonlySet<string>;
  hits_enabled: Accessor<boolean>;
}): JSXElement {
  const subpart_target = `${props.placement_name}.${props.subpart_name}`;
  const affordance_kind = createMemo<"active" | "candidate" | "none">(() => {
    const affordance = props.activeAffordance?.();
    return compute_affordance_kind({
      active_target: affordance?.active_target ?? null,
      active_gesture: affordance?.active_gesture ?? null,
      item_target: subpart_target,
      candidate_targets: props.candidateTargets,
    });
  });

  const geometry = props.geometry;
  if (geometry.shape === "circle") {
    return (
      <circle
        class="subpart-hit-target"
        data-subpart-hit="true"
        data-subpart-name={props.subpart_name}
        data-item-id={props.hits_enabled() ? subpart_target : undefined}
        data-subpart-affordance={affordance_kind()}
        cx={geometry.cx}
        cy={geometry.cy}
        r={geometry.r}
      />
    );
  }
  return (
    <rect
      class="subpart-hit-target"
      data-subpart-hit="true"
      data-subpart-name={props.subpart_name}
      data-item-id={props.hits_enabled() ? subpart_target : undefined}
      data-subpart-affordance={affordance_kind()}
      x={geometry.x}
      y={geometry.y}
      width={geometry.w}
      height={geometry.h}
    />
  );
}

// Render the declaration-owned SVG hit surface. The base artwork and material
// overlays remain pointer-events:none; these shapes are the only exact subpart
// pointer targets and are enabled only for an active subpart interaction. Inert
// shapes retain their geometry but do not advertise data-item-id: that attribute
// is the delegated pointer-target identity, not a catalog of possible future
// targets. The protocol layer still preserves the semantic distinction between
// an authored `click` gesture and an authored `select` gesture.
export function SubpartHitSurface(props: {
  def: ObjectDef;
  placement_name: string;
  activeAffordance?: ActiveAffordanceAccessor | undefined;
  candidateTargets: ReadonlySet<string>;
}): JSXElement | null {
  if (props.def.subpart_geometry === undefined || props.def.view_box === undefined) {
    return null;
  }

  const declared_subparts = new Set(props.def.subparts ?? []);
  const geometry_entries = Object.entries(props.def.subpart_geometry).filter(
    ([subpart_name, geometry]) =>
      declared_subparts.has(subpart_name) && is_interactable_subpart_geometry(geometry),
  );
  if (geometry_entries.length === 0) {
    return null;
  }

  const hits_enabled = createMemo<boolean>(() => {
    const affordance = props.activeAffordance?.();
    const active_target = affordance?.active_target ?? null;
    if (!active_target_is_placement_subpart(active_target, props.placement_name)) {
      return false;
    }
    const active_subpart = active_target.slice(props.placement_name.length + 1);
    return geometry_entries.some(([subpart_name]) => subpart_name === active_subpart);
  });
  const view_box = props.def.view_box;

  return (
    <svg
      class="subpart-hit-surface"
      data-subpart-hit-surface={props.placement_name}
      data-subpart-hits-enabled={hits_enabled() ? "true" : "false"}
      viewBox={`${view_box.min_x} ${view_box.min_y} ${view_box.width} ${view_box.height}`}
      preserveAspectRatio="xMidYMid meet"
      aria-hidden="true"
    >
      <For each={geometry_entries}>
        {([subpart_name, geometry]) => (
          <SubpartHitShape
            placement_name={props.placement_name}
            subpart_name={subpart_name}
            geometry={geometry}
            activeAffordance={props.activeAffordance}
            candidateTargets={props.candidateTargets}
            hits_enabled={hits_enabled}
          />
        )}
      </For>
    </svg>
  );
}
