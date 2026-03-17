do $$
begin
  if exists (
    select 1
    from pg_available_extensions
    where name = 'timescaledb'
  ) then
    create extension if not exists timescaledb;
  else
    raise notice 'timescaledb extension not available; continuing with regular Postgres table.';
  end if;
end
$$;

create table if not exists users (
  id uuid primary key default gen_random_uuid(),
  email text unique not null,
  created_at timestamptz not null default now()
);

create table if not exists health_profiles (
  user_id uuid primary key references users(id) on delete cascade,
  conditions text[] not null default '{}',
  age int not null check (age between 5 and 120),
  location_lat double precision not null,
  location_lng double precision not null,
  medications text[] not null default '{}',
  updated_at timestamptz not null default now()
);

create table if not exists environmental_readings (
  time timestamptz not null,
  location_lat double precision not null,
  location_lng double precision not null,
  aqi double precision,
  pm25 double precision,
  pm10 double precision,
  o3 double precision,
  no2 double precision,
  temperature double precision,
  humidity double precision,
  uv_index double precision,
  tree_pollen double precision,
  grass_pollen double precision,
  weed_pollen double precision,
  wind_speed double precision
);

do $$
begin
  if exists (
    select 1
    from pg_extension
    where extname = 'timescaledb'
  ) then
    perform create_hypertable('environmental_readings', 'time', if_not_exists => true);
  else
    raise notice 'Skipping create_hypertable() because timescaledb is not installed.';
  end if;
end
$$;

create table if not exists risk_scores (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  timestamp timestamptz not null default now(),
  risk_score double precision not null,
  risk_category text not null,
  component_scores jsonb not null default '{}'::jsonb,
  explanation text not null default '',
  anomaly_flag boolean not null default false
);

create table if not exists alerts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null unique references users(id) on delete cascade,
  threshold int not null check (threshold between 0 and 100),
  push_token text,
  phone text,
  email text,
  active boolean not null default true
);

create table if not exists community_reports (
  id uuid primary key default gen_random_uuid(),
  timestamp timestamptz not null default now(),
  location_lat double precision not null,
  location_lng double precision not null,
  symptoms text[] not null default '{}',
  severity text not null
);

create index if not exists idx_risk_scores_user_time on risk_scores(user_id, timestamp desc);
create index if not exists idx_community_reports_time on community_reports(timestamp desc);
