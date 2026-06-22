#!/usr/bin/env python3
"""Archive or purge LaTeX build artifacts under cv/ and cover_letters/.

Artifacts live in ``<application_folder>/build/``. Loose ``.aux`` / ``.log`` / ``.out``
files next to ``.tex`` are moved into ``build/`` on archive.

Usage:
  python tools/cleanup_latex.py              # archive loose artifacts now
  python tools/cleanup_latex.py --purge        # delete all build/ contents
  python tools/cleanup_latex.py --daily       # end-of-day: archive + purge build/
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BUILD_DIR_NAME = "build"

ARTIFACT_SUFFIXES = {
    ".aux",
    ".log",
    ".out",
    ".synctex.gz",
    ".fls",
    ".fdb_latexmk",
}

SCAN_ROOTS = ("cv", "cover_letters")
SKIP_DIR_NAMES = {"OpenFonts", "build", "__pycache__"}


def is_application_dir(path: Path) -> bool:
    if not path.is_dir():
        return False
    if path.name in SKIP_DIR_NAMES:
        return False
    if path.name.startswith("."):
        return False
    # dated application folders (YYYYMMDD-...) or legacy flat dirs with .tex
    return any(path.glob("*.tex")) or (path / BUILD_DIR_NAME).is_dir()


def iter_application_dirs(root: Path) -> list[Path]:
    dirs: list[Path] = []
    if not root.is_dir():
        return dirs
    for child in sorted(root.iterdir()):
        if child.is_dir() and is_application_dir(child):
            dirs.append(child)
    return dirs


def archive_loose_artifacts(app_dir: Path, dry_run: bool = False) -> int:
    """Move stray build artifacts from app_dir into app_dir/build/."""
    build_dir = app_dir / BUILD_DIR_NAME
    moved = 0
    for path in sorted(app_dir.iterdir()):
        if not path.is_file():
            continue
        if path.suffix not in ARTIFACT_SUFFIXES:
            continue
        target = build_dir / path.name
        print(f"archive {path.relative_to(REPO_ROOT)} -> {target.relative_to(REPO_ROOT)}")
        if not dry_run:
            build_dir.mkdir(parents=True, exist_ok=True)
            if target.exists():
                target.unlink()
            shutil.move(str(path), str(target))
        moved += 1
    return moved


def archive_root_loose(root: Path, dry_run: bool = False) -> int:
    """Move loose artifacts sitting directly under cv/ or cover_letters/."""
    build_dir = root / "_build"
    moved = 0
    if not root.is_dir():
        return moved
    for path in sorted(root.iterdir()):
        if not path.is_file() or path.suffix not in ARTIFACT_SUFFIXES:
            continue
        target = build_dir / path.name
        print(f"archive {path.relative_to(REPO_ROOT)} -> {target.relative_to(REPO_ROOT)}")
        if not dry_run:
            build_dir.mkdir(parents=True, exist_ok=True)
            if target.exists():
                target.unlink()
            shutil.move(str(path), str(target))
        moved += 1
    return moved


def purge_directory(dir_path: Path, dry_run: bool = False, older_than_days: int | None = None) -> int:
    if not dir_path.is_dir():
        return 0
    removed = 0
    cutoff = None
    if older_than_days is not None:
        cutoff = datetime.now().timestamp() - older_than_days * 86400
    for path in sorted(dir_path.iterdir()):
        if path.is_dir():
            continue
        if cutoff is not None and path.stat().st_mtime > cutoff:
            continue
        print(f"purge {path.relative_to(REPO_ROOT)}")
        if not dry_run:
            path.unlink()
        removed += 1
    if not dry_run and dir_path.is_dir() and not any(dir_path.iterdir()):
        dir_path.rmdir()
    return removed


def purge_build_dir(app_dir: Path, dry_run: bool = False, older_than_days: int | None = None) -> int:
    return purge_directory(app_dir / BUILD_DIR_NAME, dry_run=dry_run, older_than_days=older_than_days)


def sweep(
    *,
    archive: bool = True,
    purge: bool = False,
    older_than_days: int | None = None,
    dry_run: bool = False,
) -> dict[str, int]:
    stats = {"archived": 0, "purged": 0, "folders": 0}
    for root_name in SCAN_ROOTS:
        root = REPO_ROOT / root_name
        stats["archived"] += archive_root_loose(root, dry_run=dry_run)
        for app_dir in iter_application_dirs(root):
            stats["folders"] += 1
            if archive:
                stats["archived"] += archive_loose_artifacts(app_dir, dry_run=dry_run)
            if purge:
                stats["purged"] += purge_build_dir(
                    app_dir, dry_run=dry_run, older_than_days=older_than_days
                )
        if purge:
            stats["purged"] += purge_directory(
                root / "_build", dry_run=dry_run, older_than_days=older_than_days
            )
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Cleanup LaTeX build artifacts")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--purge",
        action="store_true",
        help="Delete files inside build/ folders (keeps .tex and .pdf in application folder)",
    )
    parser.add_argument(
        "--daily",
        action="store_true",
        help="End-of-day mode: archive loose files, then purge all build/ contents",
    )
    parser.add_argument(
        "--archive-only",
        action="store_true",
        help="Only move loose artifacts into build/ (default if neither flag set)",
    )
    args = parser.parse_args()

    if args.daily:
        archive, purge = True, True
    elif args.purge:
        archive, purge = False, True
    else:
        archive, purge = True, False

    stats = sweep(archive=archive, purge=purge, dry_run=args.dry_run)
    print(
        f"done: {stats['folders']} folders, "
        f"{stats['archived']} archived, {stats['purged']} purged"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
