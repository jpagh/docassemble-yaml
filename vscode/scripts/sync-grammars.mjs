// VS Code owns these real-file packaging copies, not the canonical sources.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export function syncGrammars(source, destination, { check = false } = {}) {
  for (const name of fs.readdirSync(source).filter((name) => name.endsWith(".json"))) {
    const expected = fs.readFileSync(new URL(name, source));
    const target = path.join(destination, name);
    if (check) {
      if (!fs.existsSync(target) || !fs.readFileSync(target).equals(expected)) {
        throw new Error(`${target} is stale; run mise run //vscode:grammar:sync`);
      }
    } else {
      fs.mkdirSync(destination, { recursive: true });
      fs.writeFileSync(target, expected);
    }
  }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  syncGrammars(
    new URL("../../grammars/textmate/", import.meta.url),
    fileURLToPath(new URL("../syntaxes/", import.meta.url)),
    { check: process.argv.includes("--check") },
  );
}
