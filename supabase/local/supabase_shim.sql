-- LOCAL DEVELOPMENT ONLY. Do not run against a Supabase project.
--
-- Supabase provides the `auth` schema, `auth.uid()` and the anon /
-- authenticated / service_role roles. This file recreates the minimum of that
-- on a plain PostgreSQL server so the migrations and RLS policies can be
-- applied and tested without Docker or a Supabase account.

do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'anon') then
    create role anon nologin noinherit;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'authenticated') then
    create role authenticated nologin noinherit;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'service_role') then
    create role service_role nologin noinherit bypassrls;
  end if;
end $$;

create schema if not exists auth;
grant usage on schema auth to anon, authenticated, service_role;
grant usage on schema public to anon, authenticated, service_role;

create table if not exists auth.users (
  id    uuid primary key default gen_random_uuid(),
  email text unique
);

-- Mirrors Supabase: reads the user id from the request's JWT claims.
create or replace function auth.uid()
returns uuid language sql stable as $$
  select nullif(
    coalesce(
      current_setting('request.jwt.claim.sub', true),
      (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub')
    ), '')::uuid;
$$;
grant execute on function auth.uid() to anon, authenticated, service_role;
