// src/scene_runtime/protocol/flatten_sequence_runner.ts
//
// Sequence-runner playback via flattening. A sequence_runner protocol lists an
// ordered set of constituent mini_protocols instead of authored steps
// (docs/PRIMARY_SPEC.md "Sequence runners"). The runtime plays a runner by
// expanding it, at mount time, into ONE flat mini_protocol-shaped ProtocolConfig
// whose steps are every constituent's steps in order:
//
//   - each constituent instance's step_names are namespaced (mp{i}__<name>) so
//     the same mini listed twice (sdspage lists three single-lane loads) keeps
//     distinct step ids;
//   - each constituent's terminal step (next_step === null) is rechained to the
//     NEXT constituent's entry step, so completing one mini advances into the
//     next; the last constituent's terminal step stays null so the whole runner
//     completes;
//   - each constituent's ENTRY step carries an explicit `scene` set to that
//     mini's resolved entry scene, so the step machine renders the correct scene
//     at the mini boundary before the student interacts (ProtocolStep.scene is
//     already the documented "initial/transition scene for this step").
//
// The whole runtime (step machine, snapshot reducer, walker debug surface, HUD)
// then runs the flattened config exactly as it runs any mini_protocol: one steps
// list, one next_step chain, one PROTOCOL_STEPS list the walker completes. There
// is NO branch on protocol_name and NO sequence-runner special case downstream;
// the only runner-aware code is this data-driven expansion keyed off
// protocol_type and the mini_protocols list.
//
// References:
//   - docs/PRIMARY_SPEC.md ("Sequence runners", "Entry-scene resolution precedence")
//   - src/scene_runtime/protocol/resolve_entry_scene.ts (per-mini scene resolution)
//   - src/scene_runtime/protocol/step_machine.ts (step-entry scene render)

import type { ProtocolConfig, ProtocolStep } from "../../shell/adapter/types.js";
import { resolve_entry_scene_name } from "./resolve_entry_scene.js";

//============================================
// Constituent expansion
//============================================

// Expand a runner into its direct mini-protocol constituents. Nested runners
// and repeated names are intentionally invalid: a runner is a single ordered
// package list, not a macro language. Keeping that shape closed makes runner
// state ownership and walkthrough accounting unambiguous.
function expand_to_step_configs(
  config: ProtocolConfig,
  protocols: Readonly<Record<string, ProtocolConfig>>,
): ProtocolConfig[] {
  if (config.protocol_type !== "sequence_runner") {
    return [config];
  }
  const mini_names = config.mini_protocols;
  if (!mini_names || mini_names.length === 0) {
    throw new Error(
      `flatten_sequence_runner: sequence_runner "${config.protocol_name}" has no mini_protocols list`,
    );
  }
  const out: ProtocolConfig[] = [];
  const seen = new Set<string>();
  for (const mini_name of mini_names) {
    if (seen.has(mini_name)) {
      throw new Error(
        `flatten_sequence_runner: sequence_runner "${config.protocol_name}" repeats constituent ` +
          `"${mini_name}"; each direct mini_protocol may appear once`,
      );
    }
    seen.add(mini_name);
    const mini_config = protocols[mini_name];
    if (!mini_config) {
      throw new Error(
        `flatten_sequence_runner: sequence_runner "${config.protocol_name}" constituent ` +
          `"${mini_name}" not found in PROTOCOLS`,
      );
    }
    if (mini_config.protocol_type !== "mini_protocol") {
      throw new Error(
        `flatten_sequence_runner: sequence_runner "${config.protocol_name}" constituent ` +
          `"${mini_name}" must be a mini_protocol, not ${mini_config.protocol_type}`,
      );
    }
    out.push(mini_config);
  }
  return out;
}

//============================================
// Step rewriting
//============================================

// Build the namespaced step id for a constituent instance.
function namespaced_step_name(instance_index: number, step_name: string): string {
  return `mp${instance_index}__${step_name}`;
}

