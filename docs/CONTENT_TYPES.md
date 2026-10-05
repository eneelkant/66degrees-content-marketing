# Supported content types

Derived from `core/generators/factory.py`, campaign kit generators, and MCP tools.

## Content factory asset types (`generate_content_asset`)

| Type | Strategy module | Status |
|---|---|---|
| `blog` | `blog_strategist.py` | Supported |
| `case_study` | `case_study_producer.py` | Supported |
| `thought_leadership` | `thought_leadership.py` | Supported |
| `website` | `website_writer.py` | Supported |
| `newsletter` | `newsletter_curator.py` | Supported |
| `whitepaper` | `whitepaper_architect.py` | Supported |
| `video_script` | `video_script.py` | Supported |
| `copywriting` | `copywriter.py` | Supported |

## Campaign kit channels (`generate_campaign_kit` / `create_campaign`)

| Channel asset | Generator | Status |
|---|---|---|
| Landing page copy | `landing_page.py` | Supported |
| Google Ads RSA | `google_ads.py` | Supported |
| LinkedIn ads | `linkedin_ads.py` | Supported |
| Email lifecycle | `email_sequence.py` | Supported. Seven emails: 3 invitations, 2 reminders, attendee follow-up, non-attendee follow-up |

## Social / repurposing

| Workflow | Tool | Notes |
|---|---|---|
| LinkedIn / platform posts | `generate_social_posts` | Uses repurposer; `linkedin` → `linkedin_post` |
| Format conversion | `repurpose_content_asset` | Target formats such as `linkedin_post` |

## OKF writing profiles

Canonical sources live in `references/` and are loaded by `core/okf/`. See `docs/OKF_CONTENT_MODEL.md`.

| `content_type` | Guideline | Used by |
|---|---|---|
| `blog` | `66degrees_blog_content_writing_guideline.json` | `generate_content_asset("blog", …)` |
| `case_study` | `66degrees_case_study_writing_guideline.json` | `generate_content_asset("case_study", …)` |
| `email` | `66degrees_email_content_writing_guideline.json` | `get_okf_profile("email")` and `generate_event_email_sequence` |
| `event_landing_page` | `66degrees_event_landing_page_content_writing_guideline.json` | `get_okf_profile("event_landing_page")` |

Each profile applies the shared 66degrees Google Cloud partner foundation plus that file's structure, tone, SEO, CTA, and dos/don'ts. `validate_okf_content(content_type, draft)` checks those constraints.

Event lifecycle email uses that email profile together with two more sources:

- `docs/Event Email OKF Model Generation.docx` is the procedural source.
- `docs/email-content.json` is the machine-readable lifecycle and campaign source.

The human-readable procedure is `references/event-email-okf-model-generation.md`. A standard event sequence is Invitation #1, Invitation #2, Invitation #3, Reminder #1, Reminder #2, Attendee Follow-Up, and Non-Attendee Follow-Up. `generate_event_email_sequence` returns those seven assets, and the kit stores them on `email_campaign`. Passing format checks does not approve the concept.

## Conceptual mapping (requested workflows)

| Requested workflow | How to run it | Supported? |
|---|---|---|
| Blog article | `generate_content_asset("blog", …)` | Yes |
| Landing-page copy | kit `landing_page` or website strategy | Yes |
| Email | kit `email_campaign` / newsletter | Yes |
| LinkedIn post | `generate_social_posts` / repurpose | Yes |
| Social campaign | `create_campaign` social stage | Yes |
| Event promotion | `process_event_brief` + kit / `create_campaign` | Yes |
| Campaign messaging | strategy + brand rules | Yes |
| Content repurposing | `repurpose_content_asset` | Yes |

## Not claimed

- Direct Salesforce / CMS publish integrations
- Paid media API submission
- Live Google Cloud event scrape during unit tests (requires refreshed `references.db`)
