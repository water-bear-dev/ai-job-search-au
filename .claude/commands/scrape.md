---
description: Search SEEK (and optionally LinkedIn) for jobs matching your profile and rank by fit. Triggers on /scrape.
---

# /scrape

Invoke the **`job-scraper`** skill to search the Australian job market and rank results
against the candidate profile.

Use the **Skill tool** to run the skill named `job-scraper`, forwarding the arguments below
verbatim:

```
$ARGUMENTS
```

Argument handling:

- **No argument** → search SEEK only (the default; LinkedIn stays off).
- **`linkedin`** → ALSO query LinkedIn's guest endpoints. This is opt-in only because
  automating LinkedIn is against its Terms of Service; the skill will remind the user it's
  at-their-own-risk before running it.

Do not duplicate the scraper logic here — the full workflow lives in
`.claude/skills/job-scraper/SKILL.md`.
