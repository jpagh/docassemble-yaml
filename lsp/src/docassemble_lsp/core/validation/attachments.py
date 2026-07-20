"""Attachment block validators (E901-E910)."""

from __future__ import annotations

from collections.abc import Mapping

from docassemble_lsp.core.field_validators import _validator_error
from docassemble_lsp.core.line_helpers import (
    _is_internal_metadata_key,
    _lc_key_line,
    _lc_line,
)
from docassemble_lsp.core.messages import MessageCode
from docassemble_lsp.core.validation.fields import _seq_item_line


class AttachmentBlockDirective:
    """Validator for top-level ``attachment`` and ``attachments`` blocks.

    Validates the static structure of attachment list items based on parser
    behavior in ``Question.process_attachment``. The parser accepts both a
    single dict and a list of dicts, so this validator handles both forms.

    Docassemble parser-backed validation:
    - Each attachment item must be a dictionary.
    - ``name``, ``filename``, ``description`` -- plain text.
    - ``variable name`` -- plain text.
    - ``metadata`` -- a dictionary.
    - ``content file`` -- text, list of text, or dict with single key ``code``.
    - ``code`` (for PDF/DOCX fields) -- plain text (Python expression).
    - ``field variables`` / ``raw field variables`` -- a list.
    - ``valid formats`` -- a string, list, or dict with single key ``code``.
    """

    def __init__(self, x):
        self.errors = []
        if isinstance(x, str):
            return
        if isinstance(x, Mapping):
            items = [x]
        elif isinstance(x, list):
            items = x
        else:
            self.errors = [_validator_error(MessageCode.ATTACHMENT_ITEM_MUST_BE_DICT)]
            return

        for item in items:
            if not isinstance(item, Mapping):
                self.errors.append(
                    _validator_error(
                        MessageCode.ATTACHMENT_ITEM_MUST_BE_DICT, _lc_line(item)
                    )
                )
                continue
            self._validate_item(item)

    def _validate_item(self, item: Mapping) -> None:
        if "name" in item and not isinstance(item["name"], str):
            self.errors.append(
                _validator_error(
                    MessageCode.ATTACHMENT_NAME_TYPE, _lc_key_line(item, "name")
                )
            )

        if "filename" in item and not isinstance(item["filename"], str):
            self.errors.append(
                _validator_error(
                    MessageCode.ATTACHMENT_FILENAME_TYPE, _lc_key_line(item, "filename")
                )
            )

        if "variable name" in item and not isinstance(item["variable name"], str):
            self.errors.append(
                _validator_error(
                    MessageCode.ATTACHMENT_VARIABLE_NAME_TYPE,
                    _lc_key_line(item, "variable name"),
                )
            )

        if "metadata" in item and not isinstance(item["metadata"], Mapping):
            self.errors.append(
                _validator_error(
                    MessageCode.ATTACHMENT_METADATA_TYPE, _lc_key_line(item, "metadata")
                )
            )

        if "metadata" in item and isinstance(item["metadata"], Mapping):
            for key, val in item["metadata"].items():
                if _is_internal_metadata_key(key):
                    continue
                if isinstance(val, (bool, str)):
                    continue
                if isinstance(val, list) and all(isinstance(sub, str) for sub in val):
                    continue
                self.errors.append(
                    _validator_error(
                        MessageCode.ATTACHMENT_METADATA_ENTRY_TYPE,
                        _lc_key_line(item["metadata"], key),
                        data_type=type(val).__name__,
                        key_name=str(key),
                    )
                )

        if "content file" in item:
            cf = item["content file"]
            if isinstance(cf, str):
                pass
            elif isinstance(cf, list):
                for idx, cf_item in enumerate(cf):
                    if not isinstance(cf_item, str):
                        self.errors.append(
                            _validator_error(
                                MessageCode.ATTACHMENT_CONTENT_FILE_TYPE,
                                _seq_item_line(cf, idx),
                            )
                        )
            elif isinstance(cf, Mapping):
                content_keys = {
                    k
                    for k in cf
                    if isinstance(k, str) and not _is_internal_metadata_key(k)
                }
                if not (content_keys == {"code"} and isinstance(cf.get("code"), str)):
                    self.errors.append(
                        _validator_error(
                            MessageCode.ATTACHMENT_CONTENT_FILE_TYPE,
                            _lc_key_line(item, "content file"),
                        )
                    )
            else:
                self.errors.append(
                    _validator_error(
                        MessageCode.ATTACHMENT_CONTENT_FILE_TYPE,
                        _lc_key_line(item, "content file"),
                    )
                )

        if "code" in item and not isinstance(item["code"], str):
            self.errors.append(
                _validator_error(
                    MessageCode.ATTACHMENT_CODE_TYPE, _lc_key_line(item, "code")
                )
            )

        for fv_key in ("field variables", "raw field variables"):
            if fv_key in item and not isinstance(item[fv_key], list):
                self.errors.append(
                    _validator_error(
                        MessageCode.ATTACHMENT_FIELD_VARIABLES_TYPE,
                        _lc_key_line(item, fv_key),
                    )
                )

        if "valid formats" in item:
            vf = item["valid formats"]
            if isinstance(vf, str):
                pass
            elif isinstance(vf, list):
                pass
            elif isinstance(vf, Mapping):
                content_keys = {
                    k
                    for k in vf
                    if isinstance(k, str) and not _is_internal_metadata_key(k)
                }
                if not (content_keys == {"code"} and isinstance(vf.get("code"), str)):
                    self.errors.append(
                        _validator_error(
                            MessageCode.ATTACHMENT_VALID_FORMATS_TYPE,
                            _lc_key_line(item, "valid formats"),
                        )
                    )
            else:
                self.errors.append(
                    _validator_error(
                        MessageCode.ATTACHMENT_VALID_FORMATS_TYPE,
                        _lc_key_line(item, "valid formats"),
                    )
                )
