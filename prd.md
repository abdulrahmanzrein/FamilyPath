# MedBridge PRD
> Voice-controlled multi-agent family doctor finder for newcomers to Canada
> ConHacks 2026 · 2 people · 36 hours

---

## Problem

6.5 million Canadians have no family doctor. Newcomers are hit hardest — they land in Brampton and Scarborough where supply is worst, don't know which portals to check, can't always make calls in English, and some (refugees, asylum seekers) have IFHP coverage that many clinics don't even know they accept.

Finding a doctor today means checking 5+ disconnected portals, calling clinics in a language you may not speak fluently, and repeating this for weeks. No tool does this automatically. We build that tool.

---

## What It Does

User enters: postal code, preferred language, insurance type (OHIP / IFHP / UHIP / waiting period).

**Five parallel AI agents** work simultaneously across a curated network of Brampton and Scarborough clinics. Results stream live to a dashboard. When an available clinic is found, a voice agent calls to confirm acceptance — and reports back to the user in their own language (Punjabi, Arabic, Tagalog, Spanish).

---

## Demo Flow (3 minutes)

| # | Action | What judges see |
|---|---|---|
| 1 | Say: *"Find me a doctor in Brampton, Punjabi, IFHP"* | Supervisor initializes; 5 agent cards light up |
| 2 | Agents fan out | Dashboard fills with clinic cards — colored by status |
| 3 | MCI card flips red early | *"No MCI clinics within radius"* — one honest failure makes the rest credible |
| 4 | Voice call placed live | ElevenLabs dials the clinic number. Judges hear English call. Transcript streams. |
| 5 | Card confirms green | *"Yes, we accept IFHP."* Card flips confirmed. |
| 6 | **Voice interrupt** | Say: *"Skip CPSO, prioritize Appletree"* — CPSO card greys out, Appletree visibly accelerates |
| 7 | Result delivered | App speaks confirmed result back to user in Punjabi |
| 8 | Sponsor slide | Call out all 8 integrations |
| 9 | Close | *"A refugee used to spend weeks on this. We did it in 90 seconds. Free. Open source."* |

**Why "skip CPSO":** The CPSO worker is scripted to be the slowest — it will still be in `searching` state when the voice interrupt fires ~10–12 seconds in, so the cancel is visually meaningful. Skipping a worker that's already finished would be a no-op on stage.

---

## Architecture

```
User (voice/form)
      │
      ▼
React Dashboard  ◄──── WebSocket (live status events)
      │
      ▼
FastAPI Server
      │
      ▼
LangGraph Supervisor Agent
      │
      ├─── Worker 1 (ODHF)        ──► seeded provider data
      ├─── Worker 2 (CPSO)        ──► scripted demo flow
      ├─── Worker 3 (Appletree)   ──► scripted demo flow
      ├─── Worker 4 (IFHP)        ──► scripted demo flow
      └─── Worker 5 (MCI)         ──► scripted demo flow
      │
      │ (in-process async call — not a WS subscription)
      ▼
ElevenLabs Voice Agent (Flash v2.5)
      │
      ▼
Twilio (outbound call to clinic, initiated by ElevenLabs)
      │
      ▼
PostgreSQL (providers · searches · search_results)
```

**nexos.ai** wraps every Claude call. `user_name` and any free-text user fields are stripped before any patient data touches an LLM. Postal code is FSA-level (e.g. `M5V`) and is allowed through.

---

## Tech Stack

| Layer | Tool |
|---|---|
| Backend | Python 3.12, FastAPI, async SQLAlchemy 2.0, asyncpg |
| HTTP client (sponsor APIs) | httpx |
| Agent orchestration | LangGraph (supervisor + worker pattern, with `interrupt`-able state) |
| Call transcript parsing | Claude Sonnet 4.6 (via nexos.ai) |
| Voice in/out | ElevenLabs Conversational AI (Flash v2.5) |
| Outbound calling | ElevenLabs Twilio integration (ElevenLabs initiates the call) |
| PII protection | nexos.ai gateway |
| Database | PostgreSQL 16 (Docker Compose) |
| Frontend | Vite + React + TypeScript (scaffolded via Lovable) |
| Styling | Tailwind CSS + shadcn/ui (Radix-based, copied into source) |
| Animations | Framer Motion (layout transitions, springs, gesture motion) |
| Visual polish | Aceternity UI / Magic UI (cursor spotlight, animated gradients, beam effects) |
| Icons | lucide-react |
| Toasts | sonner (shadcn-native) |
| Map view | react-map-gl + Mapbox (clinic pins) |
| Data fetching | @tanstack/react-query |
| Real-time | WebSocket |
| Remote trigger | NordVPN Meshnet |
| QA | Scout (URL substitution on dashboard) |
| Scheduled re-checks | GitHub Actions cron (nightly provider refresh) |

