from __future__ import annotations

import re
from functools import lru_cache
from io import StringIO
from pathlib import Path

from ruamel.yaml import YAML

_EXAMPLE_TOP_LEVEL_KEY_RE = re.compile(r"^([^:#][^:]*?)\s*:")
_FIXTURE_DOCUMENT_ID_RE = re.compile(r"^id:\s*(.+?)\s*$", re.MULTILINE)
_MESSAGE_CODE_RE = re.compile(r"[CEW]\d{3}")
_STANDALONE_BLOCK_SUPPORT_KEYS = {
    "content type",
    "event",
    "include_internal",
    "mandatory",
    "response code",
    "sleep",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def repo_example_corpus_root() -> Path:
    return _repo_root() / "tests/fixtures/examples"


def regression_fixture_root() -> Path:
    return _repo_root() / "tests/fixtures/regressions"


def regression_fixture_path(name: str) -> Path:
    return regression_fixture_root() / name


@lru_cache(maxsize=None)
def regression_fixture_text(name: str) -> str:
    return regression_fixture_path(name).read_text(encoding="utf-8")


def split_yaml_documents(text: str) -> tuple[str, ...]:
    documents: list[str] = []
    current: list[str] = []

    for line in text.splitlines(keepends=True):
        if line.strip() == "---" and current:
            documents.append("".join(current))
            current = [line]
            continue
        current.append(line)

    if current:
        documents.append("".join(current))

    return tuple(documents)


@lru_cache(maxsize=None)
def regression_fixture_documents(name: str) -> tuple[tuple[str, str], ...]:
    documents: list[tuple[str, str]] = []
    for source in split_yaml_documents(regression_fixture_text(name)):
        match = _FIXTURE_DOCUMENT_ID_RE.search(source)
        if match is None:
            continue
        documents.append((match.group(1).strip(), source))
    return tuple(documents)


def expected_codes_from_fixture_id(document_id: str) -> frozenset[str]:
    return frozenset(_MESSAGE_CODE_RE.findall(document_id))


@lru_cache(maxsize=1)
def example_corpus_roots() -> tuple[Path, ...]:
    roots = [repo_example_corpus_root()]
    roots.extend(installed_example_corpus_roots())
    return tuple(root for root in roots if root.exists())


@lru_cache(maxsize=1)
def installed_example_corpus_roots() -> tuple[Path, ...]:
    roots = tuple(
        root
        for root in (_repo_root() / ".venv").glob(
            "lib/python*/site-packages/docassemble/base/data/questions/examples"
        )
        if root.exists()
    )
    return roots


@lru_cache(maxsize=2)
def example_documents(
    *, installed_only: bool = False
) -> tuple[tuple[Path, dict[object, object]], ...]:
    yaml = YAML(typ="safe")
    documents: list[tuple[Path, dict[object, object]]] = []
    roots = (
        installed_example_corpus_roots() if installed_only else example_corpus_roots()
    )
    for root in roots:
        for path in root.rglob("*.yml"):
            try:
                loaded = list(yaml.load_all(path.read_text(encoding="utf-8")))
            except Exception:
                continue
            for document in loaded:
                if isinstance(document, dict):
                    documents.append((path, document))
    return tuple(documents)


def string_keys(mapping: object) -> set[str]:
    if not isinstance(mapping, dict):
        return set()
    return {key for key in mapping if isinstance(key, str)}


@lru_cache(maxsize=1)
def top_level_keys_from_example_corpora() -> frozenset[str]:
    keys: set[str] = set()
    for root in example_corpus_roots():
        for path in root.rglob("*.yml"):
            for text in path.read_text(encoding="utf-8").splitlines():
                if text.strip() == "---":
                    continue
                if len(text) != len(text.lstrip(" ")):
                    continue
                match = _EXAMPLE_TOP_LEVEL_KEY_RE.match(text)
                if match is not None:
                    keys.add(match.group(1).strip())
    return frozenset(keys)


@lru_cache(maxsize=1)
def metadata_keys_from_example_corpora() -> frozenset[str]:
    keys: set[str] = set()
    for _, document in example_documents(installed_only=True):
        keys.update(string_keys(document.get("metadata")))
    return frozenset(keys)


@lru_cache(maxsize=1)
def attachment_item_keys_from_example_corpora() -> frozenset[str]:
    keys: set[str] = set()
    for _, document in example_documents(installed_only=True):
        for block_name in ("attachment", "attachments"):
            value = document.get(block_name)
            if isinstance(value, dict):
                keys.update(string_keys(value))
            elif isinstance(value, list):
                for item in value:
                    keys.update(string_keys(item))
    return frozenset(keys)


@lru_cache(maxsize=1)
def default_screen_parts_keys_from_example_corpora() -> frozenset[str]:
    keys: set[str] = set()
    for _, document in example_documents(installed_only=True):
        keys.update(string_keys(document.get("default screen parts")))
    return frozenset(keys)


def render_yaml_document(document: dict[object, object]) -> str:
    yaml = YAML()
    stream = StringIO()
    yaml.dump(document, stream)
    return stream.getvalue()


@lru_cache(maxsize=1)
def installed_example_top_level_keys() -> frozenset[str]:
    keys: set[str] = set()
    for _, document in example_documents(installed_only=True):
        keys.update(key for key in document if isinstance(key, str))
    return frozenset(keys)


@lru_cache(maxsize=1)
def standalone_installed_example_blocks() -> tuple[tuple[str, str, str], ...]:
    examples_by_block: dict[str, tuple[str, str]] = {}
    repo_root = _repo_root()

    for path, document in example_documents(installed_only=True):
        document_string_keys = [key for key in document if isinstance(key, str)]
        main_keys = [
            key
            for key in document_string_keys
            if key not in _STANDALONE_BLOCK_SUPPORT_KEYS
        ]
        if len(main_keys) != 1:
            continue
        block_name = main_keys[0]
        if block_name in examples_by_block:
            continue
        examples_by_block[block_name] = (
            str(path.relative_to(repo_root)),
            render_yaml_document(document),
        )

    return tuple(
        (block_name, path, source)
        for block_name, (path, source) in sorted(examples_by_block.items())
    )
