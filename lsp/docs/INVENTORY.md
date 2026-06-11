# Docassemble LSP – Baseline Key Inventory (Packet 1)

This document records the support status of Docassemble YAML key
families as of the Packet 1 baseline. The inventory is a snapshot, not
an authoritative spec; later packets will add, refine, or correct
individual entries.

## How to read this document

Each entry uses the following fields:

| Field | Meaning |
|---|---|
| **Completions** | `yes` = offered in the relevant scope; `no` = not offered; `partial` = offered but incomplete |
| **Hover** | `yes` = description text displayed; `no` = no hover text; `schema-only` = plain type info only |
| **Diagnostics** | `yes` = invalid forms are caught; `no` = not validated; `partial` = some shapes checked |
| **Quick fix** | `yes` = auto-fix available; `no` = none |
| **Drift-tested** | `yes` = covered by a test in `tests/test_inventory.py`; `no` = not yet covered |

Ground-truth sources (in priority order):
1. `docassemble/base/parse.py` `Question.__init__` and `parse_fields`
   (last verified: 1.7.7, `4847360`)
2. Official docassemble documentation (questions / fields / modifiers
   / features pages)
3. Local `validation.py` `all_dict_keys` and `types_of_blocks`



## Top-level keys

### Block-type discriminators (exclusive)

Keys that define what kind of block this is. Only one exclusive key
may appear per document block (validated via `types_of_blocks`).

| Key | Completions | Hover | Diagnostics | Quick fix | Drift-tested | Notes |
|---|---|---|---|---|---|---|
| `question` | yes | schema-only | yes | no | yes (baseline) | Exclusive; partners with `auto terms`, `terms`, `attachment`, `attachments` |
| `code` | yes | schema-only | yes | no | yes | Co-exists with `event` |
| `event` | yes | schema-only | yes | no | yes | |
| `include` | yes | schema-only | yes | no | yes | |
| `features` | yes | schema-only | yes | no | yes | |
| `objects` | yes | schema-only | yes | no | yes | |
| `objects from file` | yes | schema-only | yes | no | yes | `use objects` is a partner key |
| `sections` | yes | schema-only | yes | no | yes | |
| `imports` | yes | schema-only | yes | no | yes | |
| `template` | yes | schema-only | yes | no | yes | Partners `terms`; requires `content` or `content file` |
| `table` | yes | schema-only | yes | no | yes | |
| `review` | yes | schema-only | yes | no | yes | |
| `signature` | yes | schema-only | yes | no | yes | Enables `required` and `pen color` |
| `action` | yes | schema-only | yes | no | yes | |
| `response` | yes | schema-only | yes | no | yes | |
| `binaryresponse` | yes | schema-only | yes | no | yes | |
| `backgroundresponse` | yes | schema-only | yes | no | yes | |
| `all_variables` | yes | schema-only | yes | no | yes | |
| `response filename` | yes | schema-only | yes | no | yes | |
| `redirect url` | yes | schema-only | yes | no | yes | |
| `null response` | yes | schema-only | yes | no | yes | |
| `interview help` | yes | schema-only | yes | no | yes | |
| `attachment` | yes | schema-only | yes | no | yes | Partners `question` |
| `attachments` | yes | schema-only | yes | no | yes | Partners `question` |
| `attachment code` | yes | schema-only | yes | no | no | |
| `attachments code` | yes | schema-only | yes | no | no | |
| `auto terms` | yes | schema-only | yes | no | yes | Partners `question` |
| `terms` | yes | schema-only | yes | no | yes | Partners `question`, `template` |
| `order` | yes | schema-only | yes | no | yes | |

### Always-on modifiers (non-exclusive)

Keys that augment any block type.

