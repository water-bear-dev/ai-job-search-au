---
description: Evaluate fit, draft tailored CV + cover letter, run reviewer, compile PDFs.
---

Follow the workflow in `workflows/apply.md`.

## Platform: Claude Code
- Shell: Bash tool
- File edits: Edit tool
- User prompts: AskUserQuestion (not for the Step 1 proceed gate — that is plain text after the evaluation table)
- Reviewer subagent: Agent tool, subagent_type general-purpose

User arguments: $ARGUMENTS
