# FamilyPath PRD

Voice-assisted family doctor discovery for newcomers in Canada.

ConHacks 2026. Two-person hackathon demo.

## Goal

FamilyPath helps newcomers find family doctor options without manually checking portals or calling clinics themselves. For the demo, the app uses a scripted multi-agent search flow and real ElevenLabs voice calls to create a believable, interactive experience.

The demo does not use Claude, LangGraph, or nexos.ai. Those are out of scope for this version.

## Demo Promise

User enters:

- Name
- Phone number
- Postal code
- Preferred language
- Insurance type: OHIP, IFHP, UHIP, or waiting period

Then:

- Five source agents appear to search in parallel.
- Results stream live to the dashboard over WebSocket.
- One source fails honestly, so the search feels credible.
- ElevenLabs places an outbound call to the demo clinic phone number.
- The dashboard shows the call/search progression.
- The clinic result has two important user-facing outcomes:
  - Yellow: clinic is accepting waitlist requests.
  - Green: the clinic was called and the user was successfully added to the waitlist.
- ElevenLabs can also call the original user phone number for a real two-way voice interaction.

## Demo Flow

1. User fills the intake form.
2. Backend creates a search and starts the scripted runner.
3. Dashboard opens `/ws/searches/{search_id}`.
4. Five source cards update live:
   - ODHF
   - CPSO
   - Appletree
   - IFHP / Medavie
   - MCI
5. MCI fails with "no clinics within radius."
6. ODHF reaches `calling` and triggers the ElevenLabs clinic call.
7. A clinic can first show as waitlist-open, then progress to user-waitlisted after the call.
8. After the search completes, ElevenLabs can call the user's phone number with the result.

## Architecture

```text
React dashboard
  -> POST /api/searches/start
  -> FastAPI backend
  -> scripted fake_runner
  -> PostgreSQL search/search_results rows
  -> WebSocket status events
  -> ElevenLabs outbound calls
```

No live scraping is required for the demo. No LLM result parsing is required for the demo.

## Current Critical Path

The demo-critical path is:

```text
frontend form
  -> /api/searches/start
  -> run_fake_search(search_id)
  -> hub.broadcast(search_id, event)
  -> dashboard agent cards
  -> place_outbound_call(...)
```

If this path works, the demo works.

## Tech Stack

| Area | Tool |
| --- | --- |
| Frontend | Vite, React, TypeScript |
| Styling | Tailwind CSS, shadcn-style local components |
| Map | MapLibre |
| Backend | FastAPI |
| Database | PostgreSQL |
| ORM | async SQLAlchemy |
| Realtime | WebSocket |
| Voice | ElevenLabs Conversational AI with outbound phone calls |

## API Contract

### Start Search

`POST /api/searches/start`

Request:

```json
{
  "name": "Jane Doe",
  "phone": "+14165550100",
  "postal_code": "L6V 4K2",
  "language": "punjabi",
  "insurance_type": "ifhp"
}
```

Response:

```json
{
  "search_id": "uuid"
}
```

### Live Search Updates

`WS /ws/searches/{search_id}`

Every event must keep this shape:

```json
{
  "source": "odhf",
  "status": "found",
  "clinic_name": "Heart Lake Health Centre",
  "message": "match found - IFHP accepted",
  "updated_at": "2026-04-29T18:23:11.421+00:00"
}
```

Allowed `source` values:

- `odhf`
- `cpso`
- `appletree`
- `ifhp`
- `mci`

Allowed `status` values:

- `pending`
- `searching`
- `found`
- `calling`
- `confirmed`
- `failed`

This WebSocket envelope is frozen. Frontend and backend should not invent another shape.

### Clinic Outcome Semantics

The UI should treat the existing statuses like this:

| WebSocket status | User-facing meaning | Color |
| --- | --- | --- |
| `found` | Clinic is accepting waitlist requests | Yellow |
| `calling` | Calling clinic to add the user to the waitlist | Yellow / in progress |
| `confirmed` | User was successfully added to the waitlist | Green |
| `failed` | No match or unable to add user | Red |

Do not describe `confirmed` as merely "clinic accepts patients." For the demo, `confirmed` means the call succeeded and the user got onto the waitlist.

## Database

Use three tables:

- `providers`: seeded clinic data
- `searches`: one row per user search
- `search_results`: current state for each source in a search

No Alembic is required. The backend creates tables on startup with `Base.metadata.create_all`.

## Voice Behavior

### Clinic Call

When the ODHF source reaches `calling`, the backend calls:

```text
place_outbound_call(
  phone_number=DEMO_PHONE_NUMBER,
  clinic_name="Heart Lake Health Centre",
  insurance_type="ifhp",
  search_id=...,
  source="odhf"
)
```

ElevenLabs should ask the clinic/demo recipient whether they are accepting new IFHP-covered patients.

### User Callback

After the scripted search completes, the backend may call the phone number entered in the form. This should be a patient-facing interaction, not a clinic-facing interaction.

Preferred dynamic variables:

```json
{
  "call_type": "patient_callback",
  "patient_language": "punjabi",
  "confirmed_clinic": "Heart Lake Health Centre",
  "result_message": "Heart Lake Health Centre is accepting new IFHP patients."
}
```

For the demo, the ElevenLabs agent prompt should support both call types:

- Clinic verification call
- Patient result callback

## Supported Languages

Demo languages:

- Punjabi
- Arabic
- Tagalog
- Spanish
- English

Do not claim Somali real-time voice support in the demo.

## Environment Variables

Backend:

```env
DATABASE_URL=postgresql+asyncpg://medbridge:medbridge@localhost:5432/medbridge
ELEVENLABS_API_KEY=
ELEVENLABS_AGENT_ID=
ELEVENLABS_PHONE_NUMBER_ID=
DEMO_PHONE_NUMBER=
```

Frontend:

```env
VITE_ELEVENLABS_AGENT_ID=
```


## Implementation Priorities

### Must Work

- Intake form starts a search.
- WebSocket agent cards update live.
- Scripted runner completes without crashing.
- ODHF triggers the ElevenLabs clinic call.
- User phone number is required if we want a user callback.
- Patient callback uses patient-facing dynamic variables.
- Map/status UI does not show false confirmations before statuses arrive.
- Yellow and green clinic statuses match the waitlist story:
  - Yellow means accepting waitlists.
  - Green means user successfully waitlisted.

### Nice To Have

- Provider API drives map pins instead of hardcoded demo clinics.
- Live call transcript panel.
- Better status colors for map pins.
- Preflight check for missing ElevenLabs config before demo.

## Known Demo Risks

| Risk | Mitigation |
| --- | --- |
| ElevenLabs call fails | Keep scripted dashboard progression as fallback |
| User forgets phone number | Require phone number in the form for callback demos |
| Agent prompt acts like wrong call type | Add `call_type` dynamic variable and prompt branches |
| Map shows misleading state | Bind marker color to live source status |
| Backend DB not running | Start Postgres with Docker Compose before rehearsal |

## Out Of Scope

- Claude transcript parsing
- LangGraph supervisors/workers
- nexos.ai gateway
- Live web scraping
- Mid-search voice interrupts
- Real provider availability verification beyond the demo call

## Success Criteria

The demo is successful if judges see:

- A user-friendly intake flow
- Parallel source cards updating live
- One realistic failed source
- A real ElevenLabs outbound phone call
- A yellow waitlist-open clinic state
- A green user-successfully-waitlisted clinic state
- A real user callback interaction when a phone number is provided

FamilyPath is a voice-first healthcare navigation demo. The goal is not perfect automation. The goal is a clear, working story: a newcomer asks for help, the system searches, calls, and reports back.
