# Event email OKF model generation

This note is the human-readable procedure for event lifecycle email. It is derived from the procedural source and it points at the machine-readable campaign source. Neither source is removed or replaced.

## Sources

| Role | Path |
|---|---|
| Procedural source | `docs/Event Email OKF Model Generation.docx` |
| Machine-readable campaign and email source | `docs/email-content.json` |
| General email OKF profile, unchanged | `references/66degrees_email_content_writing_guideline.json` |
| Shared brand model | `core/brand/brand_rules.json` |

`docs/Event Email OKF Model Generation.docx` is the procedural source.

`docs/email-content.json` is the machine-readable campaign and email source.

The DOCX describes an OKF directory (`_schema/campaign.schema.json`, `_schema/email.schema.json`, `index.md`, `log.md`, and campaign markdown paths such as `campaigns/sports/sf-giants.md`). Those paths are the DOCX architecture. They are not files in this repository, and this procedure does not invent them. The machine-readable concepts that are actually in the repo live in `docs/email-content.json`.

## Purpose

Turn an event brief into one Lifecycle Email Campaign concept with a fixed seven-email sequence. Generation uses:

1. the shared 66degrees brand model
2. the general email OKF profile
3. the procedural rules in the DOCX
4. lifecycle facts supplied on the brief, checked against `docs/email-content.json`

Approved examples in `docs/email-content.json` are evaluation fixtures. The generator does not copy their venues, statistics, or sentences into a new event.

## OKF model-generation workflow

1. Ingest the event brief. Keep only facts the brief supplies. Missing date, venue, time, contact, industry, or event name stay as `[DATE]`, `[VENUE]`, `[TIME]`, `[CONTACT]`, `[INDUSTRY]`, or `[EVENT]`. A registration target stays `[LINK]`. A venue value that already contains `[AV]` is preserved.
2. Build one concept of type `Lifecycle Email Campaign`.
3. Write the seven emails in lifecycle order. Do not emit Registration Confirmation. The DOCX also describes that extra stage; see Conflicts.
4. Apply the stage intent so invitation 2 is not a rewrite of invitation 1, invitation 3 is not a rewrite of invitation 2, reminders carry logistics rather than the invitation argument, and the two follow-ups are different.
5. Check subject, preview, body, CTA, links, spam language, and governance fields. Record every source check. Do not collapse a disagreement into one silent threshold.
6. Set `status` to `draft` and `verified` to an empty list. Formatting success does not set `approved` or `active`.
7. A human verification record is required before a concept can be approved or active. The DOCX cites sign-off names in the corpus (Alan Miller, Leah Gordon, Adam Perry). Those names are corpus examples, not a closed list coded here.
8. Production export stays behind the existing human approval gate. This procedure does not approve, export, or send mail.

## Required concept fields

The DOCX frontmatter table and the CI paragraph require these concept fields:

| Field | Rule |
|---|---|
| `type` | String. Fixed to `Lifecycle Email Campaign`. |
| `title` | Formal event name. |
| `description` | Short retrieval context. |
| `resource` | Canonical URL when the brief has one. Otherwise `[LINK]`. |
| `tags` | Array. Empty when the brief has none. |
| `sources` | Provenance objects pointing at the procedural source, the JSON source, the email profile, and the brand model. |
| `verified` | Human sign-off objects. Empty while the concept is a draft. |
| `status` | `draft`, `approved`, or `active`. |

The CI paragraph names `type`, `title`, `description`, `sources`, `verified`, and `status` as the keys that must be present. `resource` and `tags` are in the frontmatter table. A draft may use `[LINK]` for `resource` instead of inventing a URL.

Each email asset also has `lifecycle_stage`, `subject`, `preview_text`, `body`, `cta`, `validation`, and provenance. The greeting in approved examples is `Hi {{Recipient.FirstName}},`.

## Lifecycle stages

The standard lifecycle is seven emails:

1. Invitation #1
2. Invitation #2
3. Invitation #3
4. Reminder #1
5. Reminder #2
6. Attendee Follow-Up
7. Non-Attendee Follow-Up

That is 3 invitations + 2 reminders + 1 attendee follow-up + 1 non-attendee follow-up.

| Stage | DOCX style and objective | Intent used for generation |
|---|---|---|
| Invitation #1 | Strategic, thesis-led, consultative. 95–130 words. Establish the business challenge and value proposition. | Strategic opening, business value, event relevance. |
| Invitation #2 | Technical, peer-oriented, focused. 90–115 words. Architecture or peer relevance. | Technical and peer context, problem and solution context, stronger qualification. |
| Invitation #3 | Direct, scheduling-focused, polite. 75–100 words. Confirmation before roster closure. | Final registration window. Concise, direct, professional. No spam-style urgency. |
| Reminder #1 | Instructional logistics, including the 48/24-hour reminder. 110–150 words. | Operational logistics, with about 48 hours of lead time where applicable. |
| Reminder #2 | Day-of notice. Brief and mobile-optimized. 45–95 words. | Day-of, concise, mobile-friendly, immediate logistics. |
| Attendee Follow-Up | Appreciative and actionable. 100–140 words. Feedback and an advisory next step. | Thank the attendee, reinforce value, ask for feedback, optional next step. |
| Non-Attendee Follow-Up | Low-pressure and forward-looking. 75–115 words. Keep the relationship and point to the events path. | Acknowledge absence without guilt or pressure, and offer a future or resource path. |

