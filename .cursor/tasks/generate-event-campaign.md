# Task: generate-event-campaign

## Objective
Process an event brief, then generate a campaign kit for the event.

## Required inputs
- Event brief (title, date, persona, hook, CTA) or Google Cloud event query + seeded DB

## Inspect
- `core/event_brief/intake.py`
- `process_event_brief` → `generate_campaign_kit`
- Google Cloud finder fixtures if offline

## Expected output
- `READY_FOR_GENERATION` brief or clarification questions
- Campaign kit when ready

## Validation
- Missing fields return `NEEDS_CLARIFICATION` with questions
- Offline tests use seeded reference fixtures
