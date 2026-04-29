# MedBridge PRD
> Voice-controlled multi-agent family doctor finder for newcomers to Canada  
> ConHacks 2026 · 2 people · 36 hours

---

## Problem

6.5 million Canadians have no family doctor. Newcomers are hit hardest — they land in Brampton and Scarborough where supply is worst, don't know which portals to check, can't always make calls in English, and some (refugees, asylum seekers) have IFHP coverage that many clinics don't even know they accept.

Finding a doctor means checking 5+ disconnected portals, calling clinics in a language you may not speak fluently, and repeating this for weeks. No tool does this automatically. We build that tool.

---

## What It Does

User enters: postal code, preferred language, insurance type (OHIP / IFHP / UHIP / waiting period).

Six parallel AI agents fan out across clinic networks and provider directories simultaneously. Results stream live to a dashboard. When a strong match is found, a voice agent calls the clinic in English to verify they are accepting new patients — and reports back to the user in their own language (Punjabi, Arabic, Tagalog, Spanish).

---

## Demo Flow (3 minutes)

| # | Action | What judges see |
|---|---|---|
| 1 | Say: *"Find me a doctor in Brampton, Punjabi, IFHP"* | Supervisor initializes, 6 agent cards light up |
| 2 | Agents fan out | Dashboard fills with clinic cards — red / green / grey |
| 3 | Voice call placed live | ElevenLabs dials a real clinic. Judges hear English call. Transcript streams. |
| 4 | Card confirms green | *"Yes, we accept IFHP."* Card flips confirmed. |
| 5 | Voice interrupt | Say: *"Skip MCI, prioritize Appletree"* — agents reprioritize visibly |
| 6 | Result delivered | App speaks confirmed result back to user in Punjabi |
| 7 | Sponsor slide | Call out all 8 integrations |
| 8 | Close | *"A refugee used to spend weeks on this. We did it in 90 seconds. Free. Open source."* |

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
      ├─── Worker 1 (ODHF)
      ├─── Worker 2 (CPSO)        ──► Browserbase + Playwright
      ├─── Worker 3 (Appletree)        (stealth cloud browsers)
      ├─── Worker 4 (IFHP)                    │
      └─── Worker 5 (MCI)                     ▼
                                    Claude Sonnet 4.6
      │                             (vision + extraction)
      ▼
ElevenLabs Voice Agent (Flash v2.5)
      │
      ▼
Twilio (outbound calls to clinics)
      │
      ▼
