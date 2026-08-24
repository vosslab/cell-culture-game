// Generated-inventory verification for interaction envelopes.
//
// The visual layout box and the learner's hit envelope are intentionally
// distinct.  This test reads the generated precomputed inventory rather than
// naming individual protocols, so a future scene cannot bypass the 44px
// interaction/frame contract by happening not to be in a hand-picked fixture.

import test from "node:test";
import assert from "node:assert/strict";

import { PRECOMPUTED_LAYOUT } from "../generated/precomputed_layout.ts";
import {
  derive_scene_interaction_geometry,
  INTERACTION_HIT_CORE_PX,
} from "../src/scene_runtime/layout/interaction_geometry.ts";

const SCENE_ASPECT_RATIO = 16 / 9;

function envelope_rect(envelope, frame) {
  const width = frame.width_px;
  const height = frame.height_px;
  const center_x = (envelope.center_x_percent / 100) * width;
  const center_y = (envelope.center_y_percent / 100) * height;
  const envelope_width = Math.max(frame.hit_core_px, (envelope.visual_width_percent / 100) * width);
  const envelope_height = Math.max(
    frame.hit_core_px,
    (envelope.visual_height_percent / 100) * height,
  );
  return {
    left: center_x - envelope_width / 2,
    right: center_x + envelope_width / 2,
    top: center_y - envelope_height / 2,
    bottom: center_y + envelope_height / 2,
    width: envelope_width,
    height: envelope_height,
  };
}

function overlaps(first, second) {
  return (
    first.left < second.right &&
    second.left < first.right &&
    first.top < second.bottom &&
    second.top < first.bottom
  );
}

test("generated scene inventory gives every clickable placement a bounded, unambiguous 44px envelope", () => {
  assert.equal(INTERACTION_HIT_CORE_PX, 44, "the project-wide learner hit core is 44 CSS pixels");

  const scene_names = Object.keys(PRECOMPUTED_LAYOUT);
  assert.ok(scene_names.length > 0, "generated precomputed layout inventory is non-empty");

  for (const scene_name of scene_names) {
    const layout = PRECOMPUTED_LAYOUT[scene_name];
    const geometry = layout.interactionGeometry;
    assert.ok(geometry, `${scene_name}: generated interaction geometry is present`);
    assert.equal(
      geometry.valid,
      true,
      `${scene_name}: shipped scene has a usable interaction frame`,
    );
    if (!geometry.valid) {
      continue;
    }

    const frame = geometry.minimum_frame;
    assert.equal(
      frame.hit_core_px,
      INTERACTION_HIT_CORE_PX,
      `${scene_name}: frame preserves hit core`,
    );
    assert.ok(
      frame.width_px > 0 && frame.height_px > 0,
      `${scene_name}: frame dimensions are positive`,
    );
    assert.ok(
      Math.abs(frame.width_px / frame.height_px - SCENE_ASPECT_RATIO) < 0.01,
      `${scene_name}: frame remains 16:9`,
    );

    const clickable = layout.final.filter((item) => item.capabilities.includes("clickable"));
    const envelope_names = Object.keys(geometry.envelopes).sort();
    const clickable_names = clickable.map((item) => item.placement_name).sort();
    assert.deepEqual(
      envelope_names,
      clickable_names,
      `${scene_name}: generated envelopes cover exactly the clickable placements`,
    );

    const rects = clickable.map((item) => {
      const envelope = geometry.envelopes[item.placement_name];
      assert.ok(envelope, `${scene_name}/${item.placement_name}: envelope is present`);
      assert.equal(
        envelope.placement_name,
        item.placement_name,
        `${scene_name}/${item.placement_name}: envelope keeps placement identity`,
      );
      const rect = envelope_rect(envelope, frame);
      assert.ok(
        rect.width >= INTERACTION_HIT_CORE_PX && rect.height >= INTERACTION_HIT_CORE_PX,
        `${scene_name}/${item.placement_name}: envelope provides the 44px learner hit core`,
      );
      assert.ok(
        rect.left >= 0 &&
          rect.top >= 0 &&
          rect.right <= frame.width_px &&
          rect.bottom <= frame.height_px,
        `${scene_name}/${item.placement_name}: envelope stays inside its minimum usable frame`,
      );
      return { placement_name: item.placement_name, rect };
    });

    for (let index = 0; index < rects.length; index += 1) {
      for (let other = index + 1; other < rects.length; other += 1) {
        assert.equal(
          overlaps(rects[index].rect, rects[other].rect),
          false,
          `${scene_name}: envelopes for ${rects[index].placement_name} and ${rects[other].placement_name} are unambiguous`,
        );
      }
    }
  }
});

test("interaction geometry reports an ambiguous envelope set without blocking layout diagnostics", () => {
  const geometry = derive_scene_interaction_geometry([
    {
      placement_name: "first",
      capabilities: ["clickable"],
      _centerX: 50,
      _top: 50,
      _visualWidth: 1,
      _height: 1,
    },
    {
      placement_name: "second",
      capabilities: ["clickable"],
      _centerX: 50,
      _top: 50,
      _visualWidth: 1,
      _height: 1,
    },
  ]);

  assert.equal(
    geometry.valid,
    false,
    "overlapping whole-object envelopes are reported, not silently accepted",
  );
  if (!geometry.valid) {
    assert.deepEqual(geometry.issues, [
      { kind: "no_valid_frame", placements: ["first", "second"] },
    ]);
  }
});
