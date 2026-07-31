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
// to a declared subpart of this exact placement; then every declared sibling
// remains addressable so a wrong click reaches ordinary protocol validation.
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

export interface ActiveSubpartSelection {
  target_name: string;
  member_names: string[];
  is_group: boolean;
}

// Resolve one active dotted target against its declaration-owned geometry.
// A dotted target is a promise that the learner can point at THAT named part,
// not permission to quietly fall back to the containing object. Keep this
// assertion shared by SceneItem and the hit surface: SceneItem catches an
// absent object declaration, while this component owns the actual SVG shapes.
//
// Returning null means this placement is not the current dotted target. Any
// dotted target for this placement must return its declared subpart name or
// throw a precise content/runtime error. Throwing is intentional: a missing
// exact target is a broken protocol, and an inert parent-object click would
// conceal it from both students and walkthrough validation. A declared group
// resolves to every one of its concrete members; it never falls back to the
// parent object or to an invisible rectangle covering unrelated subparts.
export function resolve_active_subpart_selection(
  def: ObjectDef | undefined,
  placement_name: string,
  active_target: string | null,
): ActiveSubpartSelection | null {
  if (!active_target_is_placement_subpart(active_target, placement_name)) {
    return null;
  }

  const target_name = active_target.slice(placement_name.length + 1);
  if (def === undefined) {
    throw new Error(
      `Exact target "${active_target}" has no object declaration for placement "${placement_name}"`,
    );
  }
  if (def.view_box === undefined || def.subpart_geometry === undefined) {
    throw new Error(
      `Exact target "${active_target}" requires declared subpart geometry and view_box on object "${def.object_name}"`,
    );
  }
  const group_members = def.subpart_groups?.[target_name];
  const member_names =
    group_members === undefined
      ? def.subparts?.includes(target_name)
        ? [target_name]
        : null
      : group_members;
  if (member_names === null) {
    throw new Error(
      `Exact target "${active_target}" names undeclared subpart or group "${target_name}" on object "${def.object_name}"`,
    );
  }
  if (member_names.length === 0) {
    throw new Error(`Exact target "${active_target}" resolves to an empty declared group`);
  }
  for (const member_name of member_names) {
    if (!def.subparts?.includes(member_name)) {
      throw new Error(
        `Exact target "${active_target}" group member "${member_name}" is not a declared subpart on object "${def.object_name}"`,
      );
    }
    const geometry = def.subpart_geometry[member_name];
    if (geometry === undefined || !is_interactable_subpart_geometry(geometry)) {
      throw new Error(
        `Exact target "${active_target}" member "${member_name}" has no interactable declared geometry on object "${def.object_name}"`,
      );
    }
  }
  return {
    target_name,
    member_names: [...member_names],
    is_group: group_members !== undefined,
  };
}

// Compatibility helper for callers that need only the authored suffix. The
// full group/member resolution remains centralized above.
export function assert_active_subpart_geometry(
  def: ObjectDef | undefined,
  placement_name: string,
  active_target: string | null,
): string | null {
  return resolve_active_subpart_selection(def, placement_name, active_target)?.target_name ?? null;
}

