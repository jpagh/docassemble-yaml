import assert from "node:assert/strict";
import { test } from "node:test";
import { parsePyproject } from "./pyproject-utils.mjs";

test("parsePyproject reads project version and preserves dependency markers", () => {
  const pyproject = `
[project]
version = "26.7.0"
dependencies = [
  "docassemble-base>=1.9.12",
  "tomli>=2.0.0; python_version < \\"3.11\\"",
  "ruamel.yaml>=0.18.0",
]
`;

  const { version, deps } = parsePyproject(pyproject);

  assert.equal(version, "26.7.0");
  assert.equal(deps.length, 3);
  assert.equal(deps[0], "docassemble-base>=1.9.12");
  assert.equal(deps[1], 'tomli>=2.0.0; python_version < "3.11"');
});
