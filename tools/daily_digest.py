#!/usr/bin/env python3
"""Daily job digest: SEEK + preferred careers pages → heuristic score → SMTP email.

Schedule via scripts/install-digest.sh (launchd Mon–Fri 08:00 local / GMT+10).

Usage:
  python3 tools/daily_digest.py --dry-run
  python3 tools/daily_digest.py --send-now --force
  python3 tools/daily_digest.py --skip-careers
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import smtplib
import subprocess
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIGEST_CONFIG = ROOT / "config" / "digest.json"
STATE_PATH = ROOT / "job_scraper" / "digest_state.json"
ENV_PATH = ROOT / ".env"
SEARCH_QUERIES = ROOT / "skills" / "job-scraper" / "search-queries.md"
PROFILE_PATH = ROOT / "skills" / "job-application-assistant" / "01-candidate-profile.md"
SEEK_CLI = ROOT / "tools" / "seek-search" / "seek_search.py"

sys.path.insert(0, str(ROOT / "tools"))
from careers_search import (  # noqa: E402
    fetch_all_from_config,
    load_preferred_companies,
)


DEFAULTS = {
    "enabled": False,
    "hour": 8,
    "weekdays": [1, 2, 3, 4, 5],
    "timezone_note": "GMT+10",
    "recipient_email": "",
    "preferred_companies": [],
    "min_score": 55,
    "max_results": 25,
    "days": 3,
    "pages": 2,
    "company_boost": 15,
    "careers_enabled": True,
    # Location filter: "profile" reads Identity Location + Constraints;
    # "custom" uses locations[] below.
    "location_source": "profile",
    "locations": [],
    "include_remote": True,
}

# Map city names → SEEK --where strings
CITY_TO_SEEK = {
    "melbourne": "All Melbourne VIC",
    "sydney": "All Sydney NSW",
    "brisbane": "All Brisbane QLD",
    "perth": "All Perth WA",
    "adelaide": "All Adelaide SA",
    "canberra": "All Canberra ACT",
    "hobart": "All Hobart TAS",
    "darwin": "All Darwin NT",
}

AU_STATES = {"vic", "nsw", "qld", "wa", "sa", "tas", "act", "nt"}


def load_env(path: Path = ENV_PATH) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.is_file():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        env[key.strip()] = val.strip().strip('"').strip("'")
    return env


def load_config(path: Path = DIGEST_CONFIG) -> dict:
    cfg = dict(DEFAULTS)
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        cfg.update(data)
    return cfg


def save_config(cfg: dict, path: Path = DIGEST_CONFIG) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_state(path: Path = STATE_PATH) -> dict:
    if not path.is_file():
        return {"emailed_ids": [], "last_run": ""}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"emailed_ids": [], "last_run": ""}


def save_state(state: dict, path: Path = STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_search_queries(path: Path = SEARCH_QUERIES) -> tuple[list[str], list[str], bool]:
    """Return (keywords, where_locations, include_remote_au)."""
    if not path.is_file():
        return [], ["All Australia"], True
    text = path.read_text(encoding="utf-8")

    locations: list[str] = []
    for m in re.finditer(r"`(All [^`]+)`", text):
        loc = m.group(1).strip()
        if loc not in locations:
            locations.append(loc)
    if not locations:
        locations = ["All Australia"]

    include_remote = "All Australia" in locations or bool(re.search(r"--remote", text))

    # Keywords from fenced blocks under Priority sections (first 3 priorities).
    keywords: list[str] = []
    sections = re.split(r"^###\s+Priority\s+(\d+)", text, flags=re.M)
    # sections: [preamble, "1", body1, "2", body2, ...]
    for i in range(1, len(sections), 2):
        num = int(sections[i])
        body = sections[i + 1] if i + 1 < len(sections) else ""
        if num > 3:
            continue
        for block in re.finditer(r"```(?:\w*)\n(.*?)```", body, re.S):
            for line in block.group(1).splitlines():
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("["):
                    continue
                if line not in keywords:
                    keywords.append(line)

    # Fallback: any non-placeholder lines in code fences in the file
    if not keywords:
        for block in re.finditer(r"```(?:\w*)\n(.*?)```", text, re.S):
            for line in block.group(1).splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "[" in line:
                    continue
                if line.startswith("site:") or "OR" in line:
                    continue
                if line not in keywords:
                    keywords.append(line)

    return keywords[:12], locations[:4], include_remote


def extract_profile_skills(path: Path = PROFILE_PATH) -> list[str]:
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    skills: list[str] = []

    # Identity email is handled elsewhere; pull Technical Skills + experience titles.
    tech = re.search(r"##\s+Technical Skills\b(.*?)(?=\n##\s|\Z)", text, re.S | re.I)
    blob = tech.group(1) if tech else text
    for m in re.finditer(r"\*\*([^*]+)\*\*", blob):
        token = m.group(1).strip()
        # Drop proficiency notes in parens after
        token = re.split(r"\s*\(", token)[0].strip()
        if 1 < len(token) < 40:
            skills.append(token)

    for m in re.finditer(r"^###\s+(.+?)\s*-\s*", text, re.M):
        title = m.group(1).strip()
        if title and title not in skills:
            skills.append(title)

    # Bullet skill lines without bold
    for m in re.finditer(r"^-\s+([A-Za-z][^:\n]{1,40})$", blob, re.M):
        skills.append(m.group(1).strip())

    # Dedupe preserving order
    seen = set()
    out = []
    for s in skills:
        key = s.lower()
        if key not in seen:
            seen.add(key)
            out.append(s)
    return out[:80]


def read_profile_email(path: Path = PROFILE_PATH) -> str:
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8")
    m = re.search(r"\*\*Email:\*\*\s*(\S+)", text)
    return m.group(1).strip() if m else ""


def read_profile_location(path: Path = PROFILE_PATH) -> tuple[list[str], bool]:
    """Return (cities, include_remote) from profile Identity Location + Constraints."""
    if not path.is_file():
        return [], True
    text = path.read_text(encoding="utf-8")
    cities: list[str] = []
    loc_m = re.search(r"\*\*Location:\*\*\s*(.+)", text)
    if loc_m:
        city = _city_from_location_string(loc_m.group(1))
        if city:
            cities.append(city)
    include_remote = True
    cons_m = re.search(r"\*\*Constraints:\*\*\s*(.+)", text)
    if cons_m:
        cons = cons_m.group(1).lower()
        if any(k in cons for k in ("remote", "hybrid", "wfh", "work from home", "australia")):
            include_remote = True
        if re.search(r"\bon[\s-]?site only\b|\bno remote\b|\blocal only\b", cons):
            include_remote = False
        # Also pull extra cities mentioned in constraints
        for name in CITY_TO_SEEK:
            if name in cons and name.title() not in cities and name.capitalize() not in [c.lower() for c in cities]:
                # Only add if explicitly listed as a target city, not just "across Australia"
                if re.search(rf"\b{name}\b", cons):
                    pretty = name.title()
                    if pretty not in cities:
                        cities.append(pretty)
    return cities, include_remote


def _city_from_location_string(raw: str) -> str:
    """Turn 'Melbourne, VIC, Australia' or 'Melbourne VIC' into 'Melbourne'."""
    s = (raw or "").strip()
    if not s:
        return ""
    # Drop trailing country
    s = re.sub(r",?\s*Australia\s*$", "", s, flags=re.I).strip()
    parts = re.split(r"[,/|]", s)
    first = parts[0].strip()
    tokens = first.split()
    tokens = [t for t in tokens if t.lower().rstrip(".") not in AU_STATES and not t.isdigit()]
    if not tokens:
        return first.title()
    return " ".join(tokens).title()


def resolve_location_prefs(cfg: dict) -> tuple[list[str], bool, list[str]]:
    """Return (cities, include_remote, seek_where_list)."""
    source = (cfg.get("location_source") or "profile").strip().lower()
    include_remote = bool(cfg.get("include_remote", True))
    cities: list[str] = []

    if source == "custom":
        raw = cfg.get("locations") or []
        if isinstance(raw, str):
            raw = [p.strip() for p in raw.split(",") if p.strip()]
        for item in raw:
            city = _city_from_location_string(str(item))
            if city and city not in cities:
                cities.append(city)
    else:
        profile_cities, profile_remote = read_profile_location()
        cities = profile_cities
        # Profile constraints can force remote off; custom include_remote still applies as OR default
        if cfg.get("include_remote") is None:
            include_remote = profile_remote
        else:
            include_remote = bool(cfg.get("include_remote"))

    if not cities:
        # Fall back to search-queries home locations
        _, query_locs, query_remote = parse_search_queries()
        for loc in query_locs:
            city = _city_from_location_string(loc.replace("All ", ""))
            if city and city.lower() not in {"australia"} and city not in cities:
                cities.append(city)
        if cfg.get("include_remote") is None:
            include_remote = query_remote

    seek_where: list[str] = []
    for city in cities:
        key = city.lower()
        where = CITY_TO_SEEK.get(key) or CITY_TO_SEEK.get(key.split()[0] if key else "")
        if where and where not in seek_where:
            seek_where.append(where)
        elif not where:
            # Best-effort SEEK string
            guess = f"All {city}"
            if guess not in seek_where:
                seek_where.append(guess)
    if not seek_where:
        seek_where = ["All Australia"]

    return cities, include_remote, seek_where


def job_matches_location(job: dict, cities: list[str], include_remote: bool) -> bool:
    """Keep jobs in preferred cities, or remote/hybrid AU when allowed."""
    loc = (job.get("location") or "").lower()
    arr = (job.get("work_arrangement") or "").lower()
    blob = " ".join(
        [
            loc,
            arr,
            (job.get("teaser") or "").lower(),
            " ".join(job.get("bullet_points") or []).lower(),
        ]
    )

    city_hit = False
    for city in cities:
        c = city.lower()
        if c and c in loc:
            city_hit = True
            break

    remoteish = any(
        k in blob
        for k in ("remote", "hybrid", "work from home", "wfh", "work from anywhere")
    )
    # Australia-wide / unspecified AU often OK for remote-friendly digests
    au_wide = bool(re.search(r"\baustralia\b|\bau\b|\bnationwide\b|\banywhere\b", loc)) and not city_hit

    if city_hit:
        return True
    if include_remote and (remoteish or au_wide):
        return True
    if include_remote and not loc:
        # Careers boards often omit location — keep when remote is allowed
        return True
    if not cities:
        return True
    return False


def update_profile_email(email: str, path: Path = PROFILE_PATH) -> bool:
    """Update Identity Email line. Returns True if written."""
    if not path.is_file() or not email:
        return False
    text = path.read_text(encoding="utf-8")
    new_text, n = re.subn(
        r"(\*\*Email:\*\*\s*)\S+",
        r"\g<1>" + email,
        text,
        count=1,
    )
    if n:
        path.write_text(new_text, encoding="utf-8")
        return True
    return False


def run_seek_search(keywords: str, where: str, pages: int, days: int, remote: bool = False) -> list[dict]:
    cmd = [
        sys.executable,
        str(SEEK_CLI),
        "--keywords",
        keywords,
        "--where",
        where,
        "--pages",
        str(pages),
    ]
    if days > 0:
        cmd.extend(["--days", str(days)])
    if remote:
        cmd.append("--remote")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd=str(ROOT))
    except (subprocess.TimeoutExpired, OSError) as exc:
        print(f"[digest] seek-search failed for '{keywords}': {exc}", file=sys.stderr)
        return []
    if proc.returncode != 0:
        print(f"[digest] seek-search stderr: {proc.stderr.strip()}", file=sys.stderr)
        return []
    try:
        data = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError:
        print(f"[digest] seek-search bad JSON for '{keywords}'", file=sys.stderr)
        return []
    if not isinstance(data, list):
        return []
    for job in data:
        job.setdefault("source", "seek")
    return data


def preferred_match(company: str, preferred: list[dict]) -> dict | None:
    company_l = (company or "").lower()
    for pref in preferred:
        names = [pref.get("name", "")] + list(pref.get("aliases") or [])
        for name in names:
            n = (name or "").lower().strip()
            if not n:
                continue
            if n in company_l or company_l in n:
                return pref
    return None


def score_job(
    job: dict,
    role_keywords: list[str],
    skills: list[str],
    preferred: list[dict],
    company_boost: int,
) -> tuple[int, bool]:
    """Return (score 0-100, is_preferred)."""
    title = (job.get("title") or "").lower()
    blob = " ".join(
        [
            title,
            (job.get("teaser") or "").lower(),
            " ".join(job.get("bullet_points") or []).lower(),
            (job.get("location") or "").lower(),
            (job.get("work_arrangement") or "").lower(),
        ]
    )

    score = 0

    # Role keyword hits in title (strong) / blob (weaker)
    for kw in role_keywords:
        tokens = [t for t in re.findall(r"[a-z0-9+#.]{2,}", kw.lower()) if len(t) > 2]
        if not tokens:
            continue
        hits = sum(1 for t in tokens if t in title)
        if hits:
            score += min(35, 12 * hits)
        elif any(t in blob for t in tokens):
            score += 6

    # Skill overlap
    skill_hits = 0
    for skill in skills:
        s = skill.lower()
        if len(s) < 2:
            continue
        if s in blob:
            skill_hits += 1
    score += min(40, skill_hits * 5)

    # Remote / hybrid soft bonus
    if any(k in blob for k in ("remote", "hybrid", "work from home", "wfh")):
        score += 5

    is_pref = preferred_match(job.get("company") or "", preferred) is not None
    if is_pref or str(job.get("source", "")).startswith("careers"):
        is_pref = True
        score += company_boost

    return min(100, score), is_pref


def dedupe_jobs(jobs: list[dict]) -> list[dict]:
    seen_ids: set[str] = set()
    seen_keys: set[str] = set()
    out = []
    for job in jobs:
        jid = str(job.get("id") or "")
        url = (job.get("url") or "").rstrip("/").lower()
        key = f"{(job.get('company') or '').lower()}|{(job.get('title') or '').lower()}"
        if jid and jid in seen_ids:
            continue
        if url and url in seen_ids:
            continue
        if key in seen_keys:
            continue
        if jid:
            seen_ids.add(jid)
        if url:
            seen_ids.add(url)
        seen_keys.add(key)
        out.append(job)
    return out


def collect_jobs(cfg: dict, skip_seek: bool = False, skip_careers: bool = False) -> tuple[list[dict], list[str]]:
    keywords, _query_locs, _query_remote = parse_search_queries()
    cities, include_remote, seek_where = resolve_location_prefs(cfg)
    skills = extract_profile_skills()
    preferred = load_preferred_companies()
    notes: list[str] = []

    loc_label = ", ".join(cities) if cities else "any"
    remote_label = "yes" if include_remote else "no"
    notes.append(f"Location filter: {loc_label} (remote/hybrid: {remote_label})")

    if not keywords:
        notes.append("No role keywords found in search-queries.md — using fallback 'software engineer'")
        keywords = ["software engineer"]

    raw: list[dict] = []

    if not skip_seek:
        home_locations = [w for w in seek_where if w != "All Australia"] or seek_where[:1]
        for kw in keywords:
            for where in home_locations:
                raw.extend(
                    run_seek_search(
                        kw,
                        where,
                        pages=int(cfg.get("pages") or 2),
                        days=int(cfg.get("days") or 0),
                    )
                )
            if include_remote:
                raw.extend(
                    run_seek_search(
                        kw,
                        "All Australia",
                        pages=1,
                        days=int(cfg.get("days") or 0),
                        remote=True,
                    )
                )

    if not skip_careers and cfg.get("careers_enabled", True):
        career_jobs, errors = fetch_all_from_config(keywords=keywords)
        raw.extend(career_jobs)
        notes.extend(f"careers: {e}" for e in errors)

    jobs = dedupe_jobs(raw)
    before_loc = len(jobs)
    jobs = [j for j in jobs if job_matches_location(j, cities, include_remote)]
    dropped = before_loc - len(jobs)
    if dropped:
        notes.append(f"Dropped {dropped} role(s) outside location prefs")

    scored = []
    for job in jobs:
        sc, is_pref = score_job(
            job,
            keywords,
            skills,
            preferred,
            int(cfg.get("company_boost") or 15),
        )
        job = dict(job)
        job["digest_score"] = sc
        job["is_preferred"] = is_pref
        scored.append(job)

    min_score = int(cfg.get("min_score") or 55)
    scored = [j for j in scored if j["digest_score"] >= min_score]
    scored.sort(key=lambda j: (-int(j["is_preferred"]), -j["digest_score"], j.get("title") or ""))
    max_results = int(cfg.get("max_results") or 25)
    return scored[:max_results], notes


def build_email_bodies(jobs: list[dict], notes: list[str]) -> tuple[str, str]:
    today = datetime.now().strftime("%Y-%m-%d")
    if not jobs:
        plain = f"Job digest {today}\n\nNo new strong matches today.\n"
        if notes:
            plain += "\nNotes:\n" + "\n".join(f"- {n}" for n in notes) + "\n"
        html_body = f"<p>No new strong matches for {html.escape(today)}.</p>"
        return plain, html_body

    plain_lines = [f"Job digest {today}", f"{len(jobs)} role(s):", ""]
    html_parts = [
        f"<h2>Job digest — {html.escape(today)}</h2>",
        f"<p>{len(jobs)} role(s) matching your profile heuristics.</p>",
        "<ol>",
    ]
    for job in jobs:
        badges = []
        if job.get("is_preferred"):
            badges.append("Preferred")
        src = str(job.get("source") or "")
        if src.startswith("careers"):
            badges.append("Careers page")
        elif src == "seek":
            badges.append("SEEK")
        badge_str = f" [{', '.join(badges)}]" if badges else ""
        meta = " | ".join(
            filter(
                None,
                [
                    job.get("company"),
                    job.get("location"),
                    job.get("salary"),
                ],
            )
        )
        plain_lines.append(f"- {job.get('title')}{badge_str}")
        plain_lines.append(f"  {meta}")
        plain_lines.append(f"  {job.get('url')}")
        plain_lines.append("")

        html_parts.append("<li>")
        html_parts.append(
            f"<strong><a href=\"{html.escape(job.get('url') or '')}\">"
            f"{html.escape(job.get('title') or '')}</a></strong>"
        )
        if badges:
            html_parts.append(
                " "
                + " ".join(
                    f'<span style="background:#eef;padding:1px 6px;border-radius:4px;'
                    f'font-size:12px;margin-right:4px">{html.escape(b)}</span>'
                    for b in badges
                )
            )
        html_parts.append(f"<br/><span style=\"color:#555\">{html.escape(meta)}</span>")
        if job.get("teaser"):
            html_parts.append(f"<br/><em>{html.escape((job.get('teaser') or '')[:180])}</em>")
        html_parts.append("</li>")

    html_parts.append("</ol>")
    if notes:
        plain_lines.append("Notes:")
        plain_lines.extend(f"- {n}" for n in notes)
        html_parts.append("<h3>Notes</h3><ul>")
        html_parts.extend(f"<li>{html.escape(n)}</li>" for n in notes)
        html_parts.append("</ul>")

    return "\n".join(plain_lines), "\n".join(html_parts)


def send_smtp(subject: str, plain: str, html_body: str, recipient: str, env: dict[str, str]) -> None:
    host = env.get("SMTP_HOST") or os.environ.get("SMTP_HOST", "")
    port = int(env.get("SMTP_PORT") or os.environ.get("SMTP_PORT") or 587)
    user = env.get("SMTP_USER") or os.environ.get("SMTP_USER", "")
    password = env.get("SMTP_PASSWORD") or os.environ.get("SMTP_PASSWORD", "")
    from_addr = env.get("SMTP_FROM") or os.environ.get("SMTP_FROM") or user

    if not host or not from_addr or not recipient:
        raise RuntimeError("SMTP_HOST, SMTP_FROM/SMTP_USER, and recipient email are required")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = recipient
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(host, port, timeout=60) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        if user and password:
            smtp.login(user, password)
        smtp.sendmail(from_addr, [recipient], msg.as_string())


def should_run_today(cfg: dict, force: bool) -> bool:
    if force:
        return True
    now = datetime.now()
    # Python: Monday=0 … Sunday=6; config uses launchd-style Monday=1 … Sunday=0|7
    weekdays = cfg.get("weekdays") or [1, 2, 3, 4, 5]
    # Map launchd weekday → Python weekday
    launchd_to_py = {0: 6, 1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6}
    allowed_py = {launchd_to_py.get(int(d), int(d) - 1) for d in weekdays}
    return now.weekday() in allowed_py


def resolve_recipient(cfg: dict) -> str:
    return (cfg.get("recipient_email") or "").strip() or read_profile_email()


def run_digest(
    *,
    dry_run: bool = False,
    force: bool = False,
    skip_seek: bool = False,
    skip_careers: bool = False,
    mark_sent: bool = True,
) -> dict:
    cfg = load_config()
    if not cfg.get("enabled") and not force and not dry_run:
        return {"ok": False, "reason": "disabled", "jobs": []}

    if not should_run_today(cfg, force=force or dry_run):
        return {"ok": False, "reason": "not_scheduled_today", "jobs": []}

    jobs, notes = collect_jobs(cfg, skip_seek=skip_seek, skip_careers=skip_careers)
    state = load_state()
    emailed = set(state.get("emailed_ids") or [])
    fresh = []
    for job in jobs:
        jid = str(job.get("id") or job.get("url") or "")
        if jid and jid in emailed:
            continue
        fresh.append(job)

    recipient = resolve_recipient(cfg)
    plain, html_body = build_email_bodies(fresh, notes)
    subject = f"Job digest — {len(fresh)} match(es) — {datetime.now().strftime('%Y-%m-%d')}"

    result = {
        "ok": True,
        "recipient": recipient,
        "count": len(fresh),
        "jobs": fresh,
        "notes": notes,
        "subject": subject,
        "plain": plain,
    }

    if dry_run:
        result["sent"] = False
        return result

    if not recipient:
        raise RuntimeError("No recipient email — set config/digest.json recipient_email or profile Identity Email")

    env = load_env()
    send_smtp(subject, plain, html_body, recipient, env)
    result["sent"] = True

    if mark_sent:
        for job in fresh:
            jid = str(job.get("id") or job.get("url") or "")
            if jid and jid not in emailed:
                emailed.add(jid)
        state["emailed_ids"] = sorted(emailed)[-2000:]  # cap growth
        state["last_run"] = datetime.now().isoformat(timespec="seconds")
        save_state(state)

    return result


def main() -> None:
    ap = argparse.ArgumentParser(description="Daily job digest email")
    ap.add_argument("--dry-run", action="store_true", help="Scrape/score only; print summary, do not send")
    ap.add_argument("--send-now", action="store_true", help="Send even if enabled is false (implies --force)")
    ap.add_argument("--force", action="store_true", help="Ignore weekday schedule (and with --send-now, ignore enabled)")
    ap.add_argument("--skip-seek", action="store_true")
    ap.add_argument("--skip-careers", action="store_true")
    args = ap.parse_args()

    force = args.force or args.send_now
    dry_run = args.dry_run and not args.send_now

    # When launchd runs without flags, require enabled + weekday
    if not args.dry_run and not args.send_now and not args.force:
        cfg = load_config()
        if not cfg.get("enabled"):
            print("[digest] disabled in config/digest.json — exiting")
            return
        if not should_run_today(cfg, force=False):
            print("[digest] not a scheduled weekday — exiting")
            return
        force = True  # already validated schedule; allow send

    try:
        result = run_digest(
            dry_run=dry_run,
            force=force or dry_run,
            skip_seek=args.skip_seek,
            skip_careers=args.skip_careers,
        )
    except Exception as exc:
        print(f"[digest] error: {exc}", file=sys.stderr)
        sys.exit(1)

    if not result.get("ok"):
        print(f"[digest] skipped: {result.get('reason')}")
        return

    print(f"[digest] {result['count']} job(s) for {result.get('recipient') or '(no recipient)'}")
    for job in result.get("jobs") or []:
        badge = "★" if job.get("is_preferred") else "·"
        print(f"  {badge} [{job.get('digest_score')}] {job.get('title')} — {job.get('company')}")
    if dry_run:
        print("[digest] dry-run — email not sent")
        print(result.get("plain", "")[:2000])
    elif result.get("sent"):
        print("[digest] email sent")


if __name__ == "__main__":
    main()
