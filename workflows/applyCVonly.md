# /applyCVonly - CV-Only Job Application Workflow

You are orchestrating a two-agent job application workflow that produces a **tailored CV only** (no cover letter). The job posting is provided below as `$ARGUMENTS` (either a URL or pasted text).

Follow these steps **exactly in order**. Do not skip steps.

**Token-efficiency rules for this workflow:**
- Never re-Read a file whose contents are already in your context from an earlier step. If you read it in Step 1, it is still available in Step 2.
- When dispatching the reviewer agent, pass the CV draft **inline in the agent prompt** rather than asking the agent to Read files you already have in memory.
- Run the full verification checklist exactly once, at the end (Step 6). The reviewer focuses on content critique, not verification.
- Step 5 (compile and inspect PDF) is mandatory and non-skippable — LaTeX page-break decisions are unpredictable, and `.tex` files that look fine often produce broken PDFs (orphaned entry titles, awkward page breaks).

---

## Step 0: Parse Input

Follow **Step 0** in `workflows/apply.md` exactly:

1. Run `python tools/parse_posting.py` on `$ARGUMENTS` (use `--file` for multi-line paste).
2. Branch on `status` (`ok`, `webfetch_required`, `incomplete`, `error`) until you have a final `ok` result.
3. Store `company`, `role`, `location`, `description`, `source_url`, and `channel` from the JSON.

---

## Step 1: DRAFTER - Evaluate Fit

Read the evaluation framework:
- `skills/job-application-assistant/04-job-evaluation.md`
- `skills/job-application-assistant/01-candidate-profile.md`

Using the framework from `04-job-evaluation.md`, evaluate the job posting against the candidate's profile. If the salary lookup tool is configured, run:

```bash
python salary_lookup.py "<Company Name>" --json
```

If the posting specifies a city, add `--city "<City>"` to narrow results. Parse the JSON output and include the salary benchmark in the evaluation. If the tool is not configured or returns an error, skip the salary benchmark.

Present the evaluation to the user with:

1. **Skills match** - which required/preferred skills match vs. gaps
2. **Experience match** - how work history maps to the role
3. **Behavioral/culture match** - how behavioral profile fits the role/company culture
4. **Salary benchmark** - salary index for the company (if available)
5. **Overall fit score** and recommendation (strong fit / moderate fit / weak fit)

After presenting the evaluation, ask the user:
> "Should I proceed with drafting the CV for this role?"

**If the user says no, stop here.** If yes, continue to Step 2.

---

## Step 2: DRAFTER - Draft CV

You already have `01-candidate-profile.md` and `04-job-evaluation.md` in context from Step 1. **Do not re-read them.**

Read only the reference files you do not yet have:
- `skills/job-application-assistant/03-writing-style.md`
- `skills/job-application-assistant/05-cv-templates.md`

Also read the most recent existing CV for concrete structural reference (one is enough):
- Read any existing `applied_jobs/*/<FullName>_CV.tex` (or legacy `cv/*/<FullName>_CV.tex`, or `cv/main_example.tex` if none exist)

### File layout and naming

**Before writing any files**, compute paths and create folders:

```bash
python tools/application_paths.py \
  --company "<Company Name>" \
  --role "<Role Title>" \
  --full-name "<Candidate Full Name>" \
  --date "<YYYY-MM-DD from today or posting>" \
  --mkdir \
  --json
```

Use the JSON output for all paths below. Folder format:

```
<YYYYMMDD>-<companyName>-<position>
```

| Part | Rule | Example |
|------|------|---------|
| `<YYYYMMDD>` | Application date (`YYYY` + `MM` + `DD`) | `20260622` |
| `<companyName>` | Company in PascalCase (alphanumeric words joined) | `NorthernHealth` |
| `<position>` | Role title in PascalCase (alphanumeric words joined) | `AIEngineerAgenticAIAndAdvancedAnalytics` |
| `<FullName>` | Candidate name; spaces → underscores | `Andrew_Pham` |

Full path:

- **CV:** `applied_jobs/<application_folder>/<FullName>_CV.tex`

Example: `applied_jobs/20260622-NorthernHealth-AIEngineerAgenticAIAndAdvancedAnalytics/Andrew_Pham_CV.tex`

### CV (`applied_jobs/<application_folder>/<FullName>_CV.tex`)
- Always in **English**
- Follow the moderncv/banking format from `05-cv-templates.md`
- Tailor the profile statement and experience bullets to the specific role
- Reframe skills and achievements to match job requirements
- Keep to 2 pages

