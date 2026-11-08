# Plan — Manga Reader

Lector web de mangas, manhwas y manhuas que consume la API pública de **MangaDex**.

## Stack

| Capa | Tecnología |
|------|------------|
| Frontend | Vite + React + TypeScript, React Router, `@supabase/supabase-js` (login) |
| Backend | FastAPI (Python 3.12+), `httpx` (cliente MangaDex), `psycopg` (PostgreSQL) |
| Base de datos | PostgreSQL alojado en Supabase (migraciones SQL en `supabase/migrations`) |
| Auth | Supabase Auth (email + contraseña). El backend valida el token contra `/auth/v1/user` |
| Tests | `pytest` (backend), `vitest` + Testing Library (frontend) |
| CI/CD | GitHub Actions: lint + tests + build en cada push/PR; deploy en `main` |

## Arquitectura

```
navegador ──► frontend (Vite, GitHub Pages)
                 │  fetch /api/*
                 ▼
             backend FastAPI ──► api.mangadex.org  (catálogo, capítulos, páginas)
                 │            └► uploads.mangadex.org (proxy de imágenes)
                 ▼
             PostgreSQL (Supabase): favoritos e historial de lectura por usuario
```

El backend actúa de fachada: normaliza las respuestas de MangaDex a un formato simple
y hace de proxy de imágenes (MangaDex no permite hotlinking de portadas).

## Prácticas XP aplicadas

- **Historias de usuario** pequeñas (abajo) y **entregas pequeñas**: cada historia es un commit funcional.
- **TDD**: primero el test, luego el código mínimo, luego refactor.
- **Diseño simple / YAGNI**: sin capas ni abstracciones que no pida una historia.
- **Integración continua**: cada push corre lint + tests + build en GitHub Actions.
- **Estándares de código**: `ruff` (Python), `eslint` + `tsc` (TypeScript).
- **Refactorización continua** con los tests como red de seguridad.

## Historias de usuario (iteración 1)

1. Como lector quiero **ver mangas populares** en la portada.
2. Como lector quiero **buscar** mangas/manhwas por título.
3. Como lector quiero **ver el detalle** de un manga (portada, sinopsis, capítulos).
4. Como lector quiero **leer un capítulo** (páginas en scroll vertical, siguiente/anterior).
5. Como lector quiero **filtrar por idioma** de los capítulos (es / en).
6. Como usuario registrado quiero **guardar favoritos**.
7. Como usuario registrado quiero que se **recuerde el último capítulo leído**.

## Tareas

1. Estructura del monorepo, configuración de linters y tests.
2. Backend: cliente MangaDex + endpoints `/api/manga`, `/api/manga/{id}`, `/api/manga/{id}/chapters`, `/api/chapters/{id}/pages`, `/api/image` (TDD con `httpx.MockTransport`).
3. Base de datos: migración SQL (`favorites`, `reading_progress`) + endpoints autenticados `/api/me/favorites`, `/api/me/progress` (tests contra PostgreSQL real).
4. Frontend: páginas Inicio/Búsqueda, Detalle, Lector, Favoritos, Login (tests con vitest).
5. Docker Compose para desarrollo local (Postgres + backend + frontend).
6. CI (GitHub Actions) y CD (frontend a GitHub Pages, migraciones a Supabase, backend vía Render deploy hook). Los pasos de deploy se saltan si no hay secretos configurados.
7. Ejecutar todos los tests y subir a GitHub.

## Definición de terminado

Una tarea está terminada cuando: lint OK, todos los tests pasan y el build funciona.
