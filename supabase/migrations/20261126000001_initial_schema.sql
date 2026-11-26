-- Civic Texas: initial schema
--
-- Conventions
-- * Bill numbers are only unique within a legislative session:
--   unique (session_id, bill_type, bill_number).
-- * Official text is never overwritten. Each fetched document snapshot is a new
--   row in source_documents keyed by content hash; older snapshots are kept and
--   marked is_current = false.
-- * Legislative facts, AI summaries and community content live in separate
--   tables. Community tables never feed legislative or summary tables.
-- * The ingestion job writes with a privileged role (service_role on Supabase,
--   which bypasses RLS). Public clients read through RLS as anon/authenticated.

create extension if not exists pgcrypto;

-- ---------------------------------------------------------------------------
-- Shared helpers
-- ---------------------------------------------------------------------------

create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

-- ---------------------------------------------------------------------------
-- Reference data
-- ---------------------------------------------------------------------------

create table public.data_sources (
  id               text primary key,                 -- e.g. 'tlc_ftp'
  name             text not null,
  homepage_url     text not null,
  is_authoritative boolean not null default false,   -- official record vs. third party
  attribution      text,
  license_notes    text,
  created_at       timestamptz not null default now()
);

create table public.legislative_sessions (
  id                 text primary key,               -- TLC code: '89R', '891', '90R'
  legislature_number integer not null check (legislature_number > 0),
  session_type       text not null check (session_type in ('regular', 'special')),
  special_number     integer check (special_number is null or special_number > 0),
  name               text not null,                  -- '89th Legislature, Regular Session'
  start_date         date,
  end_date           date,                           -- null while unknown or ongoing
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now(),
  check ((session_type = 'regular') = (special_number is null))
);
create trigger legislative_sessions_updated_at before update on public.legislative_sessions
  for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- Bills
-- ---------------------------------------------------------------------------

create table public.bills (
  id                  uuid primary key default gen_random_uuid(),
  session_id          text not null references public.legislative_sessions(id),
  bill_type           text not null check (bill_type in ('HB','SB','HJR','SJR','HCR','SCR','HR','SR')),
  bill_number         integer not null check (bill_number > 0),
  identifier          text generated always as (bill_type || ' ' || bill_number) stored,
  chamber             text not null check (chamber in ('house', 'senate')),  -- chamber of origin
  caption             text not null,
  caption_version     text,                          -- bill version the caption belongs to
  status              text not null default 'unknown' check (status in (
                        'filed', 'in_committee', 'reported_from_committee',
                        'passed_origin_chamber', 'in_committee_second_chamber',
                        'reported_from_committee_second_chamber', 'amendments_pending', 'passed_both_chambers',
                        'sent_to_governor', 'signed', 'vetoed', 'became_law_without_signature',
                        'adopted', 'filed_with_secretary_of_state', 'not_passed_session_ended',
                        'unknown')),
  status_date         date,
  last_action_text    text,
  last_action_date    date,
  subjects            text[] not null default '{}',
  companions          text,
  source_id           text not null references public.data_sources(id),
  source_url          text not null,                 -- machine-readable source record
  official_url        text not null,                 -- human-readable official page
  source_updated_at   timestamptz,                   -- 'lastUpdate' reported by the source
  last_synced_at      timestamptz not null,          -- when we last confirmed this record
  content_hash        text not null,                 -- hash of the normalized source record
  search              tsvector,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now(),
  unique (session_id, bill_type, bill_number)
);
create index bills_session_idx on public.bills (session_id);
create index bills_status_idx on public.bills (status);
create index bills_chamber_idx on public.bills (chamber);
create index bills_last_action_idx on public.bills (last_action_date desc nulls last);
create index bills_subjects_idx on public.bills using gin (subjects);
create index bills_search_idx on public.bills using gin (search);
create trigger bills_updated_at before update on public.bills
  for each row execute function public.set_updated_at();

