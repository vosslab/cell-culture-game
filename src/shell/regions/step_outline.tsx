// src/shell/regions/step_outline.tsx
import type { Accessor, JSXElement } from "solid-js";
import { For } from "solid-js";
import type { ProtocolStep, ShellViewSnapshot } from "../adapter/types";

export interface StepOutlineProps {
  steps: ReadonlyArray<ProtocolStep>;
  entry_step: string;
  snapshot: Accessor<ShellViewSnapshot>;
}

type StepStatus = "complete" | "current" | "upcoming";

export function step_status(
  step_name: string,
  snapshot: ShellViewSnapshot,
  ordered_step_names: ReadonlyArray<string>,
): StepStatus {
  if (snapshot.is_complete) return "complete";
  const current_index = ordered_step_names.indexOf(snapshot.current_step_name ?? "");
  const step_index = ordered_step_names.indexOf(step_name);
  if (step_index !== -1 && current_index !== -1 && step_index < current_index) return "complete";
  if (step_name === snapshot.current_step_name) return "current";
  return "upcoming";
}

// Follow the authored protocol flow. The YAML steps array is intentionally a
// reading convenience, so its source order is not a learner-facing sequence.
// Generated protocols are validated before the host runs, but the shell still
// fails explicitly if malformed data reaches this boundary instead of showing
// a plausible, incorrect curriculum order.
export function order_steps_by_flow(
  steps: ReadonlyArray<ProtocolStep>,
  entry_step: string,
): ReadonlyArray<ProtocolStep> {
  const by_name = new Map<string, ProtocolStep>();
  for (const step of steps) {
    if (by_name.has(step.step_name)) {
      throw new Error(`Step outline cannot order duplicate step_name "${step.step_name}"`);
    }
    by_name.set(step.step_name, step);
  }

  const ordered_steps: ProtocolStep[] = [];
  const seen_names = new Set<string>();
  let current_name: string | null = entry_step;
  while (current_name !== null) {
    if (seen_names.has(current_name)) {
      throw new Error(`Step outline found cycle at step "${current_name}" in next_step chain`);
    }
    const current_step = by_name.get(current_name);
    if (current_step === undefined) {
      throw new Error(`Step outline cannot find step "${current_name}" in next_step chain`);
    }
    seen_names.add(current_name);
    ordered_steps.push(current_step);
    current_name = current_step.next_step;
  }

  if (ordered_steps.length !== steps.length) {
    const unreachable_names = steps
      .filter((step) => !seen_names.has(step.step_name))
      .map((step) => step.step_name)
      .join(", ");
    throw new Error(`Step outline found unreachable steps: ${unreachable_names}`);
  }

  return ordered_steps;
}

function step_marker(status: StepStatus): string {
  if (status === "complete") return "[OK]";
  if (status === "current") return "->";
  return "\u25CB";
}

export function StepOutline(props: StepOutlineProps): JSXElement {
  const ordered_steps = order_steps_by_flow(props.steps, props.entry_step);
  const ordered_names = ordered_steps.map((step) => step.step_name);
  return (
    <aside class="outline-panel" data-region="outline" aria-label="Protocol progress">
      <div class="outline-heading">Your protocol</div>
      <div class="outline-progress-copy">
        {props.snapshot().is_complete
          ? "All steps complete"
          : `${props.snapshot().progress.completed_step_count} of ${props.snapshot().progress.total_step_count} steps complete`}
      </div>
      <div class="outline-steps">
        <For each={ordered_steps}>
          {(step) => {
            const status = (): StepStatus =>
              step_status(step.step_name, props.snapshot(), ordered_names);
            return (
              <div
                class="outline-step-card"
                data-step-name={step.step_name}
                data-step-status={status()}
                aria-current={status() === "current" ? "step" : undefined}
                title={step.prompt}
              >
                <span class="outline-step-state" aria-hidden="true">
                  {step_marker(status())}
                </span>
                <span class="outline-step-label">{step.prompt}</span>
              </div>
            );
          }}
        </For>
      </div>
    </aside>
  );
}
