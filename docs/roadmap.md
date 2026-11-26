# Development roadmap

In priority order. An item is checked only when it has been implemented and verified.

## Milestone 1: Go live with the proof of concept (next)

- [ ] Create the Supabase project and apply the migrations ([deployment.md](deployment.md))
- [ ] Add the `DATABASE_URL` secret and run the sample sync from GitHub Actions
- [ ] Deploy `web/` to Vercel and check every route against the live database
- [ ] Run a full 90R sync in batches, and confirm run times and that `sync_runs` shows no errors
- [ ] Connect the waitlist to a form service
- [ ] Choose a license

## Milestone 2: Complete official data

- [ ] Store bill analyses (linked now, not stored)
- [ ] Add member-level floor votes, from the House and Senate journals or a supplementary provider ([data-sources.md](data-sources.md))
- [ ] Add legislator metadata (party, district) from a supplementary provider, labeled as non-authoritative
- [ ] Add special sessions automatically
- [ ] Version comparison view (diff between two versions)
- [ ] Monitoring: alert when a sync fails or data passes the stale threshold

## Milestone 3: Summaries

- [ ] Choose and approve a model provider, and add its adapter
- [ ] Expand the evaluation set to at least 20 real bill versions, with reviewer-written required facts
- [ ] Review interface for staff (now a CLI)
- [ ] Publish the first reviewed summaries

## Milestone 4: Accounts and tracking

- [ ] Supabase Auth (`@supabase/ssr`) with profiles
- [ ] Saved bills
- [ ] Email notifications when saved bills change

## Milestone 5: Community

- [ ] Bill-specific discussion with moderation, ordered by time
- [ ] Moderation queue for `content_reports`, and appeals
- [ ] Community guidelines

## Done in the Phase 2 proof of concept

- [x] Repository audit. Waitlist preserved, application in its own directories.
- [x] Data source research ([data-sources.md](data-sources.md))
- [x] Database schema with RLS (20 tables), applied and tested on PostgreSQL 16
- [x] Ingestion from official TLC bulk files: sample, incremental and full modes, verified against 89R and 90R
- [x] Status mapping with tests based on real records
- [x] Searchable directory and bill detail pages with loading, empty, error, stale and not-found states
- [x] Summarization architecture, validation, review workflow and evaluation set (no provider connected)
- [x] Anonymous error reporting
- [x] CI workflow and scheduled sync workflow (sync inactive until configured)
