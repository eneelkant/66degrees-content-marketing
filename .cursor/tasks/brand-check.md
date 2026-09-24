# Task: /brand-check

## Objective
Validate text/assets against 66degrees brand rules.

## Inputs
- Text or asset JSON

## MCP tools
- Prefer `qa_validate_asset` (includes brand)
- Or load `core.brand.rules.load_brand_rules`

## Expected output
- Forbidden jargon / terminology issues list

## Validation
- Use `core/brand/brand_rules.json` only — do not invent rules

## Safety
- Brand failures require revision before human approval
