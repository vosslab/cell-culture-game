# Virtual lab protocol simulation

Browser-based virtual lab protocol games for biology students. Authors compose scenes, objects, and workflows in YAML; the pipeline compiles them to interactive TypeScript simulations with SVG-backed objects laid out by a scene engine.

Try it live: [vosslab.github.io/virtual-lab-protocol-simulation](https://vosslab.github.io/virtual-lab-protocol-simulation/)

## Quick start

```bash
bash run_web_server.sh
```

Builds the project and serves `dist/` on a random port, then opens the protocol selector in your browser.

Other useful commands:

```bash
bash build_github_pages.sh   # build dist/ for deployment
bash check_codebase.sh       # typecheck, lint, and format check
source source_me.sh && pytest tests/   # run unit tests
```

## Documentation

Core docs:

- [docs/INSTALL.md](docs/INSTALL.md): prerequisites and setup steps
- [docs/USAGE.md](docs/USAGE.md): how to build, run, and author content
- [docs/EQUIPMENT_SVG_CONTACT_SHEET.md](docs/EQUIPMENT_SVG_CONTACT_SHEET.md): labeled visual review of every retained equipment SVG
- [docs/CODE_ARCHITECTURE.md](docs/CODE_ARCHITECTURE.md): system design and data flow
- [docs/FILE_STRUCTURE.md](docs/FILE_STRUCTURE.md): directory map and file purposes
- [docs/specs/PROTOCOL_AUTHORING_GUIDE.md](docs/specs/PROTOCOL_AUTHORING_GUIDE.md): worked example for authoring a new protocol

Reference docs:

- [AGENTS.md](AGENTS.md): agent instructions and repo guardrails
- [docs/PRIMARY_CONTRACT.md](docs/PRIMARY_CONTRACT.md): hard design invariants
- [docs/CHANGELOG.md](docs/CHANGELOG.md): record of changes
- [docs/ROADMAP.md](docs/ROADMAP.md): planned work and priorities

## License

- Code: [LICENSE.LGPL_v3](LICENSE.LGPL_v3)
- Non-code content: [LICENSE.CC_BY_4_0](LICENSE.CC_BY_4_0)

Maintained by Neil Voss, https://bsky.app/profile/neilvosslab.bsky.social
