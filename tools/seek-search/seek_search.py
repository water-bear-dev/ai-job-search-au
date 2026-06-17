#!/usr/bin/env python3
"""
seek-search — lightweight SEEK (seek.com.au) job search CLI for the Australian market.

Adapted from the API technique in qinscode/SeekSpider, but stripped to a single
zero-dependency script (Python stdlib only — no Scrapy / Postgres / OpenAI).
It queries SEEK's public JSON search API, which returns structured job data with a
plain browser User-Agent (the HTML pages are Cloudflare-blocked, the API is not).

The /scrape skill calls this to discover real postings and ranks them against the
candidate profile; /apply uses --detail to pull a posting's full description.

Usage:
  python3 seek_search.py --keywords "AI Engineer" --where "All Brisbane QLD" --pages 2
  python3 seek_search.py --keywords "Senior Full Stack" --remote --pages 3
  python3 seek_search.py --keywords "Founding Engineer" --where "All Australia" --table
  python3 seek_search.py --detail https://www.seek.com.au/job/12345678

Output: JSON array of jobs on stdout (default), or a human table with --table.
"""

import argparse
import json
import re
import sys
import time
from html import unescape
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

API = "https://www.seek.com.au/api/jobsearch/v5/search"
GRAPHQL = "https://www.seek.com.au/graphql"
JOB_URL = "https://www.seek.com.au/job/"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.4.1 Safari/605.1.15"
)


def fetch_page(keywords, where, page):
    params = {
        "siteKey": "AU-Main",
        "sourcesystem": "houston",
        "where": where,
        "page": page,
        "keywords": keywords,
        "locale": "en-AU",
        "include": "seodata",
    }
    url = f"{API}?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def normalize(job):
    """Flatten a SEEK API job record into the fields /scrape and /apply care about."""
    company = job.get("companyName") or (job.get("advertiser") or {}).get("description", "")
    locations = job.get("locations") or [{}]
    work_types = job.get("workTypes") or [""]
    arrangement = ((job.get("workArrangements") or {}).get("displayText")) or ""
    return {
        "id": str(job.get("id", "")),
        "title": job.get("title", ""),
        "company": company,
        "location": locations[0].get("label", ""),
        "salary": job.get("salaryLabel", ""),
        "work_type": work_types[0],
        "work_arrangement": arrangement,  # Remote / Hybrid / On-site
        "listing_date": job.get("listingDate", ""),
        "teaser": (job.get("teaser") or "").strip(),
        "bullet_points": job.get("bulletPoints") or [],
        "url": JOB_URL + str(job.get("id", "")),
    }


def is_remote_or_hybrid(job):
    arr = (job.get("work_arrangement") or "").lower()
    loc = (job.get("location") or "").lower()
    blob = " ".join([arr, loc, job.get("teaser", "").lower(), " ".join(job.get("bullet_points", [])).lower()])
    return any(k in blob for k in ("remote", "hybrid", "work from home", "wfh"))


def search(keywords, where, pages, remote_only):
    seen = set()
    out = []
    for page in range(1, pages + 1):
        try:
            data = fetch_page(keywords, where, page)
        except HTTPError as e:
            print(f"[seek-search] HTTP {e.code} on page {page} for '{keywords}'", file=sys.stderr)
            break
        except URLError as e:
            print(f"[seek-search] network error: {e.reason}", file=sys.stderr)
            break
        records = data.get("data", [])
        if not records:
            break
        total = data.get("totalCount", 0)
        page_size = (data.get("solMetadata") or {}).get("pageSize", 20)
        for r in records:
            j = normalize(r)
            if j["id"] in seen:
                continue
            seen.add(j["id"])
            if remote_only and not is_remote_or_hybrid(j):
                continue
            j["query"] = keywords
            out.append(j)
        # stop early if we've consumed all pages of results
        if page * page_size >= total:
            break
        time.sleep(0.4)  # be polite to SEEK
    return out


_JOBID_RE = re.compile(r"(?:/job/|jobId=|/)(\d{6,})")

# GraphQL query for a single job's full detail. Fields verified against SEEK's
# schema (introspection is disabled, so the field set is fixed here).
_DETAIL_QUERY = (
    "query jobDetails($jobId: ID!) { "
    "jobDetails(id: $jobId) { job { "
    "id title abstract content(platform: WEB) status isExpired phoneNumber "
    "expiresAt { dateTimeUtc } "
    "salary { label } "
    "workTypes { label } "
    "advertiser { id name isVerified } "
    "location { label } "
    'classifications { label(languageCode: "en") } '
    "} } }"
)


def extract_job_id(value):
    """Accept a raw job id or any seek.com.au job URL and return the numeric id."""
    value = value.strip()
    if value.isdigit():
        return value
    m = _JOBID_RE.search(value)
    return m.group(1) if m else None


