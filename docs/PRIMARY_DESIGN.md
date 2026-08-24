# Primary design

This document explains the design philosophy for the virtual lab protocol simulation. The hard contract lives in `docs/PRIMARY_CONTRACT.md`. The technical specification lives in `docs/PRIMARY_SPEC.md`.

The core design goal is simple: a student should learn a lab protocol by seeing the correct objects, clicking the correct sequence, and watching the correct state changes happen on screen.

## Core idea

A mini-protocol is designed as a visible flow of interactions.

The protocol is not just a checklist. Each step should show the student:

1. what objects matter,
2. what object to click first,
3. what object receives the action,
4. what state changed,
5. what the next step is.

This is the flow-chart discipline: the author sketches the route through the protocol before implementing YAML or TypeScript.

## Flow before implementation

Before a mini-protocol is implemented, write a small flow sketch. The sketch may be a diagram or a table, but it must describe the click path and visible state changes.

The flow sketch is the design source for:

- the `learning:` block
- the protocol step chain
- visible scene objects
- click sequence
- expected state changes
- screenshot checkpoints
- transitions between steps

The YAML should then encode that flow using the two-level protocol model: a
`protocol` with an `entry_step` and `steps`, each `step` carrying an ordered
`sequence` of interactions and a `next_step` that names the next `step_name`.
Each `interaction` is one `gesture` on one `target`, with required non-empty
plain-string `instruction` and `hint` guidance, its own `validator`, and
`response`. The protocol vocabulary treats a step as one pedagogical unit
whose `sequence` is the ordered list of interactions that complete it, each
interaction naming the scene object it acts on and the scene operations its
`response` causes. When a generic gesture cue cannot distinguish repeated
`(target, gesture)` substeps, the interaction authors paired `instruction` and
`hint` fields as non-empty plain strings, so the visible next action is grounded
in protocol intent rather than a UI heuristic. When an exact `(target, gesture)`
pair repeats, those strings must remain distinct for each materially different
substep. See [specs/PROTOCOL_VOCABULARY.md](specs/PROTOCOL_VOCABULARY.md) for
the canonical model.

## Learning block

Each mini-protocol starts with a `learning:` block. This block defines the scope of the mini-protocol.

```yaml
learning:
  objectives: "Students completing this mini-protocol will have achieved..."
  outcomes: "Students completing this mini-protocol will be able to..."
  goals: "Overall, this mini-protocol aims to accomplish..."
```

## Protocol kinds

