# /scrape

Read and follow `skills/job-scraper/SKILL.md`, forwarding user arguments verbatim:

```
$ARGUMENTS
```

Argument handling:

- **No argument** → ATS Google dorks only (wide / enterprise / startup). LinkedIn stays off.
- **`seek` or `broad`** → ATS dorks plus the SEEK CLI backup.
- **`remote`** → drop city tokens from the dorks; keep remote/hybrid only.
- **`linkedin`** → ALSO query LinkedIn's guest endpoints. This is opt-in only because
  automating LinkedIn is against its Terms of Service; the skill will remind the user it's
  at-their-own-risk before running it.

Do not duplicate the scraper logic here — the full workflow lives in
`skills/job-scraper/SKILL.md`.
