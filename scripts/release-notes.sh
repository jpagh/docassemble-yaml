#!/usr/bin/env bash
# Print the CHANGELOG.md section for a version (default: the VERSION file).
#
# Used to build GitHub Release bodies. Exits non-zero when the section is
# missing, so a release is never created with empty notes.
set -euo pipefail
cd "$(dirname "$0")/.."

version="${1:-$(cat VERSION)}"

notes="$(
    awk -v version="$version" '
        !found && substr($0, 1, 4 + length(version) + 1) == "## [" version "]" {
            found = 1
            next
        }
        found && substr($0, 1, 4) == "## [" { exit }
        found {
            if (!started && $0 ~ /^[[:space:]]*$/) next
            started = 1
            lines[++n] = $0
            if ($0 ~ /[^[:space:]]/) last = n
        }
        END { for (i = 1; i <= last; i++) print lines[i] }
    ' CHANGELOG.md
)"

if [ -z "$notes" ]; then
    echo "no CHANGELOG.md section for version '${version}'" >&2
    exit 1
fi

printf '%s\n' "$notes"
