# scripted demo version of the 5 worker agents
# walks each source through pending -> searching -> found -> calling -> confirmed/failed
# writes rows to search_results AND broadcasts events through the websocket hub
# so the REST status endpoint and the live dashboard stay in sync

import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

from app.agents.call_state import (
    attach_clinic_conversation_id,
    mark_clinic_call_finished,
    prepare_clinic_call,
    wait_for_clinic_call_finished,
)
from app.config import settings
from app.db.models import Search, SearchResult
from app.db.session import SessionLocal
from app.ws.hub import hub

logger = logging.getLogger(__name__)

_CLINIC_CALL_COMPLETION_TIMEOUT_SECONDS = 90.0
# Timer fallback: if the ElevenLabs post-call webhook hasn't arrived this many
# seconds after we placed the clinic call, mark it complete anyway so the
# patient callback still fires. Webhook wins if it arrives first.
_CLINIC_CALL_TIMER_FALLBACK_SECONDS = 30.0


# each source has its own scripted journey
# (status, clinic_name, message, delay_seconds_before_this_step)
SOURCE_SCRIPTS: dict[str, list[tuple[str, str | None, str, float]]] = {
    "odhf": [
        ("pending", None, "queued", 0.0),
        ("searching", None, "looking up clinics in postal area", 1.5),
        ("found", "Heart Lake Health Centre", "clinic is accepting waitlist requests", 1.5),
        ("calling", "Heart Lake Health Centre", "calling clinic to add user to waitlist", 2.0),
        # delay 0 — webhook gates the transition to confirmed
        ("confirmed", "Heart Lake Health Centre", "user added to waitlist", 0.0),
    ],
    "cpso": [
        ("pending", None, "queued", 0.0),
        ("searching", None, "scanning CPSO register for Punjabi GPs", 1.5),
        ("found", "Bramalea Community Clinic", "clinic is accepting waitlist requests", 2.0),
    ],
    "appletree": [
        ("pending", None, "queued", 0.0),
        ("searching", None, "checking Appletree clinic pages", 1.0),
        ("found", "Sandalwood Medical Clinic", "clinic is accepting waitlist requests", 1.5),
    ],
    "ifhp": [
        ("pending", None, "queued", 0.0),
        ("searching", None, "querying Medavie IFHP directory", 2.0),
        ("found", "Scarborough Newcomer Health Centre", "clinic is accepting waitlist requests", 1.5),
    ],
    "mci": [
        ("pending", None, "queued", 0.0),
        ("searching", None, "scanning MCI clinic locations", 1.5),
        ("failed", None, "no MCI clinics within radius", 2.0),
    ],
}

