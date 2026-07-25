# Human guidance

## Language-neutral SVG art

Keep SVG source art language-neutral so future localization and accessibility
work can own student-facing text. Put instrument identity, state, and
instructional prose in layout-manager DOM labels or object data. No i18n system
is being implemented now; this keeps that future work unblocked. When imported
art contains prose, remove it and recreate it outside the SVG rather than
path-converting it to pass normalization or blind recognition. Keep sparse,
approved physically intrinsic markings only when they are part of the
instrument: numbers, scientific units or symbols, polarity, graduations, and
plate row or column coordinates. `tools/outline_svg_text.sh` may outline those
markings during legacy/import preparation, but provenance never permits
outlining prose. Treat blind recognition as diagnostic evidence, and improve
ambiguity when it creates a material pedagogical risk.
