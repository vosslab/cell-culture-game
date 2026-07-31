// tests/test_authored_value_check.mjs
//
// Node --test suite for src/scene_runtime/protocol/authored_value_check.ts.
// Uses a fake lookup_state_field controlled per case. No mocks of the module
// under test. Each test names the exact required case from the WP-TEST scope.

import { test } from "node:test";
import assert from "node:assert";

import {
  validate_authored_validator_values,
  UnknownAuthoredObjectError,
  UnknownAuthoredSubpartError,
  UnknownAuthoredFieldError,
  BadAuthoredValueError,
} from "../src/scene_runtime/protocol/authored_value_check.ts";

//============================================
// Fixture helpers
//============================================

// Build a minimal ProtocolConfig with one step and one target_with_value
// interaction. protocol_type defaults to "mini_protocol".
function make_config_twv(opts) {
  const {
    protocol_type = "mini_protocol",
    protocol_name = "test_proto",
    step_name = "step_a",
    target = "some_obj",
    field = "some_field",
    authored_value,
  } = opts;
  return {
    protocol_name,
    protocol_type,
    entry_step: step_name,
    steps: [
      {
        step_name,
        prompt: "Click it",
        sequence: [
          {
            target,
            gesture: "click",
            validator: {
              preset: "target_with_value",
              value: { [field]: authored_value },
            },
            response: { scene_operations: [] },
          },
        ],
        step_validator: { preset: "sequence_complete" },
        outcome: { on_success: "complete", on_failure: "retry" },
        next_step: null,
      },
    ],
  };
}

// Build a minimal ProtocolConfig with one step and a final_state_matches
// step_validator. protocol_type defaults to "mini_protocol".
function make_config_fsm(opts) {
  const {
    protocol_type = "mini_protocol",
    protocol_name = "test_proto",
    step_name = "step_a",
    target = "some_obj",
    field = "some_field",
    authored_value,
  } = opts;
  return {
    protocol_name,
    protocol_type,
    entry_step: step_name,
    steps: [
      {
        step_name,
        prompt: "Do it",
        sequence: [
          {
            target: "ignored",
            gesture: "click",
            validator: { preset: "correct_target" },
            response: { scene_operations: [] },
          },
        ],
        step_validator: {
          preset: "final_state_matches",
          target,
          contains: { [field]: authored_value },
        },
        outcome: { on_success: "complete", on_failure: "retry" },
        next_step: null,
      },
    ],
  };
}

// A lookup factory: returns a function that always returns the given result.
function always(result) {
  return (_target, _field) => result;
}

//============================================
// Required Case 2: typed int field + bad value -> throws (unknown-reference
// checks and value-type checks always run; there is no exempt protocol_type)
//============================================

test("Case 2a: typed int + malformed string throws BadAuthoredValueError (twv)", () => {
  const config = make_config_twv({
    authored_value: "high",
  });
  const lookup = always({ kind: "typed", field_type: "int" });
  assert.throws(
    () => {
      validate_authored_validator_values({ protocol_config: config, lookup_state_field: lookup });
    },
    (err) => {
      assert.ok(
        err instanceof BadAuthoredValueError,
        `Expected BadAuthoredValueError, got ${err.name}`,
      );
      // Carries locating context.
      assert.ok(err.message.includes("test_proto"), "message must include protocol name");
      assert.ok(err.message.includes("step_a"), "message must include step name");
      assert.ok(err.message.includes("target_with_value"), "message must include validator kind");
      assert.ok(err.message.includes("some_obj"), "message must include target");
      assert.ok(err.message.includes("some_field"), "message must include field");
      // Carries declared type.
      assert.ok(err.message.includes("int"), "message must include declared type");
      return true;
    },
  );
});

