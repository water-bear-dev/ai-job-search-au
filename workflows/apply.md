# /apply - Drafter-Reviewer Job Application Workflow

You are orchestrating a two-agent job application workflow. The job posting is provided below as `$ARGUMENTS` (either a URL or pasted text).

Follow these steps **exactly in order**. Do not skip steps.

**Token-efficiency rules for this workflow:**
- Never re-Read a file whose contents are already in your context from an earlier step. If you read it in Step 1, it is still available in Step 2.
- When dispatching the reviewer agent, pass draft content **inline in the agent prompt** rather than asking the agent to Read files you already have in memory.
- Run the full verification checklist exactly once, at the end (Step 6). The reviewer focuses on content critique, not verification.
- Step 5 (compile and inspect PDFs) is mandatory and non-skippable — LaTeX page-break decisions are unpredictable, and `.tex` files that look fine often produce broken PDFs (orphaned entry titles, cover letters spilling to page 2, bullet fonts mismatching).

---

## Step 0: Parse Input

**MUST** normalize the posting via `tools/parse_posting.py` before fit evaluation. Do not hand-parse URLs or guess company/role from raw text.

### 0a. Run the parser

- **Single-line URL or short text:** pass `$ARGUMENTS` directly:
  ```bash
  python tools/parse_posting.py "$ARGUMENTS"
  ```
  (Use `--table` only for quick debugging; default output is JSON.)

- **Multi-line pasted posting:** write `$ARGUMENTS` to a temp file, then:
  ```bash
  python tools/parse_posting.py --file /tmp/posting.txt
  ```

Parse the JSON stdout. Fields used downstream: `status`, `company`, `role`, `location`, `salary`, `work_type`, `description`, `source_url`, `channel`, `warnings`, `error`.

### 0b. Branch on `status`

| `status` | Action |
|----------|--------|
| **`ok`** | Show the user a short summary (company, role, location, channel, description length). Proceed to Step 1. |
| **`webfetch_required`** | Use `WebFetch` on `source_url` from the JSON. Re-run: `python tools/parse_posting.py --text "<fetched content>" --source-url "<source_url>"`. If still `incomplete`, ask the user for missing fields. |
| **`incomplete`** | Use AskQuestion to collect missing `company` and/or `role` (see `warnings`). Prepend headers to the description and re-run the parser, or re-run with completed `--text`. |
| **`error`** | Report `error` to the user and ask them to paste the full posting using the structured template below. |

**Structured paste template** (when URL fetch fails or user pastes manually):

```
Company: <employer name>
Role: <job title>
Location: <city / remote>   # optional
URL: <posting link>         # optional

---
<paste full job description here>
```

### 0c. Store for later steps

From the final `ok` JSON, store:

- **`company`**, **`role`**, **`location`** — folder naming, tracker, cover letter
- **`description`** — full posting body for fit eval and tailoring
- **`source_url`** — tracker `source` field (leave empty only if user pasted with no URL)
- **`channel`** — informational (`SEEK`, `LinkedIn`, `web`, `paste`)

Do not invent or reuse example SEEK job IDs. Canonical SEEK URLs come from the parser's `source_url` field after `--detail` fetch.

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
> "Should I proceed with drafting the CV and cover letter for this role?"

**If the user says no, stop here.** If yes, continue to Step 2.

---

## Step 2: DRAFTER - Draft CV + Cover Letter

You already have `01-candidate-profile.md` and `04-job-evaluation.md` in context from Step 1. **Do not re-read them.**

Read only the reference files you do not yet have:
- `skills/job-application-assistant/03-writing-style.md`
- `skills/job-application-assistant/05-cv-templates.md`
- `skills/job-application-assistant/06-cover-letter-templates.md`

Also read the most recent existing CV and cover letter files for concrete structural reference (one of each is enough):
- Read any existing `applied_jobs/*/<FullName>_CV.tex` (or legacy `cv/*/<FullName>_CV.tex`, or `cv/main_example.tex` if none exist)
- Read any existing `applied_jobs/*/<FullName>_CoverLetter.tex` (or legacy `cover_letters/*/<FullName>_CoverLetter.tex`)

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

Full paths (both files in the same folder):

- **CV:** `applied_jobs/<application_folder>/<FullName>_CV.tex`
- **Cover letter:** `applied_jobs/<application_folder>/<FullName>_CoverLetter.tex`

