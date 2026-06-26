---
description: Evaluate fit, draft tailored CV only (no cover letter), run reviewer, compile PDF.
---

When the user runs /applyCVonly, follow `workflows/applyCVonly.md`.

## Platform: Antigravity
- Shell: run_shell_command
- Reviewer: DefineSubagent / parallel subagent (pass CV draft inline)
- Verify skills visible via /skills in CLI

User input: $ARGUMENTS
