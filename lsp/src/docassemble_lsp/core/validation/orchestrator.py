"""Validation orchestrator — the main entry points for document validation.

``find_errors`` and ``find_errors_from_string`` are the public API.
"""

from __future__ import annotations

import dataclasses
import logging
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Optional

from ruamel.yaml.constructor import DuplicateKeyError
from ruamel.yaml.error import MarkedYAMLError

from docassemble_lsp.core.accessibility import find_accessibility_findings
from docassemble_lsp.core.files import templates_dir_for_path
from docassemble_lsp.core.jinja import (
    contains_jinja_syntax,
    has_jinja_header,
    preprocess_jinja,
)
from docassemble_lsp.core.line_helpers import (
    _is_internal_metadata_key,
    _lc_key_line,
    _relative_value_line,
)
from docassemble_lsp.core.messages import MessageCode, is_experimental_code
from docassemble_lsp.core.python_paths import path_from_uri_or_path
from docassemble_lsp.core.validation.blocks import (
    _absolute_document_line,
    _allowed_top_level_keys,
    _detect_file_wide_tagged_pdf,
    _extract_yaml_parse_problem_line,
    _find_unmatched_interview_order_references,
    _format_missing_jinja_header_error,
    _format_yaml_parse_error,
    _lowercase_key_map,
    _make_yaml_parser,
    _map_rendered_lines_to_source_lines,
    _relative_top_level_error_line,
    _rewrite_yaml_parse_error_lines,
    _with_line_metadata,
    _yaml_error,
    big_dict,
    types_of_blocks,
)
from docassemble_lsp.core.validation.fields import (
    _contains_mako_syntax,
    _normalize_validator_error,
)
from docassemble_lsp.core.validation.table import validate_table_block_in_doc
from docassemble_lsp.core.validation_config import RuntimeOptions, YAMLError
from docassemble_lsp.core.workspace import WorkspaceIndex
from docassemble_lsp.core.yaml_parsing import (
    DOCUMENT_MATCH,
    normalize_yaml_document_for_parser,
)
from docassemble_lsp.core.yaml_shared import (
    _ATTACHMENT_FILE_KEYS,
    _BLOCK_SCALAR_MARKERS,
    _EVENT_REFERENCE_KEYS,
    _FILE_REFERENCE_KEYS,
    _FILE_REFERENCE_LIST_PARENTS,
    _KEY_VALUE_RE,
    _LIST_ITEM_VALUE_RE,
    _PYTHON_BLOCK_KEYS,
    _PYTHON_MODULE_REFERENCE_KEYS,
    _clean_value_and_range,
    _document_lines,
    _iter_mako_block_regions,
    _precompute_parent_keys,
)

logger = logging.getLogger(__name__)
_RuamelDuplicateKeyError = DuplicateKeyError
_RuamelMarkedYAMLError = MarkedYAMLError


