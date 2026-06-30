# Agent handoff

**Purpose:** Single source of session context when switching between Claude Code, Cursor, Antigravity, or other agents. This file is **gitignored** — copy this example once:

```bash
cp agent_handoff.example.md agent_handoff.md
```

**Start of session (any agent):** Read `agent_handoff.md` and continue from "Next steps" unless the user gives new instructions.

**End of session:** Update all sections below before closing the chat.

---

## Meta

| Field | Value |
|-------|-------|
| **Last updated** | YYYY-MM-DD HH:MM (timezone) |
| **Last agent** | Cursor / Claude Code / Antigravity / other |
| **Branch** | `main` or feature branch name |
| **User goal** | One sentence — what we're trying to accomplish overall |

---

## Current focus

**Active task:** What is in progress right now (be specific).

**Status:** Not started / In progress / Blocked / Ready for review / Done

---

## Completed (this stretch of work)

- [ ] Item with enough detail that a new agent doesn't re-do it
- [ ] Include file paths changed: `path/to/file`

---

## Next steps (in order)

1. First thing the next agent should do
2. Second step
3. …

---

## Blockers / open decisions

- **Blocker:** … → **Needs:** user input / network / tool install
- **Decision:** Option A vs B — user preference: …

---

## Key files & pointers

| Path | Why it matters |
|------|----------------|
| `skills/...` | … |
| `workflows/apply.md` | … |
| `SYSTEM_ROADMAP.md` | Phase X in progress |

---

## Verify before continuing

Commands or checks the next agent should run:

```bash
# e.g.
./verify.sh
./scripts/install-adapters.sh
git status
```

---

## Do not assume

- Things that are **not** done yet but might look done
- WIP commits, unstaged changes, or local-only files
- Profile/setup state (`/setup` run or not)

---

## Snippets / copy-paste context

Optional: error messages, job URLs, API responses, or user quotes the next agent needs verbatim.

```
(paste here)
```

---

## Notes for job-search workflow

- Profile lives in `AGENTS.md` + `skills/job-application-assistant/`
- Multi-tool setup: [PLATFORMS.md](PLATFORMS.md)
- Roadmap: [SYSTEM_ROADMAP.md](SYSTEM_ROADMAP.md)
- Privacy: don't commit filled profile files; hook: `git config core.hooksPath .githooks`
- **`/scrape` is optional** — `/apply` and `/evaluate` work from a job URL or pasted text
- Posting input is normalized by `tools/parse_posting.py` (see `workflows/apply.md` Step 0)
- **`/evaluate`** — fit check only; **`/apply`** — full CV + cover letter pipeline
- Cover letters need **`cover_letters/OpenFonts/`** on disk (tracked in git). Run `./scripts/verify-assets.sh` after clone. Symptom if missing: LaTeX PDF ~7 KB, bullets only.
- **LaTeX primary, HTML fallback:** `latex_build.py` first; on failure `/apply` asks before `html_build.py` (Chrome/Edge). Mode: `config/document_output.json` (`latex_first_with_html_fallback` | `html_first`).

### Paste template for `/apply` or `/evaluate`

```
Company: <employer>
Role: <job title>
Location: <optional>
URL: <optional posting link>

---
<paste full job description>
```
