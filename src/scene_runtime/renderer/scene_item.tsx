// src/scene_runtime/renderer/scene_item.tsx
//
// One positioned scene item, rendered by Solid. Each item is a reactive
// Solid component derived from a ComputedItem and the scene store.
//
// Geometry boundary (PRIMARY_DESIGN.md / plan "Solid owns rendering, not
// layout meaning"): every geometric value (_centerX, _top, _visualWidth, _height,
// depth, zone) comes VERBATIM from the ComputedItem produced by runPipeline.
// This component performs NO layout decisions. It derives CSS edges from the
// anchor-coordinate convention (center to edge) but does not compute anchor
// positions -- those come verbatim from the layout engine. The structured-subpart
// exception (well/lane/slot geometry) is not handled here; it would draw from
// declared object structure, never ad hoc component math.
//
// Reactive state boundary: artwork (asset / overlays / highlight) is derived
// from the scene_store via visual_state_resolver. When the store changes the
// item's state, only this item's reactive fragments update; the DOM node for
// the item is created once and reused (Solid keyed <For> in scene_view keeps
// the node stable across ObjectStateChange).
//
// Frozen DOM contract (plan "Frozen DOM contract"): the item div emits exactly
// these data-* attributes:
//   data-placement-name, data-object-name, data-zone, data-kind, data-depth,
//   data-item-id, data-asset, and (placeholder only)
//   data-missing-svg + data-placeholder-kind.
// Additive failure-only marker: data-resolver-degraded="<message>" is stamped on
// the item div when this item's visual-state resolution throws (see the resolver
// memo below). It is absent on a clean item. The scene-root marker
// (data-scene-degraded on the closest [data-scene-root]) is NOT stamped here; it
// is owned reactively by SceneView, which this item notifies via the onDegrade
// callback. SceneView stamps data-scene-root + data-scene-degraded (see
// scene_view.tsx).
// Actionability gate (M6 "Enforce capabilities in renderer and candidate
// enumeration"): data-item-id is stamped ONLY when the item's declared
// ObjectDef.capabilities includes "clickable" (item.capabilities, bound
// verbatim onto the ComputedItem by the layout pipeline). A decoration_only
// object or a missing-object placeholder (bound with capabilities: []) omits
// data-item-id entirely, so it receives no [data-item-id] CSS affordance
// (cursor, hover outline, active/candidate ring) and is invisible to the
// delegated click_resolver and to enumerate_candidate_targets. This makes
// interactivity a modeled property instead of an emergent side effect of
// "every rendered item gets an id".
// Click handling stays on the delegated click_resolver (it reads data-item-id);
// this component adds NO per-item click handler.

import type { JSXElement } from "solid-js";
import {
  createMemo,
  createSignal,
  createEffect,
  createResource,
  Show,
  For,
  onCleanup,
} from "solid-js";

import type { ComputedItem, ObjectVisualStates, SubpartGeometry } from "../layout/types.js";
import type { SceneStore } from "../state/scene_store.js";
import { type ActiveAffordanceAccessor, compute_affordance_kind } from "../protocol/affordance.js";
import {
  resolve_visual_state,
  type MaterialRegistry,
  type ObjectState,
  type ResolvedVisualState,
} from "./visual_state_resolver.js";
import { injectSvgFromManifest } from "./inject_svg.js";
import { render_liquid_material_effects } from "./liquid_paint.js";
import { resolveSvgUrl, requiresDomSvg } from "./svg_manifest_loader.js";
import { SubpartVisualStateOverlay } from "./subpart_visual_state_renderer.js";
import { SubpartHitSurface, resolve_active_subpart_selection } from "./subpart_hit_surface.js";
import { find_subpart_material_contract } from "./subpart_dispatch.js";
import { OBJECT_LIBRARY } from "../../../generated/object_library.js";

//============================================
// Depth -> z-index mapping
//============================================

const DEPTH_Z: Record<string, number> = {
  back: 1,
  mid: 2,
  front: 3,
};

// Shared empty candidate-target set used when no candidateTargets prop is
// provided. Never rebuilt per item: per-item memos call .has() (O(1)) on this
// constant reference. A single constant avoids allocating a new Set on every
// render of an item that has no active affordance plumbing wired in.
const EMPTY_CANDIDATE_TARGETS: ReadonlySet<string> = new Set<string>();

// Resolve the z-index for an item's depth tier. Items lacking a depth tier
// render in the back tier (z-index 1).
function z_index_for(item: ComputedItem): number {
  if (!item.depth) {
    return 1;
  }
  return DEPTH_Z[item.depth] ?? 1;
}

//============================================
// Static-geometry style (computed once from PipelineResult, never reactive)
//============================================

// Build the absolute-position style string for an item from its computed
// geometry. Uses scene-percent left/top/width/height and a depth-derived z-index.
//
// Geometry boundary (anchor-coordinate convention):
//   _centerX = shared horizontal center of footprint and visual box (scene-%).
//   CSS left edge = _centerX - _visualWidth / 2 (derived at this boundary).
//   _top = derived visual top edge (already absolute, used verbatim).
function position_style(item: ComputedItem): Record<string, string> {
  return {
    position: "absolute",
    // Derive CSS left from the anchor center: left edge = center - half-width.
    left: `${item._centerX - item._visualWidth / 2}%`,
    top: `${item._top}%`,
    width: `${item._visualWidth}%`,
    height: `${item._height}%`,
    "z-index": String(z_index_for(item)),
  };
}

