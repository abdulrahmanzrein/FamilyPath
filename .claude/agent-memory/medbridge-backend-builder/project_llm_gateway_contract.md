---
name: LLM gateway contract
description: Single Claude entrypoint shape used everywhere in the backend; all call sites must go through this
type: project
---

`backend/app/agents/llm_gateway.py` exposes one async function: `complete(system, user_prompt, pii_context=None, max_tokens=1024, temperature=0.0) -> str`. Every Claude call in this codebase must go through it — no direct anthropic SDK imports anywhere else.

Key decisions baked in:
- Pinned model id: `claude-sonnet-4-5-20250929` (Sonnet 4.6 family) as `CLAUDE_MODEL` constant. Change here if upgrading.
- Default path POSTs to `https://api.nexos.ai/v1/messages` with `Authorization: Bearer ${NEXOS_API_KEY}`. Body shape is Anthropic Messages API. PRD did not pin nexos's URL — this is a placeholder constant `NEXOS_BASE_URL` that may need updating when real nexos creds arrive.
- `BYPASS_NEXOS=true` (env, read via `settings.bypass_nexos`) short-circuits to `https://api.anthropic.com/v1/messages` with `x-api-key`. Local PII scrub still runs.
- `_PII_KEYS = {user_name, name, patient_name, full_name, user_notes, free_text}` get DROPPED from `pii_context` (not masked). Postal code is allowed through per PRD — FSA-level only.
- Phone numbers in user_prompt strings get regex-replaced with `[redacted-phone]` as defence in depth.
- Returns the first text content block as a plain str. No tool-use plumbed yet.

**Why:** PRD §Key Constraints requires nexos.ai wraps every Claude call before any call site lands. Centralizing in one function means future Claude usage (transcript yes/no extraction, anything else) cannot accidentally bypass the gateway.

**How to apply:** When adding any LLM call, import `from app.agents.llm_gateway import complete` and call it. Never import `anthropic` directly. If a feature needs streaming or tool-use, extend `complete()` itself rather than adding a parallel path.
