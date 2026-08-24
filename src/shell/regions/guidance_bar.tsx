// src/shell/regions/guidance_bar.tsx
import type { Accessor, JSXElement } from "solid-js";
import { Show } from "solid-js";
import type { Gesture, LastRejection, ShellViewSnapshot } from "../adapter/types";
import { AuthoredTip } from "./authored_tip.js";

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
        return "Compare the blue outlined lab items with the step goal, then choose the best match.";
      }
      if (expected_gesture === "adjust") {
        return `Use the control below to set the requested value for ${highlighted}.`;
      }
      if (expected_gesture === "type") {
        return `Enter the requested value for ${highlighted} in the field below.`;
      }
      if (expected_gesture === "drag") {
        return `Move ${highlighted} to the indicated destination.`;
      }
      if (expected_label !== null) {
        return `Select the highlighted item labeled ${highlighted}.`;
      }
      return "Select the highlighted item to continue.";
    case "wrong_value":
      if (rejection.gesture === "type") {
        return "Check the step goal, correct the entry, then commit it.";
      }
      if (rejection.gesture === "adjust") {
        return "Check the step goal, adjust the value, then commit it.";
      }
      return "Check the step goal, then make the highlighted action again.";
    case "out_of_order":
      return "Complete the highlighted action first, then return to this action.";
    case "no_active_step":
      return "Wait for the next lab action to appear.";
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
  action_hint_open: Accessor<boolean>;
  on_action_hint_toggle(open: boolean): void;
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
              data-action-target={
                props.snapshot().active_interaction?.action?.gesture === "select"
                  ? undefined
                  : (props.snapshot().active_interaction?.action?.placement_name ?? undefined)
              }
              data-action-label={
                props.snapshot().active_interaction?.action?.gesture === "select"
                  ? undefined
                  : (props.snapshot().active_interaction?.action?.label ?? undefined)
              }
              data-action-gesture={
                props.snapshot().active_interaction?.action?.gesture ?? undefined
              }
              data-action-value={
                props.snapshot().active_interaction?.action?.requested_adjustment_value ?? undefined
              }
            >
              <p class="protocol-kicker">Do this next</p>
              <div
                class="action-rail__instruction"
                data-current-action-instruction=""
                role="status"
                aria-live="polite"
                aria-atomic="true"
              >
                <Show
                  when={action_progress_copy(
                    props.snapshot().active_interaction?.index ?? -1,
                    props.snapshot().active_interaction?.count ?? 0,
                  )}
                >
                  {(progress_copy) => (
                    <p class="action-rail-progress" data-current-action-progress="">
                      {progress_copy()}
                    </p>
                  )}
                </Show>
                <Show
                  when={
                    props.snapshot().active_interaction?.action?.gesture === "select"
                      ? null
                      : (props.snapshot().active_interaction?.action ?? null)
                  }
                >
                  {(action) => (
                    <p class="action-rail__target" data-current-action-target-label="">
                      <span>Target:</span> {action().label}
                    </p>
                  )}
                </Show>
                {/* ASVS 2.3.1: guidance reflects runtime-owned sequential
                    progression and cannot advance it; JSX text stays escaped
                    with no innerHTML. */}
                <p id="guidance-text" class="action-rail__primary">
                  {props.snapshot().active_interaction?.action?.instruction ??
                    "Preparing your next lab action..."}
                </p>
              </div>
              <p class="action-rail__goal" data-current-step-goal="">
                <span class="action-rail__goal-label">Step goal:</span>{" "}
                {props.snapshot().current_prompt ?? "Preparing your lab scene..."}
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
                              props.snapshot().active_interaction?.action?.label ?? null,
                              props.snapshot().active_interaction?.action?.gesture ?? null,
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
              <details
                class="action-rail__hint"
                data-action-hint=""
                open={props.action_hint_open()}
                onToggle={(event) => props.on_action_hint_toggle(event.currentTarget.open)}
              >
                <summary>Need a hint?</summary>
                <p data-action-hint-text="">
                  {props.snapshot().active_interaction?.action?.hint ??
                    "The next action will appear when the current lab process is ready."}
                </p>
              </details>
              <AuthoredTip snapshot={props.snapshot} />
            </div>
          }
        >
          {(wait) => (
            <div
              class="action-rail action-rail--waiting"
              data-timed-wait-status=""
              role="status"
              aria-atomic="true"
            >
              <p class="protocol-kicker">Lab process running</p>
              <strong id="guidance-text" class="action-rail__wait-primary">
                Waiting: {wait().display ?? "Timed lab process"}
              </strong>
              <p class="action-rail__wait-copy">
                The next highlighted action will appear automatically when this finishes.
              </p>
              <p class="action-rail__wait-duration" data-timed-wait-duration="">
                Simulated lab duration: {String(wait().duration_min)} minutes. This virtual lab
                compresses the wait rather than showing a real-time countdown.
              </p>
            </div>
          )}
        </Show>
      </Show>
    </section>
  );
}
