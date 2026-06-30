#!/usr/bin/env python3
"""Render CV/cover-letter HTML to PDF via headless Chrome, Edge, or Chromium.

No LaTeX required. Uses the same OpenFonts as cover.cls (via templates/*.css).

Usage:
  python tools/html_build.py applied_jobs/.../Andrew_Pham_CV.html
  python tools/html_build.py \\
    --cv applied_jobs/.../Andrew_Pham_CV.html \\
    --cover applied_jobs/.../Andrew_Pham_CoverLetter.html

If no browser is found, exits 2 and prints instructions to open the .html
file in any browser and Print → Save as PDF.
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

REPO_ROOT = Path(__file__).resolve().parent.parent

# 2.3 cm ≈ 0.91 inch margins (cover.cls geometry)
PRINT_MARGINS_IN = 0.91


def _browser_candidates() -> list[list[str]]:
    system = platform.system()
    candidates: list[list[str]] = []

    if system == "Darwin":
        candidates.extend([
            [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "--headless=new",
                "--disable-gpu",
            ],
            [
                "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                "--headless=new",
                "--disable-gpu",
            ],
            [
                "/Applications/Chromium.app/Contents/MacOS/Chromium",
                "--headless=new",
                "--disable-gpu",
            ],
        ])
    elif system == "Windows":
        local = os.environ.get("LOCALAPPDATA", "")
        program_files = os.environ.get("PROGRAMFILES", r"C:\Program Files")
        for rel in (
            r"Google\Chrome\Application\chrome.exe",
            r"Microsoft\Edge\Application\msedge.exe",
        ):
            for base in (program_files, local):
                if base:
                    exe = Path(base) / rel
                    if exe.is_file():
                        candidates.append([str(exe), "--headless=new", "--disable-gpu"])
    else:
        for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge"):
            found = shutil.which(name)
            if found:
                candidates.append([found, "--headless=new", "--disable-gpu"])

    return candidates


def find_browser() -> list[str] | None:
    for prefix in _browser_candidates():
        exe = Path(prefix[0])
        if exe.is_file():
            return prefix
    return None


def file_uri(path: Path) -> str:
    resolved = path.resolve()
    return "file://" + quote(resolved.as_posix(), safe="/:")


def render_html_to_pdf(html_path: Path, pdf_path: Path, browser_prefix: list[str]) -> None:
    html_path = html_path.resolve()
    pdf_path = pdf_path.resolve()
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        *browser_prefix,
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}",
        file_uri(html_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        stderr = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"browser print failed ({result.returncode}): {stderr[:500]}")
    if not pdf_path.is_file():
        raise FileNotFoundError(f"Expected PDF not produced: {pdf_path}")


def build_html(html_path: Path) -> Path:
    html_path = html_path.resolve()
    if not html_path.is_file():
        raise FileNotFoundError(html_path)
    if html_path.suffix.lower() != ".html":
        raise ValueError(f"Expected .html file: {html_path}")

    browser = find_browser()
    pdf_path = html_path.with_suffix(".pdf")

    if browser is None:
        print(
            "error: no headless Chrome, Edge, or Chromium found.\n"
            f"  Open {html_path} in any browser → Print → Save as PDF.\n"
            "  Install Google Chrome or Microsoft Edge for automated PDF output.",
            file=sys.stderr,
        )
        raise SystemExit(2)

    render_html_to_pdf(html_path, pdf_path, browser)
    return pdf_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Render HTML CV/cover letter to PDF")
    parser.add_argument("html", nargs="?", help="Single .html file to render")
    parser.add_argument("--cv", help="CV .html path")
    parser.add_argument("--cover", help="Cover letter .html path")
    args = parser.parse_args()

    paths: list[Path] = []
    if args.html:
        paths.append(REPO_ROOT / args.html)
    if args.cv:
        paths.append(REPO_ROOT / args.cv)
    if args.cover:
        paths.append(REPO_ROOT / args.cover)
    if not paths:
        parser.error("provide an .html path or --cv / --cover")

    try:
        for path in paths:
            pdf = build_html(path)
            print(f"rendered: {pdf.relative_to(REPO_ROOT)}")
    except SystemExit:
        raise
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
