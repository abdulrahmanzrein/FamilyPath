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

_CLINIC_CALL_COMPLETION_TIMEOUT_SECONDS = 310.0  # 5 min + small buffer; matches poller max


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
                    # Read the patient's intake details so the voice agent
                    # can introduce the patient by name, give the phone, postal
                    # code, and check language compatibility.
                    patient_details = await _load_patient_details(search_id)
                    await prepare_clinic_call(search_id, source, clinic_name)
                    asyncio.create_task(
                        _place_call_safe(
                            phone_number=phone,
                            clinic_name=clinic_name,
                            insurance_type=patient_details.get("insurance_type") or "ifhp",
                            search_id=search_id,
                            source=source,
                            track_clinic_completion=True,
                            extra_dynamic_variables={
                                "patient_name": patient_details.get("name", ""),
                                "patient_phone": patient_details.get("phone", ""),
                                "patient_postal_code": patient_details.get("postal_code", ""),
                                "patient_language": patient_details.get("language", ""),
                            },
                        )
                    )

            # Only ODHF confirmed triggers the patient callback.
            if status == "confirmed" and source == _DEMO_SOURCE:
                should_call_patient = False
                async with patient_callback_lock:
                    if not patient_callback_triggered.is_set():
                        patient_callback_triggered.set()
                        should_call_patient = True

                if should_call_patient:
                    # Post-call webhook already fired — clinic leg is over; dial the patient
                    # using the phone they submitted on the form (Search.phone).
                    await _patient_callback(
                        search_id,
                        confirmed_clinic=clinic_name or source,
                        source=source,
                        waitlist_message=message,
                    )


async def _load_patient_details(search_id: UUID) -> dict[str, str]:
    """Pull the patient's intake form values out of the searches row so the
    voice agent can quote them on the clinic call (name, phone, postal code,
    language, insurance)."""
    async with SessionLocal() as session:
        search = await session.get(Search, search_id)
        if search is None:
            return {}
        return {
            "name": search.user_name or "",
            "phone": search.phone or "",
            "postal_code": search.postal_code or "",
            "language": search.language or "",
            "insurance_type": search.insurance_type or "",
        }


async def _place_call_safe(
    phone_number: str,
    clinic_name: str,
    insurance_type: str,
    search_id: UUID,
    source: str,
    track_clinic_completion: bool = False,
    extra_dynamic_variables: dict[str, str] | None = None,
) -> None:
    try:
        from app.agents.voice_caller import place_outbound_call

        conversation_id = await place_outbound_call(
            phone_number=phone_number,
            clinic_name=clinic_name,
            insurance_type=insurance_type,
            search_id=search_id,
            source=source,
            extra_dynamic_variables=extra_dynamic_variables,
        )
        logger.info("ElevenLabs clinic call queued — conversation_id=%s", conversation_id)
        if track_clinic_completion:
            await attach_clinic_conversation_id(search_id, source, conversation_id)
            # Poll ElevenLabs for the conversation status. When it flips to
            # "done" / "completed", we mark_clinic_call_finished, which
            # unblocks the confirmed step and triggers the patient callback.
            # This is the webhook-free way to know the clinic call ended.
            asyncio.create_task(
                _poll_clinic_call_until_done(search_id, source, conversation_id)
            )
    except Exception as exc:
        logger.warning("ElevenLabs outbound call failed (non-fatal): %s", exc)
        if track_clinic_completion:
            await mark_clinic_call_finished(
                search_id=search_id,
                source=source,
                outcome="failed",
            )


async def _poll_clinic_call_until_done(
    search_id: UUID, source: str, conversation_id: str
) -> None:
    """Background poller — replaces the post-call webhook for demo reliability.

    Hits ElevenLabs' GET /v1/convai/conversations/{id} every few seconds until
    the conversation status flips to done or failed, then marks the clinic
    call finished. The webhook handler still runs (for free) and `mark_clinic_call_finished`
    is idempotent — whichever signal arrives first wins.
    """
    from app.agents.voice_caller import poll_conversation_until_done

    outcome = await poll_conversation_until_done(conversation_id)
    fired = await mark_clinic_call_finished(
        search_id=search_id,
        source=source,
        outcome=outcome,
    )
    if fired:
        logger.info(
            "Polling marked clinic call %s for %s/%s — outcome=%s",
            conversation_id,
            search_id,
            source,
            outcome,
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
        patient_name = search.user_name or ""
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
                    "patient_name": patient_name,
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
