// Canonical learner-facing projection for the active protocol interaction.
//
// This module intentionally has no Solid, DOM, scene-store, or emitter
// dependency. The step-machine supplies the authoritative interaction and the
// current scene adapter's two identity resolvers; every shell consumer then
// reads the resulting atomic view from ShellViewSnapshot.

import type {
  ActiveInteractionAction,
  ActiveInteractionView,
  Interaction,
} from "../../shell/adapter/types";

export interface ActiveInteractionResolvers {
  readonly to_placement: (target: string) => string;
  readonly to_label: (target: string) => string;
}

function requested_adjustment_value(interaction: Interaction): string | number | boolean | null {
  if (interaction.gesture !== "adjust" || interaction.validator.preset !== "target_with_value") {
    return null;
  }
  const values = Object.values(interaction.validator.value ?? {});
  return values.length === 1 ? (values[0] ?? null) : null;
}

// Resolve all learner-facing action details together from one authored
// interaction. This projection intentionally has no generic copy fallback:
// content validation guarantees an instruction and hint for every action.
export function resolve_active_interaction_action(
  interaction: Interaction,
  resolvers: ActiveInteractionResolvers,
): ActiveInteractionAction {
  const label = resolvers.to_label(interaction.target);
  const value = requested_adjustment_value(interaction);
  return {
    placement_name: resolvers.to_placement(interaction.target),
    label,
    gesture: interaction.gesture,
    requested_adjustment_value: value,
    instruction: interaction.instruction,
    hint: interaction.hint,
  };
}

export function actionable_active_interaction_view(
  index: number,
  count: number,
  interaction: Interaction,
  resolvers: ActiveInteractionResolvers,
): ActiveInteractionView {
  return {
    index,
    count,
    availability: "actionable",
    action: resolve_active_interaction_action(interaction, resolvers),
  };
}

export function unavailable_active_interaction_view(
  index: number,
  count: number,
  availability: "transition" | "timed_wait",
): ActiveInteractionView {
  return { index, count, availability, action: null };
}
