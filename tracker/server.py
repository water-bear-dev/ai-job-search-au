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
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from pydantic import BaseModel, Field

from csv_store import (
    COLUMNS,
    REPO_ROOT,
    TRACKER_DIR,
    ensure_csv_exists,
    migrate_draft_rows_to_applied,
    new_row,
    normalize_stored_status,
    read_rows,
    touch_modified,
    write_rows,
)
from profile import parse_profile, write_profile
from revision import bump_revision, get_revision
from analytics import PERIODS, build_analytics
from trash_store import (
    RETENTION_DAYS,
    days_until_purge,
    permanent_delete_trash_indices,
    purge_expired_trash,
    read_trash_rows,
    restore_trash_index,
    soft_delete_indices,
    sort_trash_newest_first,
)

STATUSES_PATH = TRACKER_DIR / "statuses.json"
STATIC_DIR = TRACKER_DIR / "static"

FILE_ALLOWLIST_PREFIXES = (
    "applied_jobs/",
    "cv/",
    "cover_letters/",
    "documents/applications/",
)

@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_csv_exists()
    migrate_draft_rows_to_applied()
    purge_expired_trash()
    yield


app = FastAPI(title="AI Job Search — Tracker", docs_url="/api/docs", lifespan=lifespan)


class NoCacheStaticMiddleware(BaseHTTPMiddleware):
    """Prevent stale app.js/style.css when the tracker UI is updated."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        path = request.url.path
        if path in ("/", "/index.html", "/app.js", "/style.css") or path.endswith(
            (".js", ".css", ".html")
        ):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response


app.add_middleware(NoCacheStaticMiddleware)


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


class JobWithIndex(BaseModel):
    index: int
    job: dict[str, str]


class BulkJobRequest(BaseModel):
    indices: list[int]
    action: Literal["update_status", "delete"]
    status: str | None = None


class BulkJobResponse(BaseModel):
    updated: int


class TrashJobWithMeta(BaseModel):
    index: int
    job: dict[str, str]
    days_remaining: int


class BulkTrashRequest(BaseModel):
    indices: list[int]
    action: Literal["restore", "permanent_delete"]


class TrashInfoResponse(BaseModel):
    retention_days: int
    purged: int


class StatusProgression(BaseModel):
    pipeline: list[str] = Field(default_factory=list)
    closed: list[str] = Field(default_factory=list)
    aliases: dict[str, str] = Field(default_factory=dict)


class StatusesConfig(BaseModel):
    default_status: str
    statuses: list[str]
    labels: dict[str, str] = Field(default_factory=dict)
    progression: StatusProgression = Field(default_factory=StatusProgression)


class ProfileSection(BaseModel):
    title: str
    items: list[str] = Field(default_factory=list)
    raw: str = ""


class ProfileResponse(BaseModel):
    sections: list[ProfileSection]


class ProfileUpdate(BaseModel):
    sections: list[ProfileSection]


def load_statuses() -> StatusesConfig:
    with STATUSES_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    return StatusesConfig(**data)


def validate_status(status: str) -> str:
    cfg = load_statuses()
    if not status:
        return cfg.default_status
    normalized = normalize_stored_status(status)
    if normalized not in cfg.statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{status}'. Allowed: {cfg.statuses}",
        )
    return normalized


def sort_jobs_newest_first(rows: list[dict]) -> list[tuple[int, dict]]:
    indexed = list(enumerate(rows))
    indexed.sort(key=lambda item: item[1].get("created_at", ""), reverse=True)
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
        if key in COLUMNS and key not in ("created_at", "modified_at") and value is not None:
            row[key] = value.strip() if isinstance(value, str) else str(value)
    touch_modified(row)
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
    try:
        soft_delete_indices([index])
    except IndexError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/jobs/bulk")
def bulk_jobs(body: BulkJobRequest) -> BulkJobResponse:
    if not body.indices:
        raise HTTPException(status_code=400, detail="No jobs selected")
    unique = sorted(set(body.indices))
    rows = read_rows()
    for idx in unique:
        if idx < 0 or idx >= len(rows):
            raise HTTPException(status_code=404, detail=f"Job not found at index {idx}")

    if body.action == "delete":
        try:
            updated = soft_delete_indices(unique)
        except IndexError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return BulkJobResponse(updated=updated)

    if body.action == "update_status":
        if body.status is None:
            raise HTTPException(status_code=400, detail="status is required for update_status")
        status = validate_status(body.status)
        for idx in unique:
            rows[idx]["status"] = status
            touch_modified(rows[idx])
        write_rows(rows)
        return BulkJobResponse(updated=len(unique))

    raise HTTPException(status_code=400, detail="Invalid bulk action")


@app.get("/api/trash")
def list_trash() -> list[TrashJobWithMeta]:
    purge_expired_trash()
    return [
        TrashJobWithMeta(
            index=idx,
            job=row,
            days_remaining=days_until_purge(row.get("deleted_at", "")),
        )
        for idx, row in sort_trash_newest_first(read_trash_rows())
    ]


@app.get("/api/trash/info")
def trash_info() -> TrashInfoResponse:
    purged = purge_expired_trash()
    return TrashInfoResponse(retention_days=RETENTION_DAYS, purged=purged)


@app.post("/api/trash/{index}/restore")
def restore_trash_job(index: int) -> JobWithIndex:
    try:
        row = restore_trash_index(index)
    except IndexError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    rows = read_rows()
    return JobWithIndex(index=len(rows) - 1, job=row)


@app.delete("/api/trash/{index}", status_code=204)
def permanent_delete_trash_job(index: int) -> None:
    try:
        permanent_delete_trash_indices([index])
    except IndexError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/trash/bulk")
def bulk_trash(body: BulkTrashRequest) -> BulkJobResponse:
    if not body.indices:
        raise HTTPException(status_code=400, detail="No trash items selected")
    unique = sorted(set(body.indices))
    trash = read_trash_rows()
    for idx in unique:
        if idx < 0 or idx >= len(trash):
            raise HTTPException(status_code=404, detail=f"Trash item not found at index {idx}")

    if body.action == "restore":
        restored = 0
        for idx in sorted(unique, reverse=True):
            try:
                restore_trash_index(idx)
                restored += 1
            except IndexError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
        return BulkJobResponse(updated=restored)

    if body.action == "permanent_delete":
        try:
            deleted = permanent_delete_trash_indices(unique)
        except IndexError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return BulkJobResponse(updated=deleted)

    raise HTTPException(status_code=400, detail="Invalid bulk trash action")


@app.get("/api/statuses")
def get_statuses() -> StatusesConfig:
    return load_statuses()


@app.get("/api/analytics")
def get_analytics(period: str = Query("beginning")) -> dict[str, Any]:
    """Status mix and pipeline progression for the selected time range."""
    if period not in PERIODS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid period '{period}'. Allowed: {list(PERIODS)}",
        )
    cfg = load_statuses()
    return build_analytics(
        read_rows(),
        period=period,
        statuses=cfg.statuses,
        labels=cfg.labels,
        default_status=cfg.default_status,
        progression=cfg.progression.model_dump(),
    )


@app.get("/api/profile")
def get_profile() -> ProfileResponse:
    data = parse_profile()
    return ProfileResponse(**data)


@app.put("/api/profile")
def update_profile(body: ProfileUpdate) -> ProfileResponse:
    if not body.sections:
        raise HTTPException(status_code=400, detail="At least one profile section is required")
    try:
        write_profile([s.model_dump() for s in body.sections])
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ProfileResponse(**parse_profile())


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