The authored kinds (`mini_protocol`, `sequence_runner`) and the surrounding structural terms (protocol package, `protocol_type`, `protocol.yaml`) are defined canonically in [PROTOCOL_VOCABULARY.md](specs/PROTOCOL_VOCABULARY.md#protocol-kinds). Large protocols are assembled from mini-protocols so each part can be authored, tested, and walked independently.

## Visible interaction standard

A mini-protocol is designed around what a student can see and do. The walkthrough must use the same visible UI path a student would use.

The walker may read generated protocol data to know the expected path, but it must not write game state, skip scenes, call internal APIs, or click hidden controls. If the walker cannot complete the mini-protocol through visible UI, the YAML, scene affordance, or runtime behavior is incomplete and must be fixed before the mini-protocol is considered complete.

### Guidance and durable progress

The current interaction is the learner's unit of orientation. Its ordinal,
target, instruction, goal, and hint must all describe the same next action.
`instruction` and `hint` are mandatory authored guidance; a runtime-generated
gesture fallback is not part of the protocol model. A professor-authored
step-level `tip`, when present, is optional contextual teaching guidance and
does not replace either interaction field.
After an accepted interaction, the runtime completes its response operations
and transition before publishing the next interaction. An open hint therefore
updates with the primary message instead of describing the action that just
finished.

Progress persistence follows that same settled boundary. The interface visibly
distinguishes a fresh autosaving session, a restored session, a saved checkpoint,
and unavailable storage. Reloading resumes at the exact next interaction with
the same declared scientific and cursor state. `Start over` is an explicit,
confirmed learner command scoped to the current protocol.

The runtime projects authored guidance with the active interaction. The shell
owns rendering that projection only; it does not infer, replace, or compose
action guidance.

Browser evidence is production-shaped: Playwright drives the built application
through visible controls, observes the real save record, reloads, resumes, and
continues. Screenshots are captured from that exact journey, so visual proof and
behavioral proof cannot drift into parallel versions of the application.

Clickable visual artwork and its learner hit target are separate derived layout
products. The precompute pipeline emits a transparent, placement-keyed
interaction envelope and a scene-level minimum 16:9 interaction frame with a
44 CSS-pixel hit core. The renderer consumes that envelope verbatim while the
host consumes the emitted frame metadata; neither layer rederives geometry.
The artwork remains at its computed visual box. Exact dotted subpart targets
remain declaration-owned SVG surfaces, so enlarged whole-object envelopes never
make adjacent wells, lanes, or slots ambiguous.

## Semantic inheritance and composition

The system prefers semantic inheritance over scene-specific duplication.

Higher-level behaviors should inherit stable meaning from lower-level primitives rather than redefining behavior per scene, protocol, or UI structure. A protocol action inherits meaning from the primitive actions it composes. A scene implementation inherits behavioral guarantees from the protocol vocabulary it renders.

Inheritance in this repository is semantic first, not necessarily class-based. The architecture does not require TypeScript subclassing. The requirement is that derived concepts preserve the guarantees, constraints, and meaning of their parent concepts.

Composition is preferred over taxonomy explosion. New behavior should first be expressed as a composition of existing primitives before introducing a new primitive or top-level category.

A new primitive requires evidence that:

- existing primitives cannot express the behavior clearly,
- the behavior appears across multiple protocols or scenes,
- and the primitive defines a stable reusable semantic unit.

This repository treats primitives as durable vocabulary infrastructure, not short-term implementation conveniences.

## Source-code and content layout

Authored TypeScript source for the shared scene runtime lives under `src/scene_runtime/`. Generated protocol, scene, inventory, and registry data emits under `generated/` at the repo root. Generated files do not live under `src/`.

Curriculum content lives under `content/protocols/<cluster>/<protocol_name>/`.

## Vocabulary closure and anti-drift

Authoring vocabularies (protocol, object, scene, material, and the supporting
subsystem vocabularies in [specs/LAYOUT_ENGINE.md](specs/LAYOUT_ENGINE.md),
[specs/MATERIAL_VOCABULARY.md](specs/MATERIAL_VOCABULARY.md),
[specs/MATERIAL_CONVENTION.md](specs/MATERIAL_CONVENTION.md), and
[specs/SVG_PIPELINE.md](specs/SVG_PIPELINE.md)) are closed surfaces. Authors compose
existing terms; they do not invent new ones by editing YAML alone.

Permanent principles:

- **Closure over openness.** Every container has a closed schema. Open
  maps, free-form objects, `metadata` / `extras` / `params` blobs, and
  `additionalProperties: true` are escape hatches. They permit
  uncontrolled vocabulary growth and must be replaced by explicit fields.
- **Flat primitives over nested blobs.** State fields are flat named
  fields with primitive types (`enum`, `int`, `float`, `bool`).
  Composition happens through multiple named fields, not nested objects.
  Setter primitives may write only declared fields with values matching
  the declared primitive type.
- **Layer boundaries are strict.** Protocol = intent. Object =
  representation and state. Scene = placement and layout. A lower layer
  must not learn higher-layer meaning, and a higher layer must not name
  lower-layer mechanisms (no SVG asset names in protocol; no behavior in
  scene; no protocol sequencing in object).
- **One canonical term per concept.** Synonyms across docs are shadow
  vocabularies and must be retired with explicit pointers.
- **Counts belong in inventories.** Canonical docs describe structure,
  not snapshots. Phrases like "7 scenes" or "45 assets" age into lies;
  use "every current X" and let the inventory artifact carry the count.
- **Examples illustrate the schema; they do not extend it.** Every field
  shown in an example must already appear in a schema table.
- **Transitional wording belongs in migration docs.** Canonical
  vocabulary docs must not carry migration-narrating qualifiers; they
  state the present rule.
- **New meaning requires a vocabulary edit.** Authors must not be able
  to expand the vocabulary surface by editing YAML alone. Extension
  points are explicit RFCs, not implicit support.

These principles are operationalized as a sweep checklist with smell
classes, severity labels, section-context tags, and past-pitfall
references. The checklist is the reusable audit tool; it is invoked when
auditing existing canonical docs or onboarding a new spec.

See [specs/SPEC_DESIGN_CHECKLIST.md](specs/SPEC_DESIGN_CHECKLIST.md) for the full
checklist.

## Accessibility scope

The scene runtime is pointer-optimized. Keyboard navigation, ARIA roles, screen-reader
support, and focus management are not current product goals for the scene interaction
layer. Pointer-user UX (hover feedback, click targets, visual state changes) is in scope
and must remain correct.

This is a reversible scope note about current focus, not a permanent contract policy.
Accessibility work for shell controls (tray, modals, toasts) is deferred until the shell
UI surface is functionally stable. See [PRIMARY_CONTRACT.md](PRIMARY_CONTRACT.md)
for invariants that would govern any future accessibility commitment.

## Visual integrity: never crop scientific assets

A scene cannot pass visual review if any scientific SVG asset is cropped or aspect-distorted enough to change what the object is.

This rule applies even if precheck reports `hard_fail_count = 0`. Visible cropping or distortion is a visual failure regardless of bbox-level checks.

Forbidden in any rendered scene:

- Cropped bottoms of volumetric flasks
- Cropped bottle necks or caps
- Clipped pipette tips
- Hidden instrument edges
- Object artwork cut off by cards, regions, wrappers, `overflow: hidden`, or `.object-graphic` containers
- Squashing or stretching that changes the intended asset aspect ratio

Diagnostic requirement:

- The `artwork_integrity` check must compare the rendered asset bbox against its parent placement card and flag overflow clipping plus aspect-ratio deviation > 5%.
- Visible clipping is HARD FAIL.
- Aspect distortion is HARD FAIL for lab glassware, pipettes, plates, and instruments; advisory for decorative items.

Fix direction (not a substitute for the rule):

- Use `object-fit: contain`, never `cover`.
- Preserve SVG `preserveAspectRatio="xMidYMid meet"`.
- Remove parent `overflow: hidden` where it clips assets.
- Size cards around assets, not assets into too-small cards.
- Add `min-height` / `min-width` for tall glassware cards.

Anti-patterns (forbidden):

- Do not "fix" cropping by hiding cropped assets, deleting DOM, or weakening diagnostics.
- Do not accept a high score if the asset is visibly cropped.
- Do not claim visual success while glassware bottoms are cut off.
