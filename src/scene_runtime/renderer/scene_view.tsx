// src/scene_runtime/renderer/scene_view.tsx
//
// The Solid scene view: renders a whole scene from a PipelineResult plus a
// reactive scene store. It owns:
//   - background (via renderBackground, imperative, ref-driven)
//   - structural-guard classification (report mode, never throws)
//   - the scene-degraded marker, computed REACTIVELY from two sources:
//       1. structural violations (known at render time), and
//       2. a SceneView-owned reactive Set of resolver-degraded targets, fed by
//          each SceneItem through an onDegrade callback.
//   - one SceneItem per computed item, keyed by stable placement identity
//   - one label per computed item at its computed labelX/labelY
//
// Ordering-independent degrade marker (replaces the old onMount + child
// closest() race): SceneView holds the degraded-target Set as a signal and a
// createEffect on its own root sets/clears data-scene-degraded from that signal
// plus the structural violations. A SceneItem that fails to resolve calls
// onDegrade(target, message); a SceneItem that resolves cleanly calls
// onDegrade(target, "") to clear its membership. Because the marker is derived
// reactively from owned state -- not from a child reaching up via
// closest("[data-scene-root]") at an effect-timing-dependent moment -- it is
// correct on FIRST render and on every later render, with no onMount race.
//
// Frozen DOM contract (additive degrade markers): SceneView stamps
// data-scene-root="true" on its root (stable identity marker), and reactively
// toggles data-scene-degraded="true" (failure-only) plus, for the structural
// case, data-degraded-violation-count. Per-item data-resolver-degraded is
// stamped by SceneItem (see scene_item.tsx). All three are additive and
// failure-only except data-scene-root which is unconditional.
//
// Geometry boundary: every coordinate comes from the PipelineResult VERBATIM.
// This module performs no positioning math. runPipeline is the layout
// authority; Solid only renders.
//
// Reconciliation: the item list is rendered with Solid <For>, which reconciles
// by reference identity of the PipelineResult items. result.final is an
// immutable snapshot per render, so references are stable between
// ObjectStateChange events and no item DOM node is remounted on a state update.
// Only a SceneChange (which disposes the root and mounts a fresh SceneView)
// remounts the scene.

import type { JSXElement } from "solid-js";
import { For, Show, onMount, createMemo, createSignal, createEffect } from "solid-js";
import { Portal } from "solid-js/web";

import type { ComputedItem, PipelineResult } from "../layout/types.js";
import type { SceneStore, TargetSeed } from "../state/scene_store.js";
import type { ActiveAffordanceAccessor } from "../protocol/affordance.js";
import type { MaterialRegistry } from "./visual_state_resolver.js";
import { OBJECT_LIBRARY } from "../../../generated/object_library.js";
import { collectStructuralViolations, enforceNoLabelOwnSvgOverlap } from "./structural_guards.js";
import { LABEL_FONT_MIN_PX, LABEL_FONT_WIDTH_FRACTION } from "../layout/constants.js";
import { renderBackground } from "./render_background.js";
import { SceneItem } from "./scene_item.js";
import { SceneAnnotationRail, type SceneAnnotation } from "./scene_annotations.js";

//============================================
// Seed-list derivation from a PipelineResult
//============================================

// Build the store seed list from a pipeline result. Each unique rendered object
// whose real definition declares object-level state gets one bare-object seed.
// Structured objects with declared subpart state also seed every declared
// subpart in definition order. The generated `subparts` vocabulary is the
// authoritative enumerable set; it is deliberately not inferred from rendered
// geometry because some structured objects have no subpart overlay geometry.
// Render-error placements and state-free targets are skipped.
export function build_seed_list(result: PipelineResult): TargetSeed[] {
  const seeds: TargetSeed[] = [];
  const seenObjects = new Set<string>();
  const seenTargets = new Set<string>();
  for (const item of result.final) {
    const object_name = item.object_name;
    // The store is keyed by object_name, so repeated placements share seeds.
    if (seenObjects.has(object_name)) {
      continue;
    }
    seenObjects.add(object_name);
    const def = OBJECT_LIBRARY[object_name];
    if (def === undefined) {
      // Render-error placement: no object schema to seed.
      continue;
    }
    if (Object.keys(def.state_schema).length > 0 && !seenTargets.has(object_name)) {
      seenTargets.add(object_name);
      seeds.push({ target: object_name, object_name });
    }
    if (Object.keys(def.subpart_state_schema).length === 0) {
      continue;
    }
    for (const subpart of def.subparts ?? []) {
      const target = `${object_name}.${subpart}`;
      if (seenTargets.has(target)) {
        continue;
      }
      seenTargets.add(target);
      seeds.push({ target, object_name });
    }
  }
  return seeds;
}