test("Case 2b: typed int + malformed string throws BadAuthoredValueError (fsm)", () => {
  const config = make_config_fsm({
    authored_value: "high",
  });
  const lookup = always({ kind: "typed", field_type: "int" });
  assert.throws(
    () => {
      validate_authored_validator_values({ protocol_config: config, lookup_state_field: lookup });
    },
    (err) => {
      assert.ok(
        err instanceof BadAuthoredValueError,
        `Expected BadAuthoredValueError, got ${err.name}`,
      );
      assert.ok(err.message.includes("final_state_matches"), "message must include validator kind");
      return true;
    },
  );
});

//============================================
// Required Case 3: unknown-reference errors always throw
//============================================

test("Case 3a: unknown_object throws UnknownAuthoredObjectError (twv)", () => {
  const config = make_config_twv({ authored_value: "x" });
  const lookup = always({ kind: "unknown_object" });
  assert.throws(
    () => {
      validate_authored_validator_values({ protocol_config: config, lookup_state_field: lookup });
    },
    (err) => {
      assert.ok(
        err instanceof UnknownAuthoredObjectError,
        `Expected UnknownAuthoredObjectError, got ${err.name}`,
      );
      assert.ok(err.message.includes("test_proto"), "must include protocol name");
      assert.ok(err.message.includes("step_a"), "must include step name");
      assert.ok(err.message.includes("target_with_value"), "must include validator kind");
      assert.ok(err.message.includes("some_obj"), "must include target");
      assert.ok(err.message.includes("some_field"), "must include field");
      return true;
    },
  );
});

test("Case 3b: unknown_field throws UnknownAuthoredFieldError (twv)", () => {
  const config = make_config_twv({ authored_value: "x" });
  const lookup = always({ kind: "unknown_field" });
  assert.throws(
    () => {
      validate_authored_validator_values({ protocol_config: config, lookup_state_field: lookup });
    },
    (err) => {
      assert.ok(
        err instanceof UnknownAuthoredFieldError,
        `Expected UnknownAuthoredFieldError, got ${err.name}`,
      );
      assert.ok(err.message.includes("test_proto"));
      assert.ok(err.message.includes("step_a"));
      return true;
    },
  );
});

test("Case 3d: unknown_field throws UnknownAuthoredFieldError (fsm)", () => {
  const config = make_config_fsm({ authored_value: "x" });
  const lookup = always({ kind: "unknown_field" });
  assert.throws(
    () => {
      validate_authored_validator_values({ protocol_config: config, lookup_state_field: lookup });
    },
    (err) => {
      assert.ok(err instanceof UnknownAuthoredFieldError);
      assert.ok(err.message.includes("final_state_matches"), "must include validator kind");
      return true;
    },
  );
});

test("Case 3e: normal protocol + unknown_subpart throws with context", () => {
  // unknown_subpart must throw UnknownAuthoredSubpartError
  // and the error message must include the protocol name and step name.
  const config = make_config_twv({
    protocol_type: "mini_protocol",
    protocol_name: "test_proto",
    step_name: "step_a",
    authored_value: "x",
  });
  const lookup = always({ kind: "unknown_subpart" });
  assert.throws(
    () => {
      validate_authored_validator_values({ protocol_config: config, lookup_state_field: lookup });
    },
    (err) => {
      assert.ok(
        err instanceof UnknownAuthoredSubpartError,
        `Expected UnknownAuthoredSubpartError, got ${err.name}`,
      );
      assert.ok(err.message.includes("test_proto"), "must include protocol name");
      assert.ok(err.message.includes("step_a"), "must include step name");
      return true;
    },
  );
});

//============================================
// Required Case 4: valid cases pass
//============================================

test("Case 4a: typed int with finite numeric string passes (twv)", () => {
  const config = make_config_twv({ authored_value: "42" });
  const lookup = always({ kind: "typed", field_type: "int" });
  assert.doesNotThrow(() => {
    validate_authored_validator_values({ protocol_config: config, lookup_state_field: lookup });
  });
});

test("Case 4b: typed int with real number passes (twv)", () => {
  const config = make_config_twv({ authored_value: 42 });
  const lookup = always({ kind: "typed", field_type: "int" });
  assert.doesNotThrow(() => {
    validate_authored_validator_values({ protocol_config: config, lookup_state_field: lookup });
  });
});

