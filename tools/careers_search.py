#!/usr/bin/env python3
"""Fetch job listings from company careers / ATS board URLs.

Supports Greenhouse, Lever, and Ashby public JSON APIs, plus a best-effort
HTML fallback for generic careers pages. Soft-fails per company so one
blocked site never aborts a digest run.

Usage:
  python3 tools/careers_search.py --url "https://jobs.ashbyhq.com/acme" --json
  python3 tools/careers_search.py --config
  python3 tools/careers_search.py --url "..." --company "Acme" --keywords "engineer"
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from html import unescape
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
import ssl

ROOT = Path(__file__).resolve().parent.parent
DIGEST_CONFIG = ROOT / "config" / "digest.json"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.4.1 Safari/605.1.15"
)

# Import robots gate when available (same-repo stdlib tool).
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from robots_check import gate as robots_gate
except ImportError:  # pragma: no cover
    def robots_gate(url):  # type: ignore
        return 0, "ALLOWED - robots check unavailable"


def _ssl_context():
    """Build an SSL context that works on python.org macOS installs.

    Framework Python often ships without a populated CA bundle at
    ``…/etc/openssl/cert.pem``. Prefer certifi when available.
    """
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _http_get_json(url: str, timeout: int = 30) -> object:
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urlopen(req, timeout=timeout, context=_ssl_context()) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_get_text(url: str, timeout: int = 30) -> str:
    req = Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-AU,en;q=0.9",
        },
    )
    with urlopen(req, timeout=timeout, context=_ssl_context()) as resp:
        return resp.read().decode("utf-8", errors="replace")


def detect_ats(url: str) -> tuple[str, str]:
    """Return (ats_kind, board_token) from a careers / board URL."""
    parsed = urlparse(url.strip())
    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").strip("/")
    parts = [p for p in path.split("/") if p]

    if "greenhouse.io" in host or host.endswith("greenhouse.io"):
        # boards.greenhouse.io/<token> or job-boards.greenhouse.io/<token>
        token = parts[0] if parts else ""
        if token and token not in {"embed", "v1", "boards"}:
            return "greenhouse", token
    if "lever.co" in host:
        # jobs.lever.co/<company>
        token = parts[0] if parts else ""
        if token:
            return "lever", token
    if "ashbyhq.com" in host:
        # jobs.ashbyhq.com/<board>
        token = parts[0] if parts else ""
        if token:
            return "ashby", token
    if "smartrecruiters.com" in host:
        # jobs.smartrecruiters.com/<Company> or api.../companies/<Company>/postings
        token = ""
        if parts:
            if parts[0].lower() == "companies" and len(parts) > 1:
                token = parts[1]
            else:
                token = parts[0]
        if token:
            return "smartrecruiters", token
    return "html", ""


def _normalize_job(
    *,
    job_id: str,
    title: str,
    company: str,
    location: str = "",
    salary: str = "",
    teaser: str = "",
    url: str = "",
    source: str = "careers",
) -> dict:
    return {
        "id": str(job_id),
        "title": (title or "").strip(),
        "company": (company or "").strip(),
        "location": (location or "").strip(),
        "salary": (salary or "").strip(),
        "work_type": "",
        "work_arrangement": "",
        "listing_date": "",
        "teaser": (teaser or "").strip(),
        "bullet_points": [],
        "url": (url or "").strip(),
        "source": source,
    }


def fetch_greenhouse(token: str, company: str) -> list[dict]:
    api = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
    data = _http_get_json(api)
    jobs = []
    for item in data.get("jobs") or []:
        loc = ""
        locs = item.get("location") or {}
        if isinstance(locs, dict):
            loc = locs.get("name") or ""
        elif isinstance(locs, str):
            loc = locs
        jobs.append(
            _normalize_job(
                job_id=f"gh-{item.get('id', '')}",
                title=item.get("title", ""),
                company=company,
                location=loc,
                url=item.get("absolute_url") or "",
                source="careers-greenhouse",
            )
        )
    return jobs


def fetch_lever(token: str, company: str) -> list[dict]:
    api = f"https://api.lever.co/v0/postings/{token}?mode=json"
    data = _http_get_json(api)
    if not isinstance(data, list):
        return []
    jobs = []
    for item in data:
        cats = item.get("categories") or {}
        loc = cats.get("location") or item.get("workplaceType") or ""
        jobs.append(
            _normalize_job(
                job_id=f"lever-{item.get('id', '')}",
                title=item.get("text") or item.get("title") or "",
                company=company,
                location=loc if isinstance(loc, str) else "",
                teaser=(item.get("descriptionPlain") or "")[:400],
                url=item.get("hostedUrl") or item.get("applyUrl") or "",
                source="careers-lever",
            )
        )
    return jobs


def fetch_ashby(token: str, company: str) -> list[dict]:
    api = f"https://api.ashbyhq.com/posting-api/job-board/{token}"
    data = _http_get_json(api)
    jobs = []
    for item in data.get("jobs") or []:
        loc = item.get("location") or ""
        if isinstance(loc, dict):
            loc = loc.get("name") or loc.get("location") or ""
        jobs.append(
            _normalize_job(
                job_id=f"ashby-{item.get('id', '')}",
                title=item.get("title", ""),
                company=company,
                location=loc if isinstance(loc, str) else "",
                url=item.get("jobUrl") or item.get("applyUrl") or "",
                source="careers-ashby",
            )
        )
    return jobs


def fetch_smartrecruiters(token: str, company: str) -> list[dict]:
    """Paginate SmartRecruiters public postings API."""
    jobs = []
    offset = 0
    limit = 100
    while True:
        api = (
            f"https://api.smartrecruiters.com/v1/companies/{token}/postings"
            f"?limit={limit}&offset={offset}"
        )
        data = _http_get_json(api)
        batch = data.get("content") or []
        if not batch:
            break
        for item in batch:
            loc = ""
            location = item.get("location") or {}
            if isinstance(location, dict):
                loc = location.get("fullLocation") or location.get("city") or ""
            pid = item.get("id") or ""
            jobs.append(
                _normalize_job(
                    job_id=f"sr-{pid}",
                    title=item.get("name") or "",
                    company=company,
                    location=loc if isinstance(loc, str) else "",
                    url=f"https://jobs.smartrecruiters.com/{token}/{pid}",
                    source="careers-smartrecruiters",
                )
            )
        total = int(data.get("totalFound") or 0)
        offset += limit
        if offset >= total or len(batch) < limit:
            break
        if offset > 500:  # safety cap
            break
    return jobs


_JOB_HREF = re.compile(
    r'href=["\']([^"\']*(?:job|jobs|career|position|opening|posting)[^"\']*)["\']',
    re.I,
)
_TITLE_NEAR = re.compile(
    r"(?:>([^<]{8,120})</a>)",
    re.I,
)


def fetch_html(url: str, company: str) -> list[dict]:
    """Best-effort extraction of job links from a generic careers HTML page."""
    rc, _msg = robots_gate(url)
    if rc != 0:
        raise RuntimeError(f"robots.txt blocks fetch for {url}")

    html = _http_get_text(url)
    seen = set()
    jobs = []
    for m in _JOB_HREF.finditer(html):
        href = unescape(m.group(1).strip())
        if href.startswith("#") or href.startswith("mailto:"):
            continue
        full = urljoin(url, href)
        if full in seen:
            continue
        # Skip pure navigation
        path = urlparse(full).path.lower()
        if path.rstrip("/") in ("", "/jobs", "/careers", "/career"):
            continue
        seen.add(full)
        # Try to find link text after the href
        snippet = html[m.end() : m.end() + 200]
        title_m = _TITLE_NEAR.search(snippet)
        title = unescape(title_m.group(1)).strip() if title_m else Path(urlparse(full).path).name.replace("-", " ")
        title = re.sub(r"\s+", " ", title)
        if len(title) < 4:
            continue
        jobs.append(
            _normalize_job(
                job_id=f"html-{abs(hash(full)) % (10**12)}",
                title=title,
                company=company,
                url=full,
                source="careers-html",
            )
        )
        if len(jobs) >= 80:
            break
    return jobs


def filter_by_keywords(jobs: list[dict], keywords: list[str]) -> list[dict]:
    """Keep jobs whose title overlaps any keyword token (case-insensitive)."""
    if not keywords:
        return jobs
    tokens = set()
    for kw in keywords:
        for t in re.findall(r"[a-z0-9+#.]{2,}", kw.lower()):
            if t not in {"and", "the", "for", "with", "all"}:
                tokens.add(t)
    if not tokens:
        return jobs
    out = []
    for job in jobs:
        title = (job.get("title") or "").lower()
        if any(t in title for t in tokens):
            out.append(job)
    return out


def fetch_careers(
    url: str,
    company: str = "",
    keywords: list[str] | None = None,
) -> list[dict]:
    """Fetch and normalize jobs for one careers URL. Raises on hard failure."""
    company = company or "Unknown"
    ats, token = detect_ats(url)
    if ats == "greenhouse":
        jobs = fetch_greenhouse(token, company)
    elif ats == "lever":
        jobs = fetch_lever(token, company)
    elif ats == "ashby":
        jobs = fetch_ashby(token, company)
    elif ats == "smartrecruiters":
        jobs = fetch_smartrecruiters(token, company)
    else:
        jobs = fetch_html(url, company)
    return filter_by_keywords(jobs, keywords or [])


def load_preferred_companies(path: Path | None = None) -> list[dict]:
    cfg_path = path or DIGEST_CONFIG
    if not cfg_path.is_file():
        return []
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    companies = data.get("preferred_companies") or []
    out = []
    for item in companies:
        if isinstance(item, str):
            out.append({"name": item, "careers_url": "", "aliases": []})
        elif isinstance(item, dict) and item.get("name"):
            out.append(
                {
                    "name": item["name"],
                    "careers_url": (item.get("careers_url") or "").strip(),
                    "aliases": list(item.get("aliases") or []),
                }
            )
    return out


def fetch_all_from_config(
    keywords: list[str] | None = None,
    config_path: Path | None = None,
) -> tuple[list[dict], list[str]]:
    """Fetch careers jobs for every preferred company with a careers_url.

    Returns (jobs, errors). Soft-fails per company.
    """
    jobs: list[dict] = []
    errors: list[str] = []
    for company in load_preferred_companies(config_path):
        url = company.get("careers_url") or ""
        if not url:
            continue
        name = company["name"]
        try:
            found = fetch_careers(url, company=name, keywords=keywords)
            jobs.extend(found)
        except (HTTPError, URLError, RuntimeError, json.JSONDecodeError, TimeoutError, OSError) as exc:
            errors.append(f"{name}: {exc}")
    return jobs, errors


def main() -> None:
    ap = argparse.ArgumentParser(description="Search company careers / ATS boards.")
    ap.add_argument("--url", help="Single careers or ATS board URL")
    ap.add_argument("--company", default="", help="Company name for output rows")
    ap.add_argument("--config", action="store_true", help="Load preferred companies from config/digest.json")
    ap.add_argument("--keywords", default="", help="Comma-separated title filter keywords")
    ap.add_argument("--json", action="store_true", help="JSON output (default)")
    ap.add_argument("--table", action="store_true", help="Human-readable table")
    args = ap.parse_args()

    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()] if args.keywords else []

    jobs: list[dict] = []
    errors: list[str] = []

    if args.config:
        jobs, errors = fetch_all_from_config(keywords=keywords)
    elif args.url:
        try:
            jobs = fetch_careers(args.url, company=args.company or "Unknown", keywords=keywords)
        except Exception as exc:
            print(f"[careers-search] {exc}", file=sys.stderr)
            sys.exit(1)
    else:
        ap.error("provide --url or --config")

    for err in errors:
        print(f"[careers-search] skip: {err}", file=sys.stderr)

    if args.table:
        if not jobs:
            print("No jobs found.")
            return
        for i, j in enumerate(jobs, 1):
            print(f"{i}. {j['title']}  —  {j['company']}")
            meta = "  ".join(filter(None, [j.get("location"), j.get("salary"), j.get("source")]))
            if meta:
                print(f"   {meta}")
            print(f"   {j['url']}")
        return

    json.dump(jobs, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
