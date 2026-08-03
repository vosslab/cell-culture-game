# Install

The game builds from TypeScript source into a single self-contained HTML file.
"Installed" means you can run `bash export_single_file.sh` and open
`dist-single/game.html` in a browser.
The HTML file is a generated artifact and is not committed to git.

## Requirements

- **Node.js** with `npx` on PATH (esbuild is fetched automatically via npx)
- **Python 3.12** for running tests and the development server
- **Bash** shell (build scripts and [source_me.sh](../source_me.sh) require Bash)
- A modern browser (Chrome, Firefox, Safari, Edge)

## Install steps

1. Clone the repository:

   ```bash
   git clone <repo-url>
   cd cell-culture-game-claude
   ```

2. Verify Node.js is available:

   ```bash
   node --version
   ```

3. Install Python dev dependencies (for tests and linting):

   ```bash
   pip3 install -r pip_requirements-dev.txt
   ```

4. Build the game:
   ```bash
   bash export_single_file.sh
   ```

## SVG asset pipeline (fresh clone)

The `generated/` tree at the repo root holds SVG asset modules emitted by
[gen_svg_manifest.py](../pipeline/gen_svg_manifest.py) from
the behavior-organized `assets/equipment/**/*.svg` source tree. The whole
generated tree is gitignored, so a fresh clone has no `generated/` directory.
Most workflows regenerate it transparently, but it must exist before `tsc`, the
bundler, or any test that imports from `generated/` will run.

Three ways to make `generated/` exist on a fresh clone:

1. Run any build script. Both regenerate `generated/` before `tsc`:
   ```bash
   bash build_github_pages.sh
   ```
   or
   ```bash
   bash export_single_file.sh
   ```
2. Run the test suite. The `pytest_sessionstart` hook in
   [conftest.py](../tests/conftest.py) regenerates once per session if
   `generated/svg_manifest.ts` is missing:
   ```bash
   source source_me.sh && pytest tests/
   ```
3. Run the generator directly:
   ```bash
   source source_me.sh && python3 pipeline/generate_svg_globals.py
   ```

By design, `bash check_codebase.sh` is read-only and does NOT regenerate
`generated/`. If you run it on a fresh clone before any of the above, it
exits non-zero with a hint pointing at the generator.

To wipe `generated/` (and other build artifacts) for fresh-start testing:

```bash
bash dist_clean.sh
```

See [specs/SVG_PIPELINE.md](specs/SVG_PIPELINE.md) for the full asset pipeline rules.

## Verify install

```bash
bash export_single_file.sh && test -f dist-single/game.html && echo "OK"
```

This confirms the TypeScript compilation succeeded and the output HTML exists.

## Python development tools

Run the test suite:

```bash
source source_me.sh && python3 -m pytest tests/
```

Python dev dependencies are listed in
[pip_requirements-dev.txt](../pip_requirements-dev.txt): bandit, packaging,
pyflakes, pytest, rich.

For browser smoke tests and walkthroughs, Playwright and Chromium are also
required. See [PLAYWRIGHT_USAGE.md](PLAYWRIGHT_USAGE.md).

## Known gaps

- TODO: Confirm minimum Node.js version required by esbuild
