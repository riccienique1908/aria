<<<<<<< HEAD
-- ═══════════════════════════════════════════════════════════════
-- ARIA v3 — Full Database Setup
-- Run this in Supabase → SQL Editor
-- This REPLACES everything from v1 and v2
-- ═══════════════════════════════════════════════════════════════

-- ── Clean up previous versions ────────────────────────────────
drop table if exists conversations cascade;
drop table if exists logs cascade;
drop table if exists user_profile cascade;

-- ═══════════════════════════════════════════════════════════════
-- USERS (extends Supabase Auth)
-- ═══════════════════════════════════════════════════════════════
create table public.profiles (
  id            uuid references auth.users(id) on delete cascade primary key,
  email         text,
  display_name  text,
  role          text default 'user',   -- 'admin' | 'user'
  -- Personal info ARIA uses in every conversation
  weight_kg         float,
  height_cm         float,
  daily_cal_goal    integer,
  daily_protein_g   integer,
  workouts_per_week integer,
  sleep_goal_hours  float,
  target_weight_kg  float,
  latest_goal       text,
  qa_stack          text,
  diet_preference   text,
  notes             text,
  created_at    timestamptz default now(),
  updated_at    timestamptz default now()
);
alter table public.profiles enable row level security;
create policy "Users see own profile"   on public.profiles for select using (auth.uid() = id);
create policy "Users update own profile" on public.profiles for update using (auth.uid() = id);
create policy "Users insert own profile" on public.profiles for insert with check (auth.uid() = id);
-- Admins can see all profiles
create policy "Admins see all profiles" on public.profiles for select
  using (exists (select 1 from public.profiles p where p.id = auth.uid() and p.role = 'admin'));

-- Auto-create profile on signup
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer as $$
begin
  insert into public.profiles (id, email, display_name, role)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data->>'display_name', split_part(new.email,'@',1)),
    -- First ever user becomes admin
    case when (select count(*) from public.profiles) = 0 then 'admin' else 'user' end
  );
  return new;
