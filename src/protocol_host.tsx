// src/protocol_host.tsx
//
// Protocol host page entry. Wires every runtime module and every shell
// component into one mountable page that loads a specific protocol selected
// by URL query (?protocol=<name>) or by an inlined window.__PROTOCOL_NAME__
// fallback set by the per-protocol HTML wrapper.
//
// Mount order:
//   1. Resolve protocol name (query string or window fallback).
//   2. Look up ProtocolConfig from generated/protocols.ts.
//   3. Load and validate this protocol's saved session, if one exists.
//   4. Resolve the entry scene: (1) the restored checkpoint; (2) the entry
//      step's optional scene: field;
//      (3) the first SceneChange.to_scene in the entry step; (4) throw.
//      For sequence_runner protocols, resolution delegates to the first
//      mini-protocol's entry step. See resolve_entry_scene.ts.
//   5. Load precomputed layout and restore or initialize scene state before
//      the Solid renderer paints #scene-root.
//   6. Build emitter (seeded with initial ShellViewSnapshot), browser
//      scene-op handler, step machine, and click resolver.
//   7. Mount <ProtocolHud /> into #shell-root unless ?shell=off.
//   8. step_machine.start() drives the rest via emitter subscription.
//
// Debug-only query params (documented in seam_interface.md):
//   ?shell=off       -- skip shell mount; runtime still runs.
//   ?walker=expose   -- set window.__shellEmitter for the walker.
//
// References:
//   - docs/active_plans/active/web_ui/seam_interface.md (debug flags)
//   - src/shell/adapter/types.ts (closed seam contract)
//   - docs/PRIMARY_CONTRACT.md item 4 (visible UI contract)

import type {
  Gesture,
  ProtocolConfig,
  ProtocolShellEvent,
  ProtocolShellEmitter,
  ShellViewSnapshot,
  TimedWaitOp,
  UnsubscribeFn,
} from "./shell/adapter/types";

import { PROTOCOLS } from "../generated/protocols.js";
import { PROTOCOLS_INDEX_SLIM } from "../generated/protocols_index_slim.js";
import { SCENES } from "../generated/scenes.js";
import { OBJECT_LIBRARY } from "../generated/object_library.js";

import type { PipelineResult } from "./scene_runtime/layout/types.js";
import { resolvePrecomputedResult } from "./scene_runtime/layout/precomputed_result.js";
import { build_seed_list, mountScene, type SceneDispose } from "./scene_runtime/renderer/index.js";
import type { MaterialRegistry } from "./scene_runtime/renderer/visual_state_resolver.js";
import { create_scene_store } from "./scene_runtime/state/scene_store.js";
import { create_state_field_lookup } from "./scene_runtime/state/state_field_lookup_impl.js";
import { PROTOCOL_MATERIALS } from "../generated/protocol_materials.js";

import { createProtocolShellEmitter } from "./scene_runtime/protocol/emitter.js";
import {
  create_step_machine,
  create_snapshot_reducer,
  type StepMachineHandle,
  validate_step_machine_checkpoint,
} from "./scene_runtime/protocol/step_machine.js";
import { create_scene_op_handler } from "./scene_runtime/protocol/scene_operations.js";
import { build_store_scene_op_deps } from "./scene_runtime/protocol/scene_op_deps.js";
import { timed_wait_runtime_delay_ms } from "./scene_runtime/protocol/timed_wait.js";
import { install_walker_debug_surface } from "./scene_runtime/protocol/walker_debug.js";
import { attach_click_resolver } from "./scene_runtime/protocol/click_resolver.js";
import {
  scene_click_to_command,
  dispatch_gesture,
} from "./scene_runtime/protocol/gesture_registry.js";
import {
  build_target_adapter,
  IDENTITY_TARGET_ADAPTER,
  type TargetAdapter,
} from "./scene_runtime/protocol/target_adapter.js";
import { collect_reachable_scene_names } from "./scene_runtime/protocol/target_existence_check.js";
import type { ActiveAffordanceAccessor } from "./scene_runtime/protocol/affordance.js";
import {
  resolve_entry_scene_name,
  assert_scene_not_empty,
} from "./scene_runtime/protocol/resolve_entry_scene.js";
import { flatten_sequence_runner } from "./scene_runtime/protocol/flatten_sequence_runner.js";
import {
  create_protocol_session_persistence,
  fingerprint_protocol,
  type SessionSaveStatus,
} from "./scene_runtime/protocol/session_persistence.js";

import { createSignal } from "solid-js";
import { render } from "solid-js/web";
import { subscribeEmitterToSnapshot } from "./shell/signals.js";
import { ProtocolHud } from "./shell/hud/protocol_hud.js";
import { TypeInput } from "./shell/hud/type_input.js";
import { SetPointEditor } from "./shell/hud/set_point_editor.js";

