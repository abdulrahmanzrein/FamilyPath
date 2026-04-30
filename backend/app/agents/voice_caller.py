"""ElevenLabs outbound-call trigger.

This is the bridge between our agent supervisor (Block 4) and the actual
phone call. The supervisor calls `place_outbound_call(...)` after a worker
finds a candidate clinic; ElevenLabs then dials Twilio internally and the
agent runs the hardcoded English script:

    "Are you currently accepting new IFHP-covered patients for family medicine?"

The clinic's name and the patient's insurance type are passed as
`dynamic_variables` so the agent prompt can interpolate them. We also smuggle
`search_id` and `source` into dynamic_variables so that Block 3's end-of-call
webhook receives them in the post-call payload and can update the right
`search_results` row.

Sponsor wiring: ElevenLabs Conversational AI (which initiates the Twilio
outbound call internally — we never touch Twilio directly here).
"""

from __future__ import annotations

import asyncio
import logging
import re
from uuid import UUID

import httpx

from app.config import settings


logger = logging.getLogger(__name__)


# ElevenLabs Conversational AI outbound-call endpoint for Twilio-backed agents.
# Body shape per ElevenLabs docs:
#   https://elevenlabs.io/docs/conversational-ai/api-reference/twilio/outbound-call
_ELEVENLABS_OUTBOUND_URL = (
    "https://api.elevenlabs.io/v1/convai/twilio/outbound-call"
)

_ELEVENLABS_CONVERSATION_URL = (
    "https://api.elevenlabs.io/v1/convai/conversations/{conversation_id}"
)

# How long to wait for ElevenLabs to acknowledge the call request before
# we give up and let the supervisor mark the worker `failed`. ElevenLabs
# only needs to *queue* the call here; the call itself runs async on their
# side, so a short timeout is fine.
_REQUEST_TIMEOUT_SECONDS = 30.0


def _normalize_phone_number(phone_number: str) -> str:
    """Normalize common North American phone formats into E.164.

    Accepts inputs like:
    - `4165550100`
    - `416 555 0100`
    - `(416) 555-0100`
    - `+14165550100`

    Returns a `+1XXXXXXXXXX` string when possible.
    """
    digits = re.sub(r"\D", "", phone_number)
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    if phone_number.startswith("+") and digits:
        return f"+{digits}"
    raise ValueError(f"invalid phone number format: {phone_number!r}")


async def place_outbound_call(
    phone_number: str,
    clinic_name: str,
    insurance_type: str,
    search_id: UUID,
    source: str,
    extra_dynamic_variables: dict[str, str] | None = None,
    agent_id_override: str | None = None,
    phone_number_id_override: str | None = None,
) -> str:
    """Place an outbound call via ElevenLabs Conversational AI.

    Passes clinic_name and insurance_type as dynamic_variables for the agent's
    English script. Passes search_id and source as conversation metadata so
    Block 3's end-of-call webhook can route the result back to the right row.

    Returns the ElevenLabs conversation_id.
    """
    phone_number = _normalize_phone_number(phone_number)
    agent_id = agent_id_override or settings.elevenlabs_agent_id
    phone_number_id = phone_number_id_override or settings.elevenlabs_phone_number_id

    if not settings.elevenlabs_api_key:
        raise RuntimeError(
            "elevenlabs_api_key is not configured — cannot place outbound call"
        )
    if not agent_id:
        raise RuntimeError(
            "elevenlabs_agent_id is not configured — cannot place outbound call"
        )
    if not phone_number_id:
        raise RuntimeError(
            "elevenlabs_phone_number_id is not configured — "
            "cannot place outbound call"
        )

    # Everything Block 3's webhook needs to identify the row goes here.
    # ElevenLabs echoes dynamic_variables back in the post-call webhook
    # payload, so this is our round-trip context channel.
    dynamic_variables = {
        "clinic_name": clinic_name,
        "insurance_type": insurance_type,
        # UUID is not JSON-serializable by default — stringify it.
        "search_id": str(search_id),
        "source": source,
    }
    if extra_dynamic_variables:
        dynamic_variables.update(extra_dynamic_variables)

    payload = {
        "agent_id": agent_id,
        "agent_phone_number_id": phone_number_id,
        "to_number": phone_number,
        "conversation_initiation_client_data": {
            "dynamic_variables": dynamic_variables,
        },
    }

    headers = {
        "xi-api-key": settings.elevenlabs_api_key,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT_SECONDS) as client:
        response = await client.post(
            _ELEVENLABS_OUTBOUND_URL,
            headers=headers,
            json=payload,
        )

    # Non-2xx → raise so the supervisor can mark the worker `failed` and the
    # WS hub broadcasts a `failed` status to the dashboard.
    if response.status_code >= 400:
        raise RuntimeError(
            f"ElevenLabs outbound-call failed "
            f"(status={response.status_code}): {response.text}"
        )

    body = response.json()

    # ElevenLabs returns the conversation_id of the call it just queued.
    # Block 3's webhook uses this same id to identify which conversation
    # finished — return it so the supervisor can persist it on the
    # `search_results` row if desired.
    conversation_id = body.get("conversation_id")
    if not conversation_id:
        raise RuntimeError(
            f"ElevenLabs outbound-call response missing conversation_id: {body}"
        )

    return conversation_id


