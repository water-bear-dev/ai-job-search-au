#!/usr/bin/env python3
"""Tests for tools/brave_search.py (no network)."""

from __future__ import annotations

import json
import os
import sys
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import brave_search  # noqa: E402


class HitsToJobsTests(unittest.TestCase):
    def test_skips_seek_urls(self):
        hits = [
            {
                "title": "Data Engineer at Acme",
                "url": "https://jobs.lever.co/acme/abc",
                "description": "Melbourne hybrid",
            },
            {
                "title": "Data Engineer SEEK",
                "url": "https://www.seek.com.au/job/123",
                "description": "Melbourne",
            },
        ]
        jobs = brave_search.hits_to_jobs(hits)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["source"], "ats-dork")
        self.assertEqual(jobs[0]["url"], "https://jobs.lever.co/acme/abc")
        self.assertEqual(jobs[0]["company"], "Acme")
        self.assertIn("Melbourne", jobs[0]["location"])

    def test_dedupes_urls(self):
        hits = [
            {"title": "A", "url": "https://jobs.ashbyhq.com/x/1", "description": ""},
            {"title": "A again", "url": "https://jobs.ashbyhq.com/x/1/", "description": ""},
        ]
        self.assertEqual(len(brave_search.hits_to_jobs(hits)), 1)

    def test_skips_empty_title_or_url(self):
        hits = [
            {"title": "", "url": "https://jobs.lever.co/x/1", "description": ""},
            {"title": "Role", "url": "", "description": ""},
        ]
        self.assertEqual(brave_search.hits_to_jobs(hits), [])


class SearchTests(unittest.TestCase):
    def test_missing_key_returns_empty(self):
        hits, err = brave_search.search("site:greenhouse.io Data Engineer", "")
        self.assertEqual(hits, [])
        self.assertIsNone(err)

    def test_parses_web_results(self):
        payload = {
            "web": {
                "results": [
                    {
                        "title": "AI Engineer @ Xero",
                        "url": "https://jobs.ashbyhq.com/xero/abc",
                        "description": "Hybrid Melbourne",
                    }
                ]
            }
        }
        buf = BytesIO(json.dumps(payload).encode("utf-8"))

        class _Resp:
            def read(self):
                return buf.getvalue()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        with patch("brave_search.urlopen", return_value=_Resp()):
            hits, err = brave_search.search("dork", "test-key")
        self.assertIsNone(err)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["title"], "AI Engineer @ Xero")

    def test_http_error_soft_fail(self):
        err_obj = HTTPError(
            "https://api.search.brave.com/res/v1/web/search",
            401,
            "Unauthorized",
            hdrs=None,
            fp=None,
        )
        with patch("brave_search.urlopen", side_effect=err_obj):
            hits, err = brave_search.search("dork", "bad-key")
        self.assertEqual(hits, [])
        self.assertIn("401", err or "")

    def test_search_dorks_records_notes_on_error(self):
        err_obj = HTTPError(
            "https://api.search.brave.com/res/v1/web/search",
            429,
            "Too Many Requests",
            hdrs=None,
            fp=None,
        )
        with patch("brave_search.urlopen", side_effect=err_obj):
            jobs, notes = brave_search.search_dorks(
                [{"tier": "wide", "query": "site:greenhouse.io Data Engineer"}],
                "key",
                pause_s=0,
            )
        self.assertEqual(jobs, [])
        self.assertTrue(any("wide" in n and "429" in n for n in notes))


class CollectJobsAtsTests(unittest.TestCase):
    def test_no_key_skips_dorks(self):
        import daily_digest

        with patch.object(daily_digest, "load_env", return_value={}):
            with patch.dict(os.environ, {"BRAVE_SEARCH_API_KEY": ""}, clear=False):
                _jobs, notes = daily_digest.collect_jobs(
                    {}, skip_seek=True, skip_careers=True, skip_ats=False
                )
        self.assertTrue(any("no BRAVE_SEARCH_API_KEY" in n for n in notes))

    def test_skip_ats_flag(self):
        import daily_digest

        _jobs, notes = daily_digest.collect_jobs(
            {}, skip_seek=True, skip_careers=True, skip_ats=True
        )
        self.assertTrue(any("--skip-ats" in n for n in notes))

    def test_stubbed_dorks_merge_and_score(self):
        import daily_digest

        stub_jobs = [
            {
                "id": "ats-test1",
                "title": "Senior Data Engineer",
                "company": "Acme",
                "location": "Melbourne",
                "salary": "",
                "work_type": "",
                "work_arrangement": "Hybrid",
                "listing_date": "",
                "teaser": "Python AWS Databricks pipelines in Melbourne hybrid",
                "bullet_points": [],
                "url": "https://jobs.lever.co/acme/xyz",
                "source": "ats-dork",
            }
        ]
        with patch.object(daily_digest, "_brave_api_key", return_value="fake-key"):
            with patch.object(
                daily_digest, "search_dorks", return_value=(stub_jobs, [])
            ):
                jobs, notes = daily_digest.collect_jobs(
                    {"min_score": 1, "max_results": 25, "include_remote": True},
                    skip_seek=True,
                    skip_careers=True,
                    skip_ats=False,
                )
        self.assertTrue(any(j.get("url") == stub_jobs[0]["url"] for j in jobs))
        self.assertTrue(any("ATS dorks:" in n for n in notes))

    def test_email_badge_ats_dork(self):
        import daily_digest

        plain, html_body = daily_digest.build_email_bodies(
            [
                {
                    "title": "Data Engineer",
                    "company": "Acme",
                    "location": "Melbourne",
                    "url": "https://jobs.lever.co/acme/1",
                    "source": "ats-dork",
                    "teaser": "",
                    "is_preferred": False,
                }
            ],
            [],
        )
        self.assertIn("ATS dork", plain)
        self.assertIn("ATS dork", html_body)


if __name__ == "__main__":
    unittest.main()