`generate_event_email_sequence` returns those seven keys: `invitation_1`, `invitation_2`, `invitation_3`, `reminder_1`, `reminder_2`, `attendee_followup`, `non_attendee_followup`.

Registration Confirmation is a DOCX stage (operational, 70–115 words, confirm the calendar hold). It is not one of the seven, and it is not in `docs/email-content.json`.

## Generation rules

- Say 66degrees, and use `Google Cloud Premier Partner` from the brand terminology list. The JSON names Google Cloud as the primary cloud partner.
- Voice used from the JSON guideline is executive, consultative, technical, conversational, and direct. Stage copy uses the part of that voice that matches the stage.
- Invitation #1 states business value and why the event is relevant.
- Invitation #2 states the operational problem, the peer and technical context, and who should attend. It does not repeat the invitation #1 opening.
- Invitation #3 states the final registration window and stays shorter than invitation #1. It does not use "last chance", "act now", or "final invitation".
- Reminder #1 is logistics, including the 48-hour context. It does not repeat the invitation hook.
- Reminder #2 is the day-of note: date, start, venue, and onsite contact, written to be read on a phone. It is shorter than reminder #1.
- The attendee note thanks the reader, asks for feedback, and marks the next step as optional.
- The non-attendee note says the reader was unable to attend, does not use regret or guilt, and offers a future path.
- One standalone bracket CTA, taken from `cta_primary` when the brief has one.
- At most two functional URLs. The body uses `[LINK]` unless the brief itself contains a URL.
- Do not invent a venue, a statistic, a sender name, or a phone number. Numbers in the copy must already be in the brief, except the lifecycle's own "48" in reminder #1.
- Personalization uses `{{Recipient.FirstName}}`, matching the approved examples.
- Where the DOCX typical band and the general email profile overlap, generation aims at that overlap. The day-of band in the DOCX starts at 45 words and the general profile starts at 75, so generated day-of copy stays at or above 75. Both bounds remain in the conflict record.

## Validation rules

Counts use a whitespace split. Stored `metrics` on an approved example are preserved even when they do not match that split.

| Check | Source | Enforced failure when sources agree or the rule is explicit and uncontradicted |
|---|---|---|
| Subject 30–50 characters | JSON benchmark and DOCX engineering sentence, also the general email profile | Yes |
| Subject maximum 9 words | JSON `subject_line_max_words` | Yes, together with the DOCX maximum |
| Subject 6–9 words | DOCX CI paragraph | Reported. A subject under 6 words fails the DOCX check and passes the JSON maximum. That disagreement is a conflict, not a silent pass or a silent fail. A subject over 9 words fails both. |
| Subject characters 22–64 | DOCX empirical table | Reported beside 30–50. It does not replace 30–50. |
| Preview maximum 12 words | JSON `preview_text_max_words` | Yes |
| Preheader 40–100 characters | General email profile | Reported. The JSON does not state a character cap. |
| Body 45–215 words | JSON benchmarks and DOCX CI paragraph | Yes when both say the copy is outside that range |
| Body observed 45–212 words | DOCX prose (Padres day-of minimum, Detroit Tigers day-of maximum) | Reported. A body of 213–215 words passes 45–215 and exceeds 212. |
| Body over 220 words | DOCX risk sentence | Reported beside the 215 cap |
| Body 75–200 words | General email profile, for primary cold/promotional mail | Reported. Event sources allow 45–215. |
| Spam triggers | JSON list: `free!!!`, `act now`, `limited time only`, `guaranteed`, `raffle winner`, `claim your prize`, `urgent` | Yes |
| Discouraged phrases | DOCX substitution table | Yes. See the table below. |
| Functional URLs | JSON maximum 2, DOCX maximum two | Yes |
| Public URL shorteners | DOCX | Yes. The DOCX does not name hosts. The checker flags `bit.ly`, `bitly.com`, `tinyurl.com`, `tiny.cc`, `t.co`, `goo.gl`, `ow.ly`, and `buff.ly`. |
| Subject punctuation | DOCX engineering sentence: no exclamation marks, currency signs, or capitalization spikes | Yes |
| One CTA | Approved examples use one standalone bracket CTA. The general profile also says a single CTA. | Yes |
| Greeting and sign-off | Approved examples | Yes for `{{Recipient.FirstName}}` and `Best regards,` / `The 66degrees Team` |
| Status and verification | DOCX | `draft`, `approved`, and `active` stay distinct. `approved` or `active` requires a non-empty `verified` list. |

