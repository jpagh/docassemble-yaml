"""Shared line-number helper functions for YAML document position tracking.

These functions extract line-number information from ruamel.yaml CommentedMap /
CommentedSeq objects, using both the native ``.lc`` line-column metadata and the
custom ``__line__`` / ``__key_lines__`` / ``__value_lines__`` metadata injected
by the YAML document preprocessor.

They are factored out into their own module to avoid circular imports between
``validation.py`` and ``field_validators.py``, both of which need them.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ruamel.yaml.scalarstring import ScalarString  # type: ignore[import-untyped]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_INTERNAL_METADATA_KEYS = frozenset({"__line__", "__key_lines__", "__value_lines__"})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_internal_metadata_key(key: Any) -> bool:
    """Return True when *key* is a ruamel.yaml internal metadata key."""
    return isinstance(key, str) and key in _INTERNAL_METADATA_KEYS


def _lc_line(obj: Any) -> int:
    """Return a 1-indexed line number from a ruamel.yaml object's position metadata.

    Falls back to 1 when no position data is available (e.g. plain dicts in tests).
    """
    lc = getattr(obj, "lc", None)
    if lc is not None:
        line = getattr(lc, "line", None)
        if line is not None:
            return line + 1
    if isinstance(obj, Mapping):
        metadata_line = obj.get("__line__")
        if isinstance(metadata_line, int):
            return metadata_line
    return 1


def _lc_key_line(obj: Any, key: Any) -> int:
    """Return a 1-indexed line number for a mapping key when available."""
    lc = getattr(obj, "lc", None)
    if lc is not None:
        key_getter = getattr(lc, "key", None)
        if callable(key_getter):
            try:
                line_info = key_getter(key)
            except (AttributeError, KeyError, TypeError):
                line_info = None
            if isinstance(line_info, tuple) and len(line_info) >= 1:
                line = line_info[0]
                if isinstance(line, int):
                    return line + 1
    if isinstance(obj, Mapping):
        key_lines = obj.get("__key_lines__")
        if isinstance(key_lines, Mapping):
            metadata_line = key_lines.get(key)
            if isinstance(metadata_line, int):
                return metadata_line
    # If key-specific location data is unavailable (e.g. no metadata for this key,
    # unexpected type/shape, or non-integer line), fall back to the object's line.
    return _lc_line(obj)


def _lc_value_line(obj: Any, key: Any) -> int:
    """Return a 1-indexed line number for a mapping value when available."""
    if isinstance(obj, Mapping):
        value_lines = obj.get("__value_lines__")
        if isinstance(value_lines, Mapping):
            metadata_line = value_lines.get(key)
            if isinstance(metadata_line, int):
                return metadata_line
    return _lc_key_line(obj, key)


def _relative_value_line(mapping: Mapping[Any, Any], key: Any, code_line: int = 1) -> int:
    """Return the line number for a value offset within a mapping entry."""
    key_line = _lc_key_line(mapping, key)
    value = mapping.get(key)
    relative_line = max(code_line, 1)
    if isinstance(value, ScalarString):
        line_count = max(len(value.splitlines()), 1)
        return key_line + min(relative_line, line_count)
    value_line = _lc_value_line(mapping, key)
    return value_line + max(relative_line - 1, 0)
