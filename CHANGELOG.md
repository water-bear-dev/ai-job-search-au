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
- **Job tracker UI (Phase 1)** — `tracker/` FastAPI app + static dashboard for `job_search_tracker.csv`; `job_search_tracker.example.csv` template; `tracker/statuses.json`
- **`tools/application_paths.py`** — canonical `YYYYMMDD-CompanyName-Role` folder naming for CV and cover letter outputs
- **`tools/latex_build.py`** — compile CV (lualatex) and cover letter (xelatex) with build artifacts in per-application `build/` subfolders
- **`tools/cleanup_latex.py`** — archive loose LaTeX artifacts; optional end-of-day purge of `build/` folders
- **`scripts/cleanup-latex.sh`** and **`scripts/install-latex-cleanup.sh`** — manual cleanup wrapper and macOS launchd daily job (11 PM)
- **`tools/migrate_application_folders.py`** — migrate legacy flat `main_<company>.tex` / `cover_<company>_*.tex` files into dated application folders
- **Tracker auto-sync** — `tracker/upsert_application.py` (called by `/apply`), `tracker/csv_store.py`, `tracker/revision.py`, revision polling API, live UI refresh when the CSV changes
- **`tools/parse_posting.py`** — normalize job input (SEEK/LinkedIn URL or structured paste) for `/apply` and `/evaluate`
- **`/evaluate` command** — fit evaluation only, no CV/cover letter or tracker update
- **`tools/test_parse_posting.py`** — unit tests for paste parsing and URL routing (no network)

### Changed

- Moved skills from `.claude/skills/` → **`skills/`**
- Moved workflow bodies from `.claude/commands/` → **`workflows/`** (platform dirs now hold thin wrappers)
- **Workflows** use neutral tool language (shell commands, search/replace edits, reviewer subagent) instead of Claude Code–specific tool names
- Removed `allowed-tools` from skill frontmatter (Claude-only; ignored by other agents)
- **`AGENTS.md`** replaces inline-only `CLAUDE.md` as project brain; profile checklist references `AGENTS.md`
- **Personal workspace no longer tracked** — `cv/`, `skills/`, and `AGENTS.md` are gitignored; populate locally via `/setup` (`CLAUDE.md` remains a tracked symlink to `AGENTS.md`)
- **`/apply` output layout** — dated folders under `applied_jobs/` (CV + cover letter in one folder per application); legacy `cv/<folder>/` + `cover_letters/<folder>/` still supported
- **Pre-commit hook** — still blocks profile paths for older forks; primary privacy model is now `.gitignore` on the whole personal workspace
- **`.gitignore`** — personal workspace (`cv/`, `skills/`, `AGENTS.md`), `applied_jobs/`, nested application `.tex`, tracker revision log, LaTeX cleanup log; allow `.agents/skills/` and `.agents/workflows/`
- Updated **README**, **INSTALL**, **SETUP**, **REVIEW_NOTES**, **tracker/README**, **workflows/apply**, **documents/README** for multi-tool paths, application folders, LaTeX build/cleanup, tracker auto-tracking, and gitignored personal workspace
- **`workflows/apply.md` Step 0** — uses `parse_posting.py` instead of inline URL routing; README documents URL vs paste examples

### Migration

After pulling these changes:

```bash
./scripts/install-adapters.sh
git config core.hooksPath .githooks
cp agent_handoff.example.md agent_handoff.md   # optional, for agent handoff
/setup                                          # rebuild local cv/, skills/, AGENTS.md if missing
```

If you have legacy flat CV/cover letter files, run `python tools/migrate_application_folders.py` once (dry-run first).

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
