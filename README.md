# 🐱 Gato Mangas

Lector web de mangas, manhwas y manhuas. Los datos vienen de la API pública de
[MangaDex](https://api.mangadex.org/docs/). Ver [PLAN.md](PLAN.md) para el plan, la arquitectura y las historias de usuario.

- **Frontend**: Vite + React + TypeScript (`frontend/`)
- **Backend**: FastAPI (`backend/`) — fachada de MangaDex + proxy de imágenes + favoritos/progreso
- **Base de datos**: PostgreSQL en Supabase (`supabase/migrations/`)
- **Auth**: Supabase Auth (email + contraseña)

## Desarrollo local

Requisitos: Node 22, [uv](https://docs.astral.sh/uv/), Docker.

```bash
cp backend/.env.example backend/.env   # rellena SUPABASE_URL y SUPABASE_ANON_KEY
docker compose up -d db                # Postgres con la migración aplicada
cd backend && uv sync && uv run uvicorn app.main:app --reload
```

```bash
cd frontend && cp .env.example .env.local && npm install && npm run dev
```

Abre http://localhost:5173. Sin variables de Supabase la app funciona igual, pero sin login/favoritos.

## Tests

```bash
cd backend && uv run ruff check . && uv run pytest     # necesita Postgres (TEST_DATABASE_URL)
cd frontend && npm run lint && npm test && npm run build
```

## CI/CD (GitHub Actions — `.github/workflows/ci.yml`)

En cada push y PR: lint + tests del backend (con Postgres real) y del frontend + build.
En `main`, si todo pasa:

| Job | Qué hace | Configuración necesaria |
|-----|----------|-------------------------|
| `deploy-frontend` | Publica `frontend/dist` en GitHub Pages | Settings → Pages → Source: *GitHub Actions*. Variables: `VITE_API_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` |
| `deploy-database` | `supabase db push` de las migraciones | Secrets: `SUPABASE_ACCESS_TOKEN`, `SUPABASE_DB_PASSWORD`. Variable: `SUPABASE_PROJECT_REF` |
| `deploy-backend` | Dispara el deploy en Render con un deploy hook | Secret: `RENDER_DEPLOY_HOOK` (opcional) |

Los jobs de deploy se saltan (con un aviso) si falta su configuración.

**Backend en Render:** la forma recomendada es activar en el servicio *Settings → Auto-Deploy → After CI Checks Pass*.
Así Render despliega cada push a `main` solo cuando este workflow pasa, sin necesitar `RENDER_DEPLOY_HOOK`.
Con *Root Directory* = `backend`, Render solo redespliega si el push cambia archivos de `backend/`; para forzarlo usa *Manual Deploy*.
Recuerda poner la URL de GitHub Pages en `CORS_ORIGINS` del backend.

## Forma de trabajo (XP)

Historias pequeñas, TDD (test primero), diseño simple, integración continua y refactor con
la red de tests. Una tarea está terminada cuando lint, tests y build pasan.
