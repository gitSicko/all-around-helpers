-- ALL AROUND HELPER - Supabase schema
-- Jalankan seluruh file ini di Supabase > SQL Editor.

create extension if not exists pgcrypto;

create table if not exists public.couples (
  id uuid primary key default gen_random_uuid(),
  join_code text unique not null,
  created_by uuid not null references auth.users(id) on delete cascade,
  created_at timestamptz not null default now()
);

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  couple_id uuid references public.couples(id) on delete set null,
  created_at timestamptz not null default now()
);

create table if not exists public.events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  couple_id uuid references public.couples(id) on delete cascade,
  title text not null,
  start_at timestamp not null,
  end_at timestamp not null,
  category text,
  notes text,
  scope text not null default 'private' check (scope in ('private','couple')),
  created_at timestamptz not null default now()
);

create table if not exists public.tasks (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  title text not null,
  task_date date not null default current_date,
  is_done boolean not null default false,
  created_at timestamptz not null default now()
);

create table if not exists public.transactions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  type text not null check (type in ('income','expense')),
  amount numeric(14,2) not null check (amount > 0),
  category text,
  description text,
  occurred_on date not null default current_date,
  created_at timestamptz not null default now()
);

create table if not exists public.deadlines (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  title text not null,
  course text,
  due_date date not null,
  priority text not null default 'Medium' check (priority in ('High','Medium','Low')),
  progress int not null default 0 check (progress between 0 and 100),
  notes text,
  is_done boolean not null default false,
  created_at timestamptz not null default now()
);

create table if not exists public.notes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  title text not null,
  content text,
  category text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Profile otomatis saat signup
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.profiles (id, display_name)
  values (new.id, coalesce(new.raw_user_meta_data->>'display_name', split_part(new.email, '@', 1)))
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row execute procedure public.handle_new_user();

-- Couple helper RPCs
create or replace function public.create_couple()
returns text
language plpgsql
security definer set search_path = public
as $$
declare
  uid uuid := auth.uid();
  cid uuid;
  code text;
begin
  if uid is null then raise exception 'Not authenticated'; end if;
  if exists(select 1 from profiles where id = uid and couple_id is not null) then
    raise exception 'Already in a couple';
  end if;
  loop
    code := upper(substr(encode(gen_random_bytes(6), 'hex'), 1, 8));
    exit when not exists(select 1 from couples where join_code = code);
  end loop;
  insert into couples(join_code, created_by) values(code, uid) returning id into cid;
  update profiles set couple_id = cid where id = uid;
  return code;
end;
$$;

create or replace function public.join_couple(p_code text)
returns void
language plpgsql
security definer set search_path = public
as $$
declare
  uid uuid := auth.uid();
  cid uuid;
  members int;
begin
  if uid is null then raise exception 'Not authenticated'; end if;
  if exists(select 1 from profiles where id = uid and couple_id is not null) then
    raise exception 'Already in a couple';
  end if;
  select id into cid from couples where join_code = upper(trim(p_code));
  if cid is null then raise exception 'Invalid code'; end if;
  select count(*) into members from profiles where couple_id = cid;
  if members >= 2 then raise exception 'Couple space is full'; end if;
  update profiles set couple_id = cid where id = uid;
end;
$$;

-- Helper ini menghindari policy profiles mereferensikan dirinya sendiri (RLS recursion).
create or replace function public.current_couple_id()
returns uuid
language sql
stable
security definer set search_path = public
as $$
  select couple_id from public.profiles where id = auth.uid();
$$;
revoke all on function public.current_couple_id() from public;
grant execute on function public.current_couple_id() to authenticated;

-- RLS
alter table public.couples enable row level security;
alter table public.profiles enable row level security;
alter table public.events enable row level security;
alter table public.tasks enable row level security;
alter table public.transactions enable row level security;
alter table public.deadlines enable row level security;
alter table public.notes enable row level security;

-- profiles: lihat profil sendiri + pasangan
create policy "profiles select own or partner" on public.profiles
for select using (
  id = auth.uid() or
  (couple_id is not null and couple_id = public.current_couple_id())
);
create policy "profiles update own" on public.profiles for update using (id = auth.uid()) with check (id = auth.uid());

-- couples: hanya member
create policy "couples select member" on public.couples
for select using (id = public.current_couple_id());

-- events: private milik sendiri atau couple yang sama
create policy "events select" on public.events for select using (
  (scope = 'private' and user_id = auth.uid()) or
  (scope = 'couple' and couple_id is not null and couple_id = public.current_couple_id())
);
create policy "events insert" on public.events for insert with check (
  (scope = 'private' and user_id = auth.uid()) or
  (scope = 'couple' and user_id = auth.uid() and couple_id = public.current_couple_id())
);
create policy "events update" on public.events for update using (
  user_id = auth.uid() or (scope='couple' and couple_id = public.current_couple_id())
);
create policy "events delete" on public.events for delete using (
  user_id = auth.uid() or (scope='couple' and couple_id = public.current_couple_id())
);

-- private tables
create policy "tasks own" on public.tasks for all using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy "transactions own" on public.transactions for all using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy "deadlines own" on public.deadlines for all using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy "notes own" on public.notes for all using (user_id = auth.uid()) with check (user_id = auth.uid());

-- permissions for RPCs
revoke all on function public.create_couple() from public;
revoke all on function public.join_couple(text) from public;
grant execute on function public.create_couple() to authenticated;
grant execute on function public.join_couple(text) to authenticated;
