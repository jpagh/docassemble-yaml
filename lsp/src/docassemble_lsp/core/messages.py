from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True, slots=True)
class MessageDefinition:
    code: str
    summary: str
    template: str
    experimental: bool = True


class MessageCode(str, Enum):
    def __str__(self) -> str:
        return self.value

    YAML_DUPLICATE_KEY = "E101"
    YAML_PARSE_ERROR = "E102"
    JINJA2_SYNTAX_ERROR = "E201"
    JINJA2_TEMPLATE_ERROR = "E202"
    UNKNOWN_KEYS = "E301"

    YAML_STRING_TYPE = "E103"
    MAKO_SYNTAX_ERROR = "E111"
    MAKO_COMPILE_ERROR = "E112"
    PYTHON_CODE_TYPE = "E121"
    PYTHON_SYNTAX_ERROR = "E122"

    JS_MODIFIER_TYPE = "E203"
    JS_INVALID_SYNTAX = "E204"
    JS_MISSING_VAL_CALL = "E205"
    JS_UNKNOWN_SCREEN_FIELD = "E206"
    JS_VAL_ARG_NOT_QUOTED = "E207"

    SHOW_IF_MALFORMED = "E302"
    SHOW_IF_CODE_TYPE = "E303"
    SHOW_IF_CODE_SYNTAX = "E304"
    SHOW_IF_DICT_KEYS = "E305"
    NO_POSSIBLE_TYPES = "E306"
    TOO_MANY_TYPES = "E307"
    INTERVIEW_ORDER_UNMATCHED_GUARD = "W603"
    BOOLEAN_DATATYPE_CHOICES_IGNORED = "E534"
    VISIBILITY_MODIFIER_CONFLICT = "E535"
    VISIBILITY_JS_NON_JS_MIX = "E536"
    NESTED_VISIBILITY_LOGIC = "E309"

    PYTHON_VAR_TYPE = "E401"
    PYTHON_VAR_WHITESPACE = "E402"
    OBJECTS_BLOCK_TYPE = "E403"
    FIELDS_CODE_TYPE = "E404"
    FIELDS_TYPE = "E406"
    FIELD_MODIFIER_VARIABLE_TYPE = "E407"
    FIELD_MODIFIER_UNKNOWN_VARIABLE_DICT = "E408"
    FIELD_MODIFIER_CODE_ERROR = "E409"
    FIELD_MODIFIER_SAME_SCREEN_CODE = "E410"
    FIELD_MODIFIER_DICT_KEYS = "E411"
    FIELD_MODIFIER_UNKNOWN_VARIABLE_STRING = "E412"
    OBJECT_FIELD_CHOICES_CODE_DICT = "E413"
    FIELD_ITEM_MISSING_TARGET = "E414"
    FIELD_ITEM_MISSING_LABEL = "E415"
    FIELD_TARGET_NOT_PLAIN_TEXT = "E416"
    FIELD_TARGET_INVALID_VARIABLE = "E417"
    FIELD_LABEL_OVERWRITE = "E418"
    MULTIPLE_CHOICE_FIELD_MISSING_CHOICES = "E419"
    AJAX_FIELD_MISSING_ACTION = "E420"
    AJAX_FIELD_CANNOT_DECLARE_CHOICES = "E421"
    OBJECT_LABELER_REQUIRES_OBJECT_DATATYPE = "E422"
    FIELD_PRESENTATION_KEY_CONFLICT = "E423"
    FIELD_ITEM_MUST_BE_DICT = "E424"
    HIDDEN_FIELD_INVALID_DATATYPE = "E425"
    FIELD_EXCLUDE_INVALID_FORMAT = "E426"
    FIELD_DEFAULT_INVALID_FORMAT = "E427"
    NEED_TYPE = "E428"
    NEED_DICT_KEYS = "E429"
    NEED_PHASE_TYPE = "E430"
    NEED_ITEM_STRING = "E431"
    ON_CHANGE_TYPE = "E432"
    ON_CHANGE_EXTRA_KEYS = "E433"
    ON_CHANGE_ENTRY_TYPE = "E434"
    ACTION_BUTTONS_TYPE = "E435"
    ACTION_BUTTON_ITEM_TYPE = "E436"
    ACTION_BUTTON_ACTION_TYPE = "E437"
    ACTION_BUTTON_NEW_WINDOW_TYPE = "E438"
    ACTION_BUTTON_ARGUMENTS_TYPE = "E439"
    ACTION_BUTTON_LABEL_TYPE = "E440"
    ACTION_BUTTON_COLOR_TYPE = "E441"
    ACTION_BUTTON_ICON_TYPE = "E442"
    ACTION_BUTTON_PLACEMENT_TYPE = "E443"
    ACTION_BUTTON_CSS_CLASS_TYPE = "E444"
    ACTION_BUTTON_FORGET_PRIOR_TYPE = "E445"
    ACTION_BUTTON_ARGUMENT_ITEM_TYPE = "E446"
    TRANSLATIONS_TYPE = "E447"
    TRANSLATIONS_ITEM_TYPE = "E448"
    TRANSLATIONS_SUFFIX = "E449"
    TRANSLATIONS_PATH = "E450"
    IF_TYPE = "E451"
    REQUIRE_TYPE = "E452"
    REQUIRE_ORELSE_MISSING = "E453"
    REQUIRE_ORELSE_TYPE = "E454"
    TERMS_TYPE = "E455"
    TERMS_ITEM_TYPE = "E456"
    AUTO_TERMS_TYPE = "E457"
    AUTO_TERMS_ITEM_TYPE = "E458"

    INCLUDE_TYPE = "E459"
    INCLUDE_ITEM_TYPE = "E460"
    MODULES_TYPE = "E461"
    MODULES_ITEM_TYPE = "E462"
    IMPORTS_TYPE = "E463"
    IMPORTS_ITEM_TYPE = "E464"
    METADATA_TYPE = "E465"

    SETS_TYPE = "E466"
    SETS_ITEM_TYPE = "E467"

    FEATURES_TYPE = "E468"
    EVENT_TYPE = "E469"
    EVENT_ITEM_TYPE = "E470"

    # Packet 4: Question Modifiers
    RECONSIDER_TYPE = "E471"
    RECONSIDER_ITEM_TYPE = "E472"
    UNDEFINE_TYPE = "E473"
    UNDEFINE_ITEM_TYPE = "E474"
    SUPERSEDES_TYPE = "E475"
    SUPERSEDES_ITEM_TYPE = "E476"
    DEPENDS_ON_TYPE = "E477"
    DEPENDS_ON_ITEM_TYPE = "E478"
    ROLE_TYPE = "E479"
    ROLE_ITEM_TYPE = "E480"
    ALLOWED_TO_SET_TYPE = "E481"
    PROGRESS_TYPE = "E482"

    ACCESSIBILITY_COMBOBOX_NOT_ACCESSIBLE = "W501"
    ACCESSIBILITY_NO_LABEL_MULTI_FIELD = "W502"
    ACCESSIBILITY_TAGGED_PDF_NOT_ENABLED = "W503"
    ACCESSIBILITY_THEME_CONTRAST_TOO_LOW = "W504"
    ACCESSIBILITY_IMAGE_MISSING_ALT_TEXT = "W505"
    ACCESSIBILITY_MARKDOWN_HEADING_LEVEL_SKIP = "W506"
    ACCESSIBILITY_HTML_HEADING_LEVEL_SKIP = "W507"
    ACCESSIBILITY_EMPTY_LINK_TEXT = "W508"
    ACCESSIBILITY_NON_DESCRIPTIVE_LINK_TEXT = "W509"

    # Packet 6: Field Datatypes And Inputs
    RANGE_MISSING_MIN_MAX = "E510"
    FILE_KEY_WITHOUT_FILE_DATATYPE = "E511"
    ROWS_WITHOUT_COMPATIBLE_TYPE = "E512"

    # Packet 7: Choices And Buttons
    DISABLE_OTHERS_INCOMPATIBLE_DATATYPE = "E513"
    DISABLE_OTHERS_INVALID_TYPE = "E514"
    UNCHECK_OTHERS_REQUIRES_YESNO = "E515"
    UNCHECK_OTHERS_INVALID_TYPE = "E516"
    CHECK_OTHERS_REQUIRES_YESNO = "E517"
    CHECK_OTHERS_INVALID_TYPE = "E518"
    SHUFFLE_NOT_BOOLEAN = "E519"
    ALL_OF_THE_ABOVE_INCOMPATIBLE_DATATYPE = "E520"
    NONE_OF_THE_ABOVE_INCOMPATIBLE_DATATYPE = "E521"

    # Packet 8: Field Conditions And Validation
    VALIDATE_TYPE = "E522"
    VALIDATE_SYNTAX = "E523"
    VALIDATION_MESSAGES_TYPE = "E524"
    VALIDATION_MESSAGES_ENTRY_TYPE = "E525"
    TRIGGER_AT_TYPE = "E526"
    HELP_GENERATOR_TYPE = "E527"
    HELP_GENERATOR_SYNTAX = "E528"
    IMAGE_GENERATOR_TYPE = "E529"
    IMAGE_GENERATOR_SYNTAX = "E530"
    ML_USING_TYPE = "E531"
    KEEP_FOR_TRAINING_TYPE = "E532"

    # Packet 15: Markup
    MARKUP_BRACKET_EMPTY = "E932"

    # List collect
    LIST_COLLECT_LABEL_HAS_MAKO = "E933"

    PYTHON_BOOL_TYPE = "E533"

    # Packet 9: Documents And Attachments
    ATTACHMENT_ITEM_MUST_BE_DICT = "E901"
    ATTACHMENT_NAME_TYPE = "E902"
    ATTACHMENT_FILENAME_TYPE = "E903"
    ATTACHMENT_VARIABLE_NAME_TYPE = "E904"
    ATTACHMENT_METADATA_TYPE = "E905"
    ATTACHMENT_VALID_FORMATS_TYPE = "E906"
    ATTACHMENT_CODE_TYPE = "E907"
    ATTACHMENT_FIELD_VARIABLES_TYPE = "E908"
    ATTACHMENT_CONTENT_FILE_TYPE = "E909"
    ATTACHMENT_METADATA_ENTRY_TYPE = "E910"

    # Packet 10: Review And Table
    REVIEW_TYPE = "E911"
    REVIEW_ITEM_TYPE = "E912"
    REVIEW_LABEL_REQUIRES_FIELD = "E913"
    REVIEW_FIELD_REQUIRES_LABEL = "E914"
    REVIEW_NOTE_TYPE = "E915"
    REVIEW_SHOW_IF_TYPE = "E916"
    REVIEW_HELP_TYPE = "E917"
    REVIEW_ACTION_TYPE = "E918"
    REVIEW_BUTTON_TYPE = "E919"
    REVIEW_CSS_CLASS_TYPE = "E920"

    TABLE_REQUIRED_KEYS = "E921"
    TABLE_TYPE = "E922"
    TABLE_ROWS_TYPE = "E923"
    TABLE_COLUMNS_TYPE = "E924"
    TABLE_COLUMN_ITEM_TYPE = "E925"
    TABLE_COLUMN_HEADER_TYPE = "E926"
    TABLE_COLUMN_CELL_TYPE = "E927"

    # Packet 12: Objects And Data
    DATA_TYPE = "E928"
    DATA_VARIABLE_NAME_TYPE = "E929"
    DATA_USE_OBJECTS_TYPE = "E930"

    VALIDATION_CODE_MISSING_VALIDATION_ERROR = "C101"
    FIELDS_LABEL_SHORTHAND_DISALLOWED = "C102"
    RADIO_DATATYPE_WITH_CHOICES_PREFER_INPUT_TYPE = "C103"
    FIELD_TARGET_UNDERSCORE = "C104"
    DATATYPE_AREA_PREFER_INPUT_TYPE = "C105"
    RESERVED_DA_NAME = "E931"
    DEF_MAKO_REQUIRED = "E934"

    CROSS_DOC_UNDEFINED_EVENT = "W601"
    CROSS_DOC_UNDEFINED_DEF = "W602"
    CROSS_DOC_MISSING_FILE = "W604"
    CROSS_DOC_MISSING_TEMPLATE = "W605"


