coverage:
    uv run pytest --cov --cov-report=term-missing --cov-report=html

format:
    uv run ruff format

lint:
    uv run ruff check --fix

test:
    uv run pytest -q -n auto

test-all-pythons:
    #!/usr/bin/env bash
    for version in 3.10 3.11 3.12 3.13 3.14; do
        echo "=== Python $version ==="
        uv run --python $version --only-group test pytest -n auto || exit 1
    done
    uv sync

type:
    uv run mypy .

# Regenerate vendored docassemble stubs from installed package
update-vendor-stubs:
    uv run python scripts/update_vendored_docassemble_base_util.py