---

## Data Sources

### Seeded clinic data — ODHF

| Source | Slug | Data | Method |
|---|---|---|---|
| **Statistics Canada ODHF** | `odhf` | ~10 hardcoded Brampton/Scarborough clinics with real names, addresses, and lat/lng | Hardcoded JSON in `scripts/seed_odhf.py`, seeded into `providers` at startup. One clinic uses `DEMO_PHONE_NUMBER` for the live call. |

All 5 LangGraph worker agents are assigned providers from this seeded data. No live web scraping occurs — workers walk their assigned provider through a scripted status sequence.

---

## Agent Design

### Supervisor agent (LangGraph)

- Receives `SearchStartRequest` from FastAPI
- Spawns 5 worker subgraphs in parallel
- Receives `report_status` tool calls from workers
- For each event: writes/updates the matching `search_results` row, then `hub.broadcast(search_id, event)` pushes to all dashboards subscribed to that search
- Calls the voice agent **in-process** (asyncio task) when a worker reports `found` and the clinic is unverified
- Mutates state on `/api/voice/interrupt`:
  - `action=skip` — cancels that worker's pending tool calls
  - `action=prioritize` — boosts that worker's poll/scroll budget so it finishes sooner
  - `action=cancel` — aborts the whole search

### Worker agents (×5, parallel)

Each worker is assigned one seeded provider and walks it through a scripted status sequence. All workers speak the same `report_status` tool protocol:

1. Receive a `Provider` record from the supervisor (queried from seeded DB data)
2. Walk through scripted steps with realistic delays: `pending → searching → found` (or `failed` for most workers)
3. Call `report_status({ source, status, clinic_name, message })` after each step — supervisor writes the DB row and broadcasts via the hub
4. One designated worker (the provider with `DEMO_PHONE_NUMBER` set) proceeds to `calling` and the supervisor triggers the ElevenLabs outbound call

**Max steps per worker:** 10 (budget constraint on the scripted sequence).

### Voice agent

- **Trigger:** Supervisor invokes the voice agent via async function call. Not a separate WebSocket subscriber — the WS hub broadcasts outward to dashboards only.
- **Call placement:** Backend POSTs to ElevenLabs Conversational AI API with `{ phone_number, agent_id, dynamic_variables: { clinic_name, insurance_type } }`. ElevenLabs initiates the Twilio call.
- **Script (English, hardcoded):** *"Are you currently accepting new IFHP-covered patients for family medicine?"*
- **Live transcript:** ElevenLabs streams transcript chunks to a backend webhook → backend pushes to the WebSocket → dashboard transcript panel updates live.
- **Result extraction:** End-of-call webhook → Claude (via nexos.ai) extracts yes/no/unknown → updates `search_results.confirmed_accepting` → broadcasts `confirmed` or `failed`.
- **Result delivery:** Spoken back to user in their chosen language via ElevenLabs Flash v2.5.

