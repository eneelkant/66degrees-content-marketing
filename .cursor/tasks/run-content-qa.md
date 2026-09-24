# Task: run-content-qa

## Objective
Run QA validation on a content asset and summarize PASS / WARNING / REWRITE with actionable issues.

## Required inputs
- Asset JSON (or kit asset)
- `asset_type`

## Inspect
- `core/qa/engine.py`, `core/qa/brand.py`, `core/brand/brand_rules.json`
- `clients.public_api.qa_validate_asset`

## Expected output
- QA report with `overall_status`, check details, `approval_required=True`

## Validation
- Call with `LLM_PROVIDER=mock`
- Confirm approval still required before export
