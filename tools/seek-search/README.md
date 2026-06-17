# seek-search — SEEK (Australia) job search CLI

The Australian discovery engine for this framework. `/scrape` uses it to find real postings;
`/apply` uses it to pull a posting's full description.

## Why this exists

SEEK's HTML pages are Cloudflare-blocked (every `WebFetch`/`WebSearch` attempt to open a
posting returns HTTP 403). But SEEK's underlying **JSON and GraphQL APIs** return full
structured data with nothing more than a browser `User-Agent`. This CLI queries them
directly — no headless browser, no API key.

Approach adapted from [qinscode/SeekSpider](https://github.com/qinscode/SeekSpider), reduced
to a single zero-dependency Python script (no Scrapy / Postgres / OpenAI / web UI).

## Requirements

- Python 3.10+. **No pip install needed** — standard library only.

## Usage

```bash
cd tools/seek-search

# Search Brisbane AI Engineer roles (JSON output for the /scrape workflow)
python3 seek_search.py --keywords "AI Engineer" --where "All Brisbane QLD" --pages 2

# Remote/hybrid only, Australia-wide
python3 seek_search.py --keywords "Senior Full Stack Engineer" --where "All Australia" --remote --pages 3

# Human-readable table
python3 seek_search.py --keywords "Founding Engineer" --where "All Australia" --table

# Fetch ONE job's FULL description (by id or URL) — for /apply
python3 seek_search.py --detail "https://www.seek.com.au/job/12345678"
python3 seek_search.py --detail 12345678 --table
```

## Two endpoints, two modes

| Mode | SEEK endpoint | Returns |
|------|---------------|---------|
| Search (`--keywords`) | `/api/jobsearch/v5/search` (JSON) | List of jobs with teaser + metadata |
| Detail (`--detail`) | `/graphql` `jobDetails(id:)` (GraphQL) | One job's **full description** + salary, advertiser, status, recruiter phone |

Both work with only a browser `User-Agent` — neither is Cloudflare-blocked (the HTML
`/job/<id>` pages are). `--detail` accepts a numeric id or any seek.com.au job URL and
converts the description HTML to plain text, ready to feed straight into `/apply`.

### Arguments

| Flag | Default | Meaning |
|------|---------|---------|
| `--keywords` | — | Search terms, e.g. `"AI Engineer"`, `"Solutions Architect"` |
| `--where` | `All Brisbane QLD` | SEEK location string, e.g. `"All Sydney NSW"`, `"All Australia"` |
| `--pages` | `2` | Result pages to fetch (20 jobs/page) |
| `--remote` | off | Keep only roles whose arrangement/teaser indicate remote or hybrid |
| `--detail` | — | Fetch one job's full description by id or URL (GraphQL) |
| `--table` | off | Print a human table instead of JSON |

### Search output fields (JSON)

`id`, `title`, `company`, `location`, `salary`, `work_type`, `work_arrangement`
(Remote/Hybrid/On-site), `listing_date`, `teaser`, `bullet_points`, `url`, `query`.

### Detail output fields (JSON)

`id`, `title`, `company`, `advertiser_verified`, `location`, `salary`, `work_type`,
`classification`, `status`, `is_expired`, `expires_at`, `recruiter_phone`, `abstract`,
`description` (full, plain text), `url`.

## Known limitations

- Both endpoints are **unofficial**. If SEEK changes them, update the constants/queries in
  `seek_search.py`: `API` + `normalize()` for search, `GRAPHQL` + `_DETAIL_QUERY` +
  `fetch_detail()` for detail. GraphQL introspection is disabled, so the detail field set is
  fixed by hand. Last verified working: 2026-06.
- Salary is only present when the advertiser published it (many AU posts hide it).
- GraphQL may return `rate_limited` under heavy use — space out `--detail` calls if so.
