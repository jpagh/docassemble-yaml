from __future__ import annotations

import re

from docassemble_lsp.core.completion_rules import CompletionScope
from docassemble_lsp.core.schema_models import CompletionCandidate


def _line_at(source: str, line: int) -> str:
    lines = source.splitlines()
    if not lines:
        return ""
    if line < 0:
        return ""
    if line >= len(lines):
        return lines[-1]
    return lines[line]


def _is_list_item_context(source: str, line: int) -> bool:
    return re.fullmatch(r"\s*-\s*(?:[\w/.-][\w /.-]*)?", _line_at(source, line)) is not None


def shorthand_candidates(scope: CompletionScope, source: str, line: int) -> list[CompletionCandidate]:
    line_text = _line_at(source, line)
    if not (_is_list_item_context(source, line) or re.fullmatch(r"\s*", line_text)):
        return []

    if scope == "action_button_item":
        return [
            CompletionCandidate(
                label="label/action",
                insert_text="label: ${1:Label}\naction: ${2:event_name}",
                documentation="Action button item that runs an interview action when clicked.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="label/action with arguments",
                insert_text="label: ${1:Label}\naction: ${2:event_name}\narguments:\n  ${3:key}: ${4:value}",
                documentation="Action button item that passes arguments to an interview action.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="label/link",
                insert_text="label: ${1:Label}\naction: ${2:https://example.com}",
                documentation="Action button item that opens an external URL instead of running an interview action.",
                is_snippet=True,
            ),
        ]

    if scope == "show_if_modifier":
        return [
            CompletionCandidate(
                label="variable/is",
                insert_text="variable: ${1:other_field}\nis: ${2:value}",
                documentation="Client-side conditional form that shows or hides a field based on another on-screen field.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="code",
                insert_text="code: |\n  ${1:condition}",
                documentation="Server-side conditional form that evaluates Python code when deciding whether a modifier applies.",
                is_snippet=True,
            ),
        ]

    if scope == "review_field_item":
        return [
            CompletionCandidate(
                label="follow up",
                insert_text="follow up:\n  - ${1:variable_name}",
                documentation="Review command that asks a follow-up variable after the main field is revisited.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="recompute",
                insert_text="recompute:\n  - ${1:variable_name}",
                documentation="Review command that recomputes a derived variable after editing answers.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="undefine",
                insert_text="undefine:\n  - ${1:variable_name}",
                documentation="Review command that undefines a variable before the user revisits answers.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="invalidate",
                insert_text="invalidate:\n  - ${1:variable_name}",
                documentation="Review command that invalidates a variable while preserving its previous value as a default.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="set",
                insert_text="set:\n  - ${1:variable_name}: ${2:value}",
                documentation="Review command that sets one or more variables after the user clicks the review item.",
                is_snippet=True,
            ),
        ]

    if scope == "help_block":
        return [
            CompletionCandidate(
                label="content",
                insert_text="content: |\n  ${1:Help text}",
                documentation="Question-specific help content shown in the help tab.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="label/content",
                insert_text="label: ${1:Help}\ncontent: |\n  ${2:Help text}",
                documentation="Question-specific help with a custom help-tab or button label.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="content/audio",
                insert_text="content: |\n  ${1:Help text}\naudio:\n  - ${2:help.mp3}",
                documentation="Question-specific help content with accompanying audio media.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="content/video",
                insert_text="content: |\n  ${1:Help text}\nvideo:\n  - ${2:help.mp4}",
                documentation="Question-specific help content with accompanying video media.",
                is_snippet=True,
            ),
        ]

    if scope == "interview_help_block":
        return [
            CompletionCandidate(
                label="heading/content",
                insert_text="heading: ${1:Help heading}\ncontent: |\n  ${2:Help text}",
                documentation="Interview-wide help section with a heading and content block.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="heading/content/audio",
                insert_text="heading: ${1:Help heading}\ncontent: |\n  ${2:Help text}\naudio:\n  - ${3:help.mp3}",
                documentation="Interview-wide help section with accompanying audio media.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="heading/content/video",
                insert_text="heading: ${1:Help heading}\ncontent: |\n  ${2:Help text}\nvideo:\n  - ${3:help.mp4}",
                documentation="Interview-wide help section with accompanying video media.",
                is_snippet=True,
            ),
        ]

    if scope == "address_autocomplete_block":
        return [
            CompletionCandidate(
                label="types/fields",
                insert_text="types:\n  - ${1:place_type}\nfields:\n  - ${2:place_field}",
                documentation="Structured address autocomplete options with the fixed docassemble keys `types` and `fields`.",
                is_snippet=True,
            ),
        ]

    if scope == "list_collect_block":
        return [
            CompletionCandidate(
                label="label/add another label",
                insert_text="label: ${1:Edit items}\nadd another label: ${2:Add another item}",
                documentation="List collect options that customize the edit label and the add-another prompt.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="enable/allow append/delete",
                insert_text="enable: ${1:true}\nallow append: ${2:true}\nallow delete: ${3:true}",
                documentation="List collect options that enable the control and allow adding or deleting collected items.",
                is_snippet=True,
            ),
        ]

    if scope == "attachment_options_block":
        return [
            CompletionCandidate(
                label="metadata",
                insert_text="metadata:\n  SingleSpacing: ${1:true}\n  fontsize: ${2:10pt}",
                documentation="Interview-wide attachment metadata defaults for generated documents.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="additional yaml/template files",
                insert_text="additional yaml:\n  - ${1:package:data/templates/format.yml}\ntemplate file: ${2:template.tex}\nrtf template file: ${3:template.rtf}",
                documentation="Interview-wide attachment defaults for Pandoc metadata and template files.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="docx reference file",
                insert_text="docx reference file: ${1:reference.docx}",
                documentation="Interview-wide DOCX reference file used when generating DOCX output from Markdown attachments.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="metadata/template/docx reference",
                insert_text="metadata:\n  SingleSpacing: ${1:true}\n  fontsize: ${2:10pt}\ntemplate file: ${3:template.tex}\ndocx reference file: ${4:reference.docx}",
                documentation="Interview-wide attachment defaults that combine document metadata with template and DOCX reference files.",
                is_snippet=True,
            ),
        ]

    if scope == "default_screen_parts_block":
        return [
            CompletionCandidate(
                label="pre/submit/post",
                insert_text="pre: |\n  ${1:Introductory text}\nsubmit: |\n  ${2:Prompt before moving forward}\npost: |\n  ${3:Footer text}",
                documentation="Default screen parts content shown before fields, above the continue button, and after the main question area.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="help/continue/back buttons",
                insert_text="help label: ${1:About}\nhelp button color: ${2:warning}\nback button label: ${3:Back}\nback button color: ${4:secondary}\ncontinue button label: ${5:Continue}\ncontinue button color: ${6:success}",
                documentation="Default screen-parts settings for help, back, and continue button labels and colors.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="under/subtitle",
                insert_text="subtitle: |\n  ${1:Interview subtitle}\nunder: |\n  ${2:Text shown under the screen}",
                documentation="Default subtitle and under-text shown across interview screens.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="css/footer classes",
                insert_text="footer: |\n  ${1:Footer text}\ncss class: ${2:normalquestion}\ntable css class: ${3:table}",
                documentation="Default screen-parts styling and footer content applied across the interview.",
                is_snippet=True,
            ),
        ]

    if scope == "metadata_block":
        return [
            CompletionCandidate(
                label="title/short title/subtitle",
                insert_text="title: ${1:Interview title}\nshort title: ${2:Short title}\nsubtitle: ${3:Subtitle}",
                documentation="Top-level metadata titles commonly used for interview listings and page presentation.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="documentation/example range",
                insert_text="documentation: ${1:https://docassemble.org/docs/}\nexample start: ${2:1}\nexample end: ${3:2}",
                documentation="Metadata fields used in docassemble examples to link documentation and mark the example block range.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="authors/social",
                insert_text="authors:\n  - name: ${1:Author name}\n    organization: ${2:Organization}\nsocial:\n  name: ${3:Interview title}\n  description: ${4:Short description}\n  image: ${5:preview.png}",
                documentation="Structured metadata starter that combines author attribution with social preview details.",
                is_snippet=True,
            ),
        ]

    if scope == "metadata_author_item":
        return [
            CompletionCandidate(
                label="name/organization",
                insert_text="name: ${1:Author name}\norganization: ${2:Organization}",
                documentation="Metadata author item with the documented author name and organization fields.",
                is_snippet=True,
            ),
        ]

    if scope == "metadata_social_block":
        return [
            CompletionCandidate(
                label="name/description/image",
                insert_text="name: ${1:Site name}\ndescription: ${2:Social description}\nimage: ${3:https://example.com/image.png}",
                documentation="Social metadata block with the common name, description, and image fields.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="twitter block",
                insert_text="twitter:\n  card: ${1:summary}\n  title: ${2:Card title}\n  site: ${3:@example}",
                documentation="Social metadata block that initializes the nested Twitter metadata object.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="og block",
                insert_text="og:\n  title: ${1:Page title}\n  url: ${2:https://example.com}\n  type: ${3:website}",
                documentation="Social metadata block that initializes the nested Open Graph metadata object.",
                is_snippet=True,
            ),
        ]

    if scope == "metadata_social_twitter_block":
        return [
            CompletionCandidate(
                label="card/title/site",
                insert_text="card: ${1:summary}\ntitle: ${2:Card title}\nsite: ${3:@example}",
                documentation="Twitter social metadata fields for the card type, title, and site handle.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="description/image",
                insert_text="description: ${1:Card description}\nimage: ${2:https://example.com/image.png}\nimage:alt: ${3:Image alt text}",
                documentation="Twitter social metadata fields for description and image presentation.",
                is_snippet=True,
            ),
        ]

    if scope == "metadata_social_og_block":
        return [
            CompletionCandidate(
                label="title/url/type",
                insert_text="title: ${1:Page title}\nurl: ${2:https://example.com}\ntype: ${3:website}",
                documentation="Open Graph metadata fields for title, canonical URL, and content type.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="site/locale/image",
                insert_text="site_name: ${1:Site name}\nlocale: ${2:en_US}\nimage: ${3:https://example.com/image.png}",
                documentation="Open Graph metadata fields for site name, locale, and preview image.",
                is_snippet=True,
            ),
        ]

    if scope == "attachment_metadata_block":
        return [
            CompletionCandidate(
                label="title/author/date",
                insert_text="title: ${1:Document title}\nauthor:\n  - ${2:Author name}\ndate: ${3:${ today() }}",
                documentation="Attachment metadata fields for document identity and authorship.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="spacing/fontsize/toc",
                insert_text="SingleSpacing: ${1:true}\nfontsize: ${2:10pt}\ntoc: ${3:true}",
                documentation="Attachment metadata fields for spacing, font size, and table-of-contents generation.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="header/footer",
                insert_text="HeaderLeft: ${1:Header text}\nFooterRight: ${2:Page [PAGENUM]}\nheader-includes:\n  - ${3:\\usepackage{setspace}}",
                documentation="Attachment metadata fields for header, footer, and Pandoc header includes.",
                is_snippet=True,
            ),
        ]

    if scope == "attachment_item":
        return [
            CompletionCandidate(
                label="name/filename/content",
                insert_text="name: ${1:Document name}\nfilename: ${2:document_name}\ndescription: |\n  ${3:Document description}\ncontent: |\n  ${4:Document content}",
                documentation="Attachment that generates a document from inline Markdown content.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="name/filename/docx template file",
                insert_text="name: ${1:Document name}\nfilename: ${2:document_name}\ndocx template file: ${3:template.docx}\nfields:\n  ${4:template_field}: ${5:value}",
                documentation="Attachment that assembles a DOCX template and maps one or more template fields.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="name/filename/pdf template file",
                insert_text="name: ${1:Document name}\nfilename: ${2:document_name}\npdf template file: ${3:template.pdf}\nfields:\n  ${4:Template Field}: ${5:value}",
                documentation="Attachment that fills a PDF template using field mappings.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="name/filename/valid formats/content",
                insert_text="name: ${1:Document name}\nfilename: ${2:document_name}\nvalid formats:\n  - ${3:pdf}\ndescription: |\n  ${4:Document description}\ncontent: |\n  ${5:Document content}",
                documentation="Attachment that limits output to specific download formats.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="filename/variable name/content",
                insert_text="filename: ${1:document_name}\nvariable name: ${2:document_file}\ncontent: |\n  ${3:Document content}",
                documentation="Attachment that assembles a document and stores it in a variable for later reuse.",
                is_snippet=True,
            ),
        ]

    if scope == "image_set_block":
        return [
            CompletionCandidate(
                label="attribution/images",
                insert_text="attribution: |\n  ${1:Image attribution}\nimages:\n  ${2:icon_name}: ${3:icon.svg}",
                documentation="Image-set object with attribution text and one or more named image mappings.",
                is_snippet=True,
            ),
        ]

    if scope == "validation_messages_block":
        return [
            CompletionCandidate(
                label="required/max",
                insert_text="required: |\n  ${1:Please provide a value.}\nmax: |\n  ${2:No more than %s, please!}",
                documentation="Common validation-message overrides for required and max errors.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="date min/max",
                insert_text="date min: |\n  ${1:Enter a date on or after %s.}\ndate max: |\n  ${2:Enter a date on or before %s.}",
                documentation="Validation-message overrides for date range errors.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="checkboxes required/checkatleast",
                insert_text="checkboxes required: |\n  ${1:Select at least one option.}\ncheckatleast: |\n  ${2:Select at least %s options.}",
                documentation="Validation-message overrides for checkbox selection requirements.",
                is_snippet=True,
            ),
        ]

    if scope == "segment_block":
        return [
            CompletionCandidate(
                label="id/arguments",
                insert_text="id: ${1:segment_id}\narguments:\n  ${2:key}: ${3:value}",
                documentation="Segment analytics payload with a segment ID and optional arguments object.",
                is_snippet=True,
            )
        ]

    if scope == "grid_block":
        return [
            CompletionCandidate(
                label="width",
                insert_text="width: ${1:6}",
                documentation="Grid object that sets only the field width.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="width/label width",
                insert_text="width: ${1:6}\nlabel width: ${2:3}",
                documentation="Grid object that sets both field width and label width.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="width/breakpoint",
                insert_text="width: ${1:6}\nbreakpoint: ${2:sm}",
                documentation="Grid object that sets a field width and responsive breakpoint.",
                is_snippet=True,
            ),
        ]

    if scope == "item_grid_block":
        return [
            CompletionCandidate(
                label="width/breakpoint",
                insert_text="width: ${1:3}\nbreakpoint: ${2:sm}",
                documentation="Item-grid object that controls how radio or checkbox items are laid out responsively.",
                is_snippet=True,
            )
        ]

    if scope == "need_item":
        return [
            CompletionCandidate(
                label="pre",
                insert_text="pre:\n  - ${1:variable_name}",
                documentation="Variables that must be defined before the block is used.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="post",
                insert_text="post:\n  - ${1:variable_name}",
                documentation="Variables that must be defined after the block is used.",
                is_snippet=True,
            ),
        ]

    if scope == "attachment_fields_block":
        return [
            CompletionCandidate(
                label="template_field: value",
                insert_text="${1:template_field}: ${2:value}",
                documentation="Map a DOCX or PDF template field name to a user-defined value or expression.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="template_field list",
                insert_text="${1:template_field}:\n  - ${2:item}",
                documentation="Map a template field name to a list value for DOCX template rendering.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="template_field object",
                insert_text="${1:template_field}:\n  ${2:key}: ${3:value}",
                documentation="Map a template field name to a nested object for DOCX template rendering.",
                is_snippet=True,
            ),
        ]

    if scope == "attachment_field_variable_item":
        return [
            CompletionCandidate(
                label="variable_name",
                insert_text="${1:variable_name}",
                documentation="Variable name to expose to a DOCX or PDF template through field variables.",
                is_snippet=True,
            )
        ]

    if scope == "objects_item":
        return [
            CompletionCandidate(
                label="name: Class",
                insert_text="${1:person}: ${2:Individual}",
                documentation="Objects block item that maps a variable name to a docassemble object class.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="name.attribute: Class",
                insert_text="${1:user}.${2:case}: ${3:Case}",
                documentation="Objects block item that initializes an attribute as an object.",
                is_snippet=True,
            ),
        ]

    if scope == "objects_from_file_item":
        return [
            CompletionCandidate(
                label="name: source.yml",
                insert_text="${1:claims}: ${2:claim_list.yml}",
                documentation="Objects from file item that maps a variable name to a YAML or JSON source file.",
                is_snippet=True,
            )
        ]

    if scope == "include_item":
        return [
            CompletionCandidate(
                label="questions.yml",
                insert_text="${1:questions.yml}",
                documentation="Include a questions file from the current package.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="package:questions.yml",
                insert_text="${1:docassemble.package}:${2:questions.yml}",
                documentation="Include a questions file from another package.",
                is_snippet=True,
            ),
        ]

    if scope == "imports_item":
        return [
            CompletionCandidate(
                label="module_name",
                insert_text="${1:datetime}",
                documentation="Import a Python module into the interview namespace.",
                is_snippet=True,
            )
        ]

    if scope == "modules_item":
        return [
            CompletionCandidate(
                label="module_name",
                insert_text="${1:datetime}",
                documentation="Import exported names from a Python module.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label=".relative_module",
                insert_text=".${1:utils}",
                documentation="Import exported names from a module in the current package.",
                is_snippet=True,
            ),
        ]

    if scope == "translations_item":
        return [
            CompletionCandidate(
                label="translation.xlsx",
                insert_text="${1:translations.xlsx}",
                documentation="Reference an XLSX or XLIFF translation file from the sources folder.",
                is_snippet=True,
            )
        ]

    if scope == "reset_item":
        return [
            CompletionCandidate(
                label="variable_name",
                insert_text="${1:variable_name}",
                documentation="Variable that should be undefined each time a new screen loads.",
                is_snippet=True,
            )
        ]

    if scope == "order_item":
        return [
            CompletionCandidate(
                label="block_id",
                insert_text="${1:block_id}",
                documentation="ID of a question or code block used in an order block.",
                is_snippet=True,
            )
        ]

    if scope == "sections_item":
        return [
            CompletionCandidate(
                label="Section title",
                insert_text="${1:Section title}",
                documentation="Simple section heading item for a sections block.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="keyword: title",
                insert_text="${1:section_keyword}: ${2:Section title}",
                documentation="Keyword/title pair for sections blocks that use stable internal section names.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="keyword with subsections",
                insert_text="${1:section_keyword}: ${2:Section title}\n  subsections:\n    - ${3:Subsection title}",
                documentation="Keyword-based section definition with a subsection list.",
                is_snippet=True,
            ),
        ]

    if scope == "table_column_item":
        return [
            CompletionCandidate(
                label="Header: expression",
                insert_text="${1:Header}: ${2:row_item.value}",
                documentation="Shorthand column item mapping a header to a Python expression.",
                is_snippet=True,
            ),
            CompletionCandidate(
                label="header/cell",
                insert_text="header: ${1:Header}\ncell: ${2:row_item.value}",
                documentation="Explicit header/cell form for a table column definition.",
                is_snippet=True,
            ),
        ]

    if scope == "on_change_item":
        return [
            CompletionCandidate(
                label="variable: code",
                insert_text="${1:variable_name}: |\n  ${2:invalidate(target_variable)}",
                documentation="On change entry mapping a variable name to Python code that runs when the variable changes.",
                is_snippet=True,
            )
        ]

    if scope == "fields_item":
        return [
            CompletionCandidate(
                label="label: value",
                insert_text="${1:label}: ${2:value}",
                documentation="Parser-valid shorthand for a label/value pair item in choices-style lists.",
                is_snippet=True,
                display_kind="property",
            )
        ]

    if scope == "review_item":
        return [
            CompletionCandidate(
                label="label: value",
                insert_text="${1:label}: ${2:value}",
                documentation="Parser-valid shorthand for a label/value pair item in review lists.",
                is_snippet=True,
                display_kind="property",
            )
        ]

    return []