create or replace function public.bills_update_search()
returns trigger language plpgsql as $$
begin
  new.search :=
    setweight(to_tsvector('simple', coalesce(new.bill_type, '') || ' ' || coalesce(new.bill_number::text, '')
                                     || ' ' || coalesce(new.bill_type, '') || coalesce(new.bill_number::text, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(new.caption, '')), 'B') ||
    setweight(to_tsvector('english', array_to_string(new.subjects, ' ')), 'C');
  return new;
end;
$$;
create trigger bills_search_tsv before insert or update of caption, subjects, bill_type, bill_number
  on public.bills for each row execute function public.bills_update_search();

-- ---------------------------------------------------------------------------
-- People and committees
-- ---------------------------------------------------------------------------

-- The official bill history only gives display names ("Bell, Cecil"). Chamber is
-- inferred from the role on the bill. Richer metadata (party, district) can be
-- added later from a supplementary source via external_ids.
create table public.legislators (
  id            uuid primary key default gen_random_uuid(),
  display_name  text not null,
  chamber       text not null check (chamber in ('house', 'senate')),
  party         text,
  district      integer,
  external_ids  jsonb not null default '{}',
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  unique (chamber, display_name)
);
create trigger legislators_updated_at before update on public.legislators
  for each row execute function public.set_updated_at();

create table public.bill_sponsors (
  bill_id       uuid not null references public.bills(id) on delete cascade,
  legislator_id uuid not null references public.legislators(id),
  role          text not null check (role in ('author', 'coauthor', 'sponsor', 'cosponsor')),
  position      integer not null,
  primary key (bill_id, legislator_id, role)
);
create index bill_sponsors_legislator_idx on public.bill_sponsors (legislator_id);

create table public.committees (
  id         uuid primary key default gen_random_uuid(),
  chamber    text not null check (chamber in ('house', 'senate')),
  name       text not null,
  created_at timestamptz not null default now(),
  unique (chamber, name)
);

create table public.bill_committee_referrals (
  bill_id      uuid not null references public.bills(id) on delete cascade,
  committee_id uuid not null references public.committees(id),
  status       text,                                 -- as reported, e.g. 'Out of committee'
  updated_at   timestamptz not null default now(),
  primary key (bill_id, committee_id)
);

-- ---------------------------------------------------------------------------
-- Actions and votes
-- ---------------------------------------------------------------------------

create table public.bill_actions (
  id               uuid primary key default gen_random_uuid(),
  bill_id          uuid not null references public.bills(id) on delete cascade,
  sequence         integer not null,                 -- order in the official history
  action_code      text,                             -- e.g. 'H015', 'E020'
  actor            text not null check (actor in ('house', 'senate', 'executive', 'other')),
  action_date      date,
  action_timestamp timestamptz,
  description      text not null,
  comment          text,
  created_at       timestamptz not null default now(),
  unique (bill_id, sequence)
);
create index bill_actions_bill_idx on public.bill_actions (bill_id, sequence);

-- Vote tallies. The official bill history provides committee tallies; floor
-- record votes are referenced (e.g. 'RV#4015') but individual member votes
-- live in the House and Senate journals and are not ingested yet.
create table public.votes (
  id                 uuid primary key default gen_random_uuid(),
  bill_id            uuid not null references public.bills(id) on delete cascade,
  chamber            text not null check (chamber in ('house', 'senate')),
  vote_type          text not null check (vote_type in ('committee', 'floor')),
  committee_id       uuid references public.committees(id),
  vote_date          date,
  motion             text,
  -- Tallies are null when the source references a vote without giving counts.
  yeas               integer,
  nays               integer,
  present_not_voting integer,
  absent             integer,
  source_reference   text not null default '',       -- e.g. record vote number
  source_id          text not null references public.data_sources(id),
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now()
);
create unique index votes_natural_key on public.votes
  (bill_id, chamber, vote_type, coalesce(committee_id, '00000000-0000-0000-0000-000000000000'::uuid), source_reference);
create trigger votes_updated_at before update on public.votes
  for each row execute function public.set_updated_at();

create table public.vote_records (
  vote_id       uuid not null references public.votes(id) on delete cascade,
  legislator_id uuid not null references public.legislators(id),
  choice        text not null check (choice in ('yea', 'nay', 'present_not_voting', 'absent', 'excused')),
  primary key (vote_id, legislator_id)
);

-- ---------------------------------------------------------------------------
-- Versions and official documents
-- ---------------------------------------------------------------------------

-- One row per official version of the bill (Introduced, House Committee
-- Report, Engrossed, Senate Committee Report, Enrolled, ...).
create table public.bill_versions (
  id            uuid primary key default gen_random_uuid(),
  bill_id       uuid not null references public.bills(id) on delete cascade,
  version_code  text not null,                       -- TLC suffix: I, H, E, S, F, ...
  description   text not null,
  ordinal       integer not null,                    -- order the source lists them in
  html_url      text,
  pdf_url       text,
  first_seen_at timestamptz not null default now(),
  unique (bill_id, version_code)
);

-- Every retrieved document snapshot. Never updated in place except to flip
-- is_current when a newer snapshot of the same document arrives.
create table public.source_documents (
  id              uuid primary key default gen_random_uuid(),
  bill_id         uuid not null references public.bills(id) on delete cascade,
  bill_version_id uuid references public.bill_versions(id),
  doc_type        text not null check (doc_type in ('bill_text', 'analysis', 'fiscal_note')),
  version_code    text not null,
  source_id       text not null references public.data_sources(id),
  source_url      text not null,                     -- where we fetched it
  official_url    text,                              -- public web link
  content_hash    text not null,                     -- sha256 of raw bytes
  raw_content     text not null,                     -- as published (HTML)
  plain_text      text not null,                     -- extracted, whitespace-normalized
  retrieved_at    timestamptz not null default now(),
  is_current      boolean not null default true,
  supersedes_id   uuid references public.source_documents(id),
  unique (bill_id, doc_type, version_code, content_hash)
);
create unique index source_documents_one_current
  on public.source_documents (bill_id, doc_type, version_code) where is_current;

create or replace function public.source_documents_protect()
returns trigger language plpgsql as $$
begin
  if new.raw_content is distinct from old.raw_content
     or new.content_hash is distinct from old.content_hash
     or new.plain_text is distinct from old.plain_text then
    raise exception 'source_documents content is immutable; insert a new snapshot instead';
  end if;
  return new;
end;
$$;
create trigger source_documents_immutable before update on public.source_documents
  for each row execute function public.source_documents_protect();

create table public.fiscal_notes (
  id                 uuid primary key default gen_random_uuid(),
  bill_id            uuid not null references public.bills(id) on delete cascade,
  version_code       text not null,
  description        text not null,
  html_url           text,
  pdf_url            text,
  source_document_id uuid references public.source_documents(id),
  first_seen_at      timestamptz not null default now(),
  unique (bill_id, version_code)
);

-- ---------------------------------------------------------------------------
-- AI summaries (separate from legislative facts)
-- ---------------------------------------------------------------------------

create table public.ai_summaries (
  id                  uuid primary key default gen_random_uuid(),
  bill_id             uuid not null references public.bills(id) on delete cascade,
  bill_version_id     uuid not null references public.bill_versions(id),
  source_document_id  uuid not null references public.source_documents(id),
  source_content_hash text not null,                 -- hash of the exact text summarized
  provider            text not null,
  model_id            text not null,
  prompt_version      text not null,
  generated_at        timestamptz not null default now(),
  content             jsonb not null,                -- structured summary (see summarization/schema.py)
  validation          jsonb not null,                -- automated check results
  review_status       text not null default 'pending_review' check (review_status in
                        ('pending_review', 'approved', 'rejected', 'superseded')),
  reviewed_by         uuid,
  reviewed_at         timestamptz,
  review_notes        text,
  created_at          timestamptz not null default now()
);
create index ai_summaries_bill_idx on public.ai_summaries (bill_id, generated_at desc);
create unique index ai_summaries_one_approved
  on public.ai_summaries (bill_version_id) where review_status = 'approved';

-- When a new snapshot of a bill's text arrives, summaries of the old text are
-- superseded so they stop being shown and get regenerated.
create or replace function public.supersede_stale_summaries()
returns trigger language plpgsql as $$
begin
  if new.doc_type = 'bill_text' then
    update public.ai_summaries s
       set review_status = 'superseded'
     where s.bill_id = new.bill_id
       and s.review_status in ('pending_review', 'approved')
       and s.source_document_id in (
         select d.id from public.source_documents d
          where d.bill_id = new.bill_id and d.doc_type = 'bill_text'
            and d.version_code = new.version_code and d.id <> new.id);
  end if;
  return new;
end;
$$;
create trigger source_documents_supersede_summaries after insert on public.source_documents
  for each row execute function public.supersede_stale_summaries();

-- ---------------------------------------------------------------------------
-- Users and community (prepared, not yet used by the app)
-- ---------------------------------------------------------------------------

create table public.profiles (
  id           uuid primary key references auth.users(id) on delete cascade,
  display_name text check (char_length(display_name) <= 80),
  role         text not null default 'member' check (role in ('member', 'reviewer', 'moderator', 'admin')),
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);
create trigger profiles_updated_at before update on public.profiles
  for each row execute function public.set_updated_at();

create or replace function public.current_user_role()
returns text language sql stable security definer set search_path = public as $$
  select role from public.profiles where id = auth.uid();
$$;

create or replace function public.is_staff()
returns boolean language sql stable as $$
  select coalesce(public.current_user_role() in ('reviewer', 'moderator', 'admin'), false);
$$;

create table public.saved_bills (
  user_id    uuid not null references public.profiles(id) on delete cascade,
  bill_id    uuid not null references public.bills(id) on delete cascade,
  notify     boolean not null default false,
  created_at timestamptz not null default now(),
  primary key (user_id, bill_id)
);

-- Deliberately no score, like or vote columns: comments are ordered by time,
-- not popularity.
create table public.comments (
  id         uuid primary key default gen_random_uuid(),
  bill_id    uuid not null references public.bills(id) on delete cascade,
  user_id    uuid not null references public.profiles(id) on delete cascade,
  parent_id  uuid references public.comments(id) on delete cascade,
  body       text not null check (char_length(body) between 1 and 5000),
  status     text not null default 'visible' check (status in ('visible', 'hidden', 'removed')),
  created_at timestamptz not null default now(),
  edited_at  timestamptz
);
create index comments_bill_idx on public.comments (bill_id, created_at);

-- Reports can be filed without an account so anyone can flag an inaccurate
-- summary or data error.
create table public.content_reports (
  id               uuid primary key default gen_random_uuid(),
  reporter_id      uuid references public.profiles(id) on delete set null,
  target_type      text not null check (target_type in ('ai_summary', 'comment', 'bill_data')),
  target_id        uuid not null,
  reason           text not null check (reason in ('inaccurate', 'misleading', 'missing_information',
                                                   'biased', 'abusive', 'spam', 'other')),
  details          text check (char_length(details) <= 2000),
  status           text not null default 'open' check (status in ('open', 'reviewing', 'resolved', 'dismissed')),
  resolved_by      uuid references public.profiles(id),
  resolved_at      timestamptz,
  resolution_notes text,
  created_at       timestamptz not null default now()
);
create index content_reports_status_idx on public.content_reports (status, created_at);

-- ---------------------------------------------------------------------------
-- Synchronization bookkeeping
-- ---------------------------------------------------------------------------

create table public.sync_runs (
  id               uuid primary key default gen_random_uuid(),
  source_id        text not null references public.data_sources(id),
  session_id       text references public.legislative_sessions(id),
  mode             text not null check (mode in ('full', 'incremental', 'sample')),
  status           text not null default 'running' check (status in ('running', 'succeeded', 'partial', 'failed')),
  started_at       timestamptz not null default now(),
  finished_at      timestamptz,
  bills_seen       integer not null default 0,
  bills_changed    integer not null default 0,
  documents_added  integer not null default 0,
  errors           jsonb not null default '[]',
  notes            text
);
create index sync_runs_recent_idx on public.sync_runs (source_id, session_id, started_at desc);

create table public.sync_state (
  source_id              text not null references public.data_sources(id),
  session_id             text not null references public.legislative_sessions(id),
  last_successful_run_id uuid references public.sync_runs(id),
  last_successful_at     timestamptz,
  cursor                 text,                       -- source-specific (e.g. last seen history timestamp)
  primary key (source_id, session_id)
);

-- ---------------------------------------------------------------------------
-- Row-level security
-- ---------------------------------------------------------------------------

alter table public.data_sources             enable row level security;
alter table public.legislative_sessions     enable row level security;
alter table public.bills                    enable row level security;
alter table public.legislators              enable row level security;
alter table public.bill_sponsors            enable row level security;
alter table public.committees               enable row level security;
alter table public.bill_committee_referrals enable row level security;
alter table public.bill_actions             enable row level security;
alter table public.votes                    enable row level security;
alter table public.vote_records             enable row level security;
alter table public.bill_versions            enable row level security;
alter table public.source_documents         enable row level security;
alter table public.fiscal_notes             enable row level security;
alter table public.ai_summaries             enable row level security;
alter table public.profiles                 enable row level security;
alter table public.saved_bills              enable row level security;
alter table public.comments                 enable row level security;
alter table public.content_reports          enable row level security;
alter table public.sync_runs                enable row level security;
alter table public.sync_state               enable row level security;

-- Public legislative data: readable by everyone, no account required.
-- There are no insert/update/delete policies, so only the privileged
-- ingestion role can write.
do $$
declare t text;
begin
  foreach t in array array['data_sources', 'legislative_sessions', 'bills', 'legislators',
                           'bill_sponsors', 'committees', 'bill_committee_referrals',
                           'bill_actions', 'votes', 'vote_records', 'bill_versions',
                           'source_documents', 'fiscal_notes', 'sync_runs', 'sync_state']
  loop
    execute format('create policy "public read" on public.%I for select to anon, authenticated using (true)', t);
    execute format('grant select on public.%I to anon, authenticated', t);
  end loop;
end $$;

-- AI summaries: only reviewed and approved summaries are public. Reviewers can
-- see everything and record decisions.
create policy "approved summaries are public" on public.ai_summaries
  for select to anon, authenticated using (review_status = 'approved');
create policy "staff read all summaries" on public.ai_summaries
  for select to authenticated using (public.is_staff());
create policy "staff review summaries" on public.ai_summaries
  for update to authenticated using (public.is_staff()) with check (public.is_staff());
grant select on public.ai_summaries to anon, authenticated;
grant update (review_status, reviewed_by, reviewed_at, review_notes) on public.ai_summaries to authenticated;

-- Profiles: users read and edit their own profile, but cannot change their role.
create policy "read own profile" on public.profiles
  for select to authenticated using (id = auth.uid() or public.is_staff());
create policy "update own profile" on public.profiles
  for update to authenticated using (id = auth.uid()) with check (id = auth.uid());
grant select on public.profiles to authenticated;
grant update (display_name) on public.profiles to authenticated;

-- Saved bills: private to each user.
create policy "manage own saved bills" on public.saved_bills
  for all to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());
