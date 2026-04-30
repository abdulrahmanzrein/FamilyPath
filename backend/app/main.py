# FastAPI app entry point — what `uvicorn app.main:app` actually serves.
# Responsibilities for this slice:
#   1. Create the DB tables on startup (no Alembic — PRD §Database opts out)
#   2. Allow the React dev server to call us (CORS)
#   3. Expose a healthcheck so we can confirm the server booted
# Routers (searches / providers / voice) get mounted in later stages as their files fill in.

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import providers as providers_api
from app.api import searches as searches_api
from app.api import voice as voice_api
from app.config import settings
from app.db import models  # noqa: F401  -- importing registers the tables on Base.metadata
from app.db.base import Base
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # `create_all` issues `CREATE TABLE IF NOT EXISTS` for every model registered
    # on Base. Because we use the async engine, we have to run it inside a
    # `run_sync` block — `create_all` itself is sync DDL.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # nothing to tear down on shutdown — asyncpg pool closes itself when the process exits


app = FastAPI(title="MedBridge", lifespan=lifespan)

# CORS = browser rule that JS on origin A can't call API on origin B unless B opts in.
# Frontend will run on :5173 (Vite), API on :8000 — different ports = different origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# mount the API + WS routers. searches_api exposes both an HTTP router (with
# /api/searches prefix) and a separate ws_router (no prefix) for /ws/searches/{id}
# — the WS path is intentionally outside /api per PRD §API.
app.include_router(searches_api.router)
app.include_router(searches_api.ws_router)
app.include_router(voice_api.router)
app.include_router(providers_api.router)


@app.get("/")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
