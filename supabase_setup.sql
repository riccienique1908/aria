-- ARIA v2 — Supabase Database Setup
-- Run this in your Supabase SQL Editor (replaces the old setup)

-- Drop old tables if upgrading from v1
drop table if exists conversations;
drop table if exists logs;

-- ── Conversation history (long-term memory) ───────────────────────────────────
create table conversations (
  id           bigserial primary key,
  user_message text,
  ai_reply     text,
  module       text default 'general',
  created_at   timestamptz default now()
);

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
