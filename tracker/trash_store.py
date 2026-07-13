"""Recycle bin persistence for soft-deleted job tracker rows."""

from __future__ import annotations

import csv
from datetime import datetime, timedelta
from pathlib import Path

from csv_store import COLUMNS, REPO_ROOT, _normalize_row, now_iso, read_rows, write_rows
from revision import bump_revision

TRASH_PATH = REPO_ROOT / "job_search_tracker_trash.csv"
TRASH_COLUMNS = [*COLUMNS, "deleted_at"]
RETENTION_DAYS = 30


def ensure_trash_exists() -> None:
    if TRASH_PATH.exists():
        return
    with TRASH_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=TRASH_COLUMNS, lineterminator="\n")
        writer.writeheader()


def _normalize_trash_row(row: dict) -> dict:
    normalized = _normalize_row(row)
    normalized["deleted_at"] = _to_datetime(row.get("deleted_at", "") or now_iso())
    return normalized


def _to_datetime(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return now_iso()
    if "T" in value:
        return value
    if len(value) == 10:
        return f"{value}T00:00:00"
    return value


def _parse_datetime(value: str) -> datetime | None:
    value = (value or "").strip()
    if not value:
        return None
    normalized = _to_datetime(value)
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def read_trash_rows() -> list[dict]:
    ensure_trash_exists()
    with TRASH_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        if fieldnames != TRASH_COLUMNS:
            raise ValueError(f"Unexpected trash CSV columns. Expected {TRASH_COLUMNS}, got {fieldnames}")
        return [_normalize_trash_row(row) for row in reader]


def write_trash_rows(rows: list[dict]) -> None:
    ensure_trash_exists()
    with TRASH_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=TRASH_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(_normalize_trash_row(row))
    bump_revision()


def days_until_purge(deleted_at: str) -> int:
    deleted = _parse_datetime(deleted_at)
    if not deleted:
        return RETENTION_DAYS
    purge_at = deleted + timedelta(days=RETENTION_DAYS)
    return max(0, (purge_at.date() - datetime.now().date()).days)


def purge_expired_trash() -> int:
    trash = read_trash_rows()
    kept: list[dict] = []
    purged = 0
    for row in trash:
        deleted = _parse_datetime(row.get("deleted_at", ""))
        if deleted and datetime.now() - deleted >= timedelta(days=RETENTION_DAYS):
            purged += 1
        else:
            kept.append(row)
    if purged:
        write_trash_rows(kept)
    return purged


def soft_delete_indices(indices: list[int]) -> int:
    purge_expired_trash()
    if not indices:
        return 0
    rows = read_rows()
    trash = read_trash_rows()
    unique = sorted(set(indices), reverse=True)
    for idx in unique:
        if idx < 0 or idx >= len(rows):
            raise IndexError(f"Job not found at index {idx}")
        row = rows.pop(idx)
        row["deleted_at"] = now_iso()
        trash.append(row)
    write_rows(rows)
    write_trash_rows(trash)
    return len(unique)


def restore_trash_index(index: int) -> dict:
    purge_expired_trash()
    trash = read_trash_rows()
    if index < 0 or index >= len(trash):
        raise IndexError(f"Trash item not found at index {index}")
    row = trash.pop(index)
    row.pop("deleted_at", None)
    rows = read_rows()
    rows.append(row)
    write_rows(rows)
    write_trash_rows(trash)
    return row


def permanent_delete_trash_indices(indices: list[int]) -> int:
    purge_expired_trash()
    if not indices:
        return 0
    trash = read_trash_rows()
    unique = sorted(set(indices), reverse=True)
    for idx in unique:
        if idx < 0 or idx >= len(trash):
            raise IndexError(f"Trash item not found at index {idx}")
        trash.pop(idx)
    write_trash_rows(trash)
    return len(unique)


def sort_trash_newest_first(rows: list[dict]) -> list[tuple[int, dict]]:
    indexed = list(enumerate(rows))
    indexed.sort(key=lambda item: item[1].get("deleted_at", ""), reverse=True)
    return indexed
