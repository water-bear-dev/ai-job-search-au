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
/setup            /scrape                 /apply <seek-url | text>
  |                  |                         |
  v                  v                         v
Fill in your     Search SEEK              Fetch full posting
profile          (seek-search CLI)        Evaluate fit -> score
  |                  |                         |
  v                  v                         v
Profile files    Ranked shortlist         Draft CV + cover letter (LaTeX)
ready            by fit                    -> reviewer agent critiques
                     |                        -> revise -> compile PDFs
                     v                         |
                 Pick one -> /apply       Finished PDFs to review & submit
```

**It tailors and reviews; it does not auto-submit.** You get finished, layout-verified
PDFs — you click "apply" and upload them yourself (auto-submitting violates SEEK/LinkedIn
terms and produces worse applications anyway).

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

See **[INSTALL.md](INSTALL.md)** for prerequisites (Python, LaTeX, your AI tool of choice) —
including a **no-sudo LaTeX setup** that works on locked-down machines. Tool-specific paths:
**[PLATFORMS.md](PLATFORMS.md)**. Release history: **[CHANGELOG.md](CHANGELOG.md)**.

## Job tracker UI

Local dashboard for `job_search_tracker.csv` (applications, status, attachment links):

```bash
cd tracker
pip install -r requirements.txt
python server.py
```

Open **http://127.0.0.1:8765**. See [`tracker/README.md`](tracker/README.md). Statuses are configurable in `tracker/statuses.json`.

The dashboard **auto-refreshes** when `job_search_tracker.csv` changes — keep it open while you work. `/apply` calls `tracker/upsert_application.py` to create or update a row when it generates a CV and cover letter (status `draft` by default).

## Application files

`/apply` writes dated, per-role folders (via `tools/application_paths.py`):

```
cv/20260622-NorthernHealth-AIEngineerAgenticAIAndAdvancedAnalytics/
  Andrew_Pham_CV.tex
  Andrew_Pham_CV.pdf
  build/                    # aux, log, out (gitignored artifacts)

cover_letters/20260622-NorthernHealth-AIEngineerAgenticAIAndAdvancedAnalytics/
  Andrew_Pham_CoverLetter.tex
  Andrew_Pham_CoverLetter.pdf
  build/
```

Folder names use `<YYYYMMDD>-<CompanySlug>-<RoleSlug>`. Legacy flat `main_<company>.tex` files can be migrated with `python tools/migrate_application_folders.py`.

## Compiling LaTeX

`/apply` compiles for you. To build by hand, use **`tools/latex_build.py`** — it picks **lualatex** for CVs and **xelatex** for cover letters (`cover.cls` needs `fontspec`), runs with `-interaction=nonstopmode`, and keeps build junk in each folder's `build/` subfolder:

```bash
python tools/latex_build.py \
  --cv "cv/20260622-AcmeCorp-DataEngineer/Andrew_Pham_CV.tex" \
  --cover "cover_letters/20260622-AcmeCorp-DataEngineer/Andrew_Pham_CoverLetter.tex"
```

**Tips:**

- Always pass `-interaction=nonstopmode` if you invoke `lualatex` / `xelatex` directly — moderncv can emit non-fatal warnings that otherwise hang on `?` prompts.
- moderncv may exit non-zero yet still write a valid PDF; check that the `.pdf` exists.
- After a clean compile, purge aux/log clutter: `python tools/cleanup_latex.py` (optional daily job: `./scripts/install-latex-cleanup.sh` on macOS).

See [INSTALL.md](INSTALL.md) for LaTeX prerequisites (including a no-sudo TinyTeX setup).

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

Zero dependencies (Python 3.10+ stdlib only). Full docs in
[`tools/seek-search/README.md`](tools/seek-search/README.md).

**Health check:** SEEK's endpoints are unofficial, so run `./verify.sh` any time to confirm
search + detail still work (it exits non-zero with a pointer to the fix if SEEK changes shape).

**macOS SSL errors** (`CERTIFICATE_VERIFY_FAILED` from the system Python): run Apple's
[Install Certificates.command](https://www.python.org/download/mac/tcltk/) for your Python
install, or use `curl`/`verify.sh` as a workaround until certificates are fixed.

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

## Apply from a link or paste

`/apply` and `/evaluate` accept a **job URL** or **structured pasted text**. Input is normalized by `tools/parse_posting.py` (SEEK/LinkedIn URLs are fetched automatically; other URLs trigger a WebFetch step).

**From a link:**

```text
/apply https://www.seek.com.au/job/92686067
/evaluate https://www.linkedin.com/jobs/view/1234567890
```

**From pasted text** (use this for Indeed, company career pages, or when URL fetch fails):

```text
/apply

Company: Northern Health
Role: AI Engineer (Agentic AI)
Location: Melbourne VIC
URL: https://www.seek.com.au/job/92686067

---
<paste full job description here>
```

Run `/evaluate` with the same input for a **fit score only** (no CV or cover letter).

## Commands

| Command | What it does |
|---------|--------------|
| `/setup` | Build your profile — from your CV, a pasted resume, or an interview |
| `/scrape` | Search SEEK (+ startup boards) and rank results by fit *(optional)* |
| `/evaluate <url-or-text>` | Fit check only — parse posting, score against profile, no documents |
| `/apply <url-or-text>` | Evaluate fit -> draft tailored CV + cover letter -> reviewer agent -> compile PDFs |
| `/expand` | Enrich your profile from public sources you've linked (GitHub, portfolio, etc.) |
| `/upskill` | Gap analysis between your profile and tracked postings -> learning plan |
| `/reset` | Wipe profile data to start over (asks for confirmation) |

## How `/apply` works

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
| `cover_letters/*/*.tex`, nested CV `.tex` | Generated application outputs |
| `documents/` (except `.gitkeep`), `job_search_tracker.csv` | Supporting files and tracker |
| `job_scraper/seen_jobs.json`, `*.pdf`, `salary_data.json` | Scrape state, compiled PDFs, salary data |

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
- **Salary benchmarking:** optional — supply `salary_data.json` (see `tools/README_SALARY_TOOL.md`).

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
