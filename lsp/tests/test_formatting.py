from __future__ import annotations

import ast

from docassemble_lsp.core import format_text
from docassemble_lsp.core.formatting import FormatterConfig, format_python_code


def _first_docstring_value(code: str) -> str | None:
    module = ast.parse(code)
    return ast.get_docstring(module.body[0])


def test_format_text_formats_embedded_python() -> None:
    result = format_text("---\ncode: |\n  x={'a':1}\n")

    assert result.changed is True
    assert 'x = {"a": 1}' in result.text


def test_format_reindent_python_indent_2() -> None:
    config = FormatterConfig(indent=2)
    result = format_python_code("if True:\n    pass\n", config=config)
    assert result == "if True:\n  pass\n"


def test_reindent_python_two_space_to_four() -> None:
    config = FormatterConfig(indent=4)
    code = "# fmt: off\nif True:\n  pass\n"
    result = format_python_code(code, config=config)
    assert result == "# fmt: off\nif True:\n    pass\n"


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
    malformed = (
        "# use jinja\n{% block content %}\nkey: [unclosed list\n{% endblock %}\n"
    )
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


def test_format_text_converts_tabs_to_spaces() -> None:
    config = FormatterConfig(convert_tabs_to_spaces=True)
    result = format_text("key:\tvalue\n", config=config)
    assert "\t" not in result.text
    assert result.text == "key:  value\n"


def test_reindent_python_preserves_multiline_string_content() -> None:
    code = '# fmt: off\nx = """\n  hello\n"""\n'
    result = format_python_code(code, config=FormatterConfig(indent=4))
    assert result == code


def test_format_python_docstring_string_value_preserved() -> None:
    code = 'def f():\n    """\n      notes\n    """\n    return 1\n'
    result = format_python_code(code, config=FormatterConfig(indent=2))
    assert result == 'def f():\n  """\n    notes\n    """\n  return 1\n'
    assert _first_docstring_value(result) == _first_docstring_value(code)


def test_reindent_python_multiline_content_multiple_of_indent() -> None:
    code = 'def f():\n    x = """\n        content\n    """\n'
    result = format_python_code(code, config=FormatterConfig(indent=2))
    assert result == 'def f():\n  x = """\n        content\n    """\n'


def test_reindent_python_module_level_string_preserves_content() -> None:
    code = 'x = """\n  content\n"""\nif True:\n    pass\n'
    result = format_python_code(code, config=FormatterConfig(indent=2))
    assert result == 'x = """\n  content\n"""\nif True:\n  pass\n'
