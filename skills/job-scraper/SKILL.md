---
name: job-scraper
description: >
  Searches the Australian job market (SEEK via the seek-search CLI, plus startup boards
  via web search) for new positions matching your profile. Deduplicates across runs.
  Triggers on: job scrape, find jobs, search jobs, new jobs, job search, scrape jobs, /scrape
---

# Job Scraper (Australian market)

---

## How It Works

This skill discovers Australian job postings using two channels:

1. **SEEK — primary.** The `seek-search` CLI (`tools/seek-search/seek_search.py`) queries
   SEEK's JSON API directly and returns structured jobs (title, company, location, salary,
   remote/hybrid, teaser, URL). SEEK is the largest Australian board and its HTML pages are
   Cloudflare-blocked, so the CLI is the only reliable way in.
2. **Startup / ATS boards — secondary.** `WebSearch` over Wellfound, Y Combinator, and
   Greenhouse/Lever/Ashby for founding-engineer and AI-startup roles SEEK under-indexes.
   (`WebSearch` is US-region, so treat its AU results as supplementary and verify
   AU-eligibility before presenting.)

It then deduplicates against previously seen jobs and the application tracker, and presents
new matches with a quick fit assessment.

## Invocation

Triggered by: "Find new jobs", "Scrape for jobs", "Any new positions?", "/scrape".

Optional arguments:
- A focus area, e.g. "/scrape ai" or "/scrape full stack"
- "broad" to run all priority categories
- "remote" to hard-filter to remote/hybrid roles
- "linkedin" to ALSO query LinkedIn (opt-in only — see Step 2b; off by default for ToS reasons)

---

## Execution Steps

### Step 0: Load State

1. Read `job_scraper/seen_jobs.json` (create if missing — start with `{"seen": {}}`)
2. Read `job_search_tracker.csv` to extract already-applied companies+roles
3. Read `search-queries.md` (this directory) for the priority categories, role keywords, and `--where` locations
4. Read the candidate profile (`skills/job-application-assistant/01-candidate-profile.md` and `04-job-evaluation.md`) to ground the fit assessment in Step 4

### Step 1: Search SEEK (primary)

For each priority category in `search-queries.md`, run the CLI once per role-title keyword.
By default run the **top 3 priority categories**; if the user said "broad", run all. If the
user gave a focus area, prioritise that category's keywords.

```bash
cd tools/seek-search
python3 seek_search.py --keywords "<role title>" --where "<location>" --pages 2
# add --remote when the user asked for remote, or for an Australia-wide remote sweep:
python3 seek_search.py --keywords "<role title>" --where "All Australia" --remote --pages 2
# add --days N to limit to recent postings (e.g. --days 14 on a repeat/weekly run):
python3 seek_search.py --keywords "<role title>" --where "<location>" --days 14 --pages 2
```

- Run the CLI via a **shell command**. It prints a JSON array — parse it directly.
- Use the candidate's configured location tiers from `search-queries.md` for `--where`.
- Batch the keyword calls; each is fast.

### Step 2: Search startup boards (secondary, optional)

For founding-engineer / AI-startup coverage, run a few `WebSearch` queries over
`wellfound.com`, `workatastartup.com`, and `job-boards.greenhouse.io`. Only fetch a posting
with `WebFetch` if it looks like a strong match AND is not a SEEK URL (SEEK 403s). Verify
Australia-eligibility before presenting — many board results are US-only.

### Step 2b: LinkedIn (OPT-IN ONLY — never run by default)

Only run this if the user explicitly opted in (said "linkedin", "/scrape linkedin", or asked
for LinkedIn). **Do not query LinkedIn otherwise** — automating it is against LinkedIn's ToS,
so it is off by default. When opted in, briefly remind the user it's at-their-own-risk, then:

```bash
cd tools/linkedin-search
python3 linkedin_search.py --keywords "<role title>" --where "Australia" --days 30
```

Keep volume low (a few keyword calls). Merge LinkedIn results into the same dedup/ranking as
SEEK. For a full description or `/apply`, use `linkedin_search.py --detail <id|url>`.

### Step 3: Deduplicate

For every job from Steps 1–2:
- Skip if its SEEK `id`/URL or `company+title` key already exists in `seen_jobs.json`.
- Skip if the `company+role` already appears in `job_search_tracker.csv`.

### Step 4: Quick Fit Assessment

For each NEW job, do a rapid fit check against the candidate profile (NOT the full
`04-job-evaluation.md` pass — just a signal). Use the `teaser`, `title`, `salary`,
`work_arrangement`, and `bullet_points` the CLI returned:

- **High** — role directly hits the candidate's core skills AND location/remote works AND
  (if salary shown) it meets the candidate's salary expectation.
- **Medium** — adjacent role, or location/salary needs checking.
- **Low** — significant skill gap, or on-site outside the candidate's city with no remote.

Apply the location filter from `search-queries.md`.

### Step 5: Store

Add ALL surfaced jobs (new and skipped) to `seen_jobs.json`:
```json
{
  "seen": {
    "<seek_id_or_company_title_key>": {
      "title": "...", "company": "...", "location": "...", "url": "...",
      "salary": "...", "work_arrangement": "...",
      "first_seen": "YYYY-MM-DD", "fit": "high/medium/low", "status": "new/skipped/evaluated"
    }
  }
}
```

### Step 6: Present Results

Present new jobs in a table sorted by fit (high first):

```
## New Job Matches — YYYY-MM-DD

Found X new positions (Y high, Z medium, W low match).

| # | Fit | Title | Company | Location | Arrangement | Salary | URL |
|---|-----|-------|---------|----------|-------------|--------|-----|
| 1 | High | ... | ... | ... | Remote/Hybrid | ... | [Link](...) |

### High-Match Highlights
For each high-match job, add 2-3 bullets: why it matches, key requirements to check, any red flags.
```

After presenting, ask:
> "Want me to evaluate any of these in detail, or apply to one? Give me the number(s)."

To evaluate or apply to a SEEK result, fetch its full description first (the search step
only returns a teaser):
```bash
cd tools/seek-search && python3 seek_search.py --detail "<seek url or id>"
```
Then run the **job-application-assistant** workflow (or `/apply`) on that full description.

### Step 7: Update Tracker (Optional)

If the user decides to apply, add a row to `job_search_tracker.csv`.

---

## Important Rules

1. **Never fabricate job postings.** Only present jobs returned by the CLI or actual web results.
2. **Respect deduplication.** Always check `seen_jobs.json` AND `job_search_tracker.csv` first.
3. **Location filter.** Honour the candidate's configured location tiers; skip on-site-only
   roles outside their city unless the user opts in.
4. **Only open positions.** The CLI returns live listings; still skip anything clearly stale.
5. **Full SEEK descriptions ARE fetchable** via `seek_search.py --detail <id|url>` (GraphQL).
   The search step returns only a teaser; pull the full body with `--detail` before a full
   fit eval or `/apply`. No manual paste needed for SEEK URLs.
6. **Efficiency.** Batch CLI keyword calls; don't WebFetch every result — pre-filter on
   title/teaser/salary first.
