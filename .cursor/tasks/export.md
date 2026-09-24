# Task: /export

## Objective
Export an approved campaign/kit to JSON, DOCX, or XLSX.

## Inputs
- `campaign_id` or `kit_id`
- `export_format`

## MCP tools
- `export_campaign`
- `export_campaign_kit`

## Expected output
- File path; status EXPORTED

## Validation
- Must fail with PermissionError if not approved

## Safety
- Never bypass approval to force export