// Geometry metrics in the declaration's own viewBox. They are used only to
// focus the original structured object around a directed exact subpart; no
// second copy or alternate layout is created for the learner.
function subpart_geometry_metrics(geometry: SubpartGeometry): {
  center_x: number;
  center_y: number;
  width: number;
  height: number;
} {
  if (geometry.shape === "circle") {
    return {
      center_x: geometry.cx,
      center_y: geometry.cy,
      width: geometry.r * 2,
      height: geometry.r * 2,
    };
  }
  return {
    center_x: geometry.x + geometry.w / 2,
    center_y: geometry.y + geometry.h / 2,
    width: geometry.w,
    height: geometry.h,
  };
}

//============================================
// Object-level visual_states filtering
//============================================

// Keep only the object-level visual_states entries. Subpart entries
// (applies_to: 'subpart') describe per-subpart rendering (well/tube/lane
// material) driven by subpart state, not the object's own state, and are
// handled by the structured-subpart path (not this object-level renderer).
function filter_object_visual_states(all: ObjectVisualStates): ObjectVisualStates {
  const out: ObjectVisualStates = {};
  for (const key of Object.keys(all)) {
    const def = all[key];
    if (def !== undefined && def.applies_to === "object") {
      out[key] = def;
    }
  }
  return out;
}

//============================================
// Reactive state read
//============================================

// Read the current declared object state for a target from the store. Returns
// an empty object when the target was not seeded (e.g. a non-clickable decor
// item with no state schema); the resolver then produces no overlays and uses
// the object's default svg case via the item asset.
function read_object_state(store: SceneStore, target: string): ObjectState {
  const entry = store.state[target];
  if (entry === undefined) {
    return {};
  }
  // The reactive read of entry.state subscribes this memo to state changes.
  const out: ObjectState = {};
  for (const key of Object.keys(entry.state)) {
    const value = entry.state[key];
    if (value !== undefined) {
      out[key] = value;
    }
  }
  return out;
}

// Read the runtime highlight flags for a target. Missing target -> off.
function read_flags(
  store: SceneStore,
  target: string,
): {
  is_selected: boolean;
  timed_wait_active: boolean;
  timed_wait_display: string | null;
} {
  const entry = store.state[target];
  if (entry === undefined) {
    return { is_selected: false, timed_wait_active: false, timed_wait_display: null };
  }
  return {
    is_selected: entry.flags.is_selected,
    timed_wait_active: entry.flags.timed_wait_active,
    timed_wait_display: entry.flags.timed_wait_display,
  };
}

//============================================
// SVG host (tiered: <img> for static assets, fetched SVG DOM for DOM-required)
//============================================

// A fixed-size box that fills the item geometry. Both render tiers use it so the
// host keeps a stable layout box before SVG file text arrives (no layout shift
// while the async fetch is in flight).
const SVG_HOST_BOX_STYLE: Record<string, string> = { width: "100%", height: "100%" };

// Render a DOM-SVG-required asset: fetch its file text once (cached per URL),
// namespace ids per render instance, and inject the resulting SVG DOM. The whole
// fetch+namespace+inject runs inside a Solid resource so a failure is captured by
// the resource (no unhandled promise rejection). The ref records the host element
// and signals readiness; the resource (keyed on asset + key + host readiness)
// performs the injection only once a host exists. A fetch/parse failure flows to
// the resource's error state, which renders a visible error marker and stamps
// data-svg-load-error on the host. Success inserts ONLY already-resolved markup.
function DomSvgHost(props: {
  asset: string;
  svgInstanceKey: string;
  onDomSvgHostReady?: (host: HTMLElement) => void;
}): JSXElement {
  let hostEl: HTMLDivElement | undefined;
  // Readiness flips true once the ref has set hostEl, so the resource does not
  // run before a host exists to inject into.
  const [hostReady, setHostReady] = createSignal<boolean>(false);

  // The resource source bundles asset, key, and the host-ready flag. A changed
  // asset (e.g. an SvgSwap-style enum visual_state) re-runs the injection. The
  // resolver does the fetch+namespace+inject; its rejection becomes the
  // resource's error state, surfaced visibly below.
  const [injected] = createResource(
    () => ({ asset: props.asset, key: props.svgInstanceKey, ready: hostReady() }),
    async (k: { asset: string; key: string; ready: boolean }): Promise<boolean> => {
      if (!k.ready || hostEl === undefined) {
        // No host yet; resolve falsy and let the source re-trigger on readiness.
        return false;
      }
      // Fetch (cached by URL) + namespace per instance + insert. A failure
      // rejects, which Solid records as injected.error (handled below).
      await injectSvgFromManifest(hostEl, k.asset, k.key);
      props.onDomSvgHostReady?.(hostEl);
      return true;
    },
  );

  // Loud, visible failure: a resource error becomes an explicit rendered error
  // state plus a data-svg-load-error stamp -- never an unhandled rejection or a
  // silent blank. Reading injected.error subscribes this memo to the resource.
  const loadError = createMemo<string>(() => {
    const err: unknown = injected.error;
    if (err === undefined) {
      return "";
    }
    if (err instanceof Error) {
      return err.message;
    }
    if (typeof err === "string") {
      return err;
    }
    // Non-Error, non-string resource error: serialize safely rather than
    // relying on Object's default "[object Object]" stringification.
    return JSON.stringify(err);
  });

  let lastLoggedError = "";
  createEffect(() => {
    const message = loadError();
    if (message.length > 0 && message !== lastLoggedError) {
      // eslint-disable-next-line no-console
      console.error(`SVG load failed for asset "${props.asset}": ${message}`);
    }
    lastLoggedError = message;
  });

  return (
    <div
      style={SVG_HOST_BOX_STYLE}
      data-svg-render-mode="dom-svg"
      data-svg-load-error={loadError().length > 0 ? loadError() : undefined}
      ref={(el: HTMLDivElement) => {
        hostEl = el;
        setHostReady(true);
      }}
    >
      <Show when={loadError().length > 0}>
        <span
          style={{
            "font-size": "14px",
            "font-family": "monospace",
            color: "#c0392b",
            "pointer-events": "none",
          }}
        >
          {`SVG load failed: ${props.asset}`}
        </span>
      </Show>
    </div>
  );
}

