# /api/voice/interrupt — ElevenLabs hits this as a tool call when the user
# says something like "skip CPSO, prioritize Appletree" mid-search.
#
# For this slice we only enforce the request contract; the actual mutation of
# the running LangGraph supervisor state is a later piece. Returning 200 keeps
# the voice agent's tool call happy on stage today.

from fastapi import APIRouter, HTTPException

from app.schemas.voice import VoiceInterruptRequest


router = APIRouter(prefix="/api/voice", tags=["voice"])


@router.post("/interrupt")
async def voice_interrupt(body: VoiceInterruptRequest) -> dict[str, bool]:
    # contract: skip and prioritize need a target source; cancel kills the whole
    # run so source is optional. Pydantic Literal already filters bad actions,
    # so the only extra check is the source-required-for-skip/prioritize rule.
    if body.action in ("skip", "prioritize") and body.source is None:
        raise HTTPException(
            status_code=422,
            detail=f"action '{body.action}' requires a source",
        )

    # TODO: when the LangGraph supervisor lands, mutate its state here.
    return {"ok": True}