//============================================
// Label font size resolution (parity with render_scene.ts)
//============================================

// Resolve the label font size for the scene. Mirrors render_scene.ts: an
// authored layout_rules.label_font_size wins; otherwise derive a canvas-
// relative size from the mounted root width, floored at LABEL_FONT_MIN_PX.
function resolve_label_font_size(root: HTMLElement, result: PipelineResult): number {
  const w = root.getBoundingClientRect().width;
  const relative_px = Math.max(LABEL_FONT_MIN_PX, Math.round(w * LABEL_FONT_WIDTH_FRACTION));
  return result.scene.layout_rules?.label_font_size ?? relative_px;
}

//============================================
// Label component (parity with render_label.ts)
//============================================

// Render one label at its computed labelX/labelY. Emits data-label and
// data-label-for exactly as render_label.ts does. No geometry math: positions
// come from the ComputedItem verbatim.
function SceneLabel(props: { item: ComputedItem; fontSize: number }): JSXElement {
  const item = props.item;
  const text = item._labelLines.join("\n");
  return (
    <div
      data-label=""
      data-label-for={item.placement_name}
      style={{
        position: "absolute",
        left: `${item._labelX}%`,
        top: `${item._labelY}%`,
        transform: "translateX(-50%)",
        "font-family": '"PT Sans Narrow", "Arial Narrow", sans-serif',
        "font-size": `${props.fontSize}px`,
        // "pre" honors pipeline-chosen line breaks; no auto-wrap.
        "white-space": "pre",
        "text-align": "center",
        color: "#333333",
        "pointer-events": "none",
      }}
    >
      {text}
    </div>
  );
}

//============================================
// Public component: the whole scene
//============================================

