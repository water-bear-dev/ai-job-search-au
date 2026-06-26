"""CSV persistence for job_search_tracker.csv (repo root)."""

from __future__ import annotations

import csv
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

TRACKER_DIR = Path(__file__).resolve().parent
REPO_ROOT = TRACKER_DIR.parent
CSV_PATH = REPO_ROOT / "job_search_tracker.csv"
EXAMPLE_CSV = REPO_ROOT / "job_search_tracker.example.csv"
SEEN_JOBS_PATH = REPO_ROOT / "job_scraper" / "seen_jobs.json"
_SEEK_JOB_ID_RE = re.compile(r"seek\.com\.au/job/(\d+)", re.IGNORECASE)

COLUMNS = [
    "created_at",
    "company",
    "sector",
    "role",
    "role_type",
    "channel",
    "status",
    "contact_person",
    "fit_rating",
    "notes",
    "cv_file",
    "cover_letter_file",
    "source",
    "modified_at",
]

LEGACY_COLUMNS = [
    "date",
    "company",
    "sector",
    "role",
    "role_type",
    "channel",
    "status",
    "contact_person",
    "fit_rating",
    "notes",
    "cv_file",
    "cover_letter_file",
    "source",
]


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _to_datetime(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return now_iso()
    if "T" in value:
        return value
    if len(value) == 10:
        return f"{value}T00:00:00"
    return value


def touch_modified(row: dict) -> dict:
    row["modified_at"] = now_iso()
    return row


def ensure_csv_exists() -> None:
    """Create job_search_tracker.csv from example template if missing."""
    if CSV_PATH.exists():
        return
    if not EXAMPLE_CSV.exists():
        raise FileNotFoundError(f"Missing template: {EXAMPLE_CSV}")
    shutil.copy(EXAMPLE_CSV, CSV_PATH)


def _normalize_row(row: dict) -> dict:
    return {col: (row.get(col) or "").strip() for col in COLUMNS}


def _migrate_legacy_row(row: dict) -> dict:
    created = _to_datetime(row.pop("date", "") or row.get("created_at", ""))
    migrated = {col: "" for col in COLUMNS}
    migrated["created_at"] = created
    migrated["modified_at"] = _to_datetime(row.get("modified_at", "") or created)
    for col in COLUMNS:
        if col in ("created_at", "modified_at"):
            continue
        if col in row:
            migrated[col] = (row.get(col) or "").strip()
    return _normalize_row(migrated)


def read_rows() -> list[dict]:
    ensure_csv_exists()
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        if fieldnames == COLUMNS:
            return [_normalize_row(row) for row in reader]
        if fieldnames == LEGACY_COLUMNS:
            rows = [_migrate_legacy_row(dict(row)) for row in reader]
            write_rows(rows)
            return rows
        raise ValueError(
            f"Unexpected CSV columns. Expected {COLUMNS} or legacy {LEGACY_COLUMNS}, got {fieldnames}"
        )


def write_rows(rows: list[dict]) -> None:
    ensure_csv_exists()
    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(_normalize_row(row))
    from revision import bump_revision

    bump_revision()


def empty_row() -> dict:
    return {col: "" for col in COLUMNS}


def new_row(**fields: str) -> dict:
    row = empty_row()
    ts = now_iso()
    row["created_at"] = ts
    row["modified_at"] = ts
    for key, value in fields.items():
        if key in COLUMNS and key not in ("created_at", "modified_at"):
            row[key] = (value or "").strip()
    return row


def match_key(company: str, role: str) -> tuple[str, str]:
    return (company.strip().lower(), role.strip().lower())


def find_row_index(rows: list[dict], company: str, role: str) -> int | None:
    key = match_key(company, role)
    for index, row in enumerate(rows):
        if match_key(row["company"], row["role"]) == key:
            return index
    return None


def load_default_status() -> str:
    statuses_path = TRACKER_DIR / "statuses.json"
    if not statuses_path.exists():
        return "draft"
    with statuses_path.open(encoding="utf-8") as f:
        data = json.load(f)
    return (data.get("default_status") or "draft").strip()


def normalize_source_url(source: str) -> str:
    """Canonicalize SEEK job links to https://www.seek.com.au/job/<id>."""
    source = (source or "").strip()
    if not source:
        return ""
    match = _SEEK_JOB_ID_RE.search(source)
    if match:
        return f"https://www.seek.com.au/job/{match.group(1)}"
    return source


def _roles_match(left: str, right: str) -> bool:
    a = left.strip().lower()
    b = right.strip().lower()
    if not a or not b:
        return False
    return a == b or a in b or b in a


def lookup_source_url(company: str, role: str) -> str:
    """Find a posting URL in job_scraper/seen_jobs.json by company + role."""
    if not SEEN_JOBS_PATH.exists():
        return ""
    try:
        with SEEN_JOBS_PATH.open(encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return ""

    company_key = company.strip().lower()
    for entry in (data.get("seen") or {}).values():
        if (entry.get("company") or "").strip().lower() != company_key:
            continue
        title = entry.get("title") or ""
        if _roles_match(title, role):
            return normalize_source_url(entry.get("url") or "")
    return ""


def resolve_source_url(source: str, company: str = "", role: str = "") -> str:
    """Normalize a URL and fall back to seen_jobs.json when missing."""
    normalized = normalize_source_url(source)
    if normalized:
        return normalized
    if company and role:
        return lookup_source_url(company, role)
    return ""


def infer_channel(source: str) -> str:
    lowered = source.lower()
    if "seek.com.au" in lowered:
        return "SEEK"
    if "linkedin.com" in lowered:
        return "LinkedIn"
    if source.strip():
        return "web"
    return ""


def upsert_application(
    *,
    company: str,
    role: str,
    cv_file: str,
    cover_letter_file: str,
    source: str = "",
    fit_rating: str = "",
    notes: str = "",
    sector: str = "",
    role_type: str = "",
    channel: str = "",
    contact_person: str = "",
    status: str = "",
) -> tuple[str, dict]:
    """Create or update a tracker row keyed by company + role.

    Returns (action, row) where action is ``created`` or ``updated``.
    """
    company = company.strip()
    role = role.strip()
    if not company or not role:
        raise ValueError("company and role are required")
    if not cv_file.strip() or not cover_letter_file.strip():
        raise ValueError("cv_file and cover_letter_file are required")

    source = resolve_source_url(source, company=company, role=role)
    if not channel.strip() and source:
        channel = infer_channel(source)

    rows = read_rows()
    index = find_row_index(rows, company, role)

    if index is None:
        row = new_row(
            company=company,
            role=role,
            cv_file=cv_file,
            cover_letter_file=cover_letter_file,
            source=source,
            fit_rating=fit_rating,
            notes=notes,
            sector=sector,
            role_type=role_type,
            channel=channel,
            contact_person=contact_person,
            status=status or load_default_status(),
        )
        rows.append(row)
        write_rows(rows)
        return "created", row

    row = dict(rows[index])
    row["cv_file"] = cv_file.strip()
    row["cover_letter_file"] = cover_letter_file.strip()
    if source.strip():
        row["source"] = source.strip()
    if channel.strip() and not row.get("channel"):
        row["channel"] = channel.strip()
    if fit_rating.strip():
        row["fit_rating"] = fit_rating.strip()
    if notes.strip() and not row["notes"]:
        row["notes"] = notes.strip()
    if sector.strip() and not row["sector"]:
        row["sector"] = sector.strip()
    if role_type.strip() and not row["role_type"]:
        row["role_type"] = role_type.strip()
    if channel.strip() and not row["channel"]:
        row["channel"] = channel.strip()
    if contact_person.strip() and not row["contact_person"]:
        row["contact_person"] = contact_person.strip()
    if status.strip() and not row["status"]:
        row["status"] = status.strip()
    touch_modified(row)
    rows[index] = row
    write_rows(rows)
    return "updated", row