// Clone one constituent step into its flattened form: namespaced id, rewired
// next_step, and (for the constituent's entry step) an explicit entry scene so
// the boundary transition renders it. Every other authored field passes through.
function rewrite_step(
  step: ProtocolStep,
  instance_index: number,
  entry_step_name: string,
  entry_scene: string,
  next_instance_entry: string | null,
): ProtocolStep {
  const is_entry = step.step_name === entry_step_name;
  // A terminal step (next_step === null) chains to the next constituent's entry
  // step, or stays terminal for the final constituent. A non-terminal step keeps
  // its own next_step, namespaced to this instance.
  let next_step: string | null;
  if (step.next_step === null) {
    next_step = next_instance_entry;
  } else {
    next_step = namespaced_step_name(instance_index, step.next_step);
  }
  // The entry step declares this constituent's resolved entry scene so the step
  // machine renders it on entry (the mini boundary). Non-entry steps keep any
  // scene they authored (none do in current content).
  const scene_for_step = is_entry ? entry_scene : step.scene;
  const rewritten: ProtocolStep = {
    step_name: namespaced_step_name(instance_index, step.step_name),
    prompt: step.prompt,
    sequence: step.sequence,
    step_validator: step.step_validator,
    outcome: step.outcome,
    next_step,
    ...(step.tip !== undefined ? { tip: step.tip } : {}),
    ...(scene_for_step !== undefined ? { scene: scene_for_step } : {}),
  };
  return rewritten;
}

//============================================
// Public API
//============================================

/**
 * Flatten a sequence_runner into a single mini_protocol-shaped ProtocolConfig.
 *
 * A non-runner config is returned unchanged, so callers can flatten every
 * protocol unconditionally. A runner is expanded into one flat steps list whose
 * next_step chain plays every constituent mini-protocol in order.
 *
 * @param config - The protocol to flatten (runner or not).
 * @param protocols - The full PROTOCOLS map, needed to look up constituents.
 * @returns The flattened config (or the original when not a runner).
 * @throws Error if a constituent is missing or a runner lists no mini_protocols.
 */
export function flatten_sequence_runner(
  config: ProtocolConfig,
  protocols: Readonly<Record<string, ProtocolConfig>>,
): ProtocolConfig {
  if (config.protocol_type !== "sequence_runner") {
    return config;
  }

  // Ordered constituent configs, each carrying its own steps.
  const constituents = expand_to_step_configs(config, protocols);
  if (constituents.length === 0) {
    throw new Error(
      `flatten_sequence_runner: sequence_runner "${config.protocol_name}" expanded to no constituents`,
    );
  }

  // Precompute each constituent's namespaced entry step so terminal steps of the
  // previous constituent can point at the next constituent's entry.
  const entry_names: string[] = constituents.map((mini, index) =>
    namespaced_step_name(index, mini.entry_step),
  );

  const flat_steps: ProtocolStep[] = [];
  for (let index = 0; index < constituents.length; index++) {
    const mini = constituents[index];
    if (mini === undefined) {
      // Unreachable (index is bounded by constituents.length); satisfies
      // noUncheckedIndexedAccess.
      continue;
    }
    const mini_steps = mini.steps ?? [];
    if (mini_steps.length === 0) {
      throw new Error(
        `flatten_sequence_runner: constituent "${mini.protocol_name}" of runner ` +
          `"${config.protocol_name}" has no steps`,
      );
    }
    // Resolve this constituent's concrete entry scene through the same precedence
    // a standalone mount uses (step scene field, then first SceneChange).
    const entry_scene = resolve_entry_scene_name(mini, protocols);
    // The next constituent's entry step, or null for the final constituent
    // (whose terminal step ends the whole runner).
    const next_instance_entry =
      index + 1 < entry_names.length ? (entry_names[index + 1] ?? null) : null;
    for (const step of mini_steps) {
      flat_steps.push(rewrite_step(step, index, mini.entry_step, entry_scene, next_instance_entry));
    }
  }

  const first_entry = entry_names[0];
  if (first_entry === undefined) {
    // Unreachable given constituents.length > 0.
    throw new Error(
      `flatten_sequence_runner: sequence_runner "${config.protocol_name}" resolved no entry step`,
    );
  }

  const flattened: ProtocolConfig = {
    protocol_name: config.protocol_name,
    // The flattened form is played exactly like a mini_protocol: one steps list,
    // one next_step chain. The original runner config in PROTOCOLS is untouched.
    protocol_type: "mini_protocol",
    entry_step: first_entry,
    steps: flat_steps,
    ...(config.learning !== undefined ? { learning: config.learning } : {}),
    // Root-only precedence: the runner's declared initial state starts the
    // single flattened session. Constituent mini initial_state values are not
    // merged, because they would otherwise re-seed state midway through a run.
    ...(config.initial_state !== undefined ? { initial_state: config.initial_state } : {}),
  };
  return flattened;
}
