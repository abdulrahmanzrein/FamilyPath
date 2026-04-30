# MedBridge (FamilyPath)

Voice-first family-doctor finder for newcomers in Canada. Five agents fan out across clinic directories, place a real outbound call to confirm acceptance, and report back through a live React dashboard.

Spec: [`prd.md`](prd.md).

## Stack

- **Backend** — FastAPI + SQLAlchemy (async) + Postgres, WebSocket hub, ElevenLabs outbound calls.
- **Frontend** — Vite + React + TypeScript + Tailwind.
- **LLM** — Claude (via nexos.ai gateway) and OpenAI for the navigator chatbot.

## Layout

```
backend/
  app/
    main.py            FastAPI entry
    config.py          .env-backed settings
    api/               searches, providers, voice (interrupt + post-call), navigator
    agents/            fake_runner, voice_caller, call_state, llm_gateway
    db/                models, session, base
    schemas/           pydantic request/response shapes
    ws/                WebSocket hub
  scripts/seed_odhf.py ODHF seed loader
  tests/
frontend/
  src/
    App.tsx            onboarding form + live dashboard
    api/client.ts      backend client
    hooks/             useSearchWebSocket
    components/        AgentGrid, ClinicMap, ui/
    voice/             ElevenLabs session
docker-compose.yml     postgres
.github/workflows/     nightly scrape
```

## Run it

```bash
# 1. postgres
docker compose up -d postgres

# 2. backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in keys
uvicorn app.main:app --reload   # http://localhost:8000

# 3. frontend (new terminal)
cd frontend
npm install
npm run dev   # http://localhost:5173
```

## Branches

`main` is the demo branch. Feature work goes on `frontend/main` or `backend/agents` and merges via PR.
