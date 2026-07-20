"""Block-level directive validators (E428-E482).

All directive classes: simple list/dict is-a checks and complex type validators.
"""

from __future__ import annotations

from collections.abc import Mapping

from docassemble_lsp.core.field_validators import _validator_error
from docassemble_lsp.core.line_helpers import (
    _is_internal_metadata_key,
    _lc_key_line,
    _lc_line,
)
from docassemble_lsp.core.messages import MessageCode


class YAMLStr:
    """Should be a direct YAML string, not a list or dict."""

    def __init__(self, x):
        self.errors = []
        if not isinstance(x, str):
            self.errors = [_validator_error(MessageCode.YAML_STRING_TYPE, value=x)]


class NeedDirective:
    """Validator for top-level ``need`` directives."""

    def __init__(self, x):
        self.errors = []
        if isinstance(x, str):
            return
        if not isinstance(x, list):
            self.errors = [_validator_error(MessageCode.NEED_TYPE)]
            return

        for item in x:
            if isinstance(item, Mapping):
                item_keys = {
                    key
                    for key in item.keys()
                    if isinstance(key, str) and not _is_internal_metadata_key(key)
                }
                if not item_keys or not item_keys.issubset({"pre", "post"}):
                    self.errors.append(
                        _validator_error(MessageCode.NEED_DICT_KEYS, _lc_line(item))
                    )
                    continue
                for phase in ("pre", "post"):
                    if phase not in item:
                        continue
                    phase_value = item[phase]
                    if isinstance(phase_value, str):
                        phase_items = [phase_value]
                    elif isinstance(phase_value, list):
                        phase_items = phase_value
                    else:
                        self.errors.append(
                            _validator_error(
                                MessageCode.NEED_PHASE_TYPE,
                                _lc_key_line(item, phase),
                                phase=phase,
                            )
                        )
                        continue
                    if any(not isinstance(sub_item, str) for sub_item in phase_items):
                        self.errors.append(
                            _validator_error(
                                MessageCode.NEED_ITEM_STRING,
                                _lc_key_line(item, phase),
                            )
                        )
            elif not isinstance(item, str):
                self.errors.append(_validator_error(MessageCode.NEED_ITEM_STRING))


class OnChangeDirective:
    """Validator for top-level ``on change`` blocks."""

    def __init__(self, x):
        self.errors = []
        if not isinstance(x, Mapping):
            self.errors = [_validator_error(MessageCode.ON_CHANGE_TYPE)]
            return

        for key, value in x.items():
            if _is_internal_metadata_key(key):
                continue
            if not (isinstance(key, str) and isinstance(value, str)):
                self.errors.append(
                    _validator_error(
                        MessageCode.ON_CHANGE_ENTRY_TYPE,
                        _lc_key_line(x, key),
                    )
                )


