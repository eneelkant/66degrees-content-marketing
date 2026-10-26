# 66degrees content knowledge

Authoritative writing guidelines for Content MCP generation, optimization, and QA.

This tree is a curated extract of the 66degrees Content Knowledge pack (ZIP inspected
2026-10-26). It is **not** a wholesale dump of craft books into every prompt.

## Layout

| Path | Role |
|---|---|
| `writing_guidelines/` | Maintainable rules used at runtime |
| `source_manifest.md` | Every archive file inspected and how it maps here |
| `conflicts_and_exceptions.md` | Conflicts, precedence, and unresolved ambiguities |
| `VERSION` | Guideline version string returned in compliance metadata |

## Precedence (mandatory)

1. Company facts (`company_facts.md`)
2. Messaging foundation (`messaging_and_terminology.md`)
3. Writing rules (`brand_voice.md`, `audience_and_positioning.md`, …)
4. Format and channel specs (`content_structure.md`, `social_and_email.md`, specs)
5. Reader journey (persuasion adapted to 66 voice)
6. Proof index (verified figures only)
7. CEO voice (leadership / external only)
8. Craft mechanisms — reference only; **66 rules win** on conflict
9. Specs and guardrails (character / word limits)

## Runtime use

Load via `core.writing` (`load_guidelines`, `select_skills`, `build_writing_prompt`,
`evaluate_compliance`). Do not paste this entire tree into every LLM call — skills
select a relevant subset by asset type and channel.

Writing-style compliance is **not** factual verification and **not** human approval.
Export still requires the existing approval gate.