# which source triggers the live ElevenLabs outbound call in the demo
_DEMO_SOURCE = "odhf"
_PATIENT_CALLBACK_RETRIES = 3
_PATIENT_CALLBACK_RETRY_DELAY_SECONDS = 5.0


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

            # For ODHF confirmed: block until ElevenLabs post-call webhook fires.
            # This ensures ODHF only turns green after the clinic conversation ends.
            if status == "confirmed" and source == _DEMO_SOURCE:
                call_outcome = await wait_for_clinic_call_finished(
                    search_id,
                    source,
                    _CLINIC_CALL_COMPLETION_TIMEOUT_SECONDS,
                )
                if call_outcome != "completed":
                    status = "failed"
                    message = _clinic_call_failure_message(call_outcome)

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

            event = {
                "source": source,
                "status": status,
                "clinic_name": clinic_name,
                "message": message,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            await hub.broadcast(search_id, event)

            # When ODHF hits "calling", place the live ElevenLabs clinic call.
            # prepare_clinic_call registers the asyncio.Event that the confirmed
            # step blocks on. The call itself runs in the background.
            if status == "calling" and source == _DEMO_SOURCE:
                phone = settings.demo_phone_number
                if phone and clinic_name:
                    await prepare_clinic_call(search_id, source, clinic_name)
                    asyncio.create_task(
                        _place_call_safe(
                            phone_number=phone,
                            clinic_name=clinic_name,
                            insurance_type="ifhp",
                            search_id=search_id,
                            source=source,
                            track_clinic_completion=True,
                        )
                    )
                    # Timer fallback: if the ElevenLabs post-call webhook
                    # never arrives (e.g. tunnel down, webhook misconfigured),
                    # this fires after _CLINIC_CALL_TIMER_FALLBACK_SECONDS and
                    # unblocks the confirmed step so the patient callback
                    # still fires. The webhook wins if it arrives first
                    # because mark_clinic_call_finished is now idempotent.
                    asyncio.create_task(
                        _clinic_call_timer_fallback(search_id, source)
                    )

            # Only ODHF confirmed triggers the patient callback.
            if status == "confirmed" and source == _DEMO_SOURCE:
                should_call_patient = False
                async with patient_callback_lock:
                    if not patient_callback_triggered.is_set():
                        patient_callback_triggered.set()
                        should_call_patient = True

                if should_call_patient:
                    await _patient_callback(
                        search_id,
                        confirmed_clinic=clinic_name or source,
                        source=source,
                        waitlist_message=message,
                    )


async def _place_call_safe(
    phone_number: str,
    clinic_name: str,
    insurance_type: str,
    search_id: UUID,
    source: str,
    track_clinic_completion: bool = False,
) -> None:
    try:
        from app.agents.voice_caller import place_outbound_call

        conversation_id = await place_outbound_call(
            phone_number=phone_number,
            clinic_name=clinic_name,
            insurance_type=insurance_type,
            search_id=search_id,
            source=source,
        )
        logger.info("ElevenLabs clinic call queued — conversation_id=%s", conversation_id)
        if track_clinic_completion:
            await attach_clinic_conversation_id(search_id, source, conversation_id)
    except Exception as exc:
        logger.warning("ElevenLabs outbound call failed (non-fatal): %s", exc)
        if track_clinic_completion:
            await mark_clinic_call_finished(
                search_id=search_id,
                source=source,
                outcome="failed",
            )


async def _clinic_call_timer_fallback(search_id: UUID, source: str) -> None:
    """Demo-grade safety net: if ElevenLabs' post-call webhook never lands
    (e.g. tunnel down or webhook misconfigured), unblock the confirmed step
    after a fixed delay so the patient callback still fires."""
    await asyncio.sleep(_CLINIC_CALL_TIMER_FALLBACK_SECONDS)
    fired = await mark_clinic_call_finished(
        search_id=search_id,
        source=source,
        outcome="completed",
    )
    if fired:
        logger.info(
            "Timer fallback marked clinic call complete for %s/%s after %.0fs",
            search_id,
            source,
            _CLINIC_CALL_TIMER_FALLBACK_SECONDS,
        )


def _clinic_call_failure_message(outcome: str) -> str:
    if outcome == "timeout":
        return "clinic call completion was not received"
    if outcome == "missing":
        return "clinic call was not started"
    return "clinic call ended before waitlist confirmation"


async def _patient_callback(
    search_id: UUID,
    *,
    confirmed_clinic: str,
    source: str,
    waitlist_message: str,
) -> None:
    """Call the patient after the clinic conversation ends."""
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

    if not settings.elevenlabs_api_key:
        logger.info("ElevenLabs not configured — skipping patient callback for %s", search_id)
        return

    from app.agents.voice_caller import place_outbound_call

    for attempt in range(1, _PATIENT_CALLBACK_RETRIES + 1):
        try:
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
                agent_id_override=settings.elevenlabs_patient_agent_id or None,
                phone_number_id_override=settings.elevenlabs_patient_phone_number_id or None,
            )
            logger.info(
                "Patient callback queued for search %s — conversation_id=%s — clinic=%s",
                search_id,
                conversation_id,
                confirmed_clinic,
            )
            return
        except Exception as exc:
            if attempt == _PATIENT_CALLBACK_RETRIES:
                logger.warning(
                    "Patient callback failed after %s attempts (non-fatal): %s",
                    attempt,
                    exc,
                )
                return
            logger.warning(
                "Patient callback attempt %s failed; retrying in %.0fs: %s",
                attempt,
                _PATIENT_CALLBACK_RETRY_DELAY_SECONDS,
                exc,
            )
            await asyncio.sleep(_PATIENT_CALLBACK_RETRY_DELAY_SECONDS)


# entry point — runs all 5 sources in parallel
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

    async with SessionLocal() as session:
        search = await session.get(Search, search_id)
        if search is not None:
            from datetime import datetime, timezone as tz
            search.status = "completed"
            search.completed_at = datetime.now(tz.utc)
            await session.commit()