def html_to_text(html):
    """Convert SEEK's description HTML to readable plain text (stdlib only)."""
    if not html:
        return ""
    text = re.sub(r"(?i)<\s*(br|/p|/li|/div|/h[1-6])\s*>", "\n", html)
    text = re.sub(r"(?i)<\s*li[^>]*>", "\n- ", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text.strip()


def fetch_detail(job_id):
    """Fetch full job detail via SEEK's GraphQL API (not Cloudflare-blocked)."""
    payload = json.dumps(
        {"operationName": "jobDetails", "variables": {"jobId": str(job_id)}, "query": _DETAIL_QUERY}
    ).encode("utf-8")
    req = Request(
        GRAPHQL,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json", "User-Agent": UA},
    )
    with urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    if body.get("errors"):
        raise RuntimeError(body["errors"][0].get("message", "GraphQL error"))
    job = ((body.get("data") or {}).get("jobDetails") or {}).get("job")
    if not job:
        return None
    return {
        "id": job.get("id", ""),
        "title": job.get("title", ""),
        "company": (job.get("advertiser") or {}).get("name", ""),
        "advertiser_verified": (job.get("advertiser") or {}).get("isVerified"),
        "location": (job.get("location") or {}).get("label", ""),
        "salary": (job.get("salary") or {}).get("label", ""),
        "work_type": (job.get("workTypes") or {}).get("label", ""),
        "classification": "; ".join(c.get("label", "") for c in (job.get("classifications") or [])),
        "status": job.get("status", ""),
        "is_expired": job.get("isExpired"),
        "expires_at": (job.get("expiresAt") or {}).get("dateTimeUtc", ""),
        "recruiter_phone": job.get("phoneNumber") or "",
        "abstract": job.get("abstract", ""),
        "description": html_to_text(job.get("content", "")),
        "url": JOB_URL + str(job.get("id", "")),
    }


def print_table(jobs):
    if not jobs:
        print("No jobs found.")
        return
    for i, j in enumerate(jobs, 1):
        line = f"{i}. {j['title']}  —  {j['company']}"
        meta = "  ".join(filter(None, [j["location"], j["work_arrangement"], j["salary"], j["work_type"]]))
        print(line)
        if meta:
            print(f"   {meta}")
        print(f"   {j['url']}")
        if j["teaser"]:
            print(f"   {j['teaser'][:140]}")
        print()


def main():
    ap = argparse.ArgumentParser(description="Search seek.com.au for jobs (Australian market).")
    ap.add_argument("--keywords", help='Search terms, e.g. "AI Engineer"')
    ap.add_argument("--where", default="All Brisbane QLD",
                    help='SEEK location, e.g. "All Brisbane QLD", "All Sydney NSW", "All Australia" (default: All Brisbane QLD)')
    ap.add_argument("--pages", type=int, default=2, help="Number of result pages to fetch (20/page). Default 2.")
    ap.add_argument("--remote", action="store_true", help="Keep only remote/hybrid roles.")
    ap.add_argument("--detail", metavar="ID_OR_URL",
                    help="Fetch ONE job's full description by SEEK job id or job URL (uses the GraphQL API).")
    ap.add_argument("--table", action="store_true", help="Human-readable output instead of JSON.")
    args = ap.parse_args()

    # Detail mode: resolve a single posting's full description (for /apply).
    if args.detail:
        job_id = extract_job_id(args.detail)
        if not job_id:
            print(f"[seek-search] couldn't extract a job id from '{args.detail}'", file=sys.stderr)
            sys.exit(2)
        try:
            job = fetch_detail(job_id)
        except (HTTPError, URLError, RuntimeError) as e:
            print(f"[seek-search] detail fetch failed for {job_id}: {e}", file=sys.stderr)
            sys.exit(1)
        if not job:
            print(f"[seek-search] job {job_id} not found (may be expired/removed)", file=sys.stderr)
            sys.exit(1)
        if args.table:
            print(f"{job['title']}  —  {job['company']}"
                  f"{'  ✓verified' if job['advertiser_verified'] else ''}")
            meta = "  ".join(filter(None, [job["location"], job["salary"], job["work_type"],
                                           job["classification"], f"status: {job['status']}"]))
            print(meta)
            if job["recruiter_phone"]:
                print(f"Recruiter phone: {job['recruiter_phone']}")
            print(f"{job['url']}\n")
            print(job["description"])
        else:
            json.dump(job, sys.stdout, indent=2, ensure_ascii=False)
            sys.stdout.write("\n")
        return

    if not args.keywords:
        ap.error("provide --keywords for a search, or --detail <id|url> for one job's full description")

    jobs = search(args.keywords, args.where, args.pages, args.remote)

    if args.table:
        print_table(jobs)
    else:
        json.dump(jobs, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")


if __name__ == "__main__":
    main()
