#!/usr/bin/env python3
"""One-shot: migrate draft statuses in job_search_tracker.csv to applied."""

from __future__ import annotations

import sys

from csv_store import migrate_draft_rows_to_applied


def main() -> int:
    updated = migrate_draft_rows_to_applied()
    print(f"migrated {updated} draft row(s) to applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