test("Case 4c: typed float with finite numeric string passes (twv)", () => {
  const config = make_config_twv({ authored_value: "3.14" });
  const lookup = always({ kind: "typed", field_type: "float" });
  assert.doesNotThrow(() => {
    validate_authored_validator_values({ protocol_config: config, lookup_state_field: lookup });
  });
});

test("Case 4d: typed float with real number passes (twv)", () => {
  const config = make_config_twv({ authored_value: 3.14 });
  const lookup = always({ kind: "typed", field_type: "float" });
  assert.doesNotThrow(() => {
    validate_authored_validator_values({ protocol_config: config, lookup_state_field: lookup });
  });
});

test("numeric field rejects an authored value below its declared minimum", () => {
  const config = make_config_twv({ authored_value: 7.5 });
  const lookup = always({
    kind: "typed",
    field_type: "float",
    min: 20,
    max: 200,
    step: 1,
    unit: "ul",
  });
  assert.throws(
    () => {
      validate_authored_validator_values({ protocol_config: config, lookup_state_field: lookup });
    },
    (err) => {
      assert.ok(err instanceof BadAuthoredValueError);
      assert.ok(err.message.includes("below declared minimum 20 ul"));
      return true;
    },
  );
});

test("numeric field accepts an authored value within min max and step", () => {
  const config = make_config_twv({ authored_value: 7.5 });
  const lookup = always({
    kind: "typed",
    field_type: "float",
    min: 1,
    max: 10,
    step: 0.5,
    unit: "ul",
  });
  assert.doesNotThrow(() => {
    validate_authored_validator_values({ protocol_config: config, lookup_state_field: lookup });
  });
});

test("Case 4e: valid enum member string passes (twv)", () => {
  const config = make_config_twv({ authored_value: "open" });
  const lookup = always({ kind: "enum", allowed: ["open", "closed"] });
  assert.doesNotThrow(() => {
    validate_authored_validator_values({ protocol_config: config, lookup_state_field: lookup });
  });
});

test("Case 4f: valid material string passes (twv)", () => {
  const config = make_config_twv({ authored_value: "pbs_buffer" });
  const lookup = always({ kind: "material" });
  assert.doesNotThrow(() => {
    validate_authored_validator_values({ protocol_config: config, lookup_state_field: lookup });
  });
});

test("Case 4g: typed int with real number passes (fsm)", () => {
  const config = make_config_fsm({ authored_value: 7 });
  const lookup = always({ kind: "typed", field_type: "int" });
  assert.doesNotThrow(() => {
    validate_authored_validator_values({ protocol_config: config, lookup_state_field: lookup });
  });
});

test("Case 4h: valid enum member passes (fsm)", () => {
  const config = make_config_fsm({ authored_value: "closed" });
  const lookup = always({ kind: "enum", allowed: ["open", "closed"] });
  assert.doesNotThrow(() => {
    validate_authored_validator_values({ protocol_config: config, lookup_state_field: lookup });
  });
});

//============================================
// Additional required cases: bad bool, enum non-member, enum non-string, material non-string
//============================================

test("bad bool: string 'true' throws BadAuthoredValueError for typed bool field", () => {
  // The string "true" is not a real boolean; M1B-1 and this check both reject it.
  const config = make_config_twv({ authored_value: "true" });
  const lookup = always({ kind: "typed", field_type: "bool" });
  assert.throws(
    () => {
      validate_authored_validator_values({ protocol_config: config, lookup_state_field: lookup });
    },
    (err) => {
      assert.ok(
        err instanceof BadAuthoredValueError,
        `Expected BadAuthoredValueError, got ${err.name}`,
      );
      assert.ok(err.message.includes("bool"), "must mention declared type");
      return true;
    },
  );
});

test("bad bool: real boolean true passes for typed bool field", () => {
  const config = make_config_twv({ authored_value: true });
  const lookup = always({ kind: "typed", field_type: "bool" });
  assert.doesNotThrow(() => {
    validate_authored_validator_values({ protocol_config: config, lookup_state_field: lookup });
  });
});

