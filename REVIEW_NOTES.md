# Review & Design Notes

Context and rationale behind this repo — for reviewers, contributors, and future-me. This is
a design record, not user docs (see `README.md` / `INSTALL.md` / `SETUP.md` for those).

## Origin

This is an Australian adaptation of [MadsLorentzen/ai-job-search](https://github.com/MadsLorentzen/ai-job-search)
(MIT). The upstream project is a set of Claude Code skills/commands (`/setup`, `/scrape`,
`/apply`) that turn Claude into a job-application assistant: build a profile → evaluate fit →
generate a tailored LaTeX CV + cover letter via a drafter/reviewer loop → compile and
visually verify the PDFs.

The **core workflow is country-agnostic and was kept**. The part that was Denmark-specific —
job *discovery* — was rebuilt for Australia.

## Key technical findings

These shaped the implementation and are the most important things for a reviewer to
re-verify:

1. **SEEK blocks HTML, not its APIs.** `https://www.seek.com.au/job/<id>` and search HTML
   pages return HTTP 403 (Cloudflare) to automated clients. But two underlying endpoints
   respond to a plain browser `User-Agent` with no key/login:
   - `GET /api/jobsearch/v5/search` (JSON) → search results with company, salary, work
     arrangement, teaser, URL.
   - `POST /graphql` `jobDetails(id:)` → the full job description (+ salary, advertiser,
     status, recruiter phone). GraphQL introspection is disabled, so the queried field set
     in `tools/seek-search/seek_search.py` was discovered by probing and is fixed by hand.
2. **LinkedIn guest endpoints work without auth** (`/jobs-guest/jobs/api/seeMoreJobPostings/search`
   and `/jobs-guest/jobs/api/jobPosting/<id>`) — search cards + full descriptions, no login,
   no key. **But automating LinkedIn violates its User Agreement** (see design decisions).
3. **Indeed is not viable** — Cloudflare + CAPTCHA, no usable public API. Documented as
   not-supported; users paste Indeed postings into `/apply` instead.
4. **LaTeX with no admin rights** — TinyTeX installs into `$HOME` with no sudo, which matters
   for users on managed/work machines. The exact `tlmgr` package list needed by `moderncv` +
   `cover.cls` is documented in `INSTALL.md` so others don't hit the "File `X.sty` not found"
   one-at-a-time loop.

## What changed from upstream

- **Removed** the four Danish portal CLIs (`.agents/skills/jobindex|jobnet|jobbank|jobdanmark`)
  and the Bun dependency they required.
- **Added** `tools/seek-search/` — zero-dependency Python CLI (`--keywords/--where/--remote`
  search, `--detail <id|url>` full description). Approach adapted from
  [qinscode/SeekSpider](https://github.com/qinscode/SeekSpider), reduced from a full
  Scrapy/Postgres/web-app to a single stdlib script.
- **Added** `tools/linkedin-search/` — optional, off-by-default LinkedIn CLI (see below).
- **Rewrote** `README.md`, `INSTALL.md`, `SETUP.md` for the AU market; genericized
  `.claude/commands/{setup,apply}.md` and `.claude/skills/job-scraper/` (SKILL + search
  queries). `/apply` now resolves SEEK and LinkedIn URLs directly via the CLIs.
- **Scrubbed** all Denmark-specific references (portals, `.dk`, Danish closings, etc.).
- **Reset** all profile files to placeholders (this template ships no personal data).

## Design decisions & rationale

- **Zero-dependency tools.** Both CLIs use only the Python standard library — no `pip
  install`, no API keys. Lowers the barrier for non-developer job seekers and avoids a
  dependency-rot surface. Trade-off: HTML parsing is regex-based rather than using a parser
  library (acceptable for these small, well-structured responses; see fragility note).
- **LinkedIn is opt-in and loudly flagged.** LinkedIn's terms prohibit automated access.
  Because this repo is public and name-attached, LinkedIn support is: (a) disabled by default
  in `/scrape` (only runs on explicit `/scrape linkedin`), (b) warned about on every CLI run
  (stderr), and (c) documented as at-your-own-risk in the tool README, main README, and
  INSTALL. SEEK is positioned as the primary, supported source. A reviewer should sanity-check
  whether this posture is sufficient or whether LinkedIn should be removed entirely.
- **Privacy footgun called out explicitly.** The profile files (`CLAUDE.md` and
  `.claude/skills/job-application-assistant/*.md`) are git-**tracked**, inherited from
  upstream. After `/setup` fills them with real data they appear as normal modified files, so
  a user with a public fork could push their own PII. `.gitignore` covers resume/`documents/`/
  search-state/PDFs, but NOT these. `INSTALL.md → Keeping your data private` documents a
  `git update-index --skip-worktree` mitigation. A cleaner long-term fix (move personal data
  into a gitignored `profile.local`) is noted as a possible improvement.

## Known fragilities / maintenance

- **The SEEK and LinkedIn endpoints are unofficial.** If they change shape, the tools break.
  Each tool's README documents exactly what to update (`API`/`GRAPHQL`/`_DETAIL_QUERY` and the
  `normalize`/`fetch_detail` functions for SEEK; the regexes for LinkedIn). Last verified:
  2026-06.
- **Regex HTML parsing** for LinkedIn cards/descriptions is inherently brittle to markup
  changes. Considered acceptable to keep the zero-dependency property; a contributor could
  swap in `selectolax`/`beautifulsoup4` behind an optional extra if desired.
- **Rate limiting.** LinkedIn rate-limits aggressively; the tool sleeps 1s/page and surfaces
  HTTP errors as likely rate-limit signals. SEEK GraphQL can return `RATE_LIMITED` as an
  HTTP-200 body error.

## Attribution

- Upstream framework: [Mads Lorentzen](https://github.com/MadsLorentzen) (MIT — LICENSE preserved).
- Original job-search skill pattern: [Mikkel Krogholm](https://github.com/mikkelkrogsholm).
- SEEK API approach: [qinscode/SeekSpider](https://github.com/qinscode/SeekSpider).
