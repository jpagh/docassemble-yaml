from __future__ import annotations

from docassemble_lsp.core import format_text
from docassemble_lsp.core.formatting import FormatterConfig, format_python_code


def test_format_text_formats_embedded_python() -> None:
    result = format_text("---\ncode: |\n  x={'a':1}\n")

    assert result.changed is True
    assert 'x = {"a": 1}' in result.text


def test_format_reindent_python_indent_2() -> None:
    config = FormatterConfig(indent=2)
    result = format_python_code("if True:\n    pass\n", config=config)
    assert result == "if True:\n  pass\n"


def test_format_reindent_python_indent_4_passthrough() -> None:
    config = FormatterConfig(indent=4)
    result = format_python_code("if True:\n    pass\n", config=config)
    assert result == "if True:\n    pass\n"


def test_format_reindent_python_indent_5() -> None:
    config = FormatterConfig(indent=5)
    result = format_python_code("if True:\n    pass\n", config=config)
    assert result == "if True:\n     pass\n"


def test_format_malformed_yaml_returns_unchanged() -> None:
    malformed = "---\nkey: [unclosed list\n"
    result = format_text(malformed)
    assert result.changed is False
    assert result.text == malformed
    assert result.error is not None


def test_format_malformed_yaml_propagates_error_message() -> None:
    malformed = "---\nkey: [unclosed list\n"
    result = format_text(malformed)
    assert result.error is not None
    assert "unclosed" in result.error.lower() or "expected" in result.error.lower()


def test_format_malformed_jinja_yaml_returns_unchanged() -> None:
    malformed = "# use jinja\n{% block content %}\nkey: [unclosed list\n{% endblock %}\n"
    result = format_text(malformed)
    assert result.changed is False
    assert result.text == malformed


def test_format_reader_error_returns_unchanged() -> None:
    malformed = '---\nkey: "\x00"\n'
    result = format_text(malformed)
    assert result.changed is False
    assert result.text == malformed
    assert result.error is not None


def test_formatter_config_has_no_legacy_fields() -> None:
    assert set(FormatterConfig.__dataclass_fields__) == {
        "python_keys",
        "black_line_length",
        "indent",
        "convert_tabs_to_spaces",
        "strip_trailing_whitespace",
    }
