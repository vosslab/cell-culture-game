# AGENTS.md

This repo builds virtual lab protocol games: protocol-authoring, object-authoring, scene-layout, and browser-simulation. `docs/PRIMARY_CONTRACT.md` wins over every other doc and over code; new contract items require user approval.

## Required reading

Before nontrivial edits: `docs/PRIMARY_CONTRACT.md`, `docs/PRIMARY_DESIGN.md`, `docs/PRIMARY_SPEC.md`, `docs/REPO_STYLE.md`, `docs/MARKDOWN_STYLE.md`, `docs/specs/SPEC_DESIGN_CHECKLIST.md`.

Task-specific: `docs/PYTHON_STYLE.md`, `docs/TYPESCRIPT_STYLE.md`, `docs/E2E_TESTS.md`, `docs/PLAYWRIGHT_USAGE.md`, `docs/CLAUDE_HOOK_USAGE_GUIDE.md`, `docs/specs/`.

## Core rules

Core invariants (YAML config, TypeScript runtime, mini-protocols, SVG scene objects, layout engine, visible-UI completion, learning-block scope) live in `docs/PRIMARY_CONTRACT.md` and `docs/PRIMARY_SPEC.md`. Do not restate or override them here.

- Materials: `docs/specs/MATERIAL_VOCABULARY.md`, `docs/specs/MATERIAL_CONVENTION.md`.
- Test data policy (content is the fixture): `docs/specs/NO_FIXTURE_POLICY.md`.
- Closed authoring vocabularies, no escape hatches: `docs/specs/SPEC_DESIGN_CHECKLIST.md`.
- Stable project guidance: `docs/HUMAN_GUIDANCE.md`.

## Pipeline vs tools (binding, non-negotiable)

`pipeline/` owns anything that emits to `generated/` or `dist/` or is invoked by `build_github_pages.sh` / `package.json`; `tools/` owns dev-only helpers. Never duplicate a generator across both, and never archive superseded pipeline files into `tools/` (delete them; git history is the archive). A new pipeline script updates `docs/FILE_STRUCTURE.md` and `docs/CODE_ARCHITECTURE.md` in the same patch.

## Where to find things

- Repo map and architecture: `docs/FILE_STRUCTURE.md`, `docs/CODE_ARCHITECTURE.md`
- Specs: `docs/specs/` (`PROTOCOL_*`, `SCENE_*`, `OBJECT_*`, `MATERIAL_*`, `LAYOUT_ENGINE.md`, `QTI_v3_SPEC.md`)
- Current work: `docs/TODO.md`, `docs/ROADMAP.md`, `docs/active_plans/`

## Python environment

- Run repo-local Python via `source source_me.sh && python3` (Python 3.12 only). `source_me.sh` exports `PYTHONPATH=<repo-root>` so `pipeline.*` and `validation.*` imports resolve.
- Homebrew Python 3.12 site-packages: /opt/homebrew/lib/python3.12/site-packages/
