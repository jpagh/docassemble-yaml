from __future__ import annotations

from pathlib import Path

import pytest

import docassemble_lsp.cli as cli
from docassemble_lsp.cli import build_parser, main
from docassemble_lsp.core import FormatterConfig
from docassemble_lsp.core.validation_config import RuntimeOptions

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "regressions"
PACKAGE_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
DEMO_QUESTIONS_DIR = PACKAGE_FIXTURES_DIR / "demo_package" / "docassemble" / "demo" / "data" / "questions"


def test_check_command_reports_errors_as_json(tmp_path: Path, capsys) -> None:
    source = tmp_path / "broken.yml"
    source.write_text("---\nfoo: bar\n", encoding="utf-8")

    exit_code = main(["check", "--json", str(source)])

    assert exit_code == 1
    assert '"code": "E301"' in capsys.readouterr().out


def test_check_command_warning_only_is_zero_without_strict(tmp_path: Path) -> None:
    source = tmp_path / "warning.yml"
    source.write_text(
        """---
id: prior_question
question: First
fields:
  - A: a
  - B: b
    show if: a
---
mandatory: True
code: |
  b
""",
        encoding="utf-8",
    )

    exit_code = main(["check", "--quiet", str(source)])

    assert exit_code == 0


def test_check_command_warning_only_fails_in_strict_mode(tmp_path: Path) -> None:
    source = tmp_path / "warning.yml"
    source.write_text(
        """---
id: prior_question
question: First
fields:
  - A: a
  - B: b
    show if: a
---
mandatory: True
code: |
  b
""",
        encoding="utf-8",
    )

    exit_code = main(["check", "--quiet", "--strict", str(source)])

    assert exit_code == 1


def test_check_command_convention_only_fails_in_strict_mode(tmp_path: Path) -> None:
    source = tmp_path / "convention.yml"
    source.write_text(
        """---
question: Fruit total
fields:
  - Apples: number_apples
    datatype: integer
  - Oranges: number_oranges
    datatype: integer
validation code: |
  if number_apples + number_oranges != 10:
    raise Exception("Bad total")
""",
        encoding="utf-8",
    )

    exit_code = main(["check", "--quiet", "--strict", "--conventions", "C101", str(source)])

    assert exit_code == 1


def test_check_command_specific_convention_is_zero_without_strict(tmp_path: Path) -> None:
    source = tmp_path / "convention.yml"
    source.write_text(
        "question: Hi\nfields:\n  - Name: user.name\n",
        encoding="utf-8",
    )

    exit_code = main(["check", "--quiet", "--conventions", "C102", str(source)])

    assert exit_code == 0


def test_check_command_specific_convention_fails_in_strict_mode(tmp_path: Path) -> None:
    source = tmp_path / "convention.yml"
    source.write_text(
        "question: Hi\nfields:\n  - Name: user.name\n",
        encoding="utf-8",
    )

    exit_code = main(["check", "--quiet", "--strict", "--conventions", "C102", str(source)])

    assert exit_code == 1


def test_check_command_fix_rewrites_field_label_shorthand_file(tmp_path: Path) -> None:
    source = tmp_path / "convention.yml"
    source.write_text(
        "question: Hi\nfields:\n  - Name: user.name\n  - Age: user.age\n",
        encoding="utf-8",
    )

    exit_code = main(
        [
            "check",
            "--quiet",
            "--strict",
            "--fix",
            "--conventions",
            "C102",
            str(source),
        ]
    )

    assert exit_code == 0
    assert source.read_text(encoding="utf-8") == (
        "question: Hi\nfields:\n  - label: Name\n    field: user.name\n  - label: Age\n    field: user.age\n"
    )


def test_check_command_fix_rewrites_radio_datatype_with_choices_file(tmp_path: Path) -> None:
    source = tmp_path / "radio.yml"
    source.write_text(
        'question: Hi\nfields:\n  - label: May we text you?\n    field: texting_allowed\n    datatype: radio\n    choices:\n      - "A"\n      - "B"\n',
        encoding="utf-8",
    )

    exit_code = main(["check", "--quiet", "--strict", "--fix", "--conventions", "C103", str(source)])

    assert exit_code == 0
    assert source.read_text(encoding="utf-8") == (
        'question: Hi\nfields:\n  - label: May we text you?\n    field: texting_allowed\n    input type: radio\n    choices:\n      - "A"\n      - "B"\n'
    )


