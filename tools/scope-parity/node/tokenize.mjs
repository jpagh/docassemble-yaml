// Reference side of the scope-parity test.
//
// Tokenizes the fixture with the original VS Code TextMate grammars and
// their injection selectors (vscode-textmate, the same engine VS Code uses),
// then prints the per-character highlight category using the shared
// `categories.json`. `src/main.rs` prints the same shape from syntect, and
// `compare.py` diffs the two.
//
// Usage: node tokenize.mjs <fixture> <categories.json>

import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

import vsOnigPkg from "vscode-oniguruma";
import textmatePkg from "vscode-textmate";

const vsOnig = vsOnigPkg.default ?? vsOnigPkg;
const { Registry, parseRawGrammar } = textmatePkg;

const require = createRequire(import.meta.url);
const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, "..", "..", "..");
const syntaxes = path.join(repoRoot, "vscode", "syntaxes");

const args = process.argv.slice(2).filter((arg) => arg !== "--scopes");
const scopesMode = process.argv.includes("--scopes");
const [fixturePath, categoriesPath] = args;
if (!fixturePath || !categoriesPath) {
  console.error("usage: node tokenize.mjs <fixture> <categories.json>");
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
  [
    ["source.docassemble.yaml", "yaml.tmLanguage.json"],
    ["source.mako", "mako.tmLanguage.json"],
    ["source.jinja", "jinja.tmLanguage.json"],
    ["python.injection", "python-injection.json"],
    ["mako.injection", "mako-injection.json"],
    ["jinja.injection", "jinja-injection.json"],
  ].map(([scope, file]) => [scope, path.join(syntaxes, file)]),
);

// Everything else (source.python, source.js, text.html.basic, ...) comes
// from tm-grammars, so the reference resolves the same cross-grammar
// includes the candidate does.
const tmGrammarIndex = new Map();
function indexTmGrammars() {
  const grammarsDir = path.dirname(
    require.resolve("tm-grammars/grammars/python.json"),
  );
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

const INJECTIONS = {
  "source.docassemble.yaml": [
    "python.injection",
    "mako.injection",
    "jinja.injection",
  ],
};

// vscode-textmate loses the TextMate `\\G` anchor at a line boundary, so the
// idiom `end: "^(?=\\S)|(?!\\G)"` (block scalar bodies, the Python
// `code:`/`show if:`/`script:` injections) pops at the first character of the
// following line instead of holding the region open.  The converter lowers
// those rules into match/push contexts where syntect keeps the region open,
// so the reference applies this narrow, documented rewrite to compare against
// the grammar's intent rather than that engine artifact.
const RULE_REWRITES = [
  {
    // TextMate `\\G` anchors to the end of the previous match, which holds
    // across a line boundary; vscode-textmate resets it per line, so the
    // region pops at the first character of the next line.
    field: "end",
    from: "^(?=\\S)|(?!\\G)",
    to: "^(?=\\S)",
  },
  {
    field: "end",
    from: "(?=\\S)|(?!\\G)",
    to: "(?=\\S)",
  },
  {
    // The end of these indentation-delimited regions back-references a
    // capture from a zero-width lookahead begin; vscode-oniguruma does not
    // return that group, so `\\1` resolves to the empty string and the
    // region never ends.  Consuming the indentation (as the upstream YAML
    // grammar does) records the capture.
    field: "begin",
    from: "^(?=([ ]+)(?! ))",
    to: "^([ ]+)(?! )",
  },
];

function patchReferenceRule(rule) {
  if (!rule || typeof rule !== "object") return;
  for (const rewrite of RULE_REWRITES) {
    if (rule[rewrite.field] === rewrite.from) rule[rewrite.field] = rewrite.to;
  }
  // The docassemble fork wraps block-scalar bodies in `source.mako`; the
  // wrapper never engages under vscode-textmate (it only ever coloured the
  // body as unscoped text) and its injected context then traps the
  // `code:`/`if:` injections inside the scalar.  Restore the upstream
  // `string.unquoted.block.yaml` body; Mako still reaches the content
  // through its injection.
  if (rule.name === "source.mako" && rule.patterns) {
    rule.name = "string.unquoted.block.yaml";
    delete rule.patterns;
  }
  for (const child of Object.values(rule)) {
    if (Array.isArray(child)) child.forEach(patchReferenceRule);
    else if (child && typeof child === "object") patchReferenceRule(child);
  }
}

function loadRawGrammar(scopeName) {
  const own = ownGrammars.get(scopeName);
  if (own) {
    const raw = JSON.parse(fs.readFileSync(own, "utf8"));
    patchReferenceRule(raw);
    return parseRawGrammar(JSON.stringify(raw), own);
  }
  const file = tmGrammarIndex.get(scopeName);
  if (file) return parseRawGrammar(fs.readFileSync(file, "utf8"), file);
  return undefined;
}

async function main() {
  indexTmGrammars();
  const wasm = fs.readFileSync(
    require.resolve("vscode-oniguruma/release/onig.wasm"),
  );
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
      if (
        previous &&
        previous[1] === token.startIndex &&
        previous[2] === category
      ) {
        previous[1] = token.endIndex;
      } else {
        runs.push([token.startIndex, token.endIndex, category]);
      }
    }
    lines.push({ line: index, text: line, runs });
  }

  process.stdout.write(
    JSON.stringify({ engine: "vscode-textmate", lines }) + "\n",
  );
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
