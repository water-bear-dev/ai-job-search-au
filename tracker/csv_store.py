"""CSV persistence for job_search_tracker.csv (repo root)."""

from __future__ import annotations

import csv
import shutil
from datetime import date
from pathlib import Path

TRACKER_DIR = Path(__file__).resolve().parent
REPO_ROOT = TRACKER_DIR.parent
CSV_PATH = REPO_ROOT / "job_search_tracker.csv"
EXAMPLE_CSV = REPO_ROOT / "job_search_tracker.example.csv"

COLUMNS = [
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


def ensure_csv_exists() -> None:
    """Create job_search_tracker.csv from example template if missing."""
    if CSV_PATH.exists():
        return
    if not EXAMPLE_CSV.exists():
        raise FileNotFoundError(f"Missing template: {EXAMPLE_CSV}")
    shutil.copy(EXAMPLE_CSV, CSV_PATH)


def _normalize_row(row: dict) -> dict:
    return {col: (row.get(col) or "").strip() for col in COLUMNS}


def read_rows() -> list[dict]:
    ensure_csv_exists()
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != COLUMNS:
            raise ValueError(
                f"Unexpected CSV columns. Expected {COLUMNS}, got {reader.fieldnames}"
            )
        return [_normalize_row(row) for row in reader]


def write_rows(rows: list[dict]) -> None:
    ensure_csv_exists()
    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(_normalize_row(row))


def empty_row() -> dict:
    return {col: "" for col in COLUMNS}


def new_row(**fields: str) -> dict:
    row = empty_row()
    row["date"] = date.today().isoformat()
    for key, value in fields.items():
        if key in COLUMNS:
            row[key] = (value or "").strip()
    return row
