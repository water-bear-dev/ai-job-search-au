#!/usr/bin/env python3
"""Tests for tools/parse_posting.py (no network)."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import parse_posting  # noqa: E402


class TestParsePaste(unittest.TestCase):
    def test_structured_paste_with_separator(self):
        text = """Company: Acme Corp
Role: Data Engineer
Location: Melbourne

---
Build pipelines and own data quality."""
        result = parse_posting.parse_paste(text)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["company"], "Acme Corp")
        self.assertEqual(result["role"], "Data Engineer")
        self.assertEqual(result["location"], "Melbourne")
        self.assertIn("pipelines", result["description"])

    def test_structured_paste_headers_without_separator(self):
        text = """Company: Northern Health
Role: AI Engineer
Location: Melbourne VIC

Design agentic AI systems."""
        result = parse_posting.parse_paste(text)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["company"], "Northern Health")
        self.assertEqual(result["role"], "AI Engineer")

    def test_description_only_incomplete(self):
        text = "Senior engineer needed.\n\nMust know Python."
        result = parse_posting.parse_paste(text)
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["role"], "Senior engineer needed.")
        self.assertIn("company", " ".join(result["warnings"]))

    def test_source_url_override(self):
        text = """Company: Acme
Role: Engineer

---
Job details here."""
        result = parse_posting.parse_paste(
            text, source_url="https://jobs.lever.co/acme/123"
        )
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["source_url"], "https://jobs.lever.co/acme/123")

    def test_title_alias(self):
        text = """Company: Acme
Title: Platform Engineer

---
Description body."""
        result = parse_posting.parse_paste(text)
        self.assertEqual(result["role"], "Platform Engineer")


class TestParseInput(unittest.TestCase):
    def test_generic_url_webfetch_required(self):
        result = parse_posting.parse_input("https://jobs.lever.co/acme/123")
        self.assertEqual(result["status"], "webfetch_required")
        self.assertEqual(result["channel"], "web")
        self.assertEqual(result["source_url"], "https://jobs.lever.co/acme/123")

    def test_indeed_url_webfetch_required(self):
        result = parse_posting.parse_input(
            "https://au.indeed.com/viewjob?jk=abc123"
        )
        self.assertEqual(result["status"], "webfetch_required")

    def test_plain_text_routes_to_paste(self):
        result = parse_posting.parse_input("Company: X\nRole: Y\n\n---\nDesc")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["channel"], "paste")

    @patch.object(parse_posting, "_run_cli")
    def test_seek_url_mocked(self, mock_run):
        mock_run.return_value = {
            "id": "92686067",
            "title": "AI Engineer",
            "company": "Northern Health",
            "location": "Melbourne VIC",
            "salary": "$120k",
            "work_type": "Full time",
            "description": "Full job description here.",
            "url": "https://www.seek.com.au/job/92686067",
        }
        result = parse_posting.parse_input("https://www.seek.com.au/job/92686067")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["channel"], "SEEK")
        self.assertEqual(result["role"], "AI Engineer")
        self.assertEqual(result["company"], "Northern Health")
        mock_run.assert_called_once()

    @patch.object(parse_posting, "_run_cli")
    def test_bare_seek_id_mocked(self, mock_run):
        mock_run.return_value = {
            "title": "Engineer",
            "company": "Co",
            "description": "Desc",
            "url": "https://www.seek.com.au/job/12345678",
        }
        result = parse_posting.parse_input("12345678")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["channel"], "SEEK")

    @patch.object(parse_posting, "_run_cli")
    def test_seek_error(self, mock_run):
        mock_run.side_effect = RuntimeError("CERTIFICATE_VERIFY_FAILED")
        result = parse_posting.parse_input("https://www.seek.com.au/job/92686067")
        self.assertEqual(result["status"], "error")
        self.assertIn("CERTIFICATE", result["error"])


class TestHelpers(unittest.TestCase):
    def test_is_seek_input(self):
        self.assertTrue(parse_posting._is_seek_input("92686067"))
        self.assertTrue(parse_posting._is_seek_input("https://www.seek.com.au/job/92686067"))
        self.assertFalse(parse_posting._is_seek_input("https://jobs.lever.co/x"))


if __name__ == "__main__":
    unittest.main()
