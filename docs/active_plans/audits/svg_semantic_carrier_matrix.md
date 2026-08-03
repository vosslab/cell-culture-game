# SVG semantic carrier matrix

## Scope

This M2 probe measures the current SVG normalizer and manifest sanitizer. It does not
change the implementation. Its evidence supports the approved and ratified design:
self-describing material-rendered SVGs, authored semantic groups, no sidecar, and
runtime handles derived after normalization.

Probe sources and normalized output were created under `test-results/svg_semantic_probe/`
during the run. The Playwright build cleans that ignored directory, so the retained evidence
below includes the exact commands and results rather than relying on ephemeral files.

## Cases exercised

The `data-vlab` source used fixed back and front groups, a material base group with two
paths, and a nested highlight group containing a `rect`. The normalizer converted that
`rect` to a `path`. Separate sources exercised `id` and reserved `class` carriers. The
additional cases were a semantic group with `clip-path`, repeated normalization, a duplicate
`layer_name`, and the existing two-instance injection test.

Commands:

```sh
source source_me.sh
python3 tools/normalize_svg_v3.py -i <source> -o <output-dir>
npx playwright test tests/playwright/test_svg_id_namespacing.spec.ts
```

For sanitizer measurement, the probe parsed each normalized result and called the same
`pipeline/gen_svg_manifest.py:_strip_unsafe_attrs` function used by manifest generation.

## Carrier results

| Carrier | Normalizer | Manifest sanitizer | Groups and order | Repeated roles | Runtime derivation now | Result |
| --- | --- | --- | --- | --- | --- | --- |
| `id` | Preserved | Preserved | Preserved | Poor: ids must be unique | Existing injection namespaces ids per instance | Reject as semantic carrier; reserve for structural anchors |
| Reserved `class` tokens | Preserved, including converted shapes | Preserved | Preserved | Supported | No semantic manifest generator exists | Viable fallback, but structured values must be encoded in tokens |
| Reserved `data-vlab-*` attributes | Preserved on groups | Stripped by current allowlist | Preserved on groups | Supported | No semantic manifest generator exists | Selected authored carrier; requires material-policy preservation |

Current normalizer output is byte-identical after a second normalization for all four accepted
sources: `id`, class, `data-vlab`, and the intentionally duplicate semantic source.

## Detailed findings

| Case | Current behavior | Required material-policy behavior |
| --- | --- | --- |
| One path per role | Groups and attributes survive normalizing | Validate the group and generate a derived handle |
| Multiple paths sharing a role | A group cleanly owns both paths | Keep the group intact; one role can paint many paths |
| Nested groups | Nested groups survive | Nested nonsemantic artwork groups are allowed inside a layer; semantic layer groups must not nest |
| Fixed back/front groups | Group order survives | Retain fixed groups and use document order as the only stacking authority |
| Shape-to-path conversion | A `rect` becomes a `path`; `class` survives on a shape but arbitrary `data-*` on a shape would not be copied | Semantic attributes live on the owning group, never on leaf shapes |
| Clipped material group | Rejected as `CLIPPATH_UNSUPPORTED_COMPLEX`: `clip target <g> is not path geometry` | Material policy retains the structural clip anchor and applies clipping to the derived runtime level group, not an authored semantic group |
| Repeated normalization | Accepted probes are byte-identical on pass two | Keep byte stability as an acceptance test |
| Duplicate runtime instances | Existing Playwright suite passed 4 tests, including same-asset and duplicate-id isolation | Manifest handles must resolve host-locally through the injection seam |
| Invalid duplicate layer | Normalizer accepts duplicate `data-vlab-layer-name` because it has no semantic validator | New validator must reject duplicates on normalized output |

The normalizer preserves group structure and current document order for these probes. It does
not merge paths, but that is not yet a semantic guarantee. The material policy must prohibit
merging across a semantic boundary explicitly.

## Sanitizer evidence

The sanitizer's positive allowlist retains `id`, `class`, and the existing `data-name` plus
specific `data-*-id` fields. It strips the root `data-vlab-rendering` and every probed
`data-vlab-*` layer attribute. This makes the ratified carrier unavailable to manifest
generation until the manifest sanitizer receives a closed `data-vlab-*` allowlist under the
material policy.

This is migration work, not evidence to change the carrier. The repository owns both stages;
the final normalized and sanitized material SVG must preserve the same validated semantics.

## Decision input

`data-vlab-*` attributes on semantic groups are the clearest carrier because they represent
structured fields without abusing ids or encoding values into classes. The selected contract
and required guarantees are recorded in
[svg_material_semantic_contract.md](../decisions/svg_material_semantic_contract.md).

Residual implementation risks are deliberately visible:

- the ordinary normalizer currently rejects a group-level clip;
- the sanitizer strips the selected carrier;
- no normalized-output semantic validator or derived liquid-region manifest exists;
- current duplicate-instance evidence covers id isolation, not generated material handles.

WP-R1 ratification is complete. WP-R2 remains pending until the material policy
closes all four gaps with tests.