// Render a full scene reactively.
//
// props.root       the scene-root element (used for background + degraded
//                  marker + font sizing); the SceneView is mounted INTO it.
// props.result     PipelineResult (geometry authority)
// props.store      reactive scene store
// props.materialRegistry active protocol's material registry (may be empty)
// props.viewport   optional pixel viewport for the aspect guard
export function SceneView(props: {
  root: HTMLElement;
  result: PipelineResult;
  store: SceneStore;
  materialRegistry: MaterialRegistry | null;
  viewport?: { w: number; h: number } | undefined;
  // Active-affordance accessor (affordance plumbing). Threaded by reference into each
  // SceneItem; absent when no protocol interaction context exists (scene
  // viewer / facade render), in which case SceneItem computes no highlight.
  activeAffordance?: ActiveAffordanceAccessor | undefined;
  // Resolver-accepted candidate object names for this scene, computed once per
  // scene mount in mountScene. Passed by reference; SceneItem only calls .has().
  candidateTargets?: ReadonlySet<string> | undefined;
  annotationRoot?: HTMLElement | undefined;
}): JSXElement {
  const result = props.result;
  if (!result.interactionGeometry.valid) {
    throw new Error(
      `scene_view: invalid interaction geometry (${result.interactionGeometry.issues
        .map((issue) => issue.kind)
        .join(", ")})`,
    );
  }
  const root = props.root;

  // The active interaction supplies a placement-normalized target. Select is
  // deliberately excluded from the single-target path: moving to one target
  // could disclose an answer before the learner chooses. Select instead
  // reveals the union of every equally ringed candidate below. The memo
  // preserves equality across unrelated snapshot updates, so feedback/recovery
  // changes do not restart scene motion.
  const visible_action_target = createMemo<string | null>(() => {
    const affordance = props.activeAffordance?.();
    if (affordance?.active_gesture === "select") {
      return null;
    }
    return affordance?.active_target ?? null;
  });

  // Bring every exact active interaction surface into the nearest scene-owned
  // scrollport. Whole-object envelopes and exact/group subpart hits all expose
  // the same data-item-id contract, so measuring their union guarantees the
  // usable 44px interaction surface is visible rather than merely its artwork.
  // This writes only the scrollport's scroll position; it never calls
  // Element.scrollIntoView(), which could also move the document viewport.
  function reveal_targets(targets: readonly string[]): void {
    if (targets.length === 0) {
      return;
    }
    const scrollport = root.closest(".scene-panel");
    if (!(scrollport instanceof HTMLElement)) {
      return;
    }
    const target_set = new Set(targets);
    const target_elements = Array.from(root.querySelectorAll("[data-item-id]")).filter((element) =>
      target_set.has(element.getAttribute("data-item-id") ?? ""),
    );
    if (target_elements.length === 0) {
      return;
    }
    const target_rects = target_elements
      .map((element) => element.getBoundingClientRect())
      .filter((rect) => rect.width > 0 && rect.height > 0);
    if (target_rects.length === 0) {
      return;
    }
    const target_left = Math.min(...target_rects.map((rect) => rect.left));
    const target_right = Math.max(...target_rects.map((rect) => rect.right));
    const target_top = Math.min(...target_rects.map((rect) => rect.top));
    const target_bottom = Math.max(...target_rects.map((rect) => rect.bottom));
    const port_rect = scrollport.getBoundingClientRect();
    const inset = 12;
    function reveal_axis(
      target_start: number,
      target_end: number,
      port_start: number,
      port_end: number,
    ): number {
      const usable_start = port_start + inset;
      const usable_end = port_end - inset;
      if (target_end - target_start > usable_end - usable_start) {
        // A group can be taller/wider than the panel. There is no scroll
        // position that fully contains it, so put its midpoint at the
        // viewport midpoint deterministically rather than favoring an edge.
        return (target_start + target_end - port_start - port_end) / 2;
      }
      if (target_start < usable_start) {
        return target_start - usable_start;
      }
      if (target_end > usable_end) {
        return target_end - usable_end;
      }
      return 0;
    }
    const left = reveal_axis(target_left, target_right, port_rect.left, port_rect.right);
    const top = reveal_axis(target_top, target_bottom, port_rect.top, port_rect.bottom);
    if (left === 0 && top === 0) {
      return;
    }
    if (typeof scrollport.scrollBy === "function") {
      // This reflects a protocol state transition, not decorative movement.
      // `auto` makes the target available before the next learner action or
      // assistive-technology query, and is also motion-safe by construction.
      scrollport.scrollBy({ left, top, behavior: "auto" });
      return;
    }
    // Older embedded browsers can still reveal the target without touching
    // window scroll. Direct assignments are intentionally immediate.
    scrollport.scrollLeft += left;
    scrollport.scrollTop += top;
  }

  createEffect(() => {
    const active_affordance = props.activeAffordance?.();
    if (active_affordance?.active_gesture === "select") {
      // The candidate set is generated from the same resolved affordance
      // semantics that paint candidate rings. Revealing their combined bounds
      // keeps all choices reachable without signaling which one is correct.
      reveal_targets(Array.from(props.candidateTargets ?? []));
      return;
    }
    const target = visible_action_target();
    if (target === null) {
      return;
    }
    // createEffect runs after Solid commits this render pass, so exact/group
    // hit surfaces are already present. Keep alignment in this same reactive
    // turn: a later microtask leaves a visible but not-yet-reachable target
    // between the runtime action update and the scrollport update.
    reveal_targets([target]);
  });

  // Structural classification in report mode (never throws). Most violations
  // degrade, never blank, the scene -- same policy as render_scene.ts. This
  // list is fixed at render time (geometry is immutable per PipelineResult).
  const violations = collectStructuralViolations(result.final, result.scene, props.viewport);

  // Guard 8 (own-art label overlap) is the single exception to degrade-not-blank:
  // a label over its own object's SVG is a manufacturing defect that must hard-fail
  // at the gate, not pass green as a silent report. There is no instance where any
  // overlap should be excluded.
  enforceNoLabelOwnSvgOverlap(violations);

  // SceneView-owned reactive set of targets whose visual-state resolution has
  // failed. SceneItem feeds this through the onDegrade callback below. The set
  // is the single source of truth for resolver-driven degrade, replacing the
  // old child closest("[data-scene-root]") DOM walk.
  const [degradedTargets, setDegradedTargets] = createSignal<Set<string>>(new Set());
  const [annotationsByPlacement, setAnnotationsByPlacement] = createSignal<
    ReadonlyMap<string, readonly SceneAnnotation[]>
  >(new Map());

  function onAnnotations(placement_name: string, annotations: readonly SceneAnnotation[]): void {
    setAnnotationsByPlacement((previous) => {
      const next = new Map(previous);
      if (annotations.length === 0) {
        next.delete(placement_name);
      } else {
        next.set(placement_name, annotations);
      }
      return next;
    });
  }

  const scene_annotations = createMemo<readonly SceneAnnotation[]>(() => {
    const annotations = annotationsByPlacement();
    return result.final.flatMap((item) => annotations.get(item.placement_name) ?? []);
  });

  // A stateful production scene must provide the shell-owned rail mount. This
  // keeps every resolved learner-visible fact present exactly once instead of
  // silently losing it when a host omits the sibling root. State-free renderer
  // harnesses may intentionally omit the root.
  createEffect(() => {
    if (props.annotationRoot === undefined && scene_annotations().length > 0) {
      throw new Error(
        "SceneView: annotationRoot is required when resolved scene annotations are present",
      );
    }
  });

  // Record or clear a target's degraded membership. Called by SceneItem when
  // its resolver throws (message non-empty) or recovers (message empty). We
  // copy-on-write the Set so Solid sees a new reference and re-runs the marker
  // effect.
  function onDegrade(target: string, message: string): void {
    const current = degradedTargets();
    const isDegraded = current.has(target);
    if (message.length > 0) {
      if (isDegraded) {
        return;
      }
      const next = new Set(current);
      next.add(target);
      setDegradedTargets(next);
      return;
    }
    if (!isDegraded) {
      return;
    }
    const next = new Set(current);
    next.delete(target);
    setDegradedTargets(next);
  }

  // Stamp the stable scene-root identity marker once on mount. This is the
  // frozen-contract identity attribute (used by tests/tools to find the root);
  // the degraded marker is now a reactive effect, not an onMount branch.
  onMount(() => {
    root.setAttribute("data-scene-root", "true");
    if (result.scene.background) {
      renderBackground(root, result.scene.background);
    }
    // Warn once for structural violations (the reactive effect owns the DOM
    // marker; this warn keeps the loud diagnostic the old onMount emitted).
    if (violations.length > 0) {
      const summary = violations.map((v) => `[${v.guard}] ${v.message}`).join("\n");
      // eslint-disable-next-line no-console
      console.warn(
        `Scene "${result.scene.scene_name}" rendered DEGRADED with ${violations.length} structural violation(s):\n${summary}`,
      );
    }
  });

  // Reactive scene-degraded marker. Runs on first render (Solid flushes the
  // effect after the root node exists) and on every change to the degraded set.
  // Degraded when there is a structural violation OR any resolver-degraded
  // target. This is ordering-independent: it derives from owned state, not from
  // a child reaching up to the root at an effect-timing-dependent moment.
  createEffect(() => {
    const resolverDegradedCount = degradedTargets().size;
    const isDegraded = violations.length > 0 || resolverDegradedCount > 0;
    if (isDegraded) {
      root.setAttribute("data-scene-degraded", "true");
    } else {
      root.removeAttribute("data-scene-degraded");
    }
    // The violation count reflects structural violations only (a fixed render-
    // time fact); resolver degrades are observable per-item via
    // data-resolver-degraded. Keep this attribute for the structural case so
    // existing diagnostics still read it.
    if (violations.length > 0) {
      root.setAttribute("data-degraded-violation-count", String(violations.length));
    } else {
      root.removeAttribute("data-degraded-violation-count");
    }
  });

  const label_font_size = resolve_label_font_size(root, result);

  // Items and labels render as direct children of the SceneView fragment, in
  // depth_tier order (result.final is already sorted). Reference-identity
  // reconciliation means an ObjectStateChange never remounts an item's DOM node.
  return (
    <>
      <For each={result.final}>
        {(item: ComputedItem) => (
          <>
            <SceneItem
              item={item}
              store={props.store}
              materialRegistry={props.materialRegistry}
              sceneName={result.scene.scene_name}
              onDegrade={onDegrade}
              onAnnotations={onAnnotations}
              activeAffordance={props.activeAffordance}
              candidateTargets={props.candidateTargets}
              interactionGeometry={result.interactionGeometry.envelopes[item.placement_name]}
            />
            <SceneLabel item={item} fontSize={label_font_size} />
          </>
        )}
      </For>
      <Show when={props.annotationRoot !== undefined}>
        <Portal mount={props.annotationRoot!}>
          <SceneAnnotationRail
            annotations={scene_annotations()}
            active_target={visible_action_target()}
            active_gesture={props.activeAffordance?.().active_gesture ?? null}
            candidate_targets={props.candidateTargets ?? new Set<string>()}
          />
        </Portal>
      </Show>
    </>
  );
}
