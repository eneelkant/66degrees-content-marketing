# Conflicts and exceptions

Recorded during ZIP integration (2026-10-26). Do not invent resolutions beyond what sources state.

## Precedence (settled)

From `00_README.md` / company facts:

1. Company facts win over every other source.
2. Messaging v17 is the canonical brand messaging source.
3. Where craft (`08_CRAFT_*`) conflicts with 66 rules, **66 rules win**.
4. CEO voice skill outranks generic style for leadership / PR / external material attributed to Ben Kessler or 66degrees leadership — but **LOCKED company facts still apply** (Diamond Partner, no invented client names, literal truth). Dashes: company writing rules ban dashes; CEO tracked edits sometimes retain comma-paired phrasing instead. Prefer no dashes; do not introduce em/en dashes to mimic drama.

## Known conflicts with older repository artifacts

| Topic | Older repo artifact | New knowledge base | Resolution |
|---|---|---|---|
| Partner tier | `references/*guideline*.json` and legacy brand note "Premier Partner" | Company facts: Google Cloud **Diamond** Partner; never "Premier" | Runtime brand + writing compliance treat Diamond as mandatory; "Premier Partner" / "GCP Partner" are hard failures. Update OKF JSON when those files are next revised; until then, QA overrides. |
| Strategic pillars | `brand_rules.json` listed Modernize / Build / Manage & Scale | Messaging v17: five value pillars described as lifecycle phases, never catalog names | Generation prompts use v17 pillars; legacy pillar list retained only as historical brand_rules field until a separate brand-model migration. |
| Blog OKF "pain point" intro | Blog guideline asks to define enterprise pain point | Writing rules: bottom-of-funnel buyers; never restate the problem; lead with solution/outcome | Writing rules win for generation/QA. |
| Ben voice vs v17 wording | CEO uses "AI-first and AI-native", "Google's full-stack AI platform" | v17 prefers other framing in places | For CEO-voice assets: keep Ben's terms and flag the conflict in compliance **warnings** (not silent rewrite). For standard brand assets: follow v17. |

## Ambiguities (do not invent a rule)

- Exact LinkedIn / social character counts: specs say match the previous approved template of that type when no new limit is given. Deterministic QA warns when social limits are unknown rather than inventing numbers.
- UK audience assets: use British English and UK date format — only when the brief marks UK audience.
- Revenue figures: internal only. Projected figures must be labeled projected. Deterministic checks cannot always know projection status; flag unlabeled large currency claims as warnings when not present in proof excerpts.
- Named clients require logo clearance. Presence in the proof index does not auto-clear logo use in a new asset.

## Exceptions explicitly allowed by source

- Hyphen in **AI-Native** / **AI-native** compound branding (writing rules: no dashes, with this hyphen exception).
- Degree symbol in **Paradigm°** (required).
- Contractionsions are fine.
- CEO voice may use full names with parenthetical acronyms (FDEs, FDEU) after first full use.
