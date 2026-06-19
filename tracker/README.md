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

## First run

If `job_search_tracker.csv` does not exist, the server copies
`job_search_tracker.example.csv` from the repo root.

## Configure statuses

Edit [`statuses.json`](statuses.json) — add, remove, or reorder statuses. Restart the server.
Set `default_status` for new rows.

## Security

- Binds **127.0.0.1** only (local machine)
- No authentication — do not expose to the network
- File downloads restricted to `cv/`, `cover_letters/`, `documents/applications/`

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
| GET | `/api/statuses` | Status config |
| GET | `/api/files?path=...` | Download attachment |

Interactive docs: http://127.0.0.1:8765/api/docs
