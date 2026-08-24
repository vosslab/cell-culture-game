# Protocol steps

Protocol terminology is defined in [PROTOCOL_VOCABULARY.md](PROTOCOL_VOCABULARY.md). This doc uses that vocabulary.

How a protocol's steps are shaped, ordered, validated, and resolved.

## Source of truth

All protocol steps are defined in YAML under `content/protocols/` and
compiled at build time into a typed TypeScript constant. Each step carries
the six
required slots from [PROTOCOL_VOCABULARY.md](PROTOCOL_VOCABULARY.md):

| Slot             | Purpose                                                                                  |
| ---------------- | ---------------------------------------------------------------------------------------- |
| `step_name`      | Stable snake_case identifier for the step. Used for protocol flow, tests, and debugging. |
| `prompt`         | States what the student is asked to accomplish in this step.                             |
| `sequence`       | The ordered list of `interaction` blocks; order always matters.                          |
| `step_validator` | Named preset that checks whole-step completion.                                          |
| `outcome`        | The `{on_success, on_failure}` mapping that says how the step resolves.                  |
| `next_step`      | Names the next step by its `step_name`, or `null` for a terminal step.                   |

The full YAML schema for these slots, the `interaction` block, the
`response` container, and the validator presets is documented in
[PROTOCOL_YAML_FORMAT.md](PROTOCOL_YAML_FORMAT.md).

## A step is one pedagogical unit

A `step` is one thing the student is asked to accomplish. A step is often
multi-gesture: "Wash the flask with 4 mL PBS" is a single step, but
completing it takes three gestures. The two-level model keeps the step as
the pedagogical unit while the individual gestures live inside it in an
ordered `sequence` of `interaction` blocks.

Each `interaction` is one `gesture` on one `target`, checked by its own
`validator`, with its own `response`. There is no separate task-type slot
on an interaction; the target's kind plus the gesture carries the task
semantics. See [PROTOCOL_VOCABULARY.md](PROTOCOL_VOCABULARY.md) for the
slot charters.

## The interaction chain

Within a step, the chain runs:

1. The student performs a `gesture` on a `target`. That pair is one
   `interaction`.
2. The interaction's `validator` -- a named preset -- checks that one
   gesture on that one target.
3. A valid interaction fires its `response`: the `scene_operations` the
   gesture causes plus optional `feedback`.
4. The step's interactions run in `sequence` order. When the sequence is
   satisfied, the step's `step_validator` -- also a named preset -- checks
   whole-step completion.
5. The `step_validator` result drives the `outcome` mapping: `on_success`
   resolves the step, `on_failure` restarts the whole step (the entire
   `sequence` resets). Once the step resolves, `next_step` names which step
   runs next. Advancing is not an `outcome` value.

## Ordering: explicit, not positional

Protocol flow is `entry_step` plus each step's `next_step` pointer. Array
position in the `steps` list is reading convenience only and never controls
flow.

```
spray_hood -> aspirate_old_media -> pbs_wash -> add_trypsin -> ...
                                                     -> plate_read -> results (next_step: null)
```

The runtime follows the chain: when a step resolves `complete`, it reads its
`next_step` and that step becomes active. When `next_step` is `null`, the
protocol is complete.

### Why not array position

A positional model couples step identity to array order: inserting a step
between two others becomes a global edit, and a rename in one place without
the other causes silent deadlocks. With `next_step`, reordering is a local
edit: change two neighbors' `next_step` pointers. Inserting a step is three
edits: add the new step, point the previous step at it, point it at the
next step.

A `step_index` field may exist for display order only. It is not part of
the protocol-flow spec and never controls flow.

## The iterative loop

An iterative loop -- destaining until the background is clear -- is
expressed as a `final_state_matches` `step_validator` plus an
`outcome.on_failure: retry`. While the named state is not reached,
`on_failure: retry` restarts the whole step. There is no separate
`repeat_until` construct and no separate loop step type.

## Adding a new step

1. Add a new entry to the protocol's `steps` list with `step_name`,
   `prompt`, `sequence`, `step_validator`, `outcome`, and `next_step`.
2. For each interaction in the `sequence`, fill all six required slots:
   `target`, `gesture`, non-empty plain-string `instruction`, non-empty
   plain-string `hint`, `validator`, and `response`. If an exact
   `(target, gesture)` pair repeats within the step, every interaction in that
   group must use distinct instructions and hints after trim/case
   normalization. Select and type guidance remains answer-safe before an
   attempt. See [PROTOCOL_YAML_FORMAT.md](PROTOCOL_YAML_FORMAT.md) for the
   complete safety and validation rules.
3. Wire `next_step` to the next step's `step_name` (or `null` for the last step).
4. Find the step that should now come before the new step and change its
   `next_step` to the new step's `step_name`.
5. If this is the first step, update the protocol's `entry_step`.
6. Rebuild so the typed protocol data regenerates, and walk the protocol
   through the real UI (see [WALKTHROUGH_GUIDE.md](WALKTHROUGH_GUIDE.md)).

## Event emission

Events are emitted by the runtime on a state transition the rest of the
protocol may react to: an interaction firing a true `validator`, a step
resolving `complete`, or a timed-equipment phase elapsing. Events are not
hand-authored per interaction. Event names are snake_case and derived from
the `step_name` or equipment name of the thing they report: `<step_name>_complete`
when a step resolves, `<equipment_name>_elapsed` when a timed phase ends. An
author who renames a step renames its completion event with it.

## Startup validation

Load-time checks verify the step graph before any user interaction:

- Every step identifier is unique.
- Following the flow pointers from the first step visits every step, with
  exactly one terminal step. Catches broken links and orphan steps.
- Every flow pointer references a real step.
- Field-presence: every step has its required slots.

A validation failure injects a blocking error banner, logs to console, and
records the failure on a window-scoped validation flag.

## UI walker

The canonical real-UI regression test is the YAML-driven UI walker
documented in [WALKTHROUGH_GUIDE.md](WALKTHROUGH_GUIDE.md). It reads the
compiled protocol data and drives real DOM clicks through the same visible
path a student uses. It is the primary CI gate for whether a mini-protocol
is playable.

## Related docs

- [PROTOCOL_VOCABULARY.md](PROTOCOL_VOCABULARY.md): canonical terms.
- [PROTOCOL_YAML_FORMAT.md](PROTOCOL_YAML_FORMAT.md): full step and
  interaction YAML schema.
- [PROTOCOL_AUTHORING_GUIDE.md](PROTOCOL_AUTHORING_GUIDE.md): how to author
  a protocol end to end.
- [WALKTHROUGH_GUIDE.md](WALKTHROUGH_GUIDE.md): the real-UI walker.
