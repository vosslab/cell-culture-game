# Virtual lab protocol games

This document defines the hard design contract for the virtual lab protocol games repo. These rules are permanent invariants. This document is short on purpose: it lists only non-negotiable rules.

Agent-editable documents include the philosophy and rationale in [PRIMARY_DESIGN.md](PRIMARY_DESIGN.md). The full technical specification lives in [PRIMARY_SPEC.md](PRIMARY_SPEC.md).

If any other document or any code conflicts with this contract, this contract wins. The conflicting document or code must be fixed.

New contract items require user approval. Agents may not add, remove, or edit contract items without approval.

## Contract items

1. **Scene and protocol configuration live in YAML.**
   All scene and protocol configuration options live in YAML files. Shared behavior and common runtime systems live in TypeScript. For example, SVG object declarations and object layout belong in YAML. Object highlighting and the layout engine belong in TypeScript. Earlier TypeScript was developed around the hood scene, with other scenes treated as derivatives. That design is no longer acceptable.

2. **Large protocols are compiled from mini-protocols.**
   Large protocols are assembled from individual mini-protocols in sequence. This keeps building and testing atomic, in line with `REPO_STYLE.md`. Moving forward, each mini-protocol compiles to its own HTML file. The repo should not return to one monolithic 12,000-line HTML file.

3. **Clickable objects are SVG-backed scene objects laid out by the layout engine.**
   All clickable objects, including pipettes, instruments, bottles, flasks, plates, racks, tubes, and wells, have SVG representations stored in `assets/`. All asset SVG files must be normalized. All SVGs used in a scene are declared in that scene's YAML file.

   Scene object layout is handled by the layout engine. Scenes must use the layout engine for positioning clickable objects. Custom geometry is allowed only for subparts inside a structured scientific object, such as wells inside a plate, tubes inside a rack, lanes inside a gel, or marks inside an instrument display. The structured object itself still remains a YAML-declared scene object placed by the layout engine.

   See [specs/LAYOUT_ENGINE.md](specs/LAYOUT_ENGINE.md). All materials in objects (liquids, mixtures, suspensions, waste, future solids) are handled by the material system: terms and classification in [specs/MATERIAL_VOCABULARY.md](specs/MATERIAL_VOCABULARY.md), render convention in [specs/MATERIAL_CONVENTION.md](specs/MATERIAL_CONVENTION.md). Materials should not be hard-coded into objects. This will take effort before inserting a new asset.

4. **A mini-protocol is not complete until the visible interaction works.**
   A walkthrough script must load the page normally and complete the mini-protocol through the same visible UI path a student would use. The script must click visible scene objects, buttons, modal controls, and answer choices. It must not advance progress by calling internal APIs, mutating game state, forcing scene changes, or using hidden controls.

   The walkthrough must run every step, perform every required interaction, and save browser screenshots showing the intended objects, highlights, click targets, and visible state changes. Screenshots should provide evidence before and after meaningful interactions, not only at the final state.

   Playwright acceptance must exercise the shipped application and the same workflows students receive. Visible UI actions must produce their real persisted effects through the product path; browser tests must prove those effects survive a reload and remain operable. Screenshots are evidence only when they come from that same connected run. The exhaustive acceptance entry point must include and reach this connected browser suite even when an earlier independent gate fails; external-tool E2Es must be bounded so a hung process becomes a recorded failure instead of hiding the browser result.

   Passing TypeScript, validators, build steps, or walker setup is not enough. For interactive scene work, completion requires browser evidence that the mini-protocol can be completed by a real user through the visible interface.

5. **A mini-protocol is scoped by its learning block.**
   Every mini-protocol must define `learning.objectives`, `learning.outcomes`, and `learning.goals`. These fields define what the mini-protocol teaches, what students can do afterward, and why the mini-protocol exists in the broader curriculum. A mini-protocol teaches one focused self-contained workflow.
   - `learning objectives`: begins with "Students completing this mini-protocol will have achieved..." and states what students will gain fluency with.
   - `learning outcomes`: begins with "Students completing this mini-protocol will be able to..." and states what students can do after completing the mini-protocol.
   - `learning goals`: begins with "Overall, this mini-protocol aims to accomplish..." and states the broader purpose.

## Related references

- [specs/SCENE_ARCHITECTURE.md](specs/SCENE_ARCHITECTURE.md) explains how scenes are wired and run at runtime.
- [specs/SCENE_VOCABULARY.md](specs/SCENE_VOCABULARY.md) defines canonical scene-system terms.
- [specs/SCENE_YAML_FORMAT.md](specs/SCENE_YAML_FORMAT.md) defines scene YAML schema.
- [specs/PROTOCOL_AUTHORING_GUIDE.md](specs/PROTOCOL_AUTHORING_GUIDE.md) explains how to author protocols.
- [specs/PROTOCOL_STEPS.md](specs/PROTOCOL_STEPS.md) describes canonical protocol step behavior.
- [specs/PROTOCOL_VOCABULARY.md](specs/PROTOCOL_VOCABULARY.md) defines canonical protocol terms.
- [specs/PROTOCOL_YAML_FORMAT.md](specs/PROTOCOL_YAML_FORMAT.md) defines protocol YAML schema.
- [specs/SPEC_DESIGN_CHECKLIST.md](specs/SPEC_DESIGN_CHECKLIST.md) defines the Author YAML vocabulary lock that closes authoring surfaces.
