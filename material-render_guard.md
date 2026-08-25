# Historical material-render measurement

> Status: superseded by the material-SVG cutover completed before the 2026-08-24
> SVG consistency closeout. The measurements below preserve the pre-cutover
> finding and method; current status lives in `docs/ROADMAP.md` and
> `assets/SVG_ASSET_GAPS.md`.

Pulled the real numbers. Two genuine defects surfaced, plus a methodology win.

Data: 231 fill_height overlay entries across all scenes. 121 read 0% (empty in default state), 110 filled. Full
containers 93-97%, partials ~60-74%.

Learning 1 - full-bbox fill confirmed and quantified. The fill overlay paints the whole object bounding box, not
the SVG liquid interior. A "full" bottle hits ~95% coverage when it should only paint the liquid region. This is
the known deferred bug (ROADMAP.md:183). The guard now pins current geometry so it can't silently get worse.

Learning 2 - the bigger one: materials aren't colored at all. Every single one of the 231 fills renders
rgba(120,120,120,0.35) - the neutral "no material color" grey fallback. Zero entries carry a material identity
color (carboplatin's #a719db, PBS, waste, etc.). Per MATERIAL_DESIGN, color is material identity - so right now
a student can't tell PBS from carboplatin from waste by color; they're all grey. This lines up with the
known-incomplete per-material recolor pipeline (assets/SVG_ASSET_GAPS.md), so it's an existing gap, not a new
regression - but the guard made it visible and measurable. Arguably a worse pedagogy problem than the bbox bug.

Learning 3 - measured % is a volume proxy, not the bug itself. Because the overlay is a full-width rectangle,
the % tracks how high the fill rises (0% empty -> ~95% full). The actual defect is the width/shape (should follow
the glass interior), which the coverage % doesn't isolate. So the guard catches "fill got bigger," not "fill got
the wrong shape" - worth knowing when the real fix lands.

Learning 4 - methodology. Flat-color pixel matching failed (translucent fallback composited over artwork -> no
reliable target color). The overlay-toggle diff (screenshot with fill visible vs hidden, count changed pixels)
is the robust segmentation - color-agnostic, isolates exactly the overlay's pixels. Reusable for any
overlay-render check.

Net: the material-fill fix (ROADMAP.md:183) should address both shape (interior clip) and color (identity
resolver) - the guard proved they're separate and both currently broken. When someone takes that fix, this guard
is its acceptance oracle.