| Key | Completions | Hover | Diagnostics | Quick fix | Drift-tested | Notes |
|---|---|---|---|---|---|---|
| `mandatory` | yes | schema-only | partial | no | yes | Accepted as eval expression |
| `initial` | yes | schema-only | partial | no | yes | |
| `id` | yes | schema-only | yes | no | yes | |
| `ga id` | yes | schema-only | no | no | no | Analytics |
| `segment id` | yes | schema-only | no | no | no | Analytics |
| `comment` | yes | schema-only | no | no | yes | Non-exclusive |
| `metadata` | yes | schema-only | no | no | yes | |
| `default screen parts` | yes | schema-only | yes | no | yes | |
| `default validation messages` | yes | schema-only | no | no | yes | |
| `default language` | yes | schema-only | no | no | yes | |
| `machine learning storage` | yes | schema-only | no | no | yes | |
| `modules` | yes | schema-only | no | no | yes | |
| `reset` | yes | schema-only | no | no | yes | |
| `on change` | yes | schema-only | partial | no | yes | |
| `images` | yes | schema-only | no | no | yes | |
| `image sets` | yes | schema-only | no | no | yes | |
| `reconsider` | yes | schema-only | no | no | yes | |
| `undefine` | yes | schema-only | no | no | yes | |
| `usedefs` | yes | schema-only | no | no | yes | |
| `depends on` | yes | schema-only | no | no | yes | |
| `allowed to set` | yes | schema-only | no | no | yes | |
| `scan for variables` | yes | schema-only | no | no | yes | |
| `only sets` | yes | schema-only | no | no | yes | |
| `sets` | yes | schema-only | no | no | yes | |
| `supersedes` | yes | schema-only | no | no | yes | |
| `default role` | yes | schema-only | no | no | yes | |
| `role` | yes | schema-only | no | no | yes | |
| `if` | yes | schema-only | no | no | yes | |
| `require` | yes | schema-only | no | no | yes | |
| `orelse` | no | no | no | no | no | Parser-known; not yet in completions — ambiguous |
| `need` | yes | schema-only | no | no | yes | |
| `validation code` | yes | schema-only | partial | no | yes | |
| `language` | yes | schema-only | no | no | yes | |
| `progress` | yes | schema-only | no | no | yes | |
| `section` | yes | schema-only | no | no | yes | |
| `mako` | yes | schema-only | no | no | yes | |
| `def` | yes | schema-only | no | no | yes | |
| `segment` | yes | schema-only | no | no | yes | |
| `sleep` | yes | schema-only | no | no | yes | |
| `reload` | yes | schema-only | no | no | yes | |
| `include_internal` | yes | schema-only | no | no | yes | |
| `check in` | yes | schema-only | no | no | yes | |
| `breadcrumb` | yes | schema-only | no | no | yes | |
| `tabular` | yes | schema-only | no | no | yes | |

### Question-face modifiers

Keys that control the rendered question screen.

| Key | Completions | Hover | Diagnostics | Quick fix | Drift-tested | Notes |
|---|---|---|---|---|---|---|
| `subquestion` | yes | schema-only | no | no | no | |
| `pre` | yes | schema-only | no | no | yes | |
| `post` | yes | schema-only | no | no | yes | |
| `under` | yes | schema-only | no | no | yes | |
| `right` | yes | schema-only | no | no | yes | |
| `help` | yes | schema-only | no | no | yes | |
| `audio` | yes | schema-only | no | no | yes | |
| `video` | yes | schema-only | no | no | yes | |
| `decoration` | yes | schema-only | no | no | yes | |
| `css` | yes | schema-only | no | no | no | |
| `css class` | yes | schema-only | no | no | no | |
| `table css class` | yes | schema-only | no | no | no | |
| `script` | yes | schema-only | no | no | no | |
| `continue button label` | yes | schema-only | no | no | no | |
| `continue button color` | yes | schema-only | no | no | no | |
| `resume button label` | yes | schema-only | no | no | no | |
| `resume button color` | yes | schema-only | no | no | no | |
| `back button label` | yes | schema-only | no | no | no | |
| `back button color` | yes | schema-only | no | no | no | Added to `all_dict_keys` in Packet 1 |
| `corner back button label` | yes | schema-only | no | no | no | |
| `back button` | yes | schema-only | no | no | no | |
| `prevent going back` | yes | schema-only | no | no | no | |
| `hide continue button` | yes | schema-only | no | no | no | |
| `disable continue button` | yes | schema-only | no | no | no | |
| `skip undefined` | yes | schema-only | no | no | no | |
| `progressive` | yes | schema-only | no | no | no | Only meaningful with `sections` |
| `auto open` | yes | schema-only | no | no | no | |
| `pen color` | yes | schema-only | yes (conditional) | no | no | Only valid with `signature`; caught by E301 guard |
| `required` | yes | schema-only | yes (conditional) | no | no | Only valid with `signature` |
| `show incomplete` | yes | schema-only | no | no | no | |
| `question metadata` | yes | schema-only | no | no | no | |
| `shuffle` | yes | schema-only | no | no | no | |
| `show if empty` | yes | schema-only | no | no | no | |
| `delete buttons` | yes | schema-only | no | no | no | |
| `read only` | yes | schema-only | no | no | no | |
| `edit header` | yes | schema-only | no | no | no | |
| `not available label` | yes | schema-only | no | no | no | |
| `allow reordering` | yes | schema-only | no | no | no | |
| `confirm` | yes | schema-only | no | no | no | |
| `always include editable files` | yes | schema-only | no | no | no | |
| `include attachment notice` | yes | schema-only | no | no | no | |
| `include download tab` | yes | schema-only | no | no | no | |
| `describe file types` | yes | schema-only | no | no | no | |
| `manual attachment list` | yes | schema-only | no | no | no | |
| `action buttons` | yes | schema-only | partial | no | no | |
| `gathered` | yes | schema-only | no | no | no | |
| `use objects` | yes | schema-only | no | no | no | |
| `allow emailing` | yes | schema-only | no | no | no | |
| `allow downloading` | yes | schema-only | no | no | no | |
| `email subject` | yes | schema-only | no | no | no | |
| `email body` | yes | schema-only | no | no | no | |
| `email template` | yes | schema-only | no | no | no | |
| `email address default` | yes | schema-only | no | no | no | |
| `zip filename` | yes | schema-only | no | no | no | |
| `content type` | yes | schema-only | no | no | no | |
| `indent` | yes | schema-only | no | no | no | |
| `target` | yes | schema-only | no | no | no | |
| `url` | yes | schema-only | no | no | no | |
| `data` | yes | schema-only | no | no | no | |
| `data from code` | yes | schema-only | no | no | no | |
| `variable name` | yes | schema-only | no | no | no | |
| `default` | yes | schema-only | no | no | no | |
| `datatype` | yes | schema-only | no | no | no | |
| `extras` | no | no | no | no | no | Parser-known; rarely used |
| `rows` (question-level) | yes | schema-only | no | no | no | Dual role: table `rows` + question layout |
| `columns` (question-level) | yes | schema-only | no | no | no | Table columns |
| `require gathered` | yes | schema-only | no | no | no | |
| `sort key` | yes | schema-only | no | no | no | Table only |
| `sort reverse` | yes | schema-only | no | no | no | Table only |
| `filter` | yes | schema-only | no | no | no | Table only |
| `edit` | yes | schema-only | no | no | no | Table only |
| `attachment options` | yes | schema-only | partial | no | no | |

