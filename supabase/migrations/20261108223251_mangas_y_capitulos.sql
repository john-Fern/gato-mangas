-- Mangas propios que guarda scraper-manga (github.com/john-Fern/scraper-manga).
-- Las imágenes no se guardan: image_urls apunta al sitio de origen.
-- El scraper escribe con la service key; la lectura es pública.
create table public.mangas (
  id text primary key,
  source text not null,
  title text not null,
  type text,
  url text not null,
  created_at timestamptz not null default now()
);

create table public.chapters (
  manga_id text not null references public.mangas(id) on delete cascade,
  number numeric not null,
  title text,
  source_url text not null,
  image_urls text[] not null,
  created_at timestamptz not null default now(),
  primary key (manga_id, number)
);

alter table public.mangas enable row level security;
alter table public.chapters enable row level security;

create policy "lectura publica" on public.mangas for select using (true);
create policy "lectura publica" on public.chapters for select using (true);