end;
$$;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ═══════════════════════════════════════════════════════════════
-- CONVERSATIONS (per-user memory)
-- ═══════════════════════════════════════════════════════════════
create table public.conversations (
  id           bigserial primary key,
  user_id      uuid references auth.users(id) on delete cascade not null,
=======
-- ARIA v2 — Supabase Database Setup
-- Run this in your Supabase SQL Editor (replaces the old setup)

-- Drop old tables if upgrading from v1
drop table if exists conversations;
drop table if exists logs;

-- ── Conversation history (long-term memory) ───────────────────────────────────
create table conversations (
  id           bigserial primary key,
>>>>>>> ec931570842916d24e0fc38106a5b9433412c439
  user_message text,
  ai_reply     text,
  module       text default 'general',
  created_at   timestamptz default now()
);
<<<<<<< HEAD
alter table public.conversations enable row level security;
create policy "Users see own conversations" on public.conversations
  for select using (auth.uid() = user_id);
create policy "Users insert own conversations" on public.conversations
  for insert with check (auth.uid() = user_id);
create index idx_conv_user_date on public.conversations (user_id, created_at desc);

-- ═══════════════════════════════════════════════════════════════
-- SKILLS
-- ═══════════════════════════════════════════════════════════════
create table public.skills (
  id            bigserial primary key,
  owner_id      uuid references auth.users(id) on delete cascade,  -- null = global
  name          text not null,
  description   text,
  icon          text default '🔧',
  -- What to inject into the AI's system prompt when this skill is active
  system_prompt text not null,
  -- Trigger keywords — if any appear in user message, skill auto-activates
  trigger_words text[] default '{}',
  -- Scope
  is_global     boolean default false,   -- admin-created, available to all users
  is_active     boolean default true,
  category      text default 'general',  -- work | health | home | productivity | custom
  use_count     integer default 0,
  created_at    timestamptz default now()
);
alter table public.skills enable row level security;
-- Users see their own skills AND global skills
create policy "Users see own + global skills" on public.skills
  for select using (owner_id = auth.uid() or is_global = true);
create policy "Users insert own skills" on public.skills
  for insert with check (auth.uid() = owner_id and is_global = false);
create policy "Users update own skills" on public.skills
  for update using (auth.uid() = owner_id and is_global = false);
create policy "Users delete own skills" on public.skills
  for delete using (auth.uid() = owner_id);
-- Admins can manage global skills
create policy "Admins manage global skills" on public.skills
  for all using (
    exists (select 1 from public.profiles p where p.id = auth.uid() and p.role = 'admin')
  );

-- ── User skill activations (which skills a user has enabled) ──
create table public.user_skills (
  user_id   uuid references auth.users(id) on delete cascade,
  skill_id  bigint references public.skills(id) on delete cascade,
  enabled   boolean default true,
  primary key (user_id, skill_id)
);
alter table public.user_skills enable row level security;
create policy "Users manage own skill activations" on public.user_skills
  for all using (auth.uid() = user_id);

-- ═══════════════════════════════════════════════════════════════
-- LOGS (health, food, etc. — per user)
-- ═══════════════════════════════════════════════════════════════
create table public.logs (
  id         bigserial primary key,
  user_id    uuid references auth.users(id) on delete cascade not null,
  type       text,
  data       jsonb,
  created_at timestamptz default now()
);
alter table public.logs enable row level security;
create policy "Users see own logs" on public.logs
  for select using (auth.uid() = user_id);
create policy "Users insert own logs" on public.logs
  for insert with check (auth.uid() = user_id);
create index idx_logs_user_type on public.logs (user_id, type, created_at desc);

-- ═══════════════════════════════════════════════════════════════
-- SEED: Built-in global skills (admin creates these)
-- Insert AFTER first user signs up (they become admin)
-- Or run manually once you've signed up
-- ═══════════════════════════════════════════════════════════════
-- You can run this block manually after signing up:
/*
insert into public.skills (owner_id, name, description, icon, system_prompt, trigger_words, is_global, category)
values
  (null, 'Daily Standup Helper', 'Formats updates for standups and syncs', '📋',
   'When helping with standups, ask: What did you do yesterday? What are you doing today? Any blockers? Then format it cleanly for Slack or Jira.',
   array['standup','yesterday','today','blocker','sync'], true, 'work'),

  (null, 'Bug Report Writer', 'Turns descriptions into proper bug reports', '🐛',
   'Format bug reports with: Summary, Steps to Reproduce, Expected Result, Actual Result, Severity (Critical/High/Medium/Low), and Environment. Be precise and technical.',
   array['bug','issue','broken','not working','error','crash'], true, 'work'),

  (null, 'Email Drafter', 'Writes professional emails', '✉️',
   'Draft clear, professional emails. Ask for: recipient context, tone (formal/casual), key points to include. Keep emails concise and action-oriented.',
   array['email','write to','draft','message to','reply to'], true, 'productivity'),

  (null, 'Meal Planner', 'Creates weekly meal plans and shopping lists', '🥗',
   'Create structured weekly meal plans with: breakfast, lunch, dinner, snacks. Include calorie estimates and a consolidated shopping list. Consider user dietary preferences.',
   array['meal plan','weekly food','prep','shopping list','grocery'], true, 'health'),

  (null, 'Code Reviewer', 'Reviews code for bugs, style, and best practices', '👨‍💻',
   'Review code thoroughly. Check for: bugs, security issues, performance problems, readability, test coverage gaps. Give specific actionable feedback with examples.',
   array['review','code','function','class','refactor','pr','pull request'], true, 'work'),

  (null, 'Meeting Notes', 'Summarises meetings and extracts action items', '📝',
   'Process meeting notes or transcripts. Extract: key decisions made, action items with owners, open questions, next steps. Format cleanly as bullet points.',
   array['meeting','notes','summary','minutes','discussed','action items'], true, 'work');
*/
=======

-- Index for fast recent-history queries
create index idx_conversations_created on conversations (created_at desc);

-- ── User profile (persistent facts about you) ─────────────────────────────────
create table user_profile (
  id              integer primary key default 1,  -- single row for one user
  name            text,
  weight_kg       float,
  height_cm       float,
  daily_cal_goal  integer,
  daily_protein_g integer,
  workouts_per_week integer,
  sleep_goal_hours float,
  target_weight_kg float,
  latest_goal     text,
  qa_stack        text,    -- e.g. "Playwright, TypeScript, Jira"
  diet_preference text,    -- e.g. "high protein, no dairy"
  notes           text,    -- any other facts
  updated_at      timestamptz default now()
);

-- Insert default empty profile
insert into user_profile (id) values (1) on conflict (id) do nothing;

-- ── Health & food logs ────────────────────────────────────────────────────────
create table logs (
  id         bigserial primary key,
  type       text,    -- meal | workout | sleep | weight | mood | task | habit
  data       jsonb,
  created_at timestamptz default now()
);

create index idx_logs_type_date on logs (type, created_at desc);
>>>>>>> ec931570842916d24e0fc38106a5b9433412c439
