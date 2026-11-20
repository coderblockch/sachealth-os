# 🏥 SacHealth OS — Clinical Triage & Bed Management

[![CI](https://github.com/coderblockch/sachealth-os/actions/workflows/ci.yml/badge.svg)](https://github.com/coderblockch/sachealth-os/actions/workflows/ci.yml)
[![CodeQL](https://github.com/coderblockch/sachealth-os/actions/workflows/codeql.yml/badge.svg)](https://github.com/coderblockch/sachealth-os/actions/workflows/codeql.yml)
![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-SQLModel-009688)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**The problem:** crowded emergency departments lose time deciding which patient is most critical and which bed is actually free.
**The solution:** one dashboard that triages patients with transparent, rule-based logic, keeps each patient's triage history, and shows live bed status from a REST API backed by PostgreSQL.

🔗 **Live demo:** [sachealth-os.onrender.com](https://sachealth-os.onrender.com) · **API docs:** [/docs](https://sachealth-os.onrender.com/docs)
**Demo login** (public demo account, fake data only): `demo@sachealth.dev` / `sachealth-demo`

> Free Render tier: the first request after ~15 min idle can take up to a minute. All demo data is fake and seeded automatically.

---

## 📸 Screenshots

### React app (`/app`)

| Dashboard: stats cards + charts | Triage form + filterable history |
|---|---|
| ![React dashboard](docs/screenshots/react-dashboard.png) | ![React triage](docs/screenshots/react-triage.png) |

| Beds board: assign / discharge | Patients: search + pagination |
|---|---|
| ![React beds board](docs/screenshots/react-beds.png) | ![React patients](docs/screenshots/react-patients.png) |

| Patient detail with triage timeline | Login | Mobile |
|---|---|---|
| ![React patient detail](docs/screenshots/react-patient-detail.png) | ![React login](docs/screenshots/react-login.png) | ![React mobile dashboard](docs/screenshots/react-mobile-dashboard.png) |

### Classic dashboard (`/classic`) and API docs

| Dashboard: triage + bed status | Signed in as staff: beds can be updated |
|---|---|
| ![SacHealth OS dashboard](docs/screenshot.png) | ![Staff view with bed editing](docs/screenshot-staff.png) |

| Auto-generated API docs (FastAPI / OpenAPI) |
|---|
| ![Swagger API docs](docs/screenshot-api-docs.png) |

### 🎬 Demo (2 min)

[![SacHealth OS demo: triage, staff login, bed assignment and API docs](docs/sachealth-demo.gif)](docs/sachealth-demo.mp4)

▶️ **[Watch the full 2-minute video (MP4)](docs/sachealth-demo.mp4)**: rule-based triage, staff sign-in, assigning a bed, and the OpenAPI docs (`/stats`, filtered `/beds`), recorded on the live Render deployment backed by PostgreSQL.

---

## 🌟 Features

- **Clinical Decision Support (CDSS):** rule-based triage that assigns a priority (1 Critical → 4 Low) from age, O₂ saturation and symptoms. Deterministic and auditable.
- **Bed management dashboard:** color-coded bed cards (Available, Occupied, Pending Discharge, Cleaning) loaded from the API.
- **Staff authentication:** bcrypt-hashed passwords and short-lived JWT bearer tokens; write endpoints require a token.
- **REST API + SQL database:** FastAPI with Pydantic validation and SQLModel (SQLAlchemy) persistence. SQLite by default, PostgreSQL via `DATABASE_URL`.
- **Resilient UI:** live SYSTEM ONLINE / BACKEND OFFLINE badge and friendly error messages when the API is down.
- **Patients & triage history:** stored triage results, patient search, filtering and pagination, transactional bed assignment.
- **React + TypeScript app:** typed API client, JWT auth context with protected routes, TanStack Query caching, validated accessible forms, responsive layout (see the Frontend section below).
- **Tested and automated:** 38 Vitest/React Testing Library tests for the frontend and 83 pytest tests for the API (migration tests also run on PostgreSQL in CI), GitHub Actions CI and CodeQL on every push and pull request.

## 🛠️ Tech Stack

| Layer | Technologies |
|-------|--------------|
| Frontend | React 18, TypeScript, Vite, React Router, TanStack Query, React Hook Form + Zod, Tailwind CSS (classic page: vanilla JS) |
| Backend | Python, FastAPI, Pydantic, Uvicorn, PyJWT, bcrypt |
| Database | PostgreSQL (`psycopg`) · SQLite for local dev/tests · SQLModel / SQLAlchemy ORM · Alembic migrations |
| Testing & CI | pytest, FastAPI TestClient, Vitest, React Testing Library, ESLint, GitHub Actions, CodeQL |
| Hosting | Render (`render.yaml` Blueprint) |

---

## 🏗️ Architecture

```
Browser
  ├─ /app/*  ──────────────► FastAPI serves the React build (frontend/dist), SPA fallback to index.html
  ├─ /classic, /docs ──────► original vanilla-JS dashboard, OpenAPI docs
  └─ fetch + JWT Bearer ───► REST API (/auth /beds /patients /triage /stats)
                                   │
                                   ▼
                     SQLModel / SQLAlchemy ──► PostgreSQL (Render) | SQLite (local)
                                   ▲
                     Alembic migrations (run on startup)

Inside the React app:
  pages ─► TanStack Query hooks (cache + invalidation) ─► typed API client (fetch, JWT, ApiError)
  AuthContext (token in localStorage, verified with /auth/me) · RequireAuth route guard
```

One web service serves both the UI and the API (same origin, so no CORS in production). `/` redirects to the React app at `/app/` when it has been built. The app lives under `/app` so its routes (`/app/beds`, `/app/patients/3`) never collide with API paths (`/beds`, `/patients/3`). Full interactive docs at `/docs`.

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /health` | — | Liveness probe |
| `POST /auth/login` · `GET /auth/me` | — · Bearer | JWT login, current user |
| `GET /beds?status=` · `GET /beds/{id}` | — | Beds ordered by number, optional status filter |
| `POST /beds` | Bearer | Create a bed (409 if the number exists) |
| `PATCH /beds/{id}` | Bearer | Update status and/or patient name |
| `POST /beds/{id}/assign` | Bearer | Put a registered patient in an Available bed (row lock, atomic) |
| `POST /beds/{id}/discharge` | Bearer | Release a bed → `Cleaning` |
| `POST /patients` · `GET /patients?q=&limit=&offset=` | Bearer | Register / search patients (paginated) |
| `GET /patients/{id}` · `DELETE /patients/{id}` | Bearer | Patient with current bed + triage history / delete (cascades) |
| `POST /triage/analyze` | — | Stateless CDSS evaluation (used by the dashboard) |
| `POST /triage` | Bearer | Evaluate **and store**; can register a new patient in the same transaction |
| `GET /triage?priority=&patient_id=&since=&limit=&offset=` | Bearer | Triage history, newest first, filtered and paginated |
| `GET /stats` | — | Beds by status and triage records by priority |

### 🗄️ Data model

```
user ──< triage_record >── patient ──○ bed
 (created_by, SET NULL)   (CASCADE)   (patient_id UNIQUE, SET NULL)
```

| Table | Columns | Constraints & indexes |
|-------|---------|-----------------------|
| `bed` | `id`, `num`, `status`, `patient` (display name), `patient_id`, `updated_at` | `num` unique index · `status` CHECK (4 values) + index · `patient_id` FK → `patient` ON DELETE SET NULL, UNIQUE (one bed per patient) |
| `patient` | `id`, `full_name`, `age`, `created_at` | `age` CHECK 0–130 · index on `full_name` |
| `triage_record` | `id`, `patient_id`, `age`, `oxygen_level`, `symptoms`, `priority`, `recommendation`, `urgency`, `created_by_id`, `created_at` | FK → `patient` ON DELETE CASCADE · FK → `user` ON DELETE SET NULL · CHECKs on priority 1–4, O₂ 0–100, age · composite indexes `(patient_id, created_at)` and `(priority, created_at)` |
| `user` | `id`, `email`, `full_name`, `hashed_password` | `email` unique index (bcrypt hashes only) |

- **Migrations:** the schema is versioned with Alembic (`backend/migrations`): `0001` = original tables, `0002` = patients, triage history, constraints and indexes. CI checks that the migrations match `models.py` on both SQLite and PostgreSQL.
- **Transactions:** registering a patient and saving their triage happen in one transaction; bed assignment takes a row lock (`SELECT … FOR UPDATE` on PostgreSQL) and is protected by the unique `patient_id` constraint against double-booking.
- **Integrity in the database, not just the API:** CHECK, UNIQUE and FOREIGN KEY constraints (SQLite foreign keys are enabled with `PRAGMA foreign_keys=ON`).
- **Connections:** one `Session` per request, `pool_pre_ping`, configurable pool size; `postgres://` URLs are normalized to `postgresql+psycopg://`.

### 🧠 Triage rules (`POST /triage/analyze`)

| Condition (evaluated in order) | Priority | Recommendation |
|-----------|----------|----------------|
| O₂ saturation < 90% or "chest pain" | **1 — Critical** | ICU (Immediate) |
| Age > 70 with "cough" | **2 — High** | Respiratory Unit |
| "fever" or "headache" | **3 — Moderate** | Urgent Care / Clinic |
| None of the above | **4 — Low** | Outpatient Clinic |

---

## ⚙️ Run Locally

```bash
git clone https://github.com/coderblockch/sachealth-os.git
cd sachealth-os/backend
python3 -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
# Dashboard: http://127.0.0.1:8000  ·  API docs: http://127.0.0.1:8000/docs
```

By default this uses a local SQLite file and creates the tables on startup. To work like production (PostgreSQL + Alembic):

```bash
export DATABASE_URL=postgresql://user:password@localhost:5432/sachealth
export DB_AUTO_CREATE=false
alembic upgrade head      # create/upgrade the schema
python seed.py            # demo beds, staff user, patients and triage history (idempotent)
uvicorn main:app --reload
```

> Already have a `sachealth.db` from an older version? Run `alembic stamp 0001 && alembic upgrade head`, or just delete the file.

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `sqlite:///sachealth.db` | Any SQLAlchemy URL; `postgres://…` URLs are accepted |
| `DB_AUTO_CREATE` | `true` | Create tables on startup (set `false` when using Alembic) |
| `DB_RUN_MIGRATIONS` | `false` | Run `alembic upgrade head` on startup (used on Render) |
| `SEED_DEMO_DATA` | `true` | Seed demo beds + staff user on startup |
| `SEED_DEMO_PATIENTS` | `false` | Also seed demo patients + triage history on startup |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` | `5` / `5` | PostgreSQL connection pool |
| `JWT_SECRET` | random per process | Token signing secret (set in production) |
| `ACCESS_TOKEN_MINUTES` | `60` | Token lifetime |
| `DEMO_USER_EMAIL` / `DEMO_USER_PASSWORD` | demo account | Seeded staff account |
| `ALLOWED_ORIGINS` | local dev servers | CORS allow-list (comma-separated) |

## ⚛️ Frontend (React + TypeScript)

The React app in [`frontend/`](frontend) consumes the same API. The design decisions are explained in plain English in [`docs/FRONTEND_WALKTHROUGH.md`](docs/FRONTEND_WALKTHROUGH.md).

| Page | What it does | API |
|------|--------------|-----|
| Login | Validated form, stores the JWT, returns you to the page you wanted | `POST /auth/login`, `GET /auth/me` |
| Dashboard | Stat cards and bar charts | `GET /stats` |
| Triage | Rules-based triage for a new or existing patient, plus paginated history with a priority filter kept in the URL | `POST /triage`, `GET /triage` |
| Patients | Debounced search, pagination, register a patient, detail page with triage timeline and current bed | `GET/POST /patients`, `GET /patients/{id}` |
| Beds | Status grid with filters, assign a patient (searchable picker), discharge | `GET /beds`, `POST /beds/{id}/assign` and `/discharge` |

```bash
# terminal 1: API
cd backend && uvicorn main:app --reload           # http://127.0.0.1:8000
# terminal 2: React dev server (proxies API calls to :8000)
cd frontend && npm install && npm run dev          # http://localhost:5173/app/
```

```bash
cd frontend
npm run lint        # ESLint (0 warnings allowed)
npm run typecheck   # tsc, strict mode
npm test            # Vitest + React Testing Library (38 tests)
npm run build       # production build into frontend/dist, served by FastAPI at /app
```

```
frontend/src/
├── api/          # types.ts (mirrors the API), client.ts (fetch + JWT + errors), endpoints.ts, hooks.ts (TanStack Query)
├── auth/         # AuthContext (login/logout, /auth/me), RequireAuth route guard, tokenStorage
├── components/   # Layout, TriageForm, TriageHistory, BedCard, PatientPicker, BarChart, Pagination, FormField, badges, loading/error/empty states
├── pages/        # Login, Dashboard, Triage, Patients, PatientDetail, Beds, NotFound
├── lib/          # form schemas (Zod), formatting, query client, useDebouncedValue
└── __tests__/    # component tests (+ *.test.ts next to the code they test)
```

## 🧪 Run Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest            # API, auth, triage, CRUD, constraints, migrations and seed
# optional: also run the migration tests against PostgreSQL
TEST_POSTGRES_URL=postgresql://postgres:postgres@localhost:5432/sachealth_test pytest tests/test_migrations.py
```

API tests run against an isolated in-memory SQLite database. [GitHub Actions](https://github.com/coderblockch/sachealth-os/actions/workflows/ci.yml) runs the API suite, the frontend job (lint, typecheck, tests, build) and a PostgreSQL 17 job (migrations up/down, model/migration drift check, idempotent seed) on every push and pull request.

## ☁️ Deployment (Render)

[`render.yaml`](render.yaml) defines a Render PostgreSQL database (`sachealth-db`) and the web service. The build command installs the API and builds the React app: `pip install -r backend/requirements.txt && cd frontend && npm ci && npm run build`. `DATABASE_URL` comes from the database's internal connection string. With `DB_RUN_MIGRATIONS=true` the app runs `alembic upgrade head` on startup and then seeds the demo data (idempotent), because Render's free plan has no pre-deploy command. Pushes to `main` redeploy automatically.

---

## 🗺️ Roadmap

- [x] Frontend connected to the FastAPI backend
- [x] Bed data persisted in a SQL database (SQLModel)
- [x] JWT authentication for clinical staff
- [x] Full stack deployed to Render
- [x] Save triaged patients and assign them to beds (`patient` / `triage_record` tables with foreign keys)
- [ ] Role-based permissions (nurse vs. admin)
- [x] PostgreSQL support with Alembic migrations
- [x] Show triage history and bed assignment in the UI (React app)

## 👤 Author

**David Jimenez** — Full-Stack Developer in training · Sacramento, CA
[GitHub @coderblockch](https://github.com/coderblockch) · [Portfolio](https://portfolio-bay-nine-59.vercel.app)

## 📄 License

MIT — see [`LICENSE`](LICENSE).

> ⚠️ Educational prototype. **Not** intended for real clinical use or patient care decisions.