PostgreSQL (providers, searches, results)
```

**nexos.ai** wraps all Claude calls — PII is stripped before any patient data touches an LLM.

---

## Tech Stack

| Layer | Tool |
|---|---|
| Backend | Python 3.12, FastAPI, PostgreSQL |
| Agent orchestration | LangGraph (supervisor + worker pattern) |
| Browser automation | Browserbase + Playwright |
| AI extraction | Claude Sonnet 4.6 with Computer Use (`computer-use-2025-11-24`) |
| Voice in/out | ElevenLabs Conversational AI (Flash v2.5) |
| Outbound calling | ElevenLabs + Twilio |
| PII protection | nexos.ai gateway |
| Frontend | React (scaffolded via Lovable) |
| Real-time | WebSocket |
| Remote trigger | NordVPN Meshnet |
| QA | Scout (URL substitution on dashboard) |
| Scheduled re-checks | GitHub Actions cron (nightly provider refresh) |

---

## Data Sources

### Use these

| Source | Data we get | Access method |
|---|---|---|
| **Statistics Canada ODHF** | 7,000 Canadian clinic locations with lat/lng and address | Free CSV — `statcan.gc.ca/en/lode/databases/odhf` — download on Day 0, seed into Postgres |
| **CPSO Physician Register** | All 40,000+ licensed Ontario physicians, searchable by language + specialty + postal code | Browserbase scraper — `register.cpso.on.ca` — loop: postal FSA × language × Family Medicine |
| **Appletree Medical Group** | Doctor name, languages spoken, walk-in vs roster status, IFHP/UHIP acceptance, accepting-new-patients flag | Playwright scraper — static HTML, predictable URL: `/clinic-locations/<slug>/` |
| **Medavie IFHP Provider Search** | Federal refugee health program directory — GPs, specialists, pharmacies near a postal code | Browserbase — `ifhp.medaviebc.ca/en/providers-search` — JS-rendered, loop: FSA × provider type |
| **MCI The Doctor's Office** | Per-clinic doctor lists, some accepting-new-patients flags | Playwright scraper — `mcithedoctorsoffice.ca` |

### Enrich-only (do not drive search from these)

| Source | Why limited |
|---|---|
| **RateMDs** | Scrapable but "accepting new patients" is sparsely populated — use only for ratings/languages |
| **Ontario Health Teams** | Geographic boundary data only — physician rosters are not public |

### Do not use

| Source | Why |
|---|---|
| **Health Care Connect** | Requires a real OHIP card, returns nothing synchronously — it's a waitlist queue, not a search tool |
| **Jack Nathan Health** | Defunct — sold to WELL Health December 2024 |

---

## Agent Design

### Supervisor agent
- Receives user input from FastAPI
- Queries `providers` table for seed candidates
- Assigns one data source per worker
- Monitors worker `report_status` tool calls
- Pushes events to WebSocket → dashboard
- Handles voice interrupts via `/api/voice/interrupt` → updates LangGraph state mid-run

### Worker agents (×5, parallel)
Each worker:
1. Opens a Browserbase browser session
2. Navigates to assigned data source
3. Searches by postal code + language + specialty
4. Extracts: clinic name, address, phone, doctor name, languages, IFHP acceptance, accepting-new-patients flag
5. Calls `report_status` tool → supervisor → WebSocket → dashboard card updates

If a page can't be parsed by Playwright, the worker falls back to Claude Computer Use (screenshot → action loop, max 10 iterations).

### Voice agent
- Separate async process, subscribes to WebSocket events
- For unverified clinics: places outbound call via Twilio
- Speaks English to receptionist: *"Are you currently accepting new IFHP-covered patients for family medicine?"*
- Transcribes response → Claude extracts yes/no
- Updates dashboard with confirmed status
- Reports result to user in their chosen language

**Supported languages (ElevenLabs Flash v2.5):** Punjabi ✅ Arabic ✅ Tagalog ✅ Spanish ✅  
**Somali:** ❌ Flash v2.5 does not support Somali in real-time — fall back to Arabic or English

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/searches/start` | Start search. Body: `{ name, postal_code, language, insurance_type }`. Returns `search_id`. |
| `GET` | `/api/searches/{id}/status` | Agent statuses: `pending / searching / found / calling / confirmed / failed` |
| `WS` | `/ws/searches/{id}` | Live stream: `{ source, clinic_name, status, message, timestamp }` |
| `POST` | `/api/voice/interrupt` | ElevenLabs tool call target. Body: `{ action, source }`. Mutates LangGraph state. |
| `GET` | `/api/searches/{id}/results` | Final output: `{ confirmed: [], calling: [], failed: [] }` |
| `GET` | `/api/providers` | Provider lookup by postal code + language + insurance type |

---

## Database Schema

### `providers`
```sql
provider_id          UUID PRIMARY KEY
clinic_name          VARCHAR
doctor_name          VARCHAR         -- nullable for clinic-level records
address              VARCHAR
city                 VARCHAR
postal_code          VARCHAR
lat                  FLOAT
lng                  FLOAT
phone                VARCHAR
languages            TEXT[]          -- e.g. ["Punjabi", "English"]
accepts_ifhp         BOOLEAN
accepts_ohip         BOOLEAN
accepting_new_patients BOOLEAN       -- NULL = unknown, scrape to confirm
source               VARCHAR        -- odhf | cpso | appletree | mci | ifhp
last_scraped_at      TIMESTAMP
```

### `searches`
```sql
search_id       UUID PRIMARY KEY
user_name       VARCHAR             -- PII — nexos.ai strips before LLM calls
postal_code     VARCHAR
language        VARCHAR
insurance_type  VARCHAR             -- ohip | ifhp | uhip | waiting_period
status          VARCHAR             -- pending | running | completed | failed
created_at      TIMESTAMP
completed_at    TIMESTAMP
```

### `search_results`
```sql
result_id            UUID PRIMARY KEY
search_id            UUID REFERENCES searches
provider_id          UUID REFERENCES providers
agent_status         VARCHAR        -- pending | searching | found | calling | confirmed | failed
call_transcript      TEXT           -- nullable
confirmed_accepting  BOOLEAN        -- nullable, set after voice call
updated_at           TIMESTAMP
```

---

## What We Build

### Person 1 — Backend / Agents

