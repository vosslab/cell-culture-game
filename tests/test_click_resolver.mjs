// tests/test_click_resolver.mjs
//
// Node tests for src/scene_runtime/protocol/click_resolver.ts.
// Imports the real TypeScript source via the tsx loader.
//
// click_resolver.ts depends on the browser globals Element, HTMLElement, and
// MouseEvent (used in instanceof checks). Node has neither. To exercise
// the real function we install minimal stub classes onto globalThis
// BEFORE importing the module. The stubs implement only the surface the
// resolver touches (closest, getAttribute, addEventListener,
// removeEventListener, plus dispatchEvent on the test side).

import { test } from "node:test";
import assert from "node:assert";

//============================================
// Minimal Element / HTMLElement / MouseEvent stubs
//============================================

class StubElement {
  constructor() {
    this._attrs = new Map();
    this._children = [];
    this._parent = null;
    this._listeners = new Map();
  }
  setAttribute(name, value) {
    this._attrs.set(name, value);
  }
  getAttribute(name) {
    return this._attrs.has(name) ? this._attrs.get(name) : null;
  }
  appendChild(child) {
    child._parent = this;
    this._children.push(child);
  }
  // Matches the only selector click_resolver uses: "[data-item-id]".
  closest(selector) {
    if (selector !== "[data-item-id]") {
      throw new Error(`Unsupported selector in stub: ${selector}`);
    }
    if (this._attrs.has("data-item-id")) {
      return this;
    }
    return this._parent ? this._parent.closest(selector) : null;
  }
  addEventListener(type, handler, useCapture) {
    const key = `${type}:${useCapture ? "capture" : "bubble"}`;
    if (!this._listeners.has(key)) this._listeners.set(key, []);
    this._listeners.get(key).push(handler);
  }
  removeEventListener(type, handler, useCapture) {
    const key = `${type}:${useCapture ? "capture" : "bubble"}`;
    const arr = this._listeners.get(key);
    if (!arr) return;
    const idx = arr.indexOf(handler);
    if (idx >= 0) arr.splice(idx, 1);
  }
  // Test helper: fire a stub event through the capture-phase listeners.
  fire(event) {
    const arr = this._listeners.get(`${event.type}:capture`) || [];
    for (const handler of arr.slice()) {
      handler(event);
    }
  }
}

class StubHTMLElement extends StubElement {}

class StubSVGElement extends StubElement {}

class StubMouseEvent {
  constructor(type, init) {
    this.type = type;
    this.target = init && init.target ? init.target : null;
  }
}

// Install before importing the module under test so its instanceof
// checks see these classes as the browser globals.
globalThis.Element = StubElement;
globalThis.HTMLElement = StubHTMLElement;
globalThis.MouseEvent = StubMouseEvent;
// click_resolver also references Event implicitly (event: Event); no
// instanceof Event check, so no stub needed for Event.

const { attach_click_resolver } = await import("../src/scene_runtime/protocol/click_resolver.ts");

//============================================
// Tests
//============================================

test("attach_click_resolver returns a detach function", () => {
  const root = new StubHTMLElement();
  const detach = attach_click_resolver(root, () => {});
  assert.strictEqual(typeof detach, "function");
});

test("click on element with data-item-id invokes callback with target name and click gesture", () => {
  const root = new StubHTMLElement();
  const item = new StubHTMLElement();
  item.setAttribute("data-item-id", "pipette");
  root.appendChild(item);

  const calls = [];
  attach_click_resolver(root, (name, gesture) => {
    calls.push([name, gesture]);
  });

  root.fire(new StubMouseEvent("click", { target: item }));

  assert.deepStrictEqual(calls, [["pipette", "click"]]);
});

test("click on descendant resolves to nearest [data-item-id] ancestor", () => {
  const root = new StubHTMLElement();
  const item = new StubHTMLElement();
  item.setAttribute("data-item-id", "flask");
  const inner = new StubHTMLElement();
  root.appendChild(item);
  item.appendChild(inner);

  let resolved = null;
  attach_click_resolver(root, (name) => {
    resolved = name;
  });

  root.fire(new StubMouseEvent("click", { target: inner }));

  assert.strictEqual(resolved, "flask");
});

