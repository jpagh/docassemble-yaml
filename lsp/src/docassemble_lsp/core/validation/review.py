"""Review block validators (E911-E920)."""

from __future__ import annotations

from collections.abc import Mapping

from docassemble_lsp.core.field_validators import _validator_error
from docassemble_lsp.core.line_helpers import _lc_key_line, _lc_line
from docassemble_lsp.core.messages import MessageCode
from docassemble_lsp.core.validation.fields import _seq_item_line


class ReviewBlockDirective:
    """Validator for top-level ``review`` blocks.

    Docassemble parser-backed validation from ``Question.__init__``:
    - ``review`` must be a list (single dict is wrapped).
    - Each review item must be a dictionary.
    - If ``label`` is present, ``field`` or ``fields`` must also be present.
    - If ``field`` or ``fields`` is present, ``label`` must also be present.
    - ``note``, ``html``, ``raw html`` -- plain text.
    """

    def __init__(self, x):
        self.errors = []
        if isinstance(x, Mapping):
            items = [x]
        elif isinstance(x, list):
            items = x
        else:
            self.errors = [_validator_error(MessageCode.REVIEW_TYPE)]
            return

        for item in items:
            if not isinstance(item, Mapping):
                self.errors.append(
                    _validator_error(MessageCode.REVIEW_ITEM_TYPE, _lc_line(item))
                )
                continue
            self._validate_item(item)

    def _validate_item(self, item: Mapping) -> None:
        has_label = "label" in item
        has_field = "field" in item or "fields" in item
        is_presentation = any(k in item for k in ("note", "html", "raw html"))

        if has_label and not has_field and not is_presentation:
            self.errors.append(
                _validator_error(
                    MessageCode.REVIEW_LABEL_REQUIRES_FIELD, _lc_key_line(item, "label")
                )
            )

        if has_field and not has_label:
            self.errors.append(
                _validator_error(
                    MessageCode.REVIEW_FIELD_REQUIRES_LABEL, _lc_line(item)
                )
            )

        for pk in ("note", "html", "raw html"):
            if pk in item and not isinstance(item[pk], str):
                self.errors.append(
                    _validator_error(
                        MessageCode.REVIEW_NOTE_TYPE, _lc_key_line(item, pk)
                    )
                )

        if "show if" in item:
            show_if_val = item["show if"]
            if not isinstance(show_if_val, (str, list)):
                self.errors.append(
                    _validator_error(
                        MessageCode.REVIEW_SHOW_IF_TYPE, _lc_key_line(item, "show if")
                    )
                )
            elif isinstance(show_if_val, list):
                for sub_idx, sub_item in enumerate(show_if_val):
                    if not isinstance(sub_item, str):
                        self.errors.append(
                            _validator_error(
                                MessageCode.REVIEW_SHOW_IF_TYPE,
                                _seq_item_line(show_if_val, sub_idx),
                            )
                        )

        if "help" in item and not isinstance(item["help"], str):
            self.errors.append(
                _validator_error(
                    MessageCode.REVIEW_HELP_TYPE, _lc_key_line(item, "help")
                )
            )

        if "action" in item and not isinstance(item["action"], str):
            self.errors.append(
                _validator_error(
                    MessageCode.REVIEW_ACTION_TYPE, _lc_key_line(item, "action")
                )
            )

        if "button" in item and not isinstance(item["button"], str):
            self.errors.append(
                _validator_error(
                    MessageCode.REVIEW_BUTTON_TYPE, _lc_key_line(item, "button")
                )
            )

        if "css class" in item and not isinstance(item["css class"], str):
            self.errors.append(
                _validator_error(
                    MessageCode.REVIEW_CSS_CLASS_TYPE, _lc_key_line(item, "css class")
                )
            )
