# Changelog

All notable changes to this project are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- **Multi-tool support** — canonical `skills/`, `workflows/`, and `AGENTS.md` (`CLAUDE.md` symlink) with platform adapters for Claude Code, Cursor, and Google Antigravity / Antigravity CLI
- **`scripts/install-adapters.sh`** and **`scripts/install-adapters.ps1`** — create skill symlinks and command/workflow wrappers after clone
- **[`PLATFORMS.md`](PLATFORMS.md)** — per-tool setup and invocation guide
- **[`SYSTEM_ROADMAP.md`](SYSTEM_ROADMAP.md)** — planned job tracker UI, `/apply` integration, and SQLite upgrade phases
- **`agent_handoff.example.md`** — template for session handoff when switching between agents; live `agent_handoff.md` is gitignored
- **Cursor adapters** — `.cursor/skills/`, command skills (`/setup`, `/apply`, …), `application-reviewer` subagent, `job-search-core` rule
- **Antigravity adapters** — `.agents/skills/` symlinks and `.agents/workflows/` wrappers

### Changed

- Moved skills from `.claude/skills/` → **`skills/`**
- Moved workflow bodies from `.claude/commands/` → **`workflows/`** (platform dirs now hold thin wrappers)
- **Workflows** use neutral tool language (shell commands, search/replace edits, reviewer subagent) instead of Claude Code–specific tool names
- Removed `allowed-tools` from skill frontmatter (Claude-only; ignored by other agents)
- **`AGENTS.md`** replaces inline-only `CLAUDE.md` as project brain; profile checklist references `AGENTS.md`
- **Pre-commit hook** blocks `skills/` profile paths and `AGENTS.md` (was `.claude/skills/…` and `CLAUDE.md`)
- **`.gitignore`** — allow `.agents/skills/` and `.agents/workflows/`; ignore `agent_handoff.md`
- Updated **README**, **INSTALL**, **SETUP**, **REVIEW_NOTES**, **documents/README** for multi-tool paths

### Migration

After pulling these changes:

```bash
./scripts/install-adapters.sh
git config core.hooksPath .githooks
cp agent_handoff.example.md agent_handoff.md   # optional, for agent handoff
```

---

## [0.2.0] — 2026-06

### Added

- **Privacy pre-commit hook** (`.githooks/pre-commit`) — blocks committing profile files filled with PII
- **`verify.sh`** — smoke test for SEEK search + detail endpoints
- **`/scrape` command wrapper** — thin `.claude/commands/scrape.md` delegating to job-scraper skill
- **`--days` recency filter** on `seek-search` CLI
- **AU salary tool retune** — Australian legal-suffix stripping, AUD examples (`salary_lookup.py`, `tools/convert_salary_excel.py`)
- **`REVIEW_NOTES.md`** — design rationale and review context

### Changed

- Hardened docs and setup for public fork/release (privacy warnings, hook instructions)
- Softened AI-tool naming rule in CVs/cover letters to “specific tools you actually used”

---

## [0.1.1] — 2026-06

### Added

- **Optional LinkedIn CLI** (`tools/linkedin-search`) — guest endpoints, no API key
- LinkedIn **off by default** in `/scrape`; ToS warnings in README and CLI stderr

---

## [0.1.0] — 2026-06

Initial **AI Job Search AU** release — Australian adaptation of [MadsLorentzen/ai-job-search](https://github.com/MadsLorentzen/ai-job-search).

### Added

- **SEEK job discovery** — `tools/seek-search` (zero-dependency Python CLI; JSON search + GraphQL full descriptions)
- **Claude Code workflow** — `/setup`, `/scrape`, `/apply`, `/expand`, `/upskill`, `/reset`
- **Job application assistant skills** — fit evaluation, CV/cover letter LaTeX templates, interview prep
- **Drafter–reviewer `/apply` loop** with mandatory PDF compile and visual verification
- **LaTeX templates** — moderncv CV (`cv/`), custom `cover.cls` cover letters
- **`documents/` folder layout** for CV, LinkedIn export, diplomas, references, past applications
- **Job tracker schema** — `job_search_tracker.csv` (gitignored; used by scraper dedup and `/upskill`)
- **Scrape dedup** — `job_scraper/seen_jobs.json`
- **Optional salary benchmarking** — `salary_lookup.py`, `tools/README_SALARY_TOOL.md`
- **Docs** — README, INSTALL, SETUP, sanitized placeholder profile template

### Removed

- Danish portal CLIs and Bun dependency from upstream

---

## Links

- [SYSTEM_ROADMAP.md](SYSTEM_ROADMAP.md) — what’s planned next
- [PLATFORMS.md](PLATFORMS.md) — Claude Code, Cursor, Antigravity setup
- [REVIEW_NOTES.md](REVIEW_NOTES.md) — design decisions and fragilities