Write the file to disk. Keep the exact text of the draft in working memory — you will pass it inline to the reviewer in Step 3 and revise it in Step 4 without re-reading.

---

## Step 3: REVIEWER - Research & Critique (CV only)

Spawn a **reviewer subagent** with fresh context (see the platform adapter for the exact invocation). Pass the CV draft **inline in the prompt** below (do not make the reviewer Read it). Scope the reviewer's file reads to content-critique essentials only — the reviewer does not need `05-cv-templates.md` to critique content, since that governs structural/LaTeX concerns the drafter already applied.

Replace `<APPLICATION_FOLDER>`, `<FULLNAME>`, `<ROLE>`, `<INSERT_JOB_POSTING_TEXT_HERE>`, and `<INSERT_CV_DRAFT_HERE>` with actual values before dispatching (`<FULLNAME>` = candidate name with underscores, e.g. `Andrew_Pham`).

```
You are a hiring manager proxy reviewing a tailored CV for a job application. Your job is to make the CV as targeted and compelling as possible. There is NO cover letter — critique the CV only.

## Your Tasks

### 1. Research the Company
Use WebSearch and WebFetch to research:
- The company's website, mission, and recent news
- The specific department or team (if mentioned in the posting)
- Any recent projects, press releases, or strategic initiatives relevant to the role
- Company culture and values

### 2. Read Reference Materials (content-critique only)
Read these four files — and only these — to ground your critique:
- `skills/job-application-assistant/01-candidate-profile.md`
- `skills/job-application-assistant/02-behavioral-profile.md`
- `skills/job-application-assistant/03-writing-style.md`
- `skills/job-application-assistant/04-job-evaluation.md`

Do NOT read `05-cv-templates.md` — that governs LaTeX structure the drafter already applied.

### 3. Draft to Review
The CV draft is provided inline below. Do NOT use the Read tool on the draft file — use this exact text.

<CV_DRAFT file="applied_jobs/<APPLICATION_FOLDER>/<FULLNAME>_CV.tex">
<INSERT_CV_DRAFT_HERE>
</CV_DRAFT>

### 4. Job Posting
<JOB_POSTING>
<INSERT_JOB_POSTING_TEXT_HERE>
</JOB_POSTING>

### 5. Produce Feedback

Return your feedback in **two parts**:

**Part A — Structured edits (preferred format whenever possible):**
A JSON array of concrete edits the drafter can apply directly without re-reading the file. Each edit is an object:
```json
{
  "file": "applied_jobs/<APPLICATION_FOLDER>/<FULLNAME>_CV.tex",
  "old_string": "<exact text currently in the draft>",
  "new_string": "<replacement text>",
  "reason": "<one-line rationale: keyword match / company angle / reframing / style>"
}
```
Only use this format when you can quote the exact `old_string` from the draft above. Make `old_string` unique — include enough surrounding context so it matches exactly once.

**Part B — Narrative suggestions (for judgment calls that are not mechanical edits):**
Prose suggestions grouped by category. Produce each category even if your finding is "no issues".
- **Missed keywords/requirements** — what to add and roughly where
- **Company/department-specific angles** — connections between experience and the company's strategic priorities, based on your research
- **Action-oriented reframing** — identify passive, generic, or low-energy statements and suggest action-oriented rewrites
- **Tone and style issues** — check against `03-writing-style.md` and `02-behavioral-profile.md`

**CRITICAL RULE:** All suggestions must be grounded in actual profile data. Do NOT suggest fabricating skills, experience, or achievements. If a requirement is a gap, say so honestly and suggest how to frame adjacent experience instead.

Do **not** run a verification checklist — the drafter will do that in the final step. Focus on content critique.

Return Part A and Part B together as a single structured message.
```

---

## Step 4: DRAFTER - Revise Based on Feedback

Once the reviewer agent returns its feedback:

1. **Apply Part A (structured edits) directly** — edit the CV file in place (search/replace). Do NOT re-read the draft file — you already have it in context from Step 2. Skip any edit whose rationale would require fabricating content.
2. **Apply Part B (narrative suggestions)** using judgment. Walk through every Part B category the reviewer returned:
   - **Missed keywords/requirements:** add keywords where they fit naturally in experience bullets or the profile statement.
   - **Company/department-specific angles:** weave verified company research into the profile statement or relevant bullets. Verify every company claim via WebFetch/WebSearch before including it.
   - **Action-oriented reframing:** rewrite passive or generic phrasing in the profile statement and bullet leads.
   - **Tone and style issues:** apply the writing-style-guide fixes (no em-dashes, no cliches, no apologetic hedging, consistent active voice).
