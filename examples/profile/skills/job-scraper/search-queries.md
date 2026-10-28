# Search Queries for Job Scraper

<!-- TEMPLATE — customise for your roles and location. Run /setup --section search to fill this. -->
<!-- PRIMARY discovery = ATS Google dorks via tools/ats_dorks.py. SEEK is opt-in (`/scrape seek`). -->

## How /scrape uses this file

`/scrape` builds one Google `site:` dork per tier (do not hand-edit the dorks):

```bash
python3 tools/ats_dorks.py
# /scrape remote — drop city tokens, keep remote/hybrid:
python3 tools/ats_dorks.py --remote
```

Daily digest searches SEEK with the role nouns below, fetches
`preferred_companies` careers boards from `config/digest.json`, and runs the
same ATS dorks when `BRAVE_SEARCH_API_KEY` is set.

SEEK backup (`/scrape seek` or `/scrape broad`):

```bash
cd tools/seek-search
python3 seek_search.py --keywords "<role noun>" --where "<SEEK location>" --pages 2
python3 seek_search.py --keywords "<role noun>" --where "All Australia" --remote --pages 2
```

## Role nouns

Job titles a user would type, without seniority prefixes (those live under Tiers).
One noun per line. Lines containing `[` are placeholders and are ignored.

```
[YOUR_ROLE_NOUN_1]
[YOUR_ROLE_NOUN_2]
[YOUR_ROLE_NOUN_3]
```

## Tiers

Defaults below are the ATS-first recipe. Override prefixes or sites if needed.
Leave a **Prefixes** fence empty to search bare nouns only (quoted nouns already
match "Senior Data Engineer").

### wide

**Prefixes:**

```
# none — quoted role nouns already match "Senior Data Engineer"
```

**Sites:**

```
myworkdayjobs.com
greenhouse.io
lever.co
icims.com
ashbyhq.com
smartrecruiters.com
taleo.net
```

### enterprise

**Prefixes:**

```
Senior
Staff
Principal
```

**Sites:**

```
myworkdayjobs.com
icims.com
taleo.net
smartrecruiters.com
```

### startup

**Prefixes:**

```
Founding
Principal
Lead
```

**Sites:**

```
greenhouse.io
lever.co
ashbyhq.com
```

## SEEK locations

SEEK `--where` strings. Pattern: `All <City> <STATE>`, or `All Australia`.

```
All [YOUR_CITY] [STATE]
All Australia
```

Common strings: `All Sydney NSW`, `All Melbourne VIC`, `All Brisbane QLD`,
`All Perth WA`, `All Adelaide SA`, `All Canberra ACT`, `All Hobart TAS`,
`All Darwin NT`.

## ATS location tokens

OR-group appended to every dork: `(Melbourne OR Australia OR remote OR hybrid)`.
Leave the fence empty (or only placeholders) to omit the group.

```
[YOUR_CITY]
Australia
remote
hybrid
```

## Domain boost

Optional. Digest scoring only — never a hard filter. Empty is fine.

```
[YOUR_DOMAIN_1]
[YOUR_DOMAIN_2]
```

## Fit filters

- **Location:** keep [YOUR_CITY] (any arrangement) + remote/hybrid Australia. Drop
  on-site-only roles outside [YOUR_CITY] unless you opt in.
- **Salary:** target [YOUR_SALARY_EXPECTATION]. Flag roles in or above that band; don't
  auto-reject roles that hide salary (most AU posts do).
- **Recency:** prefer `listing_date` within the last ~21 days; flag older ones.

## Adapting on focus

- `/scrape` → three ATS dorks (wide / enterprise / startup).
- `/scrape seek` or `/scrape broad` → ATS dorks plus SEEK CLI backup.
- `/scrape <focus>` → extra role noun in the dorks for that run.
- `/scrape remote` → drop city tokens; keep remote/hybrid only.
- `/scrape linkedin` → ALSO query LinkedIn (opt-in; ToS risk).
