// src/scene_runtime/protocol/target_adapter.ts
//
// The single protocol-target-to-DOM identity adapter.
//
// Identity contract (docs/archive/decisions/target_identity.md):
//   - placement_name is the DOM and target key. It is unique per placement
//     within a scene, so it is the only key that stays unambiguous when a scene
//     places the same object more than once.
//   - object_name is the capability / asset / STATE-store lookup key. It is
//     deliberately NON-unique (two placements of one object share one object).
//   - A protocol `target` is a semantic name. It resolves through THIS adapter
//     to exactly one placement_name (for the DOM / click / highlight side) and
//     to exactly one object_name (for the state store / object library side).
//
// This module is the ONLY place that resolution happens. The step machine
// (equality + state reads), the snapshot reducer (active interaction action),
// and the click resolver (DOM read-back) all route through an adapter built
// here from the current scene's placements. Building it per scene keeps the
// resolution scene-scoped: the same authored target resolves against whatever
// scene is currently mounted.
//
// Fail-loud rule: an authored target that names a NON-unique object_name (an
// object placed more than once) with no disambiguating placement_name cannot
// resolve to a single DOM element. That throws AmbiguousTargetError rather than
// silently picking one placement. Naming a specific placement_name resolves
// uniquely (the disambiguation path).
//
// Layer boundary (docs/PRIMARY_DESIGN.md): this is protocol-layer identity
// resolution over a flat list of {object_name, placement_name} bindings. It
// imports no layout, renderer, or store module; the construction layer
// (src/protocol_host.tsx) supplies the bindings from the mounted scene.

//============================================
// Public types
//============================================

// One scene placement binding: a placement's scene-unique DOM key
// (placement_name) and the object it renders (object_name). The construction
// layer projects these from the mounted scene's ComputedItems.
export interface PlacementBinding {
  readonly object_name: string;
  readonly placement_name: string;
}

// The DOM attribute carrying the unique per-placement click key. The renderer
// (scene_item.tsx) stamps it with item.placement_name on clickable items; the
// click resolver reads it back through placement_name_from_element. Centralized
// here so the DOM click key has one canonical name.
export const TARGET_DOM_ATTR = "data-item-id";

// The resolver seam consumed by the step machine and the snapshot reducer.
// resolve_to_placement maps a semantic/object target to its unique DOM
// placement_name; resolve_to_object maps a semantic/placement target back to
// its object_name (the state-store / object-library key). Both preserve a
// ".<subpart>" suffix, resolving only the prefix. has_target reports whether
// the target's prefix (placement_name or object_name) is known to the
// currently mounted scene at all -- the load-time target-existence invariant
// (target_existence_check.ts) is the sole consumer.
export interface TargetAdapter {
  resolve_to_placement(target: string): string;
  resolve_to_object(target: string): string;
  has_target(target: string): boolean;
  // Report every placement_name the target's prefix resolves to in this scene:
  // exactly one for an explicit placement_name prefix, the object's full
  // placement list for an object_name prefix (length > 1 is the ambiguous
  // case), and an empty list for an unknown prefix. The load-time
  // ambiguous-target invariant (target_existence_check.ts) reads this to reject
  // an authored target that names an object placed more than once, promoting
  // resolve_to_placement's mid-walk AmbiguousTargetError to a named load-time
  // error.
  placements_for(target: string): readonly string[];
}

// Thrown when a semantic target names a NON-unique object_name with no
// disambiguating placement_name, so it cannot resolve to a single DOM element.
export class AmbiguousTargetError extends Error {
  constructor(object_name: string, placement_names: readonly string[]) {
    const list = placement_names.join(", ");
    super(
      `Ambiguous protocol target "${object_name}": it names an object placed ` +
        `${placement_names.length} times (placements: ${list}). Name one ` +
        `placement_name to disambiguate; the object_name cannot be a DOM key.`,
    );
    this.name = "AmbiguousTargetError";
  }
}

//============================================
// Subpart split
//============================================

// Split a target into its prefix (object_name or placement_name) and an
// optional ".<subpart>" suffix. A subpart target like "well_plate_96.A1" keeps
// its suffix; only the prefix is resolved. A prefix-only target has an empty
// suffix. Only the FIRST "." separates the prefix, so a subpart name is passed
// through verbatim.
function split_subpart(target: string): { prefix: string; suffix: string } {
  const dot_index = target.indexOf(".");
  if (dot_index === -1) {
    return { prefix: target, suffix: "" };
  }
  const prefix = target.slice(0, dot_index);
  const suffix = target.slice(dot_index);
  return { prefix, suffix };
}

//============================================
// Adapter construction
//============================================

