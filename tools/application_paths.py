#!/usr/bin/env python3
"""Application folder and file paths for CV / cover letter outputs.

Folder format:
  applied_jobs/<YYYYMMDD>-<companyName>-<position>/

Both CV and cover letter for an application live in the same dated folder.

Example:
  applied_jobs/20260622-NorthernHealth-AIEngineerAgenticAIAndAdvancedAnalytics/
    Andrew_Pham_CV.tex
    Andrew_Pham_CoverLetter.tex

Usage:
  python tools/application_paths.py \\
    --company "Northern Health" \\
    --role "AI Engineer (Agentic AI and Advanced Analytics)" \\
    --full-name "Andrew Pham" \\
    --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
APPLIED_JOBS_DIR = "applied_jobs"


def pascal_slug(text: str, max_len: int = 48) -> str:
    """Alphanumeric words joined in PascalCase (e.g. Northern Health -> NorthernHealth)."""
    words = re.findall(r"[A-Za-z0-9]+", text or "")
    if not words:
        return "Unknown"
    part = "".join(w[0].upper() + w[1:] for w in words)
    return part[:max_len] if max_len else part


def full_name_slug(full_name: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", full_name or "")
    return "_".join(words) if words else "Candidate"


def parse_folder_date(value: str | None) -> date:
    if not value:
        return date.today()
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Invalid date '{value}' — use YYYY-MM-DD or YYYYMMDD")


def build_application_folder(
    company: str,
    role: str,
    *,
    on_date: date | None = None,
) -> str:
    """Return `<YYYYMMDD>-<companyName>-<position>`."""
    day = (on_date or date.today()).strftime("%Y%m%d")
    company_part = pascal_slug(company, max_len=32)
    role_part = pascal_slug(role, max_len=48)
    return f"{day}-{company_part}-{role_part}"


def application_paths(
    company: str,
    role: str,
    full_name: str,
    *,
    on_date: date | None = None,
) -> dict[str, str]:
    folder = build_application_folder(company, role, on_date=on_date)
    app_dir_rel = f"{APPLIED_JOBS_DIR}/{folder}"
    app_dir = REPO_ROOT / app_dir_rel
    name = full_name_slug(full_name)
    cv_tex = app_dir / f"{name}_CV.tex"
    cover_tex = app_dir / f"{name}_CoverLetter.tex"
    return {
        "application_folder": folder,
        "applied_jobs_dir": app_dir_rel,
        "cv_dir": app_dir_rel,
        "cover_letter_dir": app_dir_rel,
        "cv_tex": str(cv_tex.relative_to(REPO_ROOT)),
        "cover_letter_tex": str(cover_tex.relative_to(REPO_ROOT)),
        "cv_pdf": str(cv_tex.with_suffix(".pdf").relative_to(REPO_ROOT)),
        "cover_letter_pdf": str(cover_tex.with_suffix(".pdf").relative_to(REPO_ROOT)),
        "full_name_slug": name,
        "cv_build_dir": str((app_dir / "build").relative_to(REPO_ROOT)),
        "cover_letter_build_dir": str((app_dir / "build").relative_to(REPO_ROOT)),
    }


def ensure_application_dirs(paths: dict[str, str]) -> None:
    (REPO_ROOT / paths["applied_jobs_dir"]).mkdir(parents=True, exist_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute application output paths")
    parser.add_argument("--company", required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--full-name", default="Andrew Pham")
    parser.add_argument("--date", help="Folder date YYYY-MM-DD or YYYYMMDD (default: today)")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--mkdir", action="store_true", help="Create applied_jobs/<folder>/")
    args = parser.parse_args()

    try:
        on_date = parse_folder_date(args.date)
        paths = application_paths(args.company, args.role, args.full_name, on_date=on_date)
        if args.mkdir:
            ensure_application_dirs(paths)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(paths, indent=2))
    else:
        print(paths["application_folder"])
        print(paths["cv_tex"])
        print(paths["cover_letter_tex"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
