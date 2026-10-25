import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

const tokenizer = fileURLToPath(new URL("./tokenize.mjs", import.meta.url));
const fixture = fileURLToPath(new URL("../../../grammars/fixtures/sample.yml", import.meta.url));
const categories = fileURLToPath(new URL("../categories.json", import.meta.url));

function tokenize(...options) {
  return JSON.parse(
    execFileSync(process.execPath, [tokenizer, fixture, categories, "--scopes", ...options], {
      encoding: "utf8",
    }),
  );
}

test("compatibility-reference rewrites are opt-in and distinct from shipped behavior", () => {
  const shipped = tokenize();
  const reference = tokenize("--compatibility-reference");
  assert.equal(reference.referenceMode, "compatibility");
  assert.notDeepEqual(reference.lines, shipped.lines);
});
