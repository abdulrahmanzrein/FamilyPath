"""In-memory call completion state for the live demo.

The fake runner starts the clinic call, then waits here until ElevenLabs sends
the post-call webhook. This keeps the patient callback from firing while the
clinic conversation is still in progress.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from uuid import UUID


@dataclass
class ClinicCallState:
    search_id: UUID
    source: str
    clinic_name: str
    event: asyncio.Event
    conversation_id: str | None = None
    outcome: str | None = None


_calls_by_key: dict[tuple[UUID, str], ClinicCallState] = {}
_calls_by_conversation: dict[str, ClinicCallState] = {}
_lock = asyncio.Lock()


async def prepare_clinic_call(search_id: UUID, source: str, clinic_name: str) -> None:
    async with _lock:
        key = (search_id, source)
        if key not in _calls_by_key:
            _calls_by_key[key] = ClinicCallState(
                search_id=search_id,
                source=source,
                clinic_name=clinic_name,
                event=asyncio.Event(),
            )


async def attach_clinic_conversation_id(search_id: UUID, source: str, conversation_id: str) -> None:
    async with _lock:
        call = _calls_by_key.get((search_id, source))
        if call is None:
            call = ClinicCallState(
                search_id=search_id,
                source=source,
                clinic_name=source,
                event=asyncio.Event(),
            )
            _calls_by_key[(search_id, source)] = call
        call.conversation_id = conversation_id
        _calls_by_conversation[conversation_id] = call


async def mark_clinic_call_finished(
    *,
    conversation_id: str | None = None,
    search_id: UUID | None = None,
    source: str | None = None,
    outcome: str = "completed",
) -> bool:
    async with _lock:
        call = None
        if conversation_id:
            call = _calls_by_conversation.get(conversation_id)
        if call is None and search_id is not None and source:
            call = _calls_by_key.get((search_id, source))
        # Last-resort match for the demo: if we're still searching for any
        # outstanding clinic call (e.g. webhook didn't echo our dynamic vars)
        # take the single oldest unresolved one.
        if call is None and conversation_id is None and search_id is None:
            for candidate in _calls_by_key.values():
                if not candidate.event.is_set():
                    call = candidate
                    break
        if call is None:
            return False

        # Idempotent: don't overwrite a previous outcome — first writer wins.
        if call.event.is_set():
            return True

        call.outcome = outcome
        call.event.set()
        return True


async def wait_for_clinic_call_finished(search_id: UUID, source: str, timeout_seconds: float) -> str:
    async with _lock:
        call = _calls_by_key.get((search_id, source))
        if call is None:
            return "missing"
        event = call.event

    try:
        await asyncio.wait_for(event.wait(), timeout=timeout_seconds)
    except TimeoutError:
        return "timeout"

    async with _lock:
        return call.outcome or "completed"
