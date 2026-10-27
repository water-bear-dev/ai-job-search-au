---
description: Evaluate fit, draft tailored CV only (no cover letter), run reviewer, compile PDF.
---

Follow the workflow in `workflows/applyCVonly.md`.

## Platform: Claude Code
- Shell: Bash tool
- File edits: Edit tool
- User prompts: AskUserQuestion (not for the Step 1 proceed gate — that is plain text after the evaluation table)
- Reviewer subagent: Agent tool, subagent_type general-purpose

User arguments: $ARGUMENTS
