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

from uuid import UUID

import httpx

from app.config import settings


# ElevenLabs Conversational AI outbound-call endpoint for Twilio-backed agents.
# Body shape per ElevenLabs docs:
#   https://elevenlabs.io/docs/conversational-ai/api-reference/twilio/outbound-call
_ELEVENLABS_OUTBOUND_URL = (
    "https://api.elevenlabs.io/v1/convai/twilio/outbound-call"
)

# How long to wait for ElevenLabs to acknowledge the call request before
# we give up and let the supervisor mark the worker `failed`. ElevenLabs
# only needs to *queue* the call here; the call itself runs async on their
# side, so a short timeout is fine.
_REQUEST_TIMEOUT_SECONDS = 30.0


async def place_outbound_call(
    phone_number: str,
    clinic_name: str,
    insurance_type: str,
    search_id: UUID,
    source: str,
) -> str:
    """Place an outbound call via ElevenLabs Conversational AI.

    Passes clinic_name and insurance_type as dynamic_variables for the agent's
    English script. Passes search_id and source as conversation metadata so
    Block 3's end-of-call webhook can route the result back to the right row.

    Returns the ElevenLabs conversation_id.
    """
    if not settings.elevenlabs_api_key:
        raise RuntimeError(
            "elevenlabs_api_key is not configured — cannot place outbound call"
        )
    if not settings.elevenlabs_agent_id:
        raise RuntimeError(
            "elevenlabs_agent_id is not configured — cannot place outbound call"
        )
    if not settings.elevenlabs_phone_number_id:
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

    payload = {
        "agent_id": settings.elevenlabs_agent_id,
        "agent_phone_number_id": settings.elevenlabs_phone_number_id,
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
