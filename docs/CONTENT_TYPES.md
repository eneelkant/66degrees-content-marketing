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
| Email lifecycle | `email_sequence.py` | Supported |

## Social / repurposing

| Workflow | Tool | Notes |
|---|---|---|
| LinkedIn / platform posts | `generate_social_posts` | Uses repurposer; `linkedin` → `linkedin_post` |
| Format conversion | `repurpose_content_asset` | Target formats such as `linkedin_post` |

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
