# Authentication Load & Stress Toolkit

This toolkit is separate from the Selenium smoke tests. It uses pure Python with `asyncio + httpx` to exercise Student / Organizer / Admin authentication flows at concurrent load.

## Targets

- `https://batuhanakbasak.com/student/login`
- `https://batuhanakbasak.com/organizer/organizer-login`
- `https://batuhanakbasak.com/admin/login`

## What it measures

- Response time
- Failure count and failure rate
- Throughput (requests per second)
- Percentile latency (`p50`, `p90`, `p95`, `p99`)
- Per-stage and per-request summaries

## Safety notes

- Start with the default stages first.
- Do not point aggressive stages at production unless you have explicit permission.
- The toolkit has a hard concurrency guard. Raise it only on systems you own and only intentionally.
- Dashboard API calls are disabled by default to reduce unnecessary load.

## Folder layout

- `config.py`: environment loading, stage parsing, safe defaults
- `main.py`: async runner and staged concurrency orchestration
- `report_generator.py`: JSON, CSV, and Markdown report output
- `requirements.txt`: Python dependencies for this toolkit only
- `.env.example`: example environment configuration

## Setup on Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r auth_load_toolkit\requirements.txt
Copy-Item auth_load_toolkit\.env.example auth_load_toolkit\.env
```

Then edit `auth_load_toolkit\.env` and add your real credentials.

## Run

Dry run to verify configuration only:

```powershell
python auth_load_toolkit\main.py --dry-run
```

Run the load test:

```powershell
python auth_load_toolkit\main.py
```

## Output

Each run writes a new timestamped folder under:

```text
auth_load_toolkit/results/
```

Artifacts:

- `results.json`
- `request_results.csv`
- `summary.md`

## Important environment variables

- `TARGET_BASE_URL`
- `TARGET_API_BASE_URL`
- `ENABLED_ROLES`
- `LOAD_STAGES`
- `INCLUDE_LOGIN_PAGE_GET`
- `INCLUDE_DASHBOARD_REQUEST`
- `DASHBOARD_REQUEST_MODE`
- `REQUEST_TIMEOUT_SECONDS`
- `REQUEST_DELAY_SECONDS`
- `ALLOW_HIGH_STRESS`

Credentials:

- `STUDENT_EMAIL`, `STUDENT_PASSWORD`
- `ORGANIZER_EMAIL`, `ORGANIZER_PASSWORD`
- `ADMIN_EMAIL`, `ADMIN_PASSWORD`

Optional authenticated dashboard API targets:

- `STUDENT_DASHBOARD_API_PATH`
- `ORGANIZER_DASHBOARD_API_PATH`
- `ADMIN_DASHBOARD_API_PATH`

If these are empty and `DASHBOARD_REQUEST_MODE=auto`, the toolkit falls back to dashboard page requests instead of authenticated API calls.
