-- Favoritos y progreso de lectura por usuario (user_id = auth.users.id de Supabase)
create table if not exists favorites (
    user_id    uuid        not null,
    manga_id   text        not null,
    title      text        not null,
    cover_url  text,
    created_at timestamptz not null default now(),
    primary key (user_id, manga_id)
);

create table if not exists reading_progress (
    user_id        uuid        not null,
    manga_id       text        not null,
    chapter_id     text        not null,
    chapter_number text,
    updated_at     timestamptz not null default now(),
    primary key (user_id, manga_id)
);

-- Solo el backend (rol postgres) accede a estas tablas; sin políticas, la API pública de Supabase no las expone.
alter table favorites enable row level security;
alter table reading_progress enable row level security;
