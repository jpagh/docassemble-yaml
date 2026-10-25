import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const here = new URL("../", import.meta.url);
const corpus = JSON.parse(fs.readFileSync(new URL("fixtures.json", here)));
for (const fixture of corpus.canonical) {
  test(`shipped categories cover ${fixture} in native UTF-16 units`, () => {
    const result = JSON.parse(execFileSync(process.execPath, [
      fileURLToPath(new URL("node/tokenize.mjs", here)),
      fileURLToPath(new URL(`../../grammars/fixtures/${fixture}`, here)),
      fileURLToPath(new URL("categories.json", here)),
    ], { encoding: "utf8" }));
    assert.equal(result.referenceMode, "shipped");
    assert.equal(result.offsetUnit, "utf16");
    for (const { text, runs } of result.lines) {
      let previous = 0;
      for (const [start, end] of runs) {
        assert.equal(start, previous);
        assert.ok(end > start && end <= text.length);
        previous = end;
      }
      assert.equal(previous, text.length);
    }
    const categoryAt = (text, needle) => {
      const line = result.lines.find((line) => line.text.includes(text));
      const column = line.text.indexOf(needle);
      return line.runs.find(([start, end]) => start <= column && column < end)[2];
    };
    assert.equal(categoryAt("metadata:", "metadata"), "tag");
    if (fixture === "regions.yml") {
      assert.equal(categoryAt("After code", "question"), "tag");
      assert.equal(categoryAt("After condition", "question"), "tag");
      assert.equal(categoryAt("After template dedent", "help"), "tag");
      assert.equal(categoryAt("back in YAML", "plain"), "tag");
      assert.equal(categoryAt("{{ user_name }}", "user_name"), "variable");
      assert.equal(categoryAt("Mako comment across", "Mako"), "comment");
    }
    if (fixture === "unicode.yml") {
      assert.equal(categoryAt("résultat }}", "résultat"), "variable");
      assert.equal(categoryAt("Après 😀", "question"), "tag");
      assert.equal(categoryAt("fin é", "plain"), "tag");
      const line = result.lines.find((line) => line.text.includes("${ prénom }"));
      assert.notEqual(line.text.length, [...line.text].length);
      assert.notEqual(Buffer.byteLength(line.text), line.text.length);
    }
  });
}
