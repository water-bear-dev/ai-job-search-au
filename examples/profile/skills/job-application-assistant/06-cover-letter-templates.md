# Cover Letter Templates and Tailoring Guide

## Template: Custom cover.cls (XeLaTeX)

Cover letters use a custom LaTeX document class (`cover.cls`) with Lato/Raleway fonts.

**Output file:** `applied_jobs/<application_folder>/<FullName>_CoverLetter.tex`
**Compile with:** XeLaTeX (cover.cls requires fontspec)
**Font directory:** `cover_letters/OpenFonts/fonts/` (use `../../cover_letters/OpenFonts/fonts/` in `.tex` when the file lives under `applied_jobs/`)

### File naming and layout

Each application shares one dated folder under `applied_jobs/` (same folder as the CV):

```
applied_jobs/<YYYYMMDD>-<companyName>-<position>/
```

| Part | Rule | Example |
|------|------|---------|
| `<YYYYMMDD>` | Application date | `20260622` |
| `<companyName>` | Company in PascalCase | `NorthernHealth` |
| `<position>` | Role in PascalCase | `SeniorAIEngineer` |
| `<FullName>` | Candidate name; spaces → `_` | `[YOUR_NAME]` |

**Compute paths** (creates folders with `--mkdir`):

```bash
python tools/application_paths.py \
  --company "Northern Health" \
  --role "AI Engineer" \
  --full-name "[YOUR_NAME]" \
  --mkdir --json
```

```
applied_jobs/<application_folder>/<FullName>_CoverLetter.tex
applied_jobs/<application_folder>/<FullName>_CoverLetter.pdf
```

**LaTeX adjustments** (required when the `.tex` is under `applied_jobs/<folder>/`):
- Document class: `\documentclass{../../cover_letters/cover}` (not `\documentclass[]{cover}`)
- Itemize font wrapper: `Path = ../../cover_letters/OpenFonts/fonts/raleway/`
- `latex_build.py` creates an `OpenFonts` symlink in the application folder before compiling so `cover.cls` macros (`\namesection`, `\lettercontent`, etc.) resolve Lato/Raleway fonts. Do not commit the symlink.

### Compile command

```bash
python tools/latex_build.py applied_jobs/<application_folder>/<FullName>_CoverLetter.tex
```

Build artifacts: `applied_jobs/<application_folder>/build/`

Expected output: `Output written on <FullName>_CoverLetter.pdf (1 page, ...)`. Any page count other than 1 is a failure that must be fixed before presenting to the user.

## Compile-and-Inspect Loop (MANDATORY)

After writing the cover letter and before presenting to the user, always compile and visually inspect the PDF. Iterate until the layout is clean:

1. Run `python tools/latex_build.py applied_jobs/<application_folder>/<FullName>_CoverLetter.tex`
2. Confirm page count is exactly 1 and compile succeeded
3. Read the PDF via the Read tool and visually check: signature fits at the bottom, no text cut off, bullet font matches body

### Known template pitfall: itemize inside `\lettercontent{}`

The `\lettercontent{}` macro appends `\\` to its argument. This breaks when the argument ends in `\end{itemize}` because `\\` has no line to break after the environment closes, producing `! LaTeX Error: There's no line here to end.` and no PDF output.

**Wrong (breaks compile):**
```latex
\lettercontent{Here is how my experience maps:
\begin{itemize}
    \item ...
\end{itemize}}
```

**Correct — close `\lettercontent{}` before the list and wrap the list in the matching Raleway-Medium font so typography stays consistent:**
```latex
\lettercontent{Here is how my experience maps:}

{\raggedright\fontspec[Path = ../../cover_letters/OpenFonts/fonts/raleway/]{Raleway-Medium}\fontsize{11pt}{13pt}\selectfont
\begin{itemize}
    \item ...
\end{itemize}\par}
\vspace{6pt}

\lettercontent{[next paragraph]}
```

The font wrapper is mandatory — if you just move `\begin{itemize}` outside `\lettercontent{}` without the `\fontspec` block, bullets render in the default body font (Lato) and visually mismatch the rest of the letter.

## Document Structure

