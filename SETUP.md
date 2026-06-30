# Setup Guide

Getting AI Job Search AU running. For installing the tools themselves (AI agent, Python,
LaTeX), see **[INSTALL.md](INSTALL.md)** — this guide assumes they're in place.

## 1. Fork and clone

```bash
gh repo fork <your-username>/ai-job-search-au --clone
cd ai-job-search-au

# Install platform adapters + privacy hook
./scripts/install-adapters.sh
git config core.hooksPath .githooks
```

This also seeds `skills/`, `AGENTS.md`, and `cv/main_example.tex` from tracked placeholders in `examples/profile/` (see `examples/profile/README.md`).

On Windows: `powershell -ExecutionPolicy Bypass -File scripts/install-adapters.ps1`

Or fork on GitHub and clone your fork manually. **Run the install script and `git config`
line either way** if your fork is public — see
[INSTALL.md → Keeping your data private](INSTALL.md#keeping-your-data-private).

See **[PLATFORMS.md](PLATFORMS.md)** for Claude Code, Cursor, and Antigravity specifics.

## 2. Check the SEEK tool works

No install needed (Python stdlib only). Confirm it returns live jobs:

```bash
cd tools/seek-search
python3 seek_search.py --keywords "Software Engineer" --where "All Brisbane QLD" --pages 1 --table
cd ../..
```

## 3. Run the setup interview

Open your AI agent in this repo and run:

```
/setup
```

(Claude Code: `claude` first, then `/setup`. Cursor / Antigravity: invoke `/setup` directly.)

`/setup` offers three paths and auto-detects what you have:

- **Path A — Documents folder:** drop your CV / LinkedIn export / references into `documents/` and let the agent read them all. Best signal. See `documents/README.md` for the layout.
- **Path B — Single CV import:** paste or `@`-mention one CV; the agent extracts it and asks follow-ups.
- **Path C — Interview:** structured questions section by section.

### What gets populated

| File | Content |
|------|---------|
| `AGENTS.md` | Your full candidate profile |
| `skills/job-application-assistant/01-candidate-profile.md` | Structured education, experience, skills |
| `02-behavioral-profile.md` | Behavioral profile |
| `04-job-evaluation.md` | Personalised skill-match areas and career goals |
| `05-cv-templates.md` | Profile-statement templates for your background |
| `07-interview-prep.md` | STAR examples from your experience |
| `cv/main_example.tex` | Your LaTeX CV with real details |
| `skills/job-scraper/search-queries.md` | Role keywords + AU locations for `/scrape` |
| `config/document_output.json` | LaTeX-first vs HTML-first for `/apply` |

> **Privacy:** `skills/`, `AGENTS.md`, and `cv/` are **gitignored** after `/setup` fills them with your data. Tracked placeholders live in `examples/profile/`; `./scripts/install-adapters.sh` copies them on first run. Cover-letter fonts in `cover_letters/OpenFonts/` are **tracked** — run `./scripts/verify-assets.sh` after clone.

### Re-running setup

```
/setup --section skills
/setup --section experience
/setup --section search     # reconfigure /scrape role keywords & locations
```

## 4. Optional: salary benchmarking

If you have salary data (e.g. a survey or your own research):

```bash
pip install openpyxl
python tools/convert_salary_excel.py path/to/salary-data.xlsx --source "My Salary Data 2026"
```

This creates `salary_data.json`, which `/apply` uses for benchmarking. Skip it and the
salary step is simply omitted.

## 5. Search and apply

```
/scrape                                         # ranked SEEK shortlist by fit
/apply https://www.seek.com.au/job/12345678     # SEEK URL — full description auto-fetched
/apply [paste a job description]                # or paste any posting text
```

The agent will: evaluate fit → ask before drafting → tailor a CV + cover letter → run a
reviewer subagent → compile and visually verify both PDFs → present the finished files.

## 6. Compile manually (if needed)

`/apply` compiles for you, but to do it by hand:

```bash
python tools/latex_build.py \
  --cv applied_jobs/<application_folder>/<FullName>_CV.tex \
  --cover applied_jobs/<application_folder>/<FullName>_CoverLetter.tex
python tools/cleanup_latex.py
```

## Troubleshooting

### `seek_search.py` returns nothing / an HTTP error
SEEK's API is unofficial and occasionally changes. Check `tools/seek-search/README.md` →
"Known limitations". A transient `rate_limited` resolves by spacing out calls.

### `/apply` on a SEEK URL doesn't fetch the description
SEEK HTML is Cloudflare-blocked — `/apply` must use the CLI's `--detail` mode (it does this
automatically in Step 0). If it fails, run it yourself:
`cd tools/seek-search && python3 seek_search.py --detail "<url>"`.

### LaTeX compilation errors
- CV uses **lualatex**; cover letter uses **xelatex** (needs `fontspec`).
- "File `X.sty` not found" on TinyTeX → install the package list in
  [INSTALL.md → Option A](INSTALL.md#option-a--tinytex-recommended-no-sudo--admin-password-needed).

### "salary_data.json not found"
Expected if you skipped step 4 — `/apply` omits the salary step automatically.

### Skills or /commands not found after clone
Re-run `./scripts/install-adapters.sh` (or the PowerShell variant on Windows). See
[PLATFORMS.md](PLATFORMS.md).