3. Do NOT incorporate any suggestion that would fabricate skills or experience.

After all edits are applied, the CV file on disk is the final draft.

---

## Step 5: DRAFTER - Compile & Inspect PDF (MANDATORY)

**Never skip this step.** Compile the CV and visually verify the PDF before presenting.

### 5a. Compile

```bash
python tools/latex_build.py \
  --cv "applied_jobs/<application_folder>/<FullName>_CV.tex"
```

- CV uses **lualatex**.
- Artifacts: `applied_jobs/<application_folder>/build/*`
- If compile fails, fix the error and re-compile until clean.

### 5b. Inspect layout

Read the CV PDF via the Read tool and verify:

**CV (`applied_jobs/<application_folder>/<FullName>_CV.pdf`):**
- [ ] Exactly 2 pages (not 1, not 3)
- [ ] No orphaned `\cventry` titles — a job/education title line must never sit alone at the bottom of page 1 with its bullets on page 2
- [ ] Section headings are not isolated at the top of page 2 with only 1-2 lines below
- [ ] No awkward whitespace gaps

### 5c. Iterate until clean

If the layout has problems, edit the `.tex` file and recompile. Common fixes (see `05-cv-templates.md`):

- **Orphaned CV entry title:** `\usepackage{needspace}` in preamble, then `\needspace{5\baselineskip}` immediately before the problematic `\cventry`
- **CV spills to page 3 with only a trailing section:** `\enlargethispage{2-3\baselineskip}` before a late section
- **Substantial content on page 3:** cut content using **relevance-weighted cutting** (see `05-cv-templates.md` → "Relevance-weighted cutting")

Do not proceed to Step 6 until the PDF passes inspection.

### 5d. Clean up build artifacts

After the final clean compile:

```bash
python tools/cleanup_latex.py
```

---

## Step 6: Update Tracker & Present Final Output

### 6a. Update job tracker (automatic)

After the CV PDF passes inspection (Step 5), upsert a row in `job_search_tracker.csv`. Omit `--cover-letter-file` (CV-only apply):

```bash
python tracker/upsert_application.py \
  --company "<Company Name>" \
  --role "<Role Title>" \
  --cv-file "applied_jobs/<application_folder>/<FullName>_CV.tex" \
  --source "<source_url from Step 0>" \
  --fit-rating "<strong fit | moderate fit | weak fit from Step 1>" \
  --sector "<sector if known, else omit>" \
  --json
```

- **Match key:** `company` + `role` (case-insensitive). Re-running for the same role updates file paths and `source`; existing `status` and any existing `cover_letter_file` are preserved.
- **Source URL:** must be the canonical posting link from Step 0. Never use README/example placeholder IDs.
- **Defaults:** `status` = `draft` from `tracker/statuses.json`; `channel` inferred from URL (`SEEK`, `LinkedIn`, or `web`).
- If the command fails, report the error but still present the CV to the user.

Tell the user they can view the row at **http://127.0.0.1:8765** if the tracker server is running (`cd tracker && python server.py`).

### 6b. Verification & presentation

Run the verification checklist from `AGENTS.md` now — this is the **only** verification pass. Re-read the CV file once to verify final state on disk.

### Verification Checklist (CV-only)
Report pass/fail for each applicable item:
- Factual accuracy (profile, titles, dates, contact, verified company claims)
- Targeting (profile statement and bullets tailored to the role)
- CV format (2-page moderncv/banking)
- Quality (LaTeX, spelling, grammar)
- Compiled PDF (exactly 2 pages, no orphaned `\cventry` titles)

Skip cover-letter-specific checklist items.

### Key Tailoring Decisions
Summarize 3-5 key decisions made to tailor the CV.

### Files Created
List the file written:
- `applied_jobs/<application_folder>/<FullName>_CV.tex`

Confirm tracker row was created/updated (Step 6a).

Tell the user: "The CV is ready for your review. The application is in your job tracker (http://127.0.0.1:8765 if the server is running). Run `/apply` later if you want a cover letter for the same role."
