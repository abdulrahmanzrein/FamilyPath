# /api/voice/interrupt — ElevenLabs hits this as a tool call when the user
# says something like "skip CPSO, prioritize Appletree" mid-search.
#
# For this slice we only enforce the request contract. Returning 200 keeps the
# voice agent's tool call happy on stage today.

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from app.agents.call_state import mark_clinic_call_finished
from app.schemas.voice import VoiceInterruptRequest


logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/voice", tags=["voice"], redirect_slashes=False)


@router.post("/interrupt")
async def voice_interrupt(body: VoiceInterruptRequest) -> dict[str, bool]:
    if body.action in ("skip", "prioritize") and body.source is None:
        raise HTTPException(
            status_code=422,
            detail=f"action '{body.action}' requires a source",
        )

    # TODO: mutate the scripted runner state if we need live voice interrupts.
    return {"ok": True}


@router.get("/elevenlabs/post-call")
async def elevenlabs_post_call_verify() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/elevenlabs/post-call")
async def elevenlabs_post_call(request: Request) -> dict[str, Any]:
    """Receive ElevenLabs post-call webhooks and unlock the demo callback.

    The fake runner waits for this webhook before changing ODHF from yellow to
    green and calling the patient. Patient callback webhooks are ignored so they
    cannot recursively trigger more calls.
    """
    # Read raw body so non-JSON payloads or unexpected shapes don't 422 us.
    raw = await request.body()
    logger.info(
        "ElevenLabs post-call webhook hit — content-type=%s bytes=%d",
        request.headers.get("content-type"),
        len(raw),
    )
    try:
        payload: dict[str, Any] = await request.json()
    except Exception:
        logger.warning("post-call webhook: body was not valid JSON, treating as empty")
        payload = {}

    logger.info("post-call webhook payload: %s", payload)

    data = payload.get("data")
    if not isinstance(data, dict):
        data = {}

    event_type = payload.get("type") or data.get("type")
    conversation_id = (
        data.get("conversation_id")
        or payload.get("conversation_id")
        or data.get("conversationId")
        or payload.get("conversationId")
    )
    dynamic_variables = _extract_dynamic_variables(data) or _extract_dynamic_variables(payload)

    if dynamic_variables.get("call_type") == "patient_callback":
        logger.info("post-call webhook: ignoring patient_callback echo")
        return {"ok": True, "matched": False, "ignored": "patient_callback"}

    search_id = _parse_uuid(dynamic_variables.get("search_id"))
    source = dynamic_variables.get("source")
    if source is not None:
        source = str(source)

    outcome = _webhook_outcome(event_type)
    matched = await mark_clinic_call_finished(
        conversation_id=str(conversation_id) if conversation_id else None,
        search_id=search_id,
        source=source,
        outcome=outcome,
    )

    logger.info(
        "post-call webhook resolved — matched=%s outcome=%s search_id=%s source=%s conversation_id=%s",
        matched,
        outcome,
        search_id,
        source,
        conversation_id,
    )

    return {
        "ok": True,
        "matched": matched,
        "outcome": outcome,
    }


def _extract_dynamic_variables(data: dict[str, Any]) -> dict[str, Any]:
    client_data = data.get("conversation_initiation_client_data")
    if isinstance(client_data, dict):
        dynamic_variables = client_data.get("dynamic_variables")
        if isinstance(dynamic_variables, dict):
            return dynamic_variables

    metadata = data.get("metadata")
    if isinstance(metadata, dict):
        dynamic_variables = metadata.get("dynamic_variables")
        if isinstance(dynamic_variables, dict):
            return dynamic_variables

    return {}


def _parse_uuid(value: Any) -> UUID | None:
    if value is None:
        return None
    try:
        return UUID(str(value))
    except ValueError:
        return None


def _webhook_outcome(event_type: Any) -> str:
    event_name = str(event_type or "")
    if event_name == "call_initiation_failure" or "failure" in event_name:
        return "failed"
    return "completed"
