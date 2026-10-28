#!/usr/bin/env python3
"""Brave Search API helper for digest ATS dorks.

Optional unattended stand-in for Cursor WebSearch. Requires BRAVE_SEARCH_API_KEY.
Soft-fails per query so a downed API never aborts SEEK / careers collection.

Usage (library):
  from brave_search import search, hits_to_jobs, search_dorks
"""

from __future__ import annotations

import json
import re
import time
from hashlib import sha1
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

BRAVE_API = "https://api.search.brave.com/res/v1/web/search"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.4.1 Safari/605.1.15"
)

_SEEK_HOST = re.compile(r"(^|\.)seek\.com\.au$", re.I)
_AT_COMPANY = re.compile(
    r"\s+(?:@|at|[-–—]|[|])\s+(.+)$",
    re.I,
)
_LOC_TOKEN = re.compile(
    r"\b(melbourne|sydney|brisbane|perth|adelaide|canberra|hobart|darwin|"
    r"australia|remote|hybrid)\b",
    re.I,
)


def is_seek_url(url: str) -> bool:
    host = (urlparse(url).netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return bool(_SEEK_HOST.search(host))


def _guess_company(title: str, url: str) -> str:
    m = _AT_COMPANY.search(title or "")
    if m:
        name = m.group(1).strip().rstrip("|-–— ")
        if 1 < len(name) < 80:
            return name
    host = (urlparse(url).netloc or "").lower()
    # jobs.lever.co/<token>/... — token is often the company slug
    path = (urlparse(url).path or "").strip("/")
    parts = [p for p in path.split("/") if p]
    if "lever.co" in host and parts:
        slug = parts[0].replace("-", " ").strip()
        if slug and slug not in {"jobs", "view"}:
            return slug.title()
    if "greenhouse.io" in host and parts:
        return parts[0].replace("-", " ").title()
    if "ashbyhq.com" in host and parts:
        return parts[0].replace("-", " ").title()
    return ""


def _guess_location(title: str, description: str) -> str:
    blob = f"{title} {description}"
    found = []
    for m in _LOC_TOKEN.finditer(blob):
        token = m.group(1)
        pretty = token.title() if token.lower() != "australia" else "Australia"
        if pretty not in found:
            found.append(pretty)
    return ", ".join(found[:3])


def hits_to_jobs(hits: list[dict]) -> list[dict]:
    """Turn Brave web hits into digest job dicts. Drops SEEK URLs. Does not invent facts."""
    jobs: list[dict] = []
    seen_urls: set[str] = set()
    for hit in hits:
        url = (hit.get("url") or "").strip()
        title = (hit.get("title") or "").strip()
        if not url or not title:
            continue
        if is_seek_url(url):
            continue
        key = url.rstrip("/").lower()
        if key in seen_urls:
            continue
        seen_urls.add(key)
        desc = (hit.get("description") or hit.get("teaser") or "").strip()
        job_id = "ats-" + sha1(key.encode("utf-8")).hexdigest()[:12]
        jobs.append(
            {
                "id": job_id,
                "title": title,
                "company": _guess_company(title, url),
                "location": _guess_location(title, desc),
                "salary": "",
                "work_type": "",
                "work_arrangement": "",
                "listing_date": "",
                "teaser": desc[:400],
                "bullet_points": [],
                "url": url,
                "source": "ats-dork",
            }
        )
    return jobs


def search(query: str, api_key: str, count: int = 10) -> tuple[list[dict], str | None]:
    """Return (hits, error_note). hits items have title, url, description."""
    if not query.strip() or not (api_key or "").strip():
        return [], None
    params = urlencode({"q": query, "count": max(1, min(int(count), 20))})
    req = Request(
        f"{BRAVE_API}?{params}",
        headers={
            "Accept": "application/json",
            "User-Agent": UA,
            "X-Subscription-Token": api_key.strip(),
        },
    )
    try:
        with urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        return [], f"Brave HTTP {e.code}"
    except (URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
        return [], f"Brave error: {e}"

    results = ((body.get("web") or {}).get("results")) or []
    hits = []
    for item in results:
        if not isinstance(item, dict):
            continue
        hits.append(
            {
                "title": item.get("title") or "",
                "url": item.get("url") or "",
                "description": item.get("description") or "",
            }
        )
    return hits, None


def search_dorks(
    dorks: list[dict],
    api_key: str,
    *,
    count: int = 10,
    pause_s: float = 0.4,
) -> tuple[list[dict], list[str]]:
    """Run each {tier, query} dork. Returns (jobs, notes). Soft-fails per query."""
    jobs: list[dict] = []
    notes: list[str] = []
    for i, dork in enumerate(dorks):
        query = (dork.get("query") or "").strip()
        tier = dork.get("tier") or f"dork-{i+1}"
        if not query:
            continue
        hits, err = search(query, api_key, count=count)
        if err:
            notes.append(f"ATS dorks ({tier}): {err}")
            continue
        jobs.extend(hits_to_jobs(hits))
        if i + 1 < len(dorks) and pause_s > 0:
            time.sleep(pause_s)
    return jobs, notes