// Render a static (non-DOM-SVG-required) asset as an <img>. The container item
// div already carries the data-* attributes and the delegated click affordance,
// so the image must not intercept pointer events; pointer-events:none keeps the
// container clickable/highlightable. object-fit:contain preserves aspect (never
// crop/stretch a scientific asset, per PRIMARY_DESIGN.md). The fixed box style
// keeps layout stable.
function ImgSvgHost(props: { asset: string }): JSXElement {
  const url = createMemo<string>(() => resolveSvgUrl(props.asset));
  return (
    <img
      src={url()}
      alt=""
      data-svg-render-mode="img"
      style={{
        ...SVG_HOST_BOX_STYLE,
        "object-fit": "contain",
        "pointer-events": "none",
        display: "block",
      }}
    />
  );
}

// Tiered SVG host. The render mode is chosen from the asset's DECLARED
// requires_dom_svg value in the manifest (derived at generation time from object
// declarations), never from current material/visual state -- so it is stable
// across the object's lifetime. DOM-SVG-required assets fetch + namespace +
// inject SVG DOM; static assets render as an opaque <img>. svgInstanceKey is a
// stable unique render-instance key (scene_name + placement_name) used to
// namespace internal SVG ids so two injected instances never collide on a shared
// id (e.g. clipPath id="a").
function SvgHost(props: {
  asset: string;
  svgInstanceKey: string;
  onDomSvgHostReady?: (host: HTMLElement) => void;
}): JSXElement {
  // requiresDomSvg reads the manifest's generation-time-derived boolean. It is a
  // declaration property, not runtime state, so reading it once per asset (memo)
  // is correct and stable.
  const isDomSvg = createMemo<boolean>(() => requiresDomSvg(props.asset));
  const dom_svg_props: {
    asset: string;
    svgInstanceKey: string;
    onDomSvgHostReady?: (host: HTMLElement) => void;
  } = {
    asset: props.asset,
    svgInstanceKey: props.svgInstanceKey,
  };
  if (props.onDomSvgHostReady !== undefined) {
    dom_svg_props.onDomSvgHostReady = props.onDomSvgHostReady;
  }
  return (
    <Show when={isDomSvg()} fallback={<ImgSvgHost asset={props.asset} />}>
      <DomSvgHost {...dom_svg_props} />
    </Show>
  );
}

//============================================
// Text-overlay rendering, bottom-anchored
//============================================

// Render resolved text overlays as centered captions. Multiple overlays stack
// above the bottom of the item box and do not change item geometry.
function Overlays(props: { resolved: ResolvedVisualState }): JSXElement {
  return (
    <For each={props.resolved.overlays}>
      {(overlay, index) => {
        // Multiple declared text overlays represent distinct state facts (for
        // example, an instrument's completed analysis plus its numeric
        // results). Stack them rather than placing each in the same pixels.
        // Use a pixel rhythm rather than a percentage of the object height.
        // Percentage spacing collapsed all state facts onto the same few
        // pixels on physically small objects (slides, tubes, and cassettes).
        // A compact opaque-backed caption keeps each authored observation
        // legible without changing the object's measured scene geometry.
        const bottom = 2 + index() * 16;
        return (
          <div
            data-overlay="text"
            data-overlay-field={overlay.field_name}
            style={{
              position: "absolute",
              left: "50%",
              bottom: `${bottom}px`,
              transform: "translateX(-50%)",
              "text-align": "center",
              "font-family": "monospace",
              "font-size": "10px",
              "line-height": "1.25",
              "white-space": "nowrap",
              color: "#222222",
              background: "rgba(255, 255, 255, 0.88)",
              border: "1px solid rgba(23, 59, 73, 0.22)",
              "border-radius": "3px",
              padding: "1px 4px",
              "z-index": "3",
              "pointer-events": "none",
            }}
          >
            {overlay.text}
          </div>
        );
      }}
    </For>
  );
}

