import assert from "node:assert/strict";
import { test } from "node:test";
import { tokenize } from "./tokenize-test-helper.mjs";

test("compatibility-reference rewrites are opt-in and distinct from shipped behavior", () => {
  const shipped = tokenize();
  const reference = tokenize("--compatibility-reference");
  assert.equal(reference.referenceMode, "compatibility");
  assert.notDeepEqual(reference.lines, shipped.lines);
});