Example: `applied_jobs/20260622-NorthernHealth-AIEngineerAgenticAIAndAdvancedAnalytics/`

### CV (`applied_jobs/<application_folder>/<FullName>_CV.tex`)
- Always in **English**
- Follow the moderncv/banking format from `05-cv-templates.md`
- Tailor the profile statement and experience bullets to the specific role
- Reframe skills and achievements to match job requirements
- Keep to 2 pages

### Cover Letter (`applied_jobs/<application_folder>/<FullName>_CoverLetter.tex`)
- Write in **English** (Australian spelling, e.g. "organise", "specialise")
- Follow the structure from `06-cover-letter-templates.md`
- Use the `cover.cls` template
- Tailor the opening paragraph to the specific role and company
- Address to a named person if available in the posting, otherwise "Dear Hiring Manager" (or equivalent in posting language)
- Keep to approximately one page
- Any mention of agentic coding or AI tooling should name the *specific* tools the candidate has genuinely used (e.g. Claude Code, Cursor, Copilot), not vague "AI tools" — and only ones that are actually true for them

Write both files to disk. Keep the exact text of both drafts in working memory — you will pass them inline to the reviewer in Step 3 and revise them in Step 4 without re-reading.

---

## Step 3: REVIEWER - Research & Critique

Spawn a **reviewer subagent** with fresh context (see the platform adapter for the exact invocation). Pass the drafts **inline in the prompt** below (do not make the reviewer Read them). Scope the reviewer's file reads to content-critique essentials only — the reviewer does not need the LaTeX template files (`05`, `06`) to critique content, since those govern structural/LaTeX concerns the drafter already applied.

Replace `<APPLICATION_FOLDER>`, `<FULLNAME>`, `<ROLE>`, `<INSERT_JOB_POSTING_TEXT_HERE>`, `<INSERT_CV_DRAFT_HERE>`, and `<INSERT_COVER_LETTER_DRAFT_HERE>` with actual values before dispatching (`<FULLNAME>` = candidate name with underscores, e.g. `Andrew_Pham`).

```
You are a hiring manager proxy reviewing a job application. Your job is to make the application as targeted and compelling as possible.

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
- `skills/job-application-assistant/02-behavioral-profile.md` — use this specifically to check whether the cover letter's voice matches the candidate's natural register. A "Collaborator" PI profile, for example, should not be given a combative, solo-hero tone; a "Persuader" profile should not be given over-hedged, apologetic phrasing.
- `skills/job-application-assistant/03-writing-style.md`
- `skills/job-application-assistant/04-job-evaluation.md`

Do NOT read `05-cv-templates.md` or `06-cover-letter-templates.md` — those govern LaTeX structure the drafter already applied and are not needed for content critique.

### 3. Drafts to Review
Both drafts are provided inline below. Do NOT use the Read tool on the draft files — use these exact texts.

<CV_DRAFT file="applied_jobs/<APPLICATION_FOLDER>/<FULLNAME>_CV.tex">
<INSERT_CV_DRAFT_HERE>
</CV_DRAFT>

<COVER_LETTER_DRAFT file="applied_jobs/<APPLICATION_FOLDER>/<FULLNAME>_CoverLetter.tex">
<INSERT_COVER_LETTER_DRAFT_HERE>
</COVER_LETTER_DRAFT>

### 4. Job Posting
<JOB_POSTING>
<INSERT_JOB_POSTING_TEXT_HERE>
</JOB_POSTING>

### 5. Produce Feedback

Return your feedback in **two parts**:

**Part A — Structured edits (preferred format whenever possible):**
A JSON array of concrete edits the drafter can apply directly without re-reading the files. Each edit is an object:
```json
{
  "file": "applied_jobs/<APPLICATION_FOLDER>/<FULLNAME>_CV.tex" | "applied_jobs/<APPLICATION_FOLDER>/<FULLNAME>_CoverLetter.tex",
  "old_string": "<exact text currently in the draft>",
  "new_string": "<replacement text>",
  "reason": "<one-line rationale: keyword match / company angle / reframing / style>"
}
```
Only use this format when you can quote the exact `old_string` from the drafts above. Make `old_string` unique — include enough surrounding context so it matches exactly once per file.

**Part B — Narrative suggestions (for judgment calls that are not mechanical edits):**
Prose suggestions grouped by category. Produce each category even if your finding is "no issues" — silence on a category can be mistaken for skipping it.
- **Missed keywords/requirements** — what to add and roughly where, if it cannot be expressed as a clean string replacement
- **Company/department-specific angles** — connections between experience and the company's strategic priorities, based on your research
- **Action-oriented reframing** — identify passive, generic, or low-energy statements and suggest action-oriented rewrites. Use this category especially for structural weakness that doesn't fit a single-sentence swap (e.g., "the whole opening paragraph reads as passive — restructure around your single strongest match to the posting").
- **Tone and style issues** — check against `03-writing-style.md` AND `02-behavioral-profile.md`. Flag any issues with tone, formality, or voice (cliches, hedging, over-humility, inconsistent register), and specifically flag any mismatch between the letter's voice and the candidate's natural register as described in the behavioral profile.

**CRITICAL RULE:** All suggestions must be grounded in actual profile data. Do NOT suggest fabricating skills, experience, or achievements. If a requirement is a gap, say so honestly and suggest how to frame adjacent experience instead.

Do **not** run a verification checklist — the drafter will do that in the final step. Focus on content critique.

Return Part A and Part B together as a single structured message.
```

