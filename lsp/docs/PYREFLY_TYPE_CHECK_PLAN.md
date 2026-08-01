# Pyrefly Type Check Plan

## Scope

Fix the reported Pyrefly errors while preserving the existing mypy contract.
Tests remain in scope because the reported command checks the project, while
mypy continues to win if the tools disagree.

## Changes

- Add Pyrefly configuration with `search-path = ["src", "."]` so
  `tests.corpus` resolves. Keep source and test files in the checked project.
- In `tests/test_core_api.py`, access the intentionally absent `C105` member
  through dynamic `getattr` so the runtime assertion remains unchanged.
- In `tests/test_formatting.py`, narrow the first AST statement before passing
  it to `ast.get_docstring`.
- In `tests/test_python_modules.py`, assert that `imported_module_path` is not
  `None` before calling `resolve()`.
- In `tests/test_schema.py`, type `_SCOPE_KEY_REGRESSION_CASES` with
  `CompletionScope`.
- In `src/docassemble_lsp/cli.py`, narrow the optional results returned by
  the `argparse` superclass methods.
- In `src/docassemble_lsp/core/accessibility.py`, use an integer line-number
  fallback before performing arithmetic.
- In `src/docassemble_lsp/core/diagnostics.py`, preserve the public
  `dict[str, object]` return type while making the `asdict` conversion
  explicit to Pyrefly.
- In `src/docassemble_lsp/core/python_navigation.py`, annotate the Python
  suffix sets as `set[tuple[str, ...]]`.

## Verification

Run from `lsp/`:

```bash
uvx pyrefly check
uv run mypy src/
uv run pytest -q
```

Then run the repository check task:

```bash
mise run check
```

Implementation must preserve unrelated existing worktree changes.
