// Direct shipped TextMate tokenizer; compatibility parity is explicit opt-in.
//
// Tokenizes the fixture with the original VS Code TextMate grammars and
// their injection selectors (vscode-textmate, the same engine VS Code uses),
// then prints the per-character highlight category using the shared
// `categories.json`. `src/main.rs` prints the same shape from syntect, and
// `compare.py` diffs the two.
//
// Usage: node tokenize.mjs <fixture> <categories.json> [--scopes] [--compatibility-reference]

import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

import vsOnigPkg from "vscode-oniguruma";
import textmatePkg from "vscode-textmate";
import { patchReferenceRule } from "./compatibility-reference.mjs";

const vsOnig = vsOnigPkg.default ?? vsOnigPkg;
const { Registry, parseRawGrammar } = textmatePkg;

const require = createRequire(import.meta.url);
const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, "..", "..", "..");
const compatibilityReference = process.argv.includes("--compatibility-reference");
const manifest = JSON.parse(fs.readFileSync(path.join(repoRoot, "vscode", "package.json"), "utf8"));

const args = process.argv
  .slice(2)
  .filter((arg) => !["--scopes", "--compatibility-reference"].includes(arg));
const scopesMode = process.argv.includes("--scopes");
const [fixturePath, categoriesPath] = args;
if (!fixturePath || !categoriesPath) {
  console.error(
    "usage: node tokenize.mjs <fixture> <categories.json> [--scopes] [--compatibility-reference]",
  );
  process.exit(2);
}

const categories = JSON.parse(fs.readFileSync(categoriesPath, "utf8"));

function categoryFor(stack) {
  // Embedded languages collapse to one category; see src/main.rs.
  for (let i = categories.embedded.length - 1; i >= 0; i--) {
    const { scope, category } = categories.embedded[i];
    if (stack.some((s) => s === scope || s.startsWith(`${scope}.`))) {
      return category;
    }
  }
  for (let i = stack.length - 1; i >= 0; i--) {
    for (const rule of categories.rules) {
      if (stack[i].startsWith(rule.prefix)) {
        return rule.category;
      }
    }
  }
  return "other";
}

// Our own grammars must come from the repo, not from tm-grammars: they are
// what the converter consumes.
const ownGrammars = new Map(
  manifest.contributes.grammars.map(({ scopeName, path: grammarPath }) => [
    scopeName,
    compatibilityReference
      ? path.join(repoRoot, "grammars", "textmate", path.basename(grammarPath))
      : path.resolve(repoRoot, "vscode", grammarPath),
  ]),
);

// Everything else (source.python, source.js, text.html.basic, ...) comes
// from tm-grammars, so the reference resolves the same cross-grammar
// includes the candidate does.
const tmGrammarIndex = new Map();
function indexTmGrammars() {
  const grammarsDir = path.dirname(require.resolve("tm-grammars/grammars/python.json"));
  for (const entry of fs.readdirSync(grammarsDir)) {
    if (!entry.endsWith(".json")) continue;
    const file = path.join(grammarsDir, entry);
    try {
      const raw = JSON.parse(fs.readFileSync(file, "utf8"));
      if (raw.scopeName && !tmGrammarIndex.has(raw.scopeName)) {
        tmGrammarIndex.set(raw.scopeName, file);
      }
    } catch {
      // Ignore unparsable extras; they are not part of any dependency graph
      // we exercise.
    }
  }
}

const INJECTIONS = {};
for (const { scopeName, injectTo = [] } of manifest.contributes.grammars) {
  for (const target of injectTo) (INJECTIONS[target] ??= []).push(scopeName);
}

function loadRawGrammar(scopeName) {
  const own = ownGrammars.get(scopeName);
  if (own) {
    const text = fs.readFileSync(own, "utf8");
    if (!compatibilityReference) return parseRawGrammar(text, own);
    const raw = JSON.parse(text);
    patchReferenceRule(raw);
    return parseRawGrammar(JSON.stringify(raw), own);
  }
  const file = tmGrammarIndex.get(scopeName);
  if (file) return parseRawGrammar(fs.readFileSync(file, "utf8"), file);
  return undefined;
}

async function main() {
  indexTmGrammars();
  const wasm = fs.readFileSync(require.resolve("vscode-oniguruma/release/onig.wasm"));
  await vsOnig.loadWASM(wasm.buffer);
  const onigLib = Promise.resolve({
    createOnigScanner: vsOnig.createOnigScanner,
    createOnigString: vsOnig.createOnigString,
  });

  const registry = new Registry({
    onigLib,
    loadGrammar: async (scopeName) => loadRawGrammar(scopeName),
    getInjections: (scopeName) => INJECTIONS[scopeName],
  });

  // Load the injection grammars first: `getInjections` only records their
  // scope names, and `Grammar._collectInjections` resolves them through the
  // raw-grammar repository, which needs them loaded.
  for (const scope of INJECTIONS["source.docassemble.yaml"]) {
    await registry.loadGrammar(scope);
  }

  const grammar = await registry.loadGrammar("source.docassemble.yaml");
  if (!grammar) throw new Error("failed to load source.docassemble.yaml");

  const text = fs.readFileSync(fixturePath, "utf8");
  const lines = [];
  let ruleStack = null;
  let index = 0;
  const rawLines = text.split("\n");
  // `String.split` yields a trailing empty line for a file that ends in a
  // newline; syntect's `split_inclusive` does not. Drop it so both sides
  // tokenize the same number of lines.
  if (rawLines[rawLines.length - 1] === "") rawLines.pop();
  for (const line of rawLines) {
    index += 1;
    const withNewline = index === rawLines.length ? line : line + "\n";
    const result = grammar.tokenizeLine(withNewline, ruleStack);
    ruleStack = result.ruleStack;

    if (scopesMode) {
      lines.push({
        line: index,
        text: line,
        tokens: result.tokens.map((token) => ({
          start: token.startIndex,
          end: token.endIndex,
          scopes: token.scopes,
        })),
      });
      continue;
    }

    const runs = [];
    for (const token of result.tokens) {
      const category = categoryFor(token.scopes);
      const previous = runs[runs.length - 1];
      if (previous && previous[1] === token.startIndex && previous[2] === category) {
        previous[1] = token.endIndex;
      } else {
        runs.push([token.startIndex, token.endIndex, category]);
      }
    }
    lines.push({ line: index, text: line, runs });
  }

  process.stdout.write(
    JSON.stringify({
      engine: "vscode-textmate",
      referenceMode: compatibilityReference ? "compatibility" : "shipped",
      lines,
    }) + "\n",
  );
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
