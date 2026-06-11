from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

from docassemble_lsp.core.field_keys import (
    FIELDS_ITEM_LAYOUT_PYTHON_EXPR_KEYS,
    FIELDS_ITEM_SPECIAL_PYTHON_EXPR_KEYS,
    FIELDS_ITEM_SPECIAL_STRING_KEYS,
)

CompletionScope = Literal[
    "top_level",
    "metadata_block",
    "metadata_author_item",
    "metadata_social_block",
    "metadata_social_twitter_block",
    "metadata_social_og_block",
    "attachment_metadata_block",
    "attachment_fields_block",
    "attachment_field_variable_item",
    "sections_item",
    "table_column_item",
    "objects_item",
    "objects_from_file_item",
    "on_change_item",
    "include_item",
    "imports_item",
    "modules_item",
    "translations_item",
    "reset_item",
    "order_item",
    "features_block",
    "default_screen_parts_block",
    "list_collect_block",
    "image_set_block",
    "validation_messages_block",
    "review_item",
    "review_field_item",
    "attachment_item",
    "attachment_options_block",
    "segment_block",
    "help_block",
    "interview_help_block",
    "grid_block",
    "item_grid_block",
    "address_autocomplete_block",
    "fields_item",
    "action_button_item",
    "need_item",
    "terms_item",
    "show_if_modifier",
    "unknown_nested",
]
InsertKind = Literal["scalar", "object", "array", "block_scalar"]


@dataclass(frozen=True, slots=True)
class PropertyRule:
    name: str
    value_types: tuple[str, ...]
    enum_values: tuple[str, ...]
    display_value_types: tuple[str, ...] | None = None
    description: str | None = None
    comment: str | None = None
    insert_kind: InsertKind = "scalar"


@dataclass(frozen=True, slots=True)
class SchemaMetadata:
    properties: dict[str, PropertyRule]
    top_level: dict[str, PropertyRule]
    metadata_block: dict[str, PropertyRule]
    metadata_author_item: dict[str, PropertyRule]
    metadata_social_block: dict[str, PropertyRule]
    metadata_social_twitter_block: dict[str, PropertyRule]
    metadata_social_og_block: dict[str, PropertyRule]
    attachment_metadata_block: dict[str, PropertyRule]
    attachment_fields_block: dict[str, PropertyRule]
    attachment_field_variable_item: dict[str, PropertyRule]
    sections_item: dict[str, PropertyRule]
    table_column_item: dict[str, PropertyRule]
    objects_item: dict[str, PropertyRule]
    objects_from_file_item: dict[str, PropertyRule]
    on_change_item: dict[str, PropertyRule]
    include_item: dict[str, PropertyRule]
    imports_item: dict[str, PropertyRule]
    modules_item: dict[str, PropertyRule]
    translations_item: dict[str, PropertyRule]
    reset_item: dict[str, PropertyRule]
    order_item: dict[str, PropertyRule]
    features_block: dict[str, PropertyRule]
    default_screen_parts_block: dict[str, PropertyRule]
    list_collect_block: dict[str, PropertyRule]
    image_set_block: dict[str, PropertyRule]
    validation_messages_block: dict[str, PropertyRule]
    review_item: dict[str, PropertyRule]
    review_field_item: dict[str, PropertyRule]
    attachment_item: dict[str, PropertyRule]
    attachment_options_block: dict[str, PropertyRule]
    segment_block: dict[str, PropertyRule]
    help_block: dict[str, PropertyRule]
    interview_help_block: dict[str, PropertyRule]
    grid_block: dict[str, PropertyRule]
    item_grid_block: dict[str, PropertyRule]
    address_autocomplete_block: dict[str, PropertyRule]
    fields_item: dict[str, PropertyRule]
    action_button_item: dict[str, PropertyRule]
    need_item: dict[str, PropertyRule]
    terms_item: dict[str, PropertyRule]
    show_if_modifier: dict[str, PropertyRule]
    unknown_nested: dict[str, PropertyRule]
    scoped_properties: dict[CompletionScope, dict[str, PropertyRule]]
    all_known_properties: dict[str, PropertyRule]


def _rule(
    name: str,
    *,
    value_types: tuple[str, ...] = (),
    enum_values: tuple[str, ...] = (),
    display_value_types: tuple[str, ...] | None = None,
    description: str | None = None,
    comment: str | None = None,
    insert_kind: InsertKind = "scalar",
) -> PropertyRule:
    return PropertyRule(
        name=name,
        value_types=value_types,
        enum_values=enum_values,
        display_value_types=display_value_types,
        description=description,
        comment=comment,
        insert_kind=insert_kind,
    )


def _rules(
    names: tuple[str, ...],
    *,
    value_types: tuple[str, ...],
    insert_kind: InsertKind = "scalar",
    enum_values: tuple[str, ...] = (),
    display_value_types: tuple[str, ...] | None = None,
    description: str | None = None,
    comment: str | None = None,
) -> dict[str, PropertyRule]:
    return {
        name: _rule(
            name,
            value_types=value_types,
            enum_values=enum_values,
            display_value_types=display_value_types,
            description=description,
            comment=comment,
            insert_kind=insert_kind,
        )
        for name in names
    }


_BOOLEAN_PY_EXPR_DISPLAY_TYPES = ("boolean", "python")
_TEMPLATE_STRING_DISPLAY_TYPES = ("string", "mako")
# Descriptions for keys with this display type intentionally omit
# "supports Mako/Markdown" since the display type annotations
# already convey this information.
_MARKDOWN_STRING_DISPLAY_TYPES = ("string", "mako", "markdown")
_PYTHON_EXPR_DISPLAY_TYPES = ("python",)


def _bool_expr_rule(
    name: str,
    *,
    enum_values: tuple[str, ...] = (),
    description: str | None = None,
    comment: str | None = None,
    insert_kind: InsertKind = "scalar",
) -> PropertyRule:
    return _rule(
        name,
        value_types=("boolean", "string"),
        enum_values=enum_values,
        display_value_types=_BOOLEAN_PY_EXPR_DISPLAY_TYPES,
        description=description,
        comment=comment,
        insert_kind=insert_kind,
    )


def _bool_expr_rules(
    names: tuple[str, ...],
    *,
    enum_values: tuple[str, ...] = (),
    description: str | None = None,
    comment: str | None = None,
    insert_kind: InsertKind = "scalar",
) -> dict[str, PropertyRule]:
    return _rules(
        names,
        value_types=("boolean", "string"),
        enum_values=enum_values,
        display_value_types=_BOOLEAN_PY_EXPR_DISPLAY_TYPES,
        description=description,
        comment=comment,
        insert_kind=insert_kind,
    )


def _merge_rule_maps(*maps: dict[str, PropertyRule]) -> dict[str, PropertyRule]:
    merged: dict[str, PropertyRule] = {}
    for item in maps:
        merged.update(item)
    return merged


_BOOTSTRAP_COLORS = (
    "primary",
    "secondary",
    "tertiary",
    "success",
    "danger",
    "warning",
    "info",
    "light",
    "dark",
    "link",
)

# Common IETF language tags (ISO 639-1) used in Docassemble interviews.
# The parser does not validate these values at runtime, but offering
# completions helps authors discover the standard format.
#
# ``_BLOCK_LANGUAGE_CODES`` is used for the ``language`` block-level modifier
# (scoped to a single question/block).  ``_INTERVIEW_LANGUAGE_CODES`` is used
# for the ``default language`` interview-global key (sets the fallback language
# for the entire interview).  Both accept IETF language tags; the constants are
# kept separate so they can evolve independently if the semantics diverge.
_BLOCK_LANGUAGE_CODES = (
    "en",
    "es",
    "fr",
    "de",
    "it",
    "pt",
    "nl",
    "ru",
    "zh",
    "ja",
    "ko",
    "ar",
    "sv",
    "da",
    "fi",
    "nb",
    "pl",
    "tr",
    "el",
    "he",
    "hi",
    "th",
    "vi",
    "cs",
    "ro",
    "hu",
    "uk",
)

_INTERVIEW_LANGUAGE_CODES = _BLOCK_LANGUAGE_CODES

_FIELD_DATATYPES = (
    "text",
    "password",
    "email",
    "number",
    "integer",
    "currency",
    "float",
    "date",
    "datetime",
    "time",
    "file",
    "files",
    "camera",
    "camcorder",
    "microphone",
    "user",
    "environment",
    "range",
    "object",
    "object_radio",
    "multiselect",
    "object_multiselect",
    "checkboxes",
    "object_checkboxes",
    "yesno",
    "yesnomaybe",
    "yesnoradio",
    "yesnowide",
    "noyes",
    "noyesmaybe",
    "noyesradio",
    "noyeswide",
    "ml",
    "mlarea",
    "area",
    "hidden",
    "radio",
    "dropdown",
    "pulldown",
    "combobox",
    "datalist",
    "ajax",
)

_FIELD_INPUT_TYPES = (
    "area",
    "hidden",
    "ajax",
    "radio",
    "dropdown",
    "pulldown",
    "combobox",
    "datalist",
)


