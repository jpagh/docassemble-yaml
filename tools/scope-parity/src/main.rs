//! Candidate side of the scope-parity test.
//!
//! Loads the generated Fresh grammar into syntect (exactly what Fresh does at
//! runtime) and prints the per-character highlight category of a fixture,
//! using the shared `categories.json` mapping. `node/tokenize.mjs` prints the
//! same shape from the original VS Code TextMate grammars; `compare.py`
//! diffs the two.
//!
//! Usage: scope-parity <grammar.sublime-syntax> <fixture> <categories.json>

use std::path::Path;

use serde::Deserialize;
use serde_json::json;
use syntect::parsing::{
    ClearAmount, ParseState, ScopeStack, ScopeStackOp, SyntaxDefinition, SyntaxSet,
    SyntaxSetBuilder,
};

#[derive(Deserialize)]
struct Categories {
    embedded: Vec<Embedded>,
    rules: Vec<Rule>,
}

#[derive(Deserialize)]
struct Embedded {
    scope: String,
    category: String,
}

#[derive(Deserialize)]
struct Rule {
    prefix: String,
    category: String,
}

fn category<'a>(stack: &[String], categories: &'a Categories) -> &'a str {
    // Embedded languages are normalised to a single category: the grammar
    // under test decides where Python/JS/HTML starts and stops, but the
    // internals of those grammars belong to syntect, not to this project.
    for embedded in categories.embedded.iter().rev() {
        let scope = &embedded.scope;
        if stack
            .iter()
            .any(|s| s == scope || s.starts_with(&format!("{scope}.")))
        {
            return &embedded.category;
        }
    }
    for scope in stack.iter().rev() {
        for rule in &categories.rules {
            if scope.starts_with(&rule.prefix) {
                return &rule.category;
            }
        }
    }
    "other"
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 4 {
        eprintln!("usage: scope-parity <grammar.sublime-syntax> <fixture> <categories.json>");
        std::process::exit(2);
    }
    let (grammar_path, fixture_path, categories_path) = (&args[1], &args[2], &args[3]);

    let categories: Categories =
        serde_json::from_str(&std::fs::read_to_string(categories_path).expect("categories.json"))
            .expect("parse categories.json");

    let mut builder: SyntaxSetBuilder = SyntaxSet::load_defaults_newlines().into_builder();
    let source = std::fs::read_to_string(grammar_path).expect("grammar file");
    let syntax = SyntaxDefinition::load_from_str(&source, true, Some("docassemble"))
        .expect("generated grammar must parse");
    builder.add(syntax);
    let syntax_set = builder.build();
    let syntax = syntax_set.syntaxes().last().unwrap();

    let text = std::fs::read_to_string(fixture_path).expect("fixture");
    let mut state = ParseState::new(syntax);
    let mut stack = ScopeStack::new();
    let mut lines = Vec::new();

    for (index, line) in text.split_inclusive('\n').enumerate() {
        let ops = state.parse_line(line, &syntax_set).expect("parse line");

        // Replay the ops byte by byte so each byte position gets the scope
        // stack that was active there.
        let mut active = stack.clone();
        let mut contexts: Vec<Vec<String>> = Vec::with_capacity(line.len() + 1);
        let mut pending = ops.iter().peekable();
        for position in 0..=line.len() {
            while let Some((offset, _)) = pending.peek() {
                if *offset != position {
                    break;
                }
                let (_, op) = pending.next().unwrap();
                match op {
                    ScopeStackOp::Push(scope) => active.push(*scope),
                    ScopeStackOp::Pop(count) => {
                        for _ in 0..*count {
                            active.pop();
                        }
                    }
                    ScopeStackOp::Clear(amount) => match amount {
                        ClearAmount::TopN(count) => {
                            for _ in 0..*count {
                                active.pop();
                            }
                        }
                        ClearAmount::All => active = ScopeStack::new(),
                    },
                    _ => {}
                }
            }
            contexts.push(
                active
                    .as_slice()
                    .iter()
                    .map(|scope| scope.to_string())
                    .collect(),
            );
        }

        // Collapse equal neighbouring categories into runs.
        let mut runs: Vec<(usize, usize, &str)> = Vec::new();
        for (position, scopes) in contexts.iter().take(line.len()).enumerate() {
            let current = category(scopes, &categories);
            match runs.last_mut() {
                Some((_, end, previous)) if *previous == current && *end == position => {
                    *end = position + 1;
                }
                _ => runs.push((position, position + 1, current)),
            }
        }

        lines.push(json!({
            "line": index + 1,
            "text": line.trim_end_matches('\n'),
            "runs": runs
                .iter()
                .map(|(start, end, category)| json!([start, end, category]))
                .collect::<Vec<_>>(),
        }));

        for (_, op) in ops {
            stack.apply(&op).expect("scope op applies");
        }
    }

    println!(
        "{}",
        serde_json::to_string(&json!({
            "engine": "syntect",
            "grammar": Path::new(grammar_path)
                .file_name()
                .map(|name| name.to_string_lossy().into_owned())
                .unwrap_or_default(),
            "lines": lines,
        }))
        .unwrap()
    );
}
