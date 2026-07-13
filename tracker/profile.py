"""Parse candidate profile from AGENTS.md for the tracker UI."""

from __future__ import annotations

import re
from pathlib import Path

from csv_store import REPO_ROOT

AGENTS_PATH = REPO_ROOT / "AGENTS.md"
_PROFILE_START = re.compile(r"^##\s+Candidate Profile\s*$", re.MULTILINE)
_SECTION = re.compile(r"^###\s+(.+)$", re.MULTILINE)
_BOLD = re.compile(r"\*\*([^*]+)\*\*")


def _strip_markdown_inline(text: str) -> str:
    text = _BOLD.sub(r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return text.strip()


def _profile_bounds(content: str) -> tuple[int, int] | None:
    """Return (body_start, body_end) indices for the Candidate Profile block body."""
    start = _PROFILE_START.search(content)
    if not start:
        return None
    rest = content[start.end() :]
    end_match = re.search(r"^##\s+", rest, re.MULTILINE)
    body_start = start.end()
    body_end = start.end() + (end_match.start() if end_match else len(rest))
    return body_start, body_end


def parse_profile(path: Path | None = None) -> dict:
    """Return ``{ sections: [{ title, items, raw }] }`` from AGENTS.md."""
    agents_path = path or AGENTS_PATH
    if not agents_path.is_file():
        return {"sections": []}

    content = agents_path.read_text(encoding="utf-8")
    bounds = _profile_bounds(content)
    if not bounds:
        return {"sections": []}

    body_start, body_end = bounds
    block = content[body_start:body_end]

    sections: list[dict] = []
    matches = list(_SECTION.finditer(block))
    for idx, match in enumerate(matches):
        title = match.group(1).strip()
        section_start = match.end()
        section_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(block)
        body = block[section_start:section_end]
        raw = body.strip()
        items: list[str] = []
        for line in body.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("- "):
                items.append(_strip_markdown_inline(stripped[2:]))
            elif stripped.startswith("  - "):
                items.append(_strip_markdown_inline(stripped[4:]))
        if items or raw:
            sections.append({"title": title, "items": items, "raw": raw})

    return {"sections": sections}


def write_profile(sections: list[dict], path: Path | None = None) -> None:
    """Replace the Candidate Profile body in AGENTS.md (and CLAUDE.md symlink)."""
    agents_path = path or AGENTS_PATH
    if not agents_path.is_file():
        raise FileNotFoundError("AGENTS.md not found")

    content = agents_path.read_text(encoding="utf-8")
    bounds = _profile_bounds(content)
    if not bounds:
        raise ValueError("Candidate Profile section not found in AGENTS.md")

    body_start, body_end = bounds
    parts: list[str] = []
    for section in sections:
        title = str(section.get("title", "")).strip()
        if not title:
            continue
        raw = str(section.get("raw", "")).strip()
        parts.append(f"### {title}\n{raw}" if raw else f"### {title}")

    new_body = "\n\n".join(parts)
    if new_body:
        new_body = f"\n\n{new_body}\n"
    else:
        new_body = "\n"

    agents_path.write_text(content[:body_start] + new_body + content[body_end:], encoding="utf-8")
