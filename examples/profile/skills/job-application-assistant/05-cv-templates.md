# CV Templates and Tailoring Guide

## Profile Statement Templates

<!-- Run /setup to populate role-specific profile statements -->

## File naming and layout

Each application gets a dated folder under `applied_jobs/` (CV and cover letter in the same folder):

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

Output files:

```
applied_jobs/<application_folder>/<FullName>_CV.tex
applied_jobs/<application_folder>/<FullName>_CV.pdf
applied_jobs/<application_folder>/<FullName>_CoverLetter.tex
applied_jobs/<application_folder>/<FullName>_CoverLetter.pdf
```

Compile with `latex_build.py` (artifacts go to `build/`):

```bash
python tools/latex_build.py applied_jobs/<application_folder>/<FullName>_CV.tex
python tools/latex_build.py applied_jobs/<application_folder>/<FullName>_CoverLetter.tex
```

Manual alternative from the application subfolder:

```bash
mkdir -p build
cd applied_jobs/<application_folder> && lualatex -interaction=nonstopmode -output-directory=build <FullName>_CV.tex
cp build/<FullName>_CV.pdf .
```

Legacy paths under `cv/<folder>/` and `cover_letters/<folder>/` still work; use `tools/migrate_application_folders.py` to consolidate.

Do not use legacy `main_<company>.tex` flat paths for new applications.

## Tailoring Checklist

When creating `applied_jobs/<application_folder>/<FullName>_CV.tex`:

1. **Create the application folder** — run `tools/application_paths.py --mkdir` (see above)
2. **Profile statement** — Pick or blend templates above; mirror job title language
3. **Core competencies** — Reorder to match posting keywords (AWS, Databricks, LLM, etc.)
4. **Experience bullets** — Lead with most relevant role; trim less relevant bullets to fit 2 pages
5. **Projects** — Include side projects when relevant; omit if space tight
6. **Certifications** — Lead with certs that match the posting's stack
7. **Teaching / mentoring** — Include for roles valuing communication; shorten for pure IC roles

## LaTeX Conventions

- Compile with **lualatex**
- Use `\needspace{5\baselineskip}` before each `\cventry`
- Target exactly **2 pages**
- Reference `cv/main_example.tex` for structure and styling

## Agentic Coding References

When roles mention AI-assisted development, name tools actually used:
- **Cursor** — IDE with AI pair programming
- **Claude Code / Claude** — agentic coding and documentation workflows

Do not claim tools not genuinely used.

## HTML fallback (when LaTeX unavailable)

Use when `/apply` falls back to HTML (user-approved) or `config/document_output.json` has `html_first`.

- **Template:** `templates/cv.html` — copy structure into `applied_jobs/<folder>/<FullName>_CV.html`
- **Styles:** `../../templates/cv.css` (moderncv banking blue `#2c5aa0`, 34pt name, section blocks)
- **Compile:** `python tools/html_build.py --cv applied_jobs/<folder>/<FullName>_CV.html`
- **Target:** exactly **2 pages** when printed to PDF
- **Page breaks:** use `.cv-entry { break-inside: avoid; }` — trim content if a third page appears

Reference example: `cv/main_example.html` (seeded from `examples/profile/`).
