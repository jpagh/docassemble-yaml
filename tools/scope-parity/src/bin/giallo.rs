//! Canonical-rule giallo leg: metadata adaptation only, never reference rewrites.
use std::path::Path;

use giallo::{HighlightOptions, Registry, ThemeVariant};
use scope_parity::Categories;
use serde_json::{json, Value};

fn main() {
    let args: Vec<String> = std::env::args().collect();
    assert_eq!(
        args.len(),
        5,
        "usage: giallo <canonical-grammar-dir> <fixture> <categories.json> <work-dir>"
    );
    let categories: Categories =
        serde_json::from_str(&std::fs::read_to_string(&args[3]).unwrap()).unwrap();
    let work = Path::new(&args[4]);
    let mut registry = Registry::builtin().expect("giallo builtin registry");
    let mut paths: Vec<_> = std::fs::read_dir(&args[1])
        .unwrap()
        .map(|p| p.unwrap().path())
        .collect();
    paths.sort();
    for path in paths {
        if path.extension().is_none_or(|ext| ext != "json") {
            continue;
        }
        let mut grammar: Value =
            serde_json::from_str(&std::fs::read_to_string(&path).unwrap()).unwrap();
        let stem = path.file_stem().unwrap().to_str().unwrap();
        let injection = stem.ends_with("-injection");
        grammar["name"] = json!(if path.file_name().unwrap() == "yaml.tmLanguage.json" {
            "docassemble".to_owned()
        } else if injection {
            format!("docassemble-{stem}")
        } else {
            format!("docassemble-{}", stem.split('.').next().unwrap())
        });
        // giallo links external injections by target grammar NAME, not scope.
        if injection {
            grammar["injectTo"] = json!(["docassemble"]);
        }
        let target = work.join(path.file_name().unwrap());
        std::fs::write(&target, serde_json::to_vec(&grammar).unwrap()).unwrap();
        registry
            .add_grammar_from_path(target)
            .expect("metadata-adapted canonical grammar");
    }
    registry.link_grammars();

    let diagnostic = scope_parity::DiagnosticTheme::new(&categories);
    let theme = work.join("categories-theme.json");
    std::fs::write(&theme, serde_json::to_vec(&diagnostic.theme).unwrap()).unwrap();
    registry.add_theme_from_path(theme).unwrap();
    let source = std::fs::read_to_string(&args[2]).unwrap();
    let options = HighlightOptions::new("docassemble", ThemeVariant::Single("categories"))
        .merge_same_style_tokens(false)
        .merge_whitespace(false);
    let highlighted = registry
        .highlight(&source, &options)
        .expect("giallo highlight");
    let raw_lines: Vec<_> = source.split_inclusive('\n').collect();
    assert_eq!(
        raw_lines.len() + usize::from(source.ends_with('\n')),
        highlighted.tokens.len(),
        "line count (giallo retains trailing empty line)"
    );
    let mut lines = Vec::new();
    for (index, (raw, tokens)) in raw_lines.iter().zip(&highlighted.tokens).enumerate() {
        let text = raw.trim_end_matches('\n');
        let mut restored = String::new();
        let mut runs = Vec::new();
        for token in tokens {
            let start = restored.len();
            restored.push_str(&token.text);
            let ThemeVariant::Single(style) = token.style else {
                unreachable!()
            };
            let category = diagnostic.decode(style);
            let end = restored.len().min(text.len());
            if start < end {
                runs.push(json!([start, end, category]));
            }
        }
        assert_eq!(
            restored.trim_end_matches('\n'),
            text,
            "token text reconstruction"
        );
        lines.push(json!({"line": index + 1, "text": text, "runs": runs}));
    }
    println!(
        "{}",
        json!({"engine": "giallo", "version": "0.5.2", "offsetUnit": "utf8", "transformations": ["name/injectTo metadata only"], "lines": lines})
    );
}
