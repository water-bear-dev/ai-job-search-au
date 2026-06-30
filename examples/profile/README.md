# Profile templates (tracked)

These files are **safe to commit** — they contain only placeholders (`[YOUR_NAME]`, etc.), not real personal data.

After clone, `./scripts/install-adapters.sh` runs `scripts/init-profile.sh`, which copies this tree into your local gitignored workspace:

| Template | Local copy (gitignored) |
|----------|-------------------------|
| `AGENTS.example.md` | `AGENTS.md` (+ `CLAUDE.md` symlink) |
| `skills/` | `skills/` |
| `cv/main_example.tex` | `cv/main_example.tex` |
| `cv/main_example.html` | `cv/main_example.html` (HTML fallback example) |
| `skills/` | `skills/` |
| `config/document_output.json` | `config/document_output.json` (from example on init) |

Then run **`/setup`** to replace placeholders with your real profile.

**Verify fonts after clone:** `./scripts/verify-assets.sh` (also runs from `install-adapters.sh`).

**Re-seed from templates** (destructive to blank placeholders only — skips if files already exist):

```bash
./scripts/init-profile.sh --force
```

**Manual copy** (same as init, without `--force`):

```bash
cp examples/profile/AGENTS.example.md AGENTS.md
ln -sfn AGENTS.md CLAUDE.md
cp -R examples/profile/skills/. skills/
mkdir -p cv && cp examples/profile/cv/main_example.tex cv/
```