**Supported languages (Flash v2.5 real-time):** Punjabi · Arabic · Tagalog · Spanish
**Somali:** not supported by Flash v2.5 in real-time — fall back to Arabic or English. Never claim Somali support in code or UI copy.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/searches/start` | Body: `{ name, postal_code, language, insurance_type }`. Returns `{ search_id }`. |
| `GET` | `/api/searches/{id}/status` | Returns `{ search_id, overall_status, agents: AgentStatus[] }`. Polling fallback for the WS. |
| `WS` | `/ws/searches/{id}` | Live event stream — envelope below. |
| `POST` | `/api/voice/interrupt` | ElevenLabs tool-call target. Body: `{ action, source? }`. `source` is required for `skip`/`prioritize`, optional for `cancel`. |
| `GET` | `/api/searches/{id}/results` | Final output: `{ confirmed: AgentStatus[], calling: AgentStatus[], failed: AgentStatus[] }` |
| `GET` | `/api/providers` | Provider lookup by postal code + language + insurance type |

### WebSocket event envelope (frozen contract)

Every event broadcast through `hub.broadcast()` matches the `AgentStatus` Pydantic schema:

```json
{
  "source": "cpso",
  "status": "found",
  "clinic_name": "Heart Lake Clinic",
  "message": "match found — 3 GPs accepting new patients",
  "updated_at": "2026-04-29T18:23:11.421+00:00"
}
```

**Allowed values:**
- `source`: `odhf | cpso | appletree | mci | ifhp`
- `status`: `pending | searching | found | calling | confirmed | failed`

This envelope is the integration contract between supervisor, `fake_runner`, and the dashboard. Do not invent a different shape anywhere.

---

## Database Schema

Created via `Base.metadata.create_all` on app startup. **No Alembic** — schema is small and stable; migrations cost more than they save here.

### `providers`
```
provider_id            UUID PRIMARY KEY
clinic_name            VARCHAR
doctor_name            VARCHAR        -- nullable for clinic-level records
address                VARCHAR        -- nullable
city                   VARCHAR        -- nullable
postal_code            VARCHAR        -- nullable
lat                    FLOAT          -- nullable
lng                    FLOAT          -- nullable
phone                  VARCHAR        -- nullable
languages              TEXT[]         -- e.g. ["Punjabi", "English"]
accepts_ifhp           BOOLEAN        -- nullable
accepts_ohip           BOOLEAN        -- nullable
accepting_new_patients BOOLEAN        -- NULL = unknown, voice call confirms
source                 VARCHAR        -- odhf | cpso | appletree | mci | ifhp
last_scraped_at        TIMESTAMP      -- nullable
```

### `searches`
```
search_id      UUID PRIMARY KEY
user_name      VARCHAR              -- PII — nexos.ai strips before LLM calls
postal_code    VARCHAR
language       VARCHAR
insurance_type VARCHAR              -- ohip | ifhp | uhip | waiting_period
status         VARCHAR              -- pending | running | completed | failed
created_at     TIMESTAMP
completed_at   TIMESTAMP            -- nullable
```

### `search_results`
```
result_id           UUID PRIMARY KEY
search_id           UUID REFERENCES searches
provider_id         UUID REFERENCES providers   -- nullable until matched
agent_status        VARCHAR        -- pending | searching | found | calling | confirmed | failed
call_transcript     TEXT           -- nullable
confirmed_accepting BOOLEAN        -- nullable, set after voice call
source              VARCHAR        -- which agent reported this row
clinic_name         VARCHAR        -- denormalized for dashboard render speed
updated_at          TIMESTAMP
```

`source` and `clinic_name` are denormalized onto `search_results` so the dashboard doesn't have to JOIN `providers` on every WS event. The `search_results` row is the source of truth for the agent's *current* state; `providers` is the source of truth for the *clinic's* facts.

---

## What We Build

Items marked `[x]` are already in the repo on `backend/agents` branch.

### Person 1 — Backend / Agents

**Core infrastructure**
- [x] Postgres schema + async SQLAlchemy models (`db/models.py`)
- [x] Async session + `get_session` FastAPI dependency
- [x] Pydantic schemas for all routes (`schemas/searches.py`, `schemas/providers.py`, `schemas/voice.py`)
- [x] WebSocket hub (`ws/hub.py`)
- [x] `fake_runner` — scripted 5-worker demo runner (this IS the product flow, not a fallback)
- [x] FastAPI app entry (`app/main.py`) — lifespan hook, CORS, healthcheck
- [ ] Routes: `api/searches.py`, `api/providers.py`, `api/voice.py`
- [ ] ODHF seed loader — hardcoded ~10 Brampton/Scarborough clinics with real names/addresses/lat/lng; one clinic uses `DEMO_PHONE_NUMBER`
- [ ] nexos.ai PII gateway wrapping every Claude call. Build this *before* the first Claude call lands.

**Agent orchestration**
- [ ] LangGraph supervisor with 5 scripted-demo worker subgraphs and interrupt-able state via the LangGraph checkpointer
- [ ] `/api/voice/interrupt` endpoint — mutates running supervisor graph state mid-run (the demo wow-moment)

**Sponsor integrations (P1)**
- [ ] **Claude / Anthropic** — call transcript parsing + yes/no extraction via nexos.ai
- [ ] **nexos.ai** — PII gateway on every LLM call
- [ ] **GitHub Actions** — nightly clinic data refresh cron (`.github/workflows/nightly-scrape.yml`)

---

### Person 2 — Frontend / Voice

**Voice layer**
- [ ] ElevenLabs agent configured with Flash v2.5, multilingual enabled
- [ ] Twilio phone number purchased and linked to ElevenLabs agent
- [ ] Outbound call flow: ElevenLabs dials clinic → asks acceptance question in English → extracts yes/no → updates dashboard
- [ ] Result delivered back to user in their chosen language (Punjabi / Arabic / Tagalog / Spanish)
- [ ] Voice interrupt: user speaks mid-run → ElevenLabs tool call hits `/api/voice/interrupt` → agents reprioritize

**Frontend stack setup (first 90 minutes — do this before any feature code)**

The stack is chosen to avoid the "AI-generated default" look. Goal: dark muted backgrounds, animated gradients, cursor-following spotlight on hero, smooth layout transitions when agent cards reorder.

- [ ] Scaffold Vite + React + TypeScript via Lovable (or `npm create vite@latest frontend -- --template react-ts`)
- [ ] Install Tailwind CSS, run `npx shadcn@latest init` — copies Radix-based components into `src/components/ui/` (you own them, edit freely)
- [ ] Install: `framer-motion`, `lucide-react`, `sonner`, `@tanstack/react-query`
- [ ] Install map: `react-map-gl` + `mapbox-gl` (Mapbox free tier covers hackathon)
- [ ] Pick one Aceternity UI or Magic UI component for landing page hero (spotlight/cursor-follow or animated gradient) — copy-paste from `ui.aceternity.com` or `magicui.design`, no install needed
- [ ] Establish design tokens: stick to shadcn's `bg-background`, `text-foreground`, `border-border` — no custom hex codes; this keeps every screen coherent automatically

**What NOT to use:** MUI / Material UI / Ant Design / Chakra (recognizable "library look"); Next.js (SSR overhead we don't need); custom CSS from scratch (too slow under time pressure).

**Frontend (via Lovable)**
- [ ] Onboarding form: postal code, language preference, insurance type — shadcn `Form` + `Input` + `Select`
- [ ] Live dashboard: one card per agent with animated status — shadcn `Card` + Framer Motion `layout` prop so cards reorder smoothly when one resolves before another
- [ ] Map view: clinic pins colored by status — react-map-gl + Mapbox dark style
- [ ] Clinic card detail: doctor name, languages, IFHP status, phone, address
- [ ] Live call transcript panel (streams what the agent said and what the receptionist said)
- [ ] Confirmed match card with one-tap "Call this clinic" button
- [ ] WebSocket consumer: connect to `/ws/searches/{id}`, update cards on every event
- [ ] Toast notifications via `sonner` for status pop-ups ("Found 3 clinics", "Calling Appletree…")

**Sponsor integrations (P2)**
- [ ] **ElevenLabs** — voice input, outbound calls, multilingual response to user
- [ ] **NordVPN Meshnet** — remote trigger from phone to laptop
- [ ] **Lovable** — React dashboard scaffold
- [ ] **Scout** — URL substitution QA pass on dashboard

**Demo prep**
- [ ] Full 3-minute demo rehearsed minimum 3 times
- [ ] Backup call recording captured **before hour 24**, not the night before
- [ ] Demo target clinic locked by hour 24; Twilio rehearsal call placed to confirm number is reachable
- [ ] Devpost submission written and submitted before deadline

---

## Environment Variables

```env
ANTHROPIC_API_KEY=
ELEVENLABS_API_KEY=
ELEVENLABS_AGENT_ID=
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=
DEMO_PHONE_NUMBER=            # team's phone number — the "clinic" ElevenLabs dials in the demo
ELEVENLABS_PHONE_NUMBER_ID=  # ElevenLabs phone number ID for outbound calls
NEXOS_API_KEY=
BYPASS_NEXOS=false           # emergency direct-Claude fallback if nexos.ai is down
DATABASE_URL=postgresql+asyncpg://medbridge:medbridge@localhost:5432/medbridge
```

Async driver prefix `postgresql+asyncpg://` is required — SQLAlchemy uses it to pick the asyncpg driver.

