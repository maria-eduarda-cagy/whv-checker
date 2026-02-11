create extension if not exists pgcrypto;

create table if not exists public.country_last_state (
  country text primary key,
  status text not null check (status in ('open','paused','closed')),
  last_checked_at timestamptz not null default now(),
  last_notified_status text null check (last_notified_status in ('open','paused','closed'))
);

create table if not exists public.status_checks (
  id uuid primary key default gen_random_uuid(),
  country text not null,
  status text null check (status in ('open','paused','closed')),
  checked_at timestamptz not null default now(),
  source_url text not null,
  raw_excerpt text null,
  error text null
);

create index if not exists status_checks_country_checked_at_idx
  on public.status_checks (country, checked_at desc);

create table if not exists public.notifications (
  id uuid primary key default gen_random_uuid(),
  country text not null,
  status text not null check (status in ('open','paused','closed')),
  sent_at timestamptz not null default now(),
  recipient text not null,
  provider text not null,
  provider_message_id text null
);

create index if not exists notifications_country_sent_at_idx
  on public.notifications (country, sent_at desc);