@lru_cache(maxsize=1)
def _build_registry() -> SchemaMetadata:
    # Derived from the key allowlists and parsing branches in docassemble.base.parse.Question.__init__.
    _TOP_LEVEL_TEMPLATE_STRING_RULES = _rules(
        (
            "section",
            "resume button label",
            "back button label",
            "corner back button label",
            "script",
            "css",
            "css class",
            "table css class",
            "ga id",
            "segment id",
            "response filename",
            "content type",
            "redirect url",
            "edit header",
        ),
        value_types=("string",),
        display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
    )

    _TOP_LEVEL_TEXT_RULES = _rules(
        (
            "code",
            "event",
            "machine learning storage",
            "continue button field",
            "command",
            "variable name",
            "data from code",
            "id",
            "def",
            "generic object",
            "generic list object",
            "comment",
            "attachment code",
            "attachments code",
            "yesno",
            "noyes",
            "yesnomaybe",
            "noyesmaybe",
            "field",
            "target",
            "url",
            "response code",
        ),
        value_types=("string",),
    )

    _TOP_LEVEL_MAKO_RULES = _rules(
        (
            "default",
            "subject",
            "email template",
            "not available label",
        ),
        value_types=("string",),
        display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
    )

    _TOP_LEVEL_MAKO_BLOCK_SCALAR_RULE = {
        "mako": _rule(
            "mako",
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
            description=(
                "Mako template content for a def block. Supports ${} expressions, % directives, and <% %> Python blocks."
            ),
            insert_kind="block_scalar",
        ),
    }

    _TOP_LEVEL_PEN_COLOR_RULE = {
        "pen color": _rule(
            "pen color",
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
            description=(
                "CSS color for the signature pen. Accepts any valid CSS color name (e.g. 'blue') "
                "or hex value (e.g. '#0000FF'). "
                "See https://developer.mozilla.org/en-US/docs/Web/CSS/color for valid CSS color values."
            ),
        ),
    }

    _TOP_LEVEL_VALIDATION_CODE_RULE = {
        "validation code": _rule(
            "validation code",
            value_types=("string",),
            insert_kind="block_scalar",
            description=(
                "Python code that validates or transforms user input on a question screen. "
                "Runs after the user presses Continue; call validation_error() to reject input. "
                "Useful for cross-field validation that cannot be expressed with per-field rules."
            ),
        )
    }

    _TOP_LEVEL_OBJECT_RULES = _rules(
        (
            "features",
            "segment",
            "metadata",
            "question metadata",
            "filter",
            "default validation messages",
        ),
        value_types=("object",),
        insert_kind="object",
    )

    _TOP_LEVEL_ARRAY_RULES = _rules(
        (
            "order",
            "objects",
            "fields",
            "columns",
        ),
        value_types=("array",),
        insert_kind="array",
    )

    _TOP_LEVEL_LISTISH_RULES = _rules(
        (
            "sets",
            "only sets",
            "supersedes",
            "default role",
            "modules",
            "reset",
            "imports",
            "role",
            "include",
            "if",
            "require",
            "reconsider",
            "undefine",
            "usedefs",
            "depends on",
            "allowed to set",
        ),
        value_types=("string", "array"),
        insert_kind="array",
    )

    _TOP_LEVEL_BOOLEANISH_RULES = _bool_expr_rules(
        (
            "reload",
            "scan for variables",
            "prevent going back",
            "back button",
            "skip undefined",
            "list collect",
            "mandatory",
            "initial",
            "use objects",
            "allow emailing",
            "allow downloading",
            "include_internal",
            "check in",
            "shuffle",
            "show incomplete",
            "always include editable files",
            "include attachment notice",
            "include download tab",
            "describe file types",
            "manual attachment list",
            "hide continue button",
            "disable continue button",
            "required",
            "read only",
            "delete buttons",
        ),
    )

    _TOP_LEVEL_BOOLEANISH_STRING_RULES = {
        "breadcrumb": _rule(
            "breadcrumb",
            value_types=("boolean", "string"),
            enum_values=("True", "False"),
            display_value_types=("boolean", "string", "mako"),
        ),
        "tabular": _rule(
            "tabular",
            value_types=("boolean", "string"),
            enum_values=("True", "False"),
            display_value_types=("boolean", "string", "mako"),
        ),
        "show if empty": _rule(
            "show if empty",
            value_types=("boolean", "string"),
            enum_values=("True", "False"),
            display_value_types=("boolean", "string", "mako"),
        ),
    }

    _TOP_LEVEL_BOOLEAN_RULES = _rules(
        (
            "progressive",
            "auto open",
            "allow reordering",
            "confirm",
            "gathered",
            "all_variables",
            "null response",
        ),
        value_types=("boolean",),
    )

    _TOP_LEVEL_COMPLEX_RULES = _rules(
        (
            "action buttons",
            "choices",
            "buttons",
            "dropdown",
            "combobox",
            "review",
            "attachment",
            "attachments",
        ),
        value_types=("array", "object"),
        insert_kind="array",
    )

    _TOP_LEVEL_MIXED_OBJECT_RULES = _rules(
        (
            "table",
            "binaryresponse",
            "backgroundresponse",
            "decoration",
            "data",
            "rows",
            "edit",
            "attachment options",
        ),
        value_types=("string", "array", "object"),
        insert_kind="object",
    )

    _TOP_LEVEL_MEDIA_RULES = _rules(
        ("audio", "video"),
        value_types=("string", "array"),
        insert_kind="array",
    )

    _TOP_LEVEL_NEED_RULES = _rules(
        ("need",),
        value_types=("string", "array", "object"),
        insert_kind="array",
    )

    _TOP_LEVEL_OBJECT_IMPORT_RULES: dict[str, PropertyRule] = {}

    _TOP_LEVEL_TERMS_RULES = _rules(
        (),
        value_types=("array", "object"),
        insert_kind="object",
    )

    _TOP_LEVEL_IMAGE_RULES = _rules(
        ("image sets",),
        value_types=("object",),
        insert_kind="object",
    )

    _TABLE_BLOCK_RULES = _merge_rule_maps(
        _rules(("table",), value_types=("string", "object"), insert_kind="object"),
        _rules(("rows",), value_types=("string",), display_value_types=_PYTHON_EXPR_DISPLAY_TYPES),
        _rules(("columns",), value_types=("array",), insert_kind="array"),
        _rules(("require gathered",), value_types=("boolean",)),
        _rules(("allow reordering", "confirm"), value_types=("boolean",)),
        _rules(("edit",), value_types=("boolean", "array"), insert_kind="array"),
        _rules(("read only", "not available label"), value_types=("string",)),
        _rules(("edit header",), value_types=("string",), display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES),
        _rules(("sort key",), value_types=("string",), display_value_types=_PYTHON_EXPR_DISPLAY_TYPES),
        _rules(("indent",), value_types=("integer", "string")),
        _bool_expr_rules(("sort reverse",)),
    )

    _ATTACHMENT_BLOCK_RULES = _merge_rule_maps(
        _rules(
            (
                "attachment",
                "attachments",
                "attachment options",
                "attachment code",
                "attachments code",
            ),
            value_types=("array", "object", "string"),
            insert_kind="array",
        ),
        _bool_expr_rules(
            (
                "allow emailing",
                "allow downloading",
                "include attachment notice",
                "include download tab",
                "describe file types",
                "manual attachment list",
                "always include editable files",
            ),
        ),
        _rules(
            (
                "email subject",
                "email body",
                "email address default",
                "zip filename",
            ),
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
        ),
        _rules(
            ("email template",),
            value_types=("string",),
        ),
    )

    _TOP_LEVEL_SPECIAL_RULES = {
        "question": _rule(
            "question",
            value_types=("string",),
            display_value_types=_MARKDOWN_STRING_DISPLAY_TYPES,
            description="Question text for a Docassemble interview block.",
        ),
        "subquestion": _rule(
            "subquestion",
            value_types=("string",),
            display_value_types=_MARKDOWN_STRING_DISPLAY_TYPES,
            description="Explanatory text shown below the main question text.",
        ),
        "under": _rule(
            "under",
            value_types=("string",),
            display_value_types=_MARKDOWN_STRING_DISPLAY_TYPES,
            description=(
                "Text displayed below the buttons on a question screen. "
                "Useful for footnotes, caveats, or secondary prompts."
            ),
        ),
        "pre": _rule(
            "pre",
            value_types=("string",),
            display_value_types=_MARKDOWN_STRING_DISPLAY_TYPES,
            description="Text injected before the field inputs on a question screen.",
        ),
        "post": _rule(
            "post",
            value_types=("string",),
            display_value_types=_MARKDOWN_STRING_DISPLAY_TYPES,
            description="Text injected after the field inputs on a question screen.",
        ),
        "right": _rule(
            "right",
            value_types=("string",),
            display_value_types=_MARKDOWN_STRING_DISPLAY_TYPES,
            description=(
                "Text displayed in the right-side panel of a question screen. "
                "Often used for contextual help or sidebars."
            ),
        ),
        "field": _rule(
            "field",
            value_types=("string",),
            description=(
                "Variable set by a single-field question: the continue button sets this "
                "variable to True, or it captures a signature or other single value."
            ),
        ),
        "event": _rule(
            "event",
            value_types=("string", "array"),
            display_value_types=("string",),
            description=(
                "Event name for event-type blocks. "
                "The block fires when Docassemble seeks this event name in the interview logic."
            ),
        ),
        "continue button field": _rule(
            "continue button field",
            value_types=("string",),
            description=(
                "Variable set to True when the user clicks the continue button. "
                "Used to track whether the user has reached a particular screen."
            ),
        ),
        "yesno": _rule(
            "yesno",
            value_types=("string",),
            description=(
                "Boolean yes/no question: renders Yes/No buttons and sets the named variable to True (Yes) or False (No)."
            ),
        ),
        "noyes": _rule(
            "noyes",
            value_types=("string",),
            description=(
                "Boolean no/yes question (No shown first): sets the named variable to True (Yes) or False (No)."
            ),
        ),
        "yesnomaybe": _rule(
            "yesnomaybe",
            value_types=("string",),
            description=(
                "Three-choice yes/no/maybe question: sets the named variable to True (Yes), False (No), or None (Maybe)."
            ),
        ),
        "noyesmaybe": _rule(
            "noyesmaybe",
            value_types=("string",),
            description=(
                "Three-choice no/yes/maybe question (No shown first): sets the named variable to "
                "True (Yes), False (No), or None (Maybe)."
            ),
        ),
        "sets": _rule(
            "sets",
            value_types=("string", "array"),
            description=(
                "Variable names that this block sets, used to guide Docassemble's "
                "dependency logic when the variable is not obvious from the block keys."
            ),
            insert_kind="array",
        ),
        "only sets": _rule(
            "only sets",
            value_types=("string", "array"),
            description=(
                "Like sets, but tells Docassemble this block exclusively sets these "
                "variables and no others — overrides automatic variable scanning."
            ),
            insert_kind="array",
        ),
        "buttons": _rule(
            "buttons",
            value_types=("array", "object"),
            description=(
                "Choice buttons shown instead of a continue button. "
                "Each button can set a variable, navigate to an event, or link to a URL."
            ),
            insert_kind="array",
        ),
        "fields": _rule(
            "fields",
            value_types=("array",),
            description="Field definitions for a multi-input question block.",
            insert_kind="array",
        ),
        "features": _rule(
            "features",
            value_types=("object",),
            description="Interview-wide parser options from the features block.",
            insert_kind="object",
        ),
        "list collect": _rule(
            "list collect",
            value_types=("boolean", "string", "object"),
            description="Controls Docassemble list-collection behavior for fields blocks.",
            insert_kind="object",
        ),
        "action buttons": _rule(
            "action buttons",
            value_types=("array", "object"),
            description="Additional buttons shown with a question.",
            insert_kind="array",
        ),
        "attachment": _rule(
            "attachment",
            value_types=("array", "object"),
            description="Attachment definitions processed by Docassemble's attachment parser.",
            insert_kind="array",
        ),
        "attachments": _rule(
            "attachments",
            value_types=("array", "object"),
            description="Attachment definitions processed by Docassemble's attachment parser.",
            insert_kind="array",
        ),
        "attachment options": _rule(
            "attachment options",
            value_types=("object",),
            description="Global attachment defaults used when rendering documents.",
            insert_kind="object",
        ),
        "continue button color": _rule(
            "continue button color",
            value_types=("string",),
            enum_values=_BOOTSTRAP_COLORS,
            description="Bootstrap color class for the Continue button.",
        ),
        "resume button color": _rule(
            "resume button color",
            value_types=("string",),
            enum_values=_BOOTSTRAP_COLORS,
            description="Bootstrap color class for the Resume button on review screens.",
        ),
        "back button color": _rule(
            "back button color",
            value_types=("string",),
            enum_values=_BOOTSTRAP_COLORS,
            description="Bootstrap color class for the back button.",
        ),
        "sleep": _rule(
            "sleep",
            value_types=("integer", "number", "string"),
            description="Number of seconds to wait before proceeding to the next block.",
        ),
        "include": _rule(
            "include",
            value_types=("string", "array"),
            description=(
                "YAML files or package-qualified paths to include in this interview. "
                "Accepts a single path string or a list of path strings. "
                "Package-qualified form: docassemble.PackageName:data/questions/file.yml"
            ),
            insert_kind="array",
        ),
        "metadata": _rule(
            "metadata",
            value_types=("object",),
            description=(
                "Interview-level metadata such as title, authors, and description. "
                "Displayed on the interview list page and used by Docassemble for "
                "access control and documentation."
            ),
            insert_kind="object",
        ),
        "modules": _rule(
            "modules",
            value_types=("string", "array"),
            description=(
                "Python module names to import before executing the interview. "
                "Accepts a single module name string or a list of module name strings."
            ),
            insert_kind="array",
        ),
        "imports": _rule(
            "imports",
            value_types=("string", "array"),
            description=(
                "Raw Python import statements executed before the interview. "
                "Accepts a single import statement or a list of import statements."
            ),
            insert_kind="array",
        ),
        "objects": _rule(
            "objects",
            value_types=("array", "object"),
            description=(
                "Object declarations mapping variable names to class names. "
                "Docassemble instantiates each object and makes it available in the interview."
            ),
            insert_kind="array",
        ),
        "initial": _rule(
            "initial",
            value_types=("boolean", "string"),
            display_value_types=_BOOLEAN_PY_EXPR_DISPLAY_TYPES,
            description=(
                "When True, the accompanying code block runs at the start of every page "
                "load, not just when the variable it sets is needed."
            ),
        ),
        "mandatory": _rule(
            "mandatory",
            value_types=("boolean", "string"),
            display_value_types=_BOOLEAN_PY_EXPR_DISPLAY_TYPES,
            description=(
                "When True, this block must be visited or its code must run before the interview can complete."
            ),
        ),
        "code": _rule(
            "code",
            value_types=("string",),
            description="Python code block evaluated by Docassemble during the interview.",
            insert_kind="block_scalar",
        ),
        # -----------------------------------------------------------------------
        # Packet 4: Question Modifiers
        # -----------------------------------------------------------------------
        "if": _rule(
            "if",
            value_types=("string", "array"),
            display_value_types=_PYTHON_EXPR_DISPLAY_TYPES,
            description=(
                "Python expression (or list of expressions) that must evaluate to true for this "
                "block to be considered. All expressions must be true when a list is given."
            ),
            insert_kind="array",
        ),
        "need": _rule(
            "need",
            value_types=("string", "array", "object"),
            description=(
                "Variable name(s) that must be defined before this block runs. "
                "Accepts a single name string, a list of name strings, or a dict mapping "
                "names to pre/post conditions."
            ),
            insert_kind="array",
        ),
        "reconsider": _rule(
            "reconsider",
            value_types=("boolean", "string", "array"),
            description=(
                "Variable name(s) that Docassemble should undefine and recompute whenever this "
                "block is revisited. Pass true to reconsider all variables set by the block, "
                "a single variable name string, or a list of variable name strings."
            ),
            insert_kind="array",
        ),
        "undefine": _rule(
            "undefine",
            value_types=("string", "array"),
            description=(
                "Variable name(s) to undefine whenever this block is visited. "
                "Accepts a single variable name string or a list of variable name strings."
            ),
            insert_kind="array",
        ),
        "depends on": _rule(
            "depends on",
            value_types=("string", "array"),
            description=(
                "Variable name(s) whose re-evaluation should trigger re-evaluation of this block. "
                "Accepts a single variable name string or a list of variable name strings."
            ),
            insert_kind="array",
        ),
        "supersedes": _rule(
            "supersedes",
            value_types=("string", "array"),
            description=(
                "Block ID(s) that this block supersedes. When Docassemble would visit the named "
                "block, it uses this one instead. Accepts a single block ID string or a list."
            ),
            insert_kind="array",
        ),
        "role": _rule(
            "role",
            value_types=("string", "array"),
            description=(
                "Role(s) that are allowed to fill in this block. "
                "Accepts a single role name string or a list of role name strings."
            ),
            insert_kind="array",
        ),
        "allowed to set": _rule(
            "allowed to set",
            value_types=("string", "array"),
            description=(
                "Variable name(s) that this block is allowed to set, expressed as a Python "
                "expression or a list of variable name strings."
            ),
            insert_kind="array",
        ),
        "scan for variables": _rule(
            "scan for variables",
            value_types=("boolean", "string"),
            display_value_types=_BOOLEAN_PY_EXPR_DISPLAY_TYPES,
            description=(
                "Controls whether Docassemble scans this block for variable references. "
                "Set to false to skip automatic variable detection."
            ),
        ),
        "progress": _rule(
            "progress",
            value_types=("integer",),
            description=(
                "Progress bar value for this block (0–100). "
                "Sets the interview progress bar to this percentage when the block is displayed."
            ),
        ),
        "section": _rule(
            "section",
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
            description=(
                "Interview section that this block belongs to. "
                "Used with the sections block to organise the navigation sidebar."
            ),
        ),
        "comment": _rule(
            "comment",
            value_types=("string",),
            description="Developer comment attached to this block. Not shown to interview users.",
        ),
        "language": _rule(
            "language",
            value_types=("string",),
            enum_values=_BLOCK_LANGUAGE_CODES,
            description=(
                "IETF language tag (e.g. 'en', 'es') for this block. "
                "Docassemble uses the best match for the user's language."
            ),
        ),
        "generic object": _rule(
            "generic object",
            value_types=("string",),
            description=(
                "Docassemble class name that makes this block generic over all objects of that type "
                "(e.g. 'Individual'). The special variable x refers to the matched object."
            ),
        ),
        "variable name": _rule(
            "variable name",
            value_types=("string",),
            description=(
                "Variable name that this block sets, used when Docassemble cannot detect it "
                "automatically (e.g. for response or attachment blocks)."
            ),
        ),
        "decoration": _rule(
            "decoration",
            value_types=("string", "array", "object"),
            description="Image name or list of image names shown as decoration alongside the question.",
            insert_kind="object",
        ),
        "css class": _rule(
            "css class",
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
            description="CSS class(es) added to the question <div> for custom styling.",
        ),
        "table css class": _rule(
            "table css class",
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
            description="CSS class(es) added to the generated <table> element.",
        ),
        "review": _rule(
            "review",
            value_types=("array", "object"),
            description=(
                "Review screen definition: a list of items that each reference a field or fields "
                "on a review screen, with optional actions (set, undefine, invalidate, recompute, "
                "follow up). Each item needs a label and one or more field/fields references."
            ),
            insert_kind="array",
        ),
        "table": _rule(
            "table",
            value_types=("string", "object"),
            description=(
                "Table block for displaying collection data. Requires 'rows' (Python expression "
                "returning a list-like object) and 'columns' (list of dicts with 'header' and 'cell'). "
                "The value is a variable name string or an object with table options."
            ),
            insert_kind="object",
        ),
        "check in": _rule(
            "check in",
            value_types=("string",),
            description=(
                "Event name triggered at regular intervals while the user is on this page, enabling background polling."
            ),
        ),
        "skip undefined": _rule(
            "skip undefined",
            value_types=("boolean", "string"),
            display_value_types=_BOOLEAN_PY_EXPR_DISPLAY_TYPES,
            description=(
                "When true, Docassemble skips this block instead of raising an error if a referenced variable is undefined."
            ),
        ),
        "prevent going back": _rule(
            "prevent going back",
            value_types=("boolean", "string"),
            display_value_types=_BOOLEAN_PY_EXPR_DISPLAY_TYPES,
            description=(
                "When true, removes the back button from this screen and prevents the user "
                "from returning to a previous question."
            ),
        ),
        "back button": _rule(
            "back button",
            value_types=("boolean", "string"),
            display_value_types=_BOOLEAN_PY_EXPR_DISPLAY_TYPES,
            description=(
                "Controls visibility of the back button on this screen. Overrides the interview-wide setting."
            ),
        ),
        "hide continue button": _rule(
            "hide continue button",
            value_types=("boolean", "string"),
            display_value_types=_BOOLEAN_PY_EXPR_DISPLAY_TYPES,
            description=(
                "When true, the Continue button is hidden on this screen. "
                "Useful for screens where the user continues by pressing a buttons item."
            ),
        ),
        "disable continue button": _rule(
            "disable continue button",
            value_types=("boolean", "string"),
            display_value_types=_BOOLEAN_PY_EXPR_DISPLAY_TYPES,
            description=(
                "When true, the Continue button is rendered but disabled until the user "
                "fulfils some condition (e.g. signs a signature field)."
            ),
        ),
        "reload": _rule(
            "reload",
            value_types=("boolean", "integer", "string"),
            display_value_types=_BOOLEAN_PY_EXPR_DISPLAY_TYPES,
            description=(
                "Auto-reload the page. Pass true to use the default interval, an integer for "
                "a custom number of seconds, or a Python expression."
            ),
        ),
        "id": _rule(
            "id",
            value_types=("string",),
            description="Unique identifier for this block, used with supersedes, order, and analytics.",
        ),
        "ga id": _rule(
            "ga id",
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
            description="Google Analytics event ID sent when this block is displayed.",
        ),
        "segment id": _rule(
            "segment id",
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
            description="Segment.io event ID sent when this block is displayed.",
        ),
        "order": _rule(
            "order",
            value_types=("array",),
            description=(
                "List of block IDs specifying the order in which Docassemble should visit blocks in this interview."
            ),
            insert_kind="array",
        ),
        # -----------------------------------------------------------------------
        # Packet 4 cont'd: Commonly used keys with schema-only hover (Chunk 7)
        # -----------------------------------------------------------------------
        "template": _rule(
            "template",
            value_types=("string",),
            description=(
                "Template block name. Templates define Mako/Markdown content referenced by "
                "the template name. A template block must have a matching 'content' or 'content file'."
            ),
        ),
        "content": _rule(
            "content",
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
            description=(
                "Body of a template block. Supports Mako templating and Markdown formatting. "
                "The content is rendered when the template name is referenced in the interview."
            ),
            insert_kind="block_scalar",
        ),
        "content file": _rule(
            "content file",
            value_types=("string",),
            description=(
                "Path to an external file whose contents serve as the template body. "
                "Alternative to inline 'content' for templates."
            ),
        ),
        "default screen parts": _rule(
            "default screen parts",
            value_types=("object",),
            description=(
                "Interview-wide defaults for screen parts (title, subtitle, pre, post, under, "
                "right, footer, etc.). Supports Mako templating and is re-evaluated on every page load. "
                "Overrides metadata-level defaults but is overridden by question-specific parts."
            ),
            insert_kind="object",
        ),
        "on change": _rule(
            "on change",
            value_types=("object",),
            description=(
                "Mapping of variable names to actions triggered when those variables change value. "
                "Each entry defines a block or event to re-run when the variable is modified."
            ),
            insert_kind="object",
        ),
        "translations": _rule(
            "translations",
            value_types=("array",),
            description=(
                "List of language codes for which translations are provided. "
                "Used with the language modifier to support multi-language interviews."
            ),
            insert_kind="array",
        ),
        "sections": _rule(
            "sections",
            value_types=("array",),
            description=(
                "List of section definitions for the interview navigation sidebar. "
                "Each section groups related blocks under a heading in the nav menu."
            ),
            insert_kind="array",
        ),
        "default language": _rule(
            "default language",
            value_types=("string",),
            enum_values=_INTERVIEW_LANGUAGE_CODES,
            description=(
                "IETF language tag (e.g. 'en', 'es') for the interview's default language. "
                "Docassemble uses this when the user's preferred language has no matching content."
            ),
        ),
        "continue button label": _rule(
            "continue button label",
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
            description=(
                "Custom label for the Continue button. Overrides the interview-wide default for this specific question."
            ),
        ),
        "signature": _rule(
            "signature",
            value_types=("string",),
            description=(
                "Variable name that stores the user's signature as a DAFile image. "
                "Presents a signature capture screen where the user can draw with a pointing device."
            ),
        ),
        "datatype": _rule(
            "datatype",
            value_types=("string",),
            description=(
                "Data type for a top-level multiple-choice question (e.g. 'boolean', 'threestate'). "
                "Controls how the variable value is stored and validated."
            ),
        ),
        "terms": _rule(
            "terms",
            value_types=("array", "object"),
            description=(
                "List of term definitions shown to the user on a question screen. "
                "Each term has a name and a definition that appears in a popup or sidebar."
            ),
            insert_kind="object",
        ),
        "auto terms": _rule(
            "auto terms",
            value_types=("array", "object"),
            description=(
                "Automatically generated term definitions for a question. "
                "Docassemble scans the question text and creates term entries for known variables."
            ),
            insert_kind="object",
        ),
        "objects from file": _rule(
            "objects from file",
            value_types=("array", "object"),
            description=(
                "Object declarations loaded from an external Python file. "
                "Each entry maps a variable name to a class name sourced from the file."
            ),
            insert_kind="array",
        ),
        "interview help": _rule(
            "interview help",
            value_types=("string", "array", "object"),
            description=(
                "Help content for the entire interview, shown when the user clicks the help button. "
                "Accepts raw text, a list of sections, or an object with tab/page definitions."
            ),
            insert_kind="object",
        ),
        "action": _rule(
            "action",
            value_types=("string", "array", "object"),
            description=(
                "Action block for defining a server-side action handler. "
                "Actions are called via url_action() or action buttons and can return JSON responses."
            ),
            insert_kind="object",
        ),
        "response": _rule(
            "response",
            value_types=("string", "array", "object"),
            description=(
                "HTTP response block for returning custom content (HTML, JSON, redirect, etc.) "
                "directly to the browser without rendering a question screen."
            ),
            insert_kind="object",
        ),
        "help": _rule(
            "help",
            value_types=("string", "array", "object"),
            description=(
                "Top-level help block for a question screen. "
                "Supports tabbed or single-page help content displayed alongside the question."
            ),
            insert_kind="object",
        ),
        "images": _rule(
            "images",
            value_types=("object",),
            description=(
                "Image declarations mapping image names to file paths or DAFile objects. "
                "Used to decorate buttons, choices, and other UI elements with icons."
            ),
            insert_kind="object",
        ),
        # -----------------------------------------------------------------------
        # Packet 5: Keys with descriptions added for hover coverage
        # -----------------------------------------------------------------------
        "all_variables": _rule(
            "all_variables",
            value_types=("boolean",),
            description=("When true, the response block returns all interview variables as JSON."),
        ),
        "allow downloading": _rule(
            "allow downloading",
            value_types=("boolean", "string"),
            display_value_types=_BOOLEAN_PY_EXPR_DISPLAY_TYPES,
            description="When true, attachments can be downloaded by the user.",
        ),
        "allow emailing": _rule(
            "allow emailing",
            value_types=("boolean", "string"),
            display_value_types=_BOOLEAN_PY_EXPR_DISPLAY_TYPES,
            description="When true, attachments can be sent via email.",
        ),
        "allow reordering": _rule(
            "allow reordering",
            value_types=("boolean",),
            description="When true, allows users to reorder list items or table rows.",
        ),
        "always include editable files": _rule(
            "always include editable files",
            value_types=("boolean", "string"),
            display_value_types=_BOOLEAN_PY_EXPR_DISPLAY_TYPES,
            description="When true, editable source files are always included in exports.",
        ),
        "attachment code": _rule(
            "attachment code",
            value_types=("string",),
            description=(
                "Python code that generates attachment content dynamically. "
                "Alternative to inline content or content file for attachments."
            ),
            insert_kind="block_scalar",
        ),
        "attachments code": _rule(
            "attachments code",
            value_types=("string",),
            description=(
                "Python code that generates multiple attachments dynamically. "
                "Alternative to defining each attachment individually."
            ),
            insert_kind="block_scalar",
        ),
        "audio": _rule(
            "audio",
            value_types=("string", "array", "object"),
            description=(
                "Audio file or URL to play on the question screen. "
                "Accepts a single path, a list of format alternatives, or an object with audio options."
            ),
        ),
        "auto open": _rule(
            "auto open",
            value_types=("boolean",),
            description="When true, automatically opens the attachment preview in a new tab.",
        ),
        "back button label": _rule(
            "back button label",
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
            description="Custom label for the back button on this specific question.",
        ),
        "backgroundresponse": _rule(
            "backgroundresponse",
            value_types=("string", "object"),
            description=(
                "Background response block for triggering asynchronous processing without waiting for the result."
            ),
            insert_kind="object",
        ),
        "binaryresponse": _rule(
            "binaryresponse",
            value_types=("string", "object"),
            description=(
                "Binary response block for returning raw file content (e.g. images, PDFs) directly to the browser."
            ),
            insert_kind="object",
        ),
        "breadcrumb": _rule(
            "breadcrumb",
            value_types=("boolean", "string"),
            display_value_types=_BOOLEAN_PY_EXPR_DISPLAY_TYPES,
            description="When true, shows a breadcrumb navigation trail for the current section.",
        ),
        "choices": _rule(
            "choices",
            value_types=("array", "object"),
            description=(
                "List of choices for a multiple-choice question with radio buttons. "
                "Each choice can be a plain string label, a label/value pair, or an object "
                "with label, value, image, help, and other modifiers."
            ),
            insert_kind="array",
        ),
        "columns": _rule(
            "columns",
            value_types=("array",),
            description=(
                "Column definitions for a table block. Each entry specifies the column header "
                "and a cell expression for rendering the value."
            ),
            insert_kind="array",
        ),
        "combobox": _rule(
            "combobox",
            value_types=("array", "object"),
            description=(
                "Combobox (editable dropdown) for a multiple-choice question. "
                "Users can pick from the list or type a custom value."
            ),
            insert_kind="array",
        ),
        "command": _rule(
            "command",
            value_types=("string",),
            description=(
                "Special button action name (e.g. 'exit', 'restart', 'logout'). "
                "Triggers a Docassemble command instead of setting a variable."
            ),
        ),
        "confirm": _rule(
            "confirm",
            value_types=("boolean",),
            description="When true, shows a confirmation dialog before proceeding with the action.",
        ),
        "content type": _rule(
            "content type",
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
            description="MIME content type of the response (e.g. 'application/json', 'text/html').",
        ),
        "corner back button label": _rule(
            "corner back button label",
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
            description="Custom label for the back button in the upper-left corner of the screen.",
        ),
        "css": _rule(
            "css",
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
            description=(
                "CSS styling appended to the HTML <head> for this question. Raw HTML <style> tags or CSS rules."
            ),
        ),
        "data": _rule(
            "data",
            value_types=("object", "array"),
            description=(
                "Structured data defined inline in YAML format. "
                "The data is stored in the variable specified by the 'variable name' key."
            ),
        ),
        "data from code": _rule(
            "data from code",
            value_types=("string",),
            description=(
                "Structured data defined through Python code instead of YAML literals. "
                "The code is evaluated and the result is stored in the variable specified by 'variable name'."
            ),
            insert_kind="block_scalar",
        ),
        "default": _rule(
            "default",
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
            description="Default value for a field, displayed when the question is first shown.",
        ),
        "default role": _rule(
            "default role",
            value_types=("string",),
            description=(
                "Default role assignment for blocks that do not specify a role. "
                "Used in multi-user interviews to control access."
            ),
        ),
        "default validation messages": _rule(
            "default validation messages",
            value_types=("object",),
            description=(
                "Interview-wide default validation error messages for data types. "
                "Maps datatype names to custom error message strings."
            ),
            insert_kind="object",
        ),
        "def": _rule(
            "def",
            value_types=("string",),
            description="Named Python function definition block. Defines a reusable function in the interview.",
            insert_kind="block_scalar",
        ),
        "delete buttons": _rule(
            "delete buttons",
            value_types=("boolean", "string"),
            display_value_types=_BOOLEAN_PY_EXPR_DISPLAY_TYPES,
            description="When true, shows delete buttons for removing items from a list or collection.",
        ),
        "describe file types": _rule(
            "describe file types",
            value_types=("boolean", "string"),
            display_value_types=_BOOLEAN_PY_EXPR_DISPLAY_TYPES,
            description="When true, shows descriptions of available download file types to the user.",
        ),
        "dropdown": _rule(
            "dropdown",
            value_types=("array", "object"),
            description=(
                "Dropdown selector for a multiple-choice question. Users pick one option from a drop-down list."
            ),
            insert_kind="array",
        ),
        "edit": _rule(
            "edit",
            value_types=("object",),
            description=(
                "Edit configuration for table rows. Defines how users can add, modify, or remove rows in a data table."
            ),
            insert_kind="object",
        ),
        "edit header": _rule(
            "edit header",
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
            description="Header text displayed on the edit screen for table rows.",
        ),
        "email address default": _rule(
            "email address default",
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
            description="Default recipient email address for sending attachments from this interview.",
        ),
        "email body": _rule(
            "email body",
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
            description="Body text template for emails sent with attachments.",
        ),
        "email subject": _rule(
            "email subject",
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
            description="Subject line template for emails sent with attachments.",
        ),
        "email template": _rule(
            "email template",
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
            description="Template name or inline template for the email message body.",
        ),
        "filter": _rule(
            "filter",
            value_types=("object", "string"),
            description=(
                "Filter expression for list collection or table data. "
                "Limits which items are included based on a condition."
            ),
        ),
        "gathered": _rule(
            "gathered",
            value_types=("boolean",),
            description=(
                "When true, marks the list or dict as fully gathered, meaning Docassemble "
                "will not prompt for additional items."
            ),
        ),
        "generic list object": _rule(
            "generic list object",
            value_types=("string",),
            description=(
                "Makes this block generic over list items of the named object type. "
                "The special variable x refers to the current list item."
            ),
        ),
        "image sets": _rule(
            "image sets",
            value_types=("object",),
            description=(
                "Named collections of images with attribution text. "
                "Each entry maps a set name to an object with 'images' and optional 'attribution'."
            ),
            insert_kind="object",
        ),
        "include attachment notice": _rule(
            "include attachment notice",
            value_types=("boolean", "string"),
            display_value_types=_BOOLEAN_PY_EXPR_DISPLAY_TYPES,
            description="When true, includes a notice about the attachment download functionality.",
        ),
        "include download tab": _rule(
            "include download tab",
            value_types=("boolean", "string"),
            display_value_types=_BOOLEAN_PY_EXPR_DISPLAY_TYPES,
            description="When true, includes a download tab in the attachment preview interface.",
        ),
        "include_internal": _rule(
            "include_internal",
            value_types=("boolean", "string"),
            display_value_types=_BOOLEAN_PY_EXPR_DISPLAY_TYPES,
            description="When true, includes non-standard export formats in the download options.",
        ),
        "indent": _rule(
            "indent",
            value_types=("integer",),
            description="Indentation level for list items displayed in a table or review screen.",
        ),
        "machine learning storage": _rule(
            "machine learning storage",
            value_types=("string",),
            description=(
                "Variable name where machine learning training data is stored. "
                "Used with the ML datatype for model training."
            ),
        ),
        "manual attachment list": _rule(
            "manual attachment list",
            value_types=("boolean", "string"),
            display_value_types=_BOOLEAN_PY_EXPR_DISPLAY_TYPES,
            description="When true, allows users to manually select which attachments to include.",
        ),
        "not available label": _rule(
            "not available label",
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
            description="Label text shown when a choice or option is not available to the user.",
        ),
        "null response": _rule(
            "null response",
            value_types=("boolean",),
            description="When true, the response block returns an empty 204 No Content response.",
        ),
        "progressive": _rule(
            "progressive",
            value_types=("boolean",),
            description=(
                "When true, shows one field at a time in a progressive disclosure pattern "
                "instead of displaying all fields on the screen at once."
            ),
        ),
        "question metadata": _rule(
            "question metadata",
            value_types=("object",),
            description=(
                "Custom metadata associated with a question block. "
                "Arbitrary YAML structure passed through to the JSON representation of the question."
            ),
            insert_kind="object",
        ),
        "read only": _rule(
            "read only",
            value_types=("boolean", "string"),
            display_value_types=_BOOLEAN_PY_EXPR_DISPLAY_TYPES,
            description="When true, the field or table value is displayed but cannot be edited.",
        ),
        "redirect url": _rule(
            "redirect url",
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
            description="URL to redirect to after the action or response block completes.",
        ),
        "require": _rule(
            "require",
            value_types=("string", "array"),
            description=(
                "Variable names that must be defined before this block can be used. "
                "Accepts a single name string or a list of name strings."
            ),
            insert_kind="array",
        ),
        "require gathered": _rule(
            "require gathered",
            value_types=("boolean",),
            description=(
                "When true, requires the table or collection to be marked as gathered before it can be displayed."
            ),
        ),
        "required": _rule(
            "required",
            value_types=("boolean", "string"),
            display_value_types=_BOOLEAN_PY_EXPR_DISPLAY_TYPES,
            description="When true, the user must provide a value before continuing.",
        ),
        "reset": _rule(
            "reset",
            value_types=("string", "array"),
            description=(
                "List of variable names to reset (undefine) when this block is visited. "
                "Accepts a single name string or a list of name strings."
            ),
            insert_kind="array",
        ),
        "resume button label": _rule(
            "resume button label",
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
            description="Custom label for the Resume button on review screens.",
        ),
        "response code": _rule(
            "response code",
            value_types=("string",),
            description=(
                "Python code that generates the HTTP response dynamically. "
                "Evaluated to produce the response body and headers."
            ),
            insert_kind="block_scalar",
        ),
        "response filename": _rule(
            "response filename",
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
            description="Filename for the response download, used when returning a file to the browser.",
        ),
        "rows": _rule(
            "rows",
            value_types=("string", "array"),
            description=(
                "Table row definitions or a Python expression returning the rows to display. "
                "Each row is mapped through the table's column definitions."
            ),
        ),
        "script": _rule(
            "script",
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
            description="JavaScript code executed when the question screen loads in the browser.",
            insert_kind="block_scalar",
        ),
        "segment": _rule(
            "segment",
            value_types=("string", "object"),
            description=(
                "Segment.io event tracking configuration for this block. "
                "Accepts a segment event ID string or an object with id and arguments."
            ),
        ),
        "show if empty": _rule(
            "show if empty",
            value_types=("boolean", "string"),
            display_value_types=_BOOLEAN_PY_EXPR_DISPLAY_TYPES,
            description="When true, shows the question even if the referenced variable is already defined.",
        ),
        "show incomplete": _rule(
            "show incomplete",
            value_types=("boolean", "string"),
            display_value_types=_BOOLEAN_PY_EXPR_DISPLAY_TYPES,
            description="When true, shows incomplete items in a list or collection review screen.",
        ),
        "shuffle": _rule(
            "shuffle",
            value_types=("boolean", "string"),
            display_value_types=_BOOLEAN_PY_EXPR_DISPLAY_TYPES,
            description="When true, randomizes the order of choices, buttons, or table rows.",
        ),
        "sort key": _rule(
            "sort key",
            value_types=("string",),
            description=("Attribute name or key function for sorting table rows. Specifies the field to sort by."),
        ),
        "sort reverse": _rule(
            "sort reverse",
            value_types=("boolean",),
            description="When true, reverses the sort order of table rows.",
        ),
        "subject": _rule(
            "subject",
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
            description="Subject line for an attachment or email, supporting Mako templating.",
        ),
        "tabular": _rule(
            "tabular",
            value_types=("boolean", "string"),
            display_value_types=_BOOLEAN_PY_EXPR_DISPLAY_TYPES,
            description="When true, displays list items in a tabular format instead of a simple list.",
        ),
        "target": _rule(
            "target",
            value_types=("string",),
            description=(
                "Target variable name for a field or button value. "
                "Alternative to the 'field' key for some question types."
            ),
        ),
        "url": _rule(
            "url",
            value_types=("string",),
            description=("URL for a special button (e.g. exit, leave) to redirect to. Supports Mako templating."),
        ),
        "use objects": _rule(
            "use objects",
            value_types=("boolean", "string"),
            display_value_types=_BOOLEAN_PY_EXPR_DISPLAY_TYPES,
            description=(
                "When true, data and data from code blocks create DAList/DADict objects "
                "instead of plain Python lists and dicts."
            ),
        ),
        "usedefs": _rule(
            "usedefs",
            value_types=("string", "array"),
            description=(
                "Variable names that this block uses but does not define, expressed as "
                "a single name string or a list of name strings."
            ),
            insert_kind="array",
        ),
        "video": _rule(
            "video",
            value_types=("string", "array", "object"),
            description=(
                "Video file, URL, or YouTube embed code to display on the question screen. "
                "Accepts a single path, a list of format alternatives, or an object with video options."
            ),
        ),
        "zip filename": _rule(
            "zip filename",
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
            description="Filename for the zip archive when downloading multiple attachments.",
        ),
    }

    _TOP_LEVEL_RULES = _merge_rule_maps(
        _TOP_LEVEL_TEMPLATE_STRING_RULES,
        _TOP_LEVEL_TEXT_RULES,
        _TOP_LEVEL_MAKO_RULES,
        _TOP_LEVEL_MAKO_BLOCK_SCALAR_RULE,
        _TOP_LEVEL_PEN_COLOR_RULE,
        _TOP_LEVEL_VALIDATION_CODE_RULE,
        _TOP_LEVEL_OBJECT_RULES,
        _TOP_LEVEL_ARRAY_RULES,
        _TOP_LEVEL_LISTISH_RULES,
        _TOP_LEVEL_BOOLEANISH_RULES,
        _TOP_LEVEL_BOOLEANISH_STRING_RULES,
        _TOP_LEVEL_BOOLEAN_RULES,
        _TOP_LEVEL_COMPLEX_RULES,
        _TOP_LEVEL_MIXED_OBJECT_RULES,
        _TOP_LEVEL_MEDIA_RULES,
        _TOP_LEVEL_NEED_RULES,
        _TOP_LEVEL_OBJECT_IMPORT_RULES,
        _TOP_LEVEL_TERMS_RULES,
        _TOP_LEVEL_IMAGE_RULES,
        _TABLE_BLOCK_RULES,
        _ATTACHMENT_BLOCK_RULES,
        _TOP_LEVEL_SPECIAL_RULES,
    )

    _FEATURES_BOOLEAN_RULES = _rules(
        (
            "use catchall",
            "progress bar",
            "progress can go backwards",
            "show progress bar percentage",
            "question back button",
            "question help button",
            "navigation back button",
            "centered",
            "wide side by side",
            "debug",
            "cache documents",
            "pdf/a",
            "pdftk",
            "tagged pdf",
            "disable analytics",
            "hide navbar",
            "hide standard menu",
            "labels above fields",
            "suppress autofill",
            "floating labels",
            "send question data",
            "hide corner interface",
        ),
        value_types=("boolean",),
    )

    _FEATURES_SCALAR_RULES = _rules(
        (
            "progress bar method",
            "go full screen",
            "navigation",
            "small screen navigation",
            "maximum image size",
            "image upload type",
            "bootstrap theme",
            "inverse navbar",
            "popover trigger",
            "review button icon",
            "default date min",
            "default date max",
        ),
        value_types=("boolean", "string"),
        enum_values=("True", "False", "dropdown"),
    )

    _FEATURES_NUMERIC_RULES = _merge_rule_maps(
        _rules(("table width", "loop limit", "recursion limit", "checkin interval"), value_types=("integer",)),
        _rules(("progress bar multiplier",), value_types=("number",)),
    )

    _FEATURES_COLLECTION_RULES = _merge_rule_maps(
        _rules(
            (
                "custom datatypes to load",
                "auto jinja filter",
                "javascript",
                "css",
            ),
            value_types=("string", "array"),
            insert_kind="array",
        ),
        {"review button color": _rule("review button color", value_types=("string",), enum_values=_BOOTSTRAP_COLORS)},
    )

    _FEATURES_RULES = _merge_rule_maps(
        _FEATURES_BOOLEAN_RULES,
        _FEATURES_SCALAR_RULES,
        _FEATURES_NUMERIC_RULES,
        _FEATURES_COLLECTION_RULES,
        {
            "use catchall": _rule(
                "use catchall",
                value_types=("boolean",),
                description="When true, the interview catches undefined variables and shows a generic prompt.",
            ),
            "progress bar": _rule(
                "progress bar",
                value_types=("boolean",),
                description="When true, displays a progress bar showing the user's progress through the interview.",
            ),
            "progress can go backwards": _rule(
                "progress can go backwards",
                value_types=("boolean",),
                description="When true, allows the progress bar to decrease when revisiting earlier questions.",
            ),
            "show progress bar percentage": _rule(
                "show progress bar percentage",
                value_types=("boolean",),
                description="When true, shows the percentage value alongside the progress bar.",
            ),
            "question back button": _rule(
                "question back button",
                value_types=("boolean",),
                description="When true, adds a back button to the buttons area at the bottom of each screen.",
            ),
            "question help button": _rule(
                "question help button",
                value_types=("boolean",),
                description="When true, adds a help button to the buttons area when question-specific help is available.",
            ),
            "navigation back button": _rule(
                "navigation back button",
                value_types=("boolean",),
                description="When true, shows a back button in the navigation interface.",
            ),
            "centered": _rule(
                "centered",
                value_types=("boolean",),
                description="When true, centers question content on wide screens instead of a left-aligned layout.",
            ),
            "wide side by side": _rule(
                "wide side by side",
                value_types=("boolean",),
                description="When true, displays fields side by side on wide screens for a more compact layout.",
            ),
            "debug": _rule(
                "debug", value_types=("boolean",), description="When true, enables debug mode showing variable details."
            ),
            "cache documents": _rule(
                "cache documents",
                value_types=("boolean",),
                description="When true, caches assembled documents to avoid re-generating them.",
            ),
            "pdf/a": _rule(
                "pdf/a",
                value_types=("boolean",),
                description="When true, generates PDF documents in PDF/A archival format.",
            ),
            "pdftk": _rule(
                "pdftk",
                value_types=("boolean",),
                description="When true, uses PDFtk instead of Python's PDF library for PDF manipulation.",
            ),
            "tagged pdf": _rule(
                "tagged pdf",
                value_types=("boolean",),
                description="When true, generates tagged PDFs for improved accessibility.",
            ),
            "disable analytics": _rule(
                "disable analytics",
                value_types=("boolean",),
                description="When true, disables Google Analytics and other analytics tracking.",
            ),
            "hide navbar": _rule(
                "hide navbar",
                value_types=("boolean",),
                description="When true, hides the top navigation bar during the interview.",
            ),
            "hide standard menu": _rule(
                "hide standard menu",
                value_types=("boolean",),
                description="When true, hides the standard menu options from the user.",
            ),
            "labels above fields": _rule(
                "labels above fields",
                value_types=("boolean",),
                description="When true, renders field labels above the input instead of beside them.",
            ),
            "suppress autofill": _rule(
                "suppress autofill",
                value_types=("boolean",),
                description="When true, prevents the browser from auto-filling form fields.",
            ),
            "floating labels": _rule(
                "floating labels",
                value_types=("boolean",),
                description="When true, uses floating label style that moves the label above the field on focus.",
            ),
            "send question data": _rule(
                "send question data",
                value_types=("boolean",),
                description="When true, sends question data to the server for background processing.",
            ),
            "hide corner interface": _rule(
                "hide corner interface",
                value_types=("boolean",),
                description="When true, hides the corner navigation interface elements.",
            ),
            "progress bar method": _rule(
                "progress bar method",
                value_types=("boolean", "string"),
                enum_values=("True", "False", "dropdown"),
                description="Method for calculating progress: 'fixed' uses fixed percentages, 'dynamic' adapts automatically.",
            ),
            "go full screen": _rule(
                "go full screen",
                value_types=("boolean", "string"),
                enum_values=("True", "False", "dropdown"),
                description="When true, the interview opens in full-screen mode. Accepts True, False, or 'dropdown'.",
            ),
            "navigation": _rule(
                "navigation",
                value_types=("boolean", "string"),
                enum_values=("True", "False", "dropdown"),
                description="Navigation style: True for sidebar, False for none, 'dropdown' for a dropdown menu.",
            ),
            "small screen navigation": _rule(
                "small screen navigation",
                value_types=("boolean", "string"),
                enum_values=("True", "False", "dropdown"),
                description="Navigation style on small screens, overriding the navigation setting.",
            ),
            "maximum image size": _rule(
                "maximum image size",
                value_types=("boolean", "string"),
                enum_values=("True", "False", "dropdown"),
                description="Maximum allowed dimensions for uploaded images (e.g. '1024x768').",
            ),
            "image upload type": _rule(
                "image upload type",
                value_types=("boolean", "string"),
                enum_values=("True", "False", "dropdown"),
                description="Default format for uploaded images (e.g. 'jpg', 'png').",
            ),
            "bootstrap theme": _rule(
                "bootstrap theme",
                value_types=("boolean", "string"),
                enum_values=("True", "False", "dropdown"),
                description="Bootstrap theme name or URL for customizing the interview's visual appearance.",
            ),
            "inverse navbar": _rule(
                "inverse navbar",
                value_types=("boolean", "string"),
                enum_values=("True", "False", "dropdown"),
                description="When true, uses an inverted (dark) color scheme for the navigation bar.",
            ),
            "popover trigger": _rule(
                "popover trigger",
                value_types=("boolean", "string"),
                enum_values=("True", "False", "dropdown"),
                description="Event that triggers popovers: 'click', 'hover', 'focus', or 'manual'.",
            ),
            "review button icon": _rule(
                "review button icon",
                value_types=("boolean", "string"),
                enum_values=("True", "False", "dropdown"),
                description="Font Awesome icon name for the review button.",
            ),
            "default date min": _rule(
                "default date min",
                value_types=("boolean", "string"),
                enum_values=("True", "False", "dropdown"),
                description="Default minimum date for date fields across the interview.",
            ),
            "default date max": _rule(
                "default date max",
                value_types=("boolean", "string"),
                enum_values=("True", "False", "dropdown"),
                description="Default maximum date for date fields across the interview.",
            ),
            "table width": _rule(
                "table width",
                value_types=("integer",),
                description="Default width for table elements (in pixels or percentage).",
            ),
            "loop limit": _rule(
                "loop limit",
                value_types=("integer",),
                description="Maximum number of iterations for interview loops to prevent infinite loops.",
            ),
            "recursion limit": _rule(
                "recursion limit",
                value_types=("integer",),
                description="Maximum depth of recursion for interview logic.",
            ),
            "checkin interval": _rule(
                "checkin interval",
                value_types=("integer",),
                description="Interval in seconds for background check-in requests while on a page.",
            ),
            "progress bar multiplier": _rule(
                "progress bar multiplier",
                value_types=("number",),
                description="Multiplier for the automatic progress bar advancement between questions.",
            ),
            "custom datatypes to load": _rule(
                "custom datatypes to load",
                value_types=("string", "array"),
                description="List of custom datatype module paths to load for custom field types.",
                insert_kind="array",
            ),
            "auto jinja filter": _rule(
                "auto jinja filter",
                value_types=("string", "array"),
                description="List of Jinja2 filters to register automatically for DOCX templates.",
                insert_kind="array",
            ),
            "javascript": _rule(
                "javascript",
                value_types=("string", "array"),
                description="List of JavaScript file paths or URLs to include on every screen.",
                insert_kind="array",
            ),
            "css": _rule(
                "css",
                value_types=("string", "array"),
                description="List of CSS file paths or URLs to include in the interview.",
                insert_kind="array",
            ),
            "review button color": _rule(
                "review button color",
                value_types=("string",),
                enum_values=_BOOTSTRAP_COLORS,
                description="Bootstrap color class for the review button.",
            ),
        },
    )

    _DEFAULT_SCREEN_PARTS_TEXT_RULES = _rules(
        (
            "exit link",
            "exit label",
            "exit url",
            "full",
            "logo",
            "short logo",
            "title",
            "subtitle",
            "tab title",
            "short title",
            "title url",
            "title url opens in other window",
            "navigation bar html",
            "css class",
            "table css class",
            "date format",
            "time format",
            "datetime format",
            "help label",
            "continue button label",
            "resume button label",
            "back button label",
            "corner back button label",
        ),
        value_types=("string",),
        display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
    )

    _DEFAULT_SCREEN_PARTS_MARKDOWN_RULES = _rules(
        ("under", "right", "pre", "post", "footer", "submit"),
        value_types=("string",),
        display_value_types=_MARKDOWN_STRING_DISPLAY_TYPES,
    )

    _DEFAULT_SCREEN_PARTS_RULES = _merge_rule_maps(
        _DEFAULT_SCREEN_PARTS_TEXT_RULES,
        _DEFAULT_SCREEN_PARTS_MARKDOWN_RULES,
        {
            "exit link": _rule(
                "exit link",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Controls exit behavior: 'exit' deletes session, 'leave' preserves it.",
            ),
            "exit label": _rule(
                "exit label",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Label text for the exit link.",
            ),
            "exit url": _rule(
                "exit url",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="URL to redirect to when the user exits.",
            ),
            "full": _rule(
                "full",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Mako template string for the full screen content.",
            ),
            "logo": _rule(
                "logo",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Custom HTML content replacing the title in the navigation bar.",
            ),
            "short logo": _rule(
                "short logo",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Custom HTML replacing the logo on small screens.",
            ),
            "title": _rule(
                "title",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="The interview title displayed in the navigation bar.",
            ),
            "subtitle": _rule(
                "subtitle",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Subtitle shown in the interview list page.",
            ),
            "tab title": _rule(
                "tab title",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Browser tab title for the interview.",
            ),
            "short title": _rule(
                "short title",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Short form of the title shown on small screens.",
            ),
            "title url": _rule(
                "title url",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="URL opened when clicking the interview title.",
            ),
            "title url opens in other window": _rule(
                "title url opens in other window",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="When false, the title URL opens in the same window.",
            ),
            "navigation bar html": _rule(
                "navigation bar html",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="HTML content inserted into the navigation bar.",
            ),
            "css class": _rule(
                "css class",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Default CSS class added to the <body> of every screen.",
            ),
            "table css class": _rule(
                "table css class",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Default CSS class for HTML tables generated from Markdown.",
            ),
            "date format": _rule(
                "date format",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Default date format used by format_date().",
            ),
            "time format": _rule(
                "time format",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Default time format used by format_time().",
            ),
            "datetime format": _rule(
                "datetime format",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Default date/time format used by format_datetime().",
            ),
            "help label": _rule(
                "help label",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Default label text for the help tab or help button.",
            ),
            "continue button label": _rule(
                "continue button label",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Default label for the Continue button.",
            ),
            "resume button label": _rule(
                "resume button label",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Default label for the Resume button on review screens.",
            ),
            "back button label": _rule(
                "back button label",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Default label for the back button.",
            ),
            "corner back button label": _rule(
                "corner back button label",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Default label for the back button in the upper-left corner.",
            ),
            "under": _rule(
                "under",
                value_types=("string",),
                display_value_types=_MARKDOWN_STRING_DISPLAY_TYPES,
                description="Default content displayed below the buttons, supporting Markdown.",
            ),
            "right": _rule(
                "right",
                value_types=("string",),
                display_value_types=_MARKDOWN_STRING_DISPLAY_TYPES,
                description="Default content displayed on the right side of the screen.",
            ),
            "pre": _rule(
                "pre",
                value_types=("string",),
                display_value_types=_MARKDOWN_STRING_DISPLAY_TYPES,
                description="Default content displayed above the question area.",
            ),
            "post": _rule(
                "post",
                value_types=("string",),
                display_value_types=_MARKDOWN_STRING_DISPLAY_TYPES,
                description="Default content displayed after the under area.",
            ),
            "footer": _rule(
                "footer",
                value_types=("string",),
                display_value_types=_MARKDOWN_STRING_DISPLAY_TYPES,
                description="Default content displayed in the footer bar.",
            ),
            "submit": _rule(
                "submit",
                value_types=("string",),
                display_value_types=_MARKDOWN_STRING_DISPLAY_TYPES,
                description="Default content displayed above the buttons.",
            ),
            "continue button color": _rule(
                "continue button color",
                value_types=("string",),
                enum_values=_BOOTSTRAP_COLORS,
                description="Bootstrap color class for the Continue button.",
            ),
            "resume button color": _rule(
                "resume button color",
                value_types=("string",),
                enum_values=_BOOTSTRAP_COLORS,
                description="Bootstrap color class for the Resume button on review screens.",
            ),
            "back button color": _rule(
                "back button color",
                value_types=("string",),
                enum_values=_BOOTSTRAP_COLORS,
                description="Bootstrap color class for the back button.",
            ),
            "help button color": _rule(
                "help button color",
                value_types=("string",),
                enum_values=_BOOTSTRAP_COLORS,
                description="Bootstrap color class for the help button.",
            ),
        },
    )

    _METADATA_TEXT_OR_LANGUAGE_RULES = _rules(
        (
            "title",
            "short",
            "short title",
            "logo",
            "short logo",
            "documentation",
            "comment",
            "navigation bar html",
            "tab title",
            "subtitle",
            "title url",
            "date format",
            "datetime format",
            "time format",
            "exit url",
            "exit label",
            "pre",
            "submit",
            "post",
            "footer",
            "error help",
            "right",
            "under",
            "help label",
            "continue button label",
            "resume button label",
            "back button label",
            "corner back button label",
            "css class",
            "table css class",
        ),
        value_types=("string", "object"),
    )

    _METADATA_SCALAR_RULES = _merge_rule_maps(
        _rules(
            (
                "description",
                "revision_date",
                "default language",
                "email config",
                "error action",
            ),
            value_types=("string",),
        ),
        _rules(("example start", "example end"), value_types=("integer",)),
    )

    _METADATA_COLLECTION_RULES = _merge_rule_maps(
        _rules(("authors", "tags"), value_types=("array",), insert_kind="array"),
        _rules(
            ("required privileges", "required privileges for listing"),
            value_types=("string", "array"),
            insert_kind="array",
        ),
        _rules(
            ("required privileges for initiating",),
            value_types=("string", "array", "null"),
            insert_kind="array",
        ),
        _rules(("sessions are unique",), value_types=("boolean", "array"), insert_kind="array"),
        _rules(("social",), value_types=("object",), insert_kind="object"),
    )

    _METADATA_RULES = _merge_rule_maps(
        _METADATA_TEXT_OR_LANGUAGE_RULES,
        _METADATA_SCALAR_RULES,
        _METADATA_COLLECTION_RULES,
        {
            "title": _rule(
                "title",
                value_types=("string", "object"),
                description="The interview title, displayed in the navigation bar and interview list.",
            ),
            "short": _rule(
                "short",
                value_types=("string", "object"),
                description="Short form of the title shown on small screens.",
            ),
            "short title": _rule(
                "short title",
                value_types=("string", "object"),
                description="Short form of the title used on small screens as a fallback for the full title.",
            ),
            "logo": _rule(
                "logo",
                value_types=("string", "object"),
                description="Custom HTML content replacing the title in the navigation bar (e.g. an image).",
            ),
            "short logo": _rule(
                "short logo",
                value_types=("string", "object"),
                description="Custom HTML replacing the logo on small screens.",
            ),
            "documentation": _rule(
                "documentation",
                value_types=("string", "object"),
                description="URL or path linking to documentation for this interview.",
            ),
            "comment": _rule(
                "comment",
                value_types=("string", "object"),
                description="Developer comment attached to the interview metadata.",
            ),
            "navigation bar html": _rule(
                "navigation bar html",
                value_types=("string", "object"),
                description="HTML content inserted into the navigation bar for custom navigation items.",
            ),
            "tab title": _rule(
                "tab title",
                value_types=("string", "object"),
                description="Browser tab title for the interview. Falls back to 'title' if not set.",
            ),
            "subtitle": _rule(
                "subtitle",
                value_types=("string", "object"),
                description="Subtitle shown in the interview list page. Not visible during the interview.",
            ),
            "title url": _rule(
                "title url",
                value_types=("string", "object"),
                description="URL opened when the user clicks the interview title in the navigation bar.",
            ),
            "date format": _rule(
                "date format",
                value_types=("string", "object"),
                description="Default date format used by format_date() throughout the interview.",
            ),
            "datetime format": _rule(
                "datetime format",
                value_types=("string", "object"),
                description="Default date/time format used by format_datetime().",
            ),
            "time format": _rule(
                "time format",
                value_types=("string", "object"),
                description="Default time format used by format_time().",
            ),
            "exit url": _rule(
                "exit url",
                value_types=("string", "object"),
                description="URL to redirect to when the user exits the interview.",
            ),
            "exit label": _rule(
                "exit label",
                value_types=("string", "object"),
                description="Label text for the exit link in the navigation bar.",
            ),
            "pre": _rule(
                "pre",
                value_types=("string", "object"),
                description="HTML content displayed above the question area on every screen.",
            ),
            "submit": _rule(
                "submit",
                value_types=("string", "object"),
                description="HTML content displayed above the buttons on every screen.",
            ),
            "post": _rule(
                "post",
                value_types=("string", "object"),
                description="HTML content displayed below the under area on every screen.",
            ),
            "footer": _rule(
                "footer",
                value_types=("string", "object"),
                description="HTML content displayed in the footer bar at the bottom of every screen.",
            ),
            "error help": _rule(
                "error help",
                value_types=("string", "object"),
                description="Markdown text included on error screens to help guide users.",
            ),
            "right": _rule(
                "right",
                value_types=("string", "object"),
                description="HTML content displayed on the right side of every screen.",
            ),
            "under": _rule(
                "under",
                value_types=("string", "object"),
                description="HTML content displayed below the buttons on every screen.",
            ),
            "help label": _rule(
                "help label",
                value_types=("string", "object"),
                description="Default label text for the help tab or help button.",
            ),
            "continue button label": _rule(
                "continue button label",
                value_types=("string", "object"),
                description="Default label for the Continue button across all screens.",
            ),
            "resume button label": _rule(
                "resume button label",
                value_types=("string", "object"),
                description="Default label for the Resume button on review screens.",
            ),
            "back button label": _rule(
                "back button label",
                value_types=("string", "object"),
                description="Default label for the back button throughout the interview.",
            ),
            "corner back button label": _rule(
                "corner back button label",
                value_types=("string", "object"),
                description="Default label for the back button in the upper-left corner.",
            ),
            "css class": _rule(
                "css class",
                value_types=("string", "object"),
                description="Default CSS class added to the <body> element of every screen.",
            ),
            "table css class": _rule(
                "table css class",
                value_types=("string", "object"),
                description="Default CSS class for HTML tables generated from Markdown.",
            ),
            "description": _rule(
                "description",
                value_types=("string",),
                description="Description of the interview shown in the available interviews list.",
            ),
            "revision_date": _rule(
                "revision_date",
                value_types=("string",),
                description="Date of the last revision of the interview.",
            ),
            "default language": _rule(
                "default language",
                value_types=("string",),
                description="Default language code for the interview (e.g. 'en', 'es').",
            ),
            "email config": _rule(
                "email config",
                value_types=("string",),
                description="Name of the mail configuration to use for sending emails from this interview.",
            ),
            "error action": _rule(
                "error action",
                value_types=("string",),
                description="Event name triggered when an unhandled error occurs in the interview.",
            ),
            "example start": _rule(
                "example start",
                value_types=("integer",),
                description="Starting line marker used by docassemble's documentation screenshot tool.",
            ),
            "example end": _rule(
                "example end",
                value_types=("integer",),
                description="Ending line marker used by docassemble's documentation screenshot tool.",
            ),
            "authors": _rule(
                "authors",
                value_types=("array",),
                description="List of authors with name and organization for the interview.",
                insert_kind="array",
            ),
            "tags": _rule(
                "tags",
                value_types=("array",),
                description="List of tags categorizing the interview for list filtering.",
                insert_kind="array",
            ),
            "required privileges": _rule(
                "required privileges",
                value_types=("string", "array"),
                description="List of privileges required to access this interview.",
                insert_kind="array",
            ),
            "required privileges for listing": _rule(
                "required privileges for listing",
                value_types=("string", "array"),
                description="Privileges required for the interview to appear in the listing page.",
                insert_kind="array",
            ),
            "required privileges for initiating": _rule(
                "required privileges for initiating",
                value_types=("string", "array", "null"),
                description="Privileges required to start a new session of the interview.",
                insert_kind="array",
            ),
            "sessions are unique": _rule(
                "sessions are unique",
                value_types=("boolean", "array"),
                description="When true, each user can have only one active session of this interview.",
                insert_kind="array",
            ),
            "social": _rule(
                "social",
                value_types=("object",),
                description="Social media meta tag configuration for the interview page (Open Graph, Twitter Card).",
                insert_kind="object",
            ),
            "title url opens in other window": _rule(
                "title url opens in other window",
                value_types=("boolean", "object"),
                description="When false, the title URL opens in the same window instead of a new tab.",
            ),
            "exit link": _rule(
                "exit link",
                value_types=("string", "object"),
                enum_values=("exit", "leave", "logout", "exit_logout"),
                description="Controls exit behavior: 'exit' deletes the session, 'leave' preserves it, 'logout' logs the user out.",
            ),
            "unlisted": _rule(
                "unlisted",
                value_types=("boolean",),
                description="When true, excludes the interview from the available interviews list.",
            ),
            "hidden": _rule(
                "hidden",
                value_types=("boolean",),
                description="When true, omits interview sessions from the My Interviews listing.",
            ),
            "temporary session": _rule(
                "temporary session",
                value_types=("boolean",),
                description="When true, deletes any existing session and starts a fresh one.",
            ),
            "require login": _rule(
                "require login",
                value_types=("boolean",),
                description="When true, non-logged-in users are denied access to the interview.",
            ),
            "show login": _rule(
                "show login",
                value_types=("boolean",),
                description="When false, hides the sign-in link from the interview interface.",
            ),
            "suppress loading util": _rule(
                "suppress loading util",
                value_types=("boolean",),
                description="When true, prevents the automatic import of docassemble.base.util names.",
            ),
            "continue button color": _rule(
                "continue button color",
                value_types=("string", "object"),
                enum_values=_BOOTSTRAP_COLORS,
                description="Bootstrap color class for the Continue button.",
            ),
            "resume button color": _rule(
                "resume button color",
                value_types=("string", "object"),
                enum_values=_BOOTSTRAP_COLORS,
                description="Bootstrap color class for the Resume button on review screens.",
            ),
            "back button color": _rule(
                "back button color",
                value_types=("string", "object"),
                enum_values=_BOOTSTRAP_COLORS,
                description="Bootstrap color class for the back button.",
            ),
            "help button color": _rule(
                "help button color",
                value_types=("string", "object"),
                enum_values=_BOOTSTRAP_COLORS,
                description="Bootstrap color class for the help button.",
            ),
        },
    )

    _METADATA_AUTHOR_ITEM_RULES = {
        "name": _rule("name", value_types=("string",), description="Author name for the interview metadata."),
        "organization": _rule(
            "organization", value_types=("string",), description="Author organization for the interview metadata."
        ),
    }

    _METADATA_SOCIAL_RULES = {
        "name": _rule("name", value_types=("string",), description="Social meta tag name for the interview page."),
        "description": _rule(
            "description",
            value_types=("string",),
            description="Social meta description for the interview page.",
        ),
        "image": _rule("image", value_types=("string",), description="Social meta image URL for the interview page."),
        "twitter": _rule(
            "twitter", value_types=("object",), description="Twitter Card meta tag configuration.", insert_kind="object"
        ),
        "og": _rule(
            "og", value_types=("object",), description="Open Graph meta tag configuration.", insert_kind="object"
        ),
    }

    _METADATA_SOCIAL_TWITTER_RULES = {
        "card": _rule(
            "card", value_types=("string",), description="Twitter Card type (e.g. 'summary', 'summary_large_image')."
        ),
        "title": _rule("title", value_types=("string",), description="Twitter Card title for the interview page."),
        "site": _rule("site", value_types=("string",), description="Twitter @username for the site."),
        "description": _rule(
            "description", value_types=("string",), description="Twitter Card description for the interview page."
        ),
        "image": _rule("image", value_types=("string",), description="Twitter Card image URL for the interview page."),
        "image:alt": _rule("image:alt", value_types=("string",), description="Alt text for the Twitter Card image."),
    }

    _METADATA_SOCIAL_OG_RULES = {
        "title": _rule("title", value_types=("string",), description="Open Graph title for the interview page."),
        "url": _rule("url", value_types=("string",), description="Open Graph URL for the interview page."),
        "site_name": _rule(
            "site_name", value_types=("string",), description="Open Graph site name for the interview page."
        ),
        "locale": _rule("locale", value_types=("string",), description="Open Graph locale for the interview page."),
        "type": _rule(
            "type", value_types=("string",), description="Open Graph type for the interview page (e.g. 'website')."
        ),
        "description": _rule(
            "description", value_types=("string",), description="Open Graph description for the interview page."
        ),
        "image": _rule("image", value_types=("string",), description="Open Graph image URL for the interview page."),
    }

    _ATTACHMENT_METADATA_TEXT_RULES = _merge_rule_maps(
        _rules(
            (
                "title",
                "date",
                "fontsize",
                "IndentationAmount",
                "FirstFooterLeft",
                "FirstFooterCenter",
                "FirstFooterRight",
                "FirstHeaderLeft",
                "FirstHeaderCenter",
                "FirstHeaderRight",
                "FooterLeft",
                "FooterCenter",
                "FooterRight",
                "HeaderLeft",
                "HeaderCenter",
                "HeaderRight",
                "fontfamily",
                "lang",
                "mainlang",
                "papersize",
                "documentclass",
                "geometry",
                "TopMargin",
                "BottomMargin",
                "FooterSkip",
                "author-meta",
                "title-meta",
                "citecolor",
                "urlcolor",
                "linkcolor",
                "abstract",
            ),
            value_types=("string",),
        ),
        {
            "fontsize": _rule("fontsize", value_types=("string",), enum_values=("10pt", "11pt", "12pt")),
        },
    )

    _ATTACHMENT_METADATA_COLLECTION_RULES = _merge_rule_maps(
        _rules(("author",), value_types=("string", "array"), insert_kind="array"),
        _rules(("header-includes",), value_types=("string", "array"), insert_kind="array"),
    )

    _ATTACHMENT_METADATA_BOOLEANISH_RULES = _rules(
        (
            "toc",
            "SingleSpacing",
            "OneAndAHalfSpacing",
            "DoubleSpacing",
            "TripleSpacing",
            "Indentation",
            "HangingIndent",
            "numbersections",
        ),
        value_types=("boolean", "string"),
    )

    _ATTACHMENT_METADATA_RULES = _merge_rule_maps(
        _ATTACHMENT_METADATA_TEXT_RULES,
        _ATTACHMENT_METADATA_COLLECTION_RULES,
        _ATTACHMENT_METADATA_BOOLEANISH_RULES,
        {
            "title": _rule("title", value_types=("string",), description="Document title passed to Pandoc metadata."),
            "date": _rule("date", value_types=("string",), description="Document date passed to Pandoc metadata."),
            "fontsize": _rule(
                "fontsize",
                value_types=("string",),
                enum_values=("10pt", "11pt", "12pt"),
                description="Font size for the generated PDF (10pt, 11pt, or 12pt).",
            ),
            "IndentationAmount": _rule(
                "IndentationAmount",
                value_types=("string",),
                description="Amount of first-line indentation (e.g. '0.5in').",
            ),
            "FirstFooterLeft": _rule(
                "FirstFooterLeft",
                value_types=("string",),
                description="Left footer text on the first page of the document.",
            ),
            "FirstFooterCenter": _rule(
                "FirstFooterCenter",
                value_types=("string",),
                description="Center footer text on the first page of the document.",
            ),
            "FirstFooterRight": _rule(
                "FirstFooterRight",
                value_types=("string",),
                description="Right footer text on the first page of the document.",
            ),
            "FirstHeaderLeft": _rule(
                "FirstHeaderLeft",
                value_types=("string",),
                description="Left header text on the first page of the document.",
            ),
            "FirstHeaderCenter": _rule(
                "FirstHeaderCenter",
                value_types=("string",),
                description="Center header text on the first page of the document.",
            ),
            "FirstHeaderRight": _rule(
                "FirstHeaderRight",
                value_types=("string",),
                description="Right header text on the first page of the document.",
            ),
            "FooterLeft": _rule(
                "FooterLeft",
                value_types=("string",),
                description="Left footer text on subsequent pages of the document.",
            ),
            "FooterCenter": _rule(
                "FooterCenter",
                value_types=("string",),
                description="Center footer text on subsequent pages of the document.",
            ),
            "FooterRight": _rule(
                "FooterRight",
                value_types=("string",),
                description="Right footer text on subsequent pages of the document.",
            ),
            "HeaderLeft": _rule(
                "HeaderLeft",
                value_types=("string",),
                description="Left header text on subsequent pages of the document.",
            ),
            "HeaderCenter": _rule(
                "HeaderCenter",
                value_types=("string",),
                description="Center header text on subsequent pages of the document.",
            ),
            "HeaderRight": _rule(
                "HeaderRight",
                value_types=("string",),
                description="Right header text on subsequent pages of the document.",
            ),
            "fontfamily": _rule(
                "fontfamily",
                value_types=("string",),
                description="Font family for PDF output (default: 'Times New Roman').",
            ),
            "lang": _rule(
                "lang",
                value_types=("string",),
                description="Language code for babel/polyglossia LaTeX packages.",
            ),
            "mainlang": _rule(
                "mainlang",
                value_types=("string",),
                description="Main language for polyglossia LaTeX package.",
            ),
            "papersize": _rule(
                "papersize",
                value_types=("string",),
                description="Paper size for PDF output (e.g. 'letterpaper', 'a4paper').",
            ),
            "documentclass": _rule(
                "documentclass",
                value_types=("string",),
                description="LaTeX document class for PDF generation (default: 'article').",
            ),
            "geometry": _rule(
                "geometry",
                value_types=("string",),
                description="Page geometry options passed to the LaTeX geometry package.",
            ),
            "TopMargin": _rule(
                "TopMargin",
                value_types=("string",),
                description="Top margin of the document (default: '1in').",
            ),
            "BottomMargin": _rule(
                "BottomMargin",
                value_types=("string",),
                description="Bottom margin of the document (default: '1in').",
            ),
            "FooterSkip": _rule(
                "FooterSkip",
                value_types=("string",),
                description="Vertical space between the footer and the document body.",
            ),
            "author-meta": _rule(
                "author-meta",
                value_types=("string",),
                description="PDF metadata author field.",
            ),
            "title-meta": _rule(
                "title-meta",
                value_types=("string",),
                description="PDF metadata title field.",
            ),
            "citecolor": _rule(
                "citecolor",
                value_types=("string",),
                description="Color for citation hyperlinks in the generated PDF.",
            ),
            "urlcolor": _rule(
                "urlcolor",
                value_types=("string",),
                description="Color for URL hyperlinks in the generated PDF.",
            ),
            "linkcolor": _rule(
                "linkcolor",
                value_types=("string",),
                description="Color for internal hyperlinks in the generated PDF.",
            ),
            "abstract": _rule(
                "abstract",
                value_types=("string",),
                description="Document abstract content included in the LaTeX output.",
            ),
            "author": _rule(
                "author",
                value_types=("string", "array"),
                description="List of document authors for Pandoc metadata.",
                insert_kind="array",
            ),
            "header-includes": _rule(
                "header-includes",
                value_types=("string", "array"),
                description="LaTeX code included in the document header for custom formatting.",
                insert_kind="array",
            ),
            "toc": _rule(
                "toc",
                value_types=("boolean", "string"),
                description="When true, includes a table of contents in the generated document.",
            ),
            "SingleSpacing": _rule(
                "SingleSpacing",
                value_types=("boolean", "string"),
                description="When true, uses single line spacing with no first-line indentation.",
            ),
            "OneAndAHalfSpacing": _rule(
                "OneAndAHalfSpacing",
                value_types=("boolean", "string"),
                description="When true, uses 1.5 line spacing with first-line indentation.",
            ),
            "DoubleSpacing": _rule(
                "DoubleSpacing",
                value_types=("boolean", "string"),
                description="When true, uses double line spacing with first-line indentation (default).",
            ),
            "TripleSpacing": _rule(
                "TripleSpacing",
                value_types=("boolean", "string"),
                description="When true, uses triple line spacing with first-line indentation.",
            ),
            "Indentation": _rule(
                "Indentation",
                value_types=("boolean", "string"),
                description="When true, enables first-line paragraph indentation in single-spaced mode.",
            ),
            "HangingIndent": _rule(
                "HangingIndent",
                value_types=("boolean", "string"),
                description="When true, uses hanging indentation for list items in PDF output.",
            ),
            "numbersections": _rule(
                "numbersections",
                value_types=("boolean", "string"),
                description="When true, sections are automatically numbered in the document.",
            ),
        },
    )

    _ATTACHMENT_FIELDS_RULES: dict[str, PropertyRule] = {}

    _ATTACHMENT_FIELD_VARIABLE_ITEM_RULES: dict[str, PropertyRule] = {}

    _SECTIONS_ITEM_RULES = {
        "subsections": _rule(
            "subsections",
            value_types=("array",),
            insert_kind="array",
            description="Nested subsections within a section for hierarchical navigation.",
        ),
    }

    _TABLE_COLUMN_ITEM_RULES = {
        "header": _rule(
            "header",
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
            description="Column header text displayed in the table.",
        ),
        "cell": _rule(
            "cell",
            value_types=("string",),
            display_value_types=_PYTHON_EXPR_DISPLAY_TYPES,
            description="Python expression that produces the cell value for each row.",
        ),
    }

    _OBJECTS_ITEM_RULES: dict[str, PropertyRule] = {}

    _OBJECTS_FROM_FILE_ITEM_RULES: dict[str, PropertyRule] = {}

    _ON_CHANGE_ITEM_RULES: dict[str, PropertyRule] = {}

    _INCLUDE_ITEM_RULES: dict[str, PropertyRule] = {}

    _IMPORTS_ITEM_RULES: dict[str, PropertyRule] = {}

    _MODULES_ITEM_RULES: dict[str, PropertyRule] = {}

    _TRANSLATIONS_ITEM_RULES: dict[str, PropertyRule] = {}

    _RESET_ITEM_RULES: dict[str, PropertyRule] = {}

    _ORDER_ITEM_RULES: dict[str, PropertyRule] = {}

    _LIST_COLLECT_RULES = {
        "label": _rule(
            "label",
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
            description="Label for the list-collection interface shown to the user.",
        ),
        "add another label": _rule(
            "add another label",
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
            description="Text for the 'add another item' button in list collection.",
        ),
        "enable": _rule(
            "enable",
            value_types=("boolean", "string"),
            description="When true, enables the list collection interface.",
        ),
        "is final": _rule(
            "is final",
            value_types=("boolean", "string"),
            description="When true, marks the current item as final and closes the collection.",
        ),
        "allow append": _rule(
            "allow append",
            value_types=("boolean", "string"),
            description="When true, allows the user to append new items to the list.",
        ),
        "allow delete": _rule(
            "allow delete",
            value_types=("boolean", "string"),
            description="When true, allows the user to delete items from the list.",
        ),
    }

    _IMAGE_SET_RULES = {
        "attribution": _rule(
            "attribution",
            value_types=("string",),
            description="Attribution text for the image set, displayed at the bottom of screens using these images.",
        ),
        "images": _rule(
            "images",
            value_types=("object", "array"),
            insert_kind="object",
            description="Dictionary mapping image names to file paths within the set.",
        ),
    }

    _VALIDATION_MESSAGES_RULES = _rules(
        (
            "required",
            "combobox required",
            "multiple choice required",
            "file required",
            "checkboxes required",
            "minlength",
            "maxlength",
            "minmax",
            "min",
            "max",
            "date",
            "date min",
            "date max",
            "date minmax",
            "time",
            "datetime",
            "email",
            "number",
            "integer",
            "step",
            "accept",
            "maxuploadsize",
            "checkbox minlength",
            "checkbox maxlength",
            "checkbox minmaxlength",
            "multiselect minlength",
            "multiselect maxlength",
            "multiselect minmaxlength",
            "checkatleast",
            "checkatmost",
            "checkexactly",
            "selectexactly",
            "uncheckothers",
        ),
        value_types=("string",),
        description="Known validation message keys used by docassemble.base.parse.",
    )

    _REVIEW_ITEM_RULES = _merge_rule_maps(
        _rules(("label",), value_types=("string",), display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES),
        _rules(("action", "button", "css class"), value_types=("string",)),
        _rules(
            ("field",), value_types=("string", "array"), display_value_types=("python", "array"), insert_kind="array"
        ),
        _rules(
            ("fields", "show if"),
            value_types=("string", "array"),
            display_value_types=("python", "array"),
            insert_kind="array",
        ),
        _rules(("help",), value_types=("string", "array", "object"), insert_kind="object"),
        _rules(
            ("note", "html", "raw html"), value_types=("string",), display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES
        ),
        {
            "label": _rule(
                "label",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Label text for this review item, shown to the user on the review screen.",
            ),
            "action": _rule(
                "action",
                value_types=("string",),
                description="Action name triggered when the user interacts with this review item.",
            ),
            "button": _rule(
                "button",
                value_types=("string",),
                description="Label text for the review item's action button.",
            ),
            "css class": _rule(
                "css class",
                value_types=("string",),
                description="CSS class applied to this review item element.",
            ),
            "field": _rule(
                "field",
                value_types=("string", "array"),
                display_value_types=("python", "array"),
                description="Name of the variable shown or edited in this review item.",
                insert_kind="array",
            ),
            "fields": _rule(
                "fields",
                value_types=("string", "array"),
                display_value_types=("python", "array"),
                description="List of variable names shown or edited in this review item.",
                insert_kind="array",
            ),
            "show if": _rule(
                "show if",
                value_types=("string", "array"),
                display_value_types=("python", "array"),
                description="Condition controlling whether this review item is displayed.",
                insert_kind="array",
            ),
            "help": _rule(
                "help",
                value_types=("string", "array", "object"),
                description="Help text displayed alongside this review item.",
                insert_kind="object",
            ),
            "note": _rule(
                "note",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Informational note displayed as part of the review item.",
            ),
            "html": _rule(
                "html",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Raw HTML content displayed as part of the review item.",
            ),
            "raw html": _rule(
                "raw html",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Raw HTML inserted without an enclosing element in the review item.",
            ),
        },
    )

    _REVIEW_FIELD_ITEM_RULES = _merge_rule_maps(
        _rules(
            ("set", "follow up", "undefine", "invalidate", "recompute"), value_types=("array",), insert_kind="array"
        ),
        _rules(("action",), value_types=("string",)),
        _rules(("arguments",), value_types=("object",), insert_kind="object"),
        {
            "set": _rule(
                "set",
                value_types=("array",),
                description="Variable names to set to their current values when this action is triggered.",
                insert_kind="array",
            ),
            "follow up": _rule(
                "follow up",
                value_types=("array",),
                description="Event names to trigger as follow-up actions when this item is reviewed.",
                insert_kind="array",
            ),
            "undefine": _rule(
                "undefine",
                value_types=("array",),
                description="Variable names to undefine when this review action is triggered.",
                insert_kind="array",
            ),
            "invalidate": _rule(
                "invalidate",
                value_types=("array",),
                description="Variable names to invalidate (mark as needing re-asking) on review.",
                insert_kind="array",
            ),
            "recompute": _rule(
                "recompute",
                value_types=("array",),
                description="Variable names to recompute when this review action is triggered.",
                insert_kind="array",
            ),
            "action": _rule(
                "action",
                value_types=("string",),
                description="Action name to run when the review field item is activated.",
            ),
            "arguments": _rule(
                "arguments",
                value_types=("object",),
                description="Arguments passed to the review action.",
                insert_kind="object",
            ),
        },
    )

    _ATTACHMENT_ITEM_IDENTITY_RULES = _merge_rule_maps(
        _rules(
            ("file", "language", "variable name"),
            value_types=("string",),
        ),
        _rules(
            ("name", "filename", "description"),
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
        ),
        _rules(
            ("content", "checkbox export value", "hyperlink style", "rendering font"),
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
        ),
    )

    _ATTACHMENT_ITEM_TEMPLATE_RULES = _merge_rule_maps(
        _rules(
            ("initial yaml", "additional yaml", "valid formats", "valid types"),
            value_types=("string", "array"),
            insert_kind="array",
        ),
        _rules(
            (
                "template file",
                "rtf template file",
                "docx reference file",
                "pdf template file",
                "docx template file",
                "content file",
            ),
            value_types=("string", "object"),
            insert_kind="object",
        ),
    )

    _ATTACHMENT_ITEM_PERMISSION_RULES = _merge_rule_maps(
        _bool_expr_rules(("persistent", "private", "editable", "update references")),
        _rules(("allow privileges",), value_types=("string", "array", "object"), insert_kind="array"),
        _rules(("allow users",), value_types=("string", "integer", "array", "object"), insert_kind="array"),
    )

    _ATTACHMENT_ITEM_DOCUMENT_RULES = _merge_rule_maps(
        _bool_expr_rules(("skip undefined", "redact", "pdf/a", "pdftk", "tagged pdf")),
        _rules(
            ("decimal places",), value_types=("integer", "string"), display_value_types=("integer", "string", "mako")
        ),
        _rules(("usedefs",), value_types=("string", "array"), insert_kind="array"),
    )

    _ATTACHMENT_ITEM_MAPPING_RULES = _merge_rule_maps(
        _rules(("metadata", "manual"), value_types=("object",), insert_kind="object"),
        _rules(("fields",), value_types=("object", "array"), insert_kind="object"),
        _rules(
            ("password", "owner password", "template password", "raw"),
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
        ),
        _rules(("code", "manual code"), value_types=("string",), display_value_types=_PYTHON_EXPR_DISPLAY_TYPES),
        _rules(
            ("field variables", "raw field variables", "field code"),
            value_types=("string", "array"),
            insert_kind="array",
        ),
    )

    _ATTACHMENT_ITEM_RULES = _merge_rule_maps(
        _ATTACHMENT_ITEM_IDENTITY_RULES,
        _ATTACHMENT_ITEM_TEMPLATE_RULES,
        _ATTACHMENT_ITEM_PERMISSION_RULES,
        _ATTACHMENT_ITEM_DOCUMENT_RULES,
        _ATTACHMENT_ITEM_MAPPING_RULES,
        {
            "file": _rule(
                "file",
                value_types=("string",),
                description="PDF template file path for filling in form fields.",
            ),
            "language": _rule(
                "language",
                value_types=("string",),
                description="Language code for the attachment content.",
            ),
            "variable name": _rule(
                "variable name",
                value_types=("string",),
                description="Variable name that stores the assembled document.",
            ),
            "name": _rule(
                "name",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Human-readable name for the attachment, shown to the user.",
            ),
            "filename": _rule(
                "filename",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Filename for the generated document (without extension).",
            ),
            "description": _rule(
                "description",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Description of the attachment shown to the user in the download interface.",
            ),
            "content": _rule(
                "content",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Inline Markdown content for the document body.",
            ),
            "checkbox export value": _rule(
                "checkbox export value",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Value assigned to checkboxes in PDF export, supporting Mako.",
            ),
            "hyperlink style": _rule(
                "hyperlink style",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Style for rendering hyperlinks in the generated document.",
            ),
            "rendering font": _rule(
                "rendering font",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Font used for rendering text in the generated document.",
            ),
            "initial yaml": _rule(
                "initial yaml",
                value_types=("string", "array"),
                description="YAML file(s) with Pandoc metadata options loaded before the defaults.",
                insert_kind="array",
            ),
            "additional yaml": _rule(
                "additional yaml",
                value_types=("string", "array"),
                description="YAML file(s) with Pandoc metadata options loaded in addition to defaults.",
                insert_kind="array",
            ),
            "valid formats": _rule(
                "valid formats",
                value_types=("string", "array"),
                description="List of valid output formats for the document (e.g. pdf, docx, rtf).",
                insert_kind="array",
            ),
            "valid types": _rule(
                "valid types",
                value_types=("string", "array"),
                description="List of valid document types for the attachment.",
                insert_kind="array",
            ),
            "template file": _rule(
                "template file",
                value_types=("string", "object"),
                description="Path to a custom Pandoc LaTeX template file for PDF generation.",
                insert_kind="object",
            ),
            "rtf template file": _rule(
                "rtf template file",
                value_types=("string", "object"),
                description="Path to a custom Pandoc RTF template file.",
                insert_kind="object",
            ),
            "docx reference file": _rule(
                "docx reference file",
                value_types=("string", "object"),
                description="Path to a custom DOCX reference file for Pandoc DOCX output.",
                insert_kind="object",
            ),
            "pdf template file": _rule(
                "pdf template file",
                value_types=("string", "object"),
                description="Path to a PDF template file for fill-in form document assembly.",
                insert_kind="object",
            ),
            "docx template file": _rule(
                "docx template file",
                value_types=("string", "object"),
                description="Path to a DOCX template file using Jinja2 templating.",
                insert_kind="object",
            ),
            "content file": _rule(
                "content file",
                value_types=("string", "object"),
                description="Path to an external file whose contents serve as the document body.",
                insert_kind="object",
            ),
            "persistent": _rule(
                "persistent",
                value_types=("boolean", "string"),
                description="When true, the attachment is stored persistently and not deleted after download.",
            ),
            "private": _rule(
                "private",
                value_types=("boolean", "string"),
                description="When true, the attachment is private and only accessible to the current user.",
            ),
            "editable": _rule(
                "editable",
                value_types=("boolean", "string"),
                description="When true, the user can edit the attachment before downloading.",
            ),
            "update references": _rule(
                "update references",
                value_types=("boolean", "string"),
                description="When true, updates variable references when the document is re-generated.",
            ),
            "allow privileges": _rule(
                "allow privileges",
                value_types=("string", "array", "object"),
                description="List of privileges that allow access to this attachment.",
                insert_kind="array",
            ),
            "allow users": _rule(
                "allow users",
                value_types=("string", "integer", "array", "object"),
                description="List of user IDs that are allowed to access this attachment.",
                insert_kind="array",
            ),
            "skip undefined": _rule(
                "skip undefined",
                value_types=("boolean", "string"),
                description="When true, skips the attachment if a referenced variable is undefined.",
            ),
            "redact": _rule(
                "redact",
                value_types=("boolean", "string"),
                description="When true, redacts marked fields in the generated document.",
            ),
            "pdf/a": _rule(
                "pdf/a",
                value_types=("boolean", "string"),
                description="When true, generates the PDF in PDF/A archival format.",
            ),
            "pdftk": _rule(
                "pdftk",
                value_types=("boolean", "string"),
                description="When true, uses PDFtk for PDF manipulation instead of the default library.",
            ),
            "tagged pdf": _rule(
                "tagged pdf",
                value_types=("boolean", "string"),
                description="When true, generates a tagged PDF for improved accessibility.",
            ),
            "decimal places": _rule(
                "decimal places",
                value_types=("integer", "string"),
                display_value_types=("integer", "string", "mako"),
                description="Number of decimal places for numeric values in the document.",
            ),
            "usedefs": _rule(
                "usedefs",
                value_types=("string", "array"),
                description="Variable names used by this attachment that should be tracked as dependencies.",
                insert_kind="array",
            ),
            "metadata": _rule(
                "metadata",
                value_types=("object",),
                description="Pandoc metadata options for the document (e.g. fontsize, papersize).",
                insert_kind="object",
            ),
            "manual": _rule(
                "manual",
                value_types=("object",),
                description="Manual field mapping for PDF fill-in forms.",
                insert_kind="object",
            ),
            "fields": _rule(
                "fields",
                value_types=("object", "array"),
                description="Field mapping for PDF fill-in forms, mapping PDF field names to variable names.",
                insert_kind="object",
            ),
            "password": _rule(
                "password",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Password required to open the generated PDF.",
            ),
            "owner password": _rule(
                "owner password",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Owner password for PDF permission restrictions.",
            ),
            "template password": _rule(
                "template password",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Password for accessing the PDF template file.",
            ),
            "raw": _rule(
                "raw",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Raw content passed directly to the PDF template without processing.",
            ),
            "code": _rule(
                "code",
                value_types=("string",),
                display_value_types=_PYTHON_EXPR_DISPLAY_TYPES,
                description="Python code that dynamically generates the field mapping.",
            ),
            "manual code": _rule(
                "manual code",
                value_types=("string",),
                display_value_types=_PYTHON_EXPR_DISPLAY_TYPES,
                description="Python code that dynamically generates the manual field mapping.",
            ),
            "field variables": _rule(
                "field variables",
                value_types=("string", "array"),
                description="List of variable names mapped to PDF form fields.",
                insert_kind="array",
            ),
            "raw field variables": _rule(
                "raw field variables",
                value_types=("string", "array"),
                description="List of variable names mapped to raw PDF form fields without processing.",
                insert_kind="array",
            ),
            "field code": _rule(
                "field code",
                value_types=("string", "array"),
                description="Python code that dynamically generates field variable mappings.",
                insert_kind="array",
            ),
        },
    )

    _ATTACHMENT_OPTIONS_RULES = _merge_rule_maps(
        _rules(("initial yaml", "additional yaml"), value_types=("string", "array"), insert_kind="array"),
        _rules(("template file", "rtf template file", "docx reference file"), value_types=("string",)),
        _rules(("metadata",), value_types=("object",), insert_kind="object"),
        {
            "initial yaml": _rule(
                "initial yaml",
                value_types=("string", "array"),
                description="Interview-wide default YAML file(s) with Pandoc metadata options.",
                insert_kind="array",
            ),
            "additional yaml": _rule(
                "additional yaml",
                value_types=("string", "array"),
                description="Interview-wide default YAML file(s) with additional Pandoc metadata.",
                insert_kind="array",
            ),
            "template file": _rule(
                "template file",
                value_types=("string",),
                description="Interview-wide default Pandoc LaTeX template for PDF generation.",
            ),
            "rtf template file": _rule(
                "rtf template file",
                value_types=("string",),
                description="Interview-wide default Pandoc RTF template.",
            ),
            "docx reference file": _rule(
                "docx reference file",
                value_types=("string",),
                description="Interview-wide default DOCX reference file for Pandoc DOCX output.",
            ),
            "metadata": _rule(
                "metadata",
                value_types=("object",),
                description="Interview-wide default Pandoc metadata options for all attachments.",
                insert_kind="object",
            ),
        },
    )

    _SEGMENT_RULES = _merge_rule_maps(
        _rules(
            ("id",),
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
            description="Segment identifier sent with analytics events.",
        ),
        _rules(("arguments",), value_types=("object",), insert_kind="object"),
        {
            "arguments": _rule(
                "arguments",
                value_types=("object",),
                description="Additional data arguments sent with the Segment analytics event.",
                insert_kind="object",
            ),
        },
    )

    _HELP_BLOCK_RULES = {
        "label": _rule(
            "label",
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
            description="Label text for the help tab or button.",
        ),
        "heading": _rule(
            "heading",
            value_types=("string",),
            display_value_types=_MARKDOWN_STRING_DISPLAY_TYPES,
            description="Heading displayed at the top of the help content.",
        ),
        "content": _rule(
            "content",
            value_types=("string",),
            display_value_types=_MARKDOWN_STRING_DISPLAY_TYPES,
            description="Markdown content for the help section.",
        ),
        "audio": _rule(
            "audio",
            value_types=("string", "array"),
            display_value_types=("string", "mako", "array"),
            description="Audio file or URL to play alongside the help content.",
            insert_kind="array",
        ),
        "video": _rule(
            "video",
            value_types=("string", "array"),
            display_value_types=("string", "mako", "array"),
            description="Video file or URL to display alongside the help content.",
            insert_kind="array",
        ),
    }

    _GRID_RULES = {
        "width": _rule(
            "width",
            value_types=("integer", "string"),
            description="Column width for the grid layout (e.g. 6 for half-width).",
        ),
        "label width": _rule(
            "label width",
            value_types=("integer", "string"),
            description="Width of the label column in the grid layout.",
        ),
        "offset": _rule(
            "offset",
            value_types=("integer", "string"),
            description="Offset (margin left) for the grid column.",
        ),
        "start": _rule(
            "start", value_types=("boolean", "string", "null"), description="Column start visibility state."
        ),
        "end": _rule("end", value_types=("boolean", "string", "null"), description="Column end visibility state."),
        "breakpoint": _rule(
            "breakpoint",
            value_types=("string",),
            description="Responsive breakpoint at which this grid layout applies (e.g. 'md', 'lg').",
        ),
    }

    _ITEM_GRID_RULES = {
        "width": _rule(
            "width",
            value_types=("integer", "string"),
            description="Column width for the individual field item in the grid.",
        ),
        "breakpoint": _rule(
            "breakpoint",
            value_types=("string",),
            description="Responsive breakpoint for the individual field item grid layout.",
        ),
    }

    _ADDRESS_AUTOCOMPLETE_RULES = _merge_rule_maps(
        _rules(
            ("types", "fields"),
            value_types=("array",),
            insert_kind="array",
            description="Fixed address autocomplete option keys documented by docassemble.",
        ),
    )

    _FIELDS_ITEM_BASE_TEMPLATE_RULES = {
        "label": _rule(
            "label",
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
            description="Label text displayed to the user for the field.",
        ),
        "hint": _rule(
            "hint",
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
            description=(
                "Placeholder text shown inside the field before the user types. "
                "Also used as default text for dropdown/combobox/datalist fields."
            ),
        ),
        "under text": _rule(
            "under text",
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
            description="Text displayed under the field to guide the user.",
        ),
    }

    _FIELDS_ITEM_BASE_RULES = {
        "field": _rule(
            "field",
            value_types=("string",),
            description=(
                "The variable name that will store the user's input for this field. "
                "Used with the 'label' key as an alternative to the 'Label: variable' shorthand."
            ),
        ),
        "help": _rule(
            "help",
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
            description=(
                "Contextual help text shown in a popup when the user clicks the question mark icon next to the field."
            ),
        ),
        "action": _rule(
            "action",
            value_types=("string",),
            description=(
                "Name of a Python action block that provides choices for an ajax combobox "
                "(input type: ajax). The action receives the user's typed text as the "
                "'wordstart' argument and should return a JSON list of items."
            ),
        ),
        "object": _rule(
            "object",
            value_types=("string",),
            description=(
                "Datatype for selecting an existing object from a 'choices' list. "
                "The variable becomes an alias (reference) for the selected object."
            ),
        ),
        "object multiselect": _rule(
            "object multiselect",
            value_types=("string",),
            description="Datatype for selecting multiple existing objects using an HTML <select multiple> element.",
        ),
        "object radio": _rule(
            "object radio",
            value_types=("string",),
            description="Like 'object' datatype, but presents choices as radio buttons instead of a dropdown.",
        ),
        "file css class": _rule(
            "file css class",
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
            description=(
                "CSS class for the file upload input element. Set to 'None' to use standard "
                "Bootstrap styling instead of the Bootstrap File Input plugin."
            ),
        ),
        "group": _rule(
            "group",
            value_types=("string",),
            description=(
                "Grouping label that visually organizes related fields or choices "
                "under a category subheading in the user interface."
            ),
        ),
    }

    _FIELDS_ITEM_NOTE_RULES = {
        "note": _rule(
            "note",
            value_types=("string",),
            display_value_types=_MARKDOWN_STRING_DISPLAY_TYPES,
            description=(
                "Text displayed alongside fields. As a standalone item, appears "
                "between fields. As a field modifier, appears to the right of the field "
                "on wide screens."
            ),
        ),
        "html": _rule(
            "html",
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
            description=(
                "Raw HTML content displayed alongside fields, like 'note' but expects HTML "
                "format. Can be used in combination with 'css' and 'script' question modifiers."
            ),
        ),
        "raw html": _rule(
            "raw html",
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
            description=(
                "Like 'html', but inserted into the page without an enclosing <div>, "
                "allowing structural alterations to the fields list."
            ),
        ),
    }

    _FIELDS_ITEM_CHOICE_RULES = _merge_rule_maps(
        {
            "choices": _rule(
                "choices",
                value_types=("string", "array", "object"),
                insert_kind="array",
                description=(
                    "List of options for a multiple-choice field. Can be plain text items "
                    "(label equals value), key-value pairs (label: value), or dicts with "
                    "'label' and 'value' keys."
                ),
            ),
            "exclude": _rule(
                "exclude",
                value_types=("string", "array", "object"),
                insert_kind="array",
                description=(
                    "Python expression that evaluates to items to exclude from a 'code'-generated choices list."
                ),
            ),
        },
        {
            "default": _rule(
                "default",
                value_types=("string", "array", "object", "boolean"),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Default value for the field.",
            ),
            "default value": _rule(
                "default value",
                value_types=("string", "array", "object", "boolean"),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Alternative to 'default' for specifying a default value.",
            ),
        },
        {
            "value": _rule(
                "value",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description=(
                    "Specifies the underlying value for a choice item, used alongside "
                    "'label' in list-of-dicts choice format."
                ),
            ),
        },
        {
            "address autocomplete": _rule(
                "address autocomplete",
                value_types=("boolean", "string"),
                enum_values=("True", "False"),
                display_value_types=_BOOLEAN_PY_EXPR_DISPLAY_TYPES,
                description=(
                    "Enables Google Places address autocomplete on a field whose 'field' "
                    "target ends in '.address'. Accepts True, False, or a Python expression."
                ),
            ),
        },
        {
            "all of the above": _rule(
                "all of the above",
                value_types=("boolean", "string"),
                enum_values=("True", "False"),
                display_value_types=("boolean", "string", "mako"),
                description=(
                    "Shows the 'All of the above' option for checkbox fields. "
                    "Set to True to enable with the default label, or use a string to set a custom label."
                ),
            ),
            "none of the above": _rule(
                "none of the above",
                value_types=("boolean", "string"),
                enum_values=("True", "False"),
                display_value_types=("boolean", "string", "mako"),
                description=(
                    "Shows the 'None of the above' option for checkbox and object_radio fields. "
                    "Set to True to enable with the default label, or use a string for a custom label."
                ),
            ),
        },
        {
            "shuffle": _rule(
                "shuffle",
                value_types=("boolean",),
                enum_values=("True", "False"),
                description=(
                    "When True, randomizes the order of choices in a multiple-choice field. Default is False."
                ),
            ),
        },
    )

    _FIELD_CONDITION_EXPR_DESCRIPTIONS: dict[str, PropertyRule] = {
        "show if": _rule(
            "show if",
            value_types=("string", "object"),
            description=(
                "Controls field visibility. Three forms: (1) dict { variable: name, is: value } "
                "to show when another on-screen field matches a value; (2) shorthand var name "
                "for yes/no fields; (3) dict { code: expr } for server-side Python control. "
                "Cannot be combined with hide if."
            ),
        ),
        "hide if": _rule(
            "hide if",
            value_types=("string", "object"),
            description=(
                "Like show if but hides the field when the condition is met. "
                "Uses the same three syntax forms as show if. Cannot be combined with show if."
            ),
        ),
        "enable if": _rule(
            "enable if",
            value_types=("string", "object"),
            description=(
                "Disables/enables a field based on condition. Uses the same syntax "
                "forms as show if. Cannot be combined with show if or hide if. "
                "Code-valued enable if is not supported by the parser."
            ),
        ),
        "disable if": _rule(
            "disable if",
            value_types=("string", "object"),
            description=(
                "Disables a field when condition is met. Uses the same syntax "
                "forms as show if. Cannot be combined with show if or hide if. "
                "Code-valued disable if is not supported by the parser."
            ),
        ),
    }

    _FIELD_CONDITION_JS_DESCRIPTIONS: dict[str, PropertyRule] = {
        "js show if": _rule(
            "js show if",
            value_types=("string",),
            description=(
                "JavaScript expression controlling field visibility on the client side. "
                "Use val('field_name') to reference on-screen field values. Must contain "
                "at least one val() call referencing a field on the same screen."
            ),
        ),
        "js hide if": _rule(
            "js hide if",
            value_types=("string",),
            description=(
                "JavaScript expression that hides the field on the client side. "
                "Uses the same val() syntax as js show if. Cannot be combined with js show if."
            ),
        ),
        "js enable if": _rule(
            "js enable if",
            value_types=("string",),
            description=(
                "JavaScript expression that enables the field on the client side. "
                "Uses the same val() syntax as js show if. Cannot be combined with "
                "js show if or js hide if."
            ),
        ),
        "js disable if": _rule(
            "js disable if",
            value_types=("string",),
            description=(
                "JavaScript expression that disables the field on the client side. "
                "Uses the same val() syntax as js show if. Cannot be combined with "
                "js show if or js hide if."
            ),
        ),
    }

    _FIELDS_ITEM_CONDITION_RULES = _merge_rule_maps(
        _FIELD_CONDITION_EXPR_DESCRIPTIONS,
        _FIELD_CONDITION_JS_DESCRIPTIONS,
        {
            "disabled": _rule(
                "disabled",
                value_types=("boolean", "string"),
                enum_values=("True", "False"),
                display_value_types=_BOOLEAN_PY_EXPR_DISPLAY_TYPES,
                description="Disables the field input element. Has the side effect of required: False.",
            ),
            "required": _rule(
                "required",
                value_types=("boolean", "string"),
                enum_values=("True", "False"),
                display_value_types=_BOOLEAN_PY_EXPR_DISPLAY_TYPES,
                description="Marks the field as required (red asterisk). Fields are required by default.",
            ),
            "read only": _rule(
                "read only",
                value_types=("string",),
                description=(
                    "Marks the field as read-only for review/table blocks. Must refer to a plain text attribute name."
                ),
            ),
        },
    )

    _FIELDS_ITEM_LAYOUT_RULES = _merge_rule_maps(
        {
            "grid": _rule(
                "grid",
                value_types=("object",),
                description=(
                    "Places fields side-by-side using Bootstrap's grid system. Accepts an "
                    "integer (1-12) for width or a dict with 'width', 'label width', "
                    "'offset', 'start', 'end', and 'breakpoint'."
                ),
            ),
        },
        {
            "item grid": _rule(
                "item grid",
                value_types=("object",),
                insert_kind="object",
                description=(
                    "Like 'grid', but applies to radio button or checkbox items within "
                    "a field. Accepts a width and optional breakpoint."
                ),
            ),
            "field metadata": _rule(
                "field metadata",
                value_types=("object",),
                insert_kind="object",
                description=(
                    "Associates arbitrary YAML metadata with a field. The metadata appears "
                    "in the JSON representation of the question."
                ),
            ),
        },
        {
            "label above field": _rule(
                "label above field",
                value_types=("boolean", "string"),
                enum_values=("True", "False"),
                display_value_types=_BOOLEAN_PY_EXPR_DISPLAY_TYPES,
                description="When True, positions the label above the field instead of to the left.",
            ),
            "floating label": _rule(
                "floating label",
                value_types=("boolean", "string"),
                enum_values=("True", "False"),
                display_value_types=_BOOLEAN_PY_EXPR_DISPLAY_TYPES,
                description="When True, uses Bootstrap's floating labels style for the field.",
            ),
        },
        _rules(
            FIELDS_ITEM_LAYOUT_PYTHON_EXPR_KEYS,
            value_types=("string",),
            display_value_types=_PYTHON_EXPR_DISPLAY_TYPES,
            description=(
                "Number of visible rows for a text area (input type: area) "
                "or a multiselect box (datatype: multiselect / object_multiselect). "
                "Default is 4."
            ),
        ),
        {
            "min": _rule(
                "min",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description=(
                    "Minimum value for number, currency, and date fields. Passed to the jQuery Validation Plugin."
                ),
            ),
            "max": _rule(
                "max",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description=(
                    "Maximum value for number, currency, and date fields. Passed to the jQuery Validation Plugin."
                ),
            ),
            "minlength": _rule(
                "minlength",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description=(
                    "Minimum number of characters for text fields, or minimum number "
                    "of checkboxes that must be checked."
                ),
            ),
            "maxlength": _rule(
                "maxlength",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description=(
                    "Maximum number of characters for text fields, or maximum number of checkboxes that can be checked."
                ),
            ),
            "step": _rule(
                "step",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description=(
                    "Step interval for number, currency, and range fields. Limits decimal places or slider increments."
                ),
            ),
            "scale": _rule(
                "scale",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Scale type for range sliders. Set to 'logarithmic' for a logarithmic scale.",
            ),
            "inline": _rule(
                "inline",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Display mode for embedded fields used with the [FIELD ...] subquestion syntax.",
            ),
            "inline width": _rule(
                "inline width",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description=(
                    "Width (e.g. '15em') for embedded fields used with the [FIELD ...] "
                    "subquestion syntax. Has no effect outside embedded fields."
                ),
            ),
            "currency symbol": _rule(
                "currency symbol",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Overrides the currency symbol for a 'datatype: currency' field on a per-field basis.",
            ),
            "css class": _rule(
                "css class",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description=(
                    "CSS class(es) for the HTML input element. A '-container' suffix "
                    "is added for the field's container div."
                ),
            ),
        },
    )

    _FIELDS_ITEM_FILE_RULES = _merge_rule_maps(
        {
            "maximum image size": _rule(
                "maximum image size",
                value_types=("string",),
                display_value_types=_PYTHON_EXPR_DISPLAY_TYPES,
                description=(
                    "Reduces uploaded images to at most this many pixels in height or width. "
                    "Accepts a number or Python expression, or None to disable."
                ),
            ),
            "image upload type": _rule(
                "image upload type",
                value_types=("string",),
                display_value_types=_PYTHON_EXPR_DISPLAY_TYPES,
                description=(
                    "Converts uploaded images to the specified format during upload. One of 'png', 'jpeg', or 'bmp'."
                ),
            ),
            "accept": _rule(
                "accept",
                value_types=("string",),
                display_value_types=_PYTHON_EXPR_DISPLAY_TYPES,
                description=(
                    "Limits file uploads to specific MIME types. Passed directly to the "
                    "HTML accept attribute and jQuery Validation accept method."
                ),
            ),
        },
        {
            "allow privileges": _rule(
                "allow privileges",
                value_types=("array", "string", "object"),
                insert_kind="array",
                description=(
                    "Grants file access to user privilege categories (e.g., user, developer, "
                    "advocate). Accepts a list, string, or dict with a 'code' key."
                ),
            ),
            "allow users": _rule(
                "allow users",
                value_types=("array", "string", "object"),
                insert_kind="array",
                description=(
                    "Grants file access to specific users by email address, user ID, "
                    "or Individual object. Accepts a list, string, or dict with a 'code' key."
                ),
            ),
        },
        {
            "persistent": _rule(
                "persistent",
                value_types=("boolean", "string"),
                enum_values=("True", "False"),
                display_value_types=_BOOLEAN_PY_EXPR_DISPLAY_TYPES,
                description="When True, the uploaded file persists after the session is deleted.",
            ),
            "private": _rule(
                "private",
                value_types=("boolean", "string"),
                enum_values=("True", "False"),
                display_value_types=_BOOLEAN_PY_EXPR_DISPLAY_TYPES,
                description=(
                    "When False, the uploaded file is accessible to anyone (not just the uploader and administrators)."
                ),
            ),
        },
    )

    _FIELDS_ITEM_SPECIAL_STRING_DESCRIPTIONS: dict[str, PropertyRule] = {
        "code": _rule(
            "code",
            value_types=("string",),
            insert_kind="block_scalar",
            display_value_types=_PYTHON_EXPR_DISPLAY_TYPES,
            description=(
                "Python expression that generates choices for a multiple-choice field. "
                "Evaluated when the question is asked; the result can be a list of dicts, "
                "a list of strings, a list of tuples, or a dict."
            ),
        ),
        "validate": _rule(
            "validate",
            value_types=("string",),
            display_value_types=_PYTHON_EXPR_DISPLAY_TYPES,
            description=(
                "Python expression that should evaluate to a callable function "
                "used for server-side input validation. The function receives the raw "
                "value and should return True if valid or call validation_error() with "
                "an error message."
            ),
        ),
        "validation code": _rule(
            "validation code",
            value_types=("string",),
            insert_kind="block_scalar",
            description=(
                "Python code block for question-level validation. "
                "Runs after all fields are filled; call validation_error() to reject "
                "input and show an error message at the top of the screen."
            ),
        ),
        "object labeler": _rule(
            "object labeler",
            value_types=("string",),
            display_value_types=_PYTHON_EXPR_DISPLAY_TYPES,
            description=(
                "Python expression that evaluates to a callable function used to "
                "label object choices. The function receives an object and returns "
                "the display label string. E.g. lambda y: y.nickname"
            ),
        ),
        "help generator": _rule(
            "help generator",
            value_types=("string",),
            display_value_types=_PYTHON_EXPR_DISPLAY_TYPES,
            description=(
                "Python expression that evaluates to a callable function used to "
                "generate help text for each object choice. The function receives "
                "an object and returns the help text string."
            ),
        ),
        "image generator": _rule(
            "image generator",
            value_types=("string",),
            display_value_types=_PYTHON_EXPR_DISPLAY_TYPES,
            description=(
                "Python expression that evaluates to a callable function used to "
                "generate an image for each object choice. The function receives "
                "an object and returns an image reference."
            ),
        ),
    }

    _FIELDS_ITEM_SPECIAL_RULES = _merge_rule_maps(
        _rules(
            tuple(
                key for key in FIELDS_ITEM_SPECIAL_STRING_KEYS if key not in _FIELDS_ITEM_SPECIAL_STRING_DESCRIPTIONS
            ),
            value_types=("string",),
        ),
        _rules(
            tuple(
                key
                for key in FIELDS_ITEM_SPECIAL_PYTHON_EXPR_KEYS
                if key not in _FIELDS_ITEM_SPECIAL_STRING_DESCRIPTIONS
            ),
            value_types=("string",),
            display_value_types=_PYTHON_EXPR_DISPLAY_TYPES,
        ),
        _FIELDS_ITEM_SPECIAL_STRING_DESCRIPTIONS,
        {
            "disable others": _rule(
                "disable others",
                value_types=("boolean", "array"),
                enum_values=("True", "False"),
                insert_kind="array",
                description=(
                    "When True or a list of variable names, disables other fields on "
                    "the screen when this field's value changes. Not compatible with "
                    "file, range, multiselect, or checkboxes datatypes."
                ),
            ),
            "uncheck others": _rule(
                "uncheck others",
                value_types=("boolean", "array"),
                enum_values=("True", "False"),
                insert_kind="array",
                description=(
                    "Creates a 'none of the above' behavior: checking this field "
                    "unchecks others. Accepts True (all) or a list of variable names. "
                    "Only for yesno/noyes datatypes."
                ),
            ),
            "check others": _rule(
                "check others",
                value_types=("boolean", "array"),
                enum_values=("True", "False"),
                insert_kind="array",
                description=(
                    "Creates an 'all of the above' behavior: checking this field checks "
                    "others. Accepts True (all) or a list of variable names. "
                    "Only for yesno/noyes datatypes."
                ),
            ),
        },
        {
            "validation messages": _rule(
                "validation messages",
                value_types=("object",),
                insert_kind="object",
                description=(
                    "Dictionary mapping validation message codes to custom error messages "
                    "for a specific field. Keys are validation type codes (e.g. 'required', "
                    "'min', 'max', 'date', 'email', 'number', 'step') and values are the "
                    "message text the user will see."
                ),
            ),
            "trigger at": _rule(
                "trigger at",
                value_types=("integer",),
                description=(
                    "Minimum number of characters the user must type before an ajax "
                    "combobox triggers a server request for suggestions. Must be an "
                    "integer greater than one."
                ),
            ),
        },
        {
            "using": _rule(
                "using",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description=(
                    "Machine learning group identifier for ml/mlarea datatypes. "
                    "Groups user input into a named category for ML training."
                ),
            ),
            "keep for training": _rule(
                "keep for training",
                value_types=("boolean", "string"),
                enum_values=("True", "False"),
                display_value_types=_BOOLEAN_PY_EXPR_DISPLAY_TYPES,
                description="Whether to retain this field's input for machine learning training.",
            ),
        },
        {
            "datatype": _rule(
                "datatype",
                value_types=("string",),
                enum_values=_FIELD_DATATYPES,
                description=(
                    "Controls how data is collected, validated, and stored for a field. "
                    "Affects the user interface widget and the Python type of the variable. "
                    "See the Docassemble fields documentation for details."
                ),
            ),
            "input type": _rule(
                "input type",
                value_types=("string",),
                enum_values=_FIELD_INPUT_TYPES,
                description=(
                    "Overrides the user interface widget type independently of the datatype. "
                    "Useful when combining a scalar datatype (e.g., text, number) with a "
                    "multiple-choice widget (radio, dropdown, combobox, datalist) or "
                    "a multi-line text area (area) or invisible field (hidden)."
                ),
            ),
        },
    )

    _FIELDS_ITEM_RULES = _merge_rule_maps(
        _FIELDS_ITEM_BASE_TEMPLATE_RULES,
        _FIELDS_ITEM_BASE_RULES,
        _FIELDS_ITEM_NOTE_RULES,
        _FIELDS_ITEM_CHOICE_RULES,
        _FIELDS_ITEM_CONDITION_RULES,
        _FIELDS_ITEM_LAYOUT_RULES,
        _FIELDS_ITEM_FILE_RULES,
        _FIELDS_ITEM_SPECIAL_RULES,
    )

    _ACTION_BUTTON_ITEM_RULES = _merge_rule_maps(
        _rules(
            ("action", "label", "icon", "placement", "css class"),
            value_types=("string",),
            display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
        ),
        _rules(("code",), value_types=("string",), display_value_types=_PYTHON_EXPR_DISPLAY_TYPES),
        _rules(("arguments",), value_types=("object",), insert_kind="object"),
        {
            "action": _rule(
                "action",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Name of the action to trigger when the button is clicked.",
            ),
            "label": _rule(
                "label",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Button label text displayed to the user.",
            ),
            "icon": _rule(
                "icon",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Font Awesome icon name for the action button.",
            ),
            "placement": _rule(
                "placement",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Button placement: 'before' places it before standard buttons, 'after' (default) after.",
            ),
            "css class": _rule(
                "css class",
                value_types=("string",),
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="CSS class applied to the action button element.",
            ),
            "code": _rule(
                "code",
                value_types=("string",),
                display_value_types=_PYTHON_EXPR_DISPLAY_TYPES,
                description="Python code that generates the action buttons list dynamically.",
            ),
            "arguments": _rule(
                "arguments",
                value_types=("object",),
                description="Dictionary of arguments passed to the action handler.",
                insert_kind="object",
            ),
            "color": _rule(
                "color",
                value_types=("string",),
                enum_values=_BOOTSTRAP_COLORS,
                display_value_types=_TEMPLATE_STRING_DISPLAY_TYPES,
                description="Bootstrap color class for the button (primary, secondary, success, etc.).",
            ),
            "new window": _rule(
                "new window",
                value_types=("boolean", "string"),
                enum_values=("True", "False"),
                display_value_types=("boolean", "string", "mako"),
                description="When true, the action URL opens in a new browser window.",
            ),
            "show if": _rule(
                "show if",
                value_types=("string",),
                display_value_types=_PYTHON_EXPR_DISPLAY_TYPES,
                description="Expression controlling whether the button is shown.",
            ),
            "forget prior": _rule(
                "forget prior",
                value_types=("boolean",),
                description="When true, any prior actions are forgotten before starting this action.",
            ),
        },
    )

    _NEED_ITEM_RULES = {
        "pre": _rule(
            "pre",
            value_types=("string", "array"),
            insert_kind="array",
            description="Variable name(s) that must be defined before this block runs.",
        ),
        "post": _rule(
            "post",
            value_types=("string", "array"),
            insert_kind="array",
            description="Variable name(s) that must be defined after this block runs.",
        ),
    }

    _TERMS_ITEM_RULES = {
        "phrases": _rule(
            "phrases",
            value_types=("array", "string"),
            insert_kind="array",
            description="List of phrases that trigger this term definition when enclosed in curly braces.",
        ),
        "definition": _rule(
            "definition",
            value_types=("array", "string"),
            insert_kind="array",
            display_value_types=("string", "mako", "array"),
            description="Definition text displayed when the user clicks on the term.",
        ),
    }

    _SHOW_IF_MODIFIER_RULES = {
        "variable": _rule("variable", value_types=("string",), description="Variable name to inspect."),
        "is": _rule(
            "is",
            value_types=("string", "number", "boolean", "null"),
            description="Value compared against the variable.",
        ),
        "code": _rule(
            "code",
            value_types=("string",),
            description="Expression used to decide whether the modifier applies.",
            insert_kind="block_scalar",
        ),
    }

    top_level = dict(_TOP_LEVEL_RULES)
    metadata_block = dict(_METADATA_RULES)
    metadata_author_item = dict(_METADATA_AUTHOR_ITEM_RULES)
    metadata_social_block = dict(_METADATA_SOCIAL_RULES)
    metadata_social_twitter_block = dict(_METADATA_SOCIAL_TWITTER_RULES)
    metadata_social_og_block = dict(_METADATA_SOCIAL_OG_RULES)
    attachment_metadata_block = dict(_ATTACHMENT_METADATA_RULES)
    attachment_fields_block = dict(_ATTACHMENT_FIELDS_RULES)
    attachment_field_variable_item = dict(_ATTACHMENT_FIELD_VARIABLE_ITEM_RULES)
    sections_item = dict(_SECTIONS_ITEM_RULES)
    table_column_item = dict(_TABLE_COLUMN_ITEM_RULES)
    objects_item = dict(_OBJECTS_ITEM_RULES)
    objects_from_file_item = dict(_OBJECTS_FROM_FILE_ITEM_RULES)
    on_change_item = dict(_ON_CHANGE_ITEM_RULES)
    include_item = dict(_INCLUDE_ITEM_RULES)
    imports_item = dict(_IMPORTS_ITEM_RULES)
    modules_item = dict(_MODULES_ITEM_RULES)
    translations_item = dict(_TRANSLATIONS_ITEM_RULES)
    reset_item = dict(_RESET_ITEM_RULES)
    order_item = dict(_ORDER_ITEM_RULES)
    features_block = dict(_FEATURES_RULES)
    default_screen_parts_block = dict(_DEFAULT_SCREEN_PARTS_RULES)
    list_collect_block = dict(_LIST_COLLECT_RULES)
    image_set_block = dict(_IMAGE_SET_RULES)
    validation_messages_block = dict(_VALIDATION_MESSAGES_RULES)
    review_item = dict(_REVIEW_ITEM_RULES)
    review_field_item = dict(_REVIEW_FIELD_ITEM_RULES)
    attachment_item = dict(_ATTACHMENT_ITEM_RULES)
    attachment_options_block = dict(_ATTACHMENT_OPTIONS_RULES)
    segment_block = dict(_SEGMENT_RULES)
    help_block = dict(_HELP_BLOCK_RULES)
    interview_help_block = dict(_HELP_BLOCK_RULES)
    grid_block = dict(_GRID_RULES)
    item_grid_block = dict(_ITEM_GRID_RULES)
    address_autocomplete_block = dict(_ADDRESS_AUTOCOMPLETE_RULES)
    fields_item = dict(_FIELDS_ITEM_RULES)
    action_button_item = dict(_ACTION_BUTTON_ITEM_RULES)
    need_item = dict(_NEED_ITEM_RULES)
    terms_item = dict(_TERMS_ITEM_RULES)
    show_if_modifier = dict(_SHOW_IF_MODIFIER_RULES)
    unknown_nested: dict[str, PropertyRule] = {}

    scoped_properties: dict[CompletionScope, dict[str, PropertyRule]] = {
        "top_level": top_level,
        "metadata_block": metadata_block,
        "metadata_author_item": metadata_author_item,
        "metadata_social_block": metadata_social_block,
        "metadata_social_twitter_block": metadata_social_twitter_block,
        "metadata_social_og_block": metadata_social_og_block,
        "attachment_metadata_block": attachment_metadata_block,
        "attachment_fields_block": attachment_fields_block,
        "attachment_field_variable_item": attachment_field_variable_item,
        "sections_item": sections_item,
        "table_column_item": table_column_item,
        "objects_item": objects_item,
        "objects_from_file_item": objects_from_file_item,
        "on_change_item": on_change_item,
        "include_item": include_item,
        "imports_item": imports_item,
        "modules_item": modules_item,
        "translations_item": translations_item,
        "reset_item": reset_item,
        "order_item": order_item,
        "features_block": features_block,
        "default_screen_parts_block": default_screen_parts_block,
        "list_collect_block": list_collect_block,
        "image_set_block": image_set_block,
        "validation_messages_block": validation_messages_block,
        "review_item": review_item,
        "review_field_item": review_field_item,
        "attachment_item": attachment_item,
        "attachment_options_block": attachment_options_block,
        "segment_block": segment_block,
        "help_block": help_block,
        "interview_help_block": interview_help_block,
        "grid_block": grid_block,
        "item_grid_block": item_grid_block,
        "address_autocomplete_block": address_autocomplete_block,
        "fields_item": fields_item,
        "action_button_item": action_button_item,
        "need_item": need_item,
        "terms_item": terms_item,
        "show_if_modifier": show_if_modifier,
        "unknown_nested": unknown_nested,
    }

    all_known_properties: dict[str, PropertyRule] = {}
    for scope_name, scope_properties in scoped_properties.items():
        if scope_name == "unknown_nested":
            continue
        for key, value in scope_properties.items():
            all_known_properties.setdefault(key, value)

    return SchemaMetadata(
        properties=top_level,
        top_level=top_level,
        metadata_block=metadata_block,
        metadata_author_item=metadata_author_item,
        metadata_social_block=metadata_social_block,
        metadata_social_twitter_block=metadata_social_twitter_block,
        metadata_social_og_block=metadata_social_og_block,
        attachment_metadata_block=attachment_metadata_block,
        attachment_fields_block=attachment_fields_block,
        attachment_field_variable_item=attachment_field_variable_item,
        sections_item=sections_item,
        table_column_item=table_column_item,
        objects_item=objects_item,
        objects_from_file_item=objects_from_file_item,
        on_change_item=on_change_item,
        include_item=include_item,
        imports_item=imports_item,
        modules_item=modules_item,
        translations_item=translations_item,
        reset_item=reset_item,
        order_item=order_item,
        features_block=features_block,
        default_screen_parts_block=default_screen_parts_block,
        list_collect_block=list_collect_block,
        image_set_block=image_set_block,
        validation_messages_block=validation_messages_block,
        review_item=review_item,
        review_field_item=review_field_item,
        attachment_item=attachment_item,
        attachment_options_block=attachment_options_block,
        segment_block=segment_block,
        help_block=help_block,
        interview_help_block=interview_help_block,
        grid_block=grid_block,
        item_grid_block=item_grid_block,
        address_autocomplete_block=address_autocomplete_block,
        fields_item=fields_item,
        action_button_item=action_button_item,
        need_item=need_item,
        terms_item=terms_item,
        show_if_modifier=show_if_modifier,
        unknown_nested=unknown_nested,
        scoped_properties=scoped_properties,
        all_known_properties=all_known_properties,
    )


def load_rule_registry() -> SchemaMetadata:
    return _build_registry()


def get_property_rule(scope: CompletionScope, key: str) -> PropertyRule | None:
    """Look up a property rule by scope and key name.

    Uses the same cached registry that drives completions, so any
    changes to property definitions are automatically reflected.
    Returns ``None`` when the scope or key is unknown.
    """
    registry = load_rule_registry()
    scope_rules = registry.scoped_properties.get(scope)
    if scope_rules is None:
        return None
    return scope_rules.get(key)
