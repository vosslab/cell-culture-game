// src/scene_runtime/renderer/affordance_candidates.ts
//
// Renderer-layer enumeration of the resolver-accepted candidate object names
// for a rendered scene. This belongs in the renderer layer because it depends
// on PipelineResult (the layout/render artifact); the protocol layer must not
// import layout types (PRIMARY_DESIGN.md layer boundary: protocol = intent,
// renderer/layout = placement).

import type { PipelineResult } from "../layout/types.js";
import type { ObjectDef } from "../layout/types.js";
import { OBJECT_LIBRARY } from "../../../generated/object_library.js";
import { is_interactable_subpart_geometry } from "./subpart_hit_surface.js";

//============================================
// Candidate enumeration (single source of truth with the click resolver)
//============================================

// Enumerate resolver-accepted placement and declared subpart target names for
// a rendered scene.
//
// Source of truth: the click resolver (click_resolver.ts) resolves a click by
// walking up via closest("[data-item-id]") and accepting the matched element's
// data-item-id value. The renderer (scene_item.tsx) stamps
// data-item-id={item.placement_name} ONLY when item.capabilities includes
// "clickable" (the capability gate and target identity contract: the DOM key is the
// unique per-placement placement_name, not the non-unique object_name), and the
// rendered item list is exactly PipelineResult.final (scene_view.tsx renders one
// SceneItem per result.final entry). So the set of resolver-accepted top-level
// targets is precisely
// { item.placement_name for item in result.final if item is clickable }. This
// helper reads that same PipelineResult.final and applies the identical
// capability gate, so the candidate set cannot drift from what the resolver
// would accept; it is not a parallel approximation. The set is placement_name
// keyed to match the affordance memo (item_target = placement_name) and the
// resolved active interaction placement name the select-highlight compares against.
//
// A clickable structured object contributes a dotted target only when its real
// generated ObjectDef declares an interactable geometry entry. The same
// capability and geometry gate is used by SubpartHitSurface, so candidate
// highlighting never advertises a target the delegated click resolver cannot
// receive. Plain dotted placement names in PipelineResult.final remain invalid;
// dotted names originate only from the declaration-owned subpart geometry.
//
// Computed once per scene mount and passed by reference into the scene items;
// per-item memos only call .has(item_target) (O(1)) and never rebuild the set.
export function enumerate_candidate_targets(
  result: PipelineResult,
  library: Readonly<Record<string, ObjectDef>> = OBJECT_LIBRARY,
): ReadonlySet<string> {
  const candidates = new Set<string>();
  for (const item of result.final) {
    const placement_name = item.placement_name;
    // Pipeline placements are top-level identities. A dotted placement would
    // collide with the target separator and cannot be a resolver target.
    if (placement_name.includes(".")) {
      continue;
    }
    // Exclude non-clickable items (decoration_only, missing-object
    // render-error items bound with capabilities: []): the renderer stamps no
    // data-item-id for them, so the resolver could never accept a click on
    // them either.
    if (!item.capabilities.includes("clickable")) {
      continue;
    }
    candidates.add(placement_name);

    const def = library[item.object_name];
    if (
      def?.subpart_geometry === undefined ||
      def.view_box === undefined ||
      def.subparts === undefined
    ) {
      continue;
    }
    for (const [subpart_name, geometry] of Object.entries(def.subpart_geometry)) {
      if (def.subparts.includes(subpart_name) && is_interactable_subpart_geometry(geometry)) {
        candidates.add(`${placement_name}.${subpart_name}`);
      }
    }
    for (const [group_name, members] of Object.entries(def.subpart_groups ?? {})) {
      if (
        members.length > 0 &&
        members.every((member) => {
          const geometry = def.subpart_geometry?.[member];
          return (
            def.subparts?.includes(member) === true &&
            geometry !== undefined &&
            is_interactable_subpart_geometry(geometry)
          );
        })
      ) {
        candidates.add(`${placement_name}.${group_name}`);
      }
    }
  }
  return candidates;
}
