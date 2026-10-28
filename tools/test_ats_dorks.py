#!/usr/bin/env python3
"""Tests for tools/ats_dorks.py (no network)."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import ats_dorks  # noqa: E402
from careers_search import filter_by_keywords  # noqa: E402

SAMPLE = """# Search Queries

## Role nouns

```
Data Engineer
AI Engineer
[PLACEHOLDER_NOUN]
```

## Tiers

### wide

**Prefixes:**

```
# none
```

**Sites:**

```
greenhouse.io
lever.co
```

### enterprise

**Prefixes:**

```
Senior
Staff
Principal
```

**Sites:**

```
myworkdayjobs.com
smartrecruiters.com
```

### startup

**Prefixes:**

```
Founding
Lead
```

**Sites:**

```
greenhouse.io
ashbyhq.com
```

## SEEK locations

```
All Melbourne VIC
All Australia
All [YOUR_CITY] [STATE]
```

## ATS location tokens

```
Melbourne
Australia
remote
hybrid
```

## Domain boost

```
fintech
banking
```
"""

LEGACY = """# Old format

### Priority 1: Data
```
Senior Data Engineer
AI Engineer
```

### Priority 2: Cloud
```
Databricks Engineer
site:wellfound.com founding engineer
```

Locations: `All Brisbane QLD` and `All Australia`.
"""


class ParseRecipeTests(unittest.TestCase):
    def _recipe(self, text: str) -> ats_dorks.Recipe:
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as fh:
            fh.write(text)
            path = fh.name
        try:
            return ats_dorks.parse_recipe(path)
        finally:
            Path(path).unlink(missing_ok=True)

    def test_parses_nouns_skips_placeholders(self):
        recipe = self._recipe(SAMPLE)
        self.assertEqual(recipe.nouns, ["Data Engineer", "AI Engineer"])
        self.assertEqual(recipe.seek_locations, ["All Melbourne VIC", "All Australia"])
        self.assertEqual(
            recipe.ats_location_tokens, ["Melbourne", "Australia", "remote", "hybrid"]
        )
        self.assertEqual(recipe.domain_boost, ["fintech", "banking"])

    def test_parses_tiers(self):
        recipe = self._recipe(SAMPLE)
        names = [t.name for t in recipe.tiers]
        self.assertEqual(names, ["wide", "enterprise", "startup"])
        wide = recipe.tiers[0]
        self.assertEqual(wide.prefixes, [])
        self.assertEqual(wide.sites, ["greenhouse.io", "lever.co"])
        self.assertEqual(recipe.tiers[1].prefixes, ["Senior", "Staff", "Principal"])
        self.assertEqual(recipe.tiers[2].sites, ["greenhouse.io", "ashbyhq.com"])

    def test_live_recipe_file(self):
        path = REPO_ROOT / "skills" / "job-scraper" / "search-queries.md"
        if not path.is_file():
            self.skipTest("live search-queries.md not seeded")
        recipe = ats_dorks.parse_recipe(path)
        self.assertGreaterEqual(len(recipe.nouns), 3)
        self.assertEqual([t.name for t in recipe.tiers], ["wide", "enterprise", "startup"])
        dorks = ats_dorks.build_dorks(recipe)
        self.assertEqual([d["tier"] for d in dorks], ["wide", "enterprise", "startup"])

    def test_legacy_priority_fallback(self):
        recipe = self._recipe(LEGACY)
        self.assertEqual(
            recipe.nouns, ["Senior Data Engineer", "AI Engineer", "Databricks Engineer"]
        )
        self.assertIn("All Brisbane QLD", recipe.seek_locations)


class BuildDorkTests(unittest.TestCase):
    def test_wide_dork_or_group_location(self):
        query = ats_dorks.build_dork(
            ["greenhouse.io", "lever.co"],
            ["Data Engineer", "AI Engineer"],
            prefixes=[],
            location_tokens=["Melbourne", "Australia", "remote", "hybrid"],
        )
        self.assertIn("site:greenhouse.io", query)
        self.assertIn("site:lever.co", query)
        self.assertIn('"Data Engineer"', query)
        self.assertIn('"AI Engineer"', query)
        self.assertIn("(Melbourne OR Australia OR remote OR hybrid)", query)
        self.assertNotIn('"Senior"', query)

    def test_enterprise_adds_prefixes(self):
        query = ats_dorks.build_dork(
            ["myworkdayjobs.com"],
            ["Data Engineer"],
            prefixes=["Senior", "Staff"],
            location_tokens=["Melbourne"],
        )
        self.assertIn('("Senior" OR "Staff")', query)
        self.assertIn("site:myworkdayjobs.com", query)

    def test_remote_only_drops_cities(self):
        kept = ats_dorks.location_tokens_for_run(
            ["Melbourne", "Australia", "remote", "hybrid"], remote_only=True
        )
        self.assertEqual(kept, ["remote", "hybrid"])

    def test_extra_noun_and_payload(self):
        recipe = ats_dorks.Recipe(
            nouns=["Data Engineer"],
            tiers=[
                ats_dorks.Tier("wide", prefixes=[], sites=["greenhouse.io"]),
            ],
            ats_location_tokens=["Melbourne", "remote"],
        )
        payload = ats_dorks.recipe_payload(
            recipe, extra_nouns=["MLOps"], remote_only=False
        )
        self.assertEqual(payload["nouns"], ["Data Engineer", "MLOps"])
        self.assertEqual(len(payload["dorks"]), 1)
        self.assertIn('"MLOps"', payload["dorks"][0]["query"])

    def test_empty_location_omits_group(self):
        query = ats_dorks.build_dork(
            ["greenhouse.io"], ["AI Engineer"], prefixes=[], location_tokens=[]
        )
        self.assertEqual(
            query, 'site:greenhouse.io "AI Engineer"'
        )


class ScoreJobTests(unittest.TestCase):
    def test_prefix_and_domain_boost_never_exclude(self):
        from daily_digest import score_job

        base = {
            "title": "Data Engineer",
            "teaser": "Python pipelines",
            "bullet_points": [],
            "location": "Melbourne",
            "work_arrangement": "Hybrid",
            "company": "Acme",
            "source": "seek",
        }
        senior = dict(base, title="Senior Data Engineer")
        bank = dict(base, teaser="Python pipelines in banking")
        no_boost, _ = score_job(base, ["Data Engineer"], [], [], 0)
        with_prefix, _ = score_job(
            senior, ["Data Engineer"], [], [], 0, prefixes=["Senior", "Staff"]
        )
        with_domain, _ = score_job(
            bank, ["Data Engineer"], [], [], 0, domain_boost=["banking"]
        )
        self.assertGreater(with_prefix, no_boost)
        self.assertGreater(with_domain, no_boost)
        # Missing prefix still scores; it is not excluded
        self.assertGreater(no_boost, 0)
        emailish = dict(base, teaser="Send an email")
        ai_noise, _ = score_job(emailish, ["Data Engineer"], [], [], 0, domain_boost=["AI"])
        self.assertEqual(ai_noise, no_boost)


class FilterByKeywordsTests(unittest.TestCase):
    def test_phrase_keeps_senior_data_engineer(self):
        jobs = [
            {"title": "Senior Data Engineer"},
            {"title": "Software Engineer"},
            {"title": "Data Analyst"},
        ]
        kept = filter_by_keywords(jobs, ["Data Engineer"])
        self.assertEqual([j["title"] for j in kept], ["Senior Data Engineer"])

    def test_all_tokens_of_one_noun(self):
        jobs = [
            {"title": "Cloud Data Engineer (AWS)"},
            {"title": "Platform Engineer"},
        ]
        kept = filter_by_keywords(jobs, ["Data Engineer"])
        self.assertEqual([j["title"] for j in kept], ["Cloud Data Engineer (AWS)"])

    def test_empty_keywords_keeps_all(self):
        jobs = [{"title": "Anything"}]
        self.assertEqual(filter_by_keywords(jobs, []), jobs)


if __name__ == "__main__":
    unittest.main()
