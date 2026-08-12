"""Application analytics: period filters, status mix, and pipeline progression."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any


PERIODS = ("week", "month", "quarter", "year", "beginning")


def parse_job_datetime(value: str) -> datetime | None:
    value = (value or "").strip()
    if not value:
        return None
    if len(value) == 10 and "T" not in value:
        value = f"{value}T00:00:00"
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def period_start(period: str, now: datetime | None = None) -> datetime | None:
    """Return inclusive local-calendar start for period, or None for beginning."""
    if period not in PERIODS:
        raise ValueError(f"Invalid period '{period}'. Allowed: {list(PERIODS)}")
    if period == "beginning":
        return None
    now = now or datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "week":
        return today - timedelta(days=today.weekday())
    if period == "month":
        return today.replace(day=1)
    if period == "quarter":
        quarter_month = (today.month - 1) // 3 * 3 + 1
        return today.replace(month=quarter_month, day=1)
    if period == "year":
        return today.replace(month=1, day=1)
    return None


def _created_at(row: dict[str, str]) -> str:
    return (row.get("created_at") or row.get("date") or "").strip()


def filter_rows_by_period(rows: list[dict[str, str]], period: str) -> list[dict[str, str]]:
    start = period_start(period)
    if start is None:
        return list(rows)
    filtered: list[dict[str, str]] = []
    for row in rows:
        created = parse_job_datetime(_created_at(row))
        if created is not None and created >= start:
            filtered.append(row)
    return filtered


def resolve_status(raw: str, default_status: str, aliases: dict[str, str] | None = None) -> str:
    status = (raw or "").strip() or default_status
    if aliases and status in aliases:
        return aliases[status]
    return status


def _percent(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((count / total) * 1000) / 10


def build_analytics(
    rows: list[dict[str, str]],
    *,
    period: str = "beginning",
    statuses: list[str],
    labels: dict[str, str],
    default_status: str,
    progression: dict[str, Any] | None = None,
) -> dict[str, Any]:
    progression = progression or {}
    aliases = dict(progression.get("aliases") or {})
    pipeline: list[str] = list(progression.get("pipeline") or [])
    closed: list[str] = list(progression.get("closed") or [])

    filtered = filter_rows_by_period(rows, period)
    total = len(filtered)

    counts_map: dict[str, int] = {code: 0 for code in statuses}
    resolved_statuses: list[str] = []
    for row in filtered:
        status = resolve_status(row.get("status", ""), default_status, aliases)
        resolved_statuses.append(status)
        counts_map[status] = counts_map.get(status, 0) + 1

    counts = [
        {
            "status": code,
            "label": labels.get(code, code),
            "count": counts_map.get(code, 0),
            "percent": _percent(counts_map.get(code, 0), total),
        }
        for code in statuses
    ]

    pipeline_ranks = {code: idx for idx, code in enumerate(pipeline)}
    reached = [0] * len(pipeline)
    current_in_pipeline = [0] * len(pipeline)

    active = 0
    success = 0
    closed_count = 0

    success_status = pipeline[-1] if pipeline else ""
    active_statuses = set(pipeline[:-1]) if len(pipeline) > 1 else set(pipeline)

    for status in resolved_statuses:
        if status in closed:
            closed_count += 1
            if pipeline:
                reached[0] += 1
            continue
        if status == success_status:
            success += 1
        elif status in active_statuses or status in pipeline_ranks:
            active += 1

        rank = pipeline_ranks.get(status)
        if rank is None:
            continue
        current_in_pipeline[rank] += 1
        for i in range(rank + 1):
            reached[i] += 1

    stages: list[dict[str, Any]] = []
    for idx, code in enumerate(pipeline):
        prev_reached = reached[idx - 1] if idx > 0 else None
        conversion = None
        if idx > 0 and prev_reached:
            conversion = _percent(reached[idx], prev_reached)
        elif idx > 0:
            conversion = 0.0
        stages.append(
            {
                "status": code,
                "label": labels.get(code, code),
                "current": current_in_pipeline[idx],
                "reached": reached[idx],
                "reached_percent": _percent(reached[idx], total),
                "conversion_from_previous": conversion,
            }
        )

    decided = success + closed_count
    return {
        "period": period,
        "total": total,
        "counts": counts,
        "progression": {
            "pipeline": pipeline,
            "closed": closed,
            "stages": stages,
            "active": active,
            "success": success,
            "closed_count": closed_count,
            "offer_rate": _percent(success, total),
            "close_rate": _percent(closed_count, total),
            "success_among_decided": _percent(success, decided) if decided else 0.0,
        },
    }
