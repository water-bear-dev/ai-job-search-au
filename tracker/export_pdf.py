"""Build a printable PDF log of submitted job applications."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from io import BytesIO
from typing import Iterable

from fpdf import FPDF
from fpdf.fonts import FontFace

from analytics import parse_job_datetime, resolve_status

SUBMITTED_STATUSES = frozenset(
    {
        "applied",
        "phone_screen",
        "interview",
        "offer",
        "rejected",
        "withdrawn",
        "no_response",
    }
)

EXCLUDED_RAW_STATUSES = frozenset(
    {
        "draft",
        "drafted",
        "ready to apply",
        "prepared",
    }
)

SOURCE_MAX_LEN = 56


def _created_at(row: dict[str, str]) -> str:
    return (row.get("created_at") or row.get("date") or "").strip()


def _date_only(value: str) -> str:
    dt = parse_job_datetime(value)
    if dt is None:
        return (value or "")[:10] or "-"
    return dt.strftime("%Y-%m-%d")


def _pdf_safe(text: str) -> str:
    """Helvetica core fonts are Latin-1; replace unsupported characters."""
    text = (text or "").replace("\u2026", "...").replace("\u2013", "-").replace("\u2014", "-")
    text = text.replace("\u2018", "'").replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _truncate(text: str, max_len: int = SOURCE_MAX_LEN) -> str:
    text = _pdf_safe(text).strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def is_submitted_status(
    raw: str,
    *,
    default_status: str,
    aliases: dict[str, str] | None = None,
) -> bool:
    """True when the row should appear on the applied-jobs export."""
    lowered = (raw or "").strip().lower()
    if lowered in EXCLUDED_RAW_STATUSES:
        return False
    resolved = resolve_status(raw, default_status, aliases)
    return resolved in SUBMITTED_STATUSES


def filter_submitted_rows(
    rows: Iterable[dict[str, str]],
    *,
    default_status: str,
    aliases: dict[str, str] | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
) -> list[dict[str, str]]:
    """Filter to submitted apps in optional inclusive created_at range; newest first."""
    filtered: list[dict[str, str]] = []
    for row in rows:
        if not is_submitted_status(
            row.get("status", ""),
            default_status=default_status,
            aliases=aliases,
        ):
            continue
        created = parse_job_datetime(_created_at(row))
        if from_date is not None:
            if created is None or created < from_date:
                continue
        if to_date is not None:
            if created is None or created > to_date:
                continue
        filtered.append(row)
    filtered.sort(key=lambda r: _created_at(r), reverse=True)
    return filtered


def export_filename(from_date: datetime | None, to_date: datetime | None, rows: list[dict[str, str]]) -> str:
    """Filename applied-jobs-YYYY-MM-DD-YYYY-MM-DD.pdf (all-time uses data min/max)."""
    start = from_date
    end = to_date
    if start is None or end is None:
        dates = [parse_job_datetime(_created_at(r)) for r in rows]
        dates = [d for d in dates if d is not None]
        if dates:
            if start is None:
                start = min(dates)
            if end is None:
                end = max(dates)
    if start is None and end is None:
        return "applied-jobs-all.pdf"
    start_s = start.strftime("%Y-%m-%d") if start else "all"
    end_s = end.strftime("%Y-%m-%d") if end else "all"
    return f"applied-jobs-{start_s}-{end_s}.pdf"


def _range_label(from_date: datetime | None, to_date: datetime | None, rows: list[dict[str, str]]) -> str:
    if from_date is None and to_date is None:
        dates = [parse_job_datetime(_created_at(r)) for r in rows]
        dates = [d for d in dates if d is not None]
        if not dates:
            return "All time"
        return f"{min(dates).strftime('%Y-%m-%d')} to {max(dates).strftime('%Y-%m-%d')} (all time)"
    start_s = from_date.strftime("%Y-%m-%d") if from_date else "…"
    end_s = to_date.strftime("%Y-%m-%d") if to_date else "…"
    return f"{start_s} to {end_s}"


def _status_breakdown(
    rows: list[dict[str, str]],
    *,
    default_status: str,
    labels: dict[str, str],
    aliases: dict[str, str] | None,
    status_order: list[str],
) -> str:
    counts: Counter[str] = Counter()
    for row in rows:
        resolved = resolve_status(row.get("status", ""), default_status, aliases)
        counts[resolved] += 1
    parts: list[str] = []
    seen: set[str] = set()
    for code in status_order:
        if code not in SUBMITTED_STATUSES:
            continue
        n = counts.get(code, 0)
        if n:
            parts.append(f"{labels.get(code, code)} {n}")
            seen.add(code)
    for code, n in counts.most_common():
        if code in seen or not n:
            continue
        parts.append(f"{labels.get(code, code)} {n}")
    return " · ".join(parts) if parts else "-"


class _AppliedJobsPDF(FPDF):
    def __init__(self, generated_at: str):
        super().__init__(orientation="L", format="A4", unit="mm")
        self.generated_at = generated_at
        self.set_auto_page_break(auto=True, margin=18)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", size=8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, f"Generated {self.generated_at}", align="L")
        self.cell(0, 5, f"Page {self.page_no()}/{{nb}}", align="R")


def build_applied_jobs_pdf(
    rows: list[dict[str, str]],
    *,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    default_status: str = "applied",
    labels: dict[str, str] | None = None,
    aliases: dict[str, str] | None = None,
    status_order: list[str] | None = None,
    generated_at: datetime | None = None,
) -> bytes:
    """Return PDF bytes for the given submitted application rows."""
    labels = labels or {}
    aliases = aliases or {}
    status_order = status_order or list(SUBMITTED_STATUSES)
    generated = generated_at or datetime.now()
    generated_s = generated.strftime("%Y-%m-%d %H:%M")

    pdf = _AppliedJobsPDF(generated_at=generated_s)
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(20, 20, 20)
    pdf.cell(0, 8, "Applied jobs", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", size=10)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(
        0,
        6,
        f"Application date range: {_range_label(from_date, to_date, rows)}",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    total = len(rows)
    noun = "application" if total == 1 else "applications"
    pdf.cell(0, 6, f"Total: {total} {noun}", new_x="LMARGIN", new_y="NEXT")
    breakdown = _status_breakdown(
        rows,
        default_status=default_status,
        labels=labels,
        aliases=aliases,
        status_order=status_order,
    )
    pdf.multi_cell(0, 6, f"Status: {breakdown}")
    pdf.ln(2)

    heading_style = FontFace(emphasis="BOLD", size_pt=9, color=(255, 255, 255), fill_color=(40, 40, 40))
    # Landscape A4 usable width ~277mm with default margins
    col_widths = (28, 42, 70, 28, 24, 85)

    with pdf.table(
        col_widths=col_widths,
        text_align=("LEFT", "LEFT", "LEFT", "LEFT", "LEFT", "LEFT"),
        line_height=5,
        headings_style=heading_style,
        first_row_as_headings=True,
        repeat_headings=1,
        padding=1.5,
    ) as table:
        header = table.row()
        for label in ("Date", "Company", "Role", "Status", "Fit", "Source"):
            header.cell(label)

        pdf.set_font("Helvetica", size=8)
        for row in rows:
            status_code = resolve_status(row.get("status", ""), default_status, aliases)
            status_label = labels.get(status_code, status_code)
            fit = (row.get("fit_rating") or "").strip() or "-"
            source = _truncate(row.get("source", "")) or "-"
            cells = (
                _date_only(_created_at(row)),
                _pdf_safe((row.get("company") or "").strip()) or "-",
                _pdf_safe((row.get("role") or "").strip()) or "-",
                _pdf_safe(status_label),
                _pdf_safe(fit),
                source,
            )
            tr = table.row()
            for value in cells:
                tr.cell(value)

    buffer = BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()