//============================================
// Window extensions (debug-only)
//============================================

// Walker exposes the emitter via window.__shellEmitter when
// ?walker=expose is set. Inlined fallback for the protocol name is
// optional and set by the per-protocol HTML wrapper.
declare global {
  interface Window {
    __shellEmitter?: ProtocolShellEmitter;
    __PROTOCOL_NAME__?: string;
  }
}

//============================================
// Helpers
//============================================

// Read a query param without throwing on missing search string.
function read_query_param(name: string): string | null {
  const search = window.location.search;
  const params = new URLSearchParams(search);
  return params.get(name);
}

//============================================
// Production layout source
//============================================

// The shipped browser bundle serves only the build-time precomputed layout from
// generated/precomputed_layout.ts via resolvePrecomputedResult(). The runtime
// layout engine (runPipeline) is no longer imported or reachable from this
// production path; the ?layout=runtime parity switch was retired once parity
// was proven (38/38 scenes matched). The engine still lives on disk and runs at
// BUILD time (pipeline/precompute_layout.mjs) and in tests, but no runPipeline
// call path ships to users.

// Resolve the active protocol name. URL wins over the inlined fallback.
function resolve_protocol_name(): string {
  const from_url = read_query_param("protocol");
  if (from_url !== null && from_url !== "") {
    return from_url;
  }
  const from_window = window.__PROTOCOL_NAME__;
  if (typeof from_window === "string" && from_window !== "") {
    return from_window;
  }
  throw new Error(
    "protocol_host: no protocol selected (set ?protocol=<name> or window.__PROTOCOL_NAME__)",
  );
}

function resolve_display_title(protocol_name: string): string {
  const entry = PROTOCOLS_INDEX_SLIM.find((candidate) => {
    return candidate.protocol_name === protocol_name;
  });
  if (!entry) {
    throw new Error(`protocol_host: protocol "${protocol_name}" not found in slim index`);
  }
  return entry.display_title;
}

// resolve_entry_scene_name is imported from resolve_entry_scene.ts.
// See that file for the full precedence spec and sequence_runner delegation logic.
// This thin wrapper binds the module-level PROTOCOLS map so callers in mount()
// do not have to pass it explicitly.
function resolve_entry_scene_name_bound(config: ProtocolConfig): string {
  return resolve_entry_scene_name(config, PROTOCOLS);
}

// Initial snapshot seed. Derived directly from the protocol config so the
// HUD has sensible values before the first event fires.
function build_initial_snapshot(config: ProtocolConfig): ShellViewSnapshot {
  const total_step_count = config.steps?.length ?? config.mini_protocols?.length ?? 0;
  const initial: ShellViewSnapshot = {
    protocol_name: config.protocol_name,
    current_step_name: null,
    current_prompt: null,
    // No step active yet; tip resolves to null until step_started fires.
    current_tip: null,
    active_interaction: null,
    progress: { completed_step_count: 0, total_step_count },
    last_outcome: null,
    last_rejection: null,
    last_interaction_feedback: null,
    pending_validator_kind: null,
    modal: {
      is_open: false,
      kind: null,
      prompt: null,
      choices: [],
      invoking_target: null,
    },
    help: { is_open: false, topic: null },
    tray: { items: [] },
    active_scene_name: null,
    is_complete: false,
    pending_timed_wait: null,
  };
  return initial;
}

//============================================
// Mount
//============================================

