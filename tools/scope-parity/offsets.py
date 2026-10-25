"""Normalize native engine offsets to Unicode codepoints, never graphemes.

TextMate uses JS UTF-16 code units; syntect and giallo use Rust UTF-8 bytes.
Newlines are excluded by the adapters. Invalid mid-character boundaries fail.
"""


def boundaries(text: str, unit: str) -> dict[int, int]:
    widths = {
        "utf16": lambda char: len(char.encode("utf-16-le")) // 2,
        "utf8": lambda char: len(char.encode("utf-8")),
        "codepoint": lambda char: 1,
    }
    width = widths[unit]
    result = {0: 0}
    offset = 0
    for index, char in enumerate(text, 1):
        offset += width(char)
        result[offset] = index
    return result


def normalize(line: dict, unit: str) -> list[str]:
    """Expand a complete, nonoverlapping native-unit stream into codepoints."""
    mapping = boundaries(line["text"], unit)
    result = []
    previous = 0
    for start, end, category in line["runs"]:
        if start != previous or end <= start:
            raise ValueError(f"noncontiguous/empty run: {start}-{end}")
        if start not in mapping or end not in mapping:
            raise ValueError(f"invalid {unit} boundary: {start}-{end}")
        result.extend([category] * (mapping[end] - mapping[start]))
        previous = end
    if len(result) != len(line["text"]):
        raise ValueError("incomplete category stream")
    return result
