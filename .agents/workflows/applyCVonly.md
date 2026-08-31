---
description: Evaluate fit, draft tailored CV only (no cover letter), run reviewer, compile PDF.
---

When the user runs /applyCVonly, follow `workflows/applyCVonly.md`.

## Platform: Antigravity
- Shell: run_shell_command
- Reviewer: DefineSubagent / parallel subagent (pass drafts inline)
- Verify skills visible via /skills in CLI
- Reviewer: DefineSubagent with CV draft inline in the prompt

User input: $ARGUMENTS