# How often to poll ElevenLabs for conversation status, and the max wall-clock
# we'll keep polling before giving up. The clinic call typically lasts 15–60s,
# so 5 minutes is a generous ceiling.
_POLL_INTERVAL_SECONDS = 3.0
_POLL_MAX_SECONDS = 300.0


async def poll_conversation_until_done(
    conversation_id: str,
    interval: float = _POLL_INTERVAL_SECONDS,
    max_seconds: float = _POLL_MAX_SECONDS,
) -> str:
    """Poll the ElevenLabs conversation API until the call is no longer in
    progress. Returns one of: "completed", "failed", "timeout".

    ElevenLabs sets `status` on a conversation to one of:
      - "initiated" / "in-progress" / "processing"  → still going
      - "done"                                       → completed normally
      - "failed"                                     → call failed
    Anything else we treat as still-running and keep polling.

    This is the polling counterpart to the post-call webhook — it lets us
    detect call completion without depending on a public tunnel.
    """
    if not settings.elevenlabs_api_key:
        return "failed"

    url = _ELEVENLABS_CONVERSATION_URL.format(conversation_id=conversation_id)
    headers = {"xi-api-key": settings.elevenlabs_api_key}

    elapsed = 0.0
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Give ElevenLabs a beat to register the conversation before the first poll.
        await asyncio.sleep(interval)
        while elapsed < max_seconds:
            try:
                response = await client.get(url, headers=headers)
            except httpx.HTTPError as exc:
                logger.warning(
                    "poll_conversation_until_done: transport error for %s — %s",
                    conversation_id,
                    exc,
                )
                await asyncio.sleep(interval)
                elapsed += interval
                continue

            if response.status_code == 404:
                # Conversation not yet visible — keep polling.
                await asyncio.sleep(interval)
                elapsed += interval
                continue

            if response.status_code >= 400:
                logger.warning(
                    "poll_conversation_until_done: %s returned %s — %s",
                    conversation_id,
                    response.status_code,
                    response.text[:200],
                )
                await asyncio.sleep(interval)
                elapsed += interval
                continue

            data = response.json()
            raw_status = str(data.get("status", "")).lower()
            call_successful = data.get("call_successful")
            logger.info(
                "poll_conversation_until_done: %s — status=%s call_successful=%s",
                conversation_id,
                raw_status,
                call_successful,
            )

            if raw_status in {"done", "completed", "finished", "ended"}:
                return "completed"
            if raw_status in {"failed", "error"}:
                return "failed"
            # Anything else (e.g. "processing", "in-progress", "initiated"): keep polling.

            await asyncio.sleep(interval)
            elapsed += interval

    return "timeout"
