// src/shell/hud/type_input.tsx
//
// Visible text-input affordance for the `type` gesture.
//
// `type` is one of the closed gesture set (PROTOCOL_VOCABULARY.md). A `type`
// interaction asks the student to enter a value (e.g. a counted cell number)
// into a VISIBLE input and commit it. This component renders that input
// reactively: it appears only while the active interaction's gesture is `type`
// and hides otherwise. The student types into the input and commits via the
// Commit button or the Enter key; the committed raw text is handed to the
// runtime through on_commit, which routes to step_machine.handle_type_commit.
// The runtime validates it with the interaction's target_with_value preset.
//
// Integrity (PRIMARY_SPEC.md walker rule):
//   - This is a REAL visible control with a stable data-* selector
//     (data-type-input on the input, data-type-commit on the button). The
//     walker fills + commits through Playwright actionability-checked
//     interactions; it never writes runtime state directly.
//   - on_commit is the ONLY path to advance; it calls the step machine's
//     public handle_type_commit, not any internal state write.
//   - The component reads a read-only snapshot accessor; it never mutates it.
//
// Layer boundary: this is a shell/interface control (Solid is allowed under
// src/shell/). It carries no protocol-flow logic; it only surfaces the active
// `type` interaction and forwards the committed text.

import type { Accessor, JSXElement } from "solid-js";
import { Show, createSignal, createEffect } from "solid-js";

import type { ShellViewSnapshot } from "../adapter/types";

//============================================
// Component props
//============================================

export interface TypeInputProps {
  // Live read-only protocol snapshot. The input shows only when
  // active_interaction.action.gesture === "type".
  snapshot: Accessor<ShellViewSnapshot>;
  // Commit handler. Receives the active target and the raw typed text. Wired
  // by protocol_host.tsx to step_machine.handle_type_commit. Returns true when
  // the commit was accepted, false when it was rejected by the validator.
  on_commit: (target: string, typed_text: string) => boolean;
}

//============================================
// Component implementation
//============================================

export function TypeInput(props: TypeInputProps): JSXElement {
  // Local draft text. Reset whenever the active interaction target changes so a
  // new `type` interaction starts with an empty field.
  const [draft, set_draft] = createSignal("");

  // Visible rejection feedback flag. Set to true on a rejected commit; cleared
  // on the next accepted commit or when the active interaction target changes.
  const [rejected, set_rejected] = createSignal(false);

  // Whether the active interaction is a `type` gesture.
  const is_type_active = (): boolean =>
    props.snapshot().active_interaction?.action?.gesture === "type";

  // The active target for the current type interaction (null when not typing).
  const active_target = (): string | null =>
    props.snapshot().active_interaction?.action?.placement_name ?? null;

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

  // Commit the current draft text for the active target. Updates the rejection
  // feedback signal based on whether the runtime accepted the committed value.
  function commit(): void {
    const target = active_target();
    if (target === null) {
      return;
    }
    const accepted = props.on_commit(target, draft());
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
    <Show when={is_type_active()}>
      <div data-type-input-panel="" class="value-entry-panel">
        <label data-type-input-label="" for="protocol-type-input" class="value-entry-label">
          Enter value for{" "}
          {props.snapshot().active_interaction?.action?.label ?? "the highlighted item"}:
        </label>
        <input
          id="protocol-type-input"
          data-type-input=""
          data-type-target={active_target() ?? ""}
          type="text"
          value={draft()}
          aria-invalid={rejected() ? "true" : undefined}
          aria-describedby={rejected() ? "protocol-type-reject-message" : undefined}
          onInput={(event) => set_draft(event.currentTarget.value)}
          onKeyDown={on_keydown}
          class="value-entry-input"
        />
        <button
          data-type-commit=""
          type="button"
          onClick={() => commit()}
          class="value-entry-button"
        >
          Commit
        </button>
        <Show when={rejected()}>
          <span
            id="protocol-type-reject-message"
            data-type-reject-message=""
            class="value-entry-feedback"
            role="status"
            aria-live="polite"
          >
            Entry not accepted, try again
          </span>
        </Show>
      </div>
    </Show>
  );
}
