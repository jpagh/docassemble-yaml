from __future__ import annotations

import pytest

from docassemble_lsp.core import validation


def test_yaml_structure_parser_rejects_removed_url_check_flag() -> None:
    with pytest.raises(SystemExit) as exc_info:
        validation.main(["--url-check"])

    assert exc_info.value.code == 2