class ActionButtonsDirective:
    """Validator for top-level ``action buttons`` blocks."""

    def __init__(self, x):
        self.errors = []
        if isinstance(x, Mapping):
            content_keys = {
                key
                for key in x.keys()
                if isinstance(key, str) and not _is_internal_metadata_key(key)
            }
            if content_keys == {"code"}:
                return
            self.errors = [_validator_error(MessageCode.ACTION_BUTTONS_TYPE)]
            return
        if not isinstance(x, list):
            self.errors = [_validator_error(MessageCode.ACTION_BUTTONS_TYPE)]
            return

        for item in x:
            if not isinstance(item, Mapping):
                self.errors.append(
                    _validator_error(MessageCode.ACTION_BUTTON_ITEM_TYPE)
                )
                continue

            action = item.get("action")
            target = item.get("new window")
            arguments = item.get("arguments", {})
            label = item.get("label")
            color = item.get("color", "primary")
            icon = item.get("icon")
            placement = item.get("placement")
            css_class = item.get("css class")
            forget_prior = item.get("forget prior", False)

            if not isinstance(action, str):
                self.errors.append(
                    _validator_error(
                        MessageCode.ACTION_BUTTON_ACTION_TYPE, _lc_line(item)
                    )
                )
            if target is not None and not isinstance(target, (bool, str)):
                self.errors.append(
                    _validator_error(
                        MessageCode.ACTION_BUTTON_NEW_WINDOW_TYPE,
                        _lc_key_line(item, "new window"),
                    )
                )
            if not isinstance(arguments, Mapping):
                self.errors.append(
                    _validator_error(
                        MessageCode.ACTION_BUTTON_ARGUMENTS_TYPE,
                        _lc_key_line(item, "arguments"),
                    )
                )
            else:
                if any(
                    isinstance(value, (list, dict))
                    for key, value in arguments.items()
                    if not _is_internal_metadata_key(key)
                ):
                    self.errors.append(
                        _validator_error(
                            MessageCode.ACTION_BUTTON_ARGUMENT_ITEM_TYPE,
                            _lc_key_line(item, "arguments"),
                        )
                    )
            if not isinstance(label, str):
                self.errors.append(
                    _validator_error(
                        MessageCode.ACTION_BUTTON_LABEL_TYPE, _lc_line(item)
                    )
                )
            if not isinstance(color, str):
                self.errors.append(
                    _validator_error(
                        MessageCode.ACTION_BUTTON_COLOR_TYPE,
                        _lc_key_line(item, "color"),
                    )
                )
            if icon is not None and not isinstance(icon, str):
                self.errors.append(
                    _validator_error(
                        MessageCode.ACTION_BUTTON_ICON_TYPE,
                        _lc_key_line(item, "icon"),
                    )
                )
            if placement is not None and not isinstance(placement, str):
                self.errors.append(
                    _validator_error(
                        MessageCode.ACTION_BUTTON_PLACEMENT_TYPE,
                        _lc_key_line(item, "placement"),
                    )
                )
            if css_class is not None and not isinstance(css_class, str):
                self.errors.append(
                    _validator_error(
                        MessageCode.ACTION_BUTTON_CSS_CLASS_TYPE,
                        _lc_key_line(item, "css class"),
                    )
                )
            if not isinstance(forget_prior, bool):
                self.errors.append(
                    _validator_error(
                        MessageCode.ACTION_BUTTON_FORGET_PRIOR_TYPE,
                        _lc_key_line(item, "forget prior"),
                    )
                )


class TranslationsDirective:
    """Validator for top-level ``translations`` blocks."""

    def __init__(self, x):
        self.errors = []
        if not isinstance(x, list):
            self.errors = [_validator_error(MessageCode.TRANSLATIONS_TYPE)]
            return

        for index, item in enumerate(x, start=2):
            if not isinstance(item, str):
                self.errors.append(
                    _validator_error(MessageCode.TRANSLATIONS_ITEM_TYPE, index)
                )
                continue
            if not item.endswith((".xlsx", ".xlf", ".xliff")):
                self.errors.append(
                    _validator_error(MessageCode.TRANSLATIONS_SUFFIX, index, item=item)
                )
                continue
            parts = item.split(":")
            if len(parts) == 1:
                continue
            if (
                len(parts) == 2
                and parts[0].startswith("docassemble.")
                and parts[1].startswith("data/sources/")
            ):
                continue
            self.errors.append(
                _validator_error(MessageCode.TRANSLATIONS_PATH, index, item=item)
            )


class IfDirective:
    """Validator for top-level ``if`` directives."""

    def __init__(self, x):
        self.errors = []
        if isinstance(x, (str, list)):
            return
        self.errors = [_validator_error(MessageCode.IF_TYPE)]


class RequireDirective:
    """Validator for top-level ``require`` directives."""

    def __init__(self, x):
        self.errors = []
        if isinstance(x, list):
            return
        self.errors = [_validator_error(MessageCode.REQUIRE_TYPE)]


