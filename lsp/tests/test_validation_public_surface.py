"""Verify that public names remain importable from docassemble_lsp.core.validation."""

from __future__ import annotations


class TestValidationPublicSurface:
    """The public surface of the ``validation`` package should stay stable."""

    def test_find_errors_importable(self) -> None:
        from docassemble_lsp.core.validation import find_errors

        assert callable(find_errors)

    def test_find_errors_from_string_importable(self) -> None:
        from docassemble_lsp.core.validation import find_errors_from_string

        assert callable(find_errors_from_string)

    def test_types_of_blocks_importable(self) -> None:
        from docassemble_lsp.core.validation import types_of_blocks

        assert isinstance(types_of_blocks, dict)
        assert "question" in types_of_blocks

    def test_all_dict_keys_importable(self) -> None:
        from docassemble_lsp.core.validation import all_dict_keys

        assert isinstance(all_dict_keys, tuple)
        assert "question" in all_dict_keys

    def test_big_dict_importable(self) -> None:
        from docassemble_lsp.core.validation import big_dict

        assert isinstance(big_dict, dict)
        assert "question" in big_dict

    def test_dafields_importable(self) -> None:
        from docassemble_lsp.core.validation import DAFields

        assert DAFields is not None

    def test_dapythonvar_importable(self) -> None:
        from docassemble_lsp.core.validation import DAPythonVar

        assert DAPythonVar is not None

    def test_makotext_importable(self) -> None:
        from docassemble_lsp.core.validation import MakoText

        assert MakoText is not None

    def test_pythontext_importable(self) -> None:
        from docassemble_lsp.core.validation import PythonText

        assert PythonText is not None

    def test_validationcode_importable(self) -> None:
        from docassemble_lsp.core.validation import ValidationCode

        assert ValidationCode is not None

    def test_showif_importable(self) -> None:
        from docassemble_lsp.core.validation import ShowIf

        assert ShowIf is not None

    def test_jsshowif_importable(self) -> None:
        from docassemble_lsp.core.validation import JSShowIf

        assert JSShowIf is not None

    def test_fields_direct_import(self) -> None:
        from docassemble_lsp.core.validation.fields import (
            DAFields,
            DAPythonVar,
            MakoText,
            PythonText,
            ValidationCode,
            _normalize_validator_error,
        )

        assert all(x is not None for x in [DAFields, DAPythonVar, MakoText, PythonText, ValidationCode])
        assert callable(_normalize_validator_error)

    def test_submodule_direct_import(self) -> None:
        from docassemble_lsp.core.validation.blocks import (
            all_dict_keys,
            big_dict,
            types_of_blocks,
        )

        assert isinstance(types_of_blocks, dict)
        assert isinstance(all_dict_keys, tuple)
        assert isinstance(big_dict, dict)
