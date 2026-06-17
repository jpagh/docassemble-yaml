format:
    uv run ruff format

lint:
    uv run ruff check --fix

test:
    uv run pytest -q -n auto

test-versions:
    rm -rf .venv; uv run --python 3.10 --only-group test pytest -n auto
    rm -rf .venv; uv run --python 3.11 --only-group test pytest -n auto
    rm -rf .venv; uv run --python 3.12 --only-group test pytest -n auto
    rm -rf .venv; uv run --python 3.13 --only-group test pytest -n auto
    rm -rf .venv; uv run --python 3.14 --only-group test pytest -n auto
    rm -rf .venv; uv sync

type:
    uv run mypy .
