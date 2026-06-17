# Install Guide

Everything you need to run AI Job Search AU. Most steps are one-time.

## TL;DR

| Tool | Required? | For |
|------|-----------|-----|
| [Claude Code](https://claude.com/claude-code) | **Yes** | Running the whole workflow |
| Python 3.10+ | **Yes** | `seek-search` (SEEK discovery) + salary tool |
| LaTeX (TinyTeX / MacTeX / MiKTeX / TeX Live) | **Yes, for `/apply`** | Compiling CV + cover-letter PDFs |
| [`gh`](https://cli.github.com/) (GitHub CLI) | Optional | Forking/cloning |

No Node/Bun needed (the old Danish CLIs that required Bun have been removed).

---

## 1. Claude Code

```bash
npm install -g @anthropic-ai/claude-code
```

You'll need a Claude Pro/Max/Team subscription or an Anthropic API key. Docs:
<https://docs.anthropic.com/en/docs/claude-code>.

## 2. Python 3.10+

Check:

```bash
python3 --version
```

- **macOS:** `brew install python` (or use the system Python 3)
- **Windows:** <https://www.python.org/downloads/> (tick "Add to PATH")
- **Linux:** usually preinstalled; else `sudo apt install python3`

`seek-search` uses **only the standard library** — no `pip install` required.

## 3. LaTeX (needed only when you run `/apply`)

`/apply` compiles your CV with **lualatex** and your cover letter with **xelatex**, then
visually checks the PDFs. You can set up your profile and run `/scrape` without LaTeX; you
only need it for the application step.

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
# SEEK discovery works (should print live Brisbane jobs):
cd tools/seek-search
python3 seek_search.py --keywords "Software Engineer" --where "All Brisbane QLD" --pages 1 --table

# LaTeX works (compile the example CV; should say "Output written on ... (2 pages ...)"):
cd ../../cv
lualatex -interaction=nonstopmode main_example.tex
```

---

## Keeping your data private

This repo is designed to be forked. The `.gitignore` already keeps these **out** of git:
your resume and `documents/`, `seen_jobs.json`, all compiled PDFs, generated `cv/main_*.tex`
and cover letters, the tracker CSV, and salary data.

**The one exception:** your **profile files are tracked** —

- `CLAUDE.md`
- `.claude/skills/job-application-assistant/01-candidate-profile.md` (and `02`, `04`, `05`, `07`)

After `/setup` fills these with your real name, contact details, and history, they show up
as normal modified files. If your fork is public, **don't `git push` them.** Options:

1. **Simplest:** just never commit them. Run `git update-index --skip-worktree CLAUDE.md`
   (and the same for each profile file) so git ignores your local changes to them.
2. **Belt-and-braces:** keep your filled-in copy in a *private* repo or local-only folder,
   and only push template/placeholder versions publicly.

A quick pre-push safety check:

```bash
git diff --cached --name-only | grep -E 'CLAUDE.md|01-candidate-profile|02-behavioral' \
  && echo "STOP: personal profile staged — unstage before pushing"
```
