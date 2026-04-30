---
name: Scope decisions that override agent frontmatter and older PRD assumptions
description: User-level scope changes that conflict with the original agent description; follow these, not the frontmatter
type: project
---

Two scope decisions made by the user that override the agent's built-in instructions:

1. **Voice interrupts are OUT OF SCOPE.** The agent description still mentions `POST /api/voice/interrupt` mutating LangGraph state mid-run as a "wow moment" and says "design the supervisor with interrupt support from turn one." Ignore that. Do not build interrupt mutation logic. The existing `api/voice.py` stub (returns `{ok: True}`) can stay. Current PRD §Key Constraints reflects this: "Mid-search voice interrupts are not in scope."

2. **All 5 workers are scripted-demo, not real scrapers.** The agent description and older project notes mention 4 Playwright-based scrapers (CPSO, Appletree, Medavie IFHP, MCI), Browserbase scraper sessions, and Claude Sonnet 4.6 Computer Use fallback (model id `computer-use-2025-11-24`, 10-iteration cap). The current PRD has been rewritten — there is NO live scraping. All 5 workers walk seeded providers through scripted status sequences. No Browserbase, no Computer Use, no Playwright in the supervisor.

Sponsor integrations actually owned by Person 1 in the new architecture: **Anthropic (Claude), nexos.ai, GitHub Actions.** Browserbase is no longer in P1's scope — it's not used at all in the rewritten PRD.

**Why:** PRD was rewritten and the user explicitly told me to drop interrupts. Frontmatter wasn't regenerated.

**How to apply:** When the agent frontmatter and current `prd.md` disagree, current `prd.md` wins. When the user gives an explicit scope instruction in chat, the user wins over both. Re-read `prd.md` at the start of any non-trivial decision.
