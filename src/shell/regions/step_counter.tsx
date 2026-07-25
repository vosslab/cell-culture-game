// src/shell/regions/step_counter.tsx
import type { Accessor, JSXElement } from "solid-js";
import type { ShellViewSnapshot } from "../adapter/types";

export interface StepCounterProps {
  snapshot: Accessor<ShellViewSnapshot>;
}

export function StepCounter(props: StepCounterProps): JSXElement {
  return (
    <div class="protocol-status-summary" data-region="step-counter">
      <span class="protocol-status-summary-label">Guided progress</span>
      <strong id="step-counter-text" data-step-counter-text="">
        {props.snapshot().progress.completed_step_count} /{" "}
        {props.snapshot().progress.total_step_count}
      </strong>
    </div>
  );
}
