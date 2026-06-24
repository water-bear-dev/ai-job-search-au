#!/usr/bin/env python3
"""Move legacy flat or split CV/cover-letter files into applied_jobs/<folder>/."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TRACKER_CSV = REPO_ROOT / "job_search_tracker.csv"

sys.path.insert(0, str(REPO_ROOT / "tools"))
from application_paths import application_paths, parse_folder_date  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / "tracker"))
from csv_store import read_rows, write_rows  # noqa: E402

MOVE_SUFFIXES = {".tex", ".pdf", ".aux", ".log", ".out", ".synctex.gz", ".fls", ".fdb_latexmk"}


def move_tex_bundle(src_tex: str, dest_tex: str, dry_run: bool) -> None:
    src = REPO_ROOT / src_tex
    dest = REPO_ROOT / dest_tex
    if not src.exists():
        print(f"skip missing: {src_tex}")
        return
    if src.resolve() == dest.resolve():
        print(f"already in place: {dest_tex}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    for path in src.parent.glob(f"{src.stem}.*"):
        if path.suffix not in MOVE_SUFFIXES:
            continue
        target = dest.parent / f"{dest.stem}{path.suffix}"
        print(f"move {path.relative_to(REPO_ROOT)} -> {target.relative_to(REPO_ROOT)}")
        if not dry_run:
            shutil.move(str(path), str(target))


def migrate_tracker(dry_run: bool, full_name: str = "Andrew Pham") -> None:
    rows = read_rows()
    changed = False
    for row in rows:
        cv_old = row.get("cv_file", "")
        cover_old = row.get("cover_letter_file", "")
        if not cv_old and not cover_old:
            continue
        on_date = parse_folder_date(row.get("date") or None)
        paths = application_paths(
            row["company"],
            row["role"],
            full_name,
            on_date=on_date,
        )
        move_tex_bundle(cv_old, paths["cv_tex"], dry_run)
        move_tex_bundle(cover_old, paths["cover_letter_tex"], dry_run)
        if row["cv_file"] != paths["cv_tex"] or row["cover_letter_file"] != paths["cover_letter_tex"]:
            row["cv_file"] = paths["cv_tex"]
            row["cover_letter_file"] = paths["cover_letter_tex"]
            changed = True
    if changed and not dry_run:
        write_rows(rows)
        print("Updated job_search_tracker.csv")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--full-name", default="Andrew Pham")
    args = parser.parse_args()
    if not TRACKER_CSV.exists():
        print("No job_search_tracker.csv found")
        return 0
    migrate_tracker(args.dry_run, full_name=args.full_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
