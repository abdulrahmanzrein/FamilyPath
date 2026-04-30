# nexos.ai PII gateway — wraps every Claude call so user_name + free-text user fields
# never reach Anthropic raw. Per prd.md §Key Constraints this MUST exist before any
# Claude call site lands. All transcript parsing, yes/no extraction, and any future
# LLM features in this app go through `complete()` below.
#
# Two paths:
#   1) Default — POST to nexos.ai's gateway endpoint. Gateway scrubs PII, then forwards
#      to Anthropic on our behalf. We get the Claude response back unchanged.
#   2) BYPASS_NEXOS=true — emergency demo fallback per prd.md §Risk Register. Goes
#      straight to Anthropic. We still scrub locally so PII never leaves the process.
#
# What's stripped:
#   - `user_name` (Search.user_name — patient's real name)
#   - any string field marked as free-text user input ("notes", "message_from_user", etc.)
#   - postal codes are NOT stripped — FSA-level (e.g. "M5V") is allowed through per PRD
#
# Call shape is intentionally narrow: one function, one return type. Adding tool-use,
# streaming, or multi-turn later means extending this — not bypassing it.

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Claude Sonnet 4.6 — the model id used everywhere in this app.
# Pinned here so call sites don't drift.
CLAUDE_MODEL = "claude-sonnet-4-5-20250929"

# nexos.ai gateway base URL. The PRD specifies nexos.ai wraps every Claude call but
# does not pin a URL; this is the documented Anthropic-compatible endpoint. If their
# real endpoint differs, change this one constant.
NEXOS_BASE_URL = "https://api.nexos.ai/v1"

ANTHROPIC_BASE_URL = "https://api.anthropic.com/v1"
ANTHROPIC_VERSION = "2023-06-01"

# Field names we always strip from the structured PII payload before sending.
# user_name is the canonical PII field on Search rows.
_PII_KEYS = {"user_name", "name", "patient_name", "full_name", "user_notes", "free_text"}

# Loose pattern for stripping bare phone numbers if they sneak into a free-text prompt.
# Not a security boundary — defence in depth on top of structured stripping.
_PHONE_RE = re.compile(r"\+?\d[\d\-\s().]{7,}\d")


def _scrub_pii(payload: dict[str, Any]) -> dict[str, Any]:
    """Remove PII keys from a structured payload before it leaves this process.

    Intentionally conservative: drops the key entirely rather than masking, so a
    downstream prompt template that interpolated `{user_name}` will fail loudly
    instead of silently leaking. Postal codes are FSA-level per PRD and stay.
    """
    cleaned: dict[str, Any] = {}
    for key, value in payload.items():
        if key in _PII_KEYS:
            continue
        if isinstance(value, str):
            cleaned[key] = _PHONE_RE.sub("[redacted-phone]", value)
        else:
            cleaned[key] = value
    return cleaned


async def complete(
    *,
    system: str,
    user_prompt: str,
    pii_context: dict[str, Any] | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.0,
) -> str:
    """Single Claude entrypoint for the whole backend.

    Args:
        system: System prompt — not interpolated with user PII.
        user_prompt: The actual user-turn message. Should be pre-templated by the
            caller using ONLY non-PII fields (clinic_name, transcript text, etc.).
        pii_context: Optional structured map of fields the caller *would* like Claude
            to see — passed through `_scrub_pii` first. Anything in `_PII_KEYS` is
            dropped. Survivors are appended to the user message as a JSON-ish tail.
        max_tokens: Claude max_tokens. Default 1024 — yes/no extraction is tiny.
        temperature: Defaults to 0 for deterministic extraction.

    Returns:
        The plain text of Claude's first content block. Caller does its own parsing.
    """
    safe_context = _scrub_pii(pii_context or {})
    if safe_context:
        user_prompt = f"{user_prompt}\n\nContext: {safe_context}"

    body = {
        "model": CLAUDE_MODEL,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system,
        "messages": [{"role": "user", "content": user_prompt}],
    }

    if settings.bypass_nexos:
        # Emergency path — direct Anthropic. PII still scrubbed locally above.
        logger.warning("BYPASS_NEXOS=true — calling Anthropic directly, skipping nexos.ai")
        url = f"{ANTHROPIC_BASE_URL}/messages"
        headers = {
            "x-api-key": settings.anthropic_api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
    else:
        # Default path — nexos.ai gateway. They forward to Anthropic on our behalf
        # and apply their own PII filters on top of our local scrub.
        url = f"{NEXOS_BASE_URL}/messages"
        headers = {
            "Authorization": f"Bearer {settings.nexos_api_key}",
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=body, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    # Anthropic Messages API shape: { content: [{ type: "text", text: "..." }, ...] }
    blocks = data.get("content", [])
    for block in blocks:
        if block.get("type") == "text":
            return block.get("text", "")
    return ""