---

## Step 4: DRAFTER - Revise Based on Feedback

Once the reviewer agent returns its feedback:

1. **Apply Part A (structured edits) directly** — edit files in place (search/replace). Do NOT re-read the draft files — you already have them in context from Step 2, and the reviewer's `old_string` values were quoted from that same text. For each edit in the JSON array, apply the given `file`, `old_string`, and `new_string`. Skip any whose rationale would require fabricating content.
2. **Apply Part B (narrative suggestions)** using judgment. These need interpretation, not mechanical replacement. Walk through every Part B category the reviewer returned and address it:
   - **Missed keywords/requirements:** add the keyword or capability where it fits naturally in the CV or cover letter. Prefer the experience bullets (concrete evidence) over the profile statement (abstract claim).
   - **Company/department-specific angles:** weave the reviewer's research into the cover letter opening or motivation paragraph. Verify every company claim via WebFetch/WebSearch before including it — do not trust reviewer research at face value.
   - **Action-oriented reframing:** rewrite passive or generic phrasing (CV profile statement, cover letter opening, bullet leads). Structural weakness that the reviewer flagged without a clean JSON edit lives here.
   - **Tone and style issues:** apply the writing-style-guide fixes (no em-dashes, no cliches, no apologetic hedging, consistent first-person active voice).
   Use targeted search/replace edits; only re-read a file if an edit fails because the surrounding text has shifted.
3. Do NOT incorporate any suggestion that would fabricate skills or experience. If a posting requirement is a genuine gap, acknowledge it honestly and frame adjacent experience instead.

After all edits are applied, the two files on disk are the final drafts.

---

## Step 5: DRAFTER - Compile & Inspect PDFs (MANDATORY)

**Never skip this step.** The `.tex` files looking fine is not sufficient — LaTeX page-break decisions are unpredictable and commonly produce broken layouts (orphaned job titles separated from their bullets, cover letters spilling to 2 pages, bullet fonts not matching body text). Compile both documents and visually verify the PDFs before presenting.

### 5a. Compile

Use `latex_build.py` so aux/log/out land in each application folder's `build/` subfolder (final `.pdf` stays beside the `.tex`):

```bash
python tools/latex_build.py \
  --cv "applied_jobs/<application_folder>/<FullName>_CV.tex" \
  --cover "applied_jobs/<application_folder>/<FullName>_CoverLetter.tex"
```

- CV uses **lualatex**; cover letter uses **xelatex** (cover.cls requires fontspec).
- Artifacts: `applied_jobs/<application_folder>/build/*`
- If either compile fails, fix the error and re-compile until clean.

### 5b. Inspect layout

Read both PDFs via the Read tool and verify:

**CV (`applied_jobs/<application_folder>/<FullName>_CV.pdf`):**
- [ ] Exactly 2 pages (not 1, not 3)
- [ ] No orphaned `\cventry` titles — a job/education title line must never sit alone at the bottom of page 1 with its bullets on page 2. This is the most common failure.
- [ ] Section headings are not isolated at the top of page 2 with only 1-2 lines below
- [ ] No awkward whitespace gaps

**Cover letter (`applied_jobs/<application_folder>/<FullName>_CoverLetter.pdf`):**
- [ ] Exactly 1 page
- [ ] Signature block visible, not cut off or pushed to a second page
- [ ] Bullet list font matches surrounding body text (both should be Raleway-Medium)