MESSAGE_DEFINITIONS: dict[str, MessageDefinition] = {
    MessageCode.YAML_DUPLICATE_KEY: MessageDefinition(
        code=MessageCode.YAML_DUPLICATE_KEY,
        summary="Duplicate YAML key",
        template="duplicate key '{key_name}'",
        experimental=False,
    ),
    MessageCode.YAML_PARSE_ERROR: MessageDefinition(
        code=MessageCode.YAML_PARSE_ERROR,
        summary="YAML parsing error",
        template="{error}",
        experimental=False,
    ),
    MessageCode.JINJA2_SYNTAX_ERROR: MessageDefinition(
        code=MessageCode.JINJA2_SYNTAX_ERROR,
        summary="Jinja2 syntax error",
        template="Jinja2 syntax error at line {line_number}: {message}",
        experimental=False,
    ),
    MessageCode.JINJA2_TEMPLATE_ERROR: MessageDefinition(
        code=MessageCode.JINJA2_TEMPLATE_ERROR,
        summary="Jinja2 template error",
        template="Jinja2 template error: {error}",
        experimental=False,
    ),
    MessageCode.UNKNOWN_KEYS: MessageDefinition(
        code=MessageCode.UNKNOWN_KEYS,
        summary="Unknown YAML keys",
        template="Keys that shouldn't exist! {keys}",
        experimental=False,
    ),
    MessageCode.YAML_STRING_TYPE: MessageDefinition(
        code=MessageCode.YAML_STRING_TYPE,
        summary="Expected YAML string",
        template="{value} isn't a string",
    ),
    MessageCode.MAKO_SYNTAX_ERROR: MessageDefinition(
        code=MessageCode.MAKO_SYNTAX_ERROR,
        summary="Invalid Mako syntax",
        template="{error}",
    ),
    MessageCode.MAKO_COMPILE_ERROR: MessageDefinition(
        code=MessageCode.MAKO_COMPILE_ERROR,
        summary="Mako compile error",
        template="{error}",
    ),
    MessageCode.PYTHON_CODE_TYPE: MessageDefinition(
        code=MessageCode.PYTHON_CODE_TYPE,
        summary="Expected Python code as YAML string",
        template="code block must be a YAML string, is {value_type}",
    ),
    MessageCode.PYTHON_SYNTAX_ERROR: MessageDefinition(
        code=MessageCode.PYTHON_SYNTAX_ERROR,
        summary="Python syntax error",
        template="Python syntax error: {message}",
    ),
    MessageCode.JS_MODIFIER_TYPE: MessageDefinition(
        code=MessageCode.JS_MODIFIER_TYPE,
        summary="JavaScript modifier must be string",
        template="{modifier_key} must be a string, is {value_type}",
    ),
    MessageCode.JS_INVALID_SYNTAX: MessageDefinition(
        code=MessageCode.JS_INVALID_SYNTAX,
        summary="Invalid JavaScript syntax",
        template="Invalid JavaScript syntax in {modifier_key}: {error}",
    ),
    MessageCode.JS_MISSING_VAL_CALL: MessageDefinition(
        code=MessageCode.JS_MISSING_VAL_CALL,
        summary="Missing val() call in JavaScript modifier",
        template="{modifier_key} must contain at least one val() call to reference an on-screen field",
    ),
    MessageCode.JS_UNKNOWN_SCREEN_FIELD: MessageDefinition(
        code=MessageCode.JS_UNKNOWN_SCREEN_FIELD,
        summary="val() references field not defined on this screen",
        template='{modifier_key} references val("{var_name}"), but "{var_name}" is not defined on this screen{caveat}',
    ),
    MessageCode.JS_VAL_ARG_NOT_QUOTED: MessageDefinition(
        code=MessageCode.JS_VAL_ARG_NOT_QUOTED,
        summary="val() argument must be quoted string literal",
        template='val() argument must be a quoted string literal, not "{bad_arg}". Use val("...") or val(\'...\') instead',
    ),
    MessageCode.SHOW_IF_MALFORMED: MessageDefinition(
        code=MessageCode.SHOW_IF_MALFORMED,
        summary="Malformed show if shorthand",
        template='show if value "{value}" appears to be malformed. Use YAML dict syntax: show if: {{ variable: var_name, is: value }} or show if: {{ code: ... }}',
    ),
    MessageCode.SHOW_IF_CODE_TYPE: MessageDefinition(
        code=MessageCode.SHOW_IF_CODE_TYPE,
        summary="show if code must be YAML string",
        template="show if: code must be a YAML string",
    ),
    MessageCode.SHOW_IF_CODE_SYNTAX: MessageDefinition(
        code=MessageCode.SHOW_IF_CODE_SYNTAX,
        summary="show if code has Python syntax error",
        template="show if: code has Python syntax error: {message}",
    ),
    MessageCode.SHOW_IF_DICT_KEYS: MessageDefinition(
        code=MessageCode.SHOW_IF_DICT_KEYS,
        summary="show if dict missing variable/code",
        template='show if dict must have either "variable" key or "code" key',
    ),
    MessageCode.BOOLEAN_DATATYPE_CHOICES_IGNORED: MessageDefinition(
        code=MessageCode.BOOLEAN_DATATYPE_CHOICES_IGNORED,
        summary="choices or code are silently ignored with this datatype",
        template='choices or code are silently ignored when datatype is "{datatype}"; the boolean widget takes priority at runtime',
        experimental=False,
    ),
    MessageCode.PYTHON_VAR_TYPE: MessageDefinition(
        code=MessageCode.PYTHON_VAR_TYPE,
        summary="Python variable reference must be YAML string",
        template="The python var needs to be a YAML string, is {value}",
    ),
    MessageCode.PYTHON_VAR_WHITESPACE: MessageDefinition(
        code=MessageCode.PYTHON_VAR_WHITESPACE,
        summary="Python variable reference cannot contain whitespace",
        template="The python var cannot have whitespace (is {value})",
    ),
    MessageCode.OBJECTS_BLOCK_TYPE: MessageDefinition(
        code=MessageCode.OBJECTS_BLOCK_TYPE,
        summary="Objects block must be list or dict",
        template="Objects block needs to be a list or a dict, is {value}",
    ),
    MessageCode.FIELDS_CODE_TYPE: MessageDefinition(
        code=MessageCode.FIELDS_CODE_TYPE,
        summary="fields code must be YAML string",
        template="fields: code must be a YAML string, is {value_type}",
    ),
    MessageCode.FIELDS_TYPE: MessageDefinition(
        code=MessageCode.FIELDS_TYPE,
        summary="fields must be list or dict",
        template="fields should be a list or dict, is {value}",
    ),
    MessageCode.FIELD_MODIFIER_VARIABLE_TYPE: MessageDefinition(
        code=MessageCode.FIELD_MODIFIER_VARIABLE_TYPE,
        summary="field modifier variable must be string",
        template="{modifier_key}: variable must be a string, got {value_type}",
    ),
    MessageCode.FIELD_MODIFIER_UNKNOWN_VARIABLE_DICT: MessageDefinition(
        code=MessageCode.FIELD_MODIFIER_UNKNOWN_VARIABLE_DICT,
        summary="field modifier variable references off-screen field",
        template="{modifier_key}: variable: {ref_var} is not defined on this screen. Use {modifier_key}: {{ code: ... }} instead for variables from previous screens",
    ),
    MessageCode.FIELD_MODIFIER_CODE_ERROR: MessageDefinition(
        code=MessageCode.FIELD_MODIFIER_CODE_ERROR,
        summary="field modifier code has validation error",
        template="{modifier_key}: code has {error}",
    ),
    MessageCode.FIELD_MODIFIER_SAME_SCREEN_CODE: MessageDefinition(
        code=MessageCode.FIELD_MODIFIER_SAME_SCREEN_CODE,
        summary="show if code references same-screen field",
        template="{modifier_key}: code references variable(s) defined on this screen ({references}). Use {modifier_key}: <var> or {modifier_key}: {{ variable: <var>, is: ... }} instead",
    ),
    MessageCode.FIELD_MODIFIER_DICT_KEYS: MessageDefinition(
        code=MessageCode.FIELD_MODIFIER_DICT_KEYS,
        summary="field modifier dict missing variable/code",
        template='{modifier_key} dict must have either "variable" or "code"',
    ),
    MessageCode.FIELD_MODIFIER_UNKNOWN_VARIABLE_STRING: MessageDefinition(
        code=MessageCode.FIELD_MODIFIER_UNKNOWN_VARIABLE_STRING,
        summary="field modifier shorthand references off-screen field",
        template="{modifier_key}: {modifier_value} is not defined on this screen. Use {modifier_key}: {{ code: ... }} instead for variables from previous screens",
    ),
    MessageCode.OBJECT_FIELD_CHOICES_CODE_DICT: MessageDefinition(
        code=MessageCode.OBJECT_FIELD_CHOICES_CODE_DICT,
        summary="Object field choices cannot use nested code block",
        template='Object-style fields cannot use "choices: {{ code: ... }}". Use a direct choices expression instead, for example "choices: some_object.choices()"',
    ),
    MessageCode.FIELD_ITEM_MISSING_TARGET: MessageDefinition(
        code=MessageCode.FIELD_ITEM_MISSING_TARGET,
        summary="label requires field",
        template="If you use 'label' to label a field in a 'fields' section, you must also include a 'field.'",
    ),
    MessageCode.FIELD_ITEM_MISSING_LABEL: MessageDefinition(
        code=MessageCode.FIELD_ITEM_MISSING_LABEL,
        summary="field requires label",
        template="If you use 'field' to indicate a variable in a 'fields' section, you must also include a 'label.'",
    ),
    MessageCode.FIELD_TARGET_NOT_PLAIN_TEXT: MessageDefinition(
        code=MessageCode.FIELD_TARGET_NOT_PLAIN_TEXT,
        summary="field target must be plain text",
        template="Fields in a 'field' section must be plain text.",
    ),
    MessageCode.FIELD_TARGET_INVALID_VARIABLE: MessageDefinition(
        code=MessageCode.FIELD_TARGET_INVALID_VARIABLE,
        summary="invalid field variable name",
        template="Missing or invalid variable name {value_repr}{context}.",
    ),
    MessageCode.FIELD_LABEL_OVERWRITE: MessageDefinition(
        code=MessageCode.FIELD_LABEL_OVERWRITE,
        summary="field label overwrite syntax error",
        template="Syntax error: field label '{label_key}' overwrites previous label, '{previous_label}'",
    ),
    MessageCode.MULTIPLE_CHOICE_FIELD_MISSING_CHOICES: MessageDefinition(
        code=MessageCode.MULTIPLE_CHOICE_FIELD_MISSING_CHOICES,
        summary="multiple choice field missing choices",
        template="A multiple choice field must refer to a list of choices.",
    ),
    MessageCode.AJAX_FIELD_MISSING_ACTION: MessageDefinition(
        code=MessageCode.AJAX_FIELD_MISSING_ACTION,
        summary="ajax field missing action",
        template="An ajax field must have an associated action.",
    ),
    MessageCode.AJAX_FIELD_CANNOT_DECLARE_CHOICES: MessageDefinition(
        code=MessageCode.AJAX_FIELD_CANNOT_DECLARE_CHOICES,
        summary="ajax field cannot declare choices directly",
        template="An ajax field cannot contain a list of choices except through an action.",
    ),
    MessageCode.OBJECT_LABELER_REQUIRES_OBJECT_DATATYPE: MessageDefinition(
        code=MessageCode.OBJECT_LABELER_REQUIRES_OBJECT_DATATYPE,
        summary="object labeler requires object datatype",
        template="An object labeler can only be used with an object data type.",
    ),
    MessageCode.FIELD_PRESENTATION_KEY_CONFLICT: MessageDefinition(
        code=MessageCode.FIELD_PRESENTATION_KEY_CONFLICT,
        summary="conflicting note/html/raw html keys",
        template="You cannot combine note, html, and/or raw html in a single field.",
    ),
    MessageCode.FIELD_ITEM_MUST_BE_DICT: MessageDefinition(
        code=MessageCode.FIELD_ITEM_MUST_BE_DICT,
        summary="field list item must be a dictionary",
        template="Each individual field in a list of fields must be expressed as a dictionary item, e.g., ' - Fruit: user.favorite_fruit'.",
    ),
    MessageCode.HIDDEN_FIELD_INVALID_DATATYPE: MessageDefinition(
        code=MessageCode.HIDDEN_FIELD_INVALID_DATATYPE,
        summary="invalid hidden field datatype",
        template="Invalid datatype of hidden field.",
    ),
    MessageCode.FIELDS_LABEL_SHORTHAND_DISALLOWED: MessageDefinition(
        code=MessageCode.FIELDS_LABEL_SHORTHAND_DISALLOWED,
        summary="fields label shorthand disallowed",
        template="Use explicit 'label' and 'field' keys in 'fields' instead of '{label_key}: {field_name}'.",
    ),
    MessageCode.RADIO_DATATYPE_WITH_CHOICES_PREFER_INPUT_TYPE: MessageDefinition(
        code=MessageCode.RADIO_DATATYPE_WITH_CHOICES_PREFER_INPUT_TYPE,
        summary="prefer input type radio over datatype radio with choices",
        template="Use 'input type: radio' instead of 'datatype: radio' when choices or code provide radio options.",
    ),
    MessageCode.FIELD_EXCLUDE_INVALID_FORMAT: MessageDefinition(
        code=MessageCode.FIELD_EXCLUDE_INVALID_FORMAT,
        summary="exclude entry cannot be a dictionary",
        template="An exclude entry cannot be a dictionary.",
    ),
    MessageCode.FIELD_DEFAULT_INVALID_FORMAT: MessageDefinition(
        code=MessageCode.FIELD_DEFAULT_INVALID_FORMAT,
        summary="default list is not in appropriate format",
        template="default list is not in appropriate format",
    ),
    MessageCode.RANGE_MISSING_MIN_MAX: MessageDefinition(
        code=MessageCode.RANGE_MISSING_MIN_MAX,
        summary="range datatype requires min and max",
        template="If the datatype of a field is 'range', you must provide both a 'min' and a 'max'.",
    ),
    MessageCode.FILE_KEY_WITHOUT_FILE_DATATYPE: MessageDefinition(
        code=MessageCode.FILE_KEY_WITHOUT_FILE_DATATYPE,
        summary="file-only key used on non-file datatype",
        template="'{key_name}' is only meaningful with file-like datatypes (file, files, camera, user, environment, camcorder, microphone). Current datatype is '{datatype}'.",
    ),
    MessageCode.ROWS_WITHOUT_COMPATIBLE_TYPE: MessageDefinition(
        code=MessageCode.ROWS_WITHOUT_COMPATIBLE_TYPE,
        summary="rows key requires area input type or area/multiselect datatype",
        template="The 'rows' modifier is only meaningful when 'input type' is 'area' or 'datatype' is 'area'/'multiselect'/'object_multiselect'. Current input type is '{input_type}', datatype is '{datatype}'.",
    ),
    # Packet 7: Choices And Buttons
    MessageCode.DISABLE_OTHERS_INCOMPATIBLE_DATATYPE: MessageDefinition(
        code=MessageCode.DISABLE_OTHERS_INCOMPATIBLE_DATATYPE,
        summary="disable others incompatible datatype",
        template="A 'disable others' directive cannot be used with '{datatype}' datatype.",
        experimental=False,
    ),
    MessageCode.DISABLE_OTHERS_INVALID_TYPE: MessageDefinition(
        code=MessageCode.DISABLE_OTHERS_INVALID_TYPE,
        summary="disable others must be boolean or list",
        template="A 'disable others' directive must be True, False, or a list of variable names.",
        experimental=False,
    ),
    MessageCode.UNCHECK_OTHERS_REQUIRES_YESNO: MessageDefinition(
        code=MessageCode.UNCHECK_OTHERS_REQUIRES_YESNO,
        summary="uncheck others requires yesno datatype",
        template="An 'uncheck others' directive can only be used with a yesno/noyes datatype.",
        experimental=False,
    ),
    MessageCode.UNCHECK_OTHERS_INVALID_TYPE: MessageDefinition(
        code=MessageCode.UNCHECK_OTHERS_INVALID_TYPE,
        summary="uncheck others must be boolean or list",
        template="An 'uncheck others' directive must be True, False, or a list of variable names.",
        experimental=False,
    ),
    MessageCode.CHECK_OTHERS_REQUIRES_YESNO: MessageDefinition(
        code=MessageCode.CHECK_OTHERS_REQUIRES_YESNO,
        summary="check others requires yesno datatype",
        template="A 'check others' directive can only be used with a yesno/noyes datatype.",
        experimental=False,
    ),
    MessageCode.CHECK_OTHERS_INVALID_TYPE: MessageDefinition(
        code=MessageCode.CHECK_OTHERS_INVALID_TYPE,
        summary="check others must be boolean or list",
        template="A 'check others' directive must be True, False, or a list of variable names.",
        experimental=False,
    ),
    MessageCode.SHUFFLE_NOT_BOOLEAN: MessageDefinition(
        code=MessageCode.SHUFFLE_NOT_BOOLEAN,
        summary="shuffle must be boolean",
        template="The 'shuffle' modifier must be True or False.",
        experimental=False,
    ),
    MessageCode.ALL_OF_THE_ABOVE_INCOMPATIBLE_DATATYPE: MessageDefinition(
        code=MessageCode.ALL_OF_THE_ABOVE_INCOMPATIBLE_DATATYPE,
        summary="all of the above requires checkboxes datatype",
        template="The 'all of the above' field modifier can only be used with datatype 'checkboxes' or 'object_checkboxes'. Current datatype is '{datatype}'.",
        experimental=False,
    ),
    MessageCode.NONE_OF_THE_ABOVE_INCOMPATIBLE_DATATYPE: MessageDefinition(
        code=MessageCode.NONE_OF_THE_ABOVE_INCOMPATIBLE_DATATYPE,
        summary="none of the above requires checkboxes or object_radio datatype",
        template="The 'none of the above' field modifier can only be used with datatype 'checkboxes', 'object_checkboxes', or 'object_radio'. Current datatype is '{datatype}'.",
        experimental=False,
    ),
    # Packet 8: Field Conditions And Validation
    MessageCode.VALIDATE_TYPE: MessageDefinition(
        code=MessageCode.VALIDATE_TYPE,
        summary="validate must be a Python expression string",
        template="The 'validate' field modifier must be a Python expression string, is {value_type}.",
    ),
    MessageCode.VALIDATE_SYNTAX: MessageDefinition(
        code=MessageCode.VALIDATE_SYNTAX,
        summary="validate Python expression has a syntax error",
        template="The 'validate' Python expression has a syntax error: {message}.",
    ),
    MessageCode.VALIDATION_MESSAGES_TYPE: MessageDefinition(
        code=MessageCode.VALIDATION_MESSAGES_TYPE,
        summary="validation messages must be a dictionary",
        template="The 'validation messages' field modifier must be a dictionary of text keys and text values.",
    ),
    MessageCode.VALIDATION_MESSAGES_ENTRY_TYPE: MessageDefinition(
        code=MessageCode.VALIDATION_MESSAGES_ENTRY_TYPE,
        summary="validation messages entry must have text key and text value",
        template="Each entry in 'validation messages' must have a text key and a text value.",
    ),
    MessageCode.TRIGGER_AT_TYPE: MessageDefinition(
        code=MessageCode.TRIGGER_AT_TYPE,
        summary="trigger at must be an integer greater than one",
        template="The 'trigger at' field modifier must be an integer greater than one, is {value_repr}.",
    ),
    MessageCode.HELP_GENERATOR_TYPE: MessageDefinition(
        code=MessageCode.HELP_GENERATOR_TYPE,
        summary="help generator must be a string",
        template="The 'help generator' field modifier must be a string (Python expression), is {value_type}.",
    ),
    MessageCode.HELP_GENERATOR_SYNTAX: MessageDefinition(
        code=MessageCode.HELP_GENERATOR_SYNTAX,
        summary="help generator Python expression has a syntax error",
        template="The 'help generator' Python expression has a syntax error: {message}.",
    ),
    MessageCode.IMAGE_GENERATOR_TYPE: MessageDefinition(
        code=MessageCode.IMAGE_GENERATOR_TYPE,
        summary="image generator must be a string",
        template="The 'image generator' field modifier must be a string (Python expression), is {value_type}.",
    ),
    MessageCode.IMAGE_GENERATOR_SYNTAX: MessageDefinition(
        code=MessageCode.IMAGE_GENERATOR_SYNTAX,
        summary="image generator Python expression has a syntax error",
        template="The 'image generator' Python expression has a syntax error: {message}.",
    ),
    MessageCode.ML_USING_TYPE: MessageDefinition(
        code=MessageCode.ML_USING_TYPE,
        summary="using must be a string for ml/mlarea datatypes",
        template="The 'using' field modifier must be a string when used with ml/mlarea datatypes, is {value_type}.",
    ),
    MessageCode.KEEP_FOR_TRAINING_TYPE: MessageDefinition(
        code=MessageCode.KEEP_FOR_TRAINING_TYPE,
        summary="keep for training must be boolean or Python expression",
        template="The 'keep for training' field modifier must be a boolean or Python expression string, is {value_type}.",
    ),
    MessageCode.NEED_TYPE: MessageDefinition(
        code=MessageCode.NEED_TYPE,
        summary="need must be text or list",
        template="A need phrase must be text or a list.",
    ),
    MessageCode.NEED_DICT_KEYS: MessageDefinition(
        code=MessageCode.NEED_DICT_KEYS,
        summary="need dict only allows pre/post",
        template="If 'need' contains a dictionary it can only include keys 'pre' or 'post'.",
    ),
    MessageCode.NEED_PHASE_TYPE: MessageDefinition(
        code=MessageCode.NEED_PHASE_TYPE,
        summary="need pre/post must be text or list",
        template="A need {phase} phrase must be text or a list.",
    ),
    MessageCode.NEED_ITEM_STRING: MessageDefinition(
        code=MessageCode.NEED_ITEM_STRING,
        summary="need items must be text strings",
        template="In 'need', the items must be text strings.",
    ),
    MessageCode.ON_CHANGE_TYPE: MessageDefinition(
        code=MessageCode.ON_CHANGE_TYPE,
        summary="on change must be a dictionary",
        template="An on change block must be a dictionary.",
    ),
    MessageCode.ON_CHANGE_EXTRA_KEYS: MessageDefinition(
        code=MessageCode.ON_CHANGE_EXTRA_KEYS,
        summary="on change cannot have sibling keys",
        template="An on change block must not contain any other keys.",
    ),
    MessageCode.ON_CHANGE_ENTRY_TYPE: MessageDefinition(
        code=MessageCode.ON_CHANGE_ENTRY_TYPE,
        summary="on change entries must map field names to Python code",
        template="An on change block must be a dictionary where the keys are field names and the values are Python code.",
    ),
    MessageCode.ACTION_BUTTONS_TYPE: MessageDefinition(
        code=MessageCode.ACTION_BUTTONS_TYPE,
        summary="action buttons must be a list",
        template="An action buttons specifier must be a list.",
    ),
    MessageCode.ACTION_BUTTON_ITEM_TYPE: MessageDefinition(
        code=MessageCode.ACTION_BUTTON_ITEM_TYPE,
        summary="action buttons item must be a dictionary",
        template="An action buttons item must be a dictionary.",
    ),
    MessageCode.ACTION_BUTTON_ACTION_TYPE: MessageDefinition(
        code=MessageCode.ACTION_BUTTON_ACTION_TYPE,
        summary="action button action must be plain text",
        template="An action buttons item must contain an action in plain text.",
    ),
    MessageCode.ACTION_BUTTON_NEW_WINDOW_TYPE: MessageDefinition(
        code=MessageCode.ACTION_BUTTON_NEW_WINDOW_TYPE,
        summary="new window must be true or plain text",
        template="The new window specifier in an action buttons item must refer to True or plain text.",
    ),
    MessageCode.ACTION_BUTTON_ARGUMENTS_TYPE: MessageDefinition(
        code=MessageCode.ACTION_BUTTON_ARGUMENTS_TYPE,
        summary="action button arguments must be a dictionary",
        template="The arguments specifier in an action buttons item must refer to a dictionary.",
    ),
    MessageCode.ACTION_BUTTON_LABEL_TYPE: MessageDefinition(
        code=MessageCode.ACTION_BUTTON_LABEL_TYPE,
        summary="action button label must be plain text",
        template="An action buttons item must contain a label in plain text.",
    ),
    MessageCode.ACTION_BUTTON_COLOR_TYPE: MessageDefinition(
        code=MessageCode.ACTION_BUTTON_COLOR_TYPE,
        summary="action button color must be plain text",
        template="The color specifier in an action buttons item must refer to plain text.",
    ),
    MessageCode.ACTION_BUTTON_ICON_TYPE: MessageDefinition(
        code=MessageCode.ACTION_BUTTON_ICON_TYPE,
        summary="action button icon must be plain text",
        template="The icon specifier in an action buttons item must refer to plain text.",
    ),
    MessageCode.ACTION_BUTTON_PLACEMENT_TYPE: MessageDefinition(
        code=MessageCode.ACTION_BUTTON_PLACEMENT_TYPE,
        summary="action button placement must be plain text",
        template="The placement specifier in an action buttons item must refer to plain text.",
    ),
    MessageCode.ACTION_BUTTON_CSS_CLASS_TYPE: MessageDefinition(
        code=MessageCode.ACTION_BUTTON_CSS_CLASS_TYPE,
        summary="action button css class must be plain text",
        template="The css classifier specifier in an action buttons item must refer to plain text.",
    ),
    MessageCode.ACTION_BUTTON_FORGET_PRIOR_TYPE: MessageDefinition(
        code=MessageCode.ACTION_BUTTON_FORGET_PRIOR_TYPE,
        summary="forget prior must be boolean",
        template="The forget prior specifier in an action buttons item must refer to true or false.",
    ),
    MessageCode.ACTION_BUTTON_ARGUMENT_ITEM_TYPE: MessageDefinition(
        code=MessageCode.ACTION_BUTTON_ARGUMENT_ITEM_TYPE,
        summary="action button arguments must be plain items",
        template="The arguments specifier in an action buttons item must refer to plain items.",
    ),
    MessageCode.TRANSLATIONS_TYPE: MessageDefinition(
        code=MessageCode.TRANSLATIONS_TYPE,
        summary="translations must be a list",
        template="A 'translations' block must be a list",
    ),
    MessageCode.TRANSLATIONS_ITEM_TYPE: MessageDefinition(
        code=MessageCode.TRANSLATIONS_ITEM_TYPE,
        summary="translations must be text items",
        template="A 'translations' block must be a list of text items",
    ),
    MessageCode.TRANSLATIONS_SUFFIX: MessageDefinition(
        code=MessageCode.TRANSLATIONS_SUFFIX,
        summary="translations entry must end with translation file suffix",
        template="Invalid translations entry '{item}'.  A translations entry must refer to a file ending in .xlsx, .xlf, or .xliff.",
    ),
    MessageCode.TRANSLATIONS_PATH: MessageDefinition(
        code=MessageCode.TRANSLATIONS_PATH,
        summary="translations entry must refer to data sources file",
        template="Invalid translations entry: {item}.  A translations entry must refer to a data sources file",
    ),
    MessageCode.IF_TYPE: MessageDefinition(
        code=MessageCode.IF_TYPE,
        summary="if must be text or list",
        template="An if statement must either be text or a list.",
    ),
    MessageCode.REQUIRE_TYPE: MessageDefinition(
        code=MessageCode.REQUIRE_TYPE,
        summary="require must be organized as a list",
        template="A require section must be organized as a list.",
    ),
    MessageCode.REQUIRE_ORELSE_MISSING: MessageDefinition(
        code=MessageCode.REQUIRE_ORELSE_MISSING,
        summary="require must have orelse",
        template="A require section must have an orelse part.",
    ),
    MessageCode.REQUIRE_ORELSE_TYPE: MessageDefinition(
        code=MessageCode.REQUIRE_ORELSE_TYPE,
        summary="require orelse must be a dictionary",
        template="The orelse part of a require section must be organized as a dictionary.",
    ),
    MessageCode.TERMS_TYPE: MessageDefinition(
        code=MessageCode.TERMS_TYPE,
        summary="terms must be organized as a dictionary or list",
        template="A terms section must be organized as a dictionary or a list.",
    ),
    MessageCode.TERMS_ITEM_TYPE: MessageDefinition(
        code=MessageCode.TERMS_ITEM_TYPE,
        summary="terms list must contain dictionary items",
        template="A terms section organized as a list must be a list of dictionary items.",
    ),
    MessageCode.AUTO_TERMS_TYPE: MessageDefinition(
        code=MessageCode.AUTO_TERMS_TYPE,
        summary="auto terms must be organized as a dictionary or list",
        template="An auto terms section must be organized as a dictionary or a list.",
    ),
    MessageCode.AUTO_TERMS_ITEM_TYPE: MessageDefinition(
        code=MessageCode.AUTO_TERMS_ITEM_TYPE,
        summary="auto terms list must contain dictionary items",
        template="An auto terms section organized as a list must be a list of dictionary items.",
    ),
    MessageCode.INCLUDE_TYPE: MessageDefinition(
        code=MessageCode.INCLUDE_TYPE,
        summary="include must be a string or list of strings",
        template="An include block must be a string path or a list of string paths.",
    ),
    MessageCode.INCLUDE_ITEM_TYPE: MessageDefinition(
        code=MessageCode.INCLUDE_ITEM_TYPE,
        summary="include list item must be a string",
        template="Each item in an include list must be a string path.",
    ),
    MessageCode.MODULES_TYPE: MessageDefinition(
        code=MessageCode.MODULES_TYPE,
        summary="modules must be a string or list of strings",
        template="A modules block must be a module name string or a list of module name strings.",
    ),
    MessageCode.MODULES_ITEM_TYPE: MessageDefinition(
        code=MessageCode.MODULES_ITEM_TYPE,
        summary="modules list item must be a string",
        template="Each item in a modules list must be a string.",
    ),
    MessageCode.IMPORTS_TYPE: MessageDefinition(
        code=MessageCode.IMPORTS_TYPE,
        summary="imports must be a string or list of strings",
        template="An imports block must be an import statement string or a list of import statement strings.",
    ),
    MessageCode.IMPORTS_ITEM_TYPE: MessageDefinition(
        code=MessageCode.IMPORTS_ITEM_TYPE,
        summary="imports list item must be a string",
        template="Each item in an imports list must be a string.",
    ),
    MessageCode.METADATA_TYPE: MessageDefinition(
        code=MessageCode.METADATA_TYPE,
        summary="metadata must be a mapping",
        template="A metadata block must be a YAML mapping (dictionary), not a scalar or list.",
    ),
    MessageCode.SETS_TYPE: MessageDefinition(
        code=MessageCode.SETS_TYPE,
        summary="sets/only sets must be a string or list",
        template="A sets or only sets block must be a variable name string or a list of variable name strings.",
    ),
    MessageCode.SETS_ITEM_TYPE: MessageDefinition(
        code=MessageCode.SETS_ITEM_TYPE,
        summary="sets/only sets item must be a string",
        template="Each item in a sets or only sets list must be a variable name string.",
    ),
    MessageCode.FEATURES_TYPE: MessageDefinition(
        code=MessageCode.FEATURES_TYPE,
        summary="features must be a mapping",
        template="A features block must be a YAML mapping (dictionary), not a scalar or list.",
    ),
    MessageCode.EVENT_TYPE: MessageDefinition(
        code=MessageCode.EVENT_TYPE,
        summary="event must be a string or list",
        template="An event block must be an event name string or a list of event name strings.",
    ),
    MessageCode.EVENT_ITEM_TYPE: MessageDefinition(
        code=MessageCode.EVENT_ITEM_TYPE,
        summary="event list item must be a string",
        template="Each item in an event list must be an event name string.",
    ),
    MessageCode.RECONSIDER_TYPE: MessageDefinition(
        code=MessageCode.RECONSIDER_TYPE,
        summary="reconsider must be a bool, string, or list",
        template="A reconsider directive must be true, false, a single variable name string, or a list of variable name strings.",
    ),
    MessageCode.RECONSIDER_ITEM_TYPE: MessageDefinition(
        code=MessageCode.RECONSIDER_ITEM_TYPE,
        summary="reconsider list item must be a string",
        template="Each item in a reconsider list must be a variable name string.",
    ),
    MessageCode.UNDEFINE_TYPE: MessageDefinition(
        code=MessageCode.UNDEFINE_TYPE,
        summary="undefine must be a string or list",
        template="An undefine directive must be a variable name string or a list of variable name strings.",
    ),
    MessageCode.UNDEFINE_ITEM_TYPE: MessageDefinition(
        code=MessageCode.UNDEFINE_ITEM_TYPE,
        summary="undefine list item must be a string",
        template="Each item in an undefine list must be a variable name string.",
    ),
    MessageCode.SUPERSEDES_TYPE: MessageDefinition(
        code=MessageCode.SUPERSEDES_TYPE,
        summary="supersedes must be a string or list",
        template="A supersedes directive must be a block ID string or a list of block ID strings.",
    ),
    MessageCode.SUPERSEDES_ITEM_TYPE: MessageDefinition(
        code=MessageCode.SUPERSEDES_ITEM_TYPE,
        summary="supersedes list item must be a string",
        template="Each item in a supersedes list must be a block ID string.",
    ),
    MessageCode.DEPENDS_ON_TYPE: MessageDefinition(
        code=MessageCode.DEPENDS_ON_TYPE,
        summary="depends on must be a string or list",
        template="A depends on directive must be a variable name string or a list of variable name strings.",
    ),
    MessageCode.DEPENDS_ON_ITEM_TYPE: MessageDefinition(
        code=MessageCode.DEPENDS_ON_ITEM_TYPE,
        summary="depends on list item must be a string",
        template="Each item in a depends on list must be a variable name string.",
    ),
    MessageCode.ROLE_TYPE: MessageDefinition(
        code=MessageCode.ROLE_TYPE,
        summary="role must be a string or list",
        template="A role directive must be a role name string or a list of role name strings.",
    ),
    MessageCode.ROLE_ITEM_TYPE: MessageDefinition(
        code=MessageCode.ROLE_ITEM_TYPE,
        summary="role list item must be a string",
        template="Each item in a role list must be a role name string.",
    ),
    MessageCode.ALLOWED_TO_SET_TYPE: MessageDefinition(
        code=MessageCode.ALLOWED_TO_SET_TYPE,
        summary="allowed to set must be a string or list",
        template="An allowed to set directive must be a Python expression string or a list of variable name strings.",
    ),
    MessageCode.PROGRESS_TYPE: MessageDefinition(
        code=MessageCode.PROGRESS_TYPE,
        summary="progress must be an integer",
        template="A progress directive must be an integer between 0 and 100.",
    ),
    MessageCode.NO_POSSIBLE_TYPES: MessageDefinition(
        code=MessageCode.NO_POSSIBLE_TYPES,
        summary="No recognized block type found",
        template="Couldn't identify a block type: no valid combination of keys found (looking for keys like question, include, metadata, code, objects, etc. See https://docassemble.org/docs.html)",
    ),
    MessageCode.TOO_MANY_TYPES: MessageDefinition(
        code=MessageCode.TOO_MANY_TYPES,
        summary="Block matches multiple exclusive types",
        template="Too many types this block could be: {possible_types}",
    ),
    MessageCode.INTERVIEW_ORDER_UNMATCHED_GUARD: MessageDefinition(
        code=MessageCode.INTERVIEW_ORDER_UNMATCHED_GUARD,
        summary="Interview-order block missing matching guard",
        template='interview-order style block references "{field_var}" without a matching guard for that field\'s show/hide logic; this can cause the interview to get stuck',
    ),
    MessageCode.NESTED_VISIBILITY_LOGIC: MessageDefinition(
        code=MessageCode.NESTED_VISIBILITY_LOGIC,
        summary="Visibility logic is nested too deeply",
        template="show if/hide if visibility logic is nested {depth} levels on this screen (more than 2)",
    ),
    MessageCode.ACCESSIBILITY_COMBOBOX_NOT_ACCESSIBLE: MessageDefinition(
        code=MessageCode.ACCESSIBILITY_COMBOBOX_NOT_ACCESSIBLE,
        summary="Combobox widget is not accessible",
        template="Accessibility: combobox widgets are not allowed for accessibility reasons",
    ),
    MessageCode.ACCESSIBILITY_NO_LABEL_MULTI_FIELD: MessageDefinition(
        code=MessageCode.ACCESSIBILITY_NO_LABEL_MULTI_FIELD,
        summary="Field label missing on multi-field screen",
        template="Accessibility: no label or empty/missing field label is only allowed on single-field screens",
    ),
    MessageCode.ACCESSIBILITY_TAGGED_PDF_NOT_ENABLED: MessageDefinition(
        code=MessageCode.ACCESSIBILITY_TAGGED_PDF_NOT_ENABLED,
        summary="DOCX attachment may need tagged PDF enabled",
        template="Accessibility: DOCX attachment detected without tagged pdf enabled",
    ),
    MessageCode.ACCESSIBILITY_THEME_CONTRAST_TOO_LOW: MessageDefinition(
        code=MessageCode.ACCESSIBILITY_THEME_CONTRAST_TOO_LOW,
        summary="Bootstrap theme CSS has low contrast",
        template="Accessibility: bootstrap theme CSS has low contrast",
    ),
    MessageCode.ACCESSIBILITY_IMAGE_MISSING_ALT_TEXT: MessageDefinition(
        code=MessageCode.ACCESSIBILITY_IMAGE_MISSING_ALT_TEXT,
        summary="Image is missing alt text",
        template="Accessibility: image is missing alt text",
    ),
    MessageCode.ACCESSIBILITY_MARKDOWN_HEADING_LEVEL_SKIP: MessageDefinition(
        code=MessageCode.ACCESSIBILITY_MARKDOWN_HEADING_LEVEL_SKIP,
        summary="Markdown heading levels skip",
        template="Accessibility: markdown heading levels skip",
    ),
    MessageCode.ACCESSIBILITY_HTML_HEADING_LEVEL_SKIP: MessageDefinition(
        code=MessageCode.ACCESSIBILITY_HTML_HEADING_LEVEL_SKIP,
        summary="HTML heading levels skip",
        template="Accessibility: HTML heading levels skip",
    ),
    MessageCode.ACCESSIBILITY_EMPTY_LINK_TEXT: MessageDefinition(
        code=MessageCode.ACCESSIBILITY_EMPTY_LINK_TEXT,
        summary="Link has no accessible text",
        template="Accessibility: link has no accessible text",
    ),
    MessageCode.ACCESSIBILITY_NON_DESCRIPTIVE_LINK_TEXT: MessageDefinition(
        code=MessageCode.ACCESSIBILITY_NON_DESCRIPTIVE_LINK_TEXT,
        summary="Link text is too generic",
        template="Accessibility: link text is too generic",
    ),
    MessageCode.VALIDATION_CODE_MISSING_VALIDATION_ERROR: MessageDefinition(
        code=MessageCode.VALIDATION_CODE_MISSING_VALIDATION_ERROR,
        summary="Prefer validation_error() over raise/assert in validation code",
        template="Prefer validation_error() over raise/assert in validation code",
    ),
    MessageCode.DATATYPE_AREA_PREFER_INPUT_TYPE: MessageDefinition(
        code=MessageCode.DATATYPE_AREA_PREFER_INPUT_TYPE,
        summary="prefer input type area over datatype area",
        template="Use 'input type: area' instead of 'datatype: area'. 'datatype: area' is deprecated.",
    ),
    MessageCode.FIELD_TARGET_UNDERSCORE: MessageDefinition(
        code=MessageCode.FIELD_TARGET_UNDERSCORE,
        summary="Field target starts with underscore",
        template="Field target {value_repr!s} starts with an underscore. Docassemble uses underscore-prefixed names "
        "internally; using them as interview variable names may cause unexpected behavior.",
    ),
    MessageCode.RESERVED_DA_NAME: MessageDefinition(
        code=MessageCode.RESERVED_DA_NAME,
        summary="Field target uses a Docassemble reserved name",
        template="Field target {value_repr!s} is a Docassemble reserved name{context}. "
        "Using this name may cause errors or unexpected behavior.",
    ),
    MessageCode.DEF_MAKO_REQUIRED: MessageDefinition(
        code=MessageCode.DEF_MAKO_REQUIRED,
        summary="def and mako keys should be used together",
        template="A 'def' block requires a 'mako' key and vice versa. Missing the '{missing_key}' key.",
    ),
    MessageCode.CROSS_DOC_UNDEFINED_EVENT: MessageDefinition(
        code=MessageCode.CROSS_DOC_UNDEFINED_EVENT,
        summary="Referenced event not defined in workspace",
        template="event '{name}' is referenced but not defined in any workspace document",
    ),
    MessageCode.CROSS_DOC_UNDEFINED_DEF: MessageDefinition(
        code=MessageCode.CROSS_DOC_UNDEFINED_DEF,
        summary="Referenced def not defined in workspace",
        template="def '{name}' is referenced but not defined in any workspace document",
    ),
    MessageCode.CROSS_DOC_MISSING_FILE: MessageDefinition(
        code=MessageCode.CROSS_DOC_MISSING_FILE,
        summary="Referenced file not found in workspace",
        template="file '{path}' does not exist in the workspace",
    ),
    MessageCode.CROSS_DOC_MISSING_TEMPLATE: MessageDefinition(
        code=MessageCode.CROSS_DOC_MISSING_TEMPLATE,
        summary="Template file not found in workspace",
        template="template file '{path}' does not exist in the workspace",
    ),
    # Packet 9: Documents And Attachments
    MessageCode.ATTACHMENT_ITEM_MUST_BE_DICT: MessageDefinition(
        code=MessageCode.ATTACHMENT_ITEM_MUST_BE_DICT,
        summary="Attachment item must be a dictionary",
        template="Each attachment in an attachment list must be a dictionary.",
    ),
    MessageCode.ATTACHMENT_NAME_TYPE: MessageDefinition(
        code=MessageCode.ATTACHMENT_NAME_TYPE,
        summary="Attachment name must be plain text",
        template="An attachment name must be plain text.",
    ),
    MessageCode.ATTACHMENT_FILENAME_TYPE: MessageDefinition(
        code=MessageCode.ATTACHMENT_FILENAME_TYPE,
        summary="Attachment filename must be plain text",
        template="An attachment filename must be plain text.",
    ),
    MessageCode.ATTACHMENT_VARIABLE_NAME_TYPE: MessageDefinition(
        code=MessageCode.ATTACHMENT_VARIABLE_NAME_TYPE,
        summary="Attachment variable name must be plain text",
        template="An attachment variable name must be plain text.",
    ),
    MessageCode.ATTACHMENT_METADATA_TYPE: MessageDefinition(
        code=MessageCode.ATTACHMENT_METADATA_TYPE,
        summary="Attachment metadata must be a dictionary",
        template="Attachment metadata must be a dictionary.",
    ),
    MessageCode.ATTACHMENT_VALID_FORMATS_TYPE: MessageDefinition(
        code=MessageCode.ATTACHMENT_VALID_FORMATS_TYPE,
        summary="Attachment valid formats must be a string or list",
        template="Attachment valid formats must be a string or a list.",
    ),
    MessageCode.ATTACHMENT_CODE_TYPE: MessageDefinition(
        code=MessageCode.ATTACHMENT_CODE_TYPE,
        summary="Attachment code must be plain text",
        template="The 'code' in an attachment must be plain text.",
    ),
    MessageCode.ATTACHMENT_FIELD_VARIABLES_TYPE: MessageDefinition(
        code=MessageCode.ATTACHMENT_FIELD_VARIABLES_TYPE,
        summary="Attachment field variables must be a list",
        template="The 'field variables' in an attachment must be a list.",
    ),
    MessageCode.ATTACHMENT_CONTENT_FILE_TYPE: MessageDefinition(
        code=MessageCode.ATTACHMENT_CONTENT_FILE_TYPE,
        summary="Attachment content file must be text, list of text, or a code dict",
        template="A content file must be specified as text, a list of text filenames, or a dictionary where the one key is 'code'.",
    ),
    MessageCode.ATTACHMENT_METADATA_ENTRY_TYPE: MessageDefinition(
        code=MessageCode.ATTACHMENT_METADATA_ENTRY_TYPE,
        summary="Attachment metadata entry has invalid type",
        template="Unknown data type '{data_type}' in attachment metadata key '{key_name}'.",
    ),
    # Packet 10: Review And Table
    MessageCode.REVIEW_TYPE: MessageDefinition(
        code=MessageCode.REVIEW_TYPE,
        summary="Review must be a list",
        template="A review block must be a list.",
    ),
    MessageCode.REVIEW_ITEM_TYPE: MessageDefinition(
        code=MessageCode.REVIEW_ITEM_TYPE,
        summary="Review item must be a dictionary",
        template="Each item in a review block must be a dictionary.",
    ),
    MessageCode.REVIEW_LABEL_REQUIRES_FIELD: MessageDefinition(
        code=MessageCode.REVIEW_LABEL_REQUIRES_FIELD,
        summary="Review label requires field or fields",
        template="If you use 'label' in a review block, you must also include 'field' or 'fields'.",
    ),
    MessageCode.REVIEW_FIELD_REQUIRES_LABEL: MessageDefinition(
        code=MessageCode.REVIEW_FIELD_REQUIRES_LABEL,
        summary="Review field or fields requires label",
        template="If you use 'field' or 'fields' in a review block, you must also include a 'label'.",
    ),
    MessageCode.REVIEW_NOTE_TYPE: MessageDefinition(
        code=MessageCode.REVIEW_NOTE_TYPE,
        summary="Review note/html/raw html must be plain text",
        template="Review note/html/raw html content must be plain text.",
    ),
    MessageCode.REVIEW_SHOW_IF_TYPE: MessageDefinition(
        code=MessageCode.REVIEW_SHOW_IF_TYPE,
        summary="Review show if must be plain text or a list",
        template="A 'show if' in a review item must be a variable name string or a list of variable name strings.",
    ),
    MessageCode.REVIEW_HELP_TYPE: MessageDefinition(
        code=MessageCode.REVIEW_HELP_TYPE,
        summary="Review help must be plain text",
        template="Help text in a review item must be plain text.",
    ),
    MessageCode.REVIEW_ACTION_TYPE: MessageDefinition(
        code=MessageCode.REVIEW_ACTION_TYPE,
        summary="Review action must be plain text",
        template="An 'action' in a review item must be plain text.",
    ),
    MessageCode.REVIEW_BUTTON_TYPE: MessageDefinition(
        code=MessageCode.REVIEW_BUTTON_TYPE,
        summary="Review button must be plain text",
        template="A 'button' in a review item must be plain text.",
    ),
    MessageCode.REVIEW_CSS_CLASS_TYPE: MessageDefinition(
        code=MessageCode.REVIEW_CSS_CLASS_TYPE,
        summary="Review css class must be plain text",
        template="A 'css class' in a review item must be plain text.",
    ),
    MessageCode.TABLE_REQUIRED_KEYS: MessageDefinition(
        code=MessageCode.TABLE_REQUIRED_KEYS,
        summary="Table requires table, rows, and columns",
        template="A table block must define 'table', 'rows', and 'columns'.",
    ),
    MessageCode.TABLE_TYPE: MessageDefinition(
        code=MessageCode.TABLE_TYPE,
        summary="Table must be a string or object",
        template="The 'table' value must be a variable name string or an object.",
    ),
    MessageCode.TABLE_ROWS_TYPE: MessageDefinition(
        code=MessageCode.TABLE_ROWS_TYPE,
        summary="Table rows must be plain Python code",
        template="The 'rows' value must be a Python expression string.",
    ),
    MessageCode.TABLE_COLUMNS_TYPE: MessageDefinition(
        code=MessageCode.TABLE_COLUMNS_TYPE,
        summary="Table columns must be a list",
        template="The 'columns' value must be a list.",
    ),
    MessageCode.TABLE_COLUMN_ITEM_TYPE: MessageDefinition(
        code=MessageCode.TABLE_COLUMN_ITEM_TYPE,
        summary="Table column item must be a dictionary with header and cell",
        template="Each column item must be a dictionary with 'header' and 'cell' keys.",
    ),
    MessageCode.TABLE_COLUMN_HEADER_TYPE: MessageDefinition(
        code=MessageCode.TABLE_COLUMN_HEADER_TYPE,
        summary="Table column header must be plain text",
        template="A column 'header' must be plain text.",
    ),
    MessageCode.TABLE_COLUMN_CELL_TYPE: MessageDefinition(
        code=MessageCode.TABLE_COLUMN_CELL_TYPE,
        summary="Table column cell must be plain text",
        template="A column 'cell' must be plain text.",
    ),
    MessageCode.DATA_TYPE: MessageDefinition(
        code=MessageCode.DATA_TYPE,
        summary="Data block must be a dictionary or list when used with variable name",
        template="When 'data' is used with 'variable name', the data must be a dictionary or list (not a string).",
    ),
    MessageCode.DATA_VARIABLE_NAME_TYPE: MessageDefinition(
        code=MessageCode.DATA_VARIABLE_NAME_TYPE,
        summary="Variable name in data block must be plain text",
        template="A 'variable name' in a data block must be plain text.",
    ),
    MessageCode.DATA_USE_OBJECTS_TYPE: MessageDefinition(
        code=MessageCode.DATA_USE_OBJECTS_TYPE,
        summary="Use objects must be boolean or 'objects'",
        template="The 'use objects' modifier must be True, False, or 'objects'.",
    ),
    # List collect
    MessageCode.LIST_COLLECT_LABEL_HAS_MAKO: MessageDefinition(
        code=MessageCode.LIST_COLLECT_LABEL_HAS_MAKO,
        summary="field label contains Mako templating while list collect is active",
        template="Field label {label!r} contains Mako templating (${{...}}). "
        "Docassemble does not support Mako in field labels when 'list collect' is active.",
    ),
    # Packet 15: Markup
    MessageCode.MARKUP_BRACKET_EMPTY: MessageDefinition(
        code=MessageCode.MARKUP_BRACKET_EMPTY,
        summary="Empty bracket command",
        template="Markup command '{command}' has no content. Expected '[{command} ...]' with a value.",
    ),
    MessageCode.VISIBILITY_MODIFIER_CONFLICT: MessageDefinition(
        code=MessageCode.VISIBILITY_MODIFIER_CONFLICT,
        summary="visibility modifiers conflict in same field",
        template='"{key1}" cannot be combined with "{key2}" when both use the same syntax form.',
        experimental=False,
    ),
    MessageCode.VISIBILITY_JS_NON_JS_MIX: MessageDefinition(
        code=MessageCode.VISIBILITY_JS_NON_JS_MIX,
        summary="JavaScript and non-JavaScript visibility modifiers cannot be mixed",
        template='JavaScript and non-JavaScript visibility modifiers cannot be mixed (found "{key1}" and "{key2}").',
        experimental=False,
    ),
    MessageCode.PYTHON_BOOL_TYPE: MessageDefinition(
        code=MessageCode.PYTHON_BOOL_TYPE,
        summary="mandatory/scan for variables must be boolean or string",
        template="The value must be True, False, or a Python expression string, not {value_type}.",
    ),
}


def format_message(code: str, **kwargs: object) -> str:
    if code not in MESSAGE_DEFINITIONS:
        raise ValueError(f"Unknown message code: {code!r}")
    return MESSAGE_DEFINITIONS[code].template.format(**kwargs)


def is_experimental_code(code: str) -> bool:
    if code not in MESSAGE_DEFINITIONS:
        raise ValueError(f"Unknown message code: {code!r}")
    return MESSAGE_DEFINITIONS[code].experimental
