# kakoune-lsp v22.0.0: source after `evaluate-commands %sh{ kak-lsp }`.
# Independent of giallo; enable upstream LSP once with `lsp-enable`.
try %{ declare-option -docstring 'docassemble-lsp executable (PATH name or absolute path, not shell arguments).' str docassemble_lsp_command docassemble-lsp }
try %{ declare-option -hidden bool docassemble_lsp_disabled false }
try %{ declare-option -hidden bool docassemble_lsp_active false }

define-command -override -hidden docassemble-lsp-configure %{
    evaluate-commands %sh{
        if [ "$kak_opt_filetype" = docassemble ] && [ "$kak_opt_docassemble_lsp_disabled" != true ]; then
            printf 'set-option buffer docassemble_lsp_active true\nset-option buffer lsp_language_id docassemble\n'
            if command -v "$kak_opt_docassemble_lsp_command" >/dev/null 2>&1; then
                # Escape separately for TOML strings and Kakoune single-quoted arguments.
                command=$(printf '%s' "$kak_opt_docassemble_lsp_command" | sed 's/\\/\\\\/g; s/"/\\"/g')
                config=$(printf '[docassemble]\ncommand = "%s"\nargs = ["lsp"]\nroot_globs = ["docassemble", "pyproject.toml", "setup.py", ".git"]\nsingle_instance = false\n' "$command")
                printf "set-option buffer lsp_servers '%s'\n" "$(printf '%s' "$config" | sed "s/'/''/g")"
            else
                printf "set-option buffer lsp_servers ''\n"
                printf "echo -debug -- 'Docassemble LSP: server not executable; install docassemble-lsp on PATH or set-option buffer docassemble_lsp_command /absolute/path/to/venv/bin/docassemble-lsp, then docassemble-lsp-enable. Highlighting is independent.'\n"
            fi
        elif [ "$kak_opt_docassemble_lsp_active" = true ]; then
            printf "set-option buffer docassemble_lsp_active false\nset-option buffer lsp_servers ''\nset-option buffer lsp_language_id ''\n"
        fi
    }
}

define-command -override -docstring 'Enable/retry Docassemble LSP in this buffer (upstream lsp-enable must be enabled).' docassemble-lsp-enable %{
    set-option buffer docassemble_lsp_disabled false
    docassemble-lsp-configure
    try %{ lsp-did-open }
}

define-command -override -docstring 'Disable only Docassemble LSP in this buffer; keep filetype and highlighting.' docassemble-lsp-disable %{
    try %{ lsp-did-close }
    set-option buffer docassemble_lsp_disabled true
    docassemble-lsp-configure
}

remove-hooks global docassemble-lsp
hook -group docassemble-lsp global BufSetOption filetype=.* %{ docassemble-lsp-configure }
hook -group docassemble-lsp global BufSetOption docassemble_lsp_command=.* %{ docassemble-lsp-configure }
evaluate-commands -buffer * %{ docassemble-lsp-configure }
