# Task: /approve

## Objective
Record explicit human approval for a campaign or kit.

## Inputs
- `campaign_id` or `kit_id`
- Confirmation that a human reviewed the assets

## MCP tools
- `approve_campaign`
- `approve_campaign_kit`

## Expected output
- Approval record; status APPROVED

## Validation
- Reject if status is QA_FAILED
- Confirm prior APPROVAL_PENDING when using orchestrator

## Safety
- **Human-only.** Agents must not fabricate approval.
- Do not export in the same step unless the human also requested export
