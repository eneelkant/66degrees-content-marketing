# Task: /qa

## Objective
Run QA validation and summarize PASS / WARNING / REWRITE.

## Inputs
- Content JSON + `asset_type`
- Or `campaign_id` via `get_campaign_status`

## MCP tools
- `qa_validate_asset`
- `optimize_content_asset` if revision needed
- `get_campaign_status`

## Expected output
- QA report with `approval_required=true`

## Validation
- Do not weaken checks to force PASS

## Safety
- Never approve solely because QA passed — human gate remains
