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

test("shipped TextMate grammars tokenize the shared corpus without compatibility rewrites", () => {
  const result = tokenize();
  assert.equal(result.referenceMode, "shipped");
  assert.equal(result.lines.length, 46);
  const scopesAt = (line, column) =>
    result.lines[line - 1].tokens.find((token) => token.start <= column && token.end > column)
      .scopes;
  assert.ok(scopesAt(2, 0).includes("comment.line.number-sign.yaml"));
  assert.ok(scopesAt(7, 12).includes("string.quoted.double.yaml"));
  assert.ok(scopesAt(8, 9).includes("constant.numeric.integer.yaml"));
  assert.ok(scopesAt(14, 10).includes("source.mako.expression"));
  assert.ok(scopesAt(16, 10).includes("comment.block.mako"));
  assert.ok(scopesAt(17, 6).includes("variable.other.jinja"));
  assert.ok(scopesAt(24, 19).includes("keyword.operator.logical.python"));
  // Existing shipped limitation: block bodies are not the patched reference.
  assert.deepEqual(scopesAt(20, 4), [
    "source.docassemble.yaml",
    "unquoted.plain.out.yaml",
    "entity.name.tag.yaml",
  ]);
});
