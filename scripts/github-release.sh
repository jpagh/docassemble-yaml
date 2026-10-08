#!/usr/bin/env bash
# Create the GitHub Release for the version in VERSION.
#
# The release body is the matching CHANGELOG.md section, followed by GitHub's
# auto-generated release notes ("What's Changed", new contributors, …).
# Publishing the release is what triggers .github/workflows/python-publish.yml
# (PyPI); run this with --dry-run to inspect the notes without touching GitHub.
#
# Run via `mise run release:github` (after `mise run bump`), or directly:
#
#     scripts/github-release.sh --dry-run
#     scripts/github-release.sh
set -euo pipefail
cd "$(dirname "$0")/.."

dry_run=false
case "${1:-}" in
    "") ;;
    --dry-run) dry_run=true ;;
    *)
        echo "usage: $0 [--dry-run]" >&2
        exit 2
        ;;
esac

version="$(cat VERSION)"
tag="v${version}"

notes_file="$(mktemp)"
trap 'rm -f "$notes_file"' EXIT

# Fail before the release exists if the changelog has no section for this
# version (e.g. the tag was pushed without `mise run bump`).
scripts/release-notes.sh "$version" > "$notes_file"

if [ "$dry_run" = true ]; then
    echo "tag: ${tag}"
    echo "--- release notes (before auto-generated notes) ---"
    cat "$notes_file"
    echo "--- command ---"
    echo "gh release create \"${tag}\" --verify-tag --title \"${tag}\" --notes-file <notes> --generate-notes"
    exit 0
fi

if gh release view "$tag" >/dev/null 2>&1; then
    echo "GitHub Release ${tag} already exists." >&2
    exit 1
fi

gh release create "$tag" \
    --verify-tag \
    --title "$tag" \
    --notes-file "$notes_file" \
    --generate-notes
