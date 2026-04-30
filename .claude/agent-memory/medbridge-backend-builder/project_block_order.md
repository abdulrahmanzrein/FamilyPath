---
name: Build order — what's done and what's next
description: Tracks which Person 1 blocks have landed so each turn picks up the right next piece
type: project
---

Person 1 backend block order, per PRD §What We Build (post voice-interrupt-removal):

Done before this conversation:
- DB models, async session, Pydantic schemas, WebSocket hub
- `fake_runner.py` — scripted 5-worker demo flow (this IS the product flow now, not a fallback)
- FastAPI main + lifespan + CORS + healthcheck
- Routes: `api/searches.py`, `api/providers.py`, `api/voice.py` (interrupt stub returning `{ok: True}`)
- ODHF seed loader (`scripts/seed_odhf.py`)
- `config.py` with all env vars

Done this conversation:
1. `app/agents/llm_gateway.py` — nexos.ai PII gateway. **Must precede any Claude call site** per PRD §Key Constraints.

Remaining (suggested order, adjust as needed):
2. ElevenLabs outbound call trigger module — POSTs to ElevenLabs Conversational AI with `{phone_number, agent_id, dynamic_variables}`. Probably `app/agents/voice_caller.py` or similar.
3. End-of-call webhook route — receives ElevenLabs payload, runs transcript through `llm_gateway.complete()` for yes/no extraction, updates `search_results.confirmed_accepting`, broadcasts terminal event. First Claude call site — depends on (1).
4. LangGraph supervisor + 5 scripted-demo worker subgraphs (`supervisor.py`, `graph.py`). Replaces `fake_runner` as entry point from `/api/searches/start`. Triggers (2) when designated worker (one with `DEMO_PHONE_NUMBER`) hits `found`.
5. `.github/workflows/nightly-scrape.yml` — sponsor wiring; meaningful cron (re-seed or refresh `last_scraped_at`).
6. Cleanup: delete empty `backend/scripts/seed_odfh.py` typo file.

Voice interrupts are OUT OF SCOPE per user instruction (overrides PRD §Agent Design / agent frontmatter).

**Why:** The user works in one-block-per-turn loops and commits/pushes between blocks. This file lets future-me pick up at the right step without re-deriving from scratch.

**How to apply:** At the start of each turn, read this file plus current repo state. Verify what's actually committed before assuming a block is done. Update this file as blocks land.
