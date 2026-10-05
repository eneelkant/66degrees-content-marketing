# Content quality, Slack, and Google Drive

Generation stays a draft until a person uses the existing approval gate. Slack and Drive are optional brief fields. They are not extra MCP tools. The public tool list stays at 16.

## Quality pipeline

`generate_content_asset` builds context, generates the draft, then runs `validate_content_quality`. The result keeps five layers separate:

| Layer | Where it lives | What it contains |
|---|---|---|
| Source and reference facts | `source_context.source_facts` | Repository references, the OKF identity excerpt, and Drive text that was read in memory |
| User instructions | `source_context.user_instructions` | Title, audience, hook, takeaways, and CTA from the brief |
| Feedback | `source_context.feedback` | Slack messages. `promoted_to_brand_rule` is false |
| Generated content | `asset` | Draft markdown. Metadata status is `DRAFT` |
| Validation | `quality` | `passed`, `status: DRAFT`, `grants_approval: false`, and a feedback list |

`quality.grants_approval` is always false. `qa_status` remains `GENERATED_DRAFT`. A later `qa_validate_asset` call adds a `content_quality` check for `blog`, `case_study`, `email`, and `event_landing_page`. That check does not approve or export.

Rules come from files already in the repository:

- Brand voice, forbidden jargon, mandatory terminology, and unsupported-claim phrases: `core/brand/brand_rules.json`
- Blog, case study, email, and event landing page structure: the guideline JSON files in `references/`
- Event email lifecycle: `references/event-email-okf-model-generation.md`, `docs/email-content.json`, and `docs/Event Email OKF Model Generation.docx`

The quality pass does not add brand rules. A number or percentage may appear in the draft only when the brief or a source fact already contains it. A number that appears only in Slack feedback is reported as an unsupported claim. The deterministic generator does not copy Slack text into the draft.

Blog drafts from the deterministic scaffold are shorter than the 800-word short-form minimum and do not invent internal URLs. The quality result reports `word_count` and `internal_linking` so a person can revise the draft. It does not pad the draft to hide that gap.

Campaign kits still return `DRAFT_PENDING_QA` with `qa_metadata.approval_gate` set to `LOCKED`. The kit quality block includes `event_email_assessment` for the seven event emails. That assessment does not approve the kit.

## OKF and event email

OKF profiles are unchanged. `validate_okf_content("email")` still uses `references/66degrees_email_content_writing_guideline.json`.

A full seven-stage event sequence is checked with `assess_event_email_sequence`, not with the general email shape. The stages stay:

1. Invitation #1 (`invitation_1`)
2. Invitation #2 (`invitation_2`)
3. Invitation #3 (`invitation_3`)
4. Reminder #1 (`reminder_1`)
5. Reminder #2 (`reminder_2`)
6. Attendee follow-up (`attendee_followup`)
7. Non-attendee follow-up (`non_attendee_followup`)

`generate_event_email_sequence` and the kit `email_campaign` list return those stages in that order. Generated mail status is `draft`. Drive text is attributed context. It is not mined into event-email placeholders. Those emails still use structured brief fields.

## Slack

Retrieval runs only when `brief_data.sources.slack` is an object.

| Field | Behavior |
|---|---|
| `channel` | Channel ID (`C…`, `G…`, or `D…`) or channel name. A name is resolved with `conversations.list`. |
| `thread_ts` or `thread` | Requires `channel`. Uses `conversations.replies`. |
| `keywords` | Every keyword must appear in the message (AND). |
| `oldest` / `since`, `latest` / `until` | Unix timestamp or ISO-8601. |
| `limit` | 1–50. Default 20. |

An empty Slack object, or a thread without a channel, returns `target_required` and does not list the workspace. Messages are stored with `role: feedback`. They do not become brand rules unless someone later puts them in an approved repository reference.

`SLACK_BOT_TOKEN` is optional. When the brief asks for Slack and the token is missing, the status is `credentials_missing` and `items` is empty. The token is read from the environment and is redacted in logs. Do not commit it.

Suggested bot scopes for the targeted reads above: `channels:history`, `channels:read`, `groups:history`, and `groups:read` when private channels are in scope. This server does not post to Slack.

## Google Drive

Retrieval runs only when `brief_data.sources.drive` includes `file_id`, `name`, or `query`.

| Read path | Formats |
|---|---|
| In memory via `files.export` as `text/plain` | Google Docs, Sheets, and Slides |
| In memory via `alt=media` | `text/*`, JSON, and XML |
| Not read | PDF and other binary files. Status is `unsupported_direct_read`. Use the existing download path. |

Excerpts are capped at 8,000 characters. Each item keeps `file_id`, `name`, `mime_type`, `modified_time`, and `web_view_link` when the API returns them. Drive text is a source fact. The draft labels it under `Source facts` and does not treat it as generated copy.

Nothing is written to Drive during generation.

An optional update runs only inside `export_approved_campaign`, after `require_approved`, and only when the kit has `drive_update_request.confirm` set to boolean `true` and a `file_id`. Set that from `brief_data.drive_update` when the kit is created. The update appends a short note through the Google Docs `documents.batchUpdate` `insertText` `endOfSegmentLocation`. It does not replace the document body.

| Destination | Result |
|---|---|
| Google Doc, confirmed, approved, token present | `status: appended`, `written: true` |
| `confirm` is not boolean `true` | No Drive call |
| Export before approval | `PermissionError`. Drive is not called |
| PDF or any non-Google-Doc | `unsupported_direct_edit`, `written: false`. The local JSON, DOCX, or XLSX export is the fallback |
| Missing token | `credentials_missing`, `written: false`. The local export still returns |

`GOOGLE_DRIVE_ACCESS_TOKEN` is optional. Use an OAuth access token. `drive.readonly` covers reads. A confirmed append also needs permission to edit the document (`drive` or `drive.file`) and the Docs API. Do not commit the token. A Drive API failure does not delete the local export file.

## Workflow

```text
Slack / Drive / repository reference
        → retrieve only when the brief asks
        → build source facts, instructions, and feedback
        → generate or revise a draft
        → validate against brand rules and the OKF profile
        → return the draft plus source and validation layers
        → explicit human approval
        → local export
        → optional confirmed append to a Google Doc
```

Source documents are not modified automatically. Formats the Docs API cannot append to keep the local export path.

## Environment variables

Copy `.env.example` to `.env`. Leave these empty unless the brief will request the source:

```text
SLACK_BOT_TOKEN=
GOOGLE_DRIVE_ACCESS_TOKEN=
```

Remote MCP still requires `MCP_AUTH_TOKEN` or `MCP_API_KEY`. CORS stays an explicit allowlist. Do not set `CORS_ALLOWED_ORIGINS=*`.

CI does not need Slack, Drive, or Render credentials. Tests inject fake HTTP transports.

## Security

- Tokens are not written to the repository, to quality feedback, or to logs (`slack_bot_token` and `google_drive_access_token` are redacted).
- Retrieved text is passed through `sanitize_string` before it enters the context.
- Slack and Drive are not queried when the brief omits `sources`.
- Approval and export gates are unchanged. Unapproved export raises `PermissionError` before any Drive write.