### Keys intentionally not in completions

| Key | Reason |
|---|---|
| `orelse` | Parser-accepted but undocumented; no clear user-facing use |
| `extras` | Parser internal; not meaningful in hand-written interviews |



## Field item keys (`fields:` list entries)

All field item keys are centralized in
`src/docassemble_lsp/core/field_keys.py` and offered in the
`fields_item` completion scope. The
`test_field_item_known_keys_equals_subgroup_union` drift test guards
this list.

### Base / identity

| Key | Completions | Hover | Diagnostics | Quick fix | Notes |
|---|---|---|---|---|---|
| `field` | yes | schema-only | partial | no | Variable name |
| `label` | yes | schema-only | partial | no | Display label |
| `help` | yes | schema-only | no | no | Inline help text |
| `hint` | yes | schema-only | no | no | Placeholder text |
| `action` | yes | schema-only | no | no | Action name for action-type fields |
| `under` | yes | schema-only | no | no | Text below the field |
| `group` | yes | schema-only | no | no | Grouping label |

### Note / html

| Key | Completions | Hover | Diagnostics | Quick fix | Notes |
|---|---|---|---|---|---|
| `note` | yes | schema-only | partial | no | Narrative text block |
| `html` | yes | schema-only | partial | no | Raw HTML block |
| `raw html` | yes | schema-only | partial | no | Unescaped HTML |

### Choices / defaults

| Key | Completions | Hover | Diagnostics | Quick fix | Notes |
|---|---|---|---|---|---|
| `choices` | yes | schema-only | partial | no | Choice list or Python expression |
| `exclude` | yes | schema-only | no | no | Python expression to exclude items |
| `default` | yes | schema-only | no | no | Default value |
| `default value` | yes | schema-only | no | no | Alias for `default` |
| `address autocomplete` | yes | schema-only | partial | no | Google Places autocomplete |
| `all of the above` | yes | schema-only | no | no | Checkbox: check-all option |
| `none of the above` | yes | schema-only | no | no | Checkbox: uncheck-all option |
| `shuffle` | yes | schema-only | no | no | Randomize choice order |

### Conditions / visibility

| Key | Completions | Hover | Diagnostics | Quick fix | Notes |
|---|---|---|---|---|---|
| `show if` | yes | schema-only | partial | no | Python expression or object |
| `hide if` | yes | schema-only | partial | no | |
| `enable if` | yes | schema-only | partial | no | |
| `disable if` | yes | schema-only | partial | no | |
| `js show if` | yes | schema-only | partial | no | JavaScript expression |
| `js hide if` | yes | schema-only | partial | no | |
| `js enable if` | yes | schema-only | partial | no | |
| `js disable if` | yes | schema-only | partial | no | |
| `disabled` | yes | schema-only | no | no | Boolean: always disabled |
| `required` | yes | schema-only | partial | no | Boolean or Python expression |
| `read only` | yes | schema-only | no | no | |

