# sets up the async DB connection + a FastAPI dependency for getting a session per request

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

# the engine is the long-lived connection pool to postgres
# echo=True would log every SQL query — useful for debugging, noisy otherwise
engine = create_async_engine(settings.database_url, echo=False)

# factory for short-lived sessions (one per request)
# expire_on_commit=False so we can read object attrs after committing without a re-fetch
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


# FastAPI calls this for any route that does `Depends(get_session)`
# the `async with` makes sure the session closes even if the request errors
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
