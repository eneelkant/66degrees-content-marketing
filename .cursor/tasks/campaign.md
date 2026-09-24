# Task: /campaign

## Objective
Create a governed marketing campaign that stops at human approval.

## Inputs
- Marketing brief JSON (`campaign_name`, `objective`, channels, audience, …)

## MCP tools
- `create_campaign` (primary)
- `get_campaign_status`
- `resume_campaign` if interrupted

## Expected output
- `campaign_id`
- `status=APPROVAL_PENDING`
- generated assets + QA summary
- export blocked

## Validation
- Confirm approval pending
- Confirm export raises without approval
- `LLM_PROVIDER=mock` for automated runs

## Safety
- Never call `approve_*` unless a human requested approval
- Never export before approval