def _validate_cross_document(
    full_content: str,
    current_path: Path,
    input_file: str | None,
    workspace_index: WorkspaceIndex,
) -> list[YAMLError]:
    from docassemble_lsp.core.definitions import (
        _event_helper_occurrences,
        _iter_block_scalar_regions,
    )
    from docassemble_lsp.core.python_modules import resolve_python_module_path
    from docassemble_lsp.core.python_paths import (
        docassemble_package_name,
        normalize_module_name,
    )

    def _module_path(value: str) -> Path | None:
        try:
            mname = normalize_module_name(value, current_path)
            if mname is not None:
                return resolve_python_module_path(mname, current_path, workspace_index)
        except Exception:
            logger.exception("Failed to resolve module path for %r", value)
        return None

    errors: list[YAMLError] = []
    lines = _document_lines(full_content)
    templates_dir = workspace_index.templates_dir_for(current_path)
    if templates_dir is None:
        templates_dir = templates_dir_for_path(current_path)
    parents = _precompute_parent_keys(full_content)
    own_package = docassemble_package_name(current_path) if current_path is not None else None

    for line_index, text in enumerate(lines):
        key_match = _KEY_VALUE_RE.match(text)
        if key_match is not None:
            key_name = key_match.group(2).strip()
            raw_value = key_match.group(3)
            value, _, _ = _clean_value_and_range(raw_value, key_match.start(3), key_match.end(3))
            if not value or ":" in value or value in _BLOCK_SCALAR_MARKERS:
                continue

            if key_name in _EVENT_REFERENCE_KEYS:
                if not _contains_mako_syntax(value) and value not in workspace_index.all_event_names:
                    errors.append(
                        _yaml_error(
                            code=MessageCode.CROSS_DOC_UNDEFINED_EVENT,
                            line_number=line_index + 1,
                            file_name=input_file or str(current_path),
                            name=value,
                        )
                    )
                continue

            if key_name == "usedefs":
                if value not in workspace_index.all_def_names:
                    errors.append(
                        _yaml_error(
                            code=MessageCode.CROSS_DOC_UNDEFINED_DEF,
                            line_number=line_index + 1,
                            file_name=input_file or str(current_path),
                            name=value,
                        )
                    )
                continue

            if key_name in _PYTHON_MODULE_REFERENCE_KEYS:
                if own_package is not None:
                    mname = normalize_module_name(value, current_path)
                    if mname is not None and not mname.startswith(f"{own_package}.") and mname != own_package:
                        continue
                if _module_path(value) is None:
                    errors.append(
                        _yaml_error(
                            code=MessageCode.CROSS_DOC_MISSING_FILE,
                            line_number=line_index + 1,
                            file_name=input_file or str(current_path),
                            path=value,
                        )
                    )
                continue

            if key_name in _FILE_REFERENCE_KEYS or key_name in _FILE_REFERENCE_LIST_PARENTS:
                if key_name == "translations":
                    continue
                if ":" not in value:
                    resolved = (current_path.parent / value).resolve()
                    if not resolved.exists() and key_name in _ATTACHMENT_FILE_KEYS and templates_dir is not None:
                        resolved = (templates_dir / value).resolve()
                    if not resolved.exists():
                        code = (
                            MessageCode.CROSS_DOC_MISSING_TEMPLATE
                            if key_name in _ATTACHMENT_FILE_KEYS
                            else MessageCode.CROSS_DOC_MISSING_FILE
                        )
                        errors.append(
                            _yaml_error(
                                code=code,
                                line_number=line_index + 1,
                                file_name=input_file or str(current_path),
                                path=value,
                            )
                        )
                continue

        list_match = _LIST_ITEM_VALUE_RE.match(text)
        if list_match is not None:
            raw_value = list_match.group(2)
            value, _, _ = _clean_value_and_range(raw_value, list_match.start(2), list_match.end(2))
            if not value or ":" in value:
                continue
            parent = parents[line_index]

            if parent == "usedefs":
                if value not in workspace_index.all_def_names:
                    errors.append(
                        _yaml_error(
                            code=MessageCode.CROSS_DOC_UNDEFINED_DEF,
                            line_number=line_index + 1,
                            file_name=input_file or str(current_path),
                            name=value,
                        )
                    )
                continue

            if parent in _EVENT_REFERENCE_KEYS:
                if not _contains_mako_syntax(value) and value not in workspace_index.all_event_names:
                    errors.append(
                        _yaml_error(
                            code=MessageCode.CROSS_DOC_UNDEFINED_EVENT,
                            line_number=line_index + 1,
                            file_name=input_file or str(current_path),
                            name=value,
                        )
                    )
                continue

            if parent in _PYTHON_MODULE_REFERENCE_KEYS:
                if own_package is not None:
                    mname = normalize_module_name(value, current_path)
                    if mname is not None and not mname.startswith(f"{own_package}.") and mname != own_package:
                        continue
                if _module_path(value) is None:
                    errors.append(
                        _yaml_error(
                            code=MessageCode.CROSS_DOC_MISSING_FILE,
                            line_number=line_index + 1,
                            file_name=input_file or str(current_path),
                            path=value,
                        )
                    )
                continue

            if parent in _FILE_REFERENCE_LIST_PARENTS or parent in _ATTACHMENT_FILE_KEYS:
                if parent == "translations":
                    continue
                resolved = (current_path.parent / value).resolve()
                if not resolved.exists() and parent in _ATTACHMENT_FILE_KEYS and templates_dir is not None:
                    resolved = (templates_dir / value).resolve()
                if not resolved.exists():
                    code = (
                        MessageCode.CROSS_DOC_MISSING_TEMPLATE
                        if parent in _ATTACHMENT_FILE_KEYS
                        else MessageCode.CROSS_DOC_MISSING_FILE
                    )
                    errors.append(
                        _yaml_error(
                            code=code,
                            line_number=line_index + 1,
                            file_name=input_file or str(current_path),
                            path=value,
                        )
                    )
                continue

    for region in _iter_block_scalar_regions(full_content):
        if region.key_name not in _PYTHON_BLOCK_KEYS:
            continue
        for occurrence in _event_helper_occurrences(region.text):
            if occurrence.name not in workspace_index.all_event_names:
                errors.append(
                    _yaml_error(
                        code=MessageCode.CROSS_DOC_UNDEFINED_EVENT,
                        line_number=region.content_start_line + occurrence.line + 1,
                        file_name=input_file or str(current_path),
                        name=occurrence.name,
                    )
                )

    for mako_region in _iter_mako_block_regions(full_content):
        if mako_region.is_expression:
            continue
        for occurrence in _event_helper_occurrences(mako_region.code_text):
            if occurrence.name not in workspace_index.all_event_names:
                content_before = full_content[: mako_region.content_start_offset]
                base_line = content_before.count("\n")
                errors.append(
                    _yaml_error(
                        code=MessageCode.CROSS_DOC_UNDEFINED_EVENT,
                        line_number=base_line + occurrence.line + 1,
                        file_name=input_file or str(current_path),
                        name=occurrence.name,
                    )
                )

    return errors


