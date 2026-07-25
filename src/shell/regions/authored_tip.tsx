// src/shell/regions/authored_tip.tsx
import type { Accessor, JSXElement } from "solid-js";
import { Show } from "solid-js";
import type { ShellViewSnapshot } from "../adapter/types";

export interface AuthoredTipProps {
  snapshot: Accessor<ShellViewSnapshot>;
}

export function AuthoredTip(props: AuthoredTipProps): JSXElement {
  const has_tip = (): boolean => {
    const tip = props.snapshot().current_tip;
    return tip !== null && tip.trim().length > 0;
  };

  return (
    <Show when={has_tip()}>
      <p class="action-rail-tip" data-authored-tip="">
        Tip: {props.snapshot().current_tip}
      </p>
    </Show>
  );
}
