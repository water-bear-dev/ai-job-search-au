"""Revision counter so the tracker UI can detect CSV changes from /apply or scripts."""

from __future__ import annotations

import os
import time
import urllib.error
import urllib.request

from csv_store import TRACKER_DIR

REVISION_PATH = TRACKER_DIR / ".data_revision"
DEFAULT_PORT = "8765"


def bump_revision() -> int:
    """Increment revision after job_search_tracker.csv changes."""
    revision = int(time.time() * 1000)
    REVISION_PATH.write_text(str(revision), encoding="utf-8")
    _notify_running_server(revision)
    return revision


def get_revision() -> int:
    if not REVISION_PATH.exists():
        return 0
    try:
        return int(REVISION_PATH.read_text(encoding="utf-8").strip() or "0")
    except ValueError:
        return 0


def _notify_running_server(revision: int) -> None:
    """Nudge the local tracker server so open browsers reload sooner."""
    port = os.environ.get("TRACKER_PORT", DEFAULT_PORT)
    url = f"http://127.0.0.1:{port}/api/revision"
    payload = str(revision).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={"Content-Type": "text/plain"},
    )
    try:
        with urllib.request.urlopen(request, timeout=0.5):
            pass
    except (urllib.error.URLError, TimeoutError, OSError):
        pass