```latex
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Cover Letter - [Company], [Role]
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\documentclass{../../cover_letters/cover}
\usepackage{fancyhdr}

\pagestyle{fancy}
\fancyhf{}

\rfoot{Page \thepage \hspace{0pt}}
\thispagestyle{empty}
\renewcommand{\headrulewidth}{0pt}
\begin{document}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%     TITLE NAME
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\namesection{}{\Huge{[YOUR_NAME]}}{  \href{mailto:[YOUR_EMAIL]}{[YOUR_EMAIL]} | [YOUR_PHONE] |  \urlstyle{same}\href{[YOUR_LINKEDIN_URL]}{LinkedIn}
}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%     MAIN COVER LETTER CONTENT
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\currentdate{\today}
\lettercontent{Dear [Name/Team],}

\lettercontent{[Opening paragraph - role, connection to background, 2-3 sentences]}

\lettercontent{[Body paragraph - most relevant experience, then bullet list]

\begin{itemize}
    \item [Concrete achievement/skill 1]
    \item [Concrete achievement/skill 2]
    \item [Concrete achievement/skill 3]
\end{itemize}

[Connection to company - why this role, why this company specifically]}

\lettercontent{[Personal fit paragraph - behavioral strengths, team contribution, 2-3 sentences]}

\lettercontent{I look forward to hearing from you.}

\begin{flushright}
\closing{Kind regards,\\}

\signature{[YOUR_NAME]}
\end{flushright}
\end{document}
```

## Key Commands Reference

| Command | Purpose |
|---------|---------|
| `\namesection{}{Name}{contact info}` | Header with name and contact |
| `\currentdate{date}` | Date field (use `\today` or explicit date) |
| `\lettercontent{text}` | Body paragraph (adds spacing after) |
| `\closing{text}` | Closing line |
| `\signature{name}` | Printed name below signature |

## Tailoring Guidelines

### Salutation
- If you know the hiring manager's name: "Dear [First Last],"
- If you know the team: "Dear [Company] hiring team,"
- Generic: "Dear [Company]," (avoid "To whom it may concern")

### Length - Hard 1-Page Limit
- Target: 1 page including signature block
- Maximum: **never exceed 1 page**
- **Word budget: 250-300 words** of body text (not counting LaTeX markup). This is the safe maximum. 350 words will overflow.
- **Always count**: opening paragraph + bullet list paragraph + closing paragraph = 3 blocks. Add a 4th only if the others are short.
- When adding company-specific content, trim other content to compensate rather than adding net length

### Line Spacing
- Add `\usepackage{setspace}` and `\setstretch{1.0}` if the letter is long and needs to fit on one page
- Use `\vspace{.5cm}` between major sections for readability (only if space permits)

### Bullet Lists
- Place `\begin{itemize}...\end{itemize}` **outside** a `\lettercontent{}` block (see "Known template pitfall" above), wrapped in the matching Raleway-Medium `\fontspec` so the bullet font matches the body
- 3-5 bullets is ideal
- Start each bullet with bold label or action verb
- Use `\textbf{Label:}` for category-style bullets

### LaTeX Special Characters
- Underscore: `\_`
- Ampersand: `\&`

### Conventions (Australian market)
- Write in English with Australian spelling (organise, specialise, centre)
- Date format: D Month YYYY (e.g. 17 June 2026)
- Standard closing: "Kind regards," or "Yours sincerely,"

## Checklist Before Finalizing
- [ ] No em-dashes (use commas or periods instead)
- [ ] No cliches or empty filler
- [ ] Every claim backed by specific example
- [ ] Forward-looking framing: focuses on tasks you'll solve, not just past duties
- [ ] Motivation section references this specific company's mission/values
- [ ] Company name and role are correct throughout
- [ ] Date is current
- [ ] Fits on one page
- [ ] Language matches the job posting language
- [ ] Salutation is appropriate (named person if possible)
- [ ] Headline is engaging and specific, not generic

## Submission Guidelines (Best Practice)
- Submit only the documents the employer requests
- Export as PDF to preserve formatting
- Name files clearly: `<FullName>_CV` and `<FullName>_CoverLetter` (e.g. `[YOUR_NAME]_CV.pdf`)
- Follow all employer instructions regarding anonymity or specific materials

## HTML fallback (when LaTeX unavailable)

Use when `/apply` falls back to HTML (user-approved) or `config/document_output.json` has `html_first`.

- **Template:** `templates/cover.html` — same sections as LaTeX (`cover-header`, `cover-date`, `cover-body`, `cover-signature`)
- **Styles:** `../../templates/cover.css` (Lato name 40pt, Raleway-Medium 11pt body — mirrors `cover.cls`)
- **Bullets:** native `<ul><li>` inside `.cover-body` (no `\lettercontent` + itemize pitfall)
- **Compile:** `python tools/html_build.py --cover applied_jobs/<folder>/<FullName>_CoverLetter.html`
- **Target:** exactly **1 page** including signature
- **Fonts:** shared with LaTeX via `cover_letters/OpenFonts/` and `templates/fonts.css`

Reference example: `examples/profile/cover_letters/cover_example.html`.
