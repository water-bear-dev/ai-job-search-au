# Multi-tool setup (Claude Code, Cursor, Antigravity)

This repo supports **Claude Code**, **Cursor**, and **Google Antigravity / Antigravity CLI (`agy`)** from a single canonical source of truth.

## Architecture

| Canonical | Purpose |
|-----------|---------|
| [`AGENTS.md`](AGENTS.md) | Project brain + candidate profile (`CLAUDE.md` is a symlink) |
| [`skills/`](skills/) | Skill definitions (job-application-assistant, job-scraper, upskill) |
| [`workflows/`](workflows/) | Shared workflow bodies for `/setup`, `/apply`, `/applyCVonly`, `/scrape`, `/expand`, `/reset` |

Platform adapters are thin symlinks + wrappers:

| Tool | Skills location | Commands / workflows |
|------|-----------------|----------------------|
| **Claude Code** | `.claude/skills/` → `skills/` | `.claude/commands/*.md` |
| **Cursor** | `.cursor/skills/` → `skills/` + command skills | `/setup`, `/apply`, … via `.cursor/skills/{cmd}/` |
| **Antigravity IDE** | `.agents/skills/` → `skills/` | `.agents/workflows/*.md` |
| **Antigravity CLI** | `.agents/skills/` (project) or `~/.gemini/config/skills/` (global) | Same workflow wrappers |

## After clone

```bash
./scripts/install-adapters.sh
git config core.hooksPath .githooks   # privacy hook — do this once
```

On **Windows**, if git symlinks fail:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install-adapters.ps1
```

Optional — link skills globally for Antigravity CLI:

```bash
./scripts/install-adapters.sh --antigravity-cli-global
```

Verify Antigravity CLI sees skills: run `/skills` inside `agy`.

Legacy **Gemini CLI** users can migrate old TOML commands with:

```bash
agy plugin import gemini
```

## Quick start by tool

### Claude Code

```bash
claude
/setup
/scrape
/apply https://www.seek.com.au/job/12345678
```

### Cursor

Open this repo in Cursor. Command skills are invoked as `/setup`, `/apply`, `/scrape`, etc. The always-on rule in `.cursor/rules/job-search-core.mdc` points the agent at `AGENTS.md` and `skills/`.

Reviewer subagent for `/apply` and `/applyCVonly`: delegate to `application-reviewer` (`.cursor/agents/application-reviewer.md`) or use the Task tool with `subagent_type: generalPurpose`.

### Antigravity / Antigravity CLI

Open the repo in Antigravity IDE or run `agy` in this directory. Use `/setup`, `/apply`, `/scrape`, etc. Workflows live in `.agents/workflows/` and delegate to `workflows/`.

If project-scoped skills are not picked up by CLI alone, run `./scripts/install-adapters.sh --antigravity-cli-global` or copy skills to `~/.gemini/antigravity-cli/skills/`.

## Prerequisites (all tools)

- Python 3.10+ (SEEK search CLI)
- LaTeX (for `/apply` and `/applyCVonly` PDF compilation)
- Optional: `pip install -r tracker/requirements.txt` for the [job tracker UI](tracker/README.md)
- See [INSTALL.md](INSTALL.md) for details

## Windows symlink note

Git on Windows may check out symlinks as plain files. Re-run `scripts/install-adapters.ps1` after clone to recreate junctions/symlinks locally.
