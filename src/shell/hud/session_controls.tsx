// Learner-facing session status and explicit start-over recovery.

import type { Accessor, JSXElement } from "solid-js";

import type { SessionSaveStatus } from "../../scene_runtime/protocol/session_persistence.js";

export interface SessionControlsProps {
  status: Accessor<SessionSaveStatus>;
  on_start_over(): void;
}

function status_copy(status: SessionSaveStatus): string {
  switch (status) {
    case "fresh":
      return "Autosave on";
    case "restored":
      return "Progress restored";
    case "saved":
      return "Progress saved";
    case "unavailable":
      return "Autosave unavailable";
  }
}

export function SessionControls(props: SessionControlsProps): JSXElement {
  let reset_dialog: HTMLDialogElement | undefined;

  function open_reset_dialog(): void {
    if (reset_dialog !== undefined && !reset_dialog.open) {
      reset_dialog.showModal();
    }
  }

  return (
    <div class="protocol-session-controls" data-session-controls="">
      <p
        class="protocol-session-status"
        data-session-status={props.status()}
        role="status"
        aria-live="polite"
      >
        {status_copy(props.status())}
      </p>
      <button class="protocol-start-over" type="button" onClick={open_reset_dialog}>
        Start over
      </button>

      <dialog
        class="protocol-reset-dialog"
        ref={(element) => {
          reset_dialog = element;
        }}
        aria-labelledby="protocol-reset-title"
        aria-describedby="protocol-reset-description"
      >
        <form method="dialog">
          <h2 id="protocol-reset-title">Start this protocol over?</h2>
          <p id="protocol-reset-description">
            This clears your saved progress for this protocol and returns to the first step.
          </p>
          <div class="protocol-reset-actions">
            <button class="protocol-reset-cancel" value="cancel">
              Keep my progress
            </button>
            <button
              class="protocol-reset-confirm"
              value="confirm"
              onClick={() => props.on_start_over()}
            >
              Clear progress and start over
            </button>
          </div>
        </form>
      </dialog>
    </div>
  );
}
