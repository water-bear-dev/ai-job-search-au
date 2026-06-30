#!/usr/bin/env python3
"""Upsert a job application row after /apply completes.

Usage:
  python upsert_application.py \\
    --company "Northern Health" \\
    --role "AI Engineer (Agentic AI and Advanced Analytics)" \\
    --cv-file "cv/northern_health/Andrew_Pham_CV.tex" \\
    --cover-letter-file "cover_letters/northern_health/Andrew_Pham_CoverLetter.tex" \\
    --source "https://www.seek.com.au/job/92686067" \\
    --fit-rating "strong fit"
"""

from __future__ import annotations

import argparse
import json
import sys

from csv_store import upsert_application


def main() -> int:
    parser = argparse.ArgumentParser(description="Upsert job_search_tracker.csv after /apply")
    parser.add_argument("--company", required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--cv-file", required=True, help="CV .tex or .html path")
    parser.add_argument(
        "--cover-letter-file",
        default="",
        help="Cover letter .tex or .html path (optional for CV-only applies)",
    )
    parser.add_argument(
        "--source",
        default="",
        help="Posting URL. SEEK links are canonicalized; if omitted, seen_jobs.json is checked.",
    )
    parser.add_argument("--fit-rating", default="")
    parser.add_argument("--notes", default="")
    parser.add_argument("--sector", default="")
    parser.add_argument("--role-type", default="")
    parser.add_argument("--channel", default="")
    parser.add_argument("--contact-person", default="")
    parser.add_argument("--status", default="")
    parser.add_argument("--json", action="store_true", help="Print result as JSON")
    args = parser.parse_args()

    try:
        action, row = upsert_application(
            company=args.company,
            role=args.role,
            cv_file=args.cv_file,
            cover_letter_file=args.cover_letter_file,
            source=args.source,
            fit_rating=args.fit_rating,
            notes=args.notes or "Auto-tracked by /apply",
            sector=args.sector,
            role_type=args.role_type,
            channel=args.channel,
            contact_person=args.contact_person,
            status=args.status,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps({"action": action, "job": row}, indent=2))
    else:
        print(f"{action}: {row['company']} — {row['role']} ({row['status']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