// Render object-level declarative material effects into the already-injected
// compiled SVG. Ordinary assets may have no effects, but an authored effect on
// an ordinary asset is a contract violation and degrades visibly.
function AnchorMaterialEffects(props: {
  host: HTMLElement | undefined;
  resolved: ResolvedVisualState | null;
  onDegrade: (message: string) => void;
}): JSXElement {
  createEffect(() => {
    const host = props.host;
    const resolved = props.resolved;
    if (host === undefined) {
      return;
    }
    try {
      const effects = resolved?.anchor_material_effects ?? [];
      const handled = render_liquid_material_effects(host, effects);
      if (effects.length > 0 && !handled) {
        throw new Error("material fill effect requires a compiled material SVG");
      }
      props.onDegrade("");
    } catch (err) {
      props.onDegrade(err instanceof Error ? err.message : String(err));
    }
  });
  return <></>;
}

//============================================
// Placeholder body (missing-svg / missing-object)
//============================================

// Render the labeled dashed-box body used for placeholder-mode items.
// Emits a dashed border, centered label, two-line object_name + cause text.
// NEVER an object-fit SVG container.
function PlaceholderBody(props: { item: ComputedItem }): JSXElement {
  const cause = (): string =>
    props.item._missing_object === true ? "MISSING OBJECT" : "MISSING ART";
  return (
    <span
      style={{
        "font-size": "11px",
        "font-family": "monospace",
        color: "#c0392b",
        "text-align": "center",
        padding: "2px 4px",
        "pointer-events": "none",
        // whiteSpace pre renders the \n in the label text as a line break.
        "white-space": "pre",
      }}
    >
      {`${props.item.object_name}\n${cause()}`}
    </span>
  );
}

//============================================
// Public component: one positioned item
//============================================

