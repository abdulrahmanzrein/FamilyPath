# Public Q&A for Ontario healthcare navigation (OpenAI or Claude via nexos / Anthropic).

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.agents.llm_gateway import complete_chat, complete_chat_openai
from app.config import settings
from app.schemas.navigator import NavigatorChatRequest, NavigatorChatResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/navigator", tags=["navigator"])

NAVIGATOR_SYSTEM = """You are a helpful guide for navigating the Ontario (Canada) healthcare system. You only answer the user's questions, like a clear, careful FAQ. You are not a phone agent and not part of any automated calling workflow.

Strict rules:
• Follow the reply language instruction in the hints block when present. If it requires English, the full answer must be in English.
• Give general, factual information about Ontario: OHIP, IFHP (intergovernmental refugee and protected person coverage), UHIP for many international students, walk in clinics, family doctors, specialist referrals, Telehealth Ontario (811), Health Care Connect, hospitals, and how these pieces usually fit together.
• Never claim you (or this app) already called a clinic, confirmed a waitlist spot, verified a specific insurance plan with a provider, or have live search results for this user. Never say things like "I just spoke with Clinic X" or "they confirmed they accept your coverage." If they ask about their own case, explain the general steps they should take instead.
• Do not focus on United States insurers or scenarios unless the user is only asking for a general definition; default to Ontario and Canadian public and private coverage context.
• Do not diagnose conditions or give treatment instructions. For emergencies, say to call 911 or go to the nearest emergency department. For non urgent medical questions, mention calling 811 where appropriate.
• Health Care Connect is Ontario's official program to match people with a family doctor who is taking patients; it requires OHIP and is a waitlist style process, not instant booking. Do not promise timelines.
• Keep answers concise (a few short paragraphs or bullet points unless they ask for detail). Mention checking Ontario.ca or local public health for the latest official wording when policies may change.
• In your replies, use commas and periods only. Do not use em dashes, en dashes, or minus signs used as punctuation. Avoid unnecessary hyphenated words when plain words work.

Remember: question and answer help only. No celebratory call summary scripts."""


def _llm_configured() -> bool:
    if settings.openai_api_key and settings.openai_api_key.strip():
        return True
    if settings.bypass_nexos:
        return bool(settings.anthropic_api_key and settings.anthropic_api_key.strip())
    return bool(settings.nexos_api_key and settings.nexos_api_key.strip())


@router.post("/chat", response_model=NavigatorChatResponse)
async def navigator_chat(body: NavigatorChatRequest) -> NavigatorChatResponse:
    if not _llm_configured():
        raise HTTPException(
            status_code=503,
            detail=(
                "Healthcare navigator is unavailable: set OPENAI_API_KEY, or NEXOS_API_KEY, "
                "or ANTHROPIC_API_KEY with BYPASS_NEXOS=true"
            ),
        )

    if body.messages[-1].role != "user":
        raise HTTPException(status_code=422, detail="Last message must be from the user")

    hints: list[str] = []
    if body.language:
        if body.language.strip().lower() == "english":
            hints.append(
                "Reply language (required): English only. Write the entire response in clear English, "
                "even if the user mixes in another language."
            )
        else:
            hints.append(
                f"Reply language (required): {body.language}. "
                "Write the entire response in this language. "
                "Keep well known acronyms such as OHIP, IFHP, UHIP, Health Care Connect in Latin letters when usual for readers."
            )
    if body.insurance_type:
        hints.append(
            f"Intake form indicates insurance category (general): {body.insurance_type}. "
            "Use only to tailor high level Ontario guidance, not to assert eligibility without official verification."
        )
    system = NAVIGATOR_SYSTEM + ("\n\n" + "\n".join(hints) if hints else "")

    api_messages = [{"role": m.role, "content": m.content} for m in body.messages]

    try:
        if settings.openai_api_key and settings.openai_api_key.strip():
            reply = await complete_chat_openai(
                system=system,
                messages=api_messages,
                model=settings.openai_navigator_model,
                max_tokens=2048,
                temperature=0.2,
            )
        else:
            reply = await complete_chat(
                system=system,
                messages=api_messages,
                max_tokens=2048,
                temperature=0.2,
            )
    except Exception as exc:
        logger.warning("navigator chat failed: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="The navigator could not complete this reply. Try again.",
        ) from exc

    if not reply.strip():
        reply = (
            "I don't have a detailed answer right now. Try rephrasing, or visit Ontario.ca "
            "for official information."
        )

    return NavigatorChatResponse(reply=reply.strip())
