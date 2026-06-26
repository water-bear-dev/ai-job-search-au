#!/usr/bin/env bash
# install-adapters.sh — create platform skill symlinks and command/workflow wrappers.
#
# Usage:
#   ./scripts/install-adapters.sh
#   ./scripts/install-adapters.sh --antigravity-cli-global   # also link skills into ~/.gemini/config/skills/
#
# Re-run after clone on Windows if symlinks were not checked out correctly.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SKILLS=(job-application-assistant job-scraper upskill)
COMMANDS=(setup apply applyCVonly evaluate scrape expand reset)

link_skill() {
  local platform_dir="$1"
  local skill="$2"
  local target="../../skills/${skill}"
  local link_path="${platform_dir}/${skill}"

  mkdir -p "$platform_dir"
  if [[ -e "$link_path" && ! -L "$link_path" ]]; then
    echo "ERROR: ${link_path} exists and is not a symlink. Move it aside and re-run." >&2
    exit 1
  fi
  ln -sfn "$target" "$link_path"
  echo "  linked ${link_path} -> ${target}"
}

write_claude_command() {
  local cmd="$1"
  local desc="$2"
  local extra="${3:-}"

  mkdir -p .claude/commands
  cat > ".claude/commands/${cmd}.md" <<EOF
---
description: ${desc}
---

Follow the workflow in \`workflows/${cmd}.md\`.

## Platform: Claude Code
- Shell: Bash tool
- File edits: Edit tool
- User prompts: AskUserQuestion
${extra}

User arguments: \$ARGUMENTS
EOF
  echo "  wrote .claude/commands/${cmd}.md"
}

write_cursor_command_skill() {
  local cmd="$1"
  local desc="$2"
  local extra="${3:-}"

  mkdir -p ".cursor/skills/${cmd}"
  cat > ".cursor/skills/${cmd}/SKILL.md" <<EOF
---
name: ${cmd}
description: ${desc}
disable-model-invocation: true
---

Follow the workflow in \`workflows/${cmd}.md\`.

## Platform: Cursor
- Shell: Shell tool
- File edits: StrReplace / Write
- User prompts: AskQuestion
${extra}

User arguments: \$ARGUMENTS
EOF
  echo "  wrote .cursor/skills/${cmd}/SKILL.md"
}

write_antigravity_workflow() {
  local cmd="$1"
  local desc="$2"
  local extra="${3:-}"

  mkdir -p .agents/workflows
  cat > ".agents/workflows/${cmd}.md" <<EOF
---
description: ${desc}
---

When the user runs /${cmd}, follow \`workflows/${cmd}.md\`.

## Platform: Antigravity
- Shell: run_shell_command
- Reviewer: DefineSubagent / parallel subagent (pass drafts inline)
- Verify skills visible via /skills in CLI
${extra}

User input: \$ARGUMENTS
EOF
  echo "  wrote .agents/workflows/${cmd}.md"
}

echo "Linking canonical skills into platform adapter directories..."
for skill in "${SKILLS[@]}"; do
  link_skill ".claude/skills" "$skill"
  link_skill ".cursor/skills" "$skill"
  link_skill ".agents/skills" "$skill"
done

write_claude_command setup "Build your candidate profile from documents, CV, or interview."
write_claude_command apply "Evaluate fit, draft tailored CV + cover letter, run reviewer, compile PDFs." "- Reviewer subagent: Agent tool, subagent_type general-purpose"
write_claude_command applyCVonly "Evaluate fit, draft tailored CV only (no cover letter), run reviewer, compile PDF." "- Reviewer subagent: Agent tool, subagent_type general-purpose"
write_claude_command evaluate "Evaluate job fit only — no CV or cover letter."
write_claude_command scrape "Search SEEK (and optionally LinkedIn) for jobs matching your profile."
write_claude_command expand "Enrich your profile from documents and public online presence."
write_claude_command reset "Reset candidate profile data (destructive; asks for confirmation)."

echo "Writing Cursor command skills..."
write_cursor_command_skill setup "Build your candidate profile from documents, CV, or interview."
write_cursor_command_skill apply "Evaluate fit, draft tailored CV + cover letter, run reviewer, compile PDFs." "- Reviewer subagent: Task tool, subagent_type generalPurpose (or delegate to application-reviewer subagent)"
write_cursor_command_skill applyCVonly "Evaluate fit, draft tailored CV only (no cover letter), run reviewer, compile PDF." "- Reviewer subagent: Task tool, subagent_type generalPurpose (or delegate to application-reviewer subagent)"
write_cursor_command_skill evaluate "Evaluate job fit only — no CV or cover letter."
write_cursor_command_skill scrape "Search SEEK (and optionally LinkedIn) for jobs matching your profile."
write_cursor_command_skill expand "Enrich your profile from documents and public online presence."
write_cursor_command_skill reset "Reset candidate profile data (destructive; asks for confirmation)."

echo "Writing Antigravity workflow wrappers..."
write_antigravity_workflow setup "Build your candidate profile from documents, CV, or interview."
write_antigravity_workflow apply "Evaluate fit, draft tailored CV + cover letter, run reviewer, compile PDFs." "- Reviewer: DefineSubagent with drafts inline in the prompt"
write_antigravity_workflow applyCVonly "Evaluate fit, draft tailored CV only (no cover letter), run reviewer, compile PDF." "- Reviewer: DefineSubagent with CV draft inline in the prompt"
write_antigravity_workflow evaluate "Evaluate job fit only — no CV or cover letter."
write_antigravity_workflow scrape "Search SEEK (and optionally LinkedIn) for jobs matching your profile."
write_antigravity_workflow expand "Enrich your profile from documents and public online presence."
write_antigravity_workflow reset "Reset candidate profile data (destructive; asks for confirmation)."

if [[ "${1:-}" == "--antigravity-cli-global" ]]; then
  GLOBAL="${HOME}/.gemini/config/skills"
  mkdir -p "$GLOBAL"
  echo "Linking skills into ${GLOBAL} for Antigravity CLI global scope..."
  for skill in "${SKILLS[@]}"; do
    ln -sfn "${ROOT}/skills/${skill}" "${GLOBAL}/${skill}"
    echo "  linked ${GLOBAL}/${skill}"
  done
fi

echo "Done. See PLATFORMS.md for per-tool usage."
