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


def parse_profile(path: Path | None = None) -> dict:
    """Return ``{ sections: [{ title, items }] }`` from AGENTS.md."""
    agents_path = path or AGENTS_PATH
    if not agents_path.is_file():
        return {"sections": []}

    content = agents_path.read_text(encoding="utf-8")
    start = _PROFILE_START.search(content)
    if not start:
        return {"sections": []}

    rest = content[start.end() :]
    end_match = re.search(r"^##\s+", rest, re.MULTILINE)
    block = rest[: end_match.start()] if end_match else rest

    sections: list[dict] = []
    matches = list(_SECTION.finditer(block))
    for idx, match in enumerate(matches):
        title = match.group(1).strip()
        section_start = match.end()
        section_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(block)
        body = block[section_start:section_end]
        items: list[str] = []
        for line in body.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("- "):
                items.append(_strip_markdown_inline(stripped[2:]))
            elif stripped.startswith("  - "):
                items.append(_strip_markdown_inline(stripped[4:]))
        if items:
            sections.append({"title": title, "items": items})

    return {"sections": sections}
