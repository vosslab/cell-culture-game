# Interface vocabulary

The interface is the locked, repo-wide surface that surrounds the
scene: HUD panel, modal panel, tray panel, feedback toast, help
overlay, and launcher. There is exactly one interface for the whole
repo. A protocol changes the scene, the objects, the materials, and
the steps; it does not invent a new interface. New interface panels
require editing this doc and shipping new component code, never a
protocol YAML change.

The scene is a panel inside the interface, with its own selector
contract in [SCENE_VOCABULARY.md](SCENE_VOCABULARY.md). This doc
covers every panel except the scene panel.

The relationship between interface controls, scene affordances, physical
browser input, and authored gestures is summarized in
`docs/specs/GESTURE_MODEL.md`.

This is a closed test-selector contract. Components emit only the
`data-*` attributes listed below; tests rely on these selectors.
Adding a new attribute requires editing this file.

Scope: interface DOM only. Scene-side selectors (`data-item-id`,
`data-object-name`, `data-placement-name`, `data-zone`, `data-kind`,
`data-depth`, `data-label`, `data-label-for`) are
owned by the imperative SVG renderer and documented under
[SCENE_VOCABULARY.md](SCENE_VOCABULARY.md).

## Reserved namespaces

- `data-hud-*` -- HUD presentation surface
  ([seam_interface.md](../archive/web_ui/seam_interface.md)).
- `data-modal-*` -- modal dialog surface.
- `data-tray-*` -- inventory tray.
- `data-help-*` -- help / professor overlay.
- `data-feedback-*` -- feedback toast.
- `data-interaction-feedback` -- persistent guidance-bar feedback for the
  most recent accepted or rejected interaction.
- `data-protocol-id` -- launcher link target.
- `data-launcher-*` -- launcher chrome.
- `data-type-*` -- type-gesture text-input affordance.
- `data-adjust-*` -- adjust-gesture numeric set-point affordance.

## Currently emitted attributes

| Attribute | Emitted by | Value |
| --- | --- | --- |
| `data-hud-step` | `src/shell/hud/protocol_hud.tsx` | current step name or empty string |
| `data-hud-prompt` | `src/shell/hud/protocol_hud.tsx` | current step prompt or empty string |
| `data-hud-progress` | `src/shell/hud/protocol_hud.tsx` | `<completed>/<total>` |
| `data-protocol-id` | `src/launcher/protocol_launcher.tsx` | protocol_name from PROTOCOLS_INDEX |
| `data-launcher-root` | `src/launcher/protocol_launcher.tsx` | empty, marker |
| `data-launcher-title` | `src/launcher/protocol_launcher.tsx` | empty, marker |
| `data-launcher-entry` | `src/launcher/protocol_launcher.tsx` | per-protocol link wrapper |
| `data-launcher-cluster` | `src/launcher/protocol_launcher.tsx` | cluster name |
| `data-launcher-name` | `src/launcher/protocol_launcher.tsx` | protocol_name label slot |
| `data-launcher-hook` | `src/launcher/protocol_launcher.tsx` | learning_hook text |
| `data-launcher-empty` | `src/launcher/protocol_launcher.tsx` | empty-state marker |
| `data-bg-asset-pending` | `src/scene_runtime/renderer/render_background.ts` | asset name pending registry wiring (scene-side, listed for cross-reference) |
| `data-type-input-panel` | `src/shell/hud/type_input.tsx` | empty, marker for the in-flow type-input panel (shown only while the active interaction's gesture is `type`) |
| `data-type-input-label` | `src/shell/hud/type_input.tsx` | empty, marker for the input label |
| `data-type-input` | `src/shell/hud/type_input.tsx` | empty, marker on the text input the student types into |
| `data-type-target` | `src/shell/hud/type_input.tsx` | the active `type` interaction's target name, or empty |
| `data-type-commit` | `src/shell/hud/type_input.tsx` | empty, marker on the Commit button |
| `data-type-reject-message` | `src/shell/hud/type_input.tsx` | empty, marker on the visible rejection message |
| `data-adjust-panel` | `src/shell/hud/set_point_editor.tsx` | empty, marker for the in-flow numeric set-point panel (shown only while the active interaction's gesture is `adjust`) |
| `data-adjust-label` | `src/shell/hud/set_point_editor.tsx` | empty, marker for the set-point input label |
| `data-adjust-decrement` | `src/shell/hud/set_point_editor.tsx` | empty, marker on the decrement button |
| `data-adjust-input` | `src/shell/hud/set_point_editor.tsx` | empty, marker on the numeric input |
| `data-adjust-target` | `src/shell/hud/set_point_editor.tsx` | the active `adjust` interaction's target name, or empty |
| `data-adjust-increment` | `src/shell/hud/set_point_editor.tsx` | empty, marker on the increment button |
| `data-adjust-commit` | `src/shell/hud/set_point_editor.tsx` | empty, marker on the Commit button |
| `data-adjust-reject-message` | `src/shell/hud/set_point_editor.tsx` | empty, marker on the visible rejection message |
| `data-interaction-feedback` | `src/shell/regions/guidance_bar.tsx` | `correct` or `incorrect`, identifying authored feedback projected in the guidance bar |

## Feedback state

When an interaction supplies `response.feedback.correct` or
`response.feedback.incorrect`, the runtime projects that learner-facing text
into the guidance bar. The emitted `data-interaction-feedback` value is
`correct` for accepted feedback and `incorrect` for rejected feedback. Correct
feedback remains visible through the next prompt and completion; incorrect
feedback replaces generic recovery copy for the rejected interaction. After a
rejected `select`, the same recovery surface shows the learner's selected label,
the expected label, and the authored incorrect feedback as the scientific
rationale. These labels are projected only after rejection, so the interface
does not reveal the correct choice in advance.

## Modal / tray / help

The modal, tray, and help surfaces are not yet authored as shell components.
Attributes are reserved (above). The first component patch in each namespace
must update this file with the exact attribute names and values.

## Plan amendment policy

Any new selector added to the shell requires:

1. A row in the table above.
2. A short note in
   [seam_interface.md](../archive/web_ui/seam_interface.md)
   if the selector reflects a new state surface (modal / help / tray /
   feedback transitions).
3. The component patch and this doc update land together.

Scene-side selectors are out of scope here; edit
[SCENE_VOCABULARY.md](SCENE_VOCABULARY.md) for those.