### Layout

| Key | Completions | Hover | Diagnostics | Quick fix | Notes |
|---|---|---|---|---|---|
| `grid` | yes | schema-only | partial | no | Bootstrap grid settings object |
| `item grid` | yes | schema-only | partial | no | Grid for multi-item rows |
| `field metadata` | yes | schema-only | no | no | Arbitrary metadata object |
| `label above field` | yes | schema-only | no | no | |
| `floating label` | yes | schema-only | no | no | |
| `rows` | yes | schema-only | no | no | Textarea row count |
| `min` / `max` | yes | schema-only | no | no | Numeric bounds |
| `minlength` / `maxlength` | yes | schema-only | no | no | String length bounds |
| `step` | yes | schema-only | no | no | Range step |
| `scale` | yes | schema-only | no | no | Decimal scale |
| `inline` | yes | schema-only | no | no | Inline display |
| `inline width` | yes | schema-only | no | no | |
| `currency symbol` | yes | schema-only | no | no | |
| `css class` | yes | schema-only | no | no | |

### File upload

| Key | Completions | Hover | Diagnostics | Quick fix | Notes |
|---|---|---|---|---|---|
| `maximum image size` | yes | schema-only | no | no | |
| `image upload type` | yes | schema-only | no | no | |
| `accept` | yes | schema-only | no | no | MIME types |
| `allow privileges` | yes | schema-only | no | no | |
| `allow users` | yes | schema-only | no | no | |
| `persistent` | yes | schema-only | no | no | |
| `private` | yes | schema-only | no | no | |

### Special / validators

| Key | Completions | Hover | Diagnostics | Quick fix | Notes |
|---|---|---|---|---|---|
| `code` | yes | schema-only | partial | no | Field-level code expression |
| `validate` | yes | schema-only | no | no | Custom validation function |
| `validation code` | yes | schema-only | partial | no | Inline validation Python |
| `object labeler` | yes | schema-only | no | no | Function to label objects |
| `help generator` | yes | schema-only | no | no | Function to generate help text |
| `image generator` | yes | schema-only | no | no | Function to generate images |
| `disable others` | yes | schema-only | no | no | Boolean/list |
| `uncheck others` | yes | schema-only | no | no | |
| `check others` | yes | schema-only | no | no | |
| `validation messages` | yes | schema-only | partial | no | Nested dict of override messages |
| `trigger at` | yes | schema-only | no | no | Ajax trigger threshold (integer) |
| `datatype` | yes | schema-only | yes | yes (C103) | Full enum offered |
| `input type` | yes | schema-only | yes | yes (C103) | Subset enum offered |
| `object type` | yes | schema-only | no | no | |
| `file css class` | yes | schema-only | no | no | |

### ML (machine-learning fields) — added in Packet 1

| Key | Completions | Hover | Diagnostics | Quick fix | Notes |
|---|---|---|---|---|---|
| `using` | yes | schema-only | no | no | ML group specifier for `ml`/`mlarea` |
| `keep for training` | yes | schema-only | no | no | ML training flag |



## Ambiguous / deferred keys

These keys are known to the parser but their full semantic behavior is
deferred to later packets:

| Key | Location | Ambiguity |
|---|---|---|
| `orelse` | top-level | Parser-accepted alternative branch; not documented; usage unknown |
| `extras` | top-level | Parser accepts; used internally for metadata injection; not meant for authors |
| `object labeler` / `help generator` / `image generator` | field item | Callable expressions — need eval-context coverage |
| `data from code` | top-level | Accepted by parser but rarely used; full shape unknown |
| `gathered` (as field-item) | parser note | The `gathered` attribute on group/list objects is set by the parser, not a user-writeable field key |
| `process_selections_manual` choice item keys | parse_fields | `color`, `image`, `css class` on choice items inside `choices`/`buttons` — completions not yet offered at choice-item level |
| `using` / `keep for training` context restrictions | field item | Only valid for `datatype: ml` / `datatype: mlarea`; cross-key restriction not yet diagnosed |



## Drift tests

`tests/test_inventory.py` contains five tests that fail if the
centralized lists change unexpectedly:

| Test | What it guards |
|---|---|
| `test_field_item_known_keys_equals_subgroup_union` | `FIELD_ITEM_KNOWN_KEYS` == union of all declared sub-groups |
| `test_field_item_subgroups_have_no_duplicates` | no key appears in more than one sub-group |
| `test_ml_field_keys_included_in_known_keys` | `using` and `keep for training` are in the composite set |
| `test_top_level_completion_keys_are_valid_by_validation` | no top-level completion key would always produce E301 |
| `test_all_dict_keys_baseline_coverage` | common keys are not accidentally removed from `all_dict_keys` |
