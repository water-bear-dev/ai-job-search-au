# /evaluate - Job Fit Evaluation Only

Evaluate fit for a job posting **without** drafting CV/cover letter, running the reviewer, or compiling PDFs.

The job posting is provided as `$ARGUMENTS` (URL or pasted text).

---

## Step 0: Parse Input

Follow **Step 0** in `workflows/apply.md` exactly:

1. Run `python tools/parse_posting.py` on `$ARGUMENTS` (use `--file` for multi-line paste).
2. Branch on `status` (`ok`, `webfetch_required`, `incomplete`, `error`) until you have a final `ok` result.
3. Store `company`, `role`, `location`, `description`, `source_url`, and `channel` from the JSON.

---

## Step 1: Evaluate Fit

Read the evaluation framework:

- `skills/job-application-assistant/04-job-evaluation.md`
- `skills/job-application-assistant/01-candidate-profile.md`

Using the framework from `04-job-evaluation.md`, evaluate the posting (`description` plus metadata from Step 0) against the candidate's profile. If the salary lookup tool is configured, run:

```bash
python salary_lookup.py "<Company Name>" --json
```

If the posting specifies a city, add `--city "<City>"` to narrow results. Parse the JSON output and include the salary benchmark in the evaluation. If the tool is not configured or returns an error, skip the salary benchmark.

Present the evaluation to the user with:

1. **Skills match** — which required/preferred skills match vs. gaps
2. **Experience match** — how work history maps to the role
3. **Behavioral/culture match** — how behavioral profile fits the role/company culture
4. **Salary benchmark** — salary index for the company (if available)
5. **Overall fit score** and recommendation (strong fit / moderate fit / weak fit)

Include a one-line summary of the parsed posting: company, role, location, channel, and `source_url` (if any).

---

## Stop here

Do **not** draft LaTeX, run the reviewer, compile PDFs, or update the tracker.

End with:

> "To draft a tailored CV and cover letter for this role, run `/apply` with the same URL or pasted posting. For CV only, run `/applyCVonly`."

If the user wants to proceed immediately without re-pasting, offer to run `/apply` or `/applyCVonly` for them using the same input.
