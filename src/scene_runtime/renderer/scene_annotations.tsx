// Scene-level projection of resolved state text. State facts remain derived by
// SceneItem's visual-state resolver; this component only presents that existing
// runtime projection outside the measured 16:9 scene stage.

import type { JSXElement } from "solid-js";
import { For, Show } from "solid-js";
import { compute_affordance_kind, type AffordanceGesture } from "../protocol/affordance.js";

export interface SceneAnnotation {
  placement_name: string;
  object_label: string;
  field_name: string;
  /** Stable zero-based position among resolved facts for this placement/field. */
  occurrence: number;
  text: string;
}

export function annotation_id(
  annotation: Pick<SceneAnnotation, "placement_name" | "field_name" | "occurrence">,
): string {
  return [
    "scene-annotation",
    annotation.placement_name,
    annotation.field_name,
    annotation.occurrence,
  ].join("-");
}

/**
 * Give the resolver's ordered facts stable DOM identities. `compose(...)` may
 * legitimately emit multiple labels for one state field, so field name alone
 * is not a unique presentation key.
 */
export function build_scene_annotations(
  placement_name: string,
  object_label: string,
  overlays: readonly Pick<SceneAnnotation, "field_name" | "text">[],
): readonly SceneAnnotation[] {
  const occurrences = new Map<string, number>();
  return overlays.map((overlay) => {
    const occurrence = occurrences.get(overlay.field_name) ?? 0;
    occurrences.set(overlay.field_name, occurrence + 1);
    return {
      placement_name,
      object_label,
      field_name: overlay.field_name,
      occurrence,
      text: overlay.text,
    };
  });
}

export function SceneAnnotationRail(props: {
  annotations: readonly SceneAnnotation[];
  active_target: string | null;
  active_gesture: AffordanceGesture;
  candidate_targets: ReadonlySet<string>;
}): JSXElement {
  return (
    <Show when={props.annotations.length > 0}>
      <section
        class="scene-annotation-rail"
        data-scene-annotations=""
        aria-label="Scene observations"
      >
        <h2 class="scene-annotation-rail__heading">Scene observations</h2>
        <ul class="scene-annotation-rail__list">
          <For each={props.annotations}>
            {(annotation) => {
              // Exact dotted subpart actions belong to their parent placement's
              // observation facts. This is annotation context only; hit geometry
              // remains wholly owned by the declaration-backed subpart surface.
              const annotation_target = props.active_target?.split(".")[0] ?? null;
              const affordance = compute_affordance_kind({
                active_target: annotation_target,
                active_gesture: props.active_gesture,
                item_target: annotation.placement_name,
                candidate_targets: props.candidate_targets,
              });
              return (
                <li
                  id={annotation_id(annotation)}
                  class="scene-annotation-rail__item"
                  data-annotation-for={annotation.placement_name}
                  data-annotation-field={annotation.field_name}
                  data-annotation-affordance={affordance}
                >
                  <span class="scene-annotation-rail__object">{annotation.object_label}:</span>{" "}
                  <span>{annotation.text}</span>
                </li>
              );
            }}
          </For>
        </ul>
      </section>
    </Show>
  );
}
