# Profile templates (tracked)

These files are **safe to commit** — they contain only placeholders (`[YOUR_NAME]`, etc.), not real personal data.

After clone, `./scripts/install-adapters.sh` runs `scripts/init-profile.sh`, which copies this tree into your local gitignored workspace:

| Template | Local copy (gitignored) |
|----------|-------------------------|
| `AGENTS.example.md` | `AGENTS.md` (+ `CLAUDE.md` symlink) |
| `skills/` | `skills/` |
| `skills/.../01-candidate-profile.internal-nab.md` | Optional internal overlay (created only if `/setup` opts in; placeholder is unused) |
| `cv/main_example.tex` | `cv/main_example.tex` |
| `cv/main_example.html` | `cv/main_example.html` (HTML fallback example) |
| `config/document_output.json` | `config/document_output.json` (from example on init) |
| `config/digest.json` | `config/digest.json` (from `digest.example.json` on init; gitignored) |

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