---

## Risk Register

| Risk | Mitigation |
|---|---|
| **LangGraph graph unstable by hour 30** | `fake_runner` is the on-stage fallback. WS event contract is identical; the `/api/searches/start` route can swap to `run_fake_search` with no other changes. |
| Voice call goes to voicemail | Detect silence/beep pattern → mark "unverified" → retry once → show "call required" |
| Receptionist unhelpful | Agent rephrases once; if still refused → marks "manual follow-up needed" |
| Somali user in demo | Explain Flash v2.5 limitation → fall back to English → note as roadmap item |
| Hackathon WiFi blocks Twilio | Hotspot fallback; demo Meshnet with diagram if ports blocked |
| Live call fails on stage | Pre-recorded backup call audio (captured by hour 24); show transcript replay as fallback |
| **Demo phone goes unanswered on stage** | Team member on standby to answer as receptionist; pre-record backup audio by hour 24 |
| ElevenLabs quota hit | Creator plan enables usage-based billing — no hard cutoff |
| **nexos.ai gateway down mid-demo** | `BYPASS_NEXOS=true` env flag short-circuits to direct Claude. PII risk is noted; demo trumps. |

---

## Key Constraints

- **ElevenLabs Flash v2.5 does not support Somali real-time** — Arabic/English fallback only. Never claim Somali support in code or UI copy.
- **nexos.ai must wrap every Claude call** — `user_name` and any free-text user fields are stripped before the request leaves the gateway. Postal code is FSA-level (e.g. `M5V`) and is allowed through. Build the wrapper before the first Claude call lands.
- **WebSocket event envelope is frozen:** `{ source, status, clinic_name, message, updated_at }`. Same shape across supervisor, `fake_runner`, and the dashboard. Do not invent a different envelope.
- **One demo path that works > a configurable system that mostly works.** This is 36 hours, not a production codebase.

---

*MedBridge — ConHacks 2026*
