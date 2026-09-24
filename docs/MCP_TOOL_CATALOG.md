# MCP tool catalog

Public surface: `clients/surface.py` (16 tools). Implementations: `clients/public_api.py`. Claude/Cursor server: `clients/claude/server.py`.

Classifications are derived from implementation behavior.

| Tool | Purpose | Inputs | Outputs | Dependencies | Calls LLM? | Credentials? | Modifies data? | Autonomous-safe? | Classification | Tests |
|---|---|---|---|---|---|---|---|---|---|---|
| `generate_content_strategy` | Build content strategy from goals | `goals_json` | strategy object | none | No (deterministic) | No | No | Yes | GENERATIVE | e2e journey |
| `process_event_brief` | Validate/normalize event brief | `brief_data` | status, missing fields, brief | event intake | No | No | No | Yes | READ_ONLY | test_event_brief, mcp smoke |
| `generate_campaign_kit` | Multi-channel kit | `brief_data` | kit + `kit_id` | campaign kit generators | No (template generators) | No | In-memory kit store | Yes | GENERATIVE | test_campaign_kit, e2e |
| `generate_content_asset` | Single asset by type | `asset_type`, `brief_data` | asset + `asset_id` | content factory + references | Optional via strategies | Optional if live LLM | In-memory assets | Yes with mock | GENERATIVE | test_generation_context |
| `refine_content_asset` | Refine existing asset | `asset_id`, feedback | optimized asset | optimizer + LLM router | Yes (mock/live) | Optional | Updates asset store | Yes with mock | TRANSFORMATIVE | test_step10 |
| `generate_social_posts` | Platform posts from source | source asset, platforms | assets list | repurposer | Yes (mock/live) | Optional | No persistent | Yes with mock | GENERATIVE | e2e journey, orchestrator |
| `repurpose_content_asset` | Convert formats | source, target_formats | assets | repurposer + LLM | Yes (mock/live) | Optional | No | Yes with mock | TRANSFORMATIVE | test_step10 |
| `optimize_content_asset` | Improve using QA feedback | asset, QA feedback | optimized asset | optimizer + LLM | Yes (mock/live) | Optional | No | Yes with mock | TRANSFORMATIVE | test_step10 |
| `qa_validate_asset` | Brand/hard/originality QA | content, asset_type | QA report | brand rules, references, emailens | No (analyzers) | No | No | Yes | READ_ONLY | test_qa_step9 |
| `approve_campaign_kit` | Human approve kit | `kit_id` | approval record | HumanApprovalGate | No | No | Approval records + campaign sync | **Human gate** | EXTERNAL_SIDE_EFFECT | test_step10, e2e |
| `export_campaign_kit` | Export approved kit | `kit_id`, format | file path | exporters, approval gate | No | No | Writes export files | Only after approval | EXPORT | test_step10, e2e |
| `create_campaign` | Full pipeline → approval pending | marketing `brief_data` | campaign summary | orchestrator + above tools | Indirect (stages) | Optional | Persists `data/campaigns/*.json` | Yes; stops at approval | GENERATIVE | orchestrated campaign e2e |
| `get_campaign_status` | Read campaign state | `campaign_id` | status summary | CampaignStore | No | No | No | Yes | READ_ONLY | orchestrated e2e |
| `resume_campaign` | Continue from persisted stage | `campaign_id` | status / continued run | orchestrator | Indirect | Optional | Updates campaign JSON | Yes; never skips approval | TRANSFORMATIVE | orchestrated e2e |
| `approve_campaign` | Human approve campaign | `campaign_id` | summary | state machine + kit gate | No | No | State + approval | **Human gate** | EXTERNAL_SIDE_EFFECT | state machine + e2e |
| `export_campaign` | Export approved campaign | `campaign_id`, format | export result | status machine + exporters | No | No | Export files + state | Only when APPROVED | EXPORT | orchestrated e2e |

## Classification key

- **READ_ONLY** — inspect/validate only
- **GENERATIVE** — creates new content/state
- **TRANSFORMATIVE** — mutates/transforms existing content or resumes pipeline
- **EXPORT** — writes deliverable artifacts
- **EXTERNAL_SIDE_EFFECT** — records human approval / irreversible gate action

## Safety notes for autonomous agents

1. Prefer `create_campaign` for end-to-end work; it **must not** auto-export.
2. Never call `export_*` unless status is `APPROVED`.
3. Use `LLM_PROVIDER=mock` in CI and unattended dry-runs.
4. Remote HTTP MCP still requires `MCP_AUTH_TOKEN` / `MCP_API_KEY`.
5. Pass `idempotency_key` on `create_campaign` to avoid duplicates on retry.
6. `approve_campaign` / `export_campaign` are idempotent once already approved/exported.
7. Remaining QA `REWRITE` yields `REVISION_REQUIRED` — call `resume_campaign` after fixes.
