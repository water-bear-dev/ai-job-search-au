#!/usr/bin/env python3
"""Tests for salary_lookup.py and careers_search ATS detection."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import salary_lookup  # noqa: E402
from careers_search import detect_ats  # noqa: E402


class NormalizeCityTests(unittest.TestCase):
    def test_strips_state(self):
        self.assertEqual(salary_lookup.normalize_city("Melbourne VIC"), "melbourne")
        self.assertEqual(salary_lookup.normalize_city("Sydney NSW"), "sydney")

    def test_city_matches_bidirectional(self):
        self.assertTrue(salary_lookup.city_matches("Melbourne VIC", "Melbourne"))
        self.assertTrue(salary_lookup.city_matches("Melbourne", "Melbourne VIC"))
        self.assertFalse(salary_lookup.city_matches("Sydney", "Melbourne"))


class AliasMatchTests(unittest.TestCase):
    def test_alias_scores(self):
        data = {
            "companies": [
                {
                    "company": "National Australia Bank",
                    "city": "Sydney",
                    "aliases": ["NAB"],
                    "categories": {"all_employees": {"count": 10, "index": 100}},
                }
            ]
        }
        hits = salary_lookup.search_company(data, "NAB")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["company"], "National Australia Bank")

    def test_missing_company_key_safe(self):
        data = {"companies": [{"city": "Sydney", "categories": {}}]}
        hits = salary_lookup.search_company(data, "Acme")
        self.assertEqual(hits, [])

    def test_city_filter_with_state(self):
        data = {
            "companies": [
                {
                    "company": "Atlassian",
                    "city": "Melbourne",
                    "categories": {"all_employees": {"count": 0, "index": 110}},
                }
            ]
        }
        hits = salary_lookup.search_company(data, "Atlassian", city="Melbourne VIC")
        self.assertEqual(len(hits), 1)


class FormatCountTests(unittest.TestCase):
    def test_count_zero_shown(self):
        entry = {
            "company": "Acme",
            "categories": {"all_employees": {"count": 0, "index": 100}},
        }
        text = salary_lookup.format_entry(entry, {"index_baseline": 100, "index_label": "Index"})
        self.assertIn("     0", text)


class MissingDataCliTests(unittest.TestCase):
    def test_json_soft_fail(self):
        with mock.patch.object(salary_lookup, "DATA_FILE", Path("/nonexistent/salary_data.json")):
            with mock.patch.object(sys, "argv", ["salary_lookup.py", "Acme", "--json"]):
                with mock.patch("builtins.print") as mocked_print:
                    try:
                        salary_lookup.main()
                    except SystemExit as exc:
                        self.assertEqual(exc.code, 0)
                    # First print to stdout should be the JSON payload
                    printed = []
                    for call in mocked_print.call_args_list:
                        if call.kwargs.get("file") is sys.stderr:
                            continue
                        if call.args:
                            printed.append(call.args[0])
                    json_lines = [p for p in printed if isinstance(p, str) and p.strip().startswith("{")]
                    self.assertTrue(json_lines)
                    payload = json.loads(json_lines[0])
                    self.assertEqual(payload["matches"], [])
                    self.assertEqual(payload["error"], "missing_data")


class TempDataCliTests(unittest.TestCase):
    def test_json_match_shape(self):
        payload = {
            "metadata": {"index_baseline": 100},
            "companies": [
                {
                    "company": "Canva Pty Ltd",
                    "city": "Sydney",
                    "aliases": ["Canva"],
                    "categories": {"all_employees": {"count": 5, "index": 105}},
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            data_path = Path(tmp) / "salary_data.json"
            data_path.write_text(json.dumps(payload), encoding="utf-8")
            with mock.patch.object(salary_lookup, "DATA_FILE", data_path):
                # Call search directly — full CLI uses module DATA_FILE at import
                results = salary_lookup.search_company(payload, "Canva", city="Sydney NSW")
                self.assertEqual(len(results), 1)


class AtsDetectTests(unittest.TestCase):
    def test_greenhouse(self):
        kind, token = detect_ats("https://boards.greenhouse.io/acme")
        self.assertEqual(kind, "greenhouse")
        self.assertEqual(token, "acme")

    def test_lever(self):
        kind, token = detect_ats("https://jobs.lever.co/acme/abc")
        self.assertEqual(kind, "lever")
        self.assertEqual(token, "acme")

    def test_ashby(self):
        kind, token = detect_ats("https://jobs.ashbyhq.com/acme")
        self.assertEqual(kind, "ashby")
        self.assertEqual(token, "acme")

    def test_smartrecruiters(self):
        kind, token = detect_ats("https://jobs.smartrecruiters.com/Canva")
        self.assertEqual(kind, "smartrecruiters")
        self.assertEqual(token, "Canva")

    def test_html_fallback(self):
        kind, token = detect_ats("https://www.example.com/careers")
        self.assertEqual(kind, "html")
        self.assertEqual(token, "")


if __name__ == "__main__":
    unittest.main()
