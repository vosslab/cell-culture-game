// src/shell/regions/guidance_bar.tsx
import type { Accessor, JSXElement } from "solid-js";
import { Show } from "solid-js";
import type { Gesture, LastRejection, ShellViewSnapshot } from "../adapter/types";
import { AuthoredTip } from "./authored_tip.js";

// The authored prompt names the scientific item and action. The runtime target
// is a placement or subpart identifier for scene routing, not learner-facing
// language, so this cue intentionally never renders it.
export function gesture_instruction(gesture: Gesture | null): string {
  switch (gesture) {
    case "adjust":
      return "Set the requested value in the highlighted control below.";
    case "type":
      return "Enter your observation in the highlighted field below.";
    case "select":
      return "Choose the highlighted item or option.";
    case "drag":
      return "Move the highlighted lab item to the indicated destination.";
    case "click":
      return "Click the highlighted lab item.";
    default:
      return "Follow the highlighted next action in the scene.";
  }
}

export function recovery_copy(rejection: LastRejection): string {
  switch (rejection.reason_code) {
    case "wrong_target":
      return "That item is not needed yet. Return to the highlighted item and try again.";
    case "wrong_value":
      if (rejection.gesture === "type") {
        return "That entry does not match this step. Check the prompt, correct the entry, and try again.";
      }
      if (rejection.gesture === "adjust") {
        return "That value does not match this step. Check the prompt, adjust the value, and try again.";
      }
      return "That value does not match this step. Check the prompt and try again.";
    case "out_of_order":
      return "That action is not available yet. Complete the highlighted action first.";
    case "no_active_step":
      return "This protocol is not accepting another action right now.";
  }
}

export interface GuidanceBarProps {
  snapshot: Accessor<ShellViewSnapshot>;
}

export function GuidanceBar(props: GuidanceBarProps): JSXElement {
  return (
    <section class="guidance-bar" data-region="guidance-bar">
      <Show
        when={!props.snapshot().is_complete}
        fallback={
          <div class="protocol-completion" data-protocol-complete="">
            <div>
              <p class="protocol-kicker">Protocol complete</p>
              <strong>
                You completed {props.snapshot().progress.completed_step_count} guided steps.
              </strong>
              <p>Choose another lab experience when you are ready.</p>
            </div>
            <a class="protocol-return-link" href="./index.html">
              Return to lab experiences
            </a>
          </div>
        }
      >
        <div class="action-rail" data-current-action="">
          <p class="protocol-kicker">Do this next</p>
          <strong id="guidance-text" class="action-rail-prompt">
            {props.snapshot().current_prompt ?? "Preparing your lab scene..."}
          </strong>
          <p class="action-rail-cue">
            {gesture_instruction(props.snapshot().active_interaction_gesture)}
          </p>
          <Show when={props.snapshot().last_outcome?.resolution === "complete"}>
            <p class="action-rail-acknowledgement" data-action-acknowledgement="">
              [OK] Previous step complete. Continue when ready.
            </p>
          </Show>
          <Show when={props.snapshot().last_rejection}>
            {(rejection) => (
              <p class="action-rail-recovery" data-action-recovery="" role="status">
                {recovery_copy(rejection())}
              </p>
            )}
          </Show>
          <AuthoredTip snapshot={props.snapshot} />
        </div>
      </Show>
    </section>
  );
}
