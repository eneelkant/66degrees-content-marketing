# Task: generate-campaign

## Objective
Generate a multi-channel campaign kit from a structured brief using the mocked LLM path.

## Required inputs
- Brief JSON with required metadata / audience / value_prop / CTA

## Inspect
- `clients.public_api.generate_campaign_kit`
- `core/generators/campaign_kit.py`
- E2E journey tests

## Expected output
- Kit with landing_page, google_ads, linkedin_ads, email_campaign
- `kit_id` for approval/export

## Validation
- `LLM_PROVIDER=mock`
- Export blocked until `approve_campaign_kit`
