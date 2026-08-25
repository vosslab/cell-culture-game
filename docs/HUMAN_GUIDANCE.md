# Human guidance

## Interaction guidance

Every protocol interaction owns two non-empty authored strings: `instruction`
is the primary next-action message and `hint` is additional support. The
runtime does not provide a generic guidance fallback. After a successful user
interaction, the runtime settles its response and transition, then publishes
the next interaction's instruction and hint as one atomic learner-facing view.
An already-open hint therefore advances with the primary message.

When an exact `(target, gesture)` pair occurs more than once, make every
instruction and every hint distinct after trimming and case normalization. The
pair should identify the materially different substep, even when the visible
gesture and target are the same.

Use positive, action-oriented wording. Let a hint add method, purpose, safety,
or evidence: where to aim, why the action matters, what to verify, or which
observation to use. Avoid repeating the command from the instruction. Before
an attempt, select guidance should describe how to compare evidence without
revealing the correct choice; type guidance should describe where or how to
record an observation without revealing the expected literal. Corrective
feedback may explain the result after a rejected attempt.

## Language-neutral SVG art

Keep SVG source art language-neutral so future localization and accessibility
work can own student-facing text. Put instrument identity, state, and
instructional prose in layout-manager DOM labels or object data. No i18n system
is being implemented now; this keeps that future work unblocked. When imported
art contains prose, remove it and recreate it outside the SVG rather than
path-converting it to pass normalization or blind recognition. Keep sparse,
approved physically intrinsic markings only when they are part of the
instrument: numbers, scientific units or symbols, polarity, graduations, and
plate row or column coordinates. Prefer authored path geometry for those rare
markings. When imported intrinsic markings arrive as live SVG text, prefer
`rsvg-convert --format svg` to prepare a separate path-only SVG. Run every
prepared result through `tools/normalize_svg_v3.py`; it continues to reject all
live SVG text. The repository does not integrate a desktop SVG editor.
Provenance never permits outlining prose. Treat blind recognition as
diagnostic evidence, and improve ambiguity when it creates a material
pedagogical risk.

## Scientific equipment SVGs

Research ambiguous labware against primary manufacturer images or manuals and
the recorded source asset before drawing it. Use the de-shadowed Servier
Bioicons subset as the target visual language: remove detached floor shadows
while preserving local shading that explains form. Treat other Bioicons source
families as references rather than style targets.

Reuse one canonical physical SVG form when semantic objects use the same
labware and differ only by identity, contents, or volume. Keep distinct object
names when protocols need distinct state contracts, then let their
`visual_states` select the shared form and let material rendering show the
contents. Encode state changes in equipment art when the physical object makes
them observable. An opaque sharps container, for example, uses one SVG whether
its recorded state is empty or full.

Keep genuinely different labware distinct. A T75 tissue-culture flask is a flat
growth-surface vessel with a canted neck. Microtubes and conical centrifuge
tubes are separate forms; select between them from the authored material volume
and procedure rather than from a generic "tube" label.

When the user identifies repository-authored artwork as the intended source,
compare that artwork and its history before replacing it with a generic redraw.
Use focused standalone and composite renders during implementation, then use
the labeled equipment contact sheet as the final human visual review surface.

## Connected learner acceptance

Keep browser acceptance on the same built system and visible workflows learners
receive. UI actions must create their real persisted effects, and Playwright
must prove those effects through reload and continued interaction. Capture
screenshots from that same connected run. The exhaustive acceptance command
must include this browser journey and reach it even when another independent
gate fails; bound external-tool processes so a hang is reported instead of
hiding the connected result.

## Pre-production design direction

Use the repository's pre-production state to choose the durable canonical
design without compatibility shims for unused interfaces. When one option is
clearly strongest, record the assumption, implement it, and complete its safe
follow-on work. Prefer adaptable ownership boundaries and complete system
evidence over local patches or narrow green checks.
