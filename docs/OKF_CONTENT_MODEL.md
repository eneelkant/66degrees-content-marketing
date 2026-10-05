# 66degrees OKF content model

`references/` holds the canonical content-writing guideline JSON files. The OKF layer in `core/okf/` loads those files and exposes one normalized profile per content type. It does not replace the source documents.

| Content type | Source file |
|---|---|
| `blog` | `references/66degrees_blog_content_writing_guideline.json` |
| `case_study` | `references/66degrees_case_study_writing_guideline.json` |
| `email` | `references/66degrees_email_content_writing_guideline.json` |
| `event_landing_page` | `references/66degrees_event_landing_page_content_writing_guideline.json` |

## Shared brand foundation

`get_okf_model().common_brand` keeps each file's value proposition verbatim. It records 66degrees as a Google Cloud Partner only because every source identity says so, and it lists capabilities such as cloud transformation, data engineering, analytics, and generative AI only when that wording appears in a source value proposition.

Brand voice, audience, and content rules stay on the content-type profile. Email does not define `target_audience`; its profile audience is empty and the email-type list remains in the source JSON.

## Lookup

```python
from core.okf import get_okf_profile, validate_okf_content

profile = get_okf_profile("blog")  # or case_study, email, event_landing_page
result = validate_okf_content("email", draft)
```

`profile.source` is the loaded JSON. `profile.validation` holds character limits, word-count ranges, required fields, CTA rules, and dos/don'ts metadata parsed from that JSON.

`build_generation_context(..., content_type="blog")` attaches the profile to `GenerationContext.okf_profile` when the type is one of the four OKF types. `generate_content_asset` passes its `asset_type` through, so blog and case-study drafts record `okf_content_type` and `okf_source`. Other asset types are unchanged. The public MCP tool list is unchanged.

## Validation

`validate_okf_content` checks title or subject length, meta description or preheader length, word-count range, required sections, CTA presence, and content-type fields from the source guidelines (including quantified case-study results, a single email CTA, and event timezone/format). It returns `valid` and `violations`. It does not approve or export a campaign.

## Event lifecycle email

Event email keeps this profile and adds two sources. Neither source replaces the guideline file.

| Role | Source |
|---|---|
| Procedural model-generation reference | `docs/Event Email OKF Model Generation.docx` |
| Machine-readable lifecycle and campaign reference | `docs/email-content.json` |
| Human-readable procedure | `references/event-email-okf-model-generation.md` |

The standard lifecycle is seven emails: Invitation #1, Invitation #2, Invitation #3, Reminder #1, Reminder #2, Attendee Follow-Up, and Non-Attendee Follow-Up. That is 3 invitations + 2 reminders + 1 attendee follow-up + 1 non-attendee follow-up.

`generate_event_email_sequence` returns those seven assets. The campaign kit stores the same sequence in order on `email_campaign`. Each asset has `lifecycle_stage`, `subject`, `preview_text`, `body`, `cta`, `validation`, and provenance. Generated status is `draft`. Formatting validation does not set `approved` or `active`.

Where the DOCX and `docs/email-content.json` disagree, both rules stay in `source_conflicts()` and in the markdown reference. The general email profile is still what `validate_okf_content("email")` uses. The public MCP tool list is unchanged.
