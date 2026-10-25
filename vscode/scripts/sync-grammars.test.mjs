import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { test } from "node:test";
import { syncGrammars } from "./sync-grammars.mjs";

const sources = new URL("../../grammars/textmate/", import.meta.url);

test("VS Code packages byte-identical shared grammars and keeps injection registration", () => {
  const manifest = JSON.parse(fs.readFileSync(new URL("../package.json", import.meta.url)));
  const grammars = manifest.contributes.grammars;
  assert.deepEqual(
    grammars.map(({ scopeName }) => scopeName),
    [
      "source.docassemble.yaml",
      "source.jinja",
      "source.mako",
      "python.injection",
      "mako.injection",
      "jinja.injection",
    ],
  );
  for (const grammar of grammars) {
    assert.deepEqual(
      fs.readFileSync(new URL(grammar.path, new URL("../", import.meta.url))),
      fs.readFileSync(new URL(path.basename(grammar.path), sources)),
    );
    if (grammar.scopeName.endsWith(".injection")) {
      assert.deepEqual(grammar.injectTo, ["source.docassemble.yaml"]);
    }
  }
  assert.equal(grammars.length, fs.readdirSync(sources).length);
});

test("grammar packaging detects stale or missing files without rewriting them", (t) => {
  const destination = fs.mkdtempSync(path.join(os.tmpdir(), "grammar-packaging-"));
  t.after(() => fs.rmSync(destination, { recursive: true, force: true }));
  assert.throws(() => syncGrammars(sources, destination, { check: true }), /stale/);
  syncGrammars(sources, destination);
  syncGrammars(sources, destination, { check: true });
  const file = path.join(destination, "yaml.tmLanguage.json");
  fs.writeFileSync(file, "stale");
  assert.throws(() => syncGrammars(sources, destination, { check: true }), /stale/);
  assert.equal(fs.readFileSync(file, "utf8"), "stale");
  syncGrammars(sources, destination);
  assert.deepEqual(fs.readFileSync(file), fs.readFileSync(new URL(path.basename(file), sources)));
});
