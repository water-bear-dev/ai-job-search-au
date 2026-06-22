# Install Guide

Everything you need to run AI Job Search AU. Most steps are one-time.

## TL;DR

| Tool | Required? | For |
|------|-----------|-----|
| AI agent (pick one) | **Yes** | Running the workflow — [Claude Code](https://claude.com/claude-code), [Cursor](https://cursor.com), or [Antigravity](https://antigravity.google/) / `agy` CLI |
| Python 3.10+ | **Yes** | `seek-search` (SEEK discovery) + salary tool |
| LaTeX (TinyTeX / MacTeX / MiKTeX / TeX Live) | **Yes, for `/apply`** | Compiling CV + cover-letter PDFs |
| [`gh`](https://cli.github.com/) (GitHub CLI) | Optional | Forking/cloning |
| Job tracker UI | Optional | `pip install -r tracker/requirements.txt` — local dashboard only |

No Node/Bun needed (the old Danish CLIs that required Bun have been removed).

After clone, run **`./scripts/install-adapters.sh`** to wire up platform skill symlinks. See
[PLATFORMS.md](PLATFORMS.md).

---

## 1. AI agent (pick one)

### Claude Code

```bash
npm install -g @anthropic-ai/claude-code
```

You'll need a Claude Pro/Max/Team subscription or an Anthropic API key. Docs:
<https://docs.anthropic.com/en/docs/claude-code>.

### Cursor

Install from <https://cursor.com>. Open this repo — skills in `.cursor/skills/` and the
always-on rule in `.cursor/rules/job-search-core.mdc` activate automatically.

### Antigravity / Antigravity CLI

Install from <https://antigravity.google/>. Project skills live in `.agents/skills/`. If the
CLI does not discover them, run `./scripts/install-adapters.sh --antigravity-cli-global`.

See [PLATFORMS.md](PLATFORMS.md) for invocation details per tool.

## 2. Python 3.10+

Check:

```bash
python3 --version
```

- **macOS:** `brew install python` (or use the system Python 3)
- **Windows:** <https://www.python.org/downloads/> (tick "Add to PATH")
- **Linux:** usually preinstalled; else `sudo apt install python3`

Both `seek-search` and the optional `linkedin-search` use **only the standard library** — no
`pip install` required.

> **Optional — LinkedIn (`tools/linkedin-search`):** works with no key and no login, but
> **automating LinkedIn is against its Terms of Service.** It's **off by default** in
> `/scrape` and is for personal, low-volume use at your own risk. SEEK is the primary,
> supported source. See [`tools/linkedin-search/README.md`](tools/linkedin-search/README.md).

## 3. LaTeX (needed only when you run `/apply`)

`/apply` compiles your CV with **lualatex** and your cover letter with **xelatex**, then
visually checks the PDFs. You can set up your profile and run `/scrape` without LaTeX; you
only need it for the application step.

For manual compiles, use **`tools/latex_build.py`** (recommended) — it picks the right engine,
passes `-interaction=nonstopmode`, and keeps aux/log/out in each application folder's
`build/` subfolder. See [README → Compiling LaTeX](README.md#compiling-latex).

### Option A — TinyTeX (recommended; **no sudo / admin password needed**)

TinyTeX installs entirely in your home folder. This is the easiest path, especially on
managed/work machines:

```bash
# Install TinyTeX
curl -sL "https://yihui.org/tinytex/install-bin-unix.sh" | sh        # macOS / Linux
# Windows (PowerShell):
#   irm https://yihui.org/tinytex/install-bin-windows.bat | iex

# Add the binaries to PATH (macOS/Linux). The installer prints the exact path; typically:
export PATH="$PATH:$HOME/Library/TinyTeX/bin/universal-darwin"        # macOS
# export PATH="$PATH:$HOME/.TinyTeX/bin/x86_64-linux"                 # Linux
# (append that line to ~/.zshrc or ~/.bashrc to make it permanent)

# Install the packages this project needs (one command — saves you the trial-and-error)
tlmgr install \
  moderncv needspace marvosym fontawesome5 fontspec \
  pgf luatexbase import xcolor microtype enumitem etoolbox geometry hyperref \
  l3packages l3kernel luaotfload ctablestack environ trimspaces xkeyval everysel \
  pdftexcmds infwarerr ltxcmds
```

Verify:

```bash
lualatex --version   # should print "LuaHBTeX ... TeX Live ..."
xelatex  --version
```

> The package list above is exactly what `moderncv` (CV) and `cover.cls` (cover letter)
> pull in on a minimal TinyTeX. Installing them up front avoids the "File `X.sty` not found"
> errors you'd otherwise hit one at a time.

### Option B — Full distribution (simplest if you don't mind the download size)

- **macOS:** [MacTeX](https://tug.org/mactex/) (~4 GB) — `brew install --cask mactex` (needs your password)
- **Windows:** [MiKTeX](https://miktex.org/download) (installs missing packages on demand)
- **Linux:** `sudo apt install texlive-full` or `sudo dnf install texlive-scheme-full`

## 4. (Optional) GitHub CLI

For `gh repo fork ... --clone`:

```bash
brew install gh        # macOS
gh auth login
```

---

## Verify the setup

```bash
# One-shot smoke test — confirms both SEEK endpoints (search + detail) still work:
./verify.sh

# Or just the search, as a table:
python3 tools/seek-search/seek_search.py --keywords "Software Engineer" --where "All Brisbane QLD" --pages 1 --table
```

**macOS SSL errors** (`CERTIFICATE_VERIFY_FAILED` from the system Python): run Apple's
[Install Certificates.command](https://www.python.org/download/mac/tcltk/) for your Python
install, or rely on `./verify.sh` (uses `curl`) until certificates are fixed.

**LaTeX** (after `/setup` has created your local `cv/` workspace):

```bash
# Quick check — compile the example CV (should say "Output written on ... (2 pages ...)"):
cd cv
lualatex -interaction=nonstopmode main_example.tex

# Or use the project build helper (keeps artifacts in build/):
python tools/latex_build.py cv/main_example.tex
```

---

## Keeping your data private

This repo is designed to be forked publicly. **Your personal data stays local** —
`.gitignore` keeps it out of git:

| Gitignored | What it holds |
|------------|---------------|
| `cv/`, `skills/`, `AGENTS.md` | Profile and LaTeX workspace (populated by `/setup`) |
| `cover_letters/*/*.tex`, nested CV `.tex` | Generated application outputs |
| `documents/` (except `.gitkeep`), `job_search_tracker.csv` | Supporting files and tracker |
| `job_scraper/seen_jobs.json`, `*.pdf`, `salary_data.json` | Scrape state, compiled PDFs, salary data |

Nothing in the public template repo contains your name, employment history, or applications.
After clone, run `/setup` to build your local workspace under those paths.

`CLAUDE.md` is a **symlink to `AGENTS.md`** (tracked as a symlink only — safe to push as long
as you never commit the profile file itself).

### Recommended: enable the pre-commit hook

The repo ships a hook that blocks accidentally staging profile files — useful on **older
forks** that still track them, or if you force-add ignored paths:

```bash
git config core.hooksPath .githooks
```

It refuses commits that stage `AGENTS.md`, `cv/main_example.tex`, filled-in skill files, etc.
(Intentionally editing upstream *templates* with no real data? Bypass with
`git commit --no-verify`.)

### Other options

1. **Private fork:** keep the repo private, or use a separate private clone for your filled-in
   workspace.
2. **Skip-worktree on legacy tracked files:** if your fork still tracks profile paths from
   before the gitignore change, run `git update-index --skip-worktree <file>` on each so git
   ignores local changes.

Manual pre-push check (legacy tracked paths):

```bash
git diff --cached --name-only \
  | grep -E 'AGENTS\.md|CLAUDE\.md|cv/main_example\.tex|search-queries\.md|job-application-assistant/(01|02|04|05|07)' \
  && echo "STOP: personal profile staged — unstage before pushing"
```

See also [README → Privacy](README.md#privacy-).
