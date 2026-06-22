#!/usr/bin/env python3
"""
Local job tracker — FastAPI server for job_search_tracker.csv.

Usage:
  cd tracker
  pip install -r requirements.txt
  python server.py

Opens http://127.0.0.1:8765 (override with TRACKER_PORT).
"""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from csv_store import COLUMNS, REPO_ROOT, TRACKER_DIR, ensure_csv_exists, new_row, read_rows, write_rows
from revision import bump_revision, get_revision

STATUSES_PATH = TRACKER_DIR / "statuses.json"
STATIC_DIR = TRACKER_DIR / "static"

FILE_ALLOWLIST_PREFIXES = (
    "cv/",
    "cover_letters/",
    "documents/applications/",
)

@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_csv_exists()
    yield


app = FastAPI(title="AI Job Search — Tracker", docs_url="/api/docs", lifespan=lifespan)


class JobCreate(BaseModel):
    company: str
    role: str
    source: str = ""
    status: str = ""
    notes: str = ""
    cv_file: str = ""
    cover_letter_file: str = ""
    sector: str = ""
    role_type: str = ""
    channel: str = ""
    contact_person: str = ""
    fit_rating: str = ""


class JobUpdate(BaseModel):
    company: str | None = None
    role: str | None = None
    source: str | None = None
    status: str | None = None
    notes: str | None = None
    cv_file: str | None = None
    cover_letter_file: str | None = None
    sector: str | None = None
    role_type: str | None = None
    channel: str | None = None
    contact_person: str | None = None
    fit_rating: str | None = None
    date: str | None = None


class JobWithIndex(BaseModel):
    index: int
    job: dict[str, str]


class StatusesConfig(BaseModel):
    default_status: str
    statuses: list[str]


def load_statuses() -> StatusesConfig:
    with STATUSES_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    return StatusesConfig(**data)


def validate_status(status: str) -> str:
    cfg = load_statuses()
    if not status:
        return cfg.default_status
    if status not in cfg.statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{status}'. Allowed: {cfg.statuses}",
        )
    return status


def sort_jobs_newest_first(rows: list[dict]) -> list[tuple[int, dict]]:
    indexed = list(enumerate(rows))
    indexed.sort(key=lambda item: item[1].get("date", ""), reverse=True)
    return indexed


def resolve_allowed_file(path_str: str) -> Path:
    if not path_str or ".." in path_str:
        raise HTTPException(status_code=400, detail="Invalid path")
    normalized = path_str.replace("\\", "/").lstrip("/")
    if not any(normalized.startswith(prefix) for prefix in FILE_ALLOWLIST_PREFIXES):
        raise HTTPException(status_code=403, detail="Path not in allowlist")
    resolved = (REPO_ROOT / normalized).resolve()
    if not resolved.is_relative_to(REPO_ROOT.resolve()):
        raise HTTPException(status_code=403, detail="Path escapes repo root")
    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return resolved


def apply_update(row: dict, update: JobUpdate) -> dict:
    data = update.model_dump(exclude_unset=True)
    if "status" in data and data["status"] is not None:
        data["status"] = validate_status(data["status"])
    for key, value in data.items():
        if key in COLUMNS and value is not None:
            row[key] = value.strip() if isinstance(value, str) else str(value)
    return row



@app.get("/api/jobs")
def list_jobs() -> list[JobWithIndex]:
    rows = read_rows()
    return [JobWithIndex(index=idx, job=row) for idx, row in sort_jobs_newest_first(rows)]


@app.post("/api/jobs", status_code=201)
def create_job(body: JobCreate) -> JobWithIndex:
    rows = read_rows()
    row = new_row(
        company=body.company,
        role=body.role,
        source=body.source,
        status=validate_status(body.status),
        notes=body.notes,
        cv_file=body.cv_file,
        cover_letter_file=body.cover_letter_file,
        sector=body.sector,
        role_type=body.role_type,
        channel=body.channel,
        contact_person=body.contact_person,
        fit_rating=body.fit_rating,
    )
    if not row["company"] or not row["role"]:
        raise HTTPException(status_code=400, detail="company and role are required")
    rows.append(row)
    write_rows(rows)
    index = len(rows) - 1
    return JobWithIndex(index=index, job=row)


@app.put("/api/jobs/{index}")
def update_job(index: int, body: JobUpdate) -> JobWithIndex:
    rows = read_rows()
    if index < 0 or index >= len(rows):
        raise HTTPException(status_code=404, detail="Job not found")
    row = apply_update(dict(rows[index]), body)
    if not row["company"] or not row["role"]:
        raise HTTPException(status_code=400, detail="company and role are required")
    rows[index] = row
    write_rows(rows)
    return JobWithIndex(index=index, job=row)


@app.delete("/api/jobs/{index}", status_code=204)
def delete_job(index: int) -> None:
    rows = read_rows()
    if index < 0 or index >= len(rows):
        raise HTTPException(status_code=404, detail="Job not found")
    rows.pop(index)
    write_rows(rows)


@app.get("/api/statuses")
def get_statuses() -> StatusesConfig:
    return load_statuses()


@app.get("/api/files/exists")
def file_exists(path: str = Query(..., min_length=1)) -> dict[str, Any]:
    try:
        resolve_allowed_file(path)
        return {"path": path, "exists": True}
    except HTTPException as exc:
        if exc.status_code == 404:
            return {"path": path, "exists": False}
        raise


@app.get("/api/files")
def serve_file(path: str = Query(..., min_length=1)) -> FileResponse:
    resolved = resolve_allowed_file(path)
    return FileResponse(resolved, filename=resolved.name)


class RevisionResponse(BaseModel):
    revision: int


@app.get("/api/revision")
def read_revision() -> RevisionResponse:
    """Revision counter bumped whenever job_search_tracker.csv changes."""
    return RevisionResponse(revision=get_revision())


@app.post("/api/revision", response_model=RevisionResponse)
async def notify_revision() -> RevisionResponse:
    """Called by upsert scripts so open tracker tabs reload without waiting for poll."""
    return RevisionResponse(revision=get_revision())


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")


def main() -> None:
    import uvicorn

    port = int(os.environ.get("TRACKER_PORT", "8765"))
    uvicorn.run("server:app", host="127.0.0.1", port=port, reload=False)


if __name__ == "__main__":
    main()
