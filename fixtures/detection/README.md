# Interview path detection cases

Policy owner: Fresh's `fresh/docassemble.ts` established the opt-in package-path
policy; `docs/FRESH.md` documents it. Only YAML beneath a `data/questions/`
**component pair**, including nested directories, is claimed automatically.
No package metadata lookup or workspace crawl is required. YAML elsewhere needs
explicit editor-specific opt-in. Matching is case-sensitive; separators are
normalized for the Windows-style cases inherited from Fresh.

`paths.json` is editor-independent data, not runtime implementation. `fresh` and
`kakoune` record expected decisions: Fresh currently claims `.yml` only; issue
#22 explicitly extends Kakoune to `.yaml` as well. This deliberate extension is
not a Fresh runtime change.

- `fresh/scripts/check_detection.py` tests Fresh's actual regex (its portable
  regex subset evaluated by Python) and separator normalization against every case.
- `kakoune/tests/test_docassemble.py` executes the shell decision block extracted
  from the shipped `.kak` plugin for every case, and, when Kakoune is installed,
  opens the same paths through its real hooks. No giallo/server is needed.

Keep shared policy cases here rather than copying editor-specific test lists.
