<p align="center">
  <img src="claude_animation.gif" alt="AI Job Search AU" width="200">
</p>

# AI Job Search — Australia 🇦🇺

An AI-powered job-application framework for the **Australian market**. Works with
**Claude Code**, **Cursor**, and **Google Antigravity / Antigravity CLI**. Fork it, fill in
your profile, and let the agent search SEEK, evaluate fit, tailor your CV, write cover
letters, and prep you for interviews.

> **Multi-tool setup:** see [PLATFORMS.md](PLATFORMS.md). After clone, run
> `./scripts/install-adapters.sh`.

> This is a fork of [RinaldoG/ai-job-search-au](https://github.com/RinaldoG/ai-job-search-au),
> an Australian adaptation of [MadsLorentzen/ai-job-search](https://github.com/MadsLorentzen/ai-job-search)
> (a Danish-market framework). The core workflow is the same; the job-discovery layer has
> been rebuilt for **SEEK** via a zero-dependency CLI (`tools/seek-search`) that adapts the
> API approach from [qinscode/SeekSpider](https://github.com/qinscode/SeekSpider).
> See [Credits](#credits).

## What this is

A structured workflow that turns an AI coding agent into a full job-application assistant:

```
/setup            /scrape (optional)      /evaluate <url | text>     /apply <url | text>
  |                  |                         |                        |
  v                  v                         v                        v
Fill profile     Search SEEK              Fit score only          Parse -> fit -> draft
                 Rank by fit              (no documents)          CV + cover (LaTeX)
                     |                                              -> reviewer -> PDFs
                     v                                              -> applied_jobs/
                 Pick URL -> /apply or /evaluate
```

**It tailors and reviews; it does not auto-submit.** You get finished, layout-verified
PDFs — you click "apply" and upload them yourself (auto-submitting violates SEEK/LinkedIn
terms and produces worse applications anyway).

## Features

| Feature | What it does | How to use |
|---------|--------------|------------|
| **Profile setup** | Builds your candidate skills, search queries, and templates from CVs / Q&A | [`/setup`](#1-one-time-setup) |
| **Apply** | Fit score → tailored CV + cover letter → PDFs → tracker row | [`/apply`](#2-apply-to-a-job-main-workflow) |
| **CV only** | Same as apply, without a cover letter | [`/applyCVonly`](#6-commands-reference) |
| **Evaluate** | Fit score and gaps only — no documents | [`/evaluate`](#3-check-fit-first-evaluate) |
| **Scrape & rank** | Discover SEEK roles, quick/full fit triage | [`/scrape`](#4-discover-roles-scrape--optional), `/rank` |
| **Job tracker UI** | Local dashboard: statuses, Recycle Bin, analytics, profile editor | [§5](#5-track-applications-tracker-ui) |
| **Daily digest email** | Weekday SMTP email of strong SEEK + careers-page matches | [§5b](#5b-daily-digest-email-optional) |
| **Salary benchmarks** | Optional company pay index lookup during evaluate/apply | [Salary benchmarking](#salary-benchmarking-optional) |
| **Upskill** | Skill gaps vs tracked jobs → learning plan | `/upskill` |
| **Interview prep** | Prep packs from a posting + your profile | `/interview` |
| **Gmail / Notion sync** | Inbound status proposals from Gmail; optional Notion export | `/gmail-sync`, `/notion-sync` |

Privacy model: personal profile, tracker CSV, SMTP `.env`, and `config/digest.json` stay **gitignored** on your machine.

## Why a separate AU version?

SEEK is the largest Australian job board, but its HTML pages are Cloudflare-blocked — every
automated `WebFetch` returns HTTP 403. The trick: **SEEK's underlying JSON/GraphQL APIs are
not blocked.** `tools/seek-search` uses them directly:

| Endpoint | Used for |
|----------|----------|
| `/api/jobsearch/v5/search` (JSON) | Searching — lists of jobs with company, salary, remote/hybrid, teaser, URL |
| `/graphql` `jobDetails(id:)` | The **full job description** for `/apply` (by job id or URL) |

Both work with nothing more than a browser `User-Agent`. No headless browser, no API key.

## Quick start

```bash
# 1. Fork & clone (see INSTALL.md for prerequisites)
gh repo fork <your-username>/ai-job-search-au --clone
cd ai-job-search-au

# 2. Install platform adapters + privacy hook
./scripts/install-adapters.sh
git config core.hooksPath .githooks

# 3. Build your profile (Claude Code: claude then /setup; Cursor/Antigravity: /setup)
/setup

# 4. (Optional) Search SEEK for matching roles
/scrape

# 5. Apply — URL or pasted posting (/scrape not required)
/apply https://www.seek.com.au/job/12345678
```

**`/scrape` is optional.** `/apply` and `/evaluate` work standalone from any job link or pasted description.

**Full walkthrough:** [How to use](#how-to-use)

See **[INSTALL.md](INSTALL.md)** for prerequisites (Python, LaTeX, your AI tool of choice) —
including a **no-sudo LaTeX setup** that works on locked-down machines. Tool-specific paths:
**[PLATFORMS.md](PLATFORMS.md)**. Release history: **[CHANGELOG.md](CHANGELOG.md)**.

## How to use

Open this repo in **Cursor**, **Claude Code**, or **Antigravity** and run commands in chat (type `/apply`, `/evaluate`, etc.). The agent follows workflows in `workflows/` and writes files on your machine.

### 1. One-time setup

```bash
./scripts/install-adapters.sh
git config core.hooksPath .githooks
```

Then in your AI agent:

```text
/setup
```

Point the agent at your CV in `documents/cv/`, paste a resume, or answer its questions. `./scripts/install-adapters.sh` seeds placeholder `skills/`, `AGENTS.md`, and `cv/main_example.tex` from `examples/profile/`; **`/setup`** then replaces placeholders with your real profile (all gitignored — never pushed).

You need **LaTeX** when you run `/apply` or `/applyCVonly` (see [INSTALL.md](INSTALL.md)).

### 2. Apply to a job (main workflow)

You do **not** need `/scrape` first. Paste a SEEK URL, any job link, or the full posting text.

**Option A — job URL (SEEK, LinkedIn, etc.):**

```text
/apply https://www.seek.com.au/job/92686067
```

**Option B — pasted posting** (Indeed, company careers page, or when URL fetch fails):

```text
/apply

Company: Northern Health
Role: AI Engineer (Agentic AI)
Location: Melbourne VIC
URL: https://www.seek.com.au/job/92686067

---
<paste full job description here>
```

The agent will:

1. Parse the posting (`tools/parse_posting.py` — SEEK/LinkedIn URLs fetched automatically)
2. Score fit against your profile and ask before drafting
3. Draft a tailored CV + cover letter (LaTeX)
4. Run a **reviewer agent** to critique the drafts
5. Compile PDFs (`latex_build.py` primary; `html_build.py` fallback if LaTeX unavailable — user must approve) and verify layout (2-page CV, 1-page cover letter)
6. Add a row to your job tracker (`draft` status)

**You upload the PDFs yourself** — the system does not auto-submit to SEEK or LinkedIn.

Output lands in one folder per application:

```
applied_jobs/20260622-NorthernHealth-AIEngineerAgenticAIAndAdvancedAnalytics/
  Andrew_Pham_CV.tex / .pdf
  Andrew_Pham_CoverLetter.tex / .pdf
```

(`Andrew_Pham` is your name with underscores — computed by `tools/application_paths.py`.)

### 3. Check fit first (`/evaluate`)

Not sure you want to spend time on a tailored CV? Run fit-only:

```text
/evaluate https://www.seek.com.au/job/92686067
```

Same URL or paste format as `/apply`. You get a fit score and gaps — **no** LaTeX files. If it looks good:

```text
/apply https://www.seek.com.au/job/92686067
```

### 4. Discover roles (`/scrape`) — optional

Search SEEK (and optionally LinkedIn) against your profile and rank results:

```text
/scrape
```

Pick a listing from the shortlist, then `/apply` with its URL. Scrape state is stored in `job_scraper/seen_jobs.json` (gitignored) so repeat runs skip old listings.

### 5. Track applications (tracker UI)

Keep a local dashboard open while you work:

```bash
cd tracker && pip install -r requirements.txt && python3 server.py
```

Open **http://127.0.0.1:8765**. The UI **auto-refreshes** when `/apply` or scripts update `job_search_tracker.csv`.

#### Job Tracker tab (default)

| Area | What you can do |
|------|-----------------|
| **Header** | **Add job** (left) and **Recycle Bin** with count badge (right, same row) |
| **Table** | Search, paginate, inline status edits, CV/cover PDF links (cover letter omitted when none) |
| **Selection** | Click a row to highlight and select; **Select all** applies to all filtered jobs |
| **Bulk bar** | Change status for many jobs, or **Move to Recycle Bin** (confirmation required) |
| **Edit dialog** | Update fields or move a single job to Recycle Bin (confirmation required) |

**Recycle Bin** opens as a separate view (not beside the table): deleted jobs, days until auto-purge, restore, or permanent delete. Permanent delete always shows an **irreversible** confirmation. Items are purged automatically after **30 days** (`job_search_tracker_trash.csv`, gitignored).

#### Profile tab

- View `AGENTS.md` candidate profile as rendered markdown
- **Edit profile** — light WYSIWYG per section; saves markdown back to `AGENTS.md`

#### Settings tab

- **Daily digest** — see [§5b](#5b-daily-digest-email-optional): enable/disable, recipient, preferred companies + careers URLs, location (profile or custom cities), remote/hybrid, hour
- Preview or send a test digest (SMTP from `.env`)
- Saves to gitignored `config/digest.json`; syncs Identity email in `01-candidate-profile.md` when set

Statuses are configurable in `tracker/statuses.json`. The tracker is read/edit only today; it does not run agent commands yet. See [Implementation roadmap](#implementation-roadmap). API reference: [`tracker/README.md`](tracker/README.md).

### 5b. Daily digest email (optional)

Unattended weekday email of roles that heuristically match your profile — from **SEEK** (keywords in `skills/job-scraper/search-queries.md`) plus **preferred companies' careers pages** (Greenhouse / Lever / Ashby / SmartRecruiters when you set board URLs).

This is **not** the LLM `/rank` pass. Scoring uses role keywords + profile skills + a preferred-company boost. Scores are used only for ranking; they are **not** shown in the email.

#### Setup

1. **SMTP** — copy `.env.example` → `.env` and fill in:

   | Variable | Example |
   |----------|---------|
   | `SMTP_HOST` | `smtp.gmail.com` |
   | `SMTP_PORT` | `587` |
   | `SMTP_USER` | your Gmail address |
   | `SMTP_PASSWORD` | [Gmail App Password](https://support.google.com/accounts/answer/185833) (16 letters — not your normal password) |
   | `SMTP_FROM` | usually the same as `SMTP_USER` |

2. **Digest config** — copy the example (or let `/setup` / `init-profile` seed it):

   ```bash
   cp examples/profile/config/digest.example.json config/digest.json
   ```

   `config/digest.json` is **gitignored** (recipient email + company list stay private). Edit it in the tracker **Settings** tab or by hand.

3. **Enable & schedule** (macOS, Mon–Fri at the configured hour — default 08:00 local / GMT+10):

   ```bash
   # In config/digest.json or Settings: "enabled": true
   ./scripts/install-digest.sh
   ```

   After changing the send **hour**, re-run `install-digest.sh` so launchd picks it up. Uninstall: `./scripts/uninstall-digest.sh`.

#### Configure (Settings UI or `config/digest.json`)

| Setting | Purpose |
|---------|---------|
| `enabled` | Master switch for the launchd job |
| `recipient_email` | Inbox for digests (empty → profile Identity Email) |
| `preferred_companies` | Name + optional `careers_url` + `aliases` — boosts SEEK hits and scrapes careers boards |
| `location_source` | `profile` (Identity Location, e.g. Melbourne) or `custom` |
| `locations` | City list when `location_source` is `custom` (e.g. `["Melbourne", "Sydney"]`) |
| `include_remote` | Keep remote/hybrid Australia-wide roles |
| `hour` / `weekdays` | Local send time (launchd uses `hour`; default Mon–Fri) |
| `min_score` / `max_results` / `days` / `pages` | Heuristic threshold, email length, SEEK recency & depth |
| `careers_enabled` | Toggle careers-page scraping |

Prefer ATS board URLs (`boards.greenhouse.io/…`, `jobs.lever.co/…`, `jobs.ashbyhq.com/…`, `jobs.smartrecruiters.com/…`). Marketing HTML careers pages are best-effort.

#### Commands

```bash
# Preview without sending (ignores weekday / enabled for the run)
python3 tools/daily_digest.py --dry-run --force

# Send once now
python3 tools/daily_digest.py --send-now

# SEEK only or careers only
python3 tools/daily_digest.py --dry-run --force --skip-careers
python3 tools/daily_digest.py --dry-run --force --skip-seek
```

Or use **Preview digest** / **Send test email** on the tracker Settings tab (restart the tracker server after UI updates).

Logs: `job_scraper/digest.log`. Dedup state: `job_scraper/digest_state.json` (both gitignored).

### 6. Commands reference

| Command | When to use |
|---------|-------------|
| `/setup` | First time — build your profile |
| `/evaluate <url-or-text>` | Fit check only, no documents |
| `/apply <url-or-text>` | Full application — CV + cover letter + PDFs |
| `/applyCVonly <url-or-text>` | CV only — fit, draft, review, PDF (no cover letter) |
| `/scrape` | Optional — find new roles on SEEK |
| `/rank` | Batch-score scraped jobs with the evaluation framework |
| `/expand` | Enrich profile from GitHub, portfolio, etc. |
| `/upskill` | Skill gaps vs tracked jobs → learning plan |
| `/interview` | Interview prep for a role |
| `/gmail-sync` | Propose tracker status updates from Gmail (approve before write) |
| `/notion-sync` | Sync tracker rows to Notion |
| `/outcome` | Record what happened after an application |
| `/reset` | Wipe profile and start over |

### 7. CLI tools (without the agent)

Useful for debugging or scripting:

```bash
# Normalize a URL or paste (what /apply uses in Step 0)
python tools/parse_posting.py "https://www.seek.com.au/job/92686067"
python tools/parse_posting.py --text "Company: Acme\nRole: Engineer\n\n---\nDescription..."

# SEEK search / full job description
python3 tools/seek-search/seek_search.py --keywords "AI Engineer" --where "All Melbourne VIC" --table
python3 tools/seek-search/seek_search.py --detail https://www.seek.com.au/job/92686067

# Careers / ATS boards (one URL or all preferred companies from config/digest.json)
python3 tools/careers_search.py --url "https://jobs.ashbyhq.com/airwallex" --company Airwallex --table
python3 tools/careers_search.py --config --keywords "engineer" --table

# Daily digest (see §5b)
python3 tools/daily_digest.py --dry-run --force

# Optional salary benchmark (needs salary_data.json — see below)
python3 salary_lookup.py "Atlassian" --city "Sydney" --json

# Recompile PDFs after hand-editing .tex
python tools/latex_build.py \
  --cv applied_jobs/20260622-AcmeCorp-DataEngineer/Andrew_Pham_CV.tex \
  --cover applied_jobs/20260622-AcmeCorp-DataEngineer/Andrew_Pham_CoverLetter.tex

# Move legacy cv/<folder>/ + cover_letters/<folder>/ into applied_jobs/
python tools/migrate_application_folders.py --dry-run

# Health check (SEEK APIs + parse_posting)
./verify.sh
```

Legacy applications may still live under `cv/<folder>/` and `cover_letters/<folder>/`. New `/apply` runs use **`applied_jobs/`** only.

### Salary benchmarking (optional)

During `/apply` and `/evaluate`, the agent can look up a company in a local `salary_data.json` (gitignored). Without that file the step soft-skips (`{"matches":[],"error":"missing_data"}`).

```bash
# See tools/README_SALARY_TOOL.md for Excel → JSON conversion
python3 salary_lookup.py "Canva" --json
python3 salary_lookup.py "NAB" --city "Sydney" --json   # city name only, not "Sydney NSW"
```

Add optional `aliases` on company entries (e.g. `["NAB"]`) so short names match. Full guide: [`tools/README_SALARY_TOOL.md`](tools/README_SALARY_TOOL.md).

## Job tracker UI

> **Summary:** `cd tracker && python3 server.py` → http://127.0.0.1:8765. See [How to use §5](#5-track-applications-tracker-ui).

Local FastAPI app (`tracker/`) with a tabbed browser UI. Data lives in gitignored CSV files at the repo root:

| File | Purpose |
|------|---------|
| `job_search_tracker.csv` | Active applications (`/apply`, `/scrape`, `/upskill` use this schema — do not rename columns) |
| `job_search_tracker_trash.csv` | Soft-deleted jobs (Recycle Bin); auto-purged after 30 days |

### Layout

- **Dashboard** tab — analytics / status mix
- **Job Tracker** tab — applications table
- **Profile** tab — read/edit `AGENTS.md`
- **Settings** tab — daily digest: enable, recipient, preferred companies + careers URLs, location source (profile vs custom cities), remote/hybrid, hour, preview / test send (`config/digest.json`)
- **Recycle Bin** — separate screen inside Job Tracker (button top-right, next to **Add job**); **← Back to jobs** returns to the table

### Features

| Feature | Details |
|---------|---------|
| **Search** | Filters company, role, status, notes, URLs, file paths |
| **Pagination** | 10 / 20 / 50 per page; stable column widths |
| **Row selection** | Click row to highlight; no checkbox column |
| **Bulk status** | Select many → pick status → **Change status** |
| **Soft delete** | Individual or bulk **Move to Recycle Bin**; confirm before moving |
| **Recycle Bin** | Restore to tracker, or **Delete permanently** (confirm: irreversible); shows days until purge |
| **Attachments** | Open compiled CV PDF; cover letter link only when `cover_letter_file` is set |
| **Profile editor** | WYSIWYG (bold, lists, links) with markdown round-trip to `AGENTS.md` |
| **Digest settings** | Recipient, companies + careers URLs, location filter, enable schedule; preview / test send |
| **Live refresh** | Polls `/api/revision` when `upsert_application.py` or the UI writes CSV |

### Run options

```bash
cd tracker && python3 server.py
# or
TRACKER_PORT=9000 python3 server.py
```

Interactive API docs: http://127.0.0.1:8765/api/docs

## Implementation roadmap

High-level plan for evolving the repo. Full tracker history and Phase 1–3 detail:
**[SYSTEM_ROADMAP.md](SYSTEM_ROADMAP.md)**.

### Shipped

| Area | Status |
|------|--------|
| Multi-tool agents (`/setup`, `/apply`, `/evaluate`, `/scrape`, …) | Done |
| SEEK + optional LinkedIn CLIs | Done |
| `tools/parse_posting.py` — URL or paste → normalized JSON | Done |
| Job tracker UI — tabs, search, bulk actions, Recycle Bin (30-day), profile WYSIWYG | Done |
| Daily digest email — SEEK + careers pages, SMTP, launchd, Settings tab | Done |
| `/apply` auto-upsert to tracker + live UI refresh | Done |
| Dated application folders + `latex_build.py` | Done |
| Cover letter font symlink for `applied_jobs/` compiles | Done |

### Agent commands vs scripts

`/apply` and friends are **workflow instructions** for an AI agent (`workflows/*.md`), not standalone binaries. A future UI will combine:

- **Deterministic tools** (no LLM): `parse_posting.py`, `seek_search.py`, `latex_build.py`, `upsert_application.py`
- **Agent-backed steps** (LLM): fit scoring, CV/cover letter drafting, reviewer critique

The roadmap extends the existing **`tracker/`** FastAPI app rather than building a separate stack. Local-only (`127.0.0.1`), same privacy model as today.

### Planned — workflow UI (extend `tracker/`)

| Phase | Goal | Key deliverables |
|-------|------|------------------|
| **UI-1** | Parse & preview | URL/paste form, `POST /api/parse-posting`, posting preview in browser |
| **UI-2** | Job runner skeleton | `POST /api/runs`, SSE log stream, run status (queued / running / done) |
| **UI-3** | Evaluate from UI | **Evaluate fit** button → `/evaluate` workflow (parse + fit score, no LaTeX) |
| **UI-4** | Apply from UI | **Apply** button → full pipeline (draft → compile → tracker upsert); hybrid agent or orchestrator |
| **UI-5** | Scrape tab | Run SEEK search from UI; evaluate or apply per result row |

**Smallest first slice (UI-1):** paste form + parse API + “copy prompt for Cursor” fallback — no agent automation required.

**Hybrid apply (UI-4):** UI runs parse, compile, and tracker steps; LLM steps via Python orchestrator (Claude/OpenAI API) or by spawning the agent CLI with `workflows/apply.md`.

### Planned — tracker backend (Phase 3 in SYSTEM_ROADMAP)

When application count grows:

- SQLite mirror of `job_search_tracker.csv`
- Search, filter, kanban by status
- Run history table for UI job logs

### Out of scope (for now)

- Cloud hosting or multi-user auth
- Auto-submit to SEEK/LinkedIn
- Indeed / Wellfound native parsers (paste fallback only)
- `--fast` skip-fit flag on `/apply`

Contributions welcome on any phase — comment in issues or PRs referencing [SYSTEM_ROADMAP.md](SYSTEM_ROADMAP.md).

## Application files & LaTeX / HTML fallback

`/apply` writes one dated folder per role under **`applied_jobs/`** (gitignored). CV and cover letter share the same folder — see [How to use §2](#2-apply-to-a-job-main-workflow).

`/apply` compiles for you (LaTeX first). If LaTeX fails or is unavailable, the agent asks before HTML fallback (`tools/html_build.py`). Set `html_first` in `config/document_output.json` to skip LaTeX.

```bash
# Primary (LaTeX)
python tools/latex_build.py \
  --cv "applied_jobs/20260622-AcmeCorp-DataEngineer/Andrew_Pham_CV.tex" \
  --cover "applied_jobs/20260622-AcmeCorp-DataEngineer/Andrew_Pham_CoverLetter.tex"

# Fallback (HTML → PDF)
python tools/html_build.py \
  --cv "applied_jobs/20260622-AcmeCorp-DataEngineer/Andrew_Pham_CV.html" \
  --cover "applied_jobs/20260622-AcmeCorp-DataEngineer/Andrew_Pham_CoverLetter.html"
```

**Tips:**

- Cover letters under `applied_jobs/` use `\documentclass{../../cover_letters/cover}`. `cover.cls` loads fonts from `cover_letters/OpenFonts/` (tracked in git — verify with `./scripts/verify-assets.sh` after clone). `latex_build.py` symlinks `OpenFonts` into the application folder before compile. Symptom if fonts missing: PDF ~7 KB, bullets only, no header/body.
- Always pass `-interaction=nonstopmode` if you invoke `lualatex` / `xelatex` directly — moderncv can emit non-fatal warnings that otherwise hang on `?` prompts.
- moderncv may exit non-zero yet still write a valid PDF; check that the `.pdf` exists.
- After a clean compile, purge aux/log clutter: `python tools/cleanup_latex.py` (optional daily job: `./scripts/install-latex-cleanup.sh` on macOS).

See [INSTALL.md](INSTALL.md) for LaTeX prerequisites (including no-sudo TinyTeX) and HTML fallback (Chrome/Edge).

## The `seek-search` tool (works standalone too)

```bash
cd tools/seek-search

# Search Brisbane AI roles
python3 seek_search.py --keywords "AI Engineer" --where "All Brisbane QLD" --table

# Remote/hybrid Australia-wide
python3 seek_search.py --keywords "Senior Full Stack Engineer" --where "All Australia" --remote

# Fetch one job's FULL description (id or URL) — what /apply uses
python3 seek_search.py --detail https://www.seek.com.au/job/12345678
```

See [`tools/seek-search/README.md`](tools/seek-search/README.md) for full CLI docs. Also covered in [How to use §7](#7-cli-tools-without-the-agent).

**Health check:** SEEK's endpoints are unofficial, so run `./verify.sh` any time to confirm
search + detail still work (it exits non-zero with a pointer to the fix if SEEK changes shape).

**macOS SSL errors** (`CERTIFICATE_VERIFY_FAILED` from the system Python): install
[`certifi`](https://pypi.org/project/certifi/) (used by `tools/careers_search.py`), or run
Apple's [Install Certificates.command](https://www.python.org/download/mac/tcltk/) for your
Python version. `./verify.sh` / `curl` can confirm connectivity independently.

## Job boards

| Board | Status | Notes |
|-------|--------|-------|
| **SEEK** | ✅ Primary | `tools/seek-search` — search + full descriptions, no key |
| **LinkedIn** | ⚠️ Optional, **off by default** | `tools/linkedin-search` — works with no key, but **automating LinkedIn is against its Terms of Service**; personal/low-volume use only, at your own risk |
| **Indeed** | ❌ Not supported | Cloudflare/CAPTCHA-walled with no usable API. Paste an Indeed posting into `/apply` instead |

### Optional: LinkedIn ⚠️

`tools/linkedin-search` adds LinkedIn coverage via its guest endpoints (no login, no key).
**LinkedIn's User Agreement prohibits automated access**, so this is **disabled by default in
`/scrape`** and intended for personal, low-volume use only — it can get your IP rate-limited.
SEEK is the primary, supported source. To opt in, run `/scrape linkedin`, or use the tool
directly:

```bash
cd tools/linkedin-search
python3 linkedin_search.py --keywords "AI Engineer" --where "Brisbane, Queensland, Australia" --table
```

See [`tools/linkedin-search/README.md`](tools/linkedin-search/README.md) for the full warning
and options. If in doubt, don't use it — paste LinkedIn postings into `/apply` manually.

## How `/apply` works (under the hood)

A **drafter–reviewer** workflow with mandatory PDF verification:

1. **Parse** the posting via `tools/parse_posting.py` — SEEK/LinkedIn URLs fetched automatically; other URLs via WebFetch; or structured paste.
2. **Evaluate fit** against your profile (skills, experience, culture, location, salary).
3. **Draft** a tailored CV + cover letter in LaTeX under dated application folders (see [Application files](#application-files)).
4. **Reviewer agent** (fresh context) researches the company and critiques the drafts.
5. **Revise**, then **compile & visually inspect** both PDFs (`tools/latex_build.py` — lualatex for the CV, xelatex for the cover letter) until the CV is exactly 2 pages with no orphaned headings and the cover letter is exactly 1 page.
6. **Upsert** a tracker row and **present** the finished files with a verification checklist.

All claims are checked against your real profile — the system never fabricates skills or experience.

## Privacy ⚠️

This repo is meant to be forked publicly. **Your personal data stays local** — `.gitignore`
keeps it out of git:

| Gitignored | What it holds |
|------------|---------------|
| `cv/`, `skills/`, `AGENTS.md` | Profile and LaTeX workspace (populated by `/setup`) |
| `applied_jobs/` | Generated application CVs and cover letters (per-job folders) |
| `cover_letters/*/*.tex`, nested CV `.tex` | Legacy application outputs |
| `documents/` (except `.gitkeep`), `job_search_tracker.csv`, `job_search_tracker_trash.csv` | Supporting files and tracker |
| `job_scraper/seen_jobs.json`, `*.pdf`, `salary_data.json`, `.env`, `config/digest.json` | Scrape state, compiled PDFs, salary data, SMTP secrets, digest prefs |

`CLAUDE.md` is a **symlink to `AGENTS.md`** (tracked as a symlink only — safe to push as long
as you never commit the profile file itself). After `/setup`, your filled-in workspace exists
only on disk under the paths above.

**Belt-and-braces:** enable the pre-commit hook once — it blocks accidentally staging profile
files on older forks that still track them:

```bash
git config core.hooksPath .githooks
```

See [INSTALL.md → Keeping your data private](INSTALL.md#keeping-your-data-private).

## Customisation

- **Search queries:** edit `skills/job-scraper/search-queries.md` — role-title
  keywords and `--where` locations per priority.
- **LaTeX templates:** the CV uses [moderncv](https://ctan.org/pkg/moderncv); the cover
  letter uses a custom `cover.cls` with Lato/Raleway fonts. Swap in your own.
- **Salary benchmarking:** optional — supply `salary_data.json` (see [Salary benchmarking](#salary-benchmarking-optional) and `tools/README_SALARY_TOOL.md`).
- **Daily digest:** copy `examples/profile/config/digest.example.json` → `config/digest.json`, set SMTP in `.env`, run `scripts/install-digest.sh` (see [§5b](#5b-daily-digest-email-optional)).

## Credits

- **[Rinaldo Gagiano](https://github.com/RinaldoG)** — original
  [ai-job-search-au](https://github.com/RinaldoG/ai-job-search-au) this project is forked from.
- **[Mads Lorentzen](https://github.com/MadsLorentzen)** — upstream
  [ai-job-search](https://github.com/MadsLorentzen/ai-job-search) framework (Danish market).
- **[Mikkel Krogsholm](https://github.com/mikkelkrogsholm)** — the original job-search skill pattern.
- **[qinscode/SeekSpider](https://github.com/qinscode/SeekSpider)** — the SEEK API approach
  that `tools/seek-search` adapts (reduced here to a single zero-dependency script).
- Built with AI coding agents ([Claude Code](https://claude.com/claude-code), Cursor, Antigravity).

## License

MIT — see [LICENSE](LICENSE). Inherited from the upstream project; please keep the attribution above.
