import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const tokenizer = fileURLToPath(new URL("./tokenize.mjs", import.meta.url));
const fixture = fileURLToPath(new URL("../../../grammars/fixtures/sample.yml", import.meta.url));
const categories = fileURLToPath(new URL("../categories.json", import.meta.url));

export function tokenize(...options) {
  return JSON.parse(
    execFileSync(process.execPath, [tokenizer, fixture, categories, "--scopes", ...options], {
      encoding: "utf8",
    }),
  );
}
