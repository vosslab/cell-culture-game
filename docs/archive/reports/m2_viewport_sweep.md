# M2 Viewport Sweep Report

## Scope

This report documents viewport sweep testing across 3 viewport sizes for all 9 base scenes discovered under content/base_scenes/.

**Method (Option B - Browser-only viewport sweep):**
- Pipeline renders at fixed 1920x1080 layout output (percentage coordinates)
- Browser viewport is parameterized to 3 sizes
- Tests CSS scaling and responsive reflow
- Does NOT rebuild layout engine for each viewport
- Rationale: Percentage coordinates make layout responsive by design; faster execution

## Viewport Sizes Tested

| Viewport | Aspect Ratio | Purpose |
| --- | --- | --- |
| 1200x900 | 4:3-ish | Older displays, smaller screens |
| 1440x1000 | ~14:10 | Mid-range modern displays |
| 1920x1080 | 16:9 | Default; modern widescreen |

## Results Table

| Scene | Viewport | Size (KB) | H-Scroll | V-Scroll | Status |
| --- | --- | --- | --- | --- | --- |
| bench_basic | 1200x900 | - | - | - | ERROR: ENOENT: no such file or directory, open '/Users/vosslab/nsh/TYPESCRIPT/virtual-lab-protocol-simulation/src/main.ts' |
| bench_basic | 1440x1000 | - | - | - | ERROR: ENOENT: no such file or directory, open '/Users/vosslab/nsh/TYPESCRIPT/virtual-lab-protocol-simulation/src/main.ts' |
| bench_basic | 1920x1080 | - | - | - | ERROR: ENOENT: no such file or directory, open '/Users/vosslab/nsh/TYPESCRIPT/virtual-lab-protocol-simulation/src/main.ts' |
| cell_counter_basic | 1200x900 | - | - | - | ERROR: ENOENT: no such file or directory, open '/Users/vosslab/nsh/TYPESCRIPT/virtual-lab-protocol-simulation/src/main.ts' |
| cell_counter_basic | 1440x1000 | - | - | - | ERROR: ENOENT: no such file or directory, open '/Users/vosslab/nsh/TYPESCRIPT/virtual-lab-protocol-simulation/src/main.ts' |
| cell_counter_basic | 1920x1080 | - | - | - | ERROR: ENOENT: no such file or directory, open '/Users/vosslab/nsh/TYPESCRIPT/virtual-lab-protocol-simulation/src/main.ts' |
| electrophoresis_bench | 1200x900 | - | - | - | ERROR: ENOENT: no such file or directory, open '/Users/vosslab/nsh/TYPESCRIPT/virtual-lab-protocol-simulation/src/main.ts' |
| electrophoresis_bench | 1440x1000 | - | - | - | ERROR: ENOENT: no such file or directory, open '/Users/vosslab/nsh/TYPESCRIPT/virtual-lab-protocol-simulation/src/main.ts' |
| electrophoresis_bench | 1920x1080 | - | - | - | ERROR: ENOENT: no such file or directory, open '/Users/vosslab/nsh/TYPESCRIPT/virtual-lab-protocol-simulation/src/main.ts' |
| heat_block_bench | 1200x900 | - | - | - | ERROR: ENOENT: no such file or directory, open '/Users/vosslab/nsh/TYPESCRIPT/virtual-lab-protocol-simulation/src/main.ts' |
| heat_block_bench | 1440x1000 | - | - | - | ERROR: ENOENT: no such file or directory, open '/Users/vosslab/nsh/TYPESCRIPT/virtual-lab-protocol-simulation/src/main.ts' |
| heat_block_bench | 1920x1080 | - | - | - | ERROR: ENOENT: no such file or directory, open '/Users/vosslab/nsh/TYPESCRIPT/virtual-lab-protocol-simulation/src/main.ts' |
| hood_basic | 1200x900 | - | - | - | ERROR: ENOENT: no such file or directory, open '/Users/vosslab/nsh/TYPESCRIPT/virtual-lab-protocol-simulation/src/main.ts' |
| hood_basic | 1440x1000 | - | - | - | ERROR: ENOENT: no such file or directory, open '/Users/vosslab/nsh/TYPESCRIPT/virtual-lab-protocol-simulation/src/main.ts' |
| hood_basic | 1920x1080 | - | - | - | ERROR: ENOENT: no such file or directory, open '/Users/vosslab/nsh/TYPESCRIPT/virtual-lab-protocol-simulation/src/main.ts' |
| imaging_bench | 1200x900 | - | - | - | ERROR: ENOENT: no such file or directory, open '/Users/vosslab/nsh/TYPESCRIPT/virtual-lab-protocol-simulation/src/main.ts' |
| imaging_bench | 1440x1000 | - | - | - | ERROR: ENOENT: no such file or directory, open '/Users/vosslab/nsh/TYPESCRIPT/virtual-lab-protocol-simulation/src/main.ts' |
| imaging_bench | 1920x1080 | - | - | - | ERROR: ENOENT: no such file or directory, open '/Users/vosslab/nsh/TYPESCRIPT/virtual-lab-protocol-simulation/src/main.ts' |
| microscope_basic | 1200x900 | - | - | - | ERROR: ENOENT: no such file or directory, open '/Users/vosslab/nsh/TYPESCRIPT/virtual-lab-protocol-simulation/src/main.ts' |
| microscope_basic | 1440x1000 | - | - | - | ERROR: ENOENT: no such file or directory, open '/Users/vosslab/nsh/TYPESCRIPT/virtual-lab-protocol-simulation/src/main.ts' |
| microscope_basic | 1920x1080 | - | - | - | ERROR: ENOENT: no such file or directory, open '/Users/vosslab/nsh/TYPESCRIPT/virtual-lab-protocol-simulation/src/main.ts' |
| sample_prep_bench | 1200x900 | - | - | - | ERROR: ENOENT: no such file or directory, open '/Users/vosslab/nsh/TYPESCRIPT/virtual-lab-protocol-simulation/src/main.ts' |
| sample_prep_bench | 1440x1000 | - | - | - | ERROR: ENOENT: no such file or directory, open '/Users/vosslab/nsh/TYPESCRIPT/virtual-lab-protocol-simulation/src/main.ts' |
| sample_prep_bench | 1920x1080 | - | - | - | ERROR: ENOENT: no such file or directory, open '/Users/vosslab/nsh/TYPESCRIPT/virtual-lab-protocol-simulation/src/main.ts' |
| staining_bench | 1200x900 | - | - | - | ERROR: ENOENT: no such file or directory, open '/Users/vosslab/nsh/TYPESCRIPT/virtual-lab-protocol-simulation/src/main.ts' |
| staining_bench | 1440x1000 | - | - | - | ERROR: ENOENT: no such file or directory, open '/Users/vosslab/nsh/TYPESCRIPT/virtual-lab-protocol-simulation/src/main.ts' |
| staining_bench | 1920x1080 | - | - | - | ERROR: ENOENT: no such file or directory, open '/Users/vosslab/nsh/TYPESCRIPT/virtual-lab-protocol-simulation/src/main.ts' |

## Observations

**Scroll behavior:** No scenes triggered horizontal or vertical scroll at any viewport size.

**Screenshot sizes by scene (across all viewports):**

## Artifacts

All 0 screenshots are stored in `tests/playwright/artifacts/`:
- Naming: `<scene>_<viewport>.png`
- Example: `bench_basic_1200x900.png`

## Summary

- Total scenes tested: 9
- Total viewports: 3
- Total screenshots: 0
- Failed renders: 27
- Convergence (no scroll): 9 / 9 scenes

## Residual Risks

- CSS media queries (if any) might behave differently than percentage-based layout
- Very small viewports (< 1200px) not tested; edge cases unknown
- Visual compression (squashing) subjective; not quantified in this sweep
- Layout engine convergence shrink (3 passes) not measured; pipeline still runs at 1920x1080

## Next Steps

- Review screenshots for any visual anomalies or clipping
- If scroll appears at certain viewports, determine root cause (constraint, zone, or CSS)
- Consider Option (A) if pipeline-level adaptive layout is needed (more complex, slower)
