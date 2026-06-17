# Search Queries for Job Scraper

<!-- TEMPLATE — customise for your roles and location. Run /setup --section search to fill this. -->
<!-- PRIMARY discovery = the seek-search CLI (tools/seek-search/seek_search.py). -->

## How /scrape uses this file

For each priority category below, the `job-scraper` skill runs the SEEK CLI once per
role-title keyword:

```bash
cd tools/seek-search
python3 seek_search.py --keywords "<role title>" --where "<location>" --pages 2
# remote/hybrid Australia-wide sweep:
python3 seek_search.py --keywords "<role title>" --where "All Australia" --remote --pages 2
```

It also runs a few secondary `WebSearch` queries (Section: Startup boards) for
founding-engineer roles SEEK under-indexes.

## Locations (`--where` values)

SEEK location strings look like `All <City> <STATE>`. Set your tiers:

- `All [YOUR_CITY] [STATE]` — ideal (home base), e.g. `All Brisbane QLD`
- `All Australia` paired with `--remote` — remote/hybrid Australia-wide
- `All Sydney NSW`, `All Melbourne VIC` — only for strongly-matched remote/hybrid roles

Common SEEK location strings: `All Sydney NSW`, `All Melbourne VIC`, `All Brisbane QLD`,
`All Perth WA`, `All Adelaide SA`, `All Canberra ACT`, `All Hobart TAS`, `All Darwin NT`.

## Priority Categories (role-title keywords for the CLI)

Replace these with your own target roles. Order by how much you want each.

### Priority 1: [YOUR_PRIMARY_ROLE_TYPE]  *(strongest direction)*
```
[PRIMARY_JOB_TITLE_1]
[PRIMARY_JOB_TITLE_2]
[PRIMARY_KEY_SKILL]
```

### Priority 2: [YOUR_SECONDARY_ROLE_TYPE]
```
[SECONDARY_JOB_TITLE_1]
[SECONDARY_JOB_TITLE_2]
```

### Priority 3: [YOUR_ADJACENT_ROLE_TYPE]  *(roles you could pivot into)*
```
[ADJACENT_JOB_TITLE_1]
[ADJACENT_JOB_TITLE_2]
```

### Priority 4: [BROADER_ROLE_TYPE]  *(wider net)*
```
[BROAD_JOB_TITLE_1]
[BROAD_JOB_TITLE_2]
```

## Startup boards (secondary — WebSearch, not SEEK)

For founding-engineer / AI-startup roles, run a few of these and verify AU-eligibility:
```
site:wellfound.com founding engineer Australia
site:workatastartup.com (AI OR full stack) engineer Australia remote
"founding engineer" OR "[YOUR_KEY_SKILL]" Australia remote startup
```

## Fit filters

- **Location:** keep [YOUR_CITY] (any arrangement) + remote/hybrid Australia. Drop
  on-site-only roles outside [YOUR_CITY] unless you opt in.
- **Salary:** target [YOUR_SALARY_EXPECTATION]. Flag roles in or above that band; don't
  auto-reject roles that hide salary (most AU posts do).
- **Recency:** prefer `listing_date` within the last ~21 days; flag older ones.

## Adapting on focus

- `/scrape <focus>` → that category's keywords + 2-3 custom focus terms.
- `/scrape remote` → all categories with `--where "All Australia" --remote`.
- `/scrape <city>` → run with `--where "All <City> STATE"`.