**Core infrastructure**
- [ ] FastAPI server with all endpoints above
- [ ] PostgreSQL with schema above
- [ ] ODHF CSV ingested as seed data on startup
- [ ] nexos.ai PII gateway wrapping all Claude calls
- [ ] WebSocket broadcaster pushing live status events

**Scrapers**
- [ ] Scraper: CPSO — loop postal FSA × language × Family Medicine
- [ ] Scraper: Appletree clinic pages — doctor name, languages, accepting status
- [ ] Scraper: Medavie IFHP — loop postal FSA × provider type
- [ ] Scraper: MCI clinic pages
- [ ] Unified `providers` table with provenance flags per row

**Agent orchestration**
- [ ] LangGraph supervisor agent
- [ ] 5 LangGraph worker agents (one per data source)
- [ ] Claude Computer Use fallback loop (max 10 iterations per page)
- [ ] `/api/voice/interrupt` endpoint — receives ElevenLabs tool call, mutates LangGraph state

**Sponsor integrations (P1)**
- [ ] **Browserbase** — stealth browser sessions for all scrapers
- [ ] **Claude / Anthropic** — Computer Use fallback + transcript parsing + extraction
- [ ] **nexos.ai** — PII gateway on every LLM call
- [ ] **GitHub Actions** — nightly scraper cron job

---

### Person 2 — Frontend / Voice

**Voice layer**
- [ ] ElevenLabs agent configured with Flash v2.5, multilingual enabled
- [ ] Twilio phone number purchased and linked to ElevenLabs agent
- [ ] Outbound call flow: dial clinic → ask acceptance question in English → extract yes/no → update dashboard
- [ ] Result delivered back to user in their chosen language (Punjabi / Arabic / Tagalog / Spanish)
- [ ] Voice interrupt: user speaks mid-run → hits `/api/voice/interrupt` → agents reprioritize

**Frontend (via Lovable)**
- [ ] Onboarding form: postal code, language preference, insurance type
- [ ] Live dashboard: one card per agent with animated status (searching / found / calling / confirmed / failed)
- [ ] Map view: clinic pins colored by status
- [ ] Clinic card detail: doctor name, languages, IFHP status, phone, address
- [ ] Live call transcript panel (streams what the agent said and what the receptionist said)
- [ ] Confirmed match card with one-tap "Call this clinic" button
- [ ] WebSocket consumer: connect to `/ws/searches/{id}`, update cards on every event

**Sponsor integrations (P2)**
- [ ] **ElevenLabs** — voice input, outbound calls, multilingual response to user
- [ ] **NordVPN Meshnet** — remote trigger from phone to laptop
- [ ] **Lovable** — React dashboard scaffold
- [ ] **Scout** — URL substitution QA pass on dashboard

**Demo prep**
- [ ] Full 3-minute demo rehearsed minimum 3 times
- [ ] Backup call recording ready if live call fails on stage
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
BROWSERBASE_API_KEY=
BROWSERBASE_PROJECT_ID=
NEXOS_API_KEY=
DATABASE_URL=postgresql://user:pass@localhost:5432/medbridge
```

---


## Risk Register

| Risk | Mitigation |
|---|---|
| Clinic website changes structure | Claude Computer Use fallback handles layout changes — Playwright is primary, CU is the safety net |
| Voice call goes to voicemail | Detect silence/beep pattern → mark as "unverified" → retry once → show "call required" |
| Receptionist unhelpful | Agent rephrases once; if still refused → marks "manual follow-up needed" |
| Somali user in demo | Explain Flash v2.5 limitation → fall back to English → note as roadmap item |
| Hackathon WiFi blocks Twilio | Hotspot fallback; demo Meshnet with diagram if ports blocked |
| Live call fails on stage | Pre-record backup call audio; show transcript replay as fallback |
| Browserbase rate limit | Developer plan gives 25 concurrent — well above 5 agents; queue if needed |
| ElevenLabs quota hit | Creator plan enables usage-based billing — no hard cutoff |

---

## Key Constraints

- **CPSO does not publish accepting-new-patients status** — this gap is exactly why the voice call exists
- **ElevenLabs Flash v2.5 does not support Somali real-time** — use Arabic/English fallback
- **Health Care Connect is not automatable** — requires a real OHIP card, do not attempt
- **nexos.ai must wrap every Claude call** — patient name/address must never reach Claude raw
- **Browserbase Developer is required** — free tier (1 concurrent browser) is insufficient for 5 parallel agents

---

*MedBridge — ConHacks 2026*
