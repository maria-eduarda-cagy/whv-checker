# WHV 462 Country Caps Monitor

Monitor the Australian WHV 462 country caps page and notify on Telegram when **Brazil** changes to `open`.

This project runs with **two schedulers in parallel**:
- GitHub Actions (`*/5`)
- Supabase Scheduler (`*/5`, via Edge Function proxy)

Both schedulers call the same checker logic and share state in Supabase, so deduplication is global.

## Architecture

1. Checker (`app/check_caps.py`)
- Fetches source HTML
- Parses Brazil status
- Persists checks in Supabase
- Sends Telegram only on transition/dedupe condition

2. HTTP worker (`app/server.py`)
- Exposes `POST /check` (for Supabase proxy)

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
SUPABASE_URL=... 
SUPABASE_SERVICE_ROLE_KEY=... 
TELEGRAM_BOT_TOKEN=... 
TELEGRAM_CHAT_ID=... 
python -m app.check_caps
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
- Cron: `*/5 * * * *`

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

## Operational tests

1. Local logic test (`open` transition):

```bash
PYTHONPATH=. .venv/bin/pytest -q tests/test_check_caps.py -k transition_to_open
```

2. Direct worker smoke test (bypasses Supabase):

```bash
curl -i -X POST "https://whv-checker.onrender.com/check" \
  -H "Content-Type: application/json" \
  -d '{"force_notify_test":true,"test_notify_token":"<TEST_NOTIFY_TOKEN>"}'
```

Expected:
- HTTP `200`
- JSON with `"notified":"true"`

3. Supabase path smoke test (Edge Function -> Worker -> Telegram):

```bash
SUPABASE_URL="https://<project-ref>.supabase.co" \
SUPABASE_SERVICE_ROLE_KEY="<service-role-key>" \
SUPABASE_PROJECT_REF="<project-ref>" \
TEST_NOTIFY_TOKEN="<TEST_NOTIFY_TOKEN>" \
python -m app.test_supabase_cron
```

Expected:
- `status_checks updated: True`
- `telegram notification recorded: True`
- `PASS`

4. If test 3 fails with HTTP 500, validate secrets:

```bash
supabase secrets list --project-ref <project-ref>
```

At minimum in Supabase:
- `WORKER_URL`
- `WORKER_AUTH` (optional; can be empty if worker auth disabled)

At minimum in worker runtime (Render):
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `TEST_NOTIFY_TOKEN`
