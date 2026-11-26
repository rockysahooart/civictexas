# Deployment

Nothing in this guide has been done yet. Each step needs an account owner's approval. Every service listed has a free tier, and no paid service is required.

## 1. Waitlist (already live)

GitHub Pages serves the repository root from `main`: https://rockysahooart.github.io/civictexas/. The `.nojekyll` file tells Pages to serve files as-is. The application directories are also publicly readable through Pages, as they already are on GitHub. They contain no secrets.

## 2. Database (Supabase)

1. Create a Supabase project (free tier).
2. Apply the migrations in `supabase/migrations/` in order, either with the Supabase CLI (`supabase link`, then `supabase db push`) or by pasting each file into the SQL editor. **Do not** run `supabase/local/supabase_shim.sql` on Supabase. It is for plain local PostgreSQL only.
3. Copy two connection strings from Project Settings → Database:
   - **Session or direct connection**, for the ingestion job
   - **Transaction pooler (port 6543)**, for the web app on Vercel

Keep both secret. They go in server-side environment variables only, never in client code or the repository.

## 3. Scheduled ingestion (GitHub Actions)

1. In the GitHub repository, open **Settings → Secrets and variables → Actions**.
2. Add the secret `DATABASE_URL` with the Supabase connection string.
3. Optionally add the variable `SYNC_SESSIONS`, for example `90R`. The default is `90R`.
4. Run **Actions → Sync legislative data → Run workflow** once with mode `sample` to load the sample. Then try `full` with a limit.
5. The schedule (`.github/workflows/sync.yml`) then runs incremental syncs every 6 hours. Edit the cron to change that. The source files generally refresh once a day.

Until the secret exists, the scheduled workflow exits early without doing anything.

## 4. Web app (Vercel)

1. Import the repository in Vercel and set **Root Directory** to `web`.
2. Set the environment variables:
   - `DATABASE_URL`: the transaction pooler connection string
   - `NEXT_PUBLIC_STALE_AFTER_HOURS`: for example `48`
3. Deploy. Every route that reads data is rendered on demand, so it shows current database contents.

## 5. After deploying

- Check that `/bills` lists the synced bills and that the freshness table on `/` shows recent times.
- Confirm in Supabase that the `anon` role cannot read `ai_summaries` rows that aren't approved. The migration enforces this, and `ingestion/tests/test_sync_db.py` tests it.
- Watch `sync_runs` for `partial` or `failed` runs.

## Secrets checklist

| Secret | Where it lives | Never |
| --- | --- | --- |
| `DATABASE_URL` | GitHub Actions secret, Vercel env | in the repository, in `NEXT_PUBLIC_*` variables |
| `OPEN_STATES_API_KEY` (future) | GitHub Actions secret | in client code |
| `SUMMARY_API_KEY` (future) | where summaries are generated (not the web app) | in client code |
| Waitlist subscriber emails | the form service only | anywhere in this repository |