function SubpartHitShape(props: {
  placement_name: string;
  subpart_name: string;
  geometry: SubpartGeometry;
  activeAffordance?: ActiveAffordanceAccessor | undefined;
  candidateTargets: ReadonlySet<string>;
  hits_enabled: Accessor<boolean>;
  active_selection: Accessor<ActiveSubpartSelection | null>;
}): JSXElement {
  const subpart_target = `${props.placement_name}.${props.subpart_name}`;
  const delegated_target = createMemo<string>(() => {
    const selection = props.active_selection();
    if (selection?.member_names.includes(props.subpart_name) === true) {
      return `${props.placement_name}.${selection.target_name}`;
    }
    return subpart_target;
  });
  const active_group_target = createMemo<string | undefined>(() => {
    const selection = props.active_selection();
    if (selection?.is_group === true && selection.member_names.includes(props.subpart_name)) {
      return `${props.placement_name}.${selection.target_name}`;
    }
    return undefined;
  });
  const affordance_kind = createMemo<"active" | "candidate" | "none">(() => {
    const affordance = props.activeAffordance?.();
    return compute_affordance_kind({
      active_target: affordance?.active_target ?? null,
      active_gesture: affordance?.active_gesture ?? null,
      item_target: delegated_target(),
      candidate_targets: props.candidateTargets,
    });
  });

  // Keep an exact subpart in the original object's coordinate system. SceneItem
  // magnifies the original structured object until the directed subpart has a
  // 24px core; these shapes then use only their exact declared fill area so
  // adjacent siblings cannot steal one another's click through overlapping
  // invisible padding. The visible focus shape has pointer-events:none, so it
  // cannot become a second interactive representation of the subpart.
  const pad_style = createMemo<Record<string, string>>(() => ({
    fill: "transparent",
    stroke: "transparent",
    "stroke-width": "0px",
    // `all` accepts the transparent declared fill, making the whole exact
    // region continuous while preserving sibling addressability.
    "pointer-events": props.hits_enabled() ? "all" : "none",
  }));
  const focus_style = createMemo<Record<string, string>>(() => {
    const kind = affordance_kind();
    if (kind === "active") {
      return {
        fill: "rgba(245, 166, 35, 0.2)",
        stroke: "#f5a623",
        "stroke-width": "2px",
        "vector-effect": "non-scaling-stroke",
        "pointer-events": "none",
      };
    }
    if (kind === "candidate") {
      return {
        fill: "rgba(37, 99, 235, 0.14)",
        stroke: "#2563eb",
        "stroke-width": "2px",
        "stroke-dasharray": "3 2",
        "vector-effect": "non-scaling-stroke",
        "pointer-events": "none",
      };
    }
    return { fill: "transparent", stroke: "transparent", "pointer-events": "none" };
  });
  const geometry = props.geometry;
  if (geometry.shape === "circle") {
    return (
      <g
        class="subpart-hit-group"
        data-subpart-hit="true"
        data-subpart-name={props.subpart_name}
        data-item-id={props.hits_enabled() ? delegated_target() : undefined}
        data-subpart-group-target={active_group_target()}
        data-subpart-affordance={affordance_kind()}
      >
        <circle
          class="subpart-hit-target"
          cx={geometry.cx}
          cy={geometry.cy}
          r={geometry.r}
          style={pad_style()}
        />
        <circle
          class="subpart-focus-indicator"
          data-subpart-affordance={affordance_kind()}
          cx={geometry.cx}
          cy={geometry.cy}
          r={geometry.r}
          style={focus_style()}
        />
      </g>
    );
  }
  return (
    <g
      class="subpart-hit-group"
      data-subpart-hit="true"
      data-subpart-name={props.subpart_name}
      data-item-id={props.hits_enabled() ? delegated_target() : undefined}
      data-subpart-group-target={active_group_target()}
      data-subpart-affordance={affordance_kind()}
    >
      <rect
        class="subpart-hit-target"
        x={geometry.x}
        y={geometry.y}
        width={geometry.w}
        height={geometry.h}
        style={pad_style()}
      />
      <rect
        class="subpart-focus-indicator"
        data-subpart-affordance={affordance_kind()}
        x={geometry.x}
        y={geometry.y}
        width={geometry.w}
        height={geometry.h}
        style={focus_style()}
      />
    </g>
  );
}

// Render the declaration-owned SVG hit surface. The base artwork and material
// overlays remain pointer-events:none; these shapes are the only exact subpart
// pointer targets and are enabled only for an active subpart interaction. Once
// enabled, every declared sibling advertises its own data-item-id so the normal
// delegated click resolver can reject a wrong target. The protocol layer still
// preserves the semantic distinction between an authored `click` gesture and
// an authored `select` gesture.
export function SubpartHitSurface(props: {
  def: ObjectDef;
  placement_name: string;
  activeAffordance?: ActiveAffordanceAccessor | undefined;
  candidateTargets: ReadonlySet<string>;
}): JSXElement | null {
  const active_selection = createMemo<ActiveSubpartSelection | null>(() => {
    const active_target = props.activeAffordance?.().active_target ?? null;
    return resolve_active_subpart_selection(props.def, props.placement_name, active_target);
  });

  if (props.def.subpart_geometry === undefined || props.def.view_box === undefined) {
    // Evaluate the memo before returning so an active dotted target fails
    // loudly rather than disappearing behind the whole-object target.
    active_selection();
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
    return active_selection() !== null;
  });
  const view_box = props.def.view_box;

  return (
    <svg
      class="subpart-hit-surface"
      data-subpart-hit-surface={props.placement_name}
      data-subpart-hits-enabled={hits_enabled() ? "true" : "false"}
      viewBox={`${view_box.min_x} ${view_box.min_y} ${view_box.width} ${view_box.height}`}
      preserveAspectRatio="xMidYMid meet"
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
            active_selection={active_selection}
          />
        )}
      </For>
    </svg>
  );
}