Operational requirements from the DOCX are not things an email body can prove: SPF aligned to the outbound IP, DKIM 2048-bit, DMARC moving toward quarantine or rejection, complaint rate below 0.1% and never above 0.3%, and List-Unsubscribe with one-click removal within two days. The JSON authentication list is SPF Alignment, DKIM 2048-bit, and DMARC Enforcement. Those requirements stay on the model. They are not treated as satisfied because the copy formatted cleanly.

### DOCX substitution table

| Avoid | Use instead |
|---|---|
| Exclusive 66degrees swag | Executive resources and follow-up discussion |
| Raffle | To express our appreciation for your feedback |
| Save your spot / Seats Limited | Confirm your attendance / Register your team |
| Final invitation / Last chance | Upcoming session briefing / Final registration window |
| Complimentary hosted bar and free drinks | Complimentary suite hospitality and catering |

Approved examples use "Final Registration" and venue-capacity language. Those are not the discouraged strings above, so the fixtures are not failed for them.

## Governance

- `draft`: generated or not yet verified. This is the only status the generator sets.
- `approved`: a human verification record exists and a person approved the concept. The JSON examples are approved because the file says so, including `human:Alan Miller` and `human:Leah Gordon`.
- `active`: executable status distinct from approved. The generator does not set it.
- Passing formatting validation does not approve a concept and does not open the export gate.

## Provenance

Every generated asset records:

- `docs/Event Email OKF Model Generation.docx`
- `docs/email-content.json`
- `references/66degrees_email_content_writing_guideline.json`
- `core/brand/brand_rules.json`

`verified` stays empty until a person signs. Placeholders that remain in the body are listed on the asset.

## Approval requirements

Missing verification stays `draft`. MCP consumers must not treat an unapproved concept as executable. Campaign export still calls the existing approval gate (`require_approved` / `assert_exportable`). This email work does not change that gate.

## Approved examples

`docs/email-content.json` contains three approved concepts, each with seven templates:

- `campaigns/sports-executive-hospitality/sf-giants-oracle-park`
- `campaigns/technical-summits/scale-with-ai-irvine`
- `campaigns/executive-receptions/bio-it-happy-hour-boston`

Preserve placeholders such as `[AV]`, `[LINK]`, `[DATE]`, `{{Recipient.FirstName}}`, and bracket CTAs such as `[Confirm Suite Registration]`. The Irvine venue is `[AV] Irvine, 16500 Scientific`.

Some approved subjects are longer than 50 characters, one approved subject is five words, and one approved day-of body is under 75 words. Those examples stay as written. They are why the conflicts below exist. New mail targets the overlap that can satisfy the stated rules together, and it does not rewrite the examples.

## Conflicts for human review

No conflict below has been resolved by deleting a source rule.

| ID | What the sources say |
|---|---|
| `subject_character_range` | JSON, the DOCX engineering sentence, and the email profile say 30–50 characters. The DOCX empirical table says 22–64. Some approved subjects are longer than 50 characters. |
| `subject_word_count` | JSON states a maximum of 9 and no minimum. The DOCX CI paragraph says strictly 6–9 words. Extracted empirical table cells 48 and 98 concatenate a citation marker; mean 6.98 makes them unusable, so they are not thresholds. |
| `body_word_count` | JSON and the DOCX CI paragraph say 45–215 words. DOCX prose says the observed maximum is 212 words. A risk sentence flags copy that exceeds 220 words. Extracted table cells 458 and 2128 are citation-concatenated and are not thresholds. |
| `preview_word_count` | JSON says a maximum of 12 preview words. The DOCX CI paragraph states no preview cap. Empirical preview cells extract as 28 and 148 against a mean of 7.88, so no reconstructed preview cap is enforced. |
| `lifecycle_length` | The JSON and the seven-email API have no registration confirmation. The DOCX says seven emails and also lists Registration Confirmation. |
| `general_email_profile_vs_event_lifecycle` | The general profile says 75–200 words and a 40–100 character preheader, with a separate opening field. Event sources say 45–215 body words, a 12-word preview cap, and one body field. `validate_okf_content("email")` still uses the profile. |
| `sign_off_shape` | The general profile asks for a full name, role, and contact details. Event examples sign off as "The 66degrees Team". Generation follows the examples and does not invent a sender. |
| `non_attendee_regret_phrasing` | The DOCX calls the non-attendee note low-pressure. Approved Irvine copy says "We regret that you were unable to join". That sentence stays in the JSON. New copy does not use it. |
| `stored_metrics_vs_whitespace_count` | Stored template metrics do not always match a whitespace split of the same text. The metrics are preserved. Validation counts with a whitespace split. |
| `metrics_and_unsupported_claims` | The email profile says to reference real metrics. The brand rules say not to invent claims. Generation copies a metric only when the brief already contains it. |

## Relationship to the rest of the OKF model

The four guideline profiles (`blog`, `case_study`, `email`, `event_landing_page`) stay the OKF profiles. Event lifecycle mail is an extension of the email profile plus these two sources. It is not a fifth profile and it is not a new MCP tool. The campaign kit's `email_campaign` is this seven-email sequence.