def test_check_command_ignore_codes_can_suppress_errors(tmp_path: Path) -> None:
    source = tmp_path / "ignored.yml"
    source.write_text("---\nfoo: bar\n", encoding="utf-8")

    exit_code = main(["check", "--quiet", "--ignore-codes", "E301,E306", str(source)])

    assert exit_code == 0


def test_check_command_reads_conventions_from_pyproject(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[tool.docassemble-lsp]\nconventions = ["C102"]\n',
        encoding="utf-8",
    )
    source = tmp_path / "convention.yml"
    source.write_text("question: Hi\nfields:\n  - Name: user.name\n", encoding="utf-8")

    exit_code = main(["check", "--quiet", "--strict", str(source)])

    assert exit_code == 1


def test_check_command_reads_ignore_codes_from_pyproject(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[tool.docassemble-lsp]\nignore-codes = ["E301", "E306"]\n',
        encoding="utf-8",
    )
    source = tmp_path / "ignored.yml"
    source.write_text("---\nfoo: bar\n", encoding="utf-8")

    exit_code = main(["check", "--quiet", str(source)])

    assert exit_code == 0


def test_check_command_reads_ignore_codes_snake_case_from_pyproject(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[tool.docassemble-lsp]\nignore_codes = ["E301", "E306"]\n',
        encoding="utf-8",
    )
    source = tmp_path / "ignored.yml"
    source.write_text("---\nfoo: bar\n", encoding="utf-8")

    exit_code = main(["check", "--quiet", str(source)])

    assert exit_code == 0


def test_check_command_accepts_indent_arg(tmp_path: Path) -> None:
    source = tmp_path / "test.yml"
    source.write_text("question: Hi\n", encoding="utf-8")
    exit_code = main(["check", "--quiet", "--indent", "4", str(source)])
    assert exit_code == 0