grant select, insert, update, delete on public.saved_bills to authenticated;

-- Comments: visible comments are public; members write and edit their own.
create policy "visible comments are public" on public.comments
  for select to anon, authenticated using (status = 'visible' or user_id = auth.uid() or public.is_staff());
create policy "members post comments" on public.comments
  for insert to authenticated with check (user_id = auth.uid() and status = 'visible');
create policy "members edit own comments" on public.comments
  for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy "moderators moderate comments" on public.comments
  for update to authenticated using (public.is_staff()) with check (public.is_staff());
grant select on public.comments to anon, authenticated;
grant insert (bill_id, user_id, parent_id, body) on public.comments to authenticated;
grant update (body, edited_at, status) on public.comments to authenticated;

-- Content reports: anyone can file one; reporters see their own; staff see all.
create policy "anyone can report" on public.content_reports
  for insert to anon, authenticated
  with check (status = 'open'
              and resolved_by is null
              and (reporter_id is null or reporter_id = auth.uid()));
create policy "reporters read own reports" on public.content_reports
  for select to authenticated using (reporter_id = auth.uid() or public.is_staff());
create policy "staff resolve reports" on public.content_reports
  for update to authenticated using (public.is_staff()) with check (public.is_staff());
grant insert (reporter_id, target_type, target_id, reason, details) on public.content_reports to anon, authenticated;
grant select on public.content_reports to authenticated;
grant update (status, resolved_by, resolved_at, resolution_notes) on public.content_reports to authenticated;
