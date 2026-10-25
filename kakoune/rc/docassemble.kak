# Docassemble filetype detection; shared policy cases: fixtures/detection/.
# Source after giallo-kak init with giallo_auto_enable=false (see ../README.md).
try %{ declare-option -hidden bool docassemble_active false }
try %{ declare-option -hidden bool docassemble_disabled false }
try %{ declare-option -hidden bool docassemble_automatic false }
try %{ declare-option -hidden str docassemble_previous_filetype yaml }
try %{ declare-option -hidden int docassemble_previous_indentwidth 4 }
try %{ declare-option -hidden int docassemble_previous_tabstop 8 }
try %{ declare-option -hidden str docassemble_previous_comment_line }
try %{ declare-option -hidden str docassemble_previous_comment_block_begin }
try %{ declare-option -hidden str docassemble_previous_comment_block_end }
try %{ declare-option -hidden str docassemble_previous_giallo_lang }
try %{ declare-option -hidden bool docassemble_previous_giallo_enabled false }
# Also usable with kak -n, without the standard comment module.
try %{ declare-option str comment_line '#' }
try %{ declare-option str comment_block_begin }
try %{ declare-option str comment_block_end }

define-command -override -hidden docassemble-activate %{
    evaluate-commands %sh{
        [ "$kak_opt_docassemble_active" = true ] || printf 'docassemble-setup\n'
    }
}

define-command -override -hidden docassemble-setup %{
    set-option buffer docassemble_previous_indentwidth %opt{indentwidth}
    set-option buffer docassemble_previous_tabstop %opt{tabstop}
    set-option buffer docassemble_previous_comment_line %opt{comment_line}
    set-option buffer docassemble_previous_comment_block_begin %opt{comment_block_begin}
    set-option buffer docassemble_previous_comment_block_end %opt{comment_block_end}
    set-option buffer docassemble_active true
    set-option buffer indentwidth 2
    set-option buffer tabstop 2
    set-option buffer comment_line '#'
    set-option buffer comment_block_begin ''
    set-option buffer comment_block_end ''
    # Unknown commands/options and unsupported buffers must not break editing.
    try %{
        set-option buffer docassemble_previous_giallo_lang %opt{giallo_lang}
        set-option buffer docassemble_previous_giallo_enabled %opt{giallo_enabled}
        evaluate-commands %sh{
            [ "$kak_opt_giallo_enabled" != true ] || printf 'try %%{ giallo-disable }\n'
        }
        set-option buffer giallo_lang docassemble
        giallo-enable
    }
}

define-command -override -hidden docassemble-restore %{
    evaluate-commands %sh{
        [ "$kak_opt_docassemble_active" != true ] || printf 'docassemble-teardown\n'
    }
}

define-command -override -hidden docassemble-teardown %{
    set-option buffer docassemble_active false
    try %{ giallo-disable }
    try %{
        set-option buffer giallo_lang %opt{docassemble_previous_giallo_lang}
        evaluate-commands %sh{
            [ "$kak_opt_docassemble_previous_giallo_enabled" != true ] || printf 'try %%{ giallo-enable }\n'
        }
    }
    set-option buffer indentwidth %opt{docassemble_previous_indentwidth}
    set-option buffer tabstop %opt{docassemble_previous_tabstop}
    set-option buffer comment_line %opt{docassemble_previous_comment_line}
    set-option buffer comment_block_begin %opt{docassemble_previous_comment_block_begin}
    set-option buffer comment_block_end %opt{docassemble_previous_comment_block_end}
}

define-command -override -docstring 'Enable Docassemble in this buffer, including outside data/questions.' docassemble-enable %{
    set-option buffer docassemble_disabled false
    set-option buffer docassemble_automatic false
    evaluate-commands %sh{
        if [ "$kak_opt_filetype" != docassemble ]; then
            printf 'set-option buffer docassemble_previous_filetype %%opt{filetype}\n'
            printf 'set-option buffer filetype docassemble\n'
        fi
    }
    docassemble-activate
}

define-command -override -docstring 'Disable Docassemble and restore previous buffer settings; opt out of detection.' docassemble-disable %{
    set-option buffer docassemble_disabled true
    set-option buffer docassemble_automatic false
    docassemble-restore
    evaluate-commands %sh{
        [ "$kak_opt_filetype" != docassemble ] || printf 'set-option buffer filetype %%opt{docassemble_previous_filetype}\n'
    }
}

define-command -override -hidden docassemble-detect %{
    evaluate-commands %sh{
        # BEGIN detection: executed directly by the tool-independent corpus test.
        path=$(printf '%s' "$kak_buffile" | tr '\\' '/')
        interview=false
        case "/$path" in
            */data/questions/*.yml|*/data/questions/*.yaml) interview=true ;;
        esac
        if [ "$kak_opt_docassemble_disabled" != true ]; then
            if [ "$interview" = true ]; then
                case "$kak_opt_filetype" in
                    ''|yaml)
                        printf 'docassemble-enable\nset-option buffer docassemble_automatic true\n' ;;
                    docassemble) printf 'docassemble-activate\n' ;;
                esac
            elif [ "$kak_opt_docassemble_automatic" = true ]; then
                printf 'docassemble-disable\nset-option buffer docassemble_disabled false\n'
            fi
        fi
        # END detection
    }
}

define-command -override -hidden docassemble-filetype-changed %{
    evaluate-commands %sh{
        if [ "$kak_opt_filetype" = docassemble ]; then
            printf 'set-option buffer docassemble_disabled false\ndocassemble-activate\n'
        elif [ "$kak_opt_docassemble_active" = true ]; then
            # Respect a user's language change rather than immediately re-claiming YAML.
            printf 'set-option buffer docassemble_disabled true\ndocassemble-restore\n'
            printf 'set-option buffer docassemble_previous_filetype %%opt{filetype}\n'
        else
            printf 'set-option buffer docassemble_previous_filetype %%opt{filetype}\n'
            printf 'docassemble-detect\n'
        fi
    }
}

# Named hooks are replaced on source, not accumulated. No global mappings.
remove-hooks global docassemble
hook -group docassemble global BufCreate .* %{ docassemble-detect }
hook -group docassemble global BufSetOption filetype=.* %{ docassemble-filetype-changed }
hook -group docassemble global BufReload .* %{ docassemble-detect }
hook -group docassemble global BufWritePost .* %{ docassemble-detect }
# Kakoune has no rename hook: detect renamed paths on the next display/write/reload.
# Deliberately not NormalIdle: that would spawn a shell on every idle in every buffer.
hook -group docassemble global WinDisplay .* %{ docassemble-detect }
# Support files already open when kakrc sources the plugin.
evaluate-commands -buffer * %{ docassemble-filetype-changed }