def find_errors_from_string(
    full_content: str,
    input_file: Optional[str] = None,
    runtime_options: Optional[RuntimeOptions] = None,
    _jinja_affected_sections: frozenset[int] | None = None,
    workspace_index: Optional[WorkspaceIndex] = None,
) -> list[YAMLError]:
    """Return list of YAMLError found in the given full_content string.

    Args:
        full_content: Full YAML content as a string.
        _jinja_affected_sections: Internal — set of YAML document section
            indices (0-based) whose original source contained Jinja2 syntax.
            Type validators are skipped for those sections because rendered
            types may not reflect runtime values. Passed through from the
            ``# use jinja`` preprocessing branch.

    Returns:
        list[YAMLError]: List of YAMLError instances found in the content.
    """
    all_errors: list[YAMLError] = []
    runtime_options = runtime_options or RuntimeOptions()

    if not input_file:
        input_file = "<string input>"

    if has_jinja_header(full_content):
        rendered, render_errors = preprocess_jinja(full_content, input_file=input_file)
        if render_errors:
            return [
                _yaml_error(
                    code=e.code,
                    line_number=e.line_number,
                    file_name=input_file,
                    err_str=e.message,
                )
                for e in render_errors
            ]
        _, _sep, original_body = full_content.partition("\n")
        _, _sep, rendered_body = rendered.partition("\n")
        original_sections = DOCUMENT_MATCH.split(original_body)
        jinja_affected: set[int] = set()
        for idx, section in enumerate(original_sections):
            if contains_jinja_syntax(section):
                jinja_affected.add(idx + 1)
        errors = find_errors_from_string(
            rendered_body,
            input_file=input_file,
            runtime_options=runtime_options,
            _jinja_affected_sections=frozenset(jinja_affected),
        )
        rendered_line_map = _map_rendered_lines_to_source_lines(
            original_body,
            rendered_body,
            source_start_line=2,
        )
        for err in errors:
            if err.code == MessageCode.YAML_PARSE_ERROR:
                problem_line = _extract_yaml_parse_problem_line(err.err_str)
                if problem_line is not None:
                    mapped_problem_line = rendered_line_map.get(problem_line, problem_line + 1)
                    err.line_number = mapped_problem_line
                    err.err_str = _rewrite_yaml_parse_error_lines(
                        err.err_str,
                        old_line=problem_line,
                        new_line=mapped_problem_line,
                    )
                    continue
            err.line_number = rendered_line_map.get(err.line_number, err.line_number + 1)
        return [error for error in errors if runtime_options.allows_code(error.code)]

    exclusive_keys = [key for key in types_of_blocks.keys() if types_of_blocks[key].get("exclusive", True)]
    yaml_parser = _make_yaml_parser()
    prior_conditional_fields: list[dict[str, Any]] = []
    line_number = 1
    section_index = 0

    file_wide_tagged_pdf = _detect_file_wide_tagged_pdf(full_content)
    accessibility_opts = dataclasses.replace(
        runtime_options.accessibility_options(),
        file_wide_tagged_pdf_enabled=file_wide_tagged_pdf,
    )
    for source_code in DOCUMENT_MATCH.split(full_content):
        section_index += 1
        lines_in_code = sum(source_line == "\n" for source_line in source_code)
        source_code = normalize_yaml_document_for_parser(source_code)
        try:
            doc = _with_line_metadata(yaml_parser.load(source_code))
        except Exception as errMess:
            if isinstance(errMess, DuplicateKeyError):
                key_match = re.match(r'found duplicate key "([^"]+)"', errMess.problem or "")
                key_name = key_match.group(1) if key_match else "unknown"
                dup_line = line_number
                if errMess.problem_mark is not None:
                    dup_line = line_number + errMess.problem_mark.line
                all_errors.append(
                    _yaml_error(
                        code=MessageCode.YAML_DUPLICATE_KEY,
                        line_number=dup_line,
                        file_name=input_file,
                        key_name=key_name,
                    )
                )
            elif isinstance(errMess, MarkedYAMLError):
                if errMess.context_mark is not None:
                    errMess.context_mark.line += line_number - 1
                if errMess.problem_mark is not None:
                    errMess.problem_mark.line += line_number - 1
                local_problem_line = 1
                if errMess.context_mark is not None:
                    local_problem_line = errMess.context_mark.line - line_number + 2
                elif errMess.problem_mark is not None:
                    local_problem_line = errMess.problem_mark.line - line_number + 2
                problem_line = line_number
                if errMess.context_mark is not None:
                    problem_line = errMess.context_mark.line + 1
                elif errMess.problem_mark is not None:
                    problem_line = errMess.problem_mark.line + 1
                err_str = _format_missing_jinja_header_error(source_code, line_number=local_problem_line)
                if err_str is None:
                    err_str = _format_yaml_parse_error(errMess)
                all_errors.append(
                    _yaml_error(
                        code=MessageCode.YAML_PARSE_ERROR,
                        line_number=problem_line,
                        file_name=input_file,
                        err_str=err_str,
                    )
                )
            else:
                all_errors.append(
                    _yaml_error(
                        code=MessageCode.YAML_PARSE_ERROR,
                        line_number=line_number,
                        file_name=input_file,
                        error=str(errMess),
                    )
                )
            line_number += lines_in_code
            continue

        if doc is None:
            line_number += lines_in_code
            continue
        if not isinstance(doc, dict):
            line_number += lines_in_code
            continue

        accessibility_findings = find_accessibility_findings(
            doc=doc,
            source_code=source_code,
            document_start_line=line_number,
            input_file=input_file,
            options=accessibility_opts,
        )
        for finding in accessibility_findings:
            all_errors.append(
                YAMLError(
                    err_str=finding.message,
                    line_number=finding.line_number,
                    file_name=input_file,
                    experimental=is_experimental_code(finding.code),
                    code=finding.code,
                )
            )

        doc_keys_lower = _lowercase_key_map(doc)
        non_meta_keys_lower = {
            key.lower() for key in doc.keys() if isinstance(key, str) and not _is_internal_metadata_key(key)
        }
        if non_meta_keys_lower == {"comment"}:
            pass
        else:
            any_types = [block for block in types_of_blocks.keys() if block in doc_keys_lower and block != "comment"]
            if len(any_types) == 0:
                all_errors.append(
                    _yaml_error(
                        code=MessageCode.NO_POSSIBLE_TYPES,
                        line_number=line_number,
                        file_name=input_file,
                        document=doc,
                    )
                )
        posb_types = [block for block in exclusive_keys if block in doc_keys_lower]
        if len(posb_types) > 1:
            if len(posb_types) == 2 and posb_types[1] in (types_of_blocks[posb_types[0]].get("partners") or []):
                pass
            else:
                all_errors.append(
                    _yaml_error(
                        code=MessageCode.TOO_MANY_TYPES,
                        line_number=line_number,
                        file_name=input_file,
                        possible_types=posb_types,
                    )
                )

        allowed_top_level_keys = _allowed_top_level_keys(doc_keys_lower)
        weird_keys = []
        for attr in doc.keys():
            if _is_internal_metadata_key(attr):
                continue
            if not isinstance(attr, str):
                weird_keys.append(str(attr))
            elif attr.lower() not in allowed_top_level_keys:
                weird_keys.append(attr)
        if len(weird_keys) > 0:
            all_errors.append(
                _yaml_error(
                    code=MessageCode.UNKNOWN_KEYS,
                    line_number=line_number,
                    file_name=input_file,
                    keys=weird_keys,
                )
            )
        if "on change" in doc_keys_lower and len(non_meta_keys_lower) > 1:
            all_errors.append(
                _yaml_error(
                    code=MessageCode.ON_CHANGE_EXTRA_KEYS,
                    line_number=_absolute_document_line(line_number, _lc_key_line(doc, doc_keys_lower["on change"])),
                    file_name=input_file,
                )
            )
        if "require" in doc_keys_lower:
            require_key = doc_keys_lower["require"]
            require_value = doc.get(require_key)
            if isinstance(require_value, list):
                if "orelse" not in doc_keys_lower:
                    all_errors.append(
                        _yaml_error(
                            code=MessageCode.REQUIRE_ORELSE_MISSING,
                            line_number=_absolute_document_line(line_number, _lc_key_line(doc, require_key)),
                            file_name=input_file,
                        )
                    )
                else:
                    orelse_key = doc_keys_lower["orelse"]
                    if not isinstance(doc.get(orelse_key), Mapping):
                        all_errors.append(
                            _yaml_error(
                                code=MessageCode.REQUIRE_ORELSE_TYPE,
                                line_number=_absolute_document_line(line_number, _lc_key_line(doc, orelse_key)),
                                file_name=input_file,
                            )
                        )
        all_errors.extend(validate_table_block_in_doc(doc, doc_keys_lower, line_number, input_file))

        has_def = "def" in doc_keys_lower
        has_mako = "mako" in doc_keys_lower
        if (has_def or has_mako) and not (has_def and has_mako):
            present_key = "def" if has_def else "mako"
            missing_key = "mako" if has_def else "def"
            all_errors.append(
                _yaml_error(
                    code=MessageCode.DEF_MAKO_REQUIRED,
                    line_number=_absolute_document_line(line_number, _lc_key_line(doc, doc_keys_lower[present_key])),
                    file_name=input_file,
                    missing_key=missing_key,
                )
            )

        from docassemble_lsp.core.validation.data import validate_data_block

        all_errors.extend(validate_data_block(doc_keys_lower, doc, line_number, input_file))

        from docassemble_lsp.core.validation.list_collect import validate_list_collect_mako_labels

        all_errors.extend(validate_list_collect_mako_labels(doc_keys_lower, doc, line_number, input_file))

        _run_type_validators = _jinja_affected_sections is None or section_index not in _jinja_affected_sections
        if _run_type_validators:
            for key in doc.keys():
                if not isinstance(key, str) or _is_internal_metadata_key(key):
                    continue
                lower_key = key.lower()
                if lower_key in big_dict and "type" in big_dict[lower_key]:
                    if lower_key == "fields":
                        test = big_dict[lower_key]["type"](doc[key], runtime_options=runtime_options)
                    else:
                        test = big_dict[lower_key]["type"](doc[key])
                    for err in test.errors:
                        err_msg, err_line, err_code = _normalize_validator_error(err)
                        mapped_line = _absolute_document_line(
                            line_number,
                            _relative_top_level_error_line(doc, key, err_line, err_code, source_code=source_code),
                        )
                        all_errors.append(
                            _yaml_error(
                                code=err_code,
                                err_str=err_msg,
                                line_number=mapped_line,
                                file_name=input_file,
                            )
                        )

        unmatched_refs = _find_unmatched_interview_order_references(doc, prior_conditional_fields)
        for field_var, ref_line in unmatched_refs:
            all_errors.append(
                _yaml_error(
                    code=MessageCode.INTERVIEW_ORDER_UNMATCHED_GUARD,
                    line_number=_absolute_document_line(line_number, _relative_value_line(doc, "code", ref_line)),
                    file_name=input_file,
                    field_var=field_var,
                )
            )

        from docassemble_lsp.core.validation.visibility import validate_nesting_depth

        all_errors.extend(validate_nesting_depth(doc, line_number, input_file))

        from docassemble_lsp.core.validation.visibility import collect_conditional_fields

        prior_conditional_fields.extend(collect_conditional_fields(doc, line_number))

        line_number += lines_in_code

    if workspace_index is not None and input_file not in ("<memory>", "<string input>"):
        current_path = path_from_uri_or_path(input_file)
        if current_path and current_path.suffix in (".yml", ".yaml"):
            all_errors.extend(_validate_cross_document(full_content, current_path, input_file, workspace_index))

    return [error for error in all_errors if runtime_options.allows_code(error.code)]


def find_errors(
    input_file: str,
    runtime_options: Optional[RuntimeOptions] = None,
) -> list[YAMLError]:
    """Return list of YAMLError found in the given input_file."""
    with open(input_file, "r", encoding="utf-8") as f:
        full_content = f.read()

    return find_errors_from_string(
        full_content,
        input_file=input_file,
        runtime_options=runtime_options,
    )
