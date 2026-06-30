#!/usr/bin/env bash
# verify-assets.sh — confirm cover-letter LaTeX assets are present after clone.
#
# Usage:
#   ./scripts/verify-assets.sh
#
# Exit 0 if all required files exist; non-zero with actionable message otherwise.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

missing=0

check_file() {
  if [[ ! -f "$1" ]]; then
    echo "  MISSING: $1" >&2
    missing=1
  fi
}

echo "==> Cover letter assets"

check_file "cover_letters/cover.cls"

LATO_FONTS=(
  Lato-Bla.ttf Lato-BlaIta.ttf Lato-Bol.ttf Lato-BolIta.ttf
  Lato-Hai.ttf Lato-HaiIta.ttf Lato-Lig.ttf Lato-LigIta.ttf
  Lato-Reg.ttf Lato-RegIta.ttf
)
for f in "${LATO_FONTS[@]}"; do
  check_file "cover_letters/OpenFonts/fonts/lato/${f}"
done

RALEWAY_FONTS=(
  Raleway-Bold.otf Raleway-ExtraBold.otf Raleway-ExtraLight.otf Raleway-Heavy.otf
  Raleway-Light.otf Raleway-Medium.otf Raleway-Regular.otf Raleway-SemiBold.otf
  Raleway-Thin.otf
)
for f in "${RALEWAY_FONTS[@]}"; do
  check_file "cover_letters/OpenFonts/fonts/raleway/${f}"
done

if [[ "$missing" -ne 0 ]]; then
  echo "" >&2
  echo "FAIL: cover-letter fonts or cover.cls are missing." >&2
  echo "  Symptom: cover PDF shows only bullet list (~7 KB), no header/body." >&2
  echo "  Fix: git pull origin main (fonts are tracked), or restore from a complete clone." >&2
  echo "  See cover_letters/OpenFonts/LICENSES.md and INSTALL.md troubleshooting." >&2
  exit 1
fi

echo "    cover.cls + 19 font files OK"
exit 0
