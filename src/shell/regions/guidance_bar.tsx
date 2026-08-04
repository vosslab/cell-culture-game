// src/shell/regions/guidance_bar.tsx
import type { Accessor, JSXElement } from "solid-js";
import { Show } from "solid-js";
import type { Gesture, LastRejection, ShellViewSnapshot } from "../adapter/types";
import { AuthoredTip } from "./authored_tip.js";

// Pair the gesture with the generated object label so the learner can connect
// the action rail to the highlighted scene object without decoding a placement
// identifier. Select deliberately omits the correct target label: every blue
// candidate must remain an equal visual choice.
export function gesture_instruction(
  gesture: Gesture | null,
  target_label: string | null,
  requested_value: string | number | boolean | null = null,
): string {
  const label = target_label ?? "the highlighted lab item";
  switch (gesture) {
    case "adjust":
      if (requested_value !== null) {
        return `Set ${label} to ${String(requested_value)} using the control below.`;
      }
      return `Set the requested value for ${label} using the control below.`;
    case "type":
      return `Enter the requested value for ${label} in the field below.`;
    case "select":
      return "Choose from the blue outlined lab items.";
    case "drag":
      return `Move ${label} to the indicated destination.`;
    case "click":
      return `Click ${label}.`;
    default:
      return "Follow the highlighted next action in the scene.";
  }
}

// Keep action-level progress separate from the guided-step counter: an ordered
// sequence can have several concrete learner actions while still representing
// one pedagogical step. Null prevents a stale ordinal from rendering during
// protocol startup, completion, and a step transition.
export function action_progress_copy(
  interaction_index: number,
  interaction_count: number,
): string | null {
  if (interaction_count <= 0 || interaction_index < 0 || interaction_index >= interaction_count) {
    return null;
  }
  return `Action ${String(interaction_index + 1)} of ${String(interaction_count)}`;
}

export function recovery_copy(
  rejection: LastRejection,
  expected_label: string | null = null,
  expected_gesture: Gesture | null = null,
): string {
  const highlighted = expected_label === null ? "the highlighted item" : expected_label;
  switch (rejection.reason_code) {
    case "wrong_target":
      if (expected_gesture === "select") {
        return "That option is not correct. Compare the blue outlined lab items and try again.";
      }
      if (expected_gesture === "adjust") {
        return `That item is not needed yet. Set the requested value for ${highlighted} using the control below.`;
      }
      if (expected_gesture === "type") {
        return `That item is not needed yet. Enter the requested value for ${highlighted} in the field below.`;
      }
      if (expected_gesture === "drag") {
        return `That item is not needed yet. Move ${highlighted} to the indicated destination.`;
      }
      if (expected_label !== null) {
        return `That item is not needed yet. Return to ${highlighted}, the highlighted item, and try again.`;
      }
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

export interface SelectionRecoveryDetails {
  readonly selected: string;
  readonly correct: string;
  readonly why: string;
}

// A rejected scientific choice is the teaching moment. The runtime projects
// labels only after rejection, so this panel can repeat the learner's choice
// and identify the evidence-matching answer without spoiling the decision.
export function selection_recovery_details(
  rejection: LastRejection,
  authored_reason: string | null,
): SelectionRecoveryDetails | null {
  if (
    rejection.reason_code !== "wrong_target" ||
    rejection.selected_label === null ||
    rejection.expected_label === null
  ) {
    return null;
  }
  const why =
    authored_reason ??
    "Compare the visible experimental evidence with the available choices before trying again.";
  return {
    selected: rejection.selected_label,
    correct: rejection.expected_label,
    why,
  };
}

export interface GuidanceBarProps {
  snapshot: Accessor<ShellViewSnapshot>;
}

function authored_incorrect_feedback(snapshot: ShellViewSnapshot): string | null {
  const feedback = snapshot.last_interaction_feedback;
  return feedback?.kind === "incorrect" ? feedback.message : null;
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
              <Show when={props.snapshot().last_interaction_feedback?.kind === "correct"}>
                <p
                  class="action-rail-feedback--correct"
                  data-interaction-feedback="correct"
                  role="status"
                >
                  {props.snapshot().last_interaction_feedback?.message ?? ""}
                </p>
              </Show>
            </div>
            <a class="protocol-return-link" href="./index.html">
              Return to lab experiences
            </a>
          </div>
        }
      >
        <Show
          when={props.snapshot().pending_timed_wait}
          fallback={
            <div
              class="action-rail"
              data-current-action=""
              data-action-target={props.snapshot().active_interaction_target ?? undefined}
              data-action-label={props.snapshot().active_interaction_label ?? undefined}
              data-action-gesture={props.snapshot().active_interaction_gesture ?? undefined}
              data-action-value={props.snapshot().active_interaction_value ?? undefined}
            >
              <p class="protocol-kicker">Do this next</p>
              <Show
                when={action_progress_copy(
                  props.snapshot().current_interaction_index,
                  props.snapshot().current_interaction_count,
                )}
              >
                {(progress_copy) => (
                  <p class="action-rail-progress" data-current-action-progress="">
                    {progress_copy()}
                  </p>
                )}
              </Show>
              <strong id="guidance-text" class="action-rail-prompt">
                {props.snapshot().current_prompt ?? "Preparing your lab scene..."}
              </strong>
              <p class="action-rail-cue">
                {gesture_instruction(
                  props.snapshot().active_interaction_gesture,
                  props.snapshot().active_interaction_label,
                  props.snapshot().active_interaction_value,
                )}
              </p>
              <Show when={props.snapshot().last_outcome?.resolution === "complete"}>
                <p class="action-rail-acknowledgement" data-action-acknowledgement="">
                  [OK] Previous step complete. Continue when ready.
                </p>
              </Show>
              <Show when={props.snapshot().last_interaction_feedback?.kind === "correct"}>
                <p
                  class="action-rail-feedback action-rail-feedback--correct"
                  data-interaction-feedback="correct"
                  role="status"
                >
                  {props.snapshot().last_interaction_feedback?.message ?? ""}
                </p>
              </Show>
              <Show when={props.snapshot().last_rejection}>
                {(rejection) => {
                  const authored_reason = authored_incorrect_feedback(props.snapshot());
                  return (
                    <Show
                      when={selection_recovery_details(rejection(), authored_reason)}
                      fallback={
                        <p class="action-rail-recovery" data-action-recovery="" role="status">
                          {authored_reason ??
                            recovery_copy(
                              rejection(),
                              props.snapshot().active_interaction_label,
                              props.snapshot().active_interaction_gesture,
                            )}
                        </p>
                      }
                    >
                      {(details) => (
                        <div class="action-rail-recovery" data-action-recovery="" role="status">
                          <p>
                            <strong>You chose:</strong> {details().selected}
                          </p>
                          <p>
                            <strong>Correct:</strong> {details().correct}
                          </p>
                          <p>
                            <strong>Why:</strong> {details().why}
                          </p>
                        </div>
                      )}
                    </Show>
                  );
                }}
              </Show>
              <AuthoredTip snapshot={props.snapshot} />
            </div>
          }
        >
          {(wait) => (
            <div class="action-rail action-rail--waiting" data-timed-wait-status="" role="status">
              <p class="protocol-kicker">Lab process running</p>
              <strong id="guidance-text" class="action-rail-prompt">
                Waiting: {wait().display ?? "Timed lab process"}
              </strong>
              <p class="action-rail-cue">
                The next highlighted action will appear automatically when this finishes.
              </p>
            </div>
          )}
        </Show>
      </Show>
    </section>
  );
}
