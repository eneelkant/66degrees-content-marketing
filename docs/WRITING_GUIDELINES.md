# Writing guidelines integration

The Content MCP loads curated 66degrees writing rules from `content_knowledge/` and applies them on generation, optimization, and QA. Client adapters (Claude, ChatGPT, Gemini, Cursor) call the same 16 MCP tools; they do not carry a separate copy of the full guideline set.

## Where guidelines live

| Path | Purpose |
|---|---|
| `content_knowledge/VERSION` | Guideline version string (e.g. `2026.10.26`) |
| `content_knowledge/writing_guidelines/` | Maintainable rule docs |
| `content_knowledge/source_manifest.md` | ZIP source → repo mapping |
| `content_knowledge/conflicts_and_exceptions.md` | Precedence and known conflicts |
| `core/writing/` | Loader, skill selection, prompt subsetting, compliance |

Sources inspected from the Content Knowledge ZIP are listed in the source manifest. Craft-book files are distilled; mandatory company/messaging/writing/format/specs docs are preserved in meaning.

## Skills

| Skill id | Role |
|---|---|
| `brand_voice` | Tone, vocabulary, embedded credential, human voice |
| `audience_messaging` | Buyer altitude, positioning, brief fields |
| `content_generation` | Apply rules while drafting |
| `content_optimization` | Same authoritative source when rewriting |
| `content_qa` | Deterministic hard failures + soft warnings |
| `channel_adaptation` | Email / social / ads / reg-page specs |
| `pre_publication_review` | Checklist before approval gate |
| `ceo_voice` | Leadership / PR / Ben Kessler voice only |

`select_skills(asset_type, brief_data, mode)` chooses a subset. `build_writing_prompt(...)` loads only the related docs under a character budget.

## Runtime path

```text
brief → build_generation_context (loads writing prompt + skills)
      → generate / optimize / repurpose (prompt + metadata)
      → evaluate_compliance / qa_validate_asset (writing_guidelines check)
      → human approval (unchanged)
      → export
```

Optional response fields (backward compatible):

- `guideline_version`
- `applicable_skills`
- `writing_compliance` (`status`, `hard_failures`, `warnings`, `suggested_fixes`)

## Hard failures vs warnings

- **Hard failure** → QA state `REWRITE` / compliance `needs_revision` (banned terms, Premier Partner, competitor clouds, dashes, unsupported numbers, channel limit breaches, legacy names).
- **Warning** → QA state `WARNING` when no hard failures (mechanical style, recap bridges, credential stacking, unknown social template limits, CEO vs v17 wording).

Missing guideline files yield `unavailable` — the system must not silently claim compliance.

## Writing compliance ≠ facts ≠ approval

1. Writing-style compliance checks encoded rules from the knowledge base.
2. Factual verification is limited: unsupported numbers vs brief/proof excerpts are flagged; the checker does not prove every claim true.
3. Human approval remains mandatory before export (`approval_required=True`, gate `LOCKED` until `approve_*`).

## Updating guidelines

1. Edit the relevant file under `content_knowledge/writing_guidelines/`.
2. Note conflicts in `conflicts_and_exceptions.md` and sources in `source_manifest.md`.
3. Bump `content_knowledge/VERSION`.
4. Extend deterministic checks in `core/writing/compliance.py` when a rule is objectively testable.
5. Run `./scripts/check.sh && ./scripts/test.sh` (includes `tests/test_writing_guidelines.py`).

Guideline updates do not require changing each MCP tool: tools go through `build_generation_context` and `qa_validate_asset`.

## Clients

Claude, ChatGPT, Gemini, and Cursor continue to use `clients/public_api.py` / `clients/surface.py` (16 tools). Concise client configs may tell the model to use MCP writing/QA tools; authoritative rules stay in `content_knowledge/` + `core/writing/`.
