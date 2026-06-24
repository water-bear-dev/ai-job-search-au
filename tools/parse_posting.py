#!/usr/bin/env python3
"""Normalize job posting input for /apply and /evaluate.

Accepts a SEEK/LinkedIn URL, another job-board URL, or structured pasted text.
Returns a single JSON document on stdout for the agent workflow.

Usage:
  python tools/parse_posting.py "https://www.seek.com.au/job/92686067"
  python tools/parse_posting.py --text "Company: Acme\\nRole: Engineer\\n\\n---\\n..."
  python tools/parse_posting.py --file posting.txt
  python tools/parse_posting.py --text "<fetched text>" --source-url "https://..."
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent
SEEK_CLI = REPO_ROOT / "tools" / "seek-search" / "seek_search.py"
LINKEDIN_CLI = REPO_ROOT / "tools" / "linkedin-search" / "linkedin_search.py"

_SEEK_JOB_RE = re.compile(r"(?:seek\.com\.au/job/|jobId=|/job/)(\d{6,})", re.I)
_LINKEDIN_JOB_RE = re.compile(r"linkedin\.com/jobs", re.I)
_URL_RE = re.compile(r"^https?://", re.I)

_HEADER_KEYS = {
    "company": re.compile(r"^(?:company|employer)\s*:\s*(.*)$", re.I),
    "role": re.compile(r"^(?:role|title|position|job\s*title)\s*:\s*(.*)$", re.I),
    "location": re.compile(r"^location\s*:\s*(.*)$", re.I),
    "source_url": re.compile(r"^(?:url|link|source)\s*:\s*(.*)$", re.I),
    "salary": re.compile(r"^salary\s*:\s*(.*)$", re.I),
}


def _empty_result() -> dict[str, Any]:
    return {
        "status": "error",
        "channel": "paste",
        "company": "",
        "role": "",
        "location": "",
        "salary": "",
        "work_type": "",
        "description": "",
        "source_url": "",
        "warnings": [],
        "error": None,
        "raw": {},
    }


def _is_bare_seek_id(value: str) -> bool:
    return value.strip().isdigit() and len(value.strip()) >= 6


def _is_seek_input(value: str) -> bool:
    value = value.strip()
    if _is_bare_seek_id(value):
        return True
    return bool(_SEEK_JOB_RE.search(value))


def _is_linkedin_input(value: str) -> bool:
    return bool(_LINKEDIN_JOB_RE.search(value.strip()))


def _is_url(value: str) -> bool:
    return bool(_URL_RE.match(value.strip()))


def _run_cli(cli: Path, detail_arg: str) -> dict[str, Any]:
    cmd = [sys.executable, str(cli), "--detail", detail_arg]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "subprocess failed").strip()
        raise RuntimeError(err)
    return json.loads(proc.stdout)


def _from_seek(raw: dict[str, Any]) -> dict[str, Any]:
    out = _empty_result()
    out["status"] = "ok"
    out["channel"] = "SEEK"
    out["company"] = raw.get("company", "")
    out["role"] = raw.get("title", "")
    out["location"] = raw.get("location", "")
    out["salary"] = raw.get("salary", "")
    out["work_type"] = raw.get("work_type", "")
    out["description"] = raw.get("description", "") or raw.get("abstract", "")
    out["source_url"] = raw.get("url", "")
    out["raw"] = raw
    if not out["description"]:
        out["warnings"].append("SEEK detail returned no description text")
    return out


def _from_linkedin(raw: dict[str, Any]) -> dict[str, Any]:
    out = _empty_result()
    out["status"] = "ok"
    out["channel"] = "LinkedIn"
    out["company"] = raw.get("company", "")
    out["role"] = raw.get("title", "")
    out["location"] = raw.get("location", "")
    out["work_type"] = raw.get("employment_type", "")
    out["description"] = raw.get("description", "")
    out["source_url"] = raw.get("url", "")
    out["raw"] = raw
    if raw.get("seniority"):
        out["warnings"].append(f"Seniority: {raw['seniority']}")
    if not out["description"]:
        out["warnings"].append("LinkedIn detail returned no description text")
    return out


def _finalize_paste(
    headers: dict[str, str],
    description: str,
    *,
    channel: str = "paste",
    source_url_override: str | None = None,
) -> dict[str, Any]:
    out = _empty_result()
    out["channel"] = channel
    out["company"] = headers.get("company", "").strip()
    out["role"] = headers.get("role", "").strip()
    out["location"] = headers.get("location", "").strip()
    out["salary"] = headers.get("salary", "").strip()
    out["description"] = description.strip()
    out["source_url"] = (source_url_override or headers.get("source_url", "")).strip()

    missing = []
    if not out["company"]:
        missing.append("company")
    if not out["role"]:
        missing.append("role")
    if not out["description"]:
        missing.append("description")

    if missing:
        out["status"] = "incomplete"
        out["warnings"].append(f"Missing: {', '.join(missing)}")
    else:
        out["status"] = "ok"

    return out


def parse_paste(text: str, *, source_url: str | None = None) -> dict[str, Any]:
    """Parse structured pasted posting text."""
    text = text.strip()
    if not text:
        out = _empty_result()
        out["error"] = "empty input"
        return out

    # Split on --- separator if present
    body = text
    headers_block = ""
    if re.search(r"^\s*---\s*$", text, re.M):
        parts = re.split(r"^\s*---\s*$", text, maxsplit=1, flags=re.M)
        headers_block = parts[0]
        body = parts[1] if len(parts) > 1 else ""
    else:
        lines = text.splitlines()
        header_lines: list[str] = []
        body_lines: list[str] = []
        in_headers = True
        for line in lines:
            if in_headers and any(pat.match(line.strip()) for pat in _HEADER_KEYS.values()):
                header_lines.append(line)
            elif in_headers and line.strip() == "" and header_lines:
                in_headers = False
            elif in_headers and header_lines and not any(pat.match(line.strip()) for pat in _HEADER_KEYS.values()):
                in_headers = False
                body_lines.append(line)
            elif in_headers and not header_lines:
                body_lines.append(line)
            else:
                body_lines.append(line)
        if header_lines:
            headers_block = "\n".join(header_lines)
            body = "\n".join(body_lines)

    headers: dict[str, str] = {}
    for line in headers_block.splitlines():
        line = line.strip()
        if not line:
            continue
        for key, pat in _HEADER_KEYS.items():
            m = pat.match(line)
            if m:
                headers[key] = m.group(1).strip()
                break

    if not headers and not re.search(r"^\s*---\s*$", text, re.M):
        lines = [ln for ln in text.splitlines() if ln.strip()]
        if lines:
            headers["role"] = lines[0].strip()
            body = "\n".join(lines[1:]) if len(lines) > 1 else ""

    return _finalize_paste(headers, body, source_url_override=source_url)


def parse_input(value: str, *, source_url: str | None = None) -> dict[str, Any]:
    """Route URL or paste text to the appropriate parser."""
    value = value.strip()
    if not value:
        out = _empty_result()
        out["error"] = "empty input"
        return out

    if _is_seek_input(value):
        try:
            return _from_seek(_run_cli(SEEK_CLI, value))
        except (RuntimeError, json.JSONDecodeError, FileNotFoundError) as exc:
            out = _empty_result()
            out["channel"] = "SEEK"
            out["status"] = "error"
            out["error"] = str(exc)
            out["source_url"] = value if _is_url(value) else f"https://www.seek.com.au/job/{value.strip()}"
            return out

    if _is_linkedin_input(value):
        try:
            return _from_linkedin(_run_cli(LINKEDIN_CLI, value))
        except (RuntimeError, json.JSONDecodeError, FileNotFoundError) as exc:
            out = _empty_result()
            out["channel"] = "LinkedIn"
            out["status"] = "error"
            out["error"] = str(exc)
            out["source_url"] = value
            return out

    if _is_url(value):
        out = _empty_result()
        out["status"] = "webfetch_required"
        out["channel"] = "web"
        out["source_url"] = value.strip()
        parsed = urlparse(value)
        if parsed.netloc:
            out["warnings"].append(f"Fetch content from {parsed.netloc} via WebFetch, then re-run with --text")
        return out

    return parse_paste(value, source_url=source_url)


def print_table(result: dict[str, Any]) -> None:
    print(f"status:  {result['status']}")
    print(f"channel: {result['channel']}")
    if result.get("company"):
        print(f"company: {result['company']}")
    if result.get("role"):
        print(f"role:    {result['role']}")
    if result.get("location"):
        print(f"location: {result['location']}")
    if result.get("source_url"):
        print(f"url:     {result['source_url']}")
    if result.get("error"):
        print(f"error:   {result['error']}")
    for w in result.get("warnings") or []:
        print(f"warning: {w}")
    desc = result.get("description") or ""
    if desc:
        preview = desc[:300] + ("..." if len(desc) > 300 else "")
        print(f"\ndescription ({len(desc)} chars):\n{preview}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize job posting input for /apply and /evaluate")
    parser.add_argument("input", nargs="?", help="URL or pasted posting text")
    parser.add_argument("--text", help="Posting text (alternative to positional input)")
    parser.add_argument("--file", type=Path, help="Read posting text from file")
    parser.add_argument("--source-url", help="Canonical URL when parsing fetched/pasted text")
    parser.add_argument("--table", action="store_true", help="Human-readable summary instead of JSON")
    args = parser.parse_args()

    if args.file:
        if not args.file.is_file():
            print(json.dumps({"status": "error", "error": f"file not found: {args.file}"}), file=sys.stderr)
            return 1
        content = args.file.read_text(encoding="utf-8")
        result = parse_paste(content, source_url=args.source_url) if args.source_url else parse_input(content)
    elif args.text is not None:
        if args.source_url:
            result = parse_paste(args.text, source_url=args.source_url)
            if result["status"] == "ok":
                result["channel"] = "web"
        else:
            result = parse_input(args.text)
    elif args.input is not None:
        result = parse_input(args.input)
    else:
        parser.error("provide input, --text, or --file")

    if args.table:
        print_table(result)
    else:
        json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")

    if result["status"] == "error" and result.get("error"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