class TermsDirective:
    """Validator for top-level ``terms`` blocks."""

    def __init__(self, x):
        self.errors = []
        if isinstance(x, dict):
            return
        if not isinstance(x, list):
            self.errors = [_validator_error(MessageCode.TERMS_TYPE)]
            return
        for index, item in enumerate(x, start=2):
            if not isinstance(item, Mapping):
                self.errors.append(_validator_error(MessageCode.TERMS_ITEM_TYPE, index))


class AutoTermsDirective:
    """Validator for top-level ``auto terms`` blocks."""

    def __init__(self, x):
        self.errors = []
        if isinstance(x, dict):
            return
        if not isinstance(x, list):
            self.errors = [_validator_error(MessageCode.AUTO_TERMS_TYPE)]
            return
        for index, item in enumerate(x, start=2):
            if not isinstance(item, Mapping):
                self.errors.append(
                    _validator_error(MessageCode.AUTO_TERMS_ITEM_TYPE, index)
                )


class PythonBool:
    """Some text that needs to explicitly be a python bool."""

    def __init__(self, x):
        self.errors = []
        if isinstance(x, (bool, str)):
            return
        self.errors = [
            _validator_error(MessageCode.PYTHON_BOOL_TYPE, value_type=type(x).__name__)
        ]


class IncludeDirective:
    """Validator for top-level ``include`` blocks.

    Docassemble accepts either a single path string or a list of path strings.
    """

    def __init__(self, x):
        self.errors = []
        if isinstance(x, str):
            return
        if not isinstance(x, list):
            self.errors = [_validator_error(MessageCode.INCLUDE_TYPE)]
            return
        for index, item in enumerate(x, start=2):
            if not isinstance(item, str):
                self.errors.append(
                    _validator_error(MessageCode.INCLUDE_ITEM_TYPE, index)
                )


class ModulesDirective:
    """Validator for top-level ``modules`` blocks."""

    def __init__(self, x):
        self.errors = []
        if isinstance(x, str):
            return
        if not isinstance(x, list):
            self.errors = [_validator_error(MessageCode.MODULES_TYPE)]
            return
        for index, item in enumerate(x, start=2):
            if not isinstance(item, str):
                self.errors.append(
                    _validator_error(MessageCode.MODULES_ITEM_TYPE, index)
                )


class ImportsDirective:
    """Validator for top-level ``imports`` blocks."""

    def __init__(self, x):
        self.errors = []
        if isinstance(x, str):
            return
        if not isinstance(x, list):
            self.errors = [_validator_error(MessageCode.IMPORTS_TYPE)]
            return
        for index, item in enumerate(x, start=2):
            if not isinstance(item, str):
                self.errors.append(
                    _validator_error(MessageCode.IMPORTS_ITEM_TYPE, index)
                )


class MetadataDirective:
    """Validator for top-level ``metadata`` blocks."""

    def __init__(self, x):
        self.errors = []
        if not isinstance(x, Mapping):
            self.errors = [_validator_error(MessageCode.METADATA_TYPE)]


class FeaturesDirective:
    """Validator for top-level ``features`` blocks."""

    def __init__(self, x):
        self.errors = []
        if not isinstance(x, Mapping):
            self.errors = [_validator_error(MessageCode.FEATURES_TYPE)]


class SetsDirective:
    """Validator for top-level ``sets`` and ``only sets`` blocks."""

    def __init__(self, x):
        self.errors = []
        if isinstance(x, str):
            self._check_reserved_name(x)
            return
        if not isinstance(x, list):
            self.errors = [_validator_error(MessageCode.SETS_TYPE)]
            return
        for index, item in enumerate(x, start=2):
            if not isinstance(item, str):
                self.errors.append(_validator_error(MessageCode.SETS_ITEM_TYPE, index))
            else:
                self._check_reserved_name(item)

    def _check_reserved_name(self, varname: str) -> None:
        from docassemble_lsp.core.validation.fields import _is_docassemble_reserved_name

        stripped = varname.strip()
        top_level_var = stripped.split(".")[0].split("[")[0].strip()
        if top_level_var.startswith("_"):
            self.errors.append(
                _validator_error(
                    MessageCode.FIELD_TARGET_UNDERSCORE, value_repr=repr(varname)
                )
            )
        elif _is_docassemble_reserved_name(stripped):
            self.errors.append(
                _validator_error(
                    MessageCode.RESERVED_DA_NAME, value_repr=repr(varname), context=""
                )
            )


