---
name: job-scraper
description: >
  Searches ATS boards (Greenhouse, Lever, Ashby, Workday, and similar) via Google
  site: dorks, with SEEK as an opt-in backup, for new positions matching your profile.
  Deduplicates across runs.
  Triggers on: job scrape, find jobs, search jobs, new jobs, job search, scrape jobs, /scrape
---

# Job Scraper (Australian market)

---

## How It Works

This skill discovers Australian job postings using two channels:

1. **ATS boards — primary.** `tools/ats_dorks.py` builds three Google `site:` queries
   (wide / enterprise / startup) from `search-queries.md`. Run each query with
   `WebSearch`. SEEK HTML is Cloudflare-blocked; ATS result links are usually fetchable.
   (`WebSearch` is US-region, so verify AU-eligibility before presenting.)
2. **SEEK — opt-in backup.** The `seek-search` CLI (`tools/seek-search/seek_search.py`)
   queries SEEK's JSON API. Only run it when the user said `seek` or `broad`.

It then deduplicates against previously seen jobs and the application tracker, and presents
new matches with a quick fit assessment.

Daily digest is a **separate** unattended path (`tools/daily_digest.py`): SEEK +
`preferred_companies` careers boards, plus the same ATS dorks as this skill when
`BRAVE_SEARCH_API_KEY` is set (Brave Search, not WebSearch). Do not enable it from
this skill.

## Invocation

Triggered by: "Find new jobs", "Scrape for jobs", "Any new positions?", "/scrape".

Optional arguments:
- A focus area, e.g. "/scrape ai" or "/scrape full stack" — extra role noun in the dorks
- "seek" or "broad" — also run the SEEK CLI backup
- "remote" — drop city tokens from the dorks; keep remote/hybrid only
- "linkedin" to ALSO query LinkedIn (opt-in only — see Step 2b; off by default for ToS reasons)

---

## Execution Steps

### Step 0: Load State

1. Read `job_scraper/seen_jobs.json` (create if missing — start with `{"seen": {}}`)
2. Read `job_search_tracker.csv` to extract already-applied companies+roles
3. Run the dork builder (do not invent Google OR-syntax):

```bash
python3 tools/ats_dorks.py
# /scrape remote:
python3 tools/ats_dorks.py --remote
# /scrape <focus>:
python3 tools/ats_dorks.py --extra-noun "<focus>"
```

   The JSON includes `dorks` (one query per tier), `nouns`, and `seek_locations`.
4. Read the candidate profile (`skills/job-application-assistant/01-candidate-profile.md` and `04-job-evaluation.md`) to ground the fit assessment in Step 4
5. Read `search-queries.md` (this directory) for fit filters (location, salary, recency)

### Step 1: Search ATS boards (primary)

For each object in `dorks`, run **one** `WebSearch` with that `query`.

- Only `WebFetch` a result if it looks like a strong match **and** is not a SEEK URL
  (SEEK HTML 403s). Prefer the employer's ATS posting URL.
- Verify Australia-eligibility before presenting — many board results are US-only.
- Pre-filter on title/snippet; do not fetch every hit.
- Do not run Wellfound / Y Combinator searches; the three ATS tiers replace them.

### Step 1b: Search SEEK (opt-in backup)

**Skip this step** unless the user said `seek` or `broad`.

For each role noun in the dork JSON, run the CLI against the SEEK locations
(`All Australia` with `--remote`):

```bash
cd tools/seek-search
python3 seek_search.py --keywords "<role noun>" --where "<location>" --pages 2
python3 seek_search.py --keywords "<role noun>" --where "All Australia" --remote --pages 2
# repeat/weekly runs:
python3 seek_search.py --keywords "<role noun>" --where "<location>" --days 14 --pages 2
```

- Run the CLI via a **shell command**. It prints a JSON array — parse it directly.
- Batch the keyword calls; each is fast.

### Step 2b: LinkedIn (OPT-IN ONLY — never run by default)

Only run this if the user explicitly opted in (said "linkedin", "/scrape linkedin", or asked
for LinkedIn). **Do not query LinkedIn otherwise** — automating it is against LinkedIn's ToS,
so it is off by default. When opted in, briefly remind the user it's at-their-own-risk, then:

```bash
cd tools/linkedin-search
python3 linkedin_search.py --keywords "<role title>" --where "Australia" --days 30
```

Keep volume low (a few keyword calls). Merge LinkedIn results into the same dedup/ranking as
ATS/SEEK. For a full description or `/apply`, use `linkedin_search.py --detail <id|url>`.

### Step 3: Deduplicate

For every job from Steps 1–2b:
- Skip if its id/URL or `company+title` key already exists in `seen_jobs.json`.
- Skip if the `company+role` already appears in `job_search_tracker.csv`.

### Step 4: Quick Fit Assessment

For each NEW job, do a rapid fit check against the candidate profile (NOT the full
`04-job-evaluation.md` pass — just a signal). Use title, snippet/teaser, salary,
location, and work arrangement:

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
    "<id_or_company_title_key>": {
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

To evaluate or apply to a SEEK result, fetch its full description first (search only
returns a teaser):
```bash
cd tools/seek-search && python3 seek_search.py --detail "<seek url or id>"
```
Then run the **job-application-assistant** workflow (or `/apply`) on that full description.

For an ATS URL, `WebFetch` the posting (or paste) before `/apply`.

### Step 7: Update Tracker (Optional)

If the user decides to apply, add a row to `job_search_tracker.csv`.

---

## Important Rules

1. **Never fabricate job postings.** Only present jobs returned by WebSearch, the SEEK CLI,
   or actual fetched pages.
2. **Respect deduplication.** Always check `seen_jobs.json` AND `job_search_tracker.csv` first.
3. **Location filter.** Honour the candidate's configured location tiers; skip on-site-only
   roles outside their city unless the user opts in.
4. **Only open positions.** Skip anything clearly stale or expired.
5. **Full SEEK descriptions ARE fetchable** via `seek_search.py --detail <id|url>` (GraphQL).
   ATS postings: fetch the non-SEEK URL. No manual paste needed when the fetch works.
6. **Efficiency.** One WebSearch per dork; don't WebFetch every result — pre-filter on
   title/snippet first. Do not invent dork syntax; run `tools/ats_dorks.py`.
