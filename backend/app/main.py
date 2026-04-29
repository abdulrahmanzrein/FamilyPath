# FastAPI app entry point — what `uvicorn app.main:app` actually serves.
# Responsibilities for this slice:
#   1. Create the DB tables on startup (no Alembic — PRD §Database opts out)
#   2. Allow the React dev server to call us (CORS)
#   3. Expose a healthcheck so we can confirm the server booted
# Routers (searches / providers / voice) get mounted in later stages as their files fill in.

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@app.get("/")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
