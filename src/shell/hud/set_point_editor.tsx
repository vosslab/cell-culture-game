// src/shell/hud/set_point_editor.tsx
//
// Visible shared numeric set-point editor for the `adjust` gesture.
//
// `adjust` is one of the closed gesture set (PROTOCOL_VOCABULARY.md). An
// `adjust` interaction asks the student to set a numeric set-point (a pipette
// set_volume, a power-supply set_voltage, a hotplate set_temperature, a timed
// duration, a titration pH) on a target object. ONE editor instance serves
// every set-point field: the field being set is named by the active interaction,
// not by the widget (affordance_contract.md M10 default: "One shared numeric
// set-point editor for every adjust field"). It renders a stepper (decrement /
// increment buttons) plus a direct numeric input, appears only while the active
// interaction's gesture is `adjust`, and hides otherwise.
//
// The student reaches a value by stepper clicks or direct entry and commits via
// the Commit button or the Enter key; the committed number is handed to the
// runtime through on_commit, which routes to step_machine.handle_adjust_commit.
// The runtime validates it with the interaction's target_with_value preset,
// coercing the number to the field's declared type before comparing.
//
// Integrity (PRIMARY_SPEC.md walker rule):
//   - This is a REAL visible control with stable data-* selectors
//     (data-adjust-input on the input, data-adjust-commit on the button, the
//     data-adjust-* family mirroring data-type-*). The walker fills + commits
//     through Playwright actionability-checked interactions; it never writes
//     runtime state directly.
//   - on_commit is the ONLY path to advance; it calls the step machine's public
//     handle_adjust_commit, not any internal state write.
//   - The component reads a read-only snapshot accessor; it never mutates it.
//
// Host independence: like TypeInput, this mounts into a permanent in-flow host
// outside the optional shell. It stays available under ?shell=off without
// covering the scene, guidance, or outline regions.
//
// Layer boundary: this is a shell/interface control (Solid is allowed under
// src/shell/). It carries no protocol-flow logic; it only surfaces the active
// `adjust` interaction and forwards the committed number.

import type { Accessor, JSXElement } from "solid-js";
import { Show, createSignal, createEffect } from "solid-js";

import type { ShellViewSnapshot } from "../adapter/types";

//============================================
// Component props
//============================================

export interface SetPointEditorProps {
  // Live read-only protocol snapshot. The editor shows only when
  // active_interaction_gesture === "adjust".
  snapshot: Accessor<ShellViewSnapshot>;
  // Commit handler. Receives the active target and the committed numeric
  // set-point. Wired by protocol_host.tsx to step_machine.handle_adjust_commit.
  // Returns true when the commit was accepted, false when rejected.
  on_commit: (target: string, committed_number: number) => boolean;
}

//============================================
// Stepper step size
//============================================

// Fixed stepper increment for the +/- buttons. A hardcoded internal detail
// (argparse-minimalism / hardcode-what-users-do-not-tune): the stepper is the
// coarse human affordance, and direct numeric entry covers exact values, so the
// step size never needs to be configurable per field.
const STEP_SIZE = 1;

export function parse_set_point_draft(text: string): number | null {
  const trimmed = text.trim();
  if (trimmed.length === 0) {
    return null;
  }
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

//============================================
// Component implementation
//============================================

export function SetPointEditor(props: SetPointEditorProps): JSXElement {
  // Local draft text. Reset whenever the active interaction target changes so a
  // new `adjust` interaction starts with an empty field.
  const [draft, set_draft] = createSignal("");

  // Visible rejection feedback flag. Set to true on a rejected commit; cleared
  // on the next accepted commit or when the active interaction target changes.
  const [rejected, set_rejected] = createSignal(false);

  // Whether the active interaction is an `adjust` gesture.
  const is_adjust_active = (): boolean => props.snapshot().active_interaction_gesture === "adjust";

  // The active target for the current adjust interaction (null when not adjusting).
  const active_target = (): string | null => props.snapshot().active_interaction_target;

  // Reset the draft and clear any rejection feedback when the active target
  // changes (new interaction or step started).
  let last_target: string | null = null;
  createEffect(() => {
    const target = active_target();
    if (target !== last_target) {
      last_target = target;
      set_draft("");
      set_rejected(false);
    }
  });

  function draft_number(): number | null {
    return parse_set_point_draft(draft());
  }

  // Nudge the draft by the stepper step size (direction is +1 or -1).
  function step(direction: number): void {
    const next = (draft_number() ?? 0) + direction * STEP_SIZE;
    set_draft(String(next));
  }

  // Commit the current draft value for the active target. Updates the rejection
  // feedback signal based on whether the runtime accepted the committed value.
  function commit(): void {
    const target = active_target();
    if (target === null) {
      return;
    }
    const value = draft_number();
    if (value === null) {
      set_rejected(true);
      return;
    }
    const accepted = props.on_commit(target, value);
    // Show visible feedback when the commit is rejected by the validator.
    set_rejected(!accepted);
  }

  // Commit on Enter for keyboard reachability.
  function on_keydown(event: KeyboardEvent): void {
    if (event.key === "Enter") {
      event.preventDefault();
      commit();
    }
  }

  return (
    <Show when={is_adjust_active()}>
      <div data-adjust-panel="" class="value-entry-panel">
        <label data-adjust-label="" for="protocol-adjust-input" class="value-entry-label">
          Set value for {props.snapshot().active_interaction_label ?? "the highlighted item"}:
        </label>
        <button
          data-adjust-decrement=""
          type="button"
          onClick={() => step(-1)}
          class="value-entry-button value-entry-button--stepper"
          aria-label="Decrease set value"
        >
          -
        </button>
        <input
          id="protocol-adjust-input"
          data-adjust-input=""
          data-adjust-target={active_target() ?? ""}
          type="number"
          value={draft()}
          aria-invalid={rejected() ? "true" : undefined}
          aria-describedby={rejected() ? "protocol-adjust-reject-message" : undefined}
          onInput={(event) => {
            set_draft(event.currentTarget.value);
            set_rejected(false);
          }}
          onKeyDown={on_keydown}
          class="value-entry-input"
        />
        <button
          data-adjust-increment=""
          type="button"
          onClick={() => step(1)}
          class="value-entry-button value-entry-button--stepper"
          aria-label="Increase set value"
        >
          +
        </button>
        <button
          data-adjust-commit=""
          type="button"
          onClick={() => commit()}
          class="value-entry-button"
        >
          Commit
        </button>
        <Show when={rejected()}>
          <span
            id="protocol-adjust-reject-message"
            data-adjust-reject-message=""
            class="value-entry-feedback"
            role="status"
            aria-live="polite"
          >
            Set-point not accepted, try again
          </span>
        </Show>
      </div>
    </Show>
  );
}