// Build the adapter from a scene's placement bindings. Constructs the lookup
// maps once; the returned resolvers are pure closures over them.
export function build_target_adapter(bindings: readonly PlacementBinding[]): TargetAdapter {
  // placement_name -> object_name. placement_names are unique per scene, so this
  // is a one-to-one reverse map.
  const placement_to_object = new Map<string, string>();
  // object_name -> its placement_names. An object placed more than once has a
  // list length > 1, which is the ambiguous case.
  const object_to_placements = new Map<string, string[]>();

  for (const binding of bindings) {
    placement_to_object.set(binding.placement_name, binding.object_name);
    const existing = object_to_placements.get(binding.object_name);
    if (existing === undefined) {
      object_to_placements.set(binding.object_name, [binding.placement_name]);
    } else {
      existing.push(binding.placement_name);
    }
  }

  // Resolve a semantic/object target to its unique DOM placement_name. Rules,
  // in order: an explicit placement_name resolves to itself; an object_name
  // auto-derives to its single placement (fail loud when placed more than once);
  // an unknown prefix passes through unchanged so the caller's own equality /
  // DOM lookup reports the mismatch (this adapter is not a name validator).
  function resolve_to_placement(target: string): string {
    const { prefix, suffix } = split_subpart(target);
    // Explicit placement wins: the author named a specific placement.
    if (placement_to_object.has(prefix)) {
      return target;
    }
    const placements = object_to_placements.get(prefix);
    if (placements !== undefined) {
      if (placements.length > 1) {
        throw new AmbiguousTargetError(prefix, placements);
      }
      // Length is exactly 1 here (an empty list is never stored).
      const only = placements[0];
      if (only === undefined) {
        return target;
      }
      return only + suffix;
    }
    // Unknown prefix (e.g. a target for a scene not currently mounted): identity.
    return target;
  }

  // Resolve a semantic/placement target back to its object_name (the state-store
  // and object-library key). A placement_name maps to its object; an object_name
  // is already the object key (identity); an unknown prefix passes through.
  function resolve_to_object(target: string): string {
    const { prefix, suffix } = split_subpart(target);
    const object_name = placement_to_object.get(prefix);
    if (object_name !== undefined) {
      return object_name + suffix;
    }
    // Already an object_name, or unknown: identity (object_name is the object key).
    return target;
  }

  // Report whether the target's prefix resolves to a known placement or a
  // known (possibly ambiguous) object in this scene. Ambiguity itself is
  // reported by resolve_to_placement's AmbiguousTargetError; has_target only
  // answers the existence question the load-time invariant needs.
  function has_target(target: string): boolean {
    const { prefix } = split_subpart(target);
    return placement_to_object.has(prefix) || object_to_placements.has(prefix);
  }

  // List the placement_names the target's prefix resolves to. An explicit
  // placement_name prefix resolves to itself (length 1, always unique). An
  // object_name prefix resolves to every placement of that object (length > 1
  // is ambiguous). An unknown prefix resolves to nothing (empty list). The
  // load-time invariant uses length > 1 to reject an ambiguous authored target
  // and reports the competing placements in its error.
  function placements_for(target: string): readonly string[] {
    const { prefix } = split_subpart(target);
    if (placement_to_object.has(prefix)) {
      return [prefix];
    }
    const placements = object_to_placements.get(prefix);
    if (placements !== undefined) {
      return placements;
    }
    return [];
  }

  return { resolve_to_placement, resolve_to_object, has_target, placements_for };
}

//============================================
// DOM read-back
//============================================

// Read the unique placement_name off a clicked element (or the closest ancestor
// carrying the DOM key). The click resolver uses this so the DOM click key has
// exactly one reader. Returns null when the element carries no key.
export function placement_name_from_element(element: Element): string | null {
  return element.getAttribute(TARGET_DOM_ATTR);
}

// The delegated-listener selector for a clickable scene element. Centralized
// here beside TARGET_DOM_ATTR so click_resolver's closest() lookup and the
// attribute source stay in one place.
export const TARGET_DOM_SELECTOR = `[${TARGET_DOM_ATTR}]`;

// Identity resolver seam. Used as the default when no scene adapter is supplied
// (pure protocol unit tests, or the config-only default snapshot reducer): with
// no scene placements, a target IS its own placement and object, so resolution
// is the identity function. This is the correct degenerate behavior, not a
// bug-hiding fallback -- production always supplies a real scene-built adapter.
export const IDENTITY_TARGET_ADAPTER: TargetAdapter = {
  resolve_to_placement: (target: string): string => target,
  resolve_to_object: (target: string): string => target,
  // With no scene placements to check against, every target is trivially
  // known: this mirrors resolve_to_placement/resolve_to_object's identity
  // behavior so pure protocol unit tests (no scene adapter supplied) see the
  // target-existence check pass rather than firing on every fixture target.
  has_target: (): boolean => true,
  // Identity: a target is its own single placement, so it is never ambiguous.
  // Pure protocol unit tests (no scene adapter) see the ambiguity invariant
  // pass rather than firing on every fixture target.
  placements_for: (target: string): readonly string[] => [target],
};
