-- Memory MCP schema
-- Persistent project memory for AI models and coding agents.

create extension if not exists pgcrypto;
create extension if not exists vector;

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

-- Workspaces group projects for multi-team or multi-client usage.
create table if not exists workspaces (
  id uuid primary key default gen_random_uuid(),
  owner_id text not null,
  slug text not null,
  name text not null,
  description text not null default '',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (owner_id, slug)
);

-- Projects are the top-level ownership boundary for all memory data.
create table if not exists projects (
  id uuid primary key default gen_random_uuid(),
  owner_id text not null,
  workspace_id uuid references workspaces(id) on delete set null,
  name text not null,
  slug text not null,
  description text not null default '',
  primary_interface text not null default 'native',
  repo_path text not null default '',
  repo_remote text not null default '',
  repo_branch text not null default '',
  repo_last_commit text not null default '',
  repo_status jsonb not null default '{}'::jsonb,
  project_summary text not null default '',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

alter table projects add column if not exists workspace_id uuid references workspaces(id) on delete set null;
alter table projects add column if not exists repo_path text not null default '';
alter table projects add column if not exists repo_remote text not null default '';
alter table projects add column if not exists repo_branch text not null default '';
alter table projects add column if not exists repo_last_commit text not null default '';
alter table projects add column if not exists repo_status jsonb not null default '{}'::jsonb;
alter table projects add column if not exists project_summary text not null default '';
alter table projects add column if not exists metadata jsonb not null default '{}'::jsonb;

do $$
begin
  if not exists (
    select 1 from pg_indexes where schemaname = 'public' and indexname = 'idx_projects_owner_slug'
  ) then
    create unique index idx_projects_owner_slug on projects(owner_id, slug);
  end if;
end
$$;

-- Architectural snapshots store current structure and rationale.
create table if not exists architecture (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  owner_id text not null,
  diagram text not null default '',
  summary text not null default '',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

alter table architecture add column if not exists metadata jsonb not null default '{}'::jsonb;

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
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

alter table tasks add column if not exists metadata jsonb not null default '{}'::jsonb;

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
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

alter table sessions add column if not exists metadata jsonb not null default '{}'::jsonb;

-- Warnings highlight blockers, risks, or important follow-up items.
create table if not exists warnings (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  owner_id text not null,
  interface text not null,
  severity text not null check (severity in ('low', 'medium', 'high', 'critical')),
  message text not null,
  is_active boolean not null default true,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

alter table warnings add column if not exists metadata jsonb not null default '{}'::jsonb;

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
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (session_id)
);

alter table session_state add column if not exists metadata jsonb not null default '{}'::jsonb;

-- Checkpoints summarize architecture, blockers, and next actions.
create table if not exists checkpoints (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  owner_id text not null,
  title text not null,
  architecture_summary text not null default '',
  functional_state text not null default '',
  blockers jsonb not null default '[]'::jsonb,
  next_steps jsonb not null default '[]'::jsonb,
  tags text[] not null default '{}',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

-- File memory stores file-level summaries and importance.
create table if not exists file_memory (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  owner_id text not null,
  file_path text not null,
  file_role text not null default 'module',
  summary text not null,
  symbols jsonb not null default '[]'::jsonb,
  importance text not null default 'medium',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (project_id, file_path)
);

-- File relations capture dependencies between modules or files.
create table if not exists file_relations (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  owner_id text not null,
  source_file text not null,
  target_file text not null,
  relation_type text not null default 'depends_on',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (project_id, source_file, target_file, relation_type)
);

-- Prompt patterns store reusable prompts and working styles.
create table if not exists prompt_patterns (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  owner_id text not null,
  title text not null,
  category text not null default 'general',
  prompt text not null,
  usage_notes text not null default '',
  response_style text not null default '',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (project_id, title)
);

-- Searchable memory documents back semantic and lexical search.
create table if not exists memory_documents (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  owner_id text not null,
  source_type text not null,
  source_id text not null,
  title text not null,
  content text not null,
  keywords text[] not null default '{}',
  embedding vector(1536),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

-- Timeline events make it easy to reconstruct what happened over time.
create table if not exists timeline_events (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  owner_id text not null,
  event_type text not null,
  summary text not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

-- Retention policies keep storage efficient while preserving summaries.
create table if not exists retention_policies (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references projects(id) on delete cascade,
  owner_id text not null,
  keep_recent_sessions integer not null default 5,
  keep_recent_decisions integer not null default 20,
  archive_after_days integer not null default 30,
  summarize_archived boolean not null default true,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (project_id)
);

-- Performance-oriented indexes for common access patterns.
create index if not exists idx_workspaces_owner_slug on workspaces(owner_id, slug);
create index if not exists idx_projects_owner_id on projects(owner_id);
create index if not exists idx_projects_workspace_slug on projects(workspace_id, slug);
create index if not exists idx_architecture_project_id on architecture(project_id);
create index if not exists idx_decisions_project_id on decisions(project_id);
create index if not exists idx_tasks_project_status on tasks(project_id, status);
create index if not exists idx_preferences_project_key on preferences(project_id, preference_key);
create index if not exists idx_sessions_project_interface on sessions(project_id, interface);
create index if not exists idx_warnings_project_active on warnings(project_id, is_active);
create index if not exists idx_logs_project_interface on interface_logs(project_id, interface);
create index if not exists idx_session_state_project_id on session_state(project_id);
create index if not exists idx_checkpoints_project_created on checkpoints(project_id, created_at desc);
create index if not exists idx_file_memory_project_path on file_memory(project_id, file_path);
create index if not exists idx_file_relations_project_source on file_relations(project_id, source_file);
create index if not exists idx_prompt_patterns_project_title on prompt_patterns(project_id, title);
create index if not exists idx_memory_documents_project_source on memory_documents(project_id, source_type);
create index if not exists idx_timeline_events_project_created on timeline_events(project_id, created_at desc);
create index if not exists idx_retention_policies_project on retention_policies(project_id);
create index if not exists idx_memory_documents_fts on memory_documents using gin (
  to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(content, ''))
);
create index if not exists idx_memory_documents_embedding on memory_documents using ivfflat (
  embedding vector_cosine_ops
) with (lists = 100);

-- Timestamp triggers keep update metadata accurate across all mutable tables.
create or replace trigger trg_workspaces_updated_at
before update on workspaces
for each row execute function update_updated_at_column();

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

create or replace trigger trg_checkpoints_updated_at
before update on checkpoints
for each row execute function update_updated_at_column();

create or replace trigger trg_file_memory_updated_at
before update on file_memory
for each row execute function update_updated_at_column();

create or replace trigger trg_file_relations_updated_at
before update on file_relations
for each row execute function update_updated_at_column();

create or replace trigger trg_prompt_patterns_updated_at
before update on prompt_patterns
for each row execute function update_updated_at_column();

create or replace trigger trg_memory_documents_updated_at
before update on memory_documents
for each row execute function update_updated_at_column();

create or replace trigger trg_timeline_events_updated_at
before update on timeline_events
for each row execute function update_updated_at_column();

create or replace trigger trg_retention_policies_updated_at
before update on retention_policies
for each row execute function update_updated_at_column();

-- RLS helper expression supports either JWT sub or locally injected owner context.
alter table workspaces enable row level security;
alter table projects enable row level security;
alter table architecture enable row level security;
alter table decisions enable row level security;
alter table tasks enable row level security;
alter table preferences enable row level security;
alter table sessions enable row level security;
alter table warnings enable row level security;
alter table interface_logs enable row level security;
alter table session_state enable row level security;
alter table checkpoints enable row level security;
alter table file_memory enable row level security;
alter table file_relations enable row level security;
alter table prompt_patterns enable row level security;
alter table memory_documents enable row level security;
alter table timeline_events enable row level security;
alter table retention_policies enable row level security;

create policy workspaces_owner_policy on workspaces
for all using (
  owner_id = coalesce(current_setting('request.jwt.claim.sub', true), current_setting('app.current_owner_id', true))
) with check (
  owner_id = coalesce(current_setting('request.jwt.claim.sub', true), current_setting('app.current_owner_id', true))
);

create policy projects_owner_policy on projects
for all using (
  owner_id = coalesce(current_setting('request.jwt.claim.sub', true), current_setting('app.current_owner_id', true))
) with check (
  owner_id = coalesce(current_setting('request.jwt.claim.sub', true), current_setting('app.current_owner_id', true))
);

create policy architecture_owner_policy on architecture
for all using (
  owner_id = coalesce(current_setting('request.jwt.claim.sub', true), current_setting('app.current_owner_id', true))
) with check (
  owner_id = coalesce(current_setting('request.jwt.claim.sub', true), current_setting('app.current_owner_id', true))
);

create policy decisions_owner_policy on decisions
for all using (
  owner_id = coalesce(current_setting('request.jwt.claim.sub', true), current_setting('app.current_owner_id', true))
) with check (
  owner_id = coalesce(current_setting('request.jwt.claim.sub', true), current_setting('app.current_owner_id', true))
);

create policy tasks_owner_policy on tasks
for all using (
  owner_id = coalesce(current_setting('request.jwt.claim.sub', true), current_setting('app.current_owner_id', true))
) with check (
  owner_id = coalesce(current_setting('request.jwt.claim.sub', true), current_setting('app.current_owner_id', true))
);

create policy preferences_owner_policy on preferences
for all using (
  owner_id = coalesce(current_setting('request.jwt.claim.sub', true), current_setting('app.current_owner_id', true))
) with check (
  owner_id = coalesce(current_setting('request.jwt.claim.sub', true), current_setting('app.current_owner_id', true))
);

create policy sessions_owner_policy on sessions
for all using (
  owner_id = coalesce(current_setting('request.jwt.claim.sub', true), current_setting('app.current_owner_id', true))
) with check (
  owner_id = coalesce(current_setting('request.jwt.claim.sub', true), current_setting('app.current_owner_id', true))
);

create policy warnings_owner_policy on warnings
for all using (
  owner_id = coalesce(current_setting('request.jwt.claim.sub', true), current_setting('app.current_owner_id', true))
) with check (
  owner_id = coalesce(current_setting('request.jwt.claim.sub', true), current_setting('app.current_owner_id', true))
);

create policy interface_logs_owner_policy on interface_logs
for all using (
  owner_id = coalesce(current_setting('request.jwt.claim.sub', true), current_setting('app.current_owner_id', true))
) with check (
  owner_id = coalesce(current_setting('request.jwt.claim.sub', true), current_setting('app.current_owner_id', true))
);

create policy session_state_owner_policy on session_state
for all using (
  owner_id = coalesce(current_setting('request.jwt.claim.sub', true), current_setting('app.current_owner_id', true))
) with check (
  owner_id = coalesce(current_setting('request.jwt.claim.sub', true), current_setting('app.current_owner_id', true))
);

create policy checkpoints_owner_policy on checkpoints
for all using (
  owner_id = coalesce(current_setting('request.jwt.claim.sub', true), current_setting('app.current_owner_id', true))
) with check (
  owner_id = coalesce(current_setting('request.jwt.claim.sub', true), current_setting('app.current_owner_id', true))
);

create policy file_memory_owner_policy on file_memory
for all using (
  owner_id = coalesce(current_setting('request.jwt.claim.sub', true), current_setting('app.current_owner_id', true))
) with check (
  owner_id = coalesce(current_setting('request.jwt.claim.sub', true), current_setting('app.current_owner_id', true))
);

create policy file_relations_owner_policy on file_relations
for all using (
  owner_id = coalesce(current_setting('request.jwt.claim.sub', true), current_setting('app.current_owner_id', true))
) with check (
  owner_id = coalesce(current_setting('request.jwt.claim.sub', true), current_setting('app.current_owner_id', true))
);

create policy prompt_patterns_owner_policy on prompt_patterns
for all using (
  owner_id = coalesce(current_setting('request.jwt.claim.sub', true), current_setting('app.current_owner_id', true))
) with check (
  owner_id = coalesce(current_setting('request.jwt.claim.sub', true), current_setting('app.current_owner_id', true))
);

create policy memory_documents_owner_policy on memory_documents
for all using (
  owner_id = coalesce(current_setting('request.jwt.claim.sub', true), current_setting('app.current_owner_id', true))
) with check (
  owner_id = coalesce(current_setting('request.jwt.claim.sub', true), current_setting('app.current_owner_id', true))
);

create policy timeline_events_owner_policy on timeline_events
for all using (
  owner_id = coalesce(current_setting('request.jwt.claim.sub', true), current_setting('app.current_owner_id', true))
) with check (
  owner_id = coalesce(current_setting('request.jwt.claim.sub', true), current_setting('app.current_owner_id', true))
);

create policy retention_policies_owner_policy on retention_policies
for all using (
  owner_id = coalesce(current_setting('request.jwt.claim.sub', true), current_setting('app.current_owner_id', true))
) with check (
  owner_id = coalesce(current_setting('request.jwt.claim.sub', true), current_setting('app.current_owner_id', true))
);

-- Semantic search helper using pgvector.
create or replace function match_memory_documents(
  query_embedding vector(1536),
  match_count integer,
  filter_project_id uuid,
  filter_owner_id text
)
returns table (
  id uuid,
  project_id uuid,
  owner_id text,
  source_type text,
  source_id text,
  title text,
  content text,
  keywords text[],
  metadata jsonb,
  similarity double precision
)
language sql
stable
as $$
  select
    memory_documents.id,
    memory_documents.project_id,
    memory_documents.owner_id,
    memory_documents.source_type,
    memory_documents.source_id,
    memory_documents.title,
    memory_documents.content,
    memory_documents.keywords,
    memory_documents.metadata,
    1 - (memory_documents.embedding <=> query_embedding) as similarity
  from memory_documents
  where memory_documents.embedding is not null
    and memory_documents.project_id = filter_project_id
    and memory_documents.owner_id = filter_owner_id
  order by memory_documents.embedding <=> query_embedding
  limit greatest(match_count, 1);
$$;

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
