# Job Tracker (local UI)

Browser dashboard for `job_search_tracker.csv` at the repo root. Used by `/scrape` dedup and `/upskill` — **do not change CSV column names**.

## Install

```bash
cd tracker
pip install -r requirements.txt
```

Optional: use a venv in the repo (`.venv` is gitignored).

## Run

```bash
cd tracker
python server.py
# or
./run.sh
```

Open **http://127.0.0.1:8765**

Override port: `TRACKER_PORT=9000 python server.py`

The UI **auto-refreshes** every few seconds when `job_search_tracker.csv` changes (e.g. after `/apply` runs `upsert_application.py`). Keep this server running while you work.

## First run

If `job_search_tracker.csv` does not exist, the server copies
`job_search_tracker.example.csv` from the repo root.

## Configure statuses

Edit [`statuses.json`](statuses.json) — add, remove, or reorder statuses. Restart the server.
Set `default_status` for new rows (used when `/apply` auto-tracks an application).

## Auto-tracking from `/apply`

When `/apply` finishes drafting a CV and cover letter, it runs `tracker/upsert_application.py` to create or update a row keyed by `company` + `role`. File paths, source URL, and fit rating are filled in; status defaults to `default_status` (`draft`).

Manual upsert:

```bash
python tracker/upsert_application.py \
  --company "Acme Corp" \
  --role "Data Engineer" \
  --cv-file "applied_jobs/20260622-AcmeCorp-DataEngineer/Andrew_Pham_CV.tex" \
  --cover-letter-file "applied_jobs/20260622-AcmeCorp-DataEngineer/Andrew_Pham_CoverLetter.tex" \
  --source "https://www.seek.com.au/job/92686067"
```

Paths are computed by `tools/application_paths.py` (`<YYYYMMDD>-<companyName>-<position>` folders).

## Security

- Binds **127.0.0.1** only (local machine)
- No authentication — do not expose to the network
- File downloads restricted to `applied_jobs/`, `cv/`, `cover_letters/`, `documents/applications/`

## CSV columns

```
date, company, sector, role, role_type, channel, status, contact_person,
fit_rating, notes, cv_file, cover_letter_file, source
```

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/jobs` | List jobs (newest first; `index` is CSV row index) |
| POST | `/api/jobs` | Create job |
| PUT | `/api/jobs/{index}` | Update job |
| DELETE | `/api/jobs/{index}` | Delete job |
| POST | `/api/jobs/bulk` | Bulk update status or move to Recycle Bin (`{ indices, action, status? }`) |
| GET | `/api/trash` | List Recycle Bin jobs (with `days_remaining`) |
| GET | `/api/trash/info` | Retention policy + expired purge count |
| POST | `/api/trash/{index}/restore` | Restore one job to tracker |
| DELETE | `/api/trash/{index}` | Permanently delete one job |
| POST | `/api/trash/bulk` | Bulk restore or permanent delete |
| GET | `/api/revision` | Data revision (poll to detect CSV changes from `/apply`) |
| POST | `/api/revision` | Notify hook (called by `upsert_application.py` after writes) |
| GET | `/api/profile` | Candidate profile sections from `AGENTS.md` |
| PUT | `/api/profile` | Update `AGENTS.md` Candidate Profile (body: `{ sections: [{ title, raw }] }`) |
| GET | `/api/files?path=...` | Download attachment |

Interactive docs: http://127.0.0.1:8765/api/docs