// Render one positioned scene item. The geometry comes from the ComputedItem
// verbatim; the artwork/overlays/highlight are reactive from the store.
//
// props.item            ComputedItem from runPipeline (geometry authority)
// props.store           reactive scene store
// props.materialRegistry active protocol's material registry (may be empty)
export function SceneItem(props: {
  item: ComputedItem;
  store: SceneStore;
  materialRegistry: MaterialRegistry | null;
  // Scene/page id, threaded from SceneView. Composed with placement_name into a
  // stable UNIQUE svgInstanceKey for SVG id namespacing. placement_name alone
  // can repeat across nested scenes, overlays, or side-by-side views, so the
  // scene id is required to keep the key unique per render instance.
  sceneName: string;
  // SceneView-owned degrade sink. Called with a non-empty message when this
  // item's resolver throws, and with "" when it resolves cleanly, so SceneView
  // can reactively own the scene-root data-scene-degraded marker without a
  // child closest()/onMount race. Optional so unit harnesses can mount a bare
  // SceneItem without wiring the callback.
  onDegrade?: (target: string, message: string) => void;
  // Active-affordance accessor (affordance plumbing). Read in
  // ARROW form INSIDE the per-object highlight memo (never as a plain object
  // snapshot) so the snapshot dependency is tracked reactively. Optional: absent
  // for the scene viewer / facade render, where no highlight ring is computed.
  activeAffordance?: ActiveAffordanceAccessor | undefined;
  // Resolver-accepted candidate object names for this scene, computed once per
  // scene mount and passed by reference. The affordance memo calls .has(item_target)
  // (O(1)) and must NOT rebuild the set. Optional alongside activeAffordance.
  candidateTargets?: ReadonlySet<string> | undefined;
}): JSXElement {
  const item = props.item;
  // object_name is the STATE-store / object-library lookup key (the store is
  // object_name-keyed; two placements of one object share one state). Used for
  // OBJECT_LIBRARY, read_object_state, read_flags, and the degrade channel.
  const target = item.object_name;
  // placement_name is the unique per-placement DOM / click / highlight key
  // (target-identity decision M7). It is what the click resolver reads back as
  // data-item-id, what the walker clicks, and what the affordance memo compares
  // against the resolved active_interaction_target. object_name would collapse
  // two placements of one object into one DOM key; placement_name keeps them
  // distinct.
  const placement_target = item.placement_name;

  // Placeholder-mode items skip SVG/state resolution entirely.
  const is_placeholder = item.missing_svg === true;

  // Actionability gate: an item is a click target only when its declared
  // ObjectDef.capabilities (bound verbatim onto the ComputedItem by the
  // layout pipeline) includes "clickable". decoration_only objects and
  // missing-object placeholders (bound with capabilities: []) are excluded,
  // so they render with no data-item-id and are invisible to the delegated
  // click_resolver and to enumerate_candidate_targets.
  const is_clickable = item.capabilities.includes("clickable");

  // Resolve the object's authored visual_states map (empty when the object is
  // not in the library, e.g. a missing-object placeholder), filtered to the
  // OBJECT-level entries. Subpart visual_states (applies_to: 'subpart', e.g. the
  // per-tube material on a rack, or per-well material on a plate) are NOT resolved
  // by this object-level renderer (resolving them against object-level state would
  // reference fields the object schema does not declare). They are rendered by the
  // structured-subpart path: the generic SubpartVisualStateOverlay, DISPATCHED
  // below purely on the declared contract.
  const object_def = OBJECT_LIBRARY[target];
  const all_visual_states: ObjectVisualStates = object_def?.visual_states ?? {};
  const visual_states: ObjectVisualStates = filter_object_visual_states(all_visual_states);

  // Dispatch for the declarative subpart material overlay. This is a pure
  // DISPATCH on the declared contract, NOT on object identity: it is non-null
  // exactly when this object's def carries subpart_geometry plus a subpart
  // material_tint visual_state. find_material_tint_subpart_field reads the driving
  // field NAME out of the declaration; scene_item.tsx names no object, field, or
  // shape. When non-null, the overlay renders below; when null (every object
  // without the subpart material-tint contract), nothing extra renders.
  const subpart_contract =
    object_def !== undefined ? find_subpart_material_contract(object_def) : null;

  // Validate a directed dotted target before the renderer decides which
  // optional layers to mount. This is deliberately stricter than a parent
  // object fallback: an authored `rack.slot_A1` target must have real declared
  // geometry for slot_A1 at this placement, or the scene fails visibly and the
  // broken protocol cannot masquerade as a whole-object click.
  const active_subpart_selection = createMemo(() => {
    const active_target = props.activeAffordance?.().active_target ?? null;
    return resolve_active_subpart_selection(object_def, placement_target, active_target);
  });
  const active_exact_subpart = createMemo<string | null>(() => {
    return active_subpart_selection()?.target_name ?? null;
  });

  // A rack can contain subparts only a few CSS pixels wide at its ordinary
  // scene scale. When one is the directed target, magnify that SAME object
  // about the subpart centre until EVERY declared sibling has a usable core.
  // That is intentional: a wrong click must arrive at the ordinary protocol
  // rejection path, never disappear through a tiny or inert neighbouring
  // target.  Geometry is not padded; scaling preserves the authored gaps and
  // therefore cannot make sibling hit regions overlap. offsetWidth/offsetHeight
  // intentionally ignore CSS transforms, so this calculation stays stable
  // after the focus transform is applied.
  let item_element: HTMLDivElement | undefined;
  const [item_measurement_revision, set_item_measurement_revision] = createSignal(0);
  let item_resize_observer: ResizeObserver | undefined;
  onCleanup(() => item_resize_observer?.disconnect());
  const exact_subpart_focus_style = createMemo<Record<string, string>>(() => {
    item_measurement_revision();
    const selection = active_subpart_selection();
    if (
      selection === null ||
      item_element === undefined ||
      object_def?.view_box === undefined ||
      object_def.subpart_geometry === undefined
    ) {
      return {};
    }
    const selected_metrics = selection.member_names.map((member_name) => {
      const geometry = object_def.subpart_geometry?.[member_name];
      if (geometry === undefined) {
        // active_subpart_selection already provides the public, precise
        // failure; this narrows a concurrent declaration read.
        return null;
      }
      return subpart_geometry_metrics(geometry);
    });
    if (selected_metrics.some((metrics) => metrics === null)) {
      return {};
    }
    const concrete_metrics = selected_metrics.filter(
      (metrics): metrics is NonNullable<typeof metrics> => metrics !== null,
    );
    const selection_left = Math.min(
      ...concrete_metrics.map((metrics) => metrics.center_x - metrics.width / 2),
    );
    const selection_right = Math.max(
      ...concrete_metrics.map((metrics) => metrics.center_x + metrics.width / 2),
    );
    const selection_top = Math.min(
      ...concrete_metrics.map((metrics) => metrics.center_y - metrics.height / 2),
    );
    const selection_bottom = Math.max(
      ...concrete_metrics.map((metrics) => metrics.center_y + metrics.height / 2),
    );
    const selection_center_x = (selection_left + selection_right) / 2;
    const selection_center_y = (selection_top + selection_bottom) / 2;
    const computed_style = window.getComputedStyle(item_element);
    const item_width = Number.parseFloat(computed_style.width);
    const item_height = Number.parseFloat(computed_style.height);
    if (item_width <= 0 || item_height <= 0) {
      return {};
    }
    // Leave a small fractional-pixel margin. Browser layout can otherwise
    // render a mathematically 24px subpart as 23.99px, which is neither easy
    // to click nor acceptable to the visible-action walkthrough guard.
    const minimum_core_px = 26;
    let scale = 1;
    for (const sibling_geometry of Object.values(object_def.subpart_geometry)) {
      const sibling_metrics = subpart_geometry_metrics(sibling_geometry);
      const sibling_width_px = (item_width * sibling_metrics.width) / object_def.view_box.width;
      const sibling_height_px = (item_height * sibling_metrics.height) / object_def.view_box.height;
      if (sibling_width_px <= 0 || sibling_height_px <= 0) {
        return {};
      }
      scale = Math.max(
        scale,
        minimum_core_px / sibling_width_px,
        minimum_core_px / sibling_height_px,
      );
    }
    if (!Number.isFinite(scale) || scale <= 1) {
      return {};
    }
    const origin_x =
      ((selection_center_x - object_def.view_box.min_x) / object_def.view_box.width) * 100;
    const origin_y =
      ((selection_center_y - object_def.view_box.min_y) / object_def.view_box.height) * 100;
    return {
      transform: `scale(${scale})`,
      "transform-origin": `${origin_x}% ${origin_y}%`,
      "z-index": "4",
    };
  });

  function bind_item_element(element: HTMLDivElement): void {
    item_element = element;
    item_resize_observer?.disconnect();
    item_resize_observer = new ResizeObserver(() => {
      set_item_measurement_revision((revision) => revision + 1);
    });
    item_resize_observer.observe(element);
    set_item_measurement_revision((revision) => revision + 1);
  }

  // Directed whole-object actions get the same learner-first guarantee as
  // dotted targets: the real rendered object has a 24px visible core and lies
  // within the browser viewport. This applies to every directed gesture, never
  // `select`, so a multiple-choice answer is not secretly singled out.
  const active_directed_top_level = createMemo<boolean>(() => {
    const affordance = props.activeAffordance?.();
    return (
      active_exact_subpart() === null &&
      affordance?.active_target === placement_target &&
      affordance.active_gesture !== null &&
      affordance.active_gesture !== "select"
    );
  });
  const top_level_focus_style = createMemo<Record<string, string>>(() => {
    // Read the full affordance snapshot as well as the derived boolean. A
    // click -> adjust transition keeps the boolean true, so depending only on
    // that memo would suppress the update even though the shell geometry
    // changed around the scene.
    props.activeAffordance?.();
    item_measurement_revision();
    if (!active_directed_top_level()) {
      return {};
    }
    const minimum_core = {
      "min-width": "24px",
      "min-height": "24px",
      "z-index": "4",
    };
    if (item_element === undefined) {
      return minimum_core;
    }
    // offsetWidth/offsetHeight round fractional layout pixels to integers. At
    // small scales that rounding can turn a mathematically 24px focus into a
    // real 23.46px hit box. Computed width/height retain the browser's
    // fractional untransformed box, so the rendered guarantee is truly >=24px.
    const computed_style = window.getComputedStyle(item_element);
    const raw_width = Number.parseFloat(computed_style.width);
    const raw_height = Number.parseFloat(computed_style.height);
    if (raw_width <= 0 || raw_height <= 0) {
      return minimum_core;
    }
    const scale = Math.max(1, 24 / raw_width, 24 / raw_height);
    const bounds = item_element.getBoundingClientRect();
    const focused_width = bounds.width * scale;
    const focused_height = bounds.height * scale;
    const original_center_x = bounds.left + bounds.width / 2;
    const original_center_y = bounds.top + bounds.height / 2;
    const desired_center_x =
      focused_width <= window.innerWidth
        ? Math.min(
            Math.max(original_center_x, focused_width / 2),
            window.innerWidth - focused_width / 2,
          )
        : window.innerWidth / 2;
    const desired_center_y =
      focused_height <= window.innerHeight
        ? Math.min(
            Math.max(original_center_y, focused_height / 2),
            window.innerHeight - focused_height / 2,
          )
        : window.innerHeight / 2;
    const delta_x = desired_center_x - original_center_x;
    const delta_y = desired_center_y - original_center_y;
    if (scale <= 1 && delta_x === 0 && delta_y === 0) {
      return minimum_core;
    }
    return {
      ...minimum_core,
      transform: `translate(${delta_x}px, ${delta_y}px) scale(${scale})`,
      "transform-origin": "center",
    };
  });
  // Whether this object declares any visual_states. When it does not, there is
  // no reactive artwork to derive: we render the item's bound asset directly
  // (the asset chosen at bind time by the layout pipeline), preserving static
  // behavior for decor/equipment that has no state-driven art.
  const has_visual_states = Object.keys(visual_states).length > 0;

  // Reactive degraded message for THIS item. Empty string means "not degraded".
  // A resolver failure (a content bug, e.g. a visual_states formula referencing
  // an undeclared field) is surfaced here, NOT swallowed: it sets this signal,
  // which stamps an observable per-item marker (data-resolver-degraded) AND
  // notifies SceneView via onDegrade so SceneView can reactively own the
  // scene-root data-scene-degraded marker. This routes the failure through the
  // SAME observable degrade channel structural_guards uses (data-scene-degraded
  // on the scene root), so a walker/test can detect it -- but ownership now
  // lives in SceneView, removing the old closest()/onMount timing race. We do
  // NOT throw from the memo: a Solid memo throw propagates up and blanks the
  // whole reactive tree (there is no per-item report-mode wrapper), violating
  // the degrade-never-blank policy. We also do NOT silently return null: that is
  // the exact bug-hiding fallback this fix removes.
  const [resolverDegraded, setResolverDegraded] = createSignal<string>("");
  const [anchorMaterialDegraded, setAnchorMaterialDegraded] = createSignal<string>("");

  // Pure resolution result: the resolved state OR the error message. The memo
  // stays PURE (no signal writes, no console side effects, no DOM reach): it
  // only computes. Reading store.state[target] inside the memo subscribes the
  // memo (and thus only this item's reactive fragments) to that target's state.
  // An ObjectStateChange re-runs this memo and updates the affected fragments
  // WITHOUT remounting the item's DOM node.
  type ResolveResult = { state: ResolvedVisualState | null; error: string };
  const resolveResult = createMemo<ResolveResult>(() => {
    if (is_placeholder || !has_visual_states) {
      return { state: null, error: "" };
    }
    const state = read_object_state(props.store, target);
    // An object with visual_states whose target was not seeded (no declared
    // state schema, so build_seed_list skipped it) has no state to resolve
    // against. Skip resolution and fall back to the bound asset; resolving an
    // empty state against a field-referencing formula would throw.
    if (Object.keys(state).length === 0) {
      return { state: null, error: "" };
    }
    // The strict resolver behavior is preserved for tests/CI that call
    // resolve_visual_state directly. Here in the render path a failure must
    // surface observably (degraded marker + loud warn) rather than blanking the
    // scene or being silently nulled. We keep the catch narrow to this single
    // resolve call so an unrelated bug in surrounding render code is not masked.
    try {
      const resolvedState = resolve_visual_state(visual_states, state, props.materialRegistry);
      return { state: resolvedState, error: "" };
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      return { state: null, error: message };
    }
  });

  // The resolved visual state for downstream rendering (overlays / asset).
  const resolved = createMemo<ResolvedVisualState | null>(() => resolveResult().state);

  // Side-effect channel for a resolver failure. This effect is the ONLY place
  // that mutates the degrade signals / warns / notifies SceneView, keeping the
  // memo pure. It runs on first render and whenever the resolve result changes:
  //   - stamps the per-item data-resolver-degraded signal,
  //   - warns loudly once per transition into a failure,
  //   - notifies SceneView via onDegrade so SceneView reactively owns the
  //     scene-root data-scene-degraded marker (no closest()/onMount race).
  let lastError = "";
  createEffect(() => {
    const error = resolveResult().error;
    setResolverDegraded(error);
    if (error.length > 0 && error !== lastError) {
      // eslint-disable-next-line no-console
      console.warn(`SceneItem "${target}" visual-state resolution degraded: ${error}`);
    }
    lastError = error;
  });

  const degradationMessage = createMemo<string>(
    () => resolverDegraded() || anchorMaterialDegraded(),
  );
  createEffect(() => {
    props.onDegrade?.(target, degradationMessage());
  });

  // The base asset to inject. When visual_states drive the asset, use the
  // resolved asset; otherwise fall back to the bound item.asset (static).
  const asset_name = createMemo<string>(() => {
    const r = resolved();
    if (r !== null && r.asset_name !== null) {
      return r.asset_name;
    }
    return item.asset;
  });
  const asset_layers = createMemo<readonly string[]>(() => resolved()?.asset_layers ?? []);
  const [domSvgHost, setDomSvgHost] = createSignal<HTMLElement | undefined>(undefined);

  // Reactive highlight flags.
  const flags = createMemo(() => read_flags(props.store, target));

  // Base style: static geometry plus reactive highlight outline. The outline
  // is a box-shadow so it does not change layout box size (no geometry math).
  const base_style = position_style(item);

  const highlight_style = createMemo<Record<string, string>>(() => {
    const f = flags();
    if (f.is_selected) {
      return { "box-shadow": "0 0 0 2px #4a90d9", "border-radius": "2px" };
    }
    return {};
  });

  // Keep the whole style object itself behind one reactive memo. A SceneChange
  // mounts a fresh item before the new active interaction is published; the
  // later click -> adjust transition must therefore reapply focus styles, not
  // leave the first object-literal snapshot frozen at mount time. Declare it
  // after both dependencies so the Solid compiler cannot evaluate a temporal
  // dead zone while it establishes the memo graph.
  const rendered_item_style = createMemo<Record<string, string>>(() => ({
    ...base_style,
    ...highlight_style(),
    ...exact_subpart_focus_style(),
    ...top_level_focus_style(),
  }));

  // Derived affordance kind for this item (the affordance memo). The accessor is read as a
  // FUNCTION CALL inside this memo so Solid tracks the snapshot signal as a
  // reactive dependency. Reading props.activeAffordance?.() outside the memo
  // (e.g. at SceneItem setup time) would capture a stale value and break
  // reactivity; it must stay inside. candidate_targets falls back to the shared
  // EMPTY_CANDIDATE_TARGETS constant when the prop is absent -- never a new Set.
  const affordance_kind = createMemo<"active" | "candidate" | "none">(() => {
    // Read the accessor INSIDE the memo: this is the reactive-tracking
    // requirement from the plan (SolidJS concepts/effects.mdx + on-util.mdx).
    const affordance = props.activeAffordance?.();
    const candidate_targets = props.candidateTargets ?? EMPTY_CANDIDATE_TARGETS;
    return compute_affordance_kind({
      active_target: affordance?.active_target ?? null,
      active_gesture: affordance?.active_gesture ?? null,
      // The affordance space is placement_name: active_target carries the
      // adapter-resolved placement_name and candidate_targets holds
      // placement_names, so this item's key must be its placement_name too. A
      // twice-placed object then rings the one active placement, not both.
      item_target: placement_target,
      candidate_targets,
    });
  });

  // data-asset reflects the currently rendered asset so stats tooling reads
  // the live asset. For state-free objects the resolved asset equals the
  // bound asset from the layout pipeline.

  // Per-subpart degrade forwarder. A failing well (the color resolver returns
  // ok:false for that subpart's material) is routed to the SAME SceneView-owned
  // degrade sink the object-level resolver uses, but under a subpart-qualified
  // target ("well_plate_96.A1") so each failing well is tracked independently and
  // the scene-root data-scene-degraded marker reflects it. A recovering well
  // clears its own membership with an empty message. This keeps a subpart-level
  // content defect observable instead of a silently invisible well.
  function forward_subpart_degrade(subpart_name: string, message: string): void {
    if (props.onDegrade) {
      props.onDegrade(`${target}.${subpart_name}`, message);
    }
  }

  if (is_placeholder) {
    const placeholder_kind = item._missing_object === true ? "missing-object" : "missing-svg";
    return (
      <div
        data-placement-name={item.placement_name}
        data-object-name={item.object_name}
        data-zone={item.zone}
        data-kind={item.kind}
        data-depth={item.depth ?? undefined}
        data-item-id={is_clickable ? placement_target : undefined}
        data-asset={item.asset}
        data-exact-subpart-target={active_exact_subpart() ?? undefined}
        data-affordance={affordance_kind()}
        data-missing-svg="true"
        data-placeholder-kind={placeholder_kind}
        style={{
          ...base_style,
          "box-sizing": "border-box",
          border: "2px dashed #c0392b",
          "background-color": "#fdf2f1",
          display: "flex",
          "align-items": "center",
          "justify-content": "center",
          overflow: "visible",
        }}
      >
        <PlaceholderBody item={item} />
      </div>
    );
  }

  return (
    <div
      ref={bind_item_element}
      data-placement-name={item.placement_name}
      data-object-name={item.object_name}
      data-zone={item.zone}
      data-kind={item.kind}
      data-depth={item.depth ?? undefined}
      data-item-id={is_clickable ? placement_target : undefined}
      data-asset={asset_name()}
      data-exact-subpart-target={active_exact_subpart() ?? undefined}
      data-material={resolved()?.data_attrs["data-material"]}
      data-resolver-degraded={degradationMessage().length > 0 ? degradationMessage() : undefined}
      data-affordance={affordance_kind()}
      data-timed-wait={flags().timed_wait_active ? "active" : undefined}
      style={rendered_item_style()}
    >
      {/* SVG host keyed by the resolved asset name. When the asset changes
          (e.g. an SvgSwap-style enum visual_state), the keyed Show remounts
          only the inner SVG host, never the item's outer node. */}
      <Show when={asset_name()} keyed>
        {(asset) => (
          <SvgHost
            asset={asset}
            svgInstanceKey={`${props.sceneName}__${item.placement_name}`}
            onDomSvgHostReady={setDomSvgHost}
          />
        )}
      </Show>
      <For each={asset_layers()}>
        {(asset) => (
          <div
            data-asset-layer={asset}
            style={{ position: "absolute", inset: "0", "pointer-events": "none" }}
          >
            <ImgSvgHost asset={asset} />
          </div>
        )}
      </For>
      <AnchorMaterialEffects
        host={domSvgHost()}
        resolved={resolved()}
        onDegrade={setAnchorMaterialDegraded}
      />
      <Show when={resolved() !== null}>
        <Overlays resolved={resolved()!} />
      </Show>
      {/* Structured-subpart material overlay. Rendered
          only when this object DECLARES the subpart material-tint contract
          (subpart_contract non-null + object_def present). The generic
          interpreter draws one shape per generated subpart geometry, each tinted
          by its own per-subpart material through the store + color resolver. */}
      <Show when={subpart_contract !== null && object_def !== undefined}>
        <SubpartVisualStateOverlay
          def={object_def!}
          store={props.store}
          placement_id={target}
          identity_field_name={subpart_contract!.identity_field_name}
          amount_field_name={subpart_contract!.amount?.field_name ?? null}
          capacity={subpart_contract!.amount?.capacity ?? null}
          capacity_error={subpart_contract!.amount?.capacity_error ?? ""}
          registry={props.materialRegistry}
          on_subpart_degrade={forward_subpart_degrade}
        />
      </Show>
      <Show when={is_clickable && object_def !== undefined}>
        <SubpartHitSurface
          def={object_def!}
          placement_name={placement_target}
          activeAffordance={props.activeAffordance}
          candidateTargets={props.candidateTargets ?? EMPTY_CANDIDATE_TARGETS}
        />
      </Show>
      <Show when={flags().timed_wait_active}>
        <div class="scene-item-timed-wait" role="status">
          <span aria-hidden="true">Timer:</span>
          <span>{flags().timed_wait_display ?? "Timed phase in progress"}</span>
        </div>
      </Show>
    </div>
  );
}
