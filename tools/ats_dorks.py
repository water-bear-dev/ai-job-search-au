#!/usr/bin/env python3
"""Build ATS Google dorks from skills/job-scraper/search-queries.md.

/scrape runs this and WebSearches each query. Daily digest reuses parse_recipe()
and, when BRAVE_SEARCH_API_KEY is set, runs the same dorks via Brave Search.

Usage:
  python3 tools/ats_dorks.py
  python3 tools/ats_dorks.py --remote
  python3 tools/ats_dorks.py --extra-noun MLOps --extra-noun "Staff Engineer"
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RECIPE = ROOT / "skills" / "job-scraper" / "search-queries.md"

TIER_ORDER = ("wide", "enterprise", "startup")

DEFAULT_SITES = {
    "wide": [
        "myworkdayjobs.com",
        "greenhouse.io",
        "lever.co",
        "icims.com",
        "ashbyhq.com",
        "smartrecruiters.com",
        "taleo.net",
    ],
    "enterprise": [
        "myworkdayjobs.com",
        "icims.com",
        "taleo.net",
        "smartrecruiters.com",
    ],
    "startup": [
        "greenhouse.io",
        "lever.co",
        "ashbyhq.com",
    ],
}

DEFAULT_PREFIXES = {
    "wide": [],
    "enterprise": ["Senior", "Staff", "Principal"],
    "startup": ["Founding", "Principal", "Lead"],
}

_REMOTE_RE = re.compile(r"remote|hybrid|wfh|work from home", re.I)
_FENCE = re.compile(r"```(?:\w*)\n(.*?)```", re.S)
_HEADING = re.compile(r"^##\s+(.+?)\s*$", re.M)
_TIER_HEADING = re.compile(r"^###\s+(\w+)\s*$", re.M)


@dataclass
class Tier:
    name: str
    prefixes: list[str] = field(default_factory=list)
    sites: list[str] = field(default_factory=list)


@dataclass
class Recipe:
    nouns: list[str] = field(default_factory=list)
    tiers: list[Tier] = field(default_factory=list)
    seek_locations: list[str] = field(default_factory=list)
    ats_location_tokens: list[str] = field(default_factory=list)
    domain_boost: list[str] = field(default_factory=list)

    def all_prefixes(self) -> list[str]:
        seen: list[str] = []
        for tier in self.tiers:
            for prefix in tier.prefixes:
                if prefix not in seen:
                    seen.append(prefix)
        return seen


def _is_placeholder(line: str) -> bool:
    return "[" in line


def _fence_lines(block: str) -> list[str]:
    out: list[str] = []
    for raw in block.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or _is_placeholder(line):
            continue
        if line.startswith("site:") or " OR " in line:
            continue
        out.append(line)
    return out


def _section_body(text: str, heading: str) -> str:
    """Return text after `## heading` until the next `##` heading."""
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$", re.I | re.M)
    match = pattern.search(text)
    if not match:
        return ""
    rest = text[match.end() :]
    nxt = _HEADING.search(rest)
    return rest[: nxt.start()] if nxt else rest


def _first_fence_lines(section: str) -> list[str]:
    fence = _FENCE.search(section)
    if not fence:
        return []
    return _fence_lines(fence.group(1))


def _legacy_priority_nouns(text: str) -> list[str]:
    """Fallback for older search-queries.md files with ### Priority N blocks."""
    nouns: list[str] = []
    parts = re.split(r"^###\s+Priority\s+(\d+)", text, flags=re.M)
    for i in range(1, len(parts), 2):
        body = parts[i + 1] if i + 1 < len(parts) else ""
        for fence in _FENCE.finditer(body):
            for line in _fence_lines(fence.group(1)):
                if line not in nouns:
                    nouns.append(line)
    return nouns


def _parse_tiers(text: str) -> list[Tier]:
    body = _section_body(text, "Tiers")
    found: dict[str, Tier] = {}
    if body:
        chunks = _TIER_HEADING.split(body)
        # [preamble, name1, body1, name2, body2, ...]
        for i in range(1, len(chunks), 2):
            name = chunks[i].strip().lower()
            chunk = chunks[i + 1] if i + 1 < len(chunks) else ""
            fences = [_fence_lines(m.group(1)) for m in _FENCE.finditer(chunk)]
            prefixes = fences[0] if len(fences) > 0 else list(DEFAULT_PREFIXES.get(name, []))
            sites = fences[1] if len(fences) > 1 else list(DEFAULT_SITES.get(name, []))
            if name in TIER_ORDER:
                found[name] = Tier(name=name, prefixes=prefixes, sites=sites)

    tiers: list[Tier] = []
    for name in TIER_ORDER:
        if name in found:
            tier = found[name]
            if not tier.sites:
                tier.sites = list(DEFAULT_SITES[name])
            tiers.append(tier)
        else:
            tiers.append(
                Tier(
                    name=name,
                    prefixes=list(DEFAULT_PREFIXES[name]),
                    sites=list(DEFAULT_SITES[name]),
                )
            )
    return tiers