def test_check_command_with_indent_in_config_does_not_error(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[tool.docassemble-lsp]\nargs = ["--indent", "4"]\n', encoding="utf-8")
    source = tmp_path / "test.yml"
    source.write_text("question: Hi\n", encoding="utf-8")
    exit_code = main(["check", "--quiet", str(source)])
    assert exit_code == 0


def test_check_command_suppresses_warnings_with_no_warnings(tmp_path: Path) -> None:
    source = tmp_path / "warning.yml"
    source.write_text(
        """---
id: prior
question: First
fields:
  - A: a
  - B: b
    show if: a
---
mandatory: True
code: |
  b
""",
        encoding="utf-8",
    )

    exit_code_strict = main(["check", "--strict", str(source)])
    assert exit_code_strict == 1

    exit_code_no_warn = main(["check", "--strict", "--no-warnings", str(source)])
    assert exit_code_no_warn == 0


def test_check_command_no_warnings_does_not_suppress_errors(tmp_path: Path) -> None:
    source = tmp_path / "broken.yml"
    source.write_text("---\nfoo: bar\n", encoding="utf-8")

    exit_code = main(["check", "--no-warnings", str(source)])
    assert exit_code == 1


def test_check_command_accepts_no_warnings_flag() -> None:
    parser = build_parser()
    parsed = parser.parse_args(["check", "--no-warnings", "dummy.yml"])
    assert parsed.no_warnings is True


def test_check_command_default_no_warnings_is_false() -> None:
    parser = build_parser()
    parsed = parser.parse_args(["check", "dummy.yml"])
    assert parsed.no_warnings is False


def test_check_command_ignores_convert_tabs_to_spaces_from_shared_args(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[tool.docassemble-lsp]\nargs = ["--convert-tabs-to-spaces"]\n',
        encoding="utf-8",
    )
    source = tmp_path / "ok.yml"
    source.write_text("question: Hi\n", encoding="utf-8")

    exit_code = main(["check", "--quiet", str(source)])

    assert exit_code == 0


def test_check_command_merges_conventions_from_args_and_pyproject(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[tool.docassemble-lsp]\nconventions = ["C102"]\n',
        encoding="utf-8",
    )
    source = tmp_path / "conventions.yml"
    source.write_text(
        'question: Hi\nfields:\n  - Name: user.name\n  - label: May we text you?\n    field: texting_allowed\n    datatype: radio\n    choices:\n      - "A"\n',
        encoding="utf-8",
    )

    exit_code = main(["check", "--quiet", "--strict", "--conventions", "C103", str(source)])

    assert exit_code == 1


def test_check_command_accepts_multiple_codes_after_single_flag(tmp_path: Path) -> None:
    source = tmp_path / "conventions.yml"
    source.write_text(
        'question: Hi\nfields:\n  - Name: user.name\n  - label: May we text you?\n    field: texting_allowed\n    datatype: radio\n    choices:\n      - "A"\n',
        encoding="utf-8",
    )

    exit_code = main(["check", "--quiet", "--strict", "--conventions", "C102", "C103", str(source)])

    assert exit_code == 1


def test_check_command_accepts_multiple_ignore_codes_after_single_flag(tmp_path: Path) -> None:
    source = tmp_path / "ignored.yml"
    source.write_text("---\nfoo: bar\n", encoding="utf-8")

    exit_code = main(["check", "--quiet", "--ignore-codes", "E301", "E306", str(source)])

    assert exit_code == 0


@pytest.mark.parametrize(
    ("argv", "expected_exit_code"),
    [
        (["check", "--quiet", str(FIXTURES_DIR / "large_valid_interview.yml")], 0),
        (["check", "--quiet", str(FIXTURES_DIR / "large_invalid_interview.yml")], 1),
        (["check", "--quiet", str(DEMO_QUESTIONS_DIR)], 0),
    ],
    ids=[
        "valid_fixture_passes",
        "invalid_fixture_fails",
        "package_fixture_directory_passes",
    ],
)
def test_check_command_regression_fixture_exit_codes(argv: list[str], expected_exit_code: int) -> None:
    assert main(argv) == expected_exit_code


def test_check_command_warning_regression_fixture_exit_codes() -> None:
    source = FIXTURES_DIR / "large_warning_convention_interview.yml"

    assert main(["check", "--quiet", str(source)]) == 0
    assert main(["check", "--quiet", "--strict", str(source)]) == 1


def test_check_command_invalid_fixture_reports_multiple_json_codes(capsys) -> None:
    source = FIXTURES_DIR / "large_invalid_interview.yml"

    exit_code = main(["check", "--json", str(source)])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert '"code": "E101"' in output
    assert '"code": "E301"' in output
    assert '"code": "W603"' in output


def test_codes_command_lists_code_summaries(capsys) -> None:
    exit_code = main(["codes"])

    output_lines = capsys.readouterr().out.splitlines()
    assert exit_code == 0
    assert "E101  error       Duplicate YAML key" in output_lines
    assert "C101  convention  Prefer validation_error() over raise/assert in validation code" in output_lines


def test_check_command_jinja_regression_fixtures_fail(tmp_path: Path) -> None:
    for fixture_name in (
        "large_invalid_jinja_syntax.yml",
        "large_invalid_jinja_template.yml",
    ):
        source = FIXTURES_DIR / fixture_name

        exit_code = main(["check", "--quiet", str(source)])

        assert exit_code == 1


def test_format_check_returns_nonzero_when_file_would_change(tmp_path: Path) -> None:
    source = tmp_path / "format.yml"
    source.write_text("---\ncode: |\n  x={'a':1}\n", encoding="utf-8")

    exit_code = main(["format", "--check", "--quiet", str(source)])

    assert exit_code == 1


def test_format_command_can_convert_tabs_to_spaces(tmp_path: Path) -> None:
    source = tmp_path / "tabs.yml"
    source.write_text("question:\tHi\n", encoding="utf-8")

    exit_code = main(["format", "--quiet", "--convert-tabs-to-spaces", str(source)])

    assert exit_code == 0
    assert source.read_text(encoding="utf-8") == "question:  Hi\n"


def test_format_command_can_read_convert_tabs_to_spaces_from_pyproject(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[tool.docassemble-lsp]\nformat_args = ["--convert-tabs-to-spaces"]\n',
        encoding="utf-8",
    )
    source = tmp_path / "tabs.yml"
    source.write_text("question:\tHi\n", encoding="utf-8")

    exit_code = main(["format", "--quiet", str(source)])

    assert exit_code == 0
    assert source.read_text(encoding="utf-8") == "question:  Hi\n"


def test_format_command_can_read_convert_tabs_to_spaces_from_shared_args(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[tool.docassemble-lsp]\nargs = ["--convert-tabs-to-spaces"]\n',
        encoding="utf-8",
    )
    source = tmp_path / "tabs.yml"
    source.write_text("question:\tHi\n", encoding="utf-8")

    exit_code = main(["format", "--quiet", str(source)])

    assert exit_code == 0
    assert source.read_text(encoding="utf-8") == "question:  Hi\n"


def test_lsp_command_accepts_stdio_flag_as_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    parser = build_parser()

    parsed = parser.parse_args(["lsp", "--stdio"])

    assert parsed.stdio is True

    monkeypatch.setattr(cli, "run_server", lambda **_kwargs: 17)

    assert main(["lsp", "--stdio"]) == 17


def test_lsp_command_accepts_conventions_and_ignore_codes(monkeypatch: pytest.MonkeyPatch) -> None:
    parser = build_parser()

    parsed = parser.parse_args(["lsp", "--conventions", "C102", "C103", "--ignore-codes", "E301", "W603"])

    assert parsed.conventions == ["C102,C103"]
    assert parsed.ignore_codes == ["E301,W603"]

    captured: dict[str, object] = {}

    def fake_run_server(*, runtime_options=None, formatter_config=None, log_level="WARNING"):
        captured["runtime_options"] = runtime_options
        captured["formatter_config"] = formatter_config
        return 23

    monkeypatch.setattr(cli, "run_server", fake_run_server)

    assert main(["lsp", "--conventions", "C102", "C103", "--ignore-codes", "E301", "W603"]) == 23
    runtime_options = captured.get("runtime_options")
    assert isinstance(runtime_options, RuntimeOptions)
    assert runtime_options.enabled_conventions == frozenset({"C102", "C103"})
    assert runtime_options.ignore_codes == frozenset({"E301", "W603"})
    formatter_config = captured.get("formatter_config")
    assert isinstance(formatter_config, FormatterConfig)
    assert formatter_config.convert_tabs_to_spaces is False


def test_lsp_command_accepts_convert_tabs_to_spaces(monkeypatch: pytest.MonkeyPatch) -> None:
    parser = build_parser()

    parsed = parser.parse_args(["lsp", "--convert-tabs-to-spaces"])

    assert parsed.convert_tabs_to_spaces is True

    captured: dict[str, object] = {}

    def fake_run_server(*, runtime_options=None, formatter_config=None, log_level="WARNING"):
        captured["runtime_options"] = runtime_options
        captured["formatter_config"] = formatter_config
        return 31

    monkeypatch.setattr(cli, "run_server", fake_run_server)

    assert main(["lsp", "--convert-tabs-to-spaces"]) == 31
    formatter_config = captured.get("formatter_config")
    assert isinstance(formatter_config, FormatterConfig)
    assert formatter_config.convert_tabs_to_spaces is True


def test_lsp_command_reads_runtime_options_from_pyproject(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[tool.docassemble-lsp]\nconventions = ["C102", "C103"]\nignore-codes = ["E301"]\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    captured: dict[str, object] = {}

    def fake_run_server(*, runtime_options=None, formatter_config=None, log_level="WARNING"):
        captured["runtime_options"] = runtime_options
        captured["formatter_config"] = formatter_config
        return 29

    monkeypatch.setattr(cli, "run_server", fake_run_server)

    assert main(["lsp"]) == 29
    runtime_options = captured.get("runtime_options")
    assert isinstance(runtime_options, RuntimeOptions)
    assert runtime_options.enabled_conventions == frozenset({"C102", "C103"})
    assert runtime_options.ignore_codes == frozenset({"E301"})
    formatter_config = captured.get("formatter_config")
    assert isinstance(formatter_config, FormatterConfig)
    assert formatter_config.convert_tabs_to_spaces is False


def test_lsp_command_reads_convert_tabs_to_spaces_from_shared_args(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[tool.docassemble-lsp]\nargs = ["--convert-tabs-to-spaces"]\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    captured: dict[str, object] = {}

    def fake_run_server(*, runtime_options=None, formatter_config=None, log_level="WARNING"):
        captured["runtime_options"] = runtime_options
        captured["formatter_config"] = formatter_config
        return 37

    monkeypatch.setattr(cli, "run_server", fake_run_server)

    assert main(["lsp"]) == 37
    formatter_config = captured.get("formatter_config")
    assert isinstance(formatter_config, FormatterConfig)
    assert formatter_config.convert_tabs_to_spaces is True


def test_lsp_command_log_level_default() -> None:
    parser = build_parser()
    parsed = parser.parse_args(["lsp"])
    assert parsed.log_level == "WARNING"


def test_lsp_command_log_level_accepts_lowercase() -> None:
    parser = build_parser()
    parsed = parser.parse_args(["lsp", "--log-level", "debug"])
    assert parsed.log_level == "DEBUG"


def test_lsp_command_log_level_passed_to_run_server(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_run_server(*, runtime_options=None, formatter_config=None, log_level="WARNING"):
        captured["log_level"] = log_level
        return 0

    monkeypatch.setattr(cli, "run_server", fake_run_server)
    main(["lsp", "--log-level", "DEBUG"])
    assert captured.get("log_level") == "DEBUG"


def test_check_command_accepts_log_level() -> None:
    parser = build_parser()
    parsed = parser.parse_args(["check", "--log-level", "INFO", "some.yml"])
    assert parsed.log_level == "INFO"


def test_format_command_accepts_log_level() -> None:
    parser = build_parser()
    parsed = parser.parse_args(["format", "--log-level", "ERROR", "some.yml"])
    assert parsed.log_level == "ERROR"


def test_check_command_missing_file_returns_nonzero(tmp_path: Path) -> None:
    missing = str(tmp_path / "does_not_exist.yml")
    exit_code = main(["check", "--quiet", missing])
    assert exit_code == 1


def test_check_command_missing_file_reports_error_to_stderr(tmp_path: Path, capsys) -> None:
    missing = str(tmp_path / "no_such_file.yml")
    exit_code = main(["check", missing])
    assert exit_code == 1
    stderr = capsys.readouterr().err
    assert "error" in stderr.lower()
    assert "no_such_file" in stderr


def test_check_command_missing_file_json_output(tmp_path: Path, capsys) -> None:
    missing = str(tmp_path / "nope.yml")
    import json as _json

    exit_code = main(["check", "--json", missing])
    output = _json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert any(entry.get("error") for entry in output)


def test_check_command_missing_file_quiet_still_fails(tmp_path: Path) -> None:
    missing = str(tmp_path / "nope.yml")
    exit_code = main(["check", "--quiet", missing])
    assert exit_code == 1


def test_format_command_missing_file_returns_one(tmp_path: Path) -> None:
    missing = str(tmp_path / "nope.yml")
    exit_code = main(["format", "--quiet", missing])
    assert exit_code == 1


def test_format_command_malformed_file_returns_one(tmp_path: Path, capsys) -> None:
    source = tmp_path / "bad.yml"
    source.write_text("---\nkey: [unclosed list\n", encoding="utf-8")

    exit_code = main(["format", "--quiet", str(source)])

    assert exit_code == 1


def test_format_command_malformed_file_reports_error_to_stderr(tmp_path: Path, capsys) -> None:
    source = tmp_path / "bad.yml"
    source.write_text("---\nkey: [unclosed list\n", encoding="utf-8")

    exit_code = main(["format", str(source)])

    assert exit_code == 1
    stderr = capsys.readouterr().err
    assert "error" in stderr.lower()


def test_format_command_reader_error_returns_one(tmp_path: Path, capsys) -> None:
    source = tmp_path / "bad_null.yml"
    source.write_text('---\nkey: "\x00"\n', encoding="utf-8")

    exit_code = main(["format", "--quiet", str(source)])

    assert exit_code == 1


def test_format_command_reader_error_reports_to_stderr(tmp_path: Path, capsys) -> None:
    source = tmp_path / "bad_null.yml"
    source.write_text('---\nkey: "\x00"\n', encoding="utf-8")

    exit_code = main(["format", str(source)])

    assert exit_code == 1
    stderr = capsys.readouterr().err
    assert "error" in stderr.lower()


def test_format_check_command_reader_error_returns_one(tmp_path: Path) -> None:
    source = tmp_path / "bad_null_check.yml"
    source.write_text('---\nkey: "\x00"\n', encoding="utf-8")

    exit_code = main(["format", "--check", "--quiet", str(source)])

    assert exit_code == 1
