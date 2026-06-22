#!/bin/sh
# Daily LaTeX artifact cleanup (archive loose files, purge build/ folders).
# Install: ./scripts/install-latex-cleanup.sh

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$ROOT/tools/cleanup_latex.py" --daily
