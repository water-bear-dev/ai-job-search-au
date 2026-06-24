#!/usr/bin/env python3
"""Compile CV/cover-letter .tex with build artifacts in a ``build/`` subfolder.

Keeps ``.tex`` and final ``.pdf`` in the application folder; ``.aux``, ``.log``,
``.out``, etc. go under ``build/``.

Usage:
  python tools/latex_build.py applied_jobs/20260622-Company-Role/Andrew_Pham_CV.tex
  python tools/latex_build.py \\
    --cv applied_jobs/.../Andrew_Pham_CV.tex \\
    --cover applied_jobs/.../Andrew_Pham_CoverLetter.tex
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BUILD_DIR_NAME = "build"


def _engine_for(tex_path: Path) -> str:
    if "cover_letters" in tex_path.parts or tex_path.stem.endswith("_CoverLetter"):
        return "xelatex"
    return "lualatex"


def compile_tex(tex_path: Path, *, runs: int = 1) -> Path:
    tex_path = tex_path.resolve()
    if not tex_path.is_file():
        raise FileNotFoundError(tex_path)

    work_dir = tex_path.parent
    build_dir = work_dir / BUILD_DIR_NAME
    build_dir.mkdir(parents=True, exist_ok=True)

    engine = _engine_for(tex_path)
    cmd = [
        engine,
        "-interaction=nonstopmode",
        f"-output-directory={build_dir}",
        tex_path.name,
    ]

    for _ in range(runs):
        result = subprocess.run(cmd, cwd=work_dir, check=False)
        if result.returncode != 0:
            raise RuntimeError(f"{engine} failed ({result.returncode}) for {tex_path}")

    pdf_in_build = build_dir / tex_path.with_suffix(".pdf").name
    if not pdf_in_build.is_file():
        raise FileNotFoundError(f"Expected PDF not produced: {pdf_in_build}")

    pdf_final = tex_path.with_suffix(".pdf")
    shutil.copy2(pdf_in_build, pdf_final)
    return pdf_final


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile LaTeX into application build/ folder")
    parser.add_argument("tex", nargs="?", help="Single .tex file to compile")
    parser.add_argument("--cv", help="CV .tex path")
    parser.add_argument("--cover", help="Cover letter .tex path")
    args = parser.parse_args()

    paths: list[Path] = []
    if args.tex:
        paths.append(REPO_ROOT / args.tex)
    if args.cv:
        paths.append(REPO_ROOT / args.cv)
    if args.cover:
        paths.append(REPO_ROOT / args.cover)
    if not paths:
        parser.error("provide a .tex path or --cv / --cover")

    try:
        for path in paths:
            pdf = compile_tex(path)
            print(f"compiled: {pdf.relative_to(REPO_ROOT)}")
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