class EventDirective:
    """Validator for top-level ``event`` blocks."""

    def __init__(self, x):
        self.errors = []
        if isinstance(x, str):
            return
        if not isinstance(x, list):
            self.errors = [_validator_error(MessageCode.EVENT_TYPE)]
            return
        for index, item in enumerate(x, start=2):
            if not isinstance(item, str):
                self.errors.append(_validator_error(MessageCode.EVENT_ITEM_TYPE, index))


class ReconsiderDirective:
    """Validator for ``reconsider`` blocks."""

    def __init__(self, x):
        self.errors = []
        if isinstance(x, (bool, str)):
            return
        if not isinstance(x, list):
            self.errors = [_validator_error(MessageCode.RECONSIDER_TYPE)]
            return
        for index, item in enumerate(x, start=2):
            if not isinstance(item, str):
                self.errors.append(
                    _validator_error(MessageCode.RECONSIDER_ITEM_TYPE, index)
                )


class UndefineDirective:
    """Validator for ``undefine`` blocks."""

    def __init__(self, x):
        self.errors = []
        if isinstance(x, str):
            return
        if not isinstance(x, list):
            self.errors = [_validator_error(MessageCode.UNDEFINE_TYPE)]
            return
        for index, item in enumerate(x, start=2):
            if not isinstance(item, str):
                self.errors.append(
                    _validator_error(MessageCode.UNDEFINE_ITEM_TYPE, index)
                )


class SupersedesDirective:
    """Validator for ``supersedes`` blocks."""

    def __init__(self, x):
        self.errors = []
        if isinstance(x, str):
            return
        if not isinstance(x, list):
            self.errors = [_validator_error(MessageCode.SUPERSEDES_TYPE)]
            return
        for index, item in enumerate(x, start=2):
            if not isinstance(item, str):
                self.errors.append(
                    _validator_error(MessageCode.SUPERSEDES_ITEM_TYPE, index)
                )


class DependsOnDirective:
    """Validator for ``depends on`` blocks."""

    def __init__(self, x):
        self.errors = []
        if isinstance(x, str):
            return
        if not isinstance(x, list):
            self.errors = [_validator_error(MessageCode.DEPENDS_ON_TYPE)]
            return
        for index, item in enumerate(x, start=2):
            if not isinstance(item, str):
                self.errors.append(
                    _validator_error(MessageCode.DEPENDS_ON_ITEM_TYPE, index)
                )


class RoleDirective:
    """Validator for ``role`` blocks."""

    def __init__(self, x):
        self.errors = []
        if isinstance(x, str):
            return
        if not isinstance(x, list):
            self.errors = [_validator_error(MessageCode.ROLE_TYPE)]
            return
        for index, item in enumerate(x, start=2):
            if not isinstance(item, str):
                self.errors.append(_validator_error(MessageCode.ROLE_ITEM_TYPE, index))


class AllowedToSetDirective:
    """Validator for ``allowed to set`` blocks."""

    def __init__(self, x):
        self.errors = []
        if isinstance(x, (str, list)):
            return
        self.errors = [_validator_error(MessageCode.ALLOWED_TO_SET_TYPE)]


class ProgressDirective:
    """Validator for ``progress`` blocks."""

    def __init__(self, x):
        self.errors = []
        if x is None or isinstance(x, int):
            return
        self.errors = [_validator_error(MessageCode.PROGRESS_TYPE)]
