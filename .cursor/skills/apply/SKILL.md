---
name: apply
description: Evaluate fit, draft tailored CV + cover letter, run reviewer, compile PDFs.
disable-model-invocation: true
---

Follow the workflow in `workflows/apply.md`.

## Platform: Cursor
- Shell: Shell tool
- File edits: StrReplace / Write
- User prompts: AskQuestion
- Reviewer subagent: Task tool, subagent_type generalPurpose (or delegate to application-reviewer subagent)

User arguments: $ARGUMENTS