function mount(): void {
  const protocol_name = resolve_protocol_name();
  const display_title = resolve_display_title(protocol_name);
  document.title = `${display_title} | Virtual Lab Coach`;

  // Look up the protocol config. PROTOCOLS is a closed record so a
  // missing entry must throw clearly rather than silently no-op.
  const config = PROTOCOLS[protocol_name];
  if (!config) {
    throw new Error(`protocol_host: protocol "${protocol_name}" not found in PROTOCOLS`);
  }
  // Sequence-runner playback: a sequence_runner carries no steps of its own, only
  // an ordered mini_protocols list. flatten_sequence_runner expands it into one
  // flat mini_protocol-shaped config whose next_step chain plays every
  // constituent mini-protocol in order (each mini's entry step carries its
  // resolved entry scene, so the step machine renders the correct scene at each
  // boundary). A non-runner config passes through unchanged. Everything
  // downstream -- reducer, step machine, walker surface, HUD -- then runs the one
  // flat steps list with no sequence-runner special case. The original runner
  // config in PROTOCOLS is untouched.
  const active_config = flatten_sequence_runner(config, PROTOCOLS);

  // Browser persistence is a real product boundary, not a walker fixture. One
  // repository-wide schema version and one root localStorage key own every
  // protocol session. The exact flattened protocol shape invalidates stale
  // progress without adding version fields to authored YAML.
  const persistence = create_protocol_session_persistence(
    window.localStorage,
    protocol_name,
    fingerprint_protocol(active_config),
  );
  const load_result = persistence.load();
  let restored_session = load_result.kind === "restored" ? load_result.session : null;
  const initial_session_status: SessionSaveStatus =
    load_result.kind === "restored"
      ? "restored"
      : load_result.kind === "unavailable"
        ? "unavailable"
        : "fresh";
  const [session_status, set_session_status] =
    createSignal<SessionSaveStatus>(initial_session_status);
  // The learner owns hint disclosure for the lifetime of this protocol page.
  // Keep it above the shell branches so a timed wait or other component
  // remount cannot silently close the native details element.
  const [action_hint_open, set_action_hint_open] = createSignal(false);
  if (restored_session !== null) {
    document.documentElement.dataset.protocolSessionRevision = String(
      restored_session.persistence_revision,
    );
  }

  // Resolve the permanent DOM hosts. Shell mounts as a sibling of scene-root,
  // never as an ancestor (asset-cropping rule). Value-entry controls are host
  // structure, not body-mounted overlays, so they remain usable under
  // ?shell=off without participating in optional shell composition.
  const scene_root = document.getElementById("scene-root");
  if (!(scene_root instanceof HTMLElement)) {
    throw new Error("protocol_host: #scene-root element not found");
  }
  const active_scene_root = scene_root;
  const scene_frame_element = active_scene_root.closest(".scene-panel-inner");
  if (!(scene_frame_element instanceof HTMLElement)) {
    throw new Error("protocol_host: #scene-root must be inside .scene-panel-inner");
  }
  const scene_frame: HTMLElement = scene_frame_element;
  const scene_panel_element = scene_frame.closest(".scene-panel");
  if (!(scene_panel_element instanceof HTMLElement)) {
    throw new Error("protocol_host: #scene-root must be inside .scene-panel");
  }
  const scene_panel: HTMLElement = scene_panel_element;
  const scene_annotation_root_element = document.getElementById("scene-annotation-root");
  if (!(scene_annotation_root_element instanceof HTMLElement)) {
    throw new Error("protocol_host: #scene-annotation-root element not found");
  }
  const scene_annotation_root: HTMLElement = scene_annotation_root_element;
  const shell_root = document.getElementById("shell-root");
  if (!(shell_root instanceof HTMLElement)) {
    throw new Error("protocol_host: #shell-root element not found");
  }
  const type_input_root = document.getElementById("type-input-root");
  if (!(type_input_root instanceof HTMLElement)) {
    throw new Error("protocol_host: #type-input-root element not found");
  }
  const adjust_editor_root = document.getElementById("adjust-editor-root");
  if (!(adjust_editor_root instanceof HTMLElement)) {
    throw new Error("protocol_host: #adjust-editor-root element not found");
  }

  // Resolve the entry scene from the flattened config. For a runner this reads
  // the first constituent's namespaced entry step (whose scene the flattener set
  // to that mini's resolved entry scene); for a normal protocol it is unchanged.
  const entry_scene_name = resolve_entry_scene_name_bound(active_config);
  let scene_name = restored_session?.machine.current_scene ?? entry_scene_name;

  // Measure actual #scene-root pixel dimensions before running the pipeline.
  // getBoundingClientRect() forces a synchronous layout reflow so the CSS grid
  // and flex sizing is resolved. The bounded panel is NOT full viewport and may
  // have a different aspect ratio than DEFAULT_VIEWPORT (1920x1080). The
  // pipeline's vertical_layout stage uses viewport W/H to compute item heights
  // as percentages. Passing the actual panel size makes item heights correct for
  // the bounded box: rendered pixel aspect = (visualWidth/height) * (panelW/panelH)
  // = aspect_svg (correct). Using the wrong viewport aspect ratio here would cause
  // Guard 5 (structural_guards.ts) to throw an aspect-distortion error.
  function measure_scene_viewport(el: HTMLElement): { w: number; h: number } {
    // Forces a layout reflow. Reliable even in synchronous DOMContentLoaded context.
    const rect = el.getBoundingClientRect();
    // Fail loud: zero dimensions mean CSS has not been applied or the element is
    // not yet in the rendered tree. A silent 1920x1080 fallback would hide a real
    // layout failure and cause incorrect item sizing downstream.
    if (rect.width === 0 || rect.height === 0) {
      throw new Error(
        `protocol_host: #scene-root has zero dimensions (${rect.width}x${rect.height}); CSS may not be applied`,
      );
    }
    const w = Math.round(rect.width);
    const h = Math.round(rect.height);
    return { w, h };
  }

  // Measure the actual panel size. With CSS aspect-ratio: 16/9 on #scene-root,
  // the panel should be close to 16:9 but the grid layout may constrain it to
  // a non-16:9 size depending on header/guidance bar heights. The measured size
  // is always correct regardless of CSS constraints.
  const scene_viewport = measure_scene_viewport(active_scene_root);

  // Per-protocol material registry. Each protocol package carries its
  // own materials.yaml; gen_protocols.py emits PROTOCOL_MATERIALS keyed by
  // protocol_name. A protocol with no materials.yaml has no entry; null then
  // disables material-color resolution (geometry/asset/overlays still resolve).
  // sequence_runner registries aggregate their constituent mini-protocols.
  const material_registry: MaterialRegistry | null = PROTOCOL_MATERIALS[protocol_name] ?? null;

  // Reactive scene store shared by the Solid renderer and the store-driven
  // store-driven scene_operations. The renderer seeds it from each rendered
  // scene's PipelineResult; scene operations write it after a validated
  // interaction, and the Solid renderer reacts. The material registry backs the
  // D1 acceptance check for material_name / held_material_name writes so a
  // registered drug (carboplatin, mtt) is accepted at the store and reaches the
  // well, while an unregistered non-sentinel name is rejected loudly -- the same
  // predicate the Python stepper applies.
  const scene_store = create_scene_store(material_registry);

  // The active scene's Solid root dispose handle. render_scene.ts owns the
  // dispose; protocol_host holds the latest handle so host teardown (and the
  // SceneChange reset path) can release it. mountScene returns the handle and
  // disposes any prior root for the same element internally.
  let active_dispose: SceneDispose | null = null;
  // Exactly one protocol session owns the durable declared-state archive. The
  // first scene projects its validated root initial_state; later SceneChange
  // calls reconcile that same archive rather than replacing it.
  let session_started = false;

  // Scene-scoped target-identity adapter. Rebuilt from each mounted scene's
  // placements inside render_protocol_scene so an authored protocol target
  // resolves against whatever scene is currently mounted. current_adapter holds
  // the live per-scene adapter; delegating_adapter is a STABLE wrapper captured
  // once by the step machine (created below) whose methods forward to the live
  // adapter, so a SceneChange re-point needs no step-machine rebuild. Starts as
  // identity until the entry scene mounts.
  let current_adapter: TargetAdapter = IDENTITY_TARGET_ADAPTER;
  const delegating_adapter: TargetAdapter = {
    resolve_to_placement: (target: string): string => current_adapter.resolve_to_placement(target),
    resolve_to_object: (target: string): string => current_adapter.resolve_to_object(target),
    has_target: (target: string): boolean => current_adapter.has_target(target),
    placements_for: (target: string): readonly string[] => current_adapter.placements_for(target),
  };

  function render_protocol_scene(
    next_scene_name: string,
    seed_mode: "replace" | "reconcile" | "none" = "replace",
  ): void {
    const scene = SCENES[next_scene_name];
    if (!scene) {
      throw new Error(
        `protocol_host: scene "${next_scene_name}" not found in SCENES for protocol "${protocol_name}"`,
      );
    }

    // Production layout source: load the build-time precomputed layout keyed by
    // scene_name. The canonical 16:9 frame (forced by the CSS
    // letterbox) means the precomputed positions are pixel-correct for the
    // rendered frame regardless of panel pixel size. A missing entry throws
    // loudly inside resolvePrecomputedResult rather than silently falling back
    // to the runtime engine (single production path = precomputed).
    const pipeline_result: PipelineResult = resolvePrecomputedResult(next_scene_name, scene);
    const interaction_geometry = pipeline_result.interactionGeometry;
    if (!interaction_geometry.valid) {
      throw new Error(
        `protocol_host: scene "${next_scene_name}" has invalid interaction geometry (${interaction_geometry.issues
          .map((issue) => issue.kind)
          .join(", ")})`,
      );
    }
    const minimum_frame = interaction_geometry.minimum_frame;
    const minimum_frame_text = `${minimum_frame.width_px}x${minimum_frame.height_px}`;
    const hit_core_text = String(minimum_frame.hit_core_px);
    // The host owns shell sizing, but it consumes the precomputed scene contract
    // verbatim: no browser-side envelope or frame calculation is permitted.
    for (const element of [scene_panel, scene_frame]) {
      element.style.setProperty("--scene-min-interaction-width", `${minimum_frame.width_px}px`);
      element.style.setProperty("--scene-min-interaction-height", `${minimum_frame.height_px}px`);
      element.style.setProperty("--scene-interaction-hit-core", `${minimum_frame.hit_core_px}px`);
      element.dataset.minimumInteractionFrame = minimum_frame_text;
      element.dataset.interactionHitCorePx = hit_core_text;
    }

    // Rebuild the scene-scoped target-identity adapter from this scene's
    // placements. Every ComputedItem carries its unique placement_name and its
    // object_name; the adapter maps authored targets to the unique DOM
    // placement_name and back to the object_name store key. build_target_adapter
    // fails loud only when an authored target later names a NON-unique object
    // (one placed more than once) with no disambiguating placement_name.
    current_adapter = build_target_adapter(
      pipeline_result.final.map((item) => ({
        object_name: item.object_name,
        placement_name: item.placement_name,
      })),
    );

    // Fail-loud empty-scene guard (via assert_scene_not_empty).
    // Every protocol must render a non-empty scene; the guard applies uniformly.
    assert_scene_not_empty(pipeline_result.final.length, protocol_name, next_scene_name);

    // Mount (or re-mount) the Solid scene. mountScene owns the Solid root
    // dispose: a re-render into the same root disposes the prior root first
    // (tracked per-root in render_scene.ts), so a SceneChange re-render leaks no
    // orphan roots/effects/listeners. Pass the measured viewport so Guard 5
    // (aspect ratio) uses the same dimensions as the pipeline. The active-
    // affordance accessor (affordance plumbing) is threaded by reference so the renderer
    // derives highlight rings from the live interaction snapshot; mountScene
    // re-enumerates candidate_targets from this scene's PipelineResult, so a
    // SceneChange always rings the correct scene's objects (no stale set).
    // The renderer's third mode intentionally mounts an already-projected
    // session without re-seeding it. Annotate the local union explicitly:
    // `seed_mode` itself is only a caller-facing replace/reconcile choice.
    let effective_seed_mode: "replace" | "reconcile" | "none" = seed_mode;
    if (!session_started) {
      if (restored_session === null) {
        scene_store.start_session(
          build_seed_list(pipeline_result),
          active_config.initial_state ?? [],
        );
      } else {
        scene_store.restore_session(
          build_seed_list(pipeline_result),
          restored_session.declared_state,
          restored_session.cursor_state,
          restored_session.state_revision,
        );
      }
      session_started = true;
      // start_session has already populated the active projection. Avoid the
      // mount facade's compatibility replace path, which intentionally starts
      // a blank session for stand-alone renderer callers.
      effective_seed_mode = "none";
    }
    active_dispose = mountScene(active_scene_root, pipeline_result, {
      store: scene_store,
      materialRegistry: material_registry,
      seedMode: effective_seed_mode,
      viewport: scene_viewport,
      activeAffordance: active_affordance,
      annotationRoot: scene_annotation_root,
    });
    active_scene_root.setAttribute("data-active-scene", next_scene_name);
  }

  // Build the emitter + step machine + scene-op handler. The emitter is created
  // BEFORE the first scene render so the active-affordance accessor can read its
  // snapshot signal; the renderer needs the accessor at mount time.
  const initial_snapshot = build_initial_snapshot(active_config);
  // Resolve the active interaction's authored target to the unique DOM
  // placement_name as it enters the snapshot action, so its placement identity
  // matches the data-item-id the walker clicks, the select-promotion equality,
  // and the affordance highlight. Delegates to the live per-scene adapter.
  function resolve_target_label(target: string): string {
    const object_target = current_adapter.resolve_to_object(target);
    const dot_index = object_target.indexOf(".");
    const object_name = dot_index < 0 ? object_target : object_target.slice(0, dot_index);
    const subpart_name = dot_index < 0 ? null : object_target.slice(dot_index + 1);
    const object_def = OBJECT_LIBRARY[object_name];
    if (object_def === undefined) {
      throw new Error(`protocol_host: no learner-facing label for target "${target}"`);
    }
    if (subpart_name === null || subpart_name === "") {
      return object_def.label;
    }
    const readable_subpart = subpart_name.split("_").join(" ");
    return `${object_def.label} ${readable_subpart}`;
  }

  const reducer = create_snapshot_reducer(
    active_config,
    (target: string): string => current_adapter.resolve_to_placement(target),
    resolve_target_label,
  );
  const emitter = createProtocolShellEmitter(initial_snapshot, reducer);

  // Active-affordance accessor (affordance plumbing). A Solid signal mirrors the emitter
  // snapshot; the accessor returns ONLY the active-interaction slice the
  // renderer needs. It is an ARROW that reads the signal inside, so each scene
  // item's highlight memo tracks the snapshot reactively (Solid store-dep rule)
  // and updates automatically on every step/interaction/scene change. No store
  // write, no createEffect. Threaded by reference into render_protocol_scene.
  const affordance_binding = subscribeEmitterToSnapshot(emitter);
  const affordance_snapshot_signal = affordance_binding.snapshot;
  const active_affordance: ActiveAffordanceAccessor = () => {
    const snap = affordance_snapshot_signal();
    return {
      active_target: snap.active_interaction?.action?.placement_name ?? null,
      active_gesture: snap.active_interaction?.action?.gesture ?? null,
    };
  };

  // Validate the complete candidate before the first render. JSON decoding in
  // the persistence module checks the serialized shape; these two domain
  // boundaries check the checkpoint against the current protocol and every
  // declared value against the current object schemas. The scene-store restore
  // is atomic, so any failure leaves it untouched. Discard only this protocol's
  // entry and continue as a fresh session instead of crashing during mount.
  if (restored_session !== null) {
    try {
      validate_step_machine_checkpoint(active_config, restored_session.machine);
      const restored_scene = SCENES[scene_name];
      if (restored_scene === undefined) {
        throw new Error(`protocol_host: restored scene "${scene_name}" does not exist`);
      }
      const restored_pipeline_result = resolvePrecomputedResult(scene_name, restored_scene);
      scene_store.restore_session(
        build_seed_list(restored_pipeline_result),
        restored_session.declared_state,
        restored_session.cursor_state,
        restored_session.state_revision,
      );
      session_started = true;
    } catch {
      const cleared = persistence.clear();
      restored_session = null;
      scene_name = entry_scene_name;
      delete document.documentElement.dataset.protocolSessionRevision;
      set_session_status(cleared ? "fresh" : "unavailable");
    }
  }

  // First scene render. Runs after the emitter + affordance accessor exist so
  // the renderer mounts with a live highlight derivation from the start.
  render_protocol_scene(scene_name, session_started ? "none" : "replace");
  // Store-driven scene-op deps. ObjectStateChange/CursorAttach write
  // the reactive store; SceneChange re-renders the target scene through
  // render_protocol_scene while reconciling exact target identities, and the
  // deps restore cursor-held state after transient flags reset. TimedWait writes
  // a render-layer equipment phase and schedules its elapsed transition;
  // LayoutMove fails loudly until the layout engine exposes a placement-
  // override write surface.
  let step_machine_for_timer: StepMachineHandle | null = null;
  let timed_wait_timeout: number | null = null;
  function schedule_timed_wait(op: TimedWaitOp): void {
    if (timed_wait_timeout !== null) {
      window.clearTimeout(timed_wait_timeout);
    }
    const duration_ms = timed_wait_runtime_delay_ms(op.duration_min);
    timed_wait_timeout = window.setTimeout(() => {
      timed_wait_timeout = null;
      scene_store.set_flags(op.target, {
        timed_wait_active: false,
        timed_wait_display: null,
      });
      step_machine_for_timer?.handle_timer_elapsed(op.target);
    }, duration_ms);
  }
  const scene_op_handler = create_scene_op_handler(
    build_store_scene_op_deps(
      scene_store,
      (next_scene_name: string) => render_protocol_scene(next_scene_name, "reconcile"),
      schedule_timed_wait,
    ),
  );
  // Read-only declared-field lookup seam. Built over the generated object schemas;
  // the construction layer owns the impl so the protocol layer stays free of any
  // scene_store/registry import. The load-time authored-value validation pass
  // consumes this inside the step machine.
  const lookup_state_field = create_state_field_lookup();

  // Per-scene target adapters for the load-time target-existence invariant
  // before handlers are exposed. collect_reachable_scene_names walks the same
  // reachable step
  // graph the check itself walks, tracking scene transitions the same way the
  // runtime does, so every scene the protocol can actually visit gets its own
  // adapter here -- not only the entry scene. resolvePrecomputedResult is a
  // build-time-precomputed lookup (cheap; no live layout computation), so
  // eagerly building an adapter per reachable scene here, before any handler
  // closure or student interaction, stays a load-time cost.
  const reachable_scene_names = collect_reachable_scene_names(active_config, scene_name);
  const scene_target_adapters: Record<string, TargetAdapter> = {};
  for (const reachable_scene_name of reachable_scene_names) {
    const reachable_scene = SCENES[reachable_scene_name];
    if (!reachable_scene) {
      // Scene-existence is a separate failure class, already guarded by
      // render_protocol_scene's own SCENES lookup when that scene actually
      // mounts. Skip building an adapter for it here; the target-existence
      // check treats an unresolved scene as "not checkable", not a miss.
      continue;
    }
    const reachable_pipeline_result = resolvePrecomputedResult(
      reachable_scene_name,
      reachable_scene,
    );
    scene_target_adapters[reachable_scene_name] = build_target_adapter(
      reachable_pipeline_result.final.map((item) => ({
        object_name: item.object_name,
        placement_name: item.placement_name,
      })),
    );
  }

  const step_machine = create_step_machine(active_config, emitter, scene_op_handler, {
    lookup_state_field,
    // Read-only observed object-state reader over the live scene store. The pure
    // step machine reads current declared state for a target through this seam:
    // target_with_value judges a click against real store state, and
    // final_state_matches builds its snapshot from it. Returns an empty map for
    // an unseeded target.
    read_object_state: (target: string) => {
      const entry = scene_store.state[target];
      return entry === undefined ? {} : entry.state;
    },
    // Scene-scoped target-identity adapter. The step machine normalizes the
    // equality path to the DOM placement_name and the state-read path to the
    // object_name store key through this stable delegating wrapper.
    target_adapter: delegating_adapter,
    // Per-scene resolver for the load-time target-existence invariant.
    // Looks up the eagerly-built adapter for the scene active at each authored
    // target's point in the flow graph.
    resolve_scene_target_adapter: (name: string): TargetAdapter | undefined =>
      scene_target_adapters[name],
    // Seed the step machine's current-scene tracker with the initially-mounted
    // scene so its step-entry scene render (sequence_runner boundary) fires only
    // on an actual change, never redundantly re-rendering the entry scene.
    initial_scene: scene_name,
    ...(restored_session === null ? {} : { restore_checkpoint: restored_session.machine }),
  });
  step_machine_for_timer = step_machine;

  // Persist only after the machine announces a stable accepted-interaction
  // checkpoint. This event fires after synchronous scene operations and step
  // transitions, so the stored cursor and declared state cannot lag the UI.
  let save_queued = false;
  let is_starting_over = false;
  function flush_queued_session_save(): void {
    if (!save_queued || is_starting_over) {
      return;
    }
    save_queued = false;
    const revision = persistence.save(
      step_machine.get_checkpoint(),
      scene_store.snapshot_declared_state(),
      scene_store.snapshot_cursor_state(),
      scene_store.state_revision,
    );
    if (revision === null) {
      set_session_status("unavailable");
      return;
    }
    document.documentElement.dataset.protocolSessionRevision = String(revision);
    set_session_status("saved");
  }

  function on_persistence_event(event: ProtocolShellEvent): void {
    if (event.kind !== "session_checkpoint_changed" || save_queued) {
      return;
    }
    save_queued = true;
    queueMicrotask(flush_queued_session_save);
  }

  const unsubscribe_persistence = emitter.subscribe(on_persistence_event);

  function start_over(): void {
    is_starting_over = true;
    if (!persistence.clear()) {
      is_starting_over = false;
      set_session_status("unavailable");
      return;
    }
    window.location.reload();
  }

  // Restore the read-only walker/debug surfaces (window.PROTOCOL_STEPS +
  // window.gameState) the Solid HUD migration dropped. Read-only: the walker
  // and tests read these to observe progress; nothing advances state by writing
  // them. Sourced from the emitter snapshot + step events + the scene store.
  const dispose_walker_surface = install_walker_debug_surface(active_config, emitter, scene_store);

  // Attach the click resolver to the scene root and route through the gesture
  // registry. The click resolver only knows "a scene object was clicked"
  // (gesture "click"); the registry's scene_click_to_command owns the promotion
  // that used to be an inline ternary here: a click on the active target while
  // the active gesture is `select` becomes a `select` command (the student is
  // choosing the next-step object among the present scene objects, reusing the
  // same visible-click affordance as click); every other scene click stays a
  // `click` command, and the step machine rejects a wrong/non-active target
  // (wrong target / wrong order).
  //
  // A bare click is never promoted to `adjust`, `drag`, or `type`: those each
  // need their own visible affordance. So an
  // active adjust/drag interaction reached by a bare click stays a `click`
  // command and falls to the step machine's gesture validation.
  // dispatch_gesture is the single routing point; the incoming resolver gesture
  // is ignored because the command is derived from the live snapshot.
  attach_click_resolver(active_scene_root, (target: string, _gesture: Gesture) => {
    const snapshot = emitter.get_snapshot();
    const command = scene_click_to_command(
      snapshot.active_interaction?.action?.gesture ?? null,
      snapshot.active_interaction?.action?.placement_name ?? null,
      target,
    );
    dispatch_gesture(step_machine, command);
  });

  // Mount the visible type-input affordance in its permanent in-flow host.
  // The host belongs to the static page grid, so it works whether or not the
  // HUD shell is mounted (?shell=off). It shows only while the active
  // interaction's gesture is `type`; a real fill + commit routes the typed text
  // to step_machine.handle_type_commit (the only advance path), which validates
  // it via the interaction's target_with_value preset.
  const type_binding = subscribeEmitterToSnapshot(emitter);
  const type_snapshot_signal = type_binding.snapshot;
  const dispose_type_input = render(
    () => (
      <TypeInput
        snapshot={type_snapshot_signal}
        on_commit={(target: string, typed_text: string) => {
          // Route the `type` gesture through the single registry dispatch point,
          // same as scene clicks. The registry calls handle_type_commit and
          // returns the runtime's accept signal, which drives the affordance's
          // visible rejection message. accepted is a boolean for the type
          // gesture (never null); ?? false is a defensive coercion only.
          const result = dispatch_gesture(step_machine, {
            gesture: "type",
            target,
            committed_text: typed_text,
          });
          return result.accepted ?? false;
        }}
      />
    ),
    type_input_root,
  );

  // Mount the visible shared numeric set-point editor in its permanent in-flow
  // host. Like the type control it remains available whether or not the HUD is
  // mounted
  // (?shell=off). It shows only while the active interaction's gesture is
  // `adjust`; a real stepper/entry + commit routes the committed number to
  // step_machine.handle_adjust_commit (the only advance path) through the same
  // single registry dispatch point, which validates it via the interaction's
  // target_with_value preset (coercing the number to the field's declared type).
  const adjust_binding = subscribeEmitterToSnapshot(emitter);
  const adjust_snapshot_signal = adjust_binding.snapshot;
  const dispose_adjust_editor = render(
    () => (
      <SetPointEditor
        snapshot={adjust_snapshot_signal}
        on_commit={(target: string, committed_number: number) => {
          // Route the `adjust` gesture through the single registry dispatch
          // point, same as scene clicks and type commits. The registry calls
          // handle_adjust_commit and returns the runtime's accept signal, which
          // drives the editor's visible rejection message. accepted is a boolean
          // for the adjust gesture (never null); ?? false is a defensive coercion.
          const result = dispatch_gesture(step_machine, {
            gesture: "adjust",
            target,
            committed_number,
          });
          return result.accepted ?? false;
        }}
      />
    ),
    adjust_editor_root,
  );

  // Optional shell mount. ?shell=off keeps the runtime running but
  // leaves the shell DOM empty for independence testing.
  const shell_off = read_query_param("shell") === "off";
  // Hold the shell binding's unsubscribe handle at function scope so the
  // pagehide teardown can release it. Null when the shell is not mounted.
  let shell_unsubscribe: UnsubscribeFn | null = null;
  if (!shell_off) {
    const shell_binding = subscribeEmitterToSnapshot(emitter);
    const snapshot_signal = shell_binding.snapshot;
    shell_unsubscribe = shell_binding.unsubscribe;
    // Pass the flattened config's flow data to ProtocolHud. The outline follows
    // entry_step and next_step links rather than YAML array order.
    const protocol_steps = active_config.steps ?? [];
    render(
      () => (
        <ProtocolHud
          snapshot={snapshot_signal}
          steps={protocol_steps}
          entry_step={active_config.entry_step}
          display_title={display_title}
          session_status={session_status}
          action_hint_open={action_hint_open}
          on_action_hint_toggle={set_action_hint_open}
          on_start_over={start_over}
        />
      ),
      shell_root,
    );
  }

  // Walker hook. Off by default; only consumed by the protocol walkthrough.
  const walker_expose = read_query_param("walker") === "expose";
  if (walker_expose) {
    window.__shellEmitter = emitter;
  }

  // Host teardown: dispose the active Solid root and the walker/debug surface
  // on page hide so no orphan effects/listeners/globals survive navigation away
  // (plan "Lifecycle cleanup + ownership"). pagehide fires on both unload and
  // bfcache eviction; once is enough.
  window.addEventListener(
    "pagehide",
    () => {
      flush_queued_session_save();
      if (active_dispose !== null) {
        active_dispose();
        active_dispose = null;
      }
      dispose_type_input();
      dispose_adjust_editor();
      dispose_walker_surface();
      if (timed_wait_timeout !== null) {
        window.clearTimeout(timed_wait_timeout);
        timed_wait_timeout = null;
      }
      // Release the emitter snapshot subscriptions so listeners do not
      // accumulate across navigations. These bindings mount outside a Solid
      // owner, so onCleanup does not apply; pagehide is the release path.
      affordance_binding.unsubscribe();
      type_binding.unsubscribe();
      adjust_binding.unsubscribe();
      if (shell_unsubscribe !== null) {
        shell_unsubscribe();
      }
      unsubscribe_persistence();
    },
    { once: true },
  );

  // Kick the machine. Emits protocol_loaded + step_started.
  step_machine.start();
}

//============================================
// Entry
//============================================

mount();