### 5c. Iterate until clean

If the layout has problems, edit the `.tex` files and recompile. Common fixes (see `05-cv-templates.md` and `06-cover-letter-templates.md` for full details):

- **Orphaned CV entry title:** `\usepackage{needspace}` in preamble, then `\needspace{5\baselineskip}` immediately before the problematic `\cventry`
- **CV spills to page 3 with only a trailing section:** `\enlargethispage{2-3\baselineskip}` before a late section
- **Substantial content on page 3:** cut content using **relevance-weighted cutting** (see `05-cv-templates.md` → "Relevance-weighted cutting"). Score each candidate line by (a) relevance to THIS posting's keywords and responsibilities, (b) uniqueness (is it duplicated elsewhere?), (c) narrative load (does the cover letter depend on it?). Cut the lowest-total-score line first, regardless of section. Do NOT mechanically apply a static section-based priority order — an older-role bullet that hits posting keywords is worth more than a recent-role bullet that does not.
- **Cover letter itemize breaks compile or uses wrong font:** close `\lettercontent{}` before the list, wrap the list in `{\raggedright\fontspec[Path = ../../cover_letters/OpenFonts/fonts/raleway/]{Raleway-Medium}\fontsize{11pt}{13pt}\selectfont \begin{itemize}...\end{itemize}\par}` (from `applied_jobs/<folder>/`, fonts and `cover.cls` live under `cover_letters/`)
- **Cover letter spills to 2 pages:** trim using the same relevance-weighted logic. First cut: sentences that restate what a bullet already said. Second cut: a bullet that does not hit posting keywords. Last resort: a bullet that does hit posting keywords. Never reduce geometry or line spacing.

Do not proceed to Step 6 until both PDFs pass inspection.

### 5d. Clean up build artifacts

After the final clean compile:

```bash
python tools/cleanup_latex.py
```

This moves any stray `.aux` / `.log` / `.out` files into each folder's `build/` subfolder. A **daily purge** at 11 PM can be installed with `./scripts/install-latex-cleanup.sh` (optional).

---

## Step 6: Update Tracker & Present Final Output

### 6a. Update job tracker (automatic)

After CV and cover letter PDFs pass inspection (Step 5), upsert a row in `job_search_tracker.csv` so the local tracker UI reflects this application. Run from the repo root:

```bash
python tracker/upsert_application.py \
  --company "<Company Name>" \
  --role "<Role Title>" \
  --cv-file "applied_jobs/<application_folder>/<FullName>_CV.tex" \
  --cover-letter-file "applied_jobs/<application_folder>/<FullName>_CoverLetter.tex" \
  --source "<source_url from Step 0>" \
  --fit-rating "<strong fit | moderate fit | weak fit from Step 1>" \
  --sector "<sector if known, else omit>" \
  --json
```

- **Match key:** `company` + `role` (case-insensitive). Re-running `/apply` for the same role updates file paths and `source`; existing `status` is preserved.
- **Source URL:** must be the canonical posting link from Step 0 (`url` from SEEK detail JSON). Never use README/example placeholder IDs.
- **Defaults:** `status` = `draft` from `tracker/statuses.json`; `channel` inferred from URL (`SEEK`, `LinkedIn`, or `web`).
- If the command fails, report the error but still present the documents to the user.

Tell the user they can view the row at **http://127.0.0.1:8765** if the tracker server is running (`cd tracker && python server.py`). The UI polls for CSV changes and refreshes automatically within a few seconds.

### 6b. Verification & presentation

Run the full verification checklist from `AGENTS.md` now — this is the **only** verification pass in the workflow. Re-read both files once here to verify final state on disk matches your mental model after the Step 4 and Step 5 edits.

### Verification Checklist
Report pass/fail for each item in the AGENTS.md verification checklist (factual accuracy, targeting, consistency, quality).

### Key Tailoring Decisions
Summarize 3-5 key decisions made to tailor the application:
- What was emphasized and why
- What company-specific angles were incorporated
- What the reviewer suggested that was most impactful
- Any gaps that were acknowledged or reframed

### Files Created
List the files written:
- `applied_jobs/<application_folder>/<FullName>_CV.tex`
- `applied_jobs/<application_folder>/<FullName>_CoverLetter.tex`

Confirm tracker row was created/updated (Step 6a).

Tell the user: "Both files are ready for your review. The application is in your job tracker (http://127.0.0.1:8765 if the server is running)."
