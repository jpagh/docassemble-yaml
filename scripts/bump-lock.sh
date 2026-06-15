#!/bin/bash
set -e
cd lsp && uv lock && git add uv.lock
