# Task: validate-brand

## Objective
Validate text/assets against 66degrees brand rules (terminology + forbidden jargon).

## Required inputs
- Text or asset JSON

## Inspect
- `core/brand/rules.py`, `core/brand/brand_rules.json`
- `core/qa/brand.py`

## Expected output
- List of forbidden jargon and terminology replacements
- Clear pass/fail

## Validation
- Unit test or scripted call to `load_brand_rules().validate_text(...)`
- Do not weaken rules to force a pass