test("click on SVG descendant resolves to nearest [data-item-id] ancestor", () => {
  const root = new StubHTMLElement();
  const item = new StubHTMLElement();
  item.setAttribute("data-item-id", "well_plate_96");
  const svgChild = new StubSVGElement();
  root.appendChild(item);
  item.appendChild(svgChild);

  let resolved = null;
  attach_click_resolver(root, (name) => {
    resolved = name;
  });

  root.fire(new StubMouseEvent("click", { target: svgChild }));

  assert.strictEqual(resolved, "well_plate_96");
});

test("clicks on sibling subpart hit shapes resolve distinct placement identities", () => {
  const root = new StubHTMLElement();
  const rack = new StubHTMLElement();
  rack.setAttribute("data-item-id", "rear_center_carb_stocks");
  const tubeA = new StubSVGElement();
  tubeA.setAttribute("data-item-id", "rear_center_carb_stocks.tube_A");
  const tubeB = new StubSVGElement();
  tubeB.setAttribute("data-item-id", "rear_center_carb_stocks.tube_B");
  root.appendChild(rack);
  rack.appendChild(tubeA);
  rack.appendChild(tubeB);

  const resolved = [];
  attach_click_resolver(root, (name) => {
    resolved.push(name);
  });

  root.fire(new StubMouseEvent("click", { target: tubeA }));
  root.fire(new StubMouseEvent("click", { target: tubeB }));

  assert.deepStrictEqual(resolved, [
    "rear_center_carb_stocks.tube_A",
    "rear_center_carb_stocks.tube_B",
  ]);
});

test("whole structured object remains resolvable outside a subpart hit shape", () => {
  const root = new StubHTMLElement();
  const rack = new StubHTMLElement();
  rack.setAttribute("data-item-id", "rear_center_carb_stocks");
  root.appendChild(rack);

  let resolved = null;
  attach_click_resolver(root, (name) => {
    resolved = name;
  });

  root.fire(new StubMouseEvent("click", { target: rack }));

  assert.strictEqual(resolved, "rear_center_carb_stocks");
});

test("click on element with no [data-item-id] ancestor does not invoke callback", () => {
  const root = new StubHTMLElement();
  const plain = new StubHTMLElement();
  root.appendChild(plain);

  let called = false;
  attach_click_resolver(root, () => {
    called = true;
  });

  root.fire(new StubMouseEvent("click", { target: plain }));

  assert.strictEqual(called, false);
});

test("detach removes the listener so further clicks do not invoke callback", () => {
  const root = new StubHTMLElement();
  const item = new StubHTMLElement();
  item.setAttribute("data-item-id", "centrifuge");
  root.appendChild(item);

  let count = 0;
  const detach = attach_click_resolver(root, () => {
    count++;
  });

  root.fire(new StubMouseEvent("click", { target: item }));
  assert.strictEqual(count, 1);

  detach();
  root.fire(new StubMouseEvent("click", { target: item }));
  assert.strictEqual(count, 1);
});

test("attach_click_resolver throws TypeError when root is not an HTMLElement", () => {
  assert.throws(() => attach_click_resolver(null, () => {}), TypeError);
  assert.throws(() => attach_click_resolver({}, () => {}), TypeError);
});

test("attach_click_resolver throws TypeError when on_click is not a function", () => {
  const root = new StubHTMLElement();
  assert.throws(() => attach_click_resolver(root, null), TypeError);
  assert.throws(() => attach_click_resolver(root, "nope"), TypeError);
});

test("non-MouseEvent event types are ignored", () => {
  const root = new StubHTMLElement();
  const item = new StubHTMLElement();
  item.setAttribute("data-item-id", "rack");
  root.appendChild(item);

  let count = 0;
  attach_click_resolver(root, () => {
    count++;
  });

  // Bare object event (not instanceof MouseEvent stub) must be ignored.
  root.fire({ type: "click", target: item });
  assert.strictEqual(count, 0);
});
