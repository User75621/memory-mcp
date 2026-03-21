-- Memory MCP schema
-- Persistent project memory for AI models and coding agents.

create extension if not exists pgcrypto;

-- Shared timestamp helper used by mutable tables.
create or replace function update_updated_at_column()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

-- Projects are the top-level ownership boundary for all memory data.
create table if not exists projects (
  id uuid primary key default gen_random_uuid(),
  owner_id text not null,
  name text not null,
  slug text not null unique,
  description text not null default '',
  primary_interface text not null default 'native',
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

-- Architectural snapshots store current structure and rationale.
create table if not exists architecture (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  owner_id text not null,
  diagram text not null default '',
  summary text not null default '',
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

-- Decisions persist cross-interface reasoning and implementation choices.
create table if not exists decisions (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  owner_id text not null,
  interface text not null,
  decision_type text not null default 'general',
  summary text not null,
  details text not null default '',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

-- Tasks track execution state shared among agents and interfaces.
create table if not exists tasks (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  owner_id text not null,
  title text not null default 'Untitled task',
  status text not null default 'pending',
  priority text not null default 'medium',
  details text not null default '',
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

-- Preferences store reusable behavioral or formatting settings.
create table if not exists preferences (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  owner_id text not null,
  preference_key text not null,
  preference_value jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (project_id, preference_key)
);

-- Sessions register active and historical conversations or coding sessions.
create table if not exists sessions (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  owner_id text not null,
  interface text not null,
  model_name text not null,
  status text not null default 'active',
  started_at timestamptz not null default timezone('utc', now()),
  ended_at timestamptz,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

-- Warnings highlight blockers, risks, or important follow-up items.
create table if not exists warnings (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  owner_id text not null,
  interface text not null,
  severity text not null check (severity in ('low', 'medium', 'high', 'critical')),
  message text not null,
  is_active boolean not null default true,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

-- Interface logs keep a detailed event trail for analysis and debugging.
create table if not exists interface_logs (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  owner_id text not null,
  interface text not null,
  event_name text not null,
  payload jsonb not null default '{}'::jsonb,
  latency_ms integer not null default 0,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

-- Session state stores synchronized working memory snapshots.
create table if not exists session_state (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references sessions(id) on delete cascade,
  project_id uuid not null references projects(id) on delete cascade,
  owner_id text not null,
  state jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (session_id)
);

-- Performance-oriented indexes for common access patterns.
create index if not exists idx_projects_owner_id on projects(owner_id);
create index if not exists idx_architecture_project_id on architecture(project_id);
create index if not exists idx_decisions_project_id on decisions(project_id);
create index if not exists idx_tasks_project_status on tasks(project_id, status);
create index if not exists idx_preferences_project_key on preferences(project_id, preference_key);
create index if not exists idx_sessions_project_interface on sessions(project_id, interface);
create index if not exists idx_warnings_project_active on warnings(project_id, is_active);
create index if not exists idx_logs_project_interface on interface_logs(project_id, interface);
create index if not exists idx_session_state_project_id on session_state(project_id);

-- Timestamp triggers keep update metadata accurate across all mutable tables.
create or replace trigger trg_projects_updated_at
before update on projects
for each row execute function update_updated_at_column();

create or replace trigger trg_architecture_updated_at
before update on architecture
for each row execute function update_updated_at_column();

create or replace trigger trg_decisions_updated_at
before update on decisions
for each row execute function update_updated_at_column();

create or replace trigger trg_tasks_updated_at
before update on tasks
for each row execute function update_updated_at_column();

create or replace trigger trg_preferences_updated_at
before update on preferences
for each row execute function update_updated_at_column();

create or replace trigger trg_sessions_updated_at
before update on sessions
for each row execute function update_updated_at_column();

create or replace trigger trg_warnings_updated_at
before update on warnings
for each row execute function update_updated_at_column();

create or replace trigger trg_interface_logs_updated_at
before update on interface_logs
for each row execute function update_updated_at_column();

create or replace trigger trg_session_state_updated_at
before update on session_state
for each row execute function update_updated_at_column();

-- RLS helper expression supports either JWT sub or locally injected owner context.
alter table projects enable row level security;
alter table architecture enable row level security;
alter table decisions enable row level security;
alter table tasks enable row level security;
alter table preferences enable row level security;
alter table sessions enable row level security;
alter table warnings enable row level security;
alter table interface_logs enable row level security;
alter table session_state enable row level security;

create policy projects_owner_policy on projects
for all using (
  owner_id = coalesce(
    current_setting('request.jwt.claim.sub', true),
    current_setting('app.current_owner_id', true)
  )
) with check (
  owner_id = coalesce(
    current_setting('request.jwt.claim.sub', true),
    current_setting('app.current_owner_id', true)
  )
);

create policy architecture_owner_policy on architecture
for all using (
  owner_id = coalesce(
    current_setting('request.jwt.claim.sub', true),
    current_setting('app.current_owner_id', true)
  )
) with check (
  owner_id = coalesce(
    current_setting('request.jwt.claim.sub', true),
    current_setting('app.current_owner_id', true)
  )
);

create policy decisions_owner_policy on decisions
for all using (
  owner_id = coalesce(
    current_setting('request.jwt.claim.sub', true),
    current_setting('app.current_owner_id', true)
  )
) with check (
  owner_id = coalesce(
    current_setting('request.jwt.claim.sub', true),
    current_setting('app.current_owner_id', true)
  )
);

create policy tasks_owner_policy on tasks
for all using (
  owner_id = coalesce(
    current_setting('request.jwt.claim.sub', true),
    current_setting('app.current_owner_id', true)
  )
) with check (
  owner_id = coalesce(
    current_setting('request.jwt.claim.sub', true),
    current_setting('app.current_owner_id', true)
  )
);

create policy preferences_owner_policy on preferences
for all using (
  owner_id = coalesce(
    current_setting('request.jwt.claim.sub', true),
    current_setting('app.current_owner_id', true)
  )
) with check (
  owner_id = coalesce(
    current_setting('request.jwt.claim.sub', true),
    current_setting('app.current_owner_id', true)
  )
);

create policy sessions_owner_policy on sessions
for all using (
  owner_id = coalesce(
    current_setting('request.jwt.claim.sub', true),
    current_setting('app.current_owner_id', true)
  )
) with check (
  owner_id = coalesce(
    current_setting('request.jwt.claim.sub', true),
    current_setting('app.current_owner_id', true)
  )
);

create policy warnings_owner_policy on warnings
for all using (
  owner_id = coalesce(
    current_setting('request.jwt.claim.sub', true),
    current_setting('app.current_owner_id', true)
  )
) with check (
  owner_id = coalesce(
    current_setting('request.jwt.claim.sub', true),
    current_setting('app.current_owner_id', true)
  )
);

create policy interface_logs_owner_policy on interface_logs
for all using (
  owner_id = coalesce(
    current_setting('request.jwt.claim.sub', true),
    current_setting('app.current_owner_id', true)
  )
) with check (
  owner_id = coalesce(
    current_setting('request.jwt.claim.sub', true),
    current_setting('app.current_owner_id', true)
  )
);

create policy session_state_owner_policy on session_state
for all using (
  owner_id = coalesce(
    current_setting('request.jwt.claim.sub', true),
    current_setting('app.current_owner_id', true)
  )
) with check (
  owner_id = coalesce(
    current_setting('request.jwt.claim.sub', true),
    current_setting('app.current_owner_id', true)
  )
);

-- Aggregated analytics help compare interface usage and session duration.
create or replace view interface_analytics as
select
  s.project_id,
  s.owner_id,
  s.interface,
  count(*) as total_sessions,
  count(*) filter (where s.status = 'active') as active_sessions,
  max(s.started_at) as last_started_at,
  avg(
    extract(epoch from coalesce(s.ended_at, timezone('utc', now())) - s.started_at)
  )::numeric(10, 2) as avg_session_seconds
from sessions s
group by s.project_id, s.owner_id, s.interface;
