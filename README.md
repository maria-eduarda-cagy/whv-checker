# WHV 462 Country Caps Monitor

Monitor the Australian WHV 462 country caps page and notify on Telegram when **Brazil** changes to `open`.

This project runs with **two schedulers in parallel**:
- GitHub Actions (`*/15`)
- Supabase Scheduler (`*/15`, via Edge Function proxy)

Both schedulers call the same checker logic and share state in Supabase, so deduplication is global.

## Architecture

1. Checker (`app/check_caps.py`)
- Fetches source HTML
- Parses Brazil status
- Persists checks in Supabase
- Sends Telegram only on transition/dedupe condition

2. HTTP worker (`app/server.py`)
- Exposes `POST /check` (for Supabase proxy)
- Optional bearer auth via `WORKER_AUTH`

3. Supabase Edge Function (`supabase/functions/check_caps_proxy/index.ts`)
- Calls deployed worker URL (`WORKER_URL/check`)
- Used by Supabase Scheduler

4. Shared state in Supabase tables
- `country_last_state`
- `status_checks`
- `notifications`

## Local run

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... python -m app.check_caps
```

Run HTTP worker:

```bash
uvicorn app.server:app --host 0.0.0.0 --port 8000
```

Container run:

```bash
docker build -t whv-checker .
docker run -p 8000:8000 --env-file .env whv-checker
```

## GitHub Actions scheduler

Workflow: `/Users/mariacagy/whv-checker/.github/workflows/whv-checker.yml`

Required GitHub secrets:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Optional GitHub secrets:
- `SOURCE_URL` (defaults to immi URL)
- `TARGET_COUNTRY` (defaults to `Brazil`)

## Supabase setup

1. Link project and apply migrations:

```bash
supabase link --project-ref <PROJECT_REF>
supabase db push
```

2. Deploy Edge Function:

```bash
supabase functions deploy check_caps_proxy
```

3. Set Edge Function secrets:

```bash
supabase secrets set WORKER_URL="https://<your-worker-host>" WORKER_AUTH="<your-token>"
```

4. Configure Supabase Scheduler job:
- Function: `check_caps_proxy`
- Method: `POST`
- Cron: `*/15 * * * *`

## Dedupe rule

Telegram is sent only when:
- `status == open`, and
- previous status is not `open` OR `last_notified_status` is not `open`

After successful send, `last_notified_status` becomes `open`.

## Notes

- If Supabase is unavailable, the checker fails (by design) to prevent duplicate notifications from stateless execution.
- The old `state.json` strategy is no longer the source of truth.

## Cron test (Supabase -> Worker -> Telegram)

Set a worker env var:
- `TEST_NOTIFY_TOKEN=<strong-random-token>`

Run smoke test:

```bash
SUPABASE_URL=... \
SUPABASE_SERVICE_ROLE_KEY=... \
SUPABASE_PROJECT_REF=... \
TEST_NOTIFY_TOKEN=... \
python -m app.test_supabase_cron
```

The script invokes `check_caps_proxy` with `force_notify_test`, then confirms:
- a new row in `status_checks`
- a new Telegram row in `notifications`
