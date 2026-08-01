import { readFileSync } from "node:fs";

const pkgPath = new URL("../package.json", import.meta.url);
const pkg = JSON.parse(readFileSync(pkgPath, "utf8"));

if ("__metadata" in pkg) {
  process.stderr.write(
    "vscode/package.json contains a __metadata block; remove it before committing.\n",
  );
  process.exit(1);
}
