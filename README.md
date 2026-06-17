<p align="center">
  <img src="claude_animation.gif" alt="AI Job Search AU" width="200">
</p>

# AI Job Search — Australia 🇦🇺

An AI-powered job-application framework for the **Australian market**, built on
[Claude Code](https://claude.com/claude-code). Fork it, fill in your profile, and let
Claude search SEEK, evaluate fit, tailor your CV, write cover letters, and prep you for
interviews.

> This is an Australian adaptation of [MadsLorentzen/ai-job-search](https://github.com/MadsLorentzen/ai-job-search)
> (a Danish-market framework). The core workflow is the same; the job-discovery layer has
> been rebuilt for **SEEK** via a zero-dependency CLI (`tools/seek-search`) that adapts the
> API approach from [qinscode/SeekSpider](https://github.com/qinscode/SeekSpider).
> See [Credits](#credits).

## What this is

A structured workflow that turns Claude Code into a full job-application assistant:

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

# 2. Start Claude Code and build your profile
claude
/setup

# 3. Search SEEK for matching roles
/scrape

# 4. Apply to one — paste a SEEK URL directly (full description is auto-fetched)
/apply https://www.seek.com.au/job/12345678
```

See **[INSTALL.md](INSTALL.md)** for everything to install (Claude Code, Python, LaTeX) —
including a **no-sudo LaTeX setup** that works on locked-down machines.

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

## Commands

| Command | What it does |
|---------|--------------|
| `/setup` | Build your profile — from your CV, a pasted resume, or an interview |
| `/scrape` | Search SEEK (+ startup boards) and rank results by fit |
| `/apply <url-or-text>` | Evaluate fit -> draft tailored CV + cover letter -> reviewer agent -> compile PDFs |
| `/expand` | Enrich your profile from public sources you've linked (GitHub, portfolio, etc.) |
| `/upskill` | Gap analysis between your profile and tracked postings -> learning plan |
| `/reset` | Wipe profile data to start over (asks for confirmation) |

## How `/apply` works

A **drafter–reviewer** workflow with mandatory PDF verification:

1. **Parse** the posting — a SEEK URL is resolved to its full description via the GraphQL API; other URLs via WebFetch; or paste the text.
2. **Evaluate fit** against your profile (skills, experience, culture, location, salary).
3. **Draft** a tailored CV + cover letter in LaTeX.
4. **Reviewer agent** (fresh context) researches the company and critiques the drafts.
5. **Revise**, then **compile & visually inspect** both PDFs (lualatex for the CV, xelatex for the cover letter) until the CV is exactly 2 pages with no orphaned headings and the cover letter is exactly 1 page.
6. **Present** the finished files with a verification checklist.

All claims are checked against your real profile — the system never fabricates skills or experience.

## Privacy ⚠️

Your profile files (`CLAUDE.md` and `.claude/skills/job-application-assistant/*.md`) are
**tracked by git**. After `/setup` fills them with your real data, **do not commit and push
them to a public fork.** The `.gitignore` already protects your resume, search results,
generated CVs/cover letters, and the `documents/` folder — but the profile files are the
exception. See [INSTALL.md → Keeping your data private](INSTALL.md#keeping-your-data-private).

## Customisation

- **Search queries:** edit `.claude/skills/job-scraper/search-queries.md` — role-title
  keywords and `--where` locations per priority.
- **LaTeX templates:** the CV uses [moderncv](https://ctan.org/pkg/moderncv); the cover
  letter uses a custom `cover.cls` with Lato/Raleway fonts. Swap in your own.
- **Salary benchmarking:** optional — supply `salary_data.json` (see `tools/README_SALARY_TOOL.md`).

## Credits

- **[Mads Lorentzen](https://github.com/MadsLorentzen)** — the original
  [ai-job-search](https://github.com/MadsLorentzen/ai-job-search) framework this is built on.
- **[Mikkel Krogholm](https://github.com/mikkelkrogsholm)** — the original job-search skill pattern.
- **[qinscode/SeekSpider](https://github.com/qinscode/SeekSpider)** — the SEEK API approach
  that `tools/seek-search` adapts (reduced here to a single zero-dependency script).
- Built with [Claude Code](https://claude.com/claude-code) by [Anthropic](https://anthropic.com).

## License

MIT — see [LICENSE](LICENSE). Inherited from the upstream project; please keep the attribution above.
