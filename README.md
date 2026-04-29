# MedBridge (FamilyPath)

Voice-assisted family doctor discovery for newcomers in Canada. This repository contains the **MedBridge** hackathon project layout; **product requirements and scope** live in [`prd.md`](prd.md).

## Current status

The repo is a **skeleton only**: directory and file placeholders are present; **application code is not implemented yet** (empty `backend/`, `frontend/`, and config stubs). Use `prd.md` as the build spec when you fill in each layer.

## Repository layout

| Area | Path | Intended owner |
|------|------|----------------|
| Product spec | `prd.md` | Whole team |
| Backend API, DB, agents, WebSocket | `backend/app/` | Person 1 (backend / agents) |
| ODHF seed script | `backend/scripts/seed_odfh.py` | Person 1 |
| Frontend (Vite + React) | `frontend/` | Person 2 (UI / voice) |
| PostgreSQL (to be defined) | `docker-compose.yml` | Person 1 |
| Nightly job placeholder | `.github/workflows/nightly-scrape.yml` | Person 1 |

### Backend (`backend/app/`)

- `main.py` — FastAPI entry (not yet implemented).
- `api/` — HTTP routes: searches, providers, voice interrupt.
- `db/` — SQLAlchemy models and session.
- `schemas/` — Request/response models.
- `ws/` — WebSocket broadcasting for live search updates.
- `agents/` — LangGraph supervisor, workers, LLM gateway (nexos / Anthropic per PRD).

### Frontend (`frontend/`)

- Vite + TypeScript layout: `App`, API client, WebSocket hook, agent grid, ElevenLabs integration stub.

## Getting started (after implementation)

These steps will apply once code and dependencies exist; they are **placeholders** for now.

1. Copy `backend/.env.example` to `backend/.env` and set API keys per `prd.md`.
2. Start PostgreSQL (define `docker-compose.yml` or use a managed DB); set `DATABASE_URL` accordingly.
3. Install backend: `cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
4. Install frontend: `cd frontend && npm install`
5. Run services as documented in your future `main.py` / `package.json` scripts.

## Branches

Work is expected on feature branches (for example `backend/agents`). Merge to `main` via pull request when review is complete.

## License / demo

See `prd.md` for sponsor integrations, demo flow, and constraints (PII handling, data sources, and voice limitations).
