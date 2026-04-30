# pretend version of the 5 worker agents — used until the real LangGraph supervisor is built
# walks each source through pending -> searching -> found -> calling -> confirmed/failed
# writes rows to search_results AND broadcasts events through the websocket hub
# so the REST status endpoint and the live dashboard stay in sync

import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

from app.config import settings
from app.db.models import Search, SearchResult
from app.db.session import SessionLocal
from app.ws.hub import hub

logger = logging.getLogger(__name__)


# each source has its own scripted journey
# (status, clinic_name, message, delay_seconds_before_this_step)
SOURCE_SCRIPTS: dict[str, list[tuple[str, str | None, str, float]]] = {
    "odhf": [
        ("pending", None, "queued", 0.0),
        ("searching", None, "looking up clinics in postal area", 1.5),
        ("found", "Heart Lake Health Centre", "clinic is accepting waitlist requests", 1.5),
        ("calling", "Heart Lake Health Centre", "calling clinic to add user to waitlist", 2.0),
        ("confirmed", "Heart Lake Health Centre", "user added to waitlist", 4.5),
    ],
    "cpso": [
        ("pending", None, "queued", 0.0),
        ("searching", None, "scanning CPSO register for Punjabi GPs", 1.5),
        ("found", "Bramalea Community Clinic", "clinic is accepting waitlist requests", 2.0),
        ("calling", "Bramalea Community Clinic", "calling clinic to add user to waitlist", 2.0),
        ("confirmed", "Bramalea Community Clinic", "user added to waitlist", 2.0),
    ],
    "appletree": [
        ("pending", None, "queued", 0.0),
        ("searching", None, "checking Appletree clinic pages", 1.0),
        ("found", "Sandalwood Medical Clinic", "clinic is accepting waitlist requests", 1.5),
        ("calling", "Sandalwood Medical Clinic", "calling clinic to add user to waitlist", 2.0),
        ("confirmed", "Sandalwood Medical Clinic", "user added to waitlist", 3.0),
    ],
    "ifhp": [
        ("pending", None, "queued", 0.0),
        ("searching", None, "querying Medavie IFHP directory", 2.0),
        ("found", "Scarborough Newcomer Health Centre", "clinic is accepting waitlist requests", 1.5),
        ("calling", "Scarborough Newcomer Health Centre", "calling clinic to add user to waitlist", 2.0),
        # stays in "calling" — call still ringing when search wraps up
    ],
    "mci": [
        ("pending", None, "queued", 0.0),
        ("searching", None, "scanning MCI clinic locations", 1.5),
        ("failed", None, "no MCI clinics within radius", 2.0),
    ],
}

# which source triggers the live ElevenLabs outbound call in the demo
_DEMO_SOURCE = "odhf"


async def _simulate_source(
    search_id: UUID,
    source: str,
    script: list[tuple[str, str | None, str, float]],
    patient_callback_triggered: asyncio.Event,
    patient_callback_lock: asyncio.Lock,
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

            # When the demo source hits "calling", place the live ElevenLabs call.
            # We fire-and-forget via asyncio.create_task so the scripted timeline
            # continues (next step will arrive and flip the card to "confirmed"
            # once the simulated delay elapses — the real ElevenLabs result updates
            # the same row via the post-call webhook when it lands).
            if status == "calling" and source == _DEMO_SOURCE:
                phone = settings.demo_phone_number
                if phone and clinic_name:
                    asyncio.create_task(
                        _place_call_safe(
                            phone_number=phone,
                            clinic_name=clinic_name,
                            insurance_type="ifhp",  # scripted demo always uses IFHP
                            search_id=search_id,
                            source=source,
                        )
                    )

            # The demo callback belongs to the same clinic call the audience hears.
            # Other sources can confirm visually, but only ODHF/Heart Lake calls the user back.
            if status == "confirmed" and source == _DEMO_SOURCE:
                async with patient_callback_lock:
                    if not patient_callback_triggered.is_set():
                        patient_callback_triggered.set()
                        asyncio.create_task(
                            _patient_callback(
                                search_id,
                                confirmed_clinic=clinic_name or source,
                                source=source,
                                waitlist_message=message,
                            )
                        )


async def _place_call_safe(
    phone_number: str,
    clinic_name: str,
    insurance_type: str,
    search_id: UUID,
    source: str,
) -> None:
    """Wrapper around voice_caller.place_outbound_call that logs and swallows
    exceptions so a failed call doesn't crash the fake_runner task."""
    try:
        from app.agents.voice_caller import place_outbound_call  # local import avoids circular deps

        conversation_id = await place_outbound_call(
            phone_number=phone_number,
            clinic_name=clinic_name,
            insurance_type=insurance_type,
            search_id=search_id,
            source=source,
        )
        logger.info("ElevenLabs call queued — conversation_id=%s", conversation_id)
    except Exception as exc:
        logger.warning("ElevenLabs outbound call failed (non-fatal): %s", exc)


async def _patient_callback(
    search_id: UUID,
    *,
    confirmed_clinic: str,
    source: str,
    waitlist_message: str,
) -> None:
    """Call the patient as soon as a clinic successfully confirms the waitlist."""
    async with SessionLocal() as session:
        search = await session.get(Search, search_id)
        if search is None:
            return
        patient_phone = search.phone
        language = search.language
        insurance_type = search.insurance_type

    if not patient_phone:
        logger.info("no patient phone for search %s — skipping callback", search_id)
        return

    if not settings.elevenlabs_api_key or not settings.elevenlabs_agent_id:
        logger.info("ElevenLabs not configured — skipping patient callback for %s", search_id)
        return

    try:
        from app.agents.voice_caller import place_outbound_call  # local import avoids circular deps

        conversation_id = await place_outbound_call(
            phone_number=patient_phone,
            clinic_name=confirmed_clinic,
            insurance_type=insurance_type,
            search_id=search_id,
            source=source,
            extra_dynamic_variables={
                "call_type": "patient_callback",
                "patient_language": language,
                "result_message": waitlist_message,
            },
        )
        logger.info(
            "Patient callback queued for search %s — conversation_id=%s — clinic=%s",
            search_id,
            conversation_id,
            confirmed_clinic,
        )
    except Exception as exc:
        logger.warning("Patient callback failed (non-fatal): %s", exc)


# entry point — runs all 5 sources in parallel; ODHF confirmation triggers callback
async def run_fake_search(search_id: UUID) -> None:
    patient_callback_triggered = asyncio.Event()
    patient_callback_lock = asyncio.Lock()

    await asyncio.gather(
        *(
            _simulate_source(
                search_id,
                source,
                script,
                patient_callback_triggered,
                patient_callback_lock,
            )
            for source, script in SOURCE_SCRIPTS.items()
        )
    )

    # mark the parent search row completed
    async with SessionLocal() as session:
        search = await session.get(Search, search_id)
        if search is not None:
            from datetime import datetime, timezone as tz
            search.status = "completed"
            search.completed_at = datetime.now(tz.utc)
            await session.commit()