def parse_recipe(path: str | Path | None = None) -> Recipe:
    recipe_path = Path(path) if path else DEFAULT_RECIPE
    if not recipe_path.is_file():
        return Recipe(tiers=_parse_tiers(""))

    text = recipe_path.read_text(encoding="utf-8")
    nouns = _first_fence_lines(_section_body(text, "Role nouns"))
    if not nouns:
        nouns = _legacy_priority_nouns(text)

    seek_locations = _first_fence_lines(_section_body(text, "SEEK locations"))
    if not seek_locations:
        # Older files listed `All City STATE` inline.
        for match in re.finditer(r"`(All [^`]+)`", text):
            loc = match.group(1).strip()
            if loc not in seek_locations:
                seek_locations.append(loc)

    return Recipe(
        nouns=nouns,
        tiers=_parse_tiers(text),
        seek_locations=seek_locations,
        ats_location_tokens=_first_fence_lines(_section_body(text, "ATS location tokens")),
        domain_boost=_first_fence_lines(_section_body(text, "Domain boost")),
    )


def _or_group(items: list[str], quote: bool) -> str:
    if not items:
        return ""
    if quote:
        parts = [f'"{item}"' for item in items]
    else:
        parts = list(items)
    if len(parts) == 1:
        return parts[0]
    return "(" + " OR ".join(parts) + ")"


def location_tokens_for_run(tokens: list[str], remote_only: bool) -> list[str]:
    if not remote_only:
        return list(tokens)
    return [t for t in tokens if _REMOTE_RE.search(t)]


def build_dork(
    sites: list[str],
    nouns: list[str],
    prefixes: list[str] | None = None,
    location_tokens: list[str] | None = None,
) -> str:
    if not sites or not nouns:
        return ""
    hosts = []
    for site in sites:
        host = site.strip()
        if host.lower().startswith("site:"):
            host = host[5:]
        if host and host not in hosts:
            hosts.append(host)
    parts = [
        _or_group([f"site:{host}" for host in hosts], quote=False),
        _or_group(nouns, quote=True),
    ]
    prefix_group = _or_group(prefixes or [], quote=True)
    if prefix_group:
        parts.append(prefix_group)
    loc_group = _or_group(location_tokens or [], quote=False)
    if loc_group:
        parts.append(loc_group)
    return " ".join(parts)


def build_dorks(
    recipe: Recipe,
    *,
    extra_nouns: list[str] | None = None,
    remote_only: bool = False,
) -> list[dict[str, str]]:
    nouns = list(recipe.nouns)
    for extra in extra_nouns or []:
        extra = extra.strip()
        if extra and extra not in nouns:
            nouns.append(extra)
    locations = location_tokens_for_run(recipe.ats_location_tokens, remote_only)
    dorks: list[dict[str, str]] = []
    for tier in recipe.tiers:
        query = build_dork(tier.sites, nouns, tier.prefixes, locations)
        if query:
            dorks.append({"tier": tier.name, "query": query})
    return dorks


def recipe_payload(
    recipe: Recipe,
    *,
    extra_nouns: list[str] | None = None,
    remote_only: bool = False,
) -> dict:
    dorks = build_dorks(recipe, extra_nouns=extra_nouns, remote_only=remote_only)
    nouns = list(recipe.nouns)
    for extra in extra_nouns or []:
        extra = extra.strip()
        if extra and extra not in nouns:
            nouns.append(extra)
    return {
        "nouns": nouns,
        "seek_locations": recipe.seek_locations,
        "ats_location_tokens": location_tokens_for_run(
            recipe.ats_location_tokens, remote_only
        ),
        "domain_boost": recipe.domain_boost,
        "prefixes": recipe.all_prefixes(),
        "dorks": dorks,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Build ATS Google dorks from search-queries.md.")
    ap.add_argument("--path", default=str(DEFAULT_RECIPE), help="Path to search-queries.md")
    ap.add_argument(
        "--remote",
        action="store_true",
        help="Drop city tokens from the location OR-group; keep remote/hybrid.",
    )
    ap.add_argument(
        "--extra-noun",
        action="append",
        default=[],
        dest="extra_nouns",
        help="Extra role noun for this run (repeatable). Used by /scrape <focus>.",
    )
    args = ap.parse_args()

    recipe = parse_recipe(args.path)
    payload = recipe_payload(
        recipe, extra_nouns=args.extra_nouns, remote_only=args.remote
    )
    json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