test("enum non-membership: value not in allowed set throws BadAuthoredValueError", () => {
  const config = make_config_twv({ authored_value: "half_open" });
  const lookup = always({ kind: "enum", allowed: ["open", "closed"] });
  assert.throws(
    () => {
      validate_authored_validator_values({ protocol_config: config, lookup_state_field: lookup });
    },
    (err) => {
      assert.ok(
        err instanceof BadAuthoredValueError,
        `Expected BadAuthoredValueError, got ${err.name}`,
      );
      assert.ok(err.message.includes("enum"), "must mention declared type");
      return true;
    },
  );
});

test("enum null allowed: any string passes when allowed is null (open enum)", () => {
  const config = make_config_twv({ authored_value: "anything_goes" });
  const lookup = always({ kind: "enum", allowed: null });
  assert.doesNotThrow(() => {
    validate_authored_validator_values({ protocol_config: config, lookup_state_field: lookup });
  });
});

test("enum non-string: number authored value for enum field throws BadAuthoredValueError", () => {
  const config = make_config_twv({ authored_value: 42 });
  const lookup = always({ kind: "enum", allowed: ["open", "closed"] });
  assert.throws(
    () => {
      validate_authored_validator_values({ protocol_config: config, lookup_state_field: lookup });
    },
    (err) => {
      assert.ok(
        err instanceof BadAuthoredValueError,
        `Expected BadAuthoredValueError, got ${err.name}`,
      );
      return true;
    },
  );
});

test("material non-string: number authored value for material field throws BadAuthoredValueError", () => {
  const config = make_config_twv({ authored_value: 99 });
  const lookup = always({ kind: "material" });
  assert.throws(
    () => {
      validate_authored_validator_values({ protocol_config: config, lookup_state_field: lookup });
    },
    (err) => {
      assert.ok(
        err instanceof BadAuthoredValueError,
        `Expected BadAuthoredValueError, got ${err.name}`,
      );
      assert.ok(err.message.includes("material"), "must mention declared type");
      return true;
    },
  );
});

//============================================
// Error name (instanceof double-check via .name)
//============================================

test("error class names match: UnknownAuthoredObjectError.name", () => {
  const config = make_config_twv({ authored_value: "x" });
  const lookup = always({ kind: "unknown_object" });
  assert.throws(
    () => {
      validate_authored_validator_values({ protocol_config: config, lookup_state_field: lookup });
    },
    (err) => {
      assert.strictEqual(err.name, "UnknownAuthoredObjectError");
      return true;
    },
  );
});

test("error class names match: UnknownAuthoredSubpartError.name", () => {
  const config = make_config_twv({ authored_value: "x" });
  const lookup = always({ kind: "unknown_subpart" });
  assert.throws(
    () => {
      validate_authored_validator_values({ protocol_config: config, lookup_state_field: lookup });
    },
    (err) => {
      assert.ok(
        err instanceof UnknownAuthoredSubpartError,
        `Expected UnknownAuthoredSubpartError, got ${err.name}`,
      );
      assert.strictEqual(err.name, "UnknownAuthoredSubpartError");
      return true;
    },
  );
});

test("error class names match: UnknownAuthoredFieldError.name", () => {
  const config = make_config_twv({ authored_value: "x" });
  const lookup = always({ kind: "unknown_field" });
  assert.throws(
    () => {
      validate_authored_validator_values({ protocol_config: config, lookup_state_field: lookup });
    },
    (err) => {
      assert.strictEqual(err.name, "UnknownAuthoredFieldError");
      return true;
    },
  );
});

test("error class names match: BadAuthoredValueError.name", () => {
  const config = make_config_twv({ authored_value: "high" });
  const lookup = always({ kind: "typed", field_type: "int" });
  assert.throws(
    () => {
      validate_authored_validator_values({ protocol_config: config, lookup_state_field: lookup });
    },
    (err) => {
      assert.strictEqual(err.name, "BadAuthoredValueError");
      return true;
    },
  );
});
