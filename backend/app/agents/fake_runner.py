# pretend version of the 5 worker agents — used until the real LangGraph supervisor is built
# walks each source through pending -> searching -> found -> calling -> confirmed/failed
# writes rows to search_results AND broadcasts events through the websocket hub
# so the REST status endpoint and the live dashboard stay in sync

import asyncio
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

from app.db.models import SearchResult
from app.db.session import SessionLocal
from app.ws.hub import hub


# each source has its own scripted journey
# (status, clinic_name, message, delay_seconds_before_this_step)
SOURCE_SCRIPTS: dict[str, list[tuple[str, str | None, str, float]]] = {
    "odhf": [
        ("pending", None, "queued", 0.0),
        ("searching", None, "looking up clinics in postal area", 1.5),
        ("found", "Brampton Family Medicine", "match found", 1.5),
        ("calling", "Brampton Family Medicine", "calling clinic to verify", 2.0),
        ("confirmed", "Brampton Family Medicine", "accepting new IFHP patients", 2.5),
    ],
    "cpso": [
        ("pending", None, "queued", 0.0),
        ("searching", None, "scanning CPSO register for Punjabi GPs", 1.5),
        ("found", "Dr. Singh — Heart Lake Clinic", "match found", 2.0),
        ("calling", "Dr. Singh — Heart Lake Clinic", "calling clinic to verify", 2.0),
        ("confirmed", "Dr. Singh — Heart Lake Clinic", "accepting new patients", 2.0),
    ],
    "appletree": [
        ("pending", None, "queued", 0.0),
        ("searching", None, "checking Appletree clinic pages", 1.0),
        ("found", "Appletree Bramalea", "match found", 1.5),
        ("calling", "Appletree Bramalea", "calling clinic to verify", 2.0),
        ("confirmed", "Appletree Bramalea", "accepting IFHP", 3.0),
    ],
    "ifhp": [
        ("pending", None, "queued", 0.0),
        ("searching", None, "querying Medavie IFHP directory", 2.0),
        ("found", "Newcomer Health Centre", "match found", 1.5),
        ("calling", "Newcomer Health Centre", "voice call in progress", 2.0),
        # stays in "calling" — call still ringing when search wraps up
    ],
    "mci": [
        ("pending", None, "queued", 0.0),
        ("searching", None, "scanning MCI clinic locations", 1.5),
        ("failed", None, "no MCI clinics within radius", 2.0),
    ],
}


async def _simulate_source(
    search_id: UUID,
    source: str,
    script: list[tuple[str, str | None, str, float]],
) -> None:
    # one DB session per source so they don't fight over a shared one
    async with SessionLocal() as session:
        for status, clinic_name, message, delay in script:
            if delay:
                await asyncio.sleep(delay)

            # find or create the search_results row for this (search_id, source)
            existing = await session.execute(
                select(SearchResult).where(
                    SearchResult.search_id == search_id,
                    SearchResult.source == source,
                )
            )
            row = existing.scalar_one_or_none()

            if row is None:
                row = SearchResult(
                    search_id=search_id,
                    source=source,
                    agent_status=status,
                    clinic_name=clinic_name,
                )
                session.add(row)
            else:
                row.agent_status = status
                if clinic_name is not None:
                    row.clinic_name = clinic_name

            await session.commit()

            # AgentStatus shape from app/schemas/searches.py
            event = {
                "source": source,
                "status": status,
                "clinic_name": clinic_name,
                "message": message,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            await hub.broadcast(search_id, event)


# entry point — runs all 5 sources in parallel
async def run_fake_search(search_id: UUID) -> None:
    await asyncio.gather(
        *(_simulate_source(search_id, source, script) for source, script in SOURCE_SCRIPTS.items())
    )
