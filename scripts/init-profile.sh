#!/usr/bin/env bash
# init-profile.sh — seed gitignored profile workspace from tracked examples/
#
# Usage:
#   ./scripts/init-profile.sh           # copy only if targets are missing
#   ./scripts/init-profile.sh --force   # overwrite skills/ + AGENTS.md + cv template
#
# Called automatically by install-adapters.sh after clone.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EXAMPLES="${ROOT}/examples/profile"
FORCE=false

if [[ "${1:-}" == "--force" ]]; then
  FORCE=true
fi

if [[ ! -d "${EXAMPLES}/skills" ]]; then
  echo "ERROR: missing ${EXAMPLES}/skills — run from repo root after clone." >&2
  exit 1
fi

copy_tree() {
  local src="$1"
  local dest="$2"
  local label="$3"

  if [[ "$FORCE" == true ]]; then
    mkdir -p "$dest"
    cp -R "${src}/." "$dest/"
    echo "  refreshed ${label}"
    return
  fi

  if [[ -f "${dest}/job-application-assistant/SKILL.md" ]]; then
    echo "  ${label} already present — skipping (use --force to overwrite)"
    return
  fi

  mkdir -p "$dest"
  cp -R "${src}/." "$dest/"
  echo "  seeded ${label} from examples/profile/"
}

seed_agents() {
  local dest="${ROOT}/AGENTS.md"
  if [[ "$FORCE" == true || ! -f "$dest" ]]; then
    cp "${EXAMPLES}/AGENTS.example.md" "$dest"
    echo "  seeded AGENTS.md from examples/profile/AGENTS.example.md"
  else
    echo "  AGENTS.md already present — skipping (use --force to overwrite)"
  fi

  if [[ ! -e "${ROOT}/CLAUDE.md" ]]; then
    ln -sfn AGENTS.md "${ROOT}/CLAUDE.md"
    echo "  linked CLAUDE.md -> AGENTS.md"
  fi
}

seed_cv() {
  local dest_tex="${ROOT}/cv/main_example.tex"
  local dest_html="${ROOT}/cv/main_example.html"
  if [[ "$FORCE" == true || ! -f "$dest_tex" ]]; then
    mkdir -p "${ROOT}/cv"
    cp "${EXAMPLES}/cv/main_example.tex" "$dest_tex"
    echo "  seeded cv/main_example.tex"
  else
    echo "  cv/main_example.tex already present — skipping (use --force to overwrite)"
  fi
  if [[ "$FORCE" == true || ! -f "$dest_html" ]]; then
    mkdir -p "${ROOT}/cv"
    cp "${EXAMPLES}/cv/main_example.html" "$dest_html"
    echo "  seeded cv/main_example.html"
  fi
}

seed_config() {
  local dest="${ROOT}/config/document_output.json"
  if [[ "$FORCE" == true || ! -f "$dest" ]]; then
    mkdir -p "${ROOT}/config"
    cp "${EXAMPLES}/config/document_output.example.json" "$dest"
    echo "  seeded config/document_output.json"
  else
    echo "  config/document_output.json already present — skipping"
  fi
}

echo "Initializing local profile workspace..."
copy_tree "${EXAMPLES}/skills" "${ROOT}/skills" "skills/"
seed_agents
seed_cv
seed_config
echo "Done. Run /setup to populate your candidate profile."
