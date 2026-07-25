// src/shell/hud/protocol_hud.tsx
//
// The protocol shell is one Solid composition root. It projects the typed
// runtime snapshot into the student-facing regions; it never reads scene DOM
// or changes protocol state. The host places #shell-root in the page grid, and
// .protocol-shell uses display: contents so these three regions remain grid
// siblings of the scene panel without making the shell an ancestor of it.

import type { Accessor, JSXElement } from "solid-js";
import type { ProtocolStep, ShellViewSnapshot } from "../adapter/types";
import { GuidanceBar } from "../regions/guidance_bar.js";
import { StepCounter } from "../regions/step_counter.js";
import { StepOutline } from "../regions/step_outline.js";

export interface ProtocolHudProps {
  snapshot: Accessor<ShellViewSnapshot>;
  steps?: ReadonlyArray<ProtocolStep>;
  entry_step: string;
  display_title: string;
}

export function ProtocolHud(props: ProtocolHudProps): JSXElement {
  const steps = props.steps ?? [];

  return (
    <div class="protocol-shell">
      <header class="protocol-header" data-region="header">
        <div class="protocol-brand" aria-label="Virtual lab coach">
          <span class="protocol-brand-mark" aria-hidden="true">
            VL
          </span>
          <span>Virtual Lab Coach</span>
        </div>
        <p class="protocol-display-title" data-protocol-display-title="">
          {props.display_title}
        </p>
        <StepCounter snapshot={props.snapshot} />
        <div class="protocol-hud" aria-hidden="true">
          <span data-hud-step>{props.snapshot().current_step_name ?? ""}</span>
          <span data-hud-prompt>{props.snapshot().current_prompt ?? ""}</span>
          <span data-hud-progress>
            {props.snapshot().progress.completed_step_count}/
            {props.snapshot().progress.total_step_count}
          </span>
        </div>
      </header>

      <StepOutline steps={steps} entry_step={props.entry_step} snapshot={props.snapshot} />
      <GuidanceBar snapshot={props.snapshot} />
    </div>
  );
}
