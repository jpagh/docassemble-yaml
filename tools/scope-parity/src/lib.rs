use serde::Deserialize;
use serde_json::json;

#[derive(Deserialize)]
pub struct Categories {
    pub embedded: Vec<Embedded>,
    pub rules: Vec<Rule>,
}

#[derive(Deserialize)]
pub struct Embedded {
    pub scope: String,
    pub category: String,
}

#[derive(Deserialize)]
pub struct Rule {
    pub prefix: String,
    pub category: String,
}

pub fn category<'a>(stack: &[String], categories: &'a Categories) -> &'a str {
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

/// Diagnostic colours are an adapter for giallo's public styles-only API.
pub struct DiagnosticTheme {
    pub colors: std::collections::BTreeMap<String, String>,
    pub theme: serde_json::Value,
}

impl DiagnosticTheme {
    pub fn new(categories: &Categories) -> Self {
        // Foreground encodes the innermost matching category rule. Background is a
        // separate channel for embedded-language scopes, which override ALL inner
        // foreground rules in the shared reduction (Python strings stay Python).
        let mut names = vec!["other".to_owned()];
        names.extend(categories.rules.iter().map(|r| r.category.clone()));
        names.extend(categories.embedded.iter().map(|r| r.category.clone()));
        names.sort();
        names.dedup();
        let colors: std::collections::BTreeMap<_, _> = names
            .iter()
            .enumerate()
            .map(|(i, n)| (n.as_str(), format!("#{:06X}", i + 1)))
            .collect();
        let mut rules = Vec::new();
        // Reverse because the first matching rule in categories.json wins ties.
        for rule in categories.rules.iter().rev() {
            rules.push(json!({"scope": rule.prefix.trim_end_matches('.'), "settings": {"foreground": colors[rule.category.as_str()]}}));
        }
        for embedded in &categories.embedded {
            rules.push(json!({"scope": embedded.scope, "settings": {"background": colors[embedded.category.as_str()]}}));
        }
        let theme = json!({
            "name": "categories", "colors": {"editor.foreground": colors["other"], "editor.background": colors["other"]},
            "tokenColors": rules
        });
        Self {
            colors: colors
                .into_iter()
                .map(|(key, value)| (key.to_owned(), value))
                .collect(),
            theme,
        }
    }

    pub fn decode(&self, style: giallo::Style) -> &str {
        let color = if style.background.as_hex() != self.colors["other"] {
            style.background
        } else {
            style.foreground
        }
        .as_hex();
        self.colors
            .iter()
            .find(|(_, value)| **value == color)
            .expect("unrecognized diagnostic colour")
            .0
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use giallo::{HighlightOptions, Registry, ThemeVariant};

    #[test]
    fn diagnostic_theme_inverts_all_categories_and_detects_wrong_colors() {
        let categories: Categories =
            serde_json::from_str(include_str!("../categories.json")).unwrap();
        let diagnostic = DiagnosticTheme::new(&categories);
        let distinct: std::collections::BTreeSet<_> = diagnostic.colors.values().collect();
        assert_eq!(
            distinct.len(),
            diagnostic.colors.len(),
            "unambiguous inversion"
        );
        let mut stacks = vec![vec!["unmatched.scope".to_owned()]];
        for rule in &categories.rules {
            stacks.push(vec![format!("{}.probe", rule.prefix.trim_end_matches('.'))]);
            // Inner rule must override a matching outer string scope.
            stacks.push(vec![
                "string.quoted.outer".to_owned(),
                format!("{}.probe", rule.prefix.trim_end_matches('.')),
            ]);
        }
        for embedded in &categories.embedded {
            stacks.push(vec![
                embedded.scope.clone(),
                "string.quoted.inner".to_owned(),
            ]);
            stacks.push(vec![
                format!("{}.probe", embedded.scope),
                "comment.inner".to_owned(),
            ]);
        }
        let expected: Vec<_> = stacks
            .iter()
            .map(|stack| category(stack, &categories))
            .collect();
        let observed_categories: std::collections::BTreeSet<_> = expected.iter().copied().collect();
        assert_eq!(
            observed_categories.len(),
            diagnostic.colors.len(),
            "probe every category"
        );
        let patterns: Vec<_> = stacks
            .iter()
            .enumerate()
            .map(|(i, stack)| json!({"match": format!("probe{i}x"), "name": stack.join(" ")}))
            .collect();
        let source = (0..stacks.len())
            .map(|i| format!("probe{i}x\n"))
            .collect::<String>();
        let directory =
            std::env::temp_dir().join(format!("scope-parity-probe-{}", std::process::id()));
        std::fs::create_dir_all(&directory).unwrap();
        let grammar = directory.join("probe.json");
        let theme = directory.join("theme.json");
        std::fs::write(
            &grammar,
            serde_json::to_vec(
                &json!({"name": "probe", "scopeName": "source.probe", "patterns": patterns}),
            )
            .unwrap(),
        )
        .unwrap();
        let run = |value: &serde_json::Value| {
            std::fs::write(&theme, serde_json::to_vec(value).unwrap()).unwrap();
            let mut registry = Registry::default();
            registry.add_grammar_from_path(&grammar).unwrap();
            registry.link_grammars();
            registry.add_theme_from_path(&theme).unwrap();
            let result = registry
                .highlight(
                    &source,
                    &HighlightOptions::new("probe", ThemeVariant::Single("categories"))
                        .merge_whitespace(false)
                        .merge_same_style_tokens(false),
                )
                .unwrap();
            result
                .tokens
                .iter()
                .take(stacks.len())
                .map(|line| {
                    let ThemeVariant::Single(style) = line[0].style else {
                        unreachable!()
                    };
                    diagnostic.decode(style).to_owned()
                })
                .collect::<Vec<_>>()
        };
        assert_eq!(run(&diagnostic.theme), expected);
        let mut wrong = diagnostic.theme.clone();
        for rule in wrong["tokenColors"].as_array_mut().unwrap() {
            if rule["scope"] == "comment" {
                rule["settings"]["foreground"] = json!(diagnostic.colors["number"]);
            }
        }
        assert_ne!(
            run(&wrong),
            expected,
            "wrong theme category must be observable"
        );
        std::fs::remove_dir_all(directory).unwrap();
    }
}
